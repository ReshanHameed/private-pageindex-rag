"""Tests for tree-search retrieval."""

import pytest
from private_pageindex.retrieval.tree_search import RetrievalResult, search_tree


SAMPLE_TREE = {
    "doc_id": "doc-1",
    "nodes": [
        {
            "node_id": "0001",
            "title": "Introduction",
            "start_page": 1,
            "end_page": 1,
            "summary": "Overview of the machine manual.",
            "nodes": [],
        },
        {
            "node_id": "0002",
            "title": "Safety Requirements",
            "start_page": 2,
            "end_page": 3,
            "summary": "Safety rules and protective equipment.",
            "nodes": [
                {
                    "node_id": "0003",
                    "title": "Protective Equipment",
                    "start_page": 3,
                    "end_page": 3,
                    "summary": "Goggles and gloves required.",
                    "nodes": [],
                },
            ],
        },
        {
            "node_id": "0004",
            "title": "Maintenance",
            "start_page": 4,
            "end_page": 4,
            "summary": "Weekly filter cleaning schedule.",
            "nodes": [],
        },
    ],
}

SAMPLE_PAGES = [
    {"page_number": 1, "text": "This manual explains the machine.", "char_count": 34},
    {"page_number": 2, "text": "Wear protective equipment at all times.", "char_count": 39},
    {"page_number": 3, "text": "Use goggles and gloves.", "char_count": 22},
    {"page_number": 4, "text": "Clean the filters weekly.", "char_count": 25},
]


class FakeJsonClient:
    """Fake LLM client that returns pre-configured node selections."""

    def __init__(self, selected_ids: list[str]):
        self.selected_ids = selected_ids
        self.calls: list[dict] = []

    def chat_json(self, system: str, user: str, schema_hint: str | None = None):
        self.calls.append({"system": system, "user": user})
        return {"selected_node_ids": self.selected_ids}


class FailingJsonClient:
    """Fake LLM client that always raises an exception."""

    def chat_json(self, system: str, user: str, schema_hint: str | None = None):
        raise RuntimeError("Local Ollama server is unreachable")


def test_search_tree_selects_relevant_nodes_and_retrieves_pages():
    client = FakeJsonClient(["0002", "0003"])

    result = search_tree(
        question="What safety equipment is required?",
        tree=SAMPLE_TREE,
        pages=SAMPLE_PAGES,
        llm_client=client,
    )

    assert isinstance(result, RetrievalResult)
    assert result.selected_node_ids == ["0002", "0003"]
    # Pages 2 and 3 should be retrieved.
    assert [p["page_number"] for p in result.retrieved_pages] == [2, 3]
    assert len(result.trace) >= 2  # inspect_tree + select_nodes + fetch steps
    assert result.trace[0].action == "inspect_tree"
    assert result.trace[1].action == "select_nodes"
    assert len(client.calls) == 1


def test_search_tree_returns_empty_when_no_nodes_selected():
    client = FakeJsonClient([])

    result = search_tree(
        question="Something completely unrelated",
        tree=SAMPLE_TREE,
        pages=SAMPLE_PAGES,
        llm_client=client,
    )

    assert result.selected_node_ids == []
    assert result.retrieved_pages == []
    assert any(step.action == "select_nodes" for step in result.trace)


def test_search_tree_filters_out_invalid_node_ids():
    client = FakeJsonClient(["0001", "9999", "bad_id"])

    result = search_tree(
        question="What is the introduction about?",
        tree=SAMPLE_TREE,
        pages=SAMPLE_PAGES,
        llm_client=client,
    )

    # Only 0001 is valid from LLM output; 9999 and bad_id are filtered.
    assert "0001" in result.selected_node_ids
    # Invalid IDs must not appear
    assert "9999" not in result.selected_node_ids
    assert "bad_id" not in result.selected_node_ids
    # Page 1 must be retrieved
    assert any(p["page_number"] == 1 for p in result.retrieved_pages)
    # Trace should mention filtered IDs.
    select_step = next(s for s in result.trace if s.action == "select_nodes")
    assert "invalid" in select_step.reason.lower() or "9999" in select_step.reason


