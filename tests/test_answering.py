"""Tests for answer generation."""

from private_pageindex.retrieval.answering import AnswerResult, generate_answer, is_no_info_answer


SAMPLE_PAGES = [
    {"page_number": 2, "text": "Wear protective equipment at all times.", "char_count": 39},
    {"page_number": 3, "text": "Use goggles and gloves.", "char_count": 22},
]


class FakeTextClient:
    """Fake LLM client that returns a pre-configured answer."""

    def __init__(self, answer: str):
        self.answer = answer
        self.calls: list[dict] = []

    def chat_text(self, system: str, user: str, **kwargs) -> str:
        self.calls.append({"system": system, "user": user, **kwargs})
        return self.answer


class FailingTextClient:
    """Fake LLM client that always raises."""

    def chat_text(self, system: str, user: str, **kwargs) -> str:
        raise RuntimeError("Ollama connection refused")


def test_generate_answer_returns_cited_answer():
    client = FakeTextClient(
        "You must wear goggles and gloves [page 3] at all times [page 2]."
    )

    result = generate_answer(
        question="What safety equipment is required?",
        retrieved_pages=SAMPLE_PAGES,
        llm_client=client,
    )

    assert isinstance(result, AnswerResult)
    assert "[page 3]" in result.answer
    assert "[page 2]" in result.answer
    assert result.trace_step.action == "generate_answer"
    assert "2 page(s)" in result.trace_step.reason
    assert len(client.calls) == 1


def test_generate_answer_returns_no_info_when_no_pages():
    client = FakeTextClient("This should not be called")

    result = generate_answer(
        question="Anything",
        retrieved_pages=[],
        llm_client=client,
    )

    assert "could not find" in result.answer.lower()
    assert result.trace_step.action == "generate_answer"
    assert "No pages" in result.trace_step.reason
    # LLM should NOT have been called.
    assert len(client.calls) == 0


def test_generate_answer_handles_llm_failure():
    client = FailingTextClient()

    result = generate_answer(
        question="What is in the document?",
        retrieved_pages=SAMPLE_PAGES,
        llm_client=client,
    )

    assert "failed" in result.answer.lower()
    assert result.trace_step.action == "generate_answer"


def test_generate_answer_respects_char_budget():
    long_page = {
        "page_number": 1,
        "text": "A" * 5000,
        "char_count": 5000,
    }
    client = FakeTextClient("Answer based on truncated text.")

    result = generate_answer(
        question="Test budget",
        retrieved_pages=[long_page],
        llm_client=client,
        max_page_chars=200,
    )

    # The context sent to LLM should have been truncated.
    assert len(client.calls) == 1
    user_prompt = client.calls[0]["user"]
    # The page text in the prompt should be limited.
    assert len(user_prompt) < 5000
    assert result.trace_step.action == "generate_answer"


def test_generate_answer_includes_page_range_in_trace():
    client = FakeTextClient("Answer. [page 2]")

    result = generate_answer(
        question="Test",
        retrieved_pages=SAMPLE_PAGES,
        llm_client=client,
    )

    assert result.trace_step.pages == "2-3"


def test_is_no_info_answer_detects_negatives():
    assert is_no_info_answer("I could not find any information about safety rules.") is True
    assert is_no_info_answer("This document does not contain mention of contacts.") is True
    assert is_no_info_answer("The team names are not mentioned.") is True
    assert is_no_info_answer("Here is the answer: goggles are required.") is False

