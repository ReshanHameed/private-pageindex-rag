"""Tree-search retrieval: select relevant nodes from the document tree."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from private_pageindex.config import get_settings


class TreeSearchError(RuntimeError):
    """Raised when tree search fails."""


@dataclass
class TraceStep:
    """One step in the retrieval trace."""

    action: str
    node_id: str | None
    pages: str | None
    reason: str
    node_ids: list[str] | None = None


@dataclass
class RetrievalResult:
    """Result of a tree-search retrieval."""

    selected_node_ids: list[str]
    retrieved_pages: list[dict[str, Any]]
    trace: list[TraceStep] = field(default_factory=list)


def search_tree(
    question: str,
    tree: dict[str, Any],
    pages: list[dict[str, Any]],
    llm_client: Any,
    *,
    max_tree_prompt_chars: int | None = None,
) -> RetrievalResult:
    """Search the document tree to find pages relevant to *question*.

    Steps:
        1. Format the tree structure for the LLM prompt.
        2. Ask the LLM to select relevant ``node_id`` values (JSON mode).
        3. Validate selected IDs against the actual tree.
        4. Collect page text for selected nodes.
        5. Return the result with a full trace.
    """
    settings = get_settings()
    budget = max_tree_prompt_chars or settings.max_tree_prompt_chars

    trace: list[TraceStep] = []

    # --- Step 1: Format tree for the prompt ----------------------------------
    tree_nodes = tree.get("nodes", [])
    compact_threshold = settings.tree_prompt_compact_threshold
    tree_text, used_compact = _format_tree_auto(tree_nodes, compact_threshold)
    if len(tree_text) > budget:
        tree_text = tree_text[:budget]

    mode_label = "compact (titles only)" if used_compact else "full (titles + summaries)"
    trace.append(TraceStep(
        action="inspect_tree",
        node_id=None,
        pages=None,
        reason=f"Formatted tree with {len(tree_nodes)} top-level nodes "
               f"({len(tree_text)} chars, {mode_label}).",
    ))

    # --- Step 2: Ask LLM to select relevant nodes ---------------------------
    all_node_ids = _collect_node_ids(tree_nodes)

    system_prompt = (
        "You are a local document retrieval assistant. Given a document tree "
        "structure and a user question, select the node_ids of the sections "
        "most likely to contain the answer. Return only relevant nodes. "
        "If no node is relevant, return an empty list."
    )
    user_prompt = (
        f"Document tree:\n{tree_text}\n\n"
        f"Question: {question}\n\n"
        f"Available node_ids: {json.dumps(all_node_ids)}"
    )
    schema_hint = '{"selected_node_ids": ["0001", "0002"]}'

    try:
        result = llm_client.chat_json(system_prompt, user_prompt, schema_hint=schema_hint)
    except Exception as exc:
        trace.append(TraceStep(
            action="select_nodes",
            node_id=None,
            pages=None,
            reason=f"LLM call failed: {exc}",
        ))
        return RetrievalResult(
            selected_node_ids=[],
            retrieved_pages=[],
            trace=trace,
        )

    raw_ids = result.get("selected_node_ids", [])
    if not isinstance(raw_ids, list):
        raw_ids = []

    # --- Step 3: Validate selected IDs against actual tree -------------------
    valid_ids = [nid for nid in raw_ids if isinstance(nid, str) and nid in all_node_ids]
    invalid_ids = [nid for nid in raw_ids if nid not in valid_ids]

    reason_parts = [f"LLM selected {len(raw_ids)} node(s)."]
    if invalid_ids:
        reason_parts.append(f"Filtered out {len(invalid_ids)} invalid ID(s): {invalid_ids}.")
    reason_parts.append(f"Valid: {valid_ids}.")

    trace.append(TraceStep(
        action="select_nodes",
        node_id=None,
        pages=None,
        reason=" ".join(reason_parts),
        node_ids=valid_ids,
    ))

    if not valid_ids:
        # Weak selection fallback: try lexical matching
        valid_ids = _lexical_fallback(question, tree_nodes, pages)
        if valid_ids:
            trace.append(TraceStep(
                action="lexical_fallback",
                node_id=None,
                pages=None,
                reason=f"LLM returned no nodes. Lexical fallback found: {valid_ids}.",
            ))
        else:
            # Last-resort fallback: try raw page text matching
            valid_ids = _page_text_fallback(question, pages, tree_nodes)
            if valid_ids:
                trace.append(TraceStep(
                    action="page_text_fallback",
                    node_id=None,
                    pages=None,
                    reason=f"LLM and lexical fallback returned no nodes. Page-text fallback found: {valid_ids}.",
                ))
            else:
                return RetrievalResult(
                    selected_node_ids=[],
                    retrieved_pages=[],
                    trace=trace,
                )

    # --- Step 3b: Expand selection based on question type --------------------
    q_type = _classify_question(question)
    if q_type == "overview":
        expanded = _expand_for_overview(valid_ids, tree_nodes)
        if expanded != valid_ids:
            trace.append(TraceStep(
                action="overview_expansion",
                node_id=None,
                pages=None,
                reason=f"Overview question detected. Expanded from {len(valid_ids)} to {len(expanded)} nodes.",
            ))
            valid_ids = expanded
    elif len(valid_ids) == 1:
        expanded = _expand_weak_selection(valid_ids, tree_nodes)
        if expanded != valid_ids:
            trace.append(TraceStep(
                action="sibling_expansion",
                node_id=None,
                pages=None,
                reason=f"Weak selection (1 node). Expanded to {len(expanded)} nodes via siblings.",
            ))
            valid_ids = expanded

    # --- Step 4: Collect pages for selected nodes ----------------------------
    node_map = _build_node_map(tree_nodes)
    page_ranges: set[int] = set()
    for nid in valid_ids:
        node = node_map.get(nid)
        if node:
            start = node.get("start_page", 0)
            end = node.get("end_page", start)
            page_ranges.update(range(start, end + 1))

    page_index = {p["page_number"]: p for p in pages}
    retrieved = [
        page_index[pn]
        for pn in sorted(page_ranges)
        if pn in page_index
    ]

    for nid in valid_ids:
        node = node_map.get(nid, {})
        trace.append(TraceStep(
            action="fetch_pages",
            node_id=nid,
            pages=f"{node.get('start_page', '?')}-{node.get('end_page', '?')}",
            reason=f"Fetched pages for node '{node.get('title', nid)}'.",
        ))

    return RetrievalResult(
        selected_node_ids=valid_ids,
        retrieved_pages=retrieved,
        trace=trace,
    )


async def search_tree_async(
    question: str,
    tree: dict[str, Any],
    pages: list[dict[str, Any]],
    llm_client: Any,
    *,
    max_tree_prompt_chars: int | None = None,
) -> RetrievalResult:
    """Async version of :func:`search_tree`.

    Identical logic but ``await``-s the LLM call so it can run inside
    an async FastAPI handler without blocking the event loop.  All
    non-LLM helpers are shared with the sync version.
    """
    settings = get_settings()
    budget = max_tree_prompt_chars or settings.max_tree_prompt_chars

    trace: list[TraceStep] = []

    tree_nodes = tree.get("nodes", [])
    compact_threshold = settings.tree_prompt_compact_threshold
    tree_text, used_compact = _format_tree_auto(tree_nodes, compact_threshold)
    if len(tree_text) > budget:
        tree_text = tree_text[:budget]

    mode_label = "compact (titles only)" if used_compact else "full (titles + summaries)"
    trace.append(TraceStep(
        action="inspect_tree",
        node_id=None,
        pages=None,
        reason=f"Formatted tree with {len(tree_nodes)} top-level nodes "
               f"({len(tree_text)} chars, {mode_label}).",
    ))

    all_node_ids = _collect_node_ids(tree_nodes)

    system_prompt = (
        "You are a local document retrieval assistant. Given a document tree "
        "structure and a user question, select the node_ids of the sections "
        "most likely to contain the answer. Return only relevant nodes. "
        "If no node is relevant, return an empty list."
    )
    user_prompt = (
        f"Document tree:\n{tree_text}\n\n"
        f"Question: {question}\n\n"
        f"Available node_ids: {json.dumps(all_node_ids)}"
    )
    schema_hint = '{"selected_node_ids": ["0001", "0002"]}'

    try:
        result = await llm_client.chat_json(system_prompt, user_prompt, schema_hint=schema_hint)
    except Exception as exc:
        trace.append(TraceStep(
            action="select_nodes",
            node_id=None,
            pages=None,
            reason=f"LLM call failed: {exc}",
        ))
        return RetrievalResult(
            selected_node_ids=[],
            retrieved_pages=[],
            trace=trace,
        )

    raw_ids = result.get("selected_node_ids", [])
    if not isinstance(raw_ids, list):
        raw_ids = []

    valid_ids = [nid for nid in raw_ids if isinstance(nid, str) and nid in all_node_ids]
    invalid_ids = [nid for nid in raw_ids if nid not in valid_ids]

    reason_parts = [f"LLM selected {len(raw_ids)} node(s)."]
    if invalid_ids:
        reason_parts.append(f"Filtered out {len(invalid_ids)} invalid ID(s): {invalid_ids}.")
    reason_parts.append(f"Valid: {valid_ids}.")

    trace.append(TraceStep(
        action="select_nodes",
        node_id=None,
        pages=None,
        reason=" ".join(reason_parts),
        node_ids=valid_ids,
    ))

    if not valid_ids:
        valid_ids = _lexical_fallback(question, tree_nodes, pages)
        if valid_ids:
            trace.append(TraceStep(
                action="lexical_fallback",
                node_id=None,
                pages=None,
                reason=f"LLM returned no nodes. Lexical fallback found: {valid_ids}.",
            ))
        else:
            valid_ids = _page_text_fallback(question, pages, tree_nodes)
            if valid_ids:
                trace.append(TraceStep(
                    action="page_text_fallback",
                    node_id=None,
                    pages=None,
                    reason=f"LLM and lexical fallback returned no nodes. Page-text fallback found: {valid_ids}.",
                ))
            else:
                return RetrievalResult(
                    selected_node_ids=[],
                    retrieved_pages=[],
                    trace=trace,
                )

    q_type = _classify_question(question)
    if q_type == "overview":
        expanded = _expand_for_overview(valid_ids, tree_nodes)
        if expanded != valid_ids:
            trace.append(TraceStep(
                action="overview_expansion",
                node_id=None,
                pages=None,
                reason=f"Overview question detected. Expanded from {len(valid_ids)} to {len(expanded)} nodes.",
            ))
            valid_ids = expanded
    elif len(valid_ids) == 1:
        expanded = _expand_weak_selection(valid_ids, tree_nodes)
        if expanded != valid_ids:
            trace.append(TraceStep(
                action="sibling_expansion",
                node_id=None,
                pages=None,
                reason=f"Weak selection (1 node). Expanded to {len(expanded)} nodes via siblings.",
            ))
            valid_ids = expanded

    node_map = _build_node_map(tree_nodes)
    page_ranges: set[int] = set()
    for nid in valid_ids:
        node = node_map.get(nid)
        if node:
            start = node.get("start_page", 0)
            end = node.get("end_page", start)
            page_ranges.update(range(start, end + 1))

    page_index = {p["page_number"]: p for p in pages}
    retrieved = [
        page_index[pn]
        for pn in sorted(page_ranges)
        if pn in page_index
    ]

    for nid in valid_ids:
        node = node_map.get(nid, {})
        trace.append(TraceStep(
            action="fetch_pages",
            node_id=nid,
            pages=f"{node.get('start_page', '?')}-{node.get('end_page', '?')}",
            reason=f"Fetched pages for node '{node.get('title', nid)}'.",
        ))

    return RetrievalResult(
        selected_node_ids=valid_ids,
        retrieved_pages=retrieved,
        trace=trace,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _format_tree_for_prompt(
    nodes: list[dict[str, Any]],
    indent: int = 0,
) -> str:
    """Recursively format tree nodes with titles + summaries (full mode)."""
    lines: list[str] = []
    prefix = "  " * indent
    for node in nodes:
        nid = node.get("node_id", "?")
        title = node.get("title", "Untitled")
        sp = node.get("start_page", "?")
        ep = node.get("end_page", "?")
        summary = node.get("summary", "")
        lines.append(f"{prefix}[{nid}] {title} (pages {sp}-{ep})")
        if summary:
            lines.append(f"{prefix}  Summary: {summary}")
        children = node.get("nodes", [])
        if children:
            lines.append(_format_tree_for_prompt(children, indent + 1))
    return "\n".join(lines)


def _format_tree_compact(
    nodes: list[dict[str, Any]],
    indent: int = 0,
) -> str:
    """Recursively format tree nodes in compact mode: one line per node.

    Omits summaries entirely so the LLM sees only the structural
    outline.  Used automatically when the full prompt exceeds
    ``tree_prompt_compact_threshold``.
    """
    lines: list[str] = []
    prefix = "  " * indent
    for node in nodes:
        nid = node.get("node_id", "?")
        title = node.get("title", "Untitled")
        sp = node.get("start_page", "?")
        ep = node.get("end_page", "?")
        page_str = f"p{sp}" if sp == ep else f"pp{sp}-{ep}"
        lines.append(f"{prefix}[{nid}] {title} ({page_str})")
        children = node.get("nodes", [])
        if children:
            lines.append(_format_tree_compact(children, indent + 1))
    return "\n".join(lines)


def _format_tree_auto(
    nodes: list[dict[str, Any]],
    compact_threshold: int,
) -> tuple[str, bool]:
    """Return ``(prompt_text, used_compact)``.

    Tries full mode first.  If the result exceeds *compact_threshold*
    characters, falls back to compact mode and returns ``True`` as the
    second element so callers can record which mode was used.
    """
    full_text = _format_tree_for_prompt(nodes)
    if len(full_text) <= compact_threshold:
        return full_text, False
    return _format_tree_compact(nodes), True


def _collect_node_ids(nodes: list[dict[str, Any]]) -> list[str]:
    """Collect all node_id values from a nested tree."""
    ids: list[str] = []
    for node in nodes:
        nid = node.get("node_id")
        if nid:
            ids.append(nid)
        ids.extend(_collect_node_ids(node.get("nodes", [])))
    return ids


def _build_node_map(nodes: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Build a flat map from node_id → node dict."""
    result: dict[str, dict[str, Any]] = {}
    for node in nodes:
        nid = node.get("node_id")
        if nid:
            result[nid] = node
        result.update(_build_node_map(node.get("nodes", [])))
    return result


