"""Tree builder: orchestrate heading detection → tree construction → post-processing.

This module is the public entry-point for building a document tree.
Heavy logic lives in sub-modules:

- ``heading_detection`` — regex heading detection, blank-page handling
- ``tree_postprocessing`` — fragment merging, cover noise, duplicate titles
- ``tree_validation`` — ``TreeReport`` + ``validate_tree()``

All public names are re-exported here so existing imports like
``from private_pageindex.indexing.tree_builder import build_tree, validate_tree``
continue to work unchanged.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Protocol, Callable

from private_pageindex.config import get_settings
from private_pageindex.indexing.heading_detection import (
    HeadingCandidate,
    detect_headings,
    detect_repeated_headers,
    normalize_line,
)
from private_pageindex.indexing.tree_postprocessing import (
    flag_duplicate_titles,
    merge_title_fragments,
    suppress_cover_noise,
)
from private_pageindex.indexing.tree_validation import (
    TreeReport,
    validate_tree,
)
from private_pageindex.indexing.entity_extraction import extract_key_entities
from private_pageindex.ingest.pdf_text import ExtractedPage

# Re-export for backward compatibility
__all__ = [
    "JsonChatClient",
    "TreeNode",
    "TreeReport",
    "HeadingCandidate",
    "build_tree",
    "flatten_tree",
    "validate_tree",
]


class JsonChatClient(Protocol):
    def chat_json(
        self,
        system: str,
        user: str,
        schema_hint: str | None = None,
    ) -> dict:
        ...


@dataclass
class TreeNode:
    node_id: str
    title: str
    start_page: int
    end_page: int
    summary: str
    nodes: list["TreeNode"] = field(default_factory=list)
    flags: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "title": self.title,
            "start_page": self.start_page,
            "end_page": self.end_page,
            "summary": self.summary,
            "nodes": [node.to_dict() for node in self.nodes],
            "flags": dict(self.flags),
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_tree(
    pages: list[ExtractedPage],
    *,
    max_pages_per_node: int | None = None,
    llm_client: JsonChatClient | None = None,
    progress_callback: Callable[[str, int], None] | None = None,
) -> list[TreeNode]:
    if not pages:
        return []

    settings = get_settings()
    max_pages = max_pages_per_node or settings.tree_max_pages_per_node

    if progress_callback:
        progress_callback("detecting headings", 45)
    headings = detect_headings(pages)
    if headings:
        tree = _tree_from_headings(headings, pages)
    else:
        if progress_callback:
            progress_callback("checking repeated headers", 46)
        repeated = detect_repeated_headers(pages)
        if repeated:
            tree = _tree_from_headings(repeated, pages)
        else:
            if progress_callback:
                progress_callback("fallback page ranges", 46)
            tree = _fallback_page_ranges(pages, max_pages=max_pages)

    # Ensure pages before the first heading are covered
    if tree and pages:
        first_page = min(p.page_number for p in pages)
        first_node_page = tree[0].start_page
        if first_node_page > first_page:
            front_matter = TreeNode(
                node_id="",
                title="Front Matter",
                start_page=first_page,
                end_page=first_node_page - 1,
                summary="",
                flags={"is_front_matter": True},
            )
            tree.insert(0, front_matter)

    # Post-processing
    if progress_callback:
        progress_callback("normalizing structures", 47)
    page_map = {page.page_number: page for page in pages}
    tree = merge_title_fragments(tree, page_map)
    tree = suppress_cover_noise(tree, page_map)
    tree = flag_duplicate_titles(tree)

    _write_node_ids(tree)
    
    if progress_callback:
        progress_callback("generating summaries", 48)
    _fill_summaries(tree, pages)

    if llm_client is not None:
        _enhance_with_llm(tree, pages, llm_client, progress_callback)
    return tree


def flatten_tree(nodes: list[TreeNode]) -> list[TreeNode]:
    flattened: list[TreeNode] = []
    for node in nodes:
        flattened.append(node)
        flattened.extend(flatten_tree(node.nodes))
    return flattened


# ---------------------------------------------------------------------------
# Tree construction from headings
# ---------------------------------------------------------------------------


def _tree_from_headings(
    headings: list[HeadingCandidate],
    pages: list[ExtractedPage],
) -> list[TreeNode]:
    max_page = max(page.page_number for page in pages)
    root_nodes: list[TreeNode] = []
    stack: list[TreeNode] = []

    for index, heading in enumerate(headings):
        next_heading = headings[index + 1] if index + 1 < len(headings) else None
        end_page = (next_heading.page_number - 1) if next_heading else max_page
        end_page = max(heading.page_number, end_page)
        node_flags = dict(heading.flags)
        node_flags["source"] = heading.source
        node = TreeNode(
            node_id="",
            title=heading.title,
            start_page=heading.page_number,
            end_page=end_page,
            summary="",
            flags=node_flags,
        )

        while len(stack) >= heading.level:
            stack.pop()
        if stack:
            parent = stack[-1]
            parent.nodes.append(node)
            parent.end_page = max(parent.end_page, node.end_page)
        else:
            root_nodes.append(node)
        stack.append(node)

    return root_nodes


# ---------------------------------------------------------------------------
# Fallback: page-range nodes
# ---------------------------------------------------------------------------


def _fallback_page_ranges(
    pages: list[ExtractedPage],
    *,
    max_pages: int,
) -> list[TreeNode]:
    if max_pages < 1:
        raise ValueError("max_pages_per_node must be at least 1")

    sorted_pages = sorted(pages, key=lambda page: page.page_number)
    total = len(sorted_pages)

    num_groups = math.ceil(total / max_pages)
    if num_groups > 5:
        return _two_level_fallback(sorted_pages, max_pages)

    nodes: list[TreeNode] = []
    for start in range(0, total, max_pages):
        group = sorted_pages[start : start + max_pages]
        start_page = group[0].page_number
        end_page = group[-1].page_number
        title = f"Page {start_page}" if start_page == end_page else f"Pages {start_page}-{end_page}"
        nodes.append(
            TreeNode(
                node_id="",
                title=title,
                start_page=start_page,
                end_page=end_page,
                summary="",
            )
        )
    return nodes


def _two_level_fallback(
    sorted_pages: list[ExtractedPage],
    max_pages: int,
) -> list[TreeNode]:
    """Create parent groups with individual page children for large docs."""
    nodes: list[TreeNode] = []
    for start in range(0, len(sorted_pages), max_pages):
        group = sorted_pages[start : start + max_pages]
        start_page = group[0].page_number
        end_page = group[-1].page_number
        part_num = (start // max_pages) + 1
        parent_title = (
            f"Part {part_num}: Page {start_page}"
            if start_page == end_page
            else f"Part {part_num}: Pages {start_page}-{end_page}"
        )

        children: list[TreeNode] = []
        for p in group:
            children.append(
                TreeNode(
                    node_id="",
                    title=f"Page {p.page_number}",
                    start_page=p.page_number,
                    end_page=p.page_number,
                    summary="",
                )
            )

        nodes.append(
            TreeNode(
                node_id="",
                title=parent_title,
                start_page=start_page,
                end_page=end_page,
                summary="",
                nodes=children,
            )
        )
    return nodes


# ---------------------------------------------------------------------------
# Node ID assignment and summaries
# ---------------------------------------------------------------------------


def _write_node_ids(nodes: list[TreeNode]) -> None:
    for index, node in enumerate(flatten_tree(nodes), start=1):
        node.node_id = str(index).zfill(4)


def _fill_summaries(nodes: list[TreeNode], pages: list[ExtractedPage]) -> None:
    page_text = {page.page_number: page.text for page in pages}
    for node in flatten_tree(nodes):
        if not node.summary:
            text = _node_text(node, page_text)
            node.summary = _deterministic_summary(text, fallback=node.title)


def _enhance_with_llm(
    nodes: list[TreeNode],
    pages: list[ExtractedPage],
    llm_client: JsonChatClient,
    progress_callback: Callable[[str, int], None] | None = None,
) -> None:
    page_text = {page.page_number: page.text for page in pages}
    schema_hint = '{"title": "Clean section title", "summary": "One sentence summary"}'
    system = (
        "You clean section titles and write short factual summaries for a local "
        "PageIndex tree. Use only the provided local page text."
    )
    flat_nodes = flatten_tree(nodes)
    total_nodes = len(flat_nodes)
    for index, node in enumerate(flat_nodes, 1):
        if progress_callback:
            # We want to display progress in the range 49% to 68%
            percent = 49 + int(((index - 1) / max(1, total_nodes)) * 20)
            progress_callback(
                f"enhancing node {index} of {total_nodes}",
                percent,
            )
        text = _node_text(node, page_text)[:4000]
        user = (
            f"Node title: {node.title}\n"
            f"Page range: {node.start_page}-{node.end_page}\n"
            f"Page text:\n{text}"
        )
        try:
            result = llm_client.chat_json(system, user, schema_hint=schema_hint)
        except Exception:
            continue
        summary = result.get("summary")
        if isinstance(summary, str) and summary.strip():
            node.summary = summary.strip()


def _node_text(node: TreeNode, page_text: dict[int, str]) -> str:
    return "\n".join(
        page_text.get(page_number, "")
        for page_number in range(node.start_page, node.end_page + 1)
    ).strip()


def _deterministic_summary(text: str, *, fallback: str) -> str:
    clean = " ".join(text.split())
    if not clean:
        return f"No selectable text found for {fallback}."
    
    base = clean[:200]
    entities = extract_key_entities(text)
    if entities:
        base += " | Key: " + ", ".join(entities)
        
    return base[:300]
