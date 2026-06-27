"""Answer generation from retrieved page text."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from private_pageindex.config import get_settings
from private_pageindex.retrieval.tree_search import TraceStep


class AnswerError(RuntimeError):
    """Raised when answer generation fails."""


@dataclass(frozen=True)
class AnswerResult:
    """Generated answer with trace."""

    answer: str
    trace_step: TraceStep


def generate_answer(
    question: str,
    retrieved_pages: list[dict[str, Any]],
    llm_client: Any,
    *,
    max_page_chars: int | None = None,
    chat_history: list[dict[str, str]] | None = None,
) -> AnswerResult:
    """Generate an answer grounded in the retrieved page text.

    The answer must include ``[page N]`` citations referencing the source
    pages. If no pages are provided, returns a clear "no information" message
    without calling the LLM.
    """
    settings = get_settings()
    budget = max_page_chars or settings.max_page_chars

    if not retrieved_pages:
        no_info = "I could not find relevant information in the document to answer this question."
        return AnswerResult(
            answer=no_info,
            trace_step=TraceStep(
                action="generate_answer",
                node_id=None,
                pages=None,
                reason="No pages retrieved; returned default no-information answer.",
            ),
        )

    # --- Format retrieved pages as context ------------------------------------
    context_parts: list[str] = []
    page_numbers: list[int] = []
    total_chars = 0
    for page in retrieved_pages:
        pn = page.get("page_number", 0)
        text = page.get("text", "")
        if total_chars + len(text) > budget:
            remaining = budget - total_chars
            if remaining > 100:
                text = text[:remaining]
            else:
                break
        context_parts.append(f"--- Page {pn} ---\n{text}")
        page_numbers.append(pn)
        total_chars += len(text)

    context = "\n\n".join(context_parts)

    system_prompt = (
        "You are a local document assistant. Answer the user's question using "
        "ONLY the provided page text. Include [page N] citations for every "
        "fact you reference. If the text does not contain enough information "
        "to answer, say so clearly."
    )
    user_prompt = (
        f"Retrieved document pages:\n\n{context}\n\n"
        f"Question: {question}"
    )

    try:
        answer = llm_client.chat_text(system_prompt, user_prompt, history=chat_history)
    except Exception as exc:
        answer = f"Answer generation failed: {exc}"

    page_range_str = (
        f"{min(page_numbers)}-{max(page_numbers)}" if page_numbers else "none"
    )

    return AnswerResult(
        answer=answer,
        trace_step=TraceStep(
            action="generate_answer",
            node_id=None,
            pages=page_range_str,
            reason=f"Generated answer from {len(retrieved_pages)} page(s) "
                   f"({total_chars} chars of context).",
        ),
    )


async def generate_answer_async(
    question: str,
    retrieved_pages: list[dict[str, Any]],
    llm_client: Any,
    *,
    max_page_chars: int | None = None,
    chat_history: list[dict[str, str]] | None = None,
) -> AnswerResult:
    """Async version of :func:`generate_answer`.

    Identical logic but ``await``-s the LLM call so it can run inside
    an async FastAPI handler without blocking the event loop.
    """
    settings = get_settings()
    budget = max_page_chars or settings.max_page_chars

    if not retrieved_pages:
        no_info = "I could not find relevant information in the document to answer this question."
        return AnswerResult(
            answer=no_info,
            trace_step=TraceStep(
                action="generate_answer",
                node_id=None,
                pages=None,
                reason="No pages retrieved; returned default no-information answer.",
            ),
        )

    context_parts: list[str] = []
    page_numbers: list[int] = []
    total_chars = 0
    for page in retrieved_pages:
        pn = page.get("page_number", 0)
        text = page.get("text", "")
        if total_chars + len(text) > budget:
            remaining = budget - total_chars
            if remaining > 100:
                text = text[:remaining]
            else:
                break
        context_parts.append(f"--- Page {pn} ---\n{text}")
        page_numbers.append(pn)
        total_chars += len(text)

    context = "\n\n".join(context_parts)

    system_prompt = (
        "You are a local document assistant. Answer the user's question using "
        "ONLY the provided page text. Include [page N] citations for every "
        "fact you reference. If the text does not contain enough information "
        "to answer, say so clearly."
    )
    user_prompt = (
        f"Retrieved document pages:\n\n{context}\n\n"
        f"Question: {question}"
    )

    try:
        answer = await llm_client.chat_text(system_prompt, user_prompt, history=chat_history)
    except Exception as exc:
        answer = f"Answer generation failed: {exc}"

    page_range_str = (
        f"{min(page_numbers)}-{max(page_numbers)}" if page_numbers else "none"
    )

    return AnswerResult(
        answer=answer,
        trace_step=TraceStep(
            action="generate_answer",
            node_id=None,
            pages=page_range_str,
            reason=f"Generated answer from {len(retrieved_pages)} page(s) "
                   f"({total_chars} chars of context).",
        ),
    )


async def generate_answer_stream(
    question: str,
    retrieved_pages: list[dict[str, Any]],
    llm_client: Any,
    *,
    max_page_chars: int | None = None,
    chat_history: list[dict[str, str]] | None = None,
) -> Any:
    """Async generator version of :func:`generate_answer_async`.

    Yields dicts suitable for SSE serialization:

    - ``{"type": "context_ready", "page_count": N, "total_chars": M}``
    - ``{"type": "token", "text": "..."}``  (one per LLM token)
    - ``{"type": "answer_done", "answer": "full text", "pages": "1-5", "page_count": N}``

    If no pages are retrieved, yields a single ``answer_done`` with the
    default no-information message (no LLM call).
    """
    settings = get_settings()
    budget = max_page_chars or settings.max_page_chars

    if not retrieved_pages:
        no_info = "I could not find relevant information in the document to answer this question."
        yield {
            "type": "answer_done",
            "answer": no_info,
            "pages": "none",
            "page_count": 0,
        }
        return

    # --- Format retrieved pages as context ------------------------------------
    context_parts: list[str] = []
    page_numbers: list[int] = []
    total_chars = 0
    for page in retrieved_pages:
        pn = page.get("page_number", 0)
        text = page.get("text", "")
        if total_chars + len(text) > budget:
            remaining = budget - total_chars
            if remaining > 100:
                text = text[:remaining]
            else:
                break
        context_parts.append(f"--- Page {pn} ---\n{text}")
        page_numbers.append(pn)
        total_chars += len(text)

    context = "\n\n".join(context_parts)

    yield {
        "type": "context_ready",
        "page_count": len(page_numbers),
        "total_chars": total_chars,
    }

    system_prompt = (
        "You are a local document assistant. Answer the user's question using "
        "ONLY the provided page text. Include [page N] citations for every "
        "fact you reference. If the text does not contain enough information "
        "to answer, say so clearly."
    )
    user_prompt = (
        f"Retrieved document pages:\n\n{context}\n\n"
        f"Question: {question}"
    )

    full_answer_parts: list[str] = []
    try:
        async for token in llm_client.chat_text_stream(system_prompt, user_prompt, history=chat_history):
            full_answer_parts.append(token)
            yield {"type": "token", "text": token}
    except Exception:
        error_msg = "Answer generation failed due to an internal error."
        full_answer_parts = [error_msg]
        yield {"type": "token", "text": error_msg}

    full_answer = "".join(full_answer_parts)
    page_range_str = (
        f"{min(page_numbers)}-{max(page_numbers)}" if page_numbers else "none"
    )

    yield {
        "type": "answer_done",
        "answer": full_answer,
        "pages": page_range_str,
        "page_count": len(retrieved_pages),
    }


_NO_INFO_MARKERS = [
    "could not find",
    "does not contain",
    "no information",
    "not mentioned",
    "not contain",
    "does not mention",
    "not find any",
    "no details are provided",
]


def is_no_info_answer(answer: str) -> bool:
    """Check if the answer indicates that the information was not found.

    Used by the chat endpoint to detect negative answers and trigger broad
    fallback search retry.
    """
    lower = answer.lower()
    return any(marker in lower for marker in _NO_INFO_MARKERS)