# ---------------------------------------------------------------------------
# Retrieval fallbacks
# ---------------------------------------------------------------------------

_OVERVIEW_KEYWORDS = {
    "summarize", "summary", "overview", "about", "main", "topics",
    "describe", "introduction", "purpose", "scope", "outline",
    "general", "overall", "brief", "highlights",
}
_STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can",
    "of", "in", "to", "for", "with", "on", "at", "from", "by",
    "and", "or", "not", "but", "if", "then", "than", "so",
    "what", "which", "who", "whom", "this", "that", "these",
    "those", "it", "its", "my", "your", "his", "her", "our",
    "their", "me", "him", "us", "them", "i", "you", "he", "she",
    "we", "they", "how", "when", "where", "why",
}
_MAX_EXPANDED_NODES = 8


def _classify_question(question: str) -> str:
    """Classify a question as 'overview', 'keyword', or 'specific'."""
    words = set(question.lower().split())
    if words & _OVERVIEW_KEYWORDS:
        return "overview"
    return "specific"


def _expand_for_overview(
    valid_ids: list[str],
    tree_nodes: list[dict[str, Any]],
) -> list[str]:
    """For overview questions, include representative root-level sections."""
    selected = set(valid_ids)
    for node in tree_nodes:
        nid = node.get("node_id")
        if nid and nid not in selected:
            selected.add(nid)
        if len(selected) >= _MAX_EXPANDED_NODES:
            break
    return list(selected)


