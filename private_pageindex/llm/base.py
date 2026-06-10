"""Provider-agnostic LLM interface protocols.

These are structural protocols (PEP 544) — any class that implements
the right method signatures automatically satisfies them without
explicit inheritance.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LLMTextProvider(Protocol):
    """A provider that can generate free-text responses."""

    def chat_text(self, system: str, user: str) -> str: ...


@runtime_checkable
class LLMJsonProvider(Protocol):
    """A provider that can return structured JSON responses."""

    def chat_json(
        self,
        system: str,
        user: str,
        schema_hint: str | None = None,
    ) -> dict[str, Any]: ...


@runtime_checkable
class LLMProvider(LLMTextProvider, LLMJsonProvider, Protocol):
    """Combined text + JSON LLM provider."""

    ...


# -- Async counterparts -----------------------------------------------------


@runtime_checkable
class AsyncLLMTextProvider(Protocol):
    """Async provider that can generate free-text responses."""

    async def chat_text(self, system: str, user: str) -> str: ...


@runtime_checkable
class AsyncLLMJsonProvider(Protocol):
    """Async provider that can return structured JSON responses."""

    async def chat_json(
        self,
        system: str,
        user: str,
        schema_hint: str | None = None,
    ) -> dict[str, Any]: ...


@runtime_checkable
class AsyncLLMProvider(AsyncLLMTextProvider, AsyncLLMJsonProvider, Protocol):
    """Combined async text + JSON LLM provider."""

    ...