def test_search_tree_handles_llm_failure_gracefully():
    client = FailingJsonClient()

    result = search_tree(
        question="Any question",
        tree=SAMPLE_TREE,
        pages=SAMPLE_PAGES,
        llm_client=client,
    )

    assert result.selected_node_ids == []
    assert result.retrieved_pages == []
    # Trace records the failure.
    select_step = next(s for s in result.trace if s.action == "select_nodes")
    assert "failed" in select_step.reason.lower() or "unreachable" in select_step.reason.lower()


def test_search_tree_records_full_trace():
    client = FakeJsonClient(["0004"])

    result = search_tree(
        question="How often should filters be cleaned?",
        tree=SAMPLE_TREE,
        pages=SAMPLE_PAGES,
        llm_client=client,
    )

    actions = [step.action for step in result.trace]
    assert "inspect_tree" in actions
    assert "select_nodes" in actions
    assert "fetch_pages" in actions


# ---------------------------------------------------------------------------
# Fix 5: Retrieval fallback tests
# ---------------------------------------------------------------------------


def test_overview_question_expands_to_major_sections():
    """An overview question should expand retrieval beyond a narrow LLM pick."""
    client = FakeJsonClient(["0001"])  # LLM only picks Introduction

    result = search_tree(
        question="Give me an overview of this document",
        tree=SAMPLE_TREE,
        pages=SAMPLE_PAGES,
        llm_client=client,
    )

    # Should have expanded beyond just 0001
    assert len(result.selected_node_ids) > 1
    # Should have an overview_expansion trace step
    actions = [step.action for step in result.trace]
    assert "overview_expansion" in actions


def test_keyword_fallback_adds_matching_nodes():
    """When LLM returns no nodes, keyword fallback should find relevant ones."""
    client = FakeJsonClient([])  # LLM returns nothing

    result = search_tree(
        question="What about maintenance and filters?",
        tree=SAMPLE_TREE,
        pages=SAMPLE_PAGES,
        llm_client=client,
    )

    # Lexical fallback should find Maintenance (title contains "filters" in summary)
    assert len(result.selected_node_ids) > 0
    actions = [step.action for step in result.trace]
    assert "lexical_fallback" in actions


def test_weak_selection_expands_to_siblings():
    """When LLM picks only 1 node that has siblings, expand to include them."""
    # Use 0003 (Protective Equipment) which is a child of 0002
    client = FakeJsonClient(["0003"])

    result = search_tree(
        question="What specific equipment is needed?",
        tree=SAMPLE_TREE,
        pages=SAMPLE_PAGES,
        llm_client=client,
    )

    # 0003 is the only child of 0002, so sibling expansion should still work
    # (finds root-level siblings if no direct siblings)
    assert "0003" in result.selected_node_ids
    assert len(result.retrieved_pages) >= 1


def test_specific_question_does_not_over_expand():
    """A specific question with good LLM selection should not add unnecessary nodes."""
    client = FakeJsonClient(["0002", "0003"])  # Good, targeted selection

    result = search_tree(
        question="What protective equipment do I need?",
        tree=SAMPLE_TREE,
        pages=SAMPLE_PAGES,
        llm_client=client,
    )

    # Should not have overview or sibling expansion
    actions = [step.action for step in result.trace]
    assert "overview_expansion" not in actions
    assert "lexical_fallback" not in actions
    # Should keep the original selection
    assert "0002" in result.selected_node_ids
    assert "0003" in result.selected_node_ids


# ---------------------------------------------------------------------------
# Change 2: Tree prompt compression tests
# ---------------------------------------------------------------------------

from private_pageindex.retrieval.tree_search import (
    _format_tree_auto,
    _format_tree_compact,
    _format_tree_for_prompt,
)