def _lexical_fallback(
    question: str,
    tree_nodes: list[dict[str, Any]],
    pages: list[dict[str, Any]],
) -> list[str]:
    """Score nodes by keyword overlap with the question."""
    keywords = {
        w.lower().strip(".,;:!?'\"")
        for w in question.split()
    } - _STOP_WORDS
    if not keywords:
        return []

    node_map = _build_node_map(tree_nodes)
    scores: list[tuple[str, float]] = []
    for nid, node in node_map.items():
        title = node.get("title", "").lower()
        summary = node.get("summary", "").lower()
        score = 0.0
        for kw in keywords:
            if kw in title:
                score += 3.0
            if kw in summary:
                score += 1.0
        if score > 0:
            scores.append((nid, score))

    scores.sort(key=lambda x: x[1], reverse=True)
    return [nid for nid, _ in scores[:2]]


def _page_text_fallback(
    question: str,
    pages: list[dict[str, Any]],
    tree_nodes: list[dict[str, Any]],
) -> list[str]:
    """Last-resort fallback: search raw page text for question keywords."""
    keywords = {
        w.lower().strip(".,;:!?'\"")
        for w in question.split()
    } - _STOP_WORDS
    if not keywords:
        return []

    scored_pages: list[tuple[int, float]] = []
    for page in pages:
        text_lower = page.get("text", "").lower()
        score = 0.0
        for kw in keywords:
            if kw in text_lower:
                score += 3.0
        if score > 0:
            scored_pages.append((page["page_number"], score))

    if not scored_pages:
        return []

    # Sort pages by score descending, page_number ascending
    scored_pages.sort(key=lambda x: (-x[1], x[0]))

    # Map top pages (up to 2) to their most specific nodes
    node_map = _build_node_map(tree_nodes)
    selected_node_ids: list[str] = []
    for page_num, _ in scored_pages[:2]:
        best_node_id = None
        best_span = float("inf")
        for nid, node in node_map.items():
            sp = node.get("start_page", 0)
            ep = node.get("end_page", sp)
            if sp <= page_num <= ep:
                span = ep - sp
                if span < best_span:
                    best_span = span
                    best_node_id = nid
        if best_node_id and best_node_id not in selected_node_ids:
            selected_node_ids.append(best_node_id)

    return selected_node_ids


