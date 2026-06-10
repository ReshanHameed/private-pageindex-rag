import json

import httpx
import pytest

from private_pageindex.llm.ollama import (
    OllamaClient,
    OllamaConnectionError,
    OllamaInvalidResponseError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
)


def mock_client(handler):
    transport = httpx.MockTransport(handler)
    return httpx.Client(transport=transport)


def test_chat_text_posts_to_local_chat_endpoint_and_returns_message_content():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        payload = json.loads(request.content)
        assert request.url == "http://localhost:11434/api/chat"
        assert payload == {
            "model": "gemma4:e4b",
            "messages": [
                {"role": "system", "content": "You answer briefly."},
                {"role": "user", "content": "Say local ok."},
            ],
            "stream": False,
            "options": {"num_ctx": 4096},
        }
        return httpx.Response(
            200,
            json={"message": {"role": "assistant", "content": "local ok"}},
        )

    client = OllamaClient(http_client=mock_client(handler))

    assert client.chat_text("You answer briefly.", "Say local ok.") == "local ok"
    assert len(requests) == 1


def test_chat_json_requests_json_format_and_parses_assistant_content():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["format"] == "json"
        assert "Return JSON" in payload["messages"][0]["content"]
        return httpx.Response(
            200,
            json={"message": {"content": "{\"selected_node_ids\": [\"0001\"]}"}},
        )

    client = OllamaClient(http_client=mock_client(handler))

    assert client.chat_json(
        system="Return JSON.",
        user="Select relevant nodes.",
        schema_hint='{"selected_node_ids": ["0001"]}',
    ) == {"selected_node_ids": ["0001"]}


def test_chat_json_rejects_invalid_json_content():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": "not json"}})

    client = OllamaClient(http_client=mock_client(handler))

    with pytest.raises(OllamaInvalidResponseError, match="valid JSON"):
        client.chat_json("system", "user")


def test_model_not_found_error_is_specific():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "model 'gemma4:e4b' not found"})

    client = OllamaClient(http_client=mock_client(handler))

    with pytest.raises(OllamaModelNotFoundError, match="gemma4:e4b"):
        client.chat_text("system", "user")


def test_connection_and_timeout_errors_are_wrapped():
    def connection_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out", request=request)

    connection_client = OllamaClient(http_client=mock_client(connection_handler))
    timeout_client = OllamaClient(http_client=mock_client(timeout_handler))

    with pytest.raises(OllamaConnectionError, match="localhost"):
        connection_client.chat_text("system", "user")

    with pytest.raises(OllamaTimeoutError, match="timed out"):
        timeout_client.chat_text("system", "user")


def test_invalid_ollama_response_shape_is_rejected():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"done": True})

    client = OllamaClient(http_client=mock_client(handler))

    with pytest.raises(OllamaInvalidResponseError, match="message.content"):
        client.chat_text("system", "user")