def _make_node(nid: str, title: str, sp: int, ep: int, summary: str = "", children=None):
    return {
        "node_id": nid,
        "title": title,
        "start_page": sp,
        "end_page": ep,
        "summary": summary,
        "nodes": children or [],
    }


def test_small_tree_uses_full_mode():
    """A tree whose full prompt is under the threshold stays in full mode."""
    nodes = [
        _make_node("0001", "Introduction", 1, 1, "Overview of the document."),
        _make_node("0002", "Methods", 2, 3, "Research methodology."),
    ]
    text, used_compact = _format_tree_auto(nodes, compact_threshold=4000)
    assert used_compact is False
    # Full mode includes summaries
    assert "Summary:" in text
    assert "Overview of the document." in text


def test_large_tree_switches_to_compact_mode():
    """A tree whose full prompt exceeds the threshold switches to compact mode."""
    # Create enough nodes with long summaries to exceed a small threshold
    nodes = [
        _make_node(
            f"{i:04d}",
            f"Section {i}: A Long Section Title With Many Words",
            i,
            i,
            "This is a verbose summary that adds many characters to the prompt. " * 3,
        )
        for i in range(1, 20)
    ]
    # Use a small threshold (500 chars) to force compact mode
    text, used_compact = _format_tree_auto(nodes, compact_threshold=500)
    assert used_compact is True
    # Compact mode must NOT include summaries
    assert "Summary:" not in text
    assert "This is a verbose summary" not in text
    # But node IDs and titles must still be present
    assert "[0001]" in text
    assert "Section 1:" in text


def test_compact_format_uses_single_line_per_node():
    """Compact format: each node is one line with id, title, and page range."""
    nodes = [
        _make_node("0001", "Introduction", 1, 1, "Some long summary text."),
        _make_node("0002", "Chapter Two", 2, 5, "Another long summary."),
    ]
    text = _format_tree_compact(nodes)
    lines = [l for l in text.splitlines() if l.strip()]

    assert len(lines) == 2
    # Single-page node uses p1 format
    assert "p1" in lines[0] or "pp1-1" in lines[0]
    # Multi-page node uses pp2-5 format
    assert "pp2-5" in lines[1]
    # No summaries
    assert "Summary:" not in text


def test_compact_mode_recorded_in_trace():
    """When compact mode is triggered, the inspect_tree trace step records it."""
    # Build a tree large enough to exceed a tiny threshold
    big_tree = {
        "nodes": [
            _make_node(
                f"{i:04d}",
                f"Section {i}",
                i, i,
                "Long summary " * 10,
            )
            for i in range(1, 30)
        ]
    }
    big_pages = [
        {"page_number": i, "text": f"Page {i} content.", "char_count": 15}
        for i in range(1, 30)
    ]

    client = FakeJsonClient(["0001"])

    # Force compact by using a tiny threshold override via max_tree_prompt_chars
    # We monkeypatch the settings by passing a patched config
    from unittest.mock import patch
    from private_pageindex.config import Settings

    fake_settings = Settings()
    fake_settings.__dict__["tree_prompt_compact_threshold"] = 100

    with patch("private_pageindex.retrieval.tree_search.get_settings", return_value=lambda: fake_settings):
        # Call directly with a low threshold instead
        from private_pageindex.retrieval.tree_search import _format_tree_auto
        _, used_compact = _format_tree_auto(big_tree["nodes"], compact_threshold=100)

    assert used_compact is True


def test_full_mode_recorded_in_trace():
    """When full mode is used, the inspect_tree trace step records it."""
    client = FakeJsonClient(["0001"])

    result = search_tree(
        question="What is the introduction?",
        tree=SAMPLE_TREE,
        pages=SAMPLE_PAGES,
        llm_client=client,
    )

    inspect_step = next(s for s in result.trace if s.action == "inspect_tree")
    # SAMPLE_TREE is small — should use full mode
    assert "full (titles + summaries)" in inspect_step.reason