def _expand_weak_selection(
    valid_ids: list[str],
    tree_nodes: list[dict[str, Any]],
) -> list[str]:
    """If only 1 node is selected, add its sibling nodes."""
    if len(valid_ids) != 1:
        return valid_ids

    target_id = valid_ids[0]
    # Find the parent that contains the target node
    siblings = _find_siblings(target_id, tree_nodes)
    if siblings:
        expanded = set(valid_ids)
        for sib_id in siblings:
            expanded.add(sib_id)
            if len(expanded) >= 4:
                break
        return list(expanded)
    return valid_ids


def _find_siblings(
    target_id: str,
    nodes: list[dict[str, Any]],
) -> list[str]:
    """Find sibling node IDs of the target within the tree."""
    for node in nodes:
        children = node.get("nodes", [])
        child_ids = [c.get("node_id") for c in children if c.get("node_id")]
        if target_id in child_ids:
            return [cid for cid in child_ids if cid != target_id]
        # Recurse into children
        found = _find_siblings(target_id, children)
        if found:
            return found
    # Check if target is at root level
    root_ids = [n.get("node_id") for n in nodes if n.get("node_id")]
    if target_id in root_ids:
        return [rid for rid in root_ids if rid != target_id]
    return []


def search_tree_broad(
    question: str,
    tree: dict[str, Any],
    pages: list[dict[str, Any]],
    llm_client: Any = None,
) -> RetrievalResult:
    """Broad fallback retrieval: retrieve pages from all root-level sections.

    Used when the initial targeted search resulted in a 'no information' answer.
    Does not use the LLM; instead, retrieves pages covering all top-level sections.
    Capped at a reasonable number of pages to fit within LLM context budget.
    """
    settings = get_settings()
    trace: list[TraceStep] = []

    tree_nodes = tree.get("nodes", [])
    if not tree_nodes:
        return RetrievalResult(selected_node_ids=[], retrieved_pages=[], trace=trace)

    # Get all root-level node IDs
    root_node_ids = [n.get("node_id") for n in tree_nodes if n.get("node_id")]

    # Collect page numbers from all root-level nodes
    page_numbers: set[int] = set()
    for node in tree_nodes:
        sp = node.get("start_page", 0)
        ep = node.get("end_page", sp)
        page_numbers.update(range(sp, ep + 1))

    page_index = {p["page_number"]: p for p in pages}
    sorted_pages = sorted(list(page_numbers))

    # Cap to avoid blowing LLM context (e.g. 2x settings.tree_max_pages_per_node)
    cap = settings.tree_max_pages_per_node * 2
    retrieved = [
        page_index[pn]
        for pn in sorted_pages[:cap]
        if pn in page_index
    ]

    trace.append(TraceStep(
        action="search_tree_broad",
        node_id=None,
        pages=f"1-{len(retrieved)}" if retrieved else "none",
        reason=f"Broad fallback retrieval activated. Retrieved {len(retrieved)} page(s) covering top-level nodes.",
    ))

    return RetrievalResult(
        selected_node_ids=root_node_ids,
        retrieved_pages=retrieved,
        trace=trace,
    )


async def search_tree_broad_async(
    question: str,
    tree: dict[str, Any],
    pages: list[dict[str, Any]],
    llm_client: Any = None,
) -> RetrievalResult:
    """Async version of :func:`search_tree_broad`."""
    return search_tree_broad(question, tree, pages, llm_client)

