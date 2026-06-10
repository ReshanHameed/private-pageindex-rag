from __future__ import annotations

import json
from typing import Any

import httpx

from private_pageindex.config import get_settings


class OllamaError(RuntimeError):
    """Base error for local Ollama client failures."""


class OllamaConnectionError(OllamaError):
    """Raised when the local Ollama server cannot be reached."""


class OllamaTimeoutError(OllamaError):
    """Raised when the local Ollama server does not respond in time."""


class OllamaModelNotFoundError(OllamaError):
    """Raised when the configured local model is not available."""


class OllamaInvalidResponseError(OllamaError):
    """Raised when Ollama returns an unexpected or unparsable response."""


class OllamaClient:
    """Small synchronous client for Ollama's local /api/chat endpoint."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 300.0,
        http_client: httpx.Client | None = None,
    ):
        settings = get_settings()
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.timeout = timeout
        self._client = http_client or httpx.Client(timeout=timeout)

    def chat_text(self, system: str, user: str, history: list[dict[str, str]] | None = None) -> str:
        messages = [{"role": "system", "content": system}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user})
        
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"num_ctx": 4096},
        }
        response_payload = self._post_chat(payload)
        return self._extract_message_content(response_payload)

    def chat_json(
        self,
        system: str,
        user: str,
        schema_hint: str | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        json_system = system
        if schema_hint:
            json_system = f"{system}\nReturn valid JSON matching this shape:\n{schema_hint}"
            
        messages = [{"role": "system", "content": json_system}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user})
            
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": "json",
            "options": {"num_ctx": 4096},
        }
        response_payload = self._post_chat(payload)
        content = self._extract_message_content(response_payload)
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise OllamaInvalidResponseError(
                "Ollama response message.content was not valid JSON."
            ) from exc
        if not isinstance(parsed, dict):
            raise OllamaInvalidResponseError(
                "Ollama JSON response must be a JSON object."
            )
        return parsed

    def close(self) -> None:
        self._client.close()

    def check_health(self) -> dict[str, Any]:
        """Lightweight health check using ``/api/tags`` (no inference).

        Returns a dict with ``status``, ``model``, and ``models`` keys.
        This does NOT load or run the model — it just checks whether the
        Ollama server is reachable and lists available models.
        """
        url = f"{self.base_url}/api/tags"
        try:
            response = self._client.get(url, timeout=5.0)
            response.raise_for_status()
        except httpx.ConnectError:
            return {"status": "unreachable", "detail": f"Cannot connect to {self.base_url}"}
        except httpx.TimeoutException:
            return {"status": "timeout", "detail": "Ollama server did not respond in time"}
        except Exception as exc:
            return {"status": "error", "detail": str(exc)}

        try:
            data = response.json()
        except Exception:
            return {"status": "error", "detail": "Invalid response from Ollama"}

        models = data.get("models", [])
        model_names = [m.get("name", "") for m in models]
        model_available = any(self.model in name for name in model_names)

        return {
            "status": "connected",
            "model": self.model,
            "model_available": model_available,
            "models": model_names,
        }

    def _post_chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/api/chat"
        try:
            response = self._client.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise OllamaTimeoutError(
                f"Ollama request timed out after {self.timeout} seconds."
            ) from exc
        except httpx.ConnectError as exc:
            raise OllamaConnectionError(
                f"Could not connect to local Ollama server at {self.base_url}."
            ) from exc
        except httpx.HTTPStatusError as exc:
            self._raise_status_error(exc.response)

        try:
            response_payload = response.json()
        except json.JSONDecodeError as exc:
            raise OllamaInvalidResponseError(
                "Ollama HTTP response body was not valid JSON."
            ) from exc
        if not isinstance(response_payload, dict):
            raise OllamaInvalidResponseError(
                "Ollama HTTP response body must be a JSON object."
            )
        return response_payload

    def _raise_status_error(self, response: httpx.Response) -> None:
        error_text = response.text
        try:
            response_payload = response.json()
            if isinstance(response_payload, dict):
                error_text = str(response_payload.get("error", error_text))
        except json.JSONDecodeError:
            pass

        if response.status_code == 404 and "model" in error_text.lower():
            raise OllamaModelNotFoundError(
                f"Ollama model is not available locally: {self.model}. "
                f"Server said: {error_text}"
            )
        raise OllamaError(
            f"Ollama request failed with HTTP {response.status_code}: {error_text}"
        )

    @staticmethod
    def _extract_message_content(response_payload: dict[str, Any]) -> str:
        message = response_payload.get("message")
        if not isinstance(message, dict) or not isinstance(
            message.get("content"), str
        ):
            raise OllamaInvalidResponseError(
                "Ollama response must contain message.content."
            )
        return message["content"]


class AsyncOllamaClient:
    """Async counterpart of :class:`OllamaClient`.

    Uses ``httpx.AsyncClient`` so it can be ``await``-ed inside async
    FastAPI route handlers without blocking the event loop.  The method
    signatures mirror the sync client exactly so both satisfy the
    ``LLMProvider`` / ``AsyncLLMProvider`` protocols.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 300.0,
        http_client: httpx.AsyncClient | None = None,
    ):
        settings = get_settings()
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.timeout = timeout
        self._client = http_client or httpx.AsyncClient(timeout=timeout)

    async def chat_text(self, system: str, user: str, history: list[dict[str, str]] | None = None) -> str:
        messages = [{"role": "system", "content": system}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user})
        
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"num_ctx": 4096},
        }
        response_payload = await self._post_chat(payload)
        return OllamaClient._extract_message_content(response_payload)

    async def chat_json(
        self,
        system: str,
        user: str,
        schema_hint: str | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        json_system = system
        if schema_hint:
            json_system = f"{system}\nReturn valid JSON matching this shape:\n{schema_hint}"
            
        messages = [{"role": "system", "content": json_system}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user})
            
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": "json",
            "options": {"num_ctx": 4096},
        }
        response_payload = await self._post_chat(payload)
        content = OllamaClient._extract_message_content(response_payload)
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise OllamaInvalidResponseError(
                "Ollama response message.content was not valid JSON."
            ) from exc
        if not isinstance(parsed, dict):
            raise OllamaInvalidResponseError(
                "Ollama JSON response must be a JSON object."
            )
        return parsed

    async def chat_text_stream(
        self,
        system: str,
        user: str,
        history: list[dict[str, str]] | None = None,
    ) -> Any:
        """Async generator that yields text tokens from Ollama streaming."""
        import collections.abc

        messages = [{"role": "system", "content": system}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user})

        url = f"{self.base_url}/api/chat"
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {"num_ctx": 4096},
        }

        try:
            async with self._client.stream(
                "POST", url, json=payload, timeout=self.timeout
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    msg = chunk.get("message", {})
                    content = msg.get("content", "")
                    if content:
                        yield content
                    if chunk.get("done", False):
                        return
        except httpx.TimeoutException as exc:
            raise OllamaTimeoutError(
                f"Ollama streaming request timed out after {self.timeout} seconds."
            ) from exc
        except httpx.ConnectError as exc:
            raise OllamaConnectionError(
                f"Could not connect to local Ollama server at {self.base_url}."
            ) from exc
        except httpx.HTTPStatusError as exc:
            self._raise_status_error(exc.response)

    async def close(self) -> None:
        await self._client.aclose()

    async def check_health(self) -> dict[str, Any]:
        """Async lightweight health check using ``/api/tags``."""
        url = f"{self.base_url}/api/tags"
        try:
            response = await self._client.get(url, timeout=5.0)
            response.raise_for_status()
        except httpx.ConnectError:
            return {"status": "unreachable", "detail": f"Cannot connect to {self.base_url}"}
        except httpx.TimeoutException:
            return {"status": "timeout", "detail": "Ollama server did not respond in time"}
        except Exception as exc:
            return {"status": "error", "detail": str(exc)}

        try:
            data = response.json()
        except Exception:
            return {"status": "error", "detail": "Invalid response from Ollama"}

        models = data.get("models", [])
        model_names = [m.get("name", "") for m in models]
        model_available = any(self.model in name for name in model_names)

        return {
            "status": "connected",
            "model": self.model,
            "model_available": model_available,
            "models": model_names,
        }

    async def _post_chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/api/chat"
        try:
            response = await self._client.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise OllamaTimeoutError(
                f"Ollama request timed out after {self.timeout} seconds."
            ) from exc
        except httpx.ConnectError as exc:
            raise OllamaConnectionError(
                f"Could not connect to local Ollama server at {self.base_url}."
            ) from exc
        except httpx.HTTPStatusError as exc:
            self._raise_status_error(exc.response)

        try:
            response_payload = response.json()
        except json.JSONDecodeError as exc:
            raise OllamaInvalidResponseError(
                "Ollama HTTP response body was not valid JSON."
            ) from exc
        if not isinstance(response_payload, dict):
            raise OllamaInvalidResponseError(
                "Ollama HTTP response body must be a JSON object."
            )
        return response_payload

    def _raise_status_error(self, response: httpx.Response) -> None:
        error_text = response.text
        try:
            response_payload = response.json()
            if isinstance(response_payload, dict):
                error_text = str(response_payload.get("error", error_text))
        except json.JSONDecodeError:
            pass

        if response.status_code == 404 and "model" in error_text.lower():
            raise OllamaModelNotFoundError(
                f"Ollama model is not available locally: {self.model}. "
                f"Server said: {error_text}"
            )
        raise OllamaError(
            f"Ollama request failed with HTTP {response.status_code}: {error_text}"
        )