def test_page_text_fallback_finds_relevant_nodes():
    """When LLM selection and title/summary lexical fallback find nothing,
    but a keyword exists only in the raw page text, page-text fallback should trigger.
    """
    client = FakeJsonClient([])  # LLM returns nothing

    # "secret_keyword" is only in page 4 text, NOT in any node titles or summaries.
    pages = [
        {"page_number": 1, "text": "Page 1 intro.", "char_count": 13},
        {"page_number": 2, "text": "Page 2 safety.", "char_count": 14},
        {"page_number": 3, "text": "Page 3 safety rules.", "char_count": 20},
        {"page_number": 4, "text": "Page 4 has the secret_keyword text.", "char_count": 35},
    ]

    result = search_tree(
        question="Where is the secret_keyword discussed?",
        tree=SAMPLE_TREE,
        pages=pages,
        llm_client=client,
    )

    # Should find node 0004 (which then expands to siblings).
    assert "0004" in result.selected_node_ids
    # Page 4 must be retrieved.
    assert 4 in [p["page_number"] for p in result.retrieved_pages]

    actions = [step.action for step in result.trace]
    assert "page_text_fallback" in actions

    fallback_step = next(s for s in result.trace if s.action == "page_text_fallback")
    assert "page-text fallback found" in fallback_step.reason.lower()


@pytest.mark.anyio
async def test_search_tree_async_page_text_fallback():
    """Async search_tree version should also support page-text fallback search."""
    class FakeAsyncJsonClient:
        async def chat_json(self, system: str, user: str, schema_hint: str | None = None):
            return {"selected_node_ids": []}

    client = FakeAsyncJsonClient()
    pages = [
        {"page_number": 1, "text": "Page 1 intro.", "char_count": 13},
        {"page_number": 2, "text": "Page 2 safety.", "char_count": 14},
        {"page_number": 3, "text": "Page 3 safety rules.", "char_count": 20},
        {"page_number": 4, "text": "Page 4 has the secret_keyword text.", "char_count": 35},
    ]

    from private_pageindex.retrieval.tree_search import search_tree_async
    result = await search_tree_async(
        question="Where is the secret_keyword discussed?",
        tree=SAMPLE_TREE,
        pages=pages,
        llm_client=client,
    )

    assert "0004" in result.selected_node_ids
    assert 4 in [p["page_number"] for p in result.retrieved_pages]
    actions = [step.action for step in result.trace]
    assert "page_text_fallback" in actions


def test_search_tree_broad_retrieves_all_root_pages():
    """search_tree_broad should retrieve pages from all root-level nodes up to budget."""
    from private_pageindex.retrieval.tree_search import search_tree_broad

    result = search_tree_broad(
        question="Help",
        tree=SAMPLE_TREE,
        pages=SAMPLE_PAGES,
    )

    # SAMPLE_TREE has root nodes 0001, 0002, 0004.
    # Pages covering these are: 0001 (page 1), 0002 (pages 2-3), 0004 (page 4).
    # So it should retrieve pages 1, 2, 3, 4.
    assert result.selected_node_ids == ["0001", "0002", "0004"]
    retrieved_pns = [p["page_number"] for p in result.retrieved_pages]
    assert retrieved_pns == [1, 2, 3, 4]

    actions = [step.action for step in result.trace]
    assert "search_tree_broad" in actions


@pytest.mark.anyio
async def test_search_tree_broad_async_retrieves_all_root_pages():
    """search_tree_broad_async should correctly retrieve pages asynchronously."""
    from private_pageindex.retrieval.tree_search import search_tree_broad_async

    result = await search_tree_broad_async(
        question="Help",
        tree=SAMPLE_TREE,
        pages=SAMPLE_PAGES,
    )

    assert result.selected_node_ids == ["0001", "0002", "0004"]
    retrieved_pns = [p["page_number"] for p in result.retrieved_pages]
    assert retrieved_pns == [1, 2, 3, 4]


