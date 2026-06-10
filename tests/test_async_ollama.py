"""Tests for AsyncOllamaClient and LLM provider protocols."""

import json

import httpx
import pytest

from private_pageindex.llm.base import (
    AsyncLLMProvider,
    LLMProvider,
)
from private_pageindex.llm.ollama import (
    AsyncOllamaClient,
    OllamaClient,
    OllamaConnectionError,
    OllamaInvalidResponseError,
    OllamaTimeoutError,
)


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_sync_client_satisfies_llm_provider_protocol():
    client = OllamaClient(http_client=httpx.Client())
    assert isinstance(client, LLMProvider)
    client.close()


def test_async_client_satisfies_async_llm_provider_protocol():
    client = AsyncOllamaClient(http_client=httpx.AsyncClient())
    assert isinstance(client, AsyncLLMProvider)


# ---------------------------------------------------------------------------
# Async chat_text
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_async_chat_text_posts_and_returns_content():
    response_body = {
        "message": {"role": "assistant", "content": "Hello from async!"},
    }

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=response_body)

    transport = httpx.MockTransport(mock_handler)
    http_client = httpx.AsyncClient(transport=transport)
    client = AsyncOllamaClient(
        base_url="http://test-ollama:11434",
        model="test-model",
        http_client=http_client,
    )

    result = await client.chat_text("system prompt", "user message")
    assert result == "Hello from async!"
    await client.close()


# ---------------------------------------------------------------------------
# Async chat_json
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_async_chat_json_parses_json_response():
    json_content = {"selected_node_ids": ["0001", "0002"]}
    response_body = {
        "message": {
            "role": "assistant",
            "content": json.dumps(json_content),
        },
    }

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["format"] == "json"
        return httpx.Response(200, json=response_body)

    transport = httpx.MockTransport(mock_handler)
    http_client = httpx.AsyncClient(transport=transport)
    client = AsyncOllamaClient(
        base_url="http://test-ollama:11434",
        model="test-model",
        http_client=http_client,
    )

    result = await client.chat_json("system", "user", schema_hint='{"ids": []}')
    assert result == json_content
    await client.close()


@pytest.mark.anyio
async def test_async_chat_json_rejects_invalid_json():
    response_body = {
        "message": {"role": "assistant", "content": "not json at all"},
    }

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=response_body)

    transport = httpx.MockTransport(mock_handler)
    http_client = httpx.AsyncClient(transport=transport)
    client = AsyncOllamaClient(
        base_url="http://test-ollama:11434",
        model="test-model",
        http_client=http_client,
    )

    with pytest.raises(OllamaInvalidResponseError):
        await client.chat_json("system", "user")
    await client.close()


# ---------------------------------------------------------------------------
# Async error handling
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_async_connection_error_is_wrapped():
    async def mock_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    transport = httpx.MockTransport(mock_handler)
    http_client = httpx.AsyncClient(transport=transport)
    client = AsyncOllamaClient(
        base_url="http://unreachable:11434",
        model="test-model",
        http_client=http_client,
    )

    with pytest.raises(OllamaConnectionError):
        await client.chat_text("system", "user")
    await client.close()


@pytest.mark.anyio
async def test_async_timeout_error_is_wrapped():
    async def mock_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Read timed out")

    transport = httpx.MockTransport(mock_handler)
    http_client = httpx.AsyncClient(transport=transport)
    client = AsyncOllamaClient(
        base_url="http://slow-ollama:11434",
        model="test-model",
        http_client=http_client,
    )

    with pytest.raises(OllamaTimeoutError):
        await client.chat_text("system", "user")
    await client.close()


# ---------------------------------------------------------------------------
# Async health check
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_async_check_health_returns_model_info():
    tags_response = {
        "models": [
            {"name": "test-model:latest"},
            {"name": "other-model:latest"},
        ]
    }

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=tags_response)

    transport = httpx.MockTransport(mock_handler)
    http_client = httpx.AsyncClient(transport=transport)
    client = AsyncOllamaClient(
        base_url="http://test-ollama:11434",
        model="test-model",
        http_client=http_client,
    )

    health = await client.check_health()
    assert health["status"] == "connected"
    assert health["model_available"] is True
    assert "test-model:latest" in health["models"]
    await client.close()


@pytest.mark.anyio
async def test_async_check_health_handles_unreachable_server():
    async def mock_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    transport = httpx.MockTransport(mock_handler)
    http_client = httpx.AsyncClient(transport=transport)
    client = AsyncOllamaClient(
        base_url="http://unreachable:11434",
        model="test-model",
        http_client=http_client,
    )

    health = await client.check_health()
    assert health["status"] == "unreachable"
    await client.close()
