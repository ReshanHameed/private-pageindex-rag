"""Tree post-processing: normalization, cover-noise suppression, duplicate handling.

These transforms run after the initial tree is built from headings or
fallback page ranges, and before node IDs and summaries are assigned.
"""

from __future__ import annotations

from private_pageindex.indexing.heading_detection import HeadingCandidate  # noqa: F401 — re-export
from private_pageindex.ingest.pdf_text import ExtractedPage

# Avoid circular import — import TreeNode at runtime only for type hints.
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from private_pageindex.indexing.tree_builder import TreeNode


# ---------------------------------------------------------------------------
# Fragment merging
# ---------------------------------------------------------------------------

_FRAGMENT_SOURCES = {"all_caps", "title_case", "known_heading"}


def merge_title_fragments(
    nodes: list["TreeNode"],
    page_map: dict[int, ExtractedPage],
) -> list["TreeNode"]:
    """Merge consecutive same-page root nodes that look like title fragments.

    For example, a title page with lines ``RESEARCH REPORT ON ARTIFICIAL`` and
    ``INTELLIGENCE`` produces two root nodes.  This merges them into a single
    node with the combined title.
    """
    if len(nodes) < 2:
        return nodes

    merged: list["TreeNode"] = []
    i = 0
    while i < len(nodes):
        current = nodes[i]
        if _is_fragment_candidate(current):
            run = [current]
            j = i + 1
            while j < len(nodes) and _can_merge(current, nodes[j]):
                run.append(nodes[j])
                j += 1
            if len(run) > 1:
                merged.append(_combine_fragments(run))
                i = j
                continue
        merged.append(current)
        i += 1
    return merged


def _is_fragment_candidate(node: "TreeNode") -> bool:
    """Return True if the node looks like a title fragment rather than a
    real structural heading."""
    if node.nodes:  # has children → real section
        return False
    if node.flags.get("is_blank"):
        return False
    source = node.flags.get("source", "")
    title_words = len(node.title.split())
    return title_words <= 6 and source in _FRAGMENT_SOURCES


def _can_merge(anchor: "TreeNode", candidate: "TreeNode") -> bool:
    """Return True if *candidate* can be merged into *anchor*'s fragment run."""
    if candidate.start_page != anchor.start_page:
        return False
    return _is_fragment_candidate(candidate)


def _combine_fragments(run: list["TreeNode"]) -> "TreeNode":
    """Combine a list of fragment nodes into one merged node."""
    from private_pageindex.indexing.tree_builder import TreeNode

    combined_title = " ".join(node.title for node in run)
    return TreeNode(
        node_id="",
        title=combined_title,
        start_page=run[0].start_page,
        end_page=run[-1].end_page,
        summary="",
        flags={"merged_title": True},
    )


# ---------------------------------------------------------------------------
# Cover-page noise suppression
# ---------------------------------------------------------------------------

_COVER_PAGE_MAX_CHARS = 500
_COVER_PAGE_MIN_CANDIDATES = 3


def suppress_cover_noise(
    nodes: list["TreeNode"],
    page_map: dict[int, ExtractedPage],
) -> list["TreeNode"]:
    """Collapse noisy cover-page heading candidates into a single node.

    If page 1 has many short heading candidates and very little total text,
    it is almost certainly a title/cover page — not real document sections.
    """
    from private_pageindex.indexing.tree_builder import TreeNode

    if not nodes:
        return nodes

    first_page_num = min(page_map.keys()) if page_map else 1
    first_page = page_map.get(first_page_num)
    if first_page is None:
        return nodes

    cover_nodes: list["TreeNode"] = []
    rest_nodes: list["TreeNode"] = []
    for node in nodes:
        if node.start_page == first_page_num and not rest_nodes:
            cover_nodes.append(node)
        else:
            rest_nodes.append(node)

    if len(cover_nodes) < _COVER_PAGE_MIN_CANDIDATES:
        return nodes
    if first_page.char_count >= _COVER_PAGE_MAX_CHARS:
        return nodes
    if any(node.nodes for node in cover_nodes):
        return nodes

    cover = TreeNode(
        node_id="",
        title="Cover Page",
        start_page=first_page_num,
        end_page=first_page_num,
        summary="",
        flags={"is_cover": True},
    )
    return [cover] + rest_nodes


# ---------------------------------------------------------------------------
# Duplicate heading handling
# ---------------------------------------------------------------------------

_RECURRING_HEADER_THRESHOLD = 3


def flag_duplicate_titles(nodes: list["TreeNode"]) -> list["TreeNode"]:
    """Flag and disambiguate nodes that share the same title.

    - Nodes with identical titles get ``flags["duplicate_title"] = True``.
    - The 2nd+ occurrence gets a page-context suffix.
    - Titles that recur >= 3 times are treated as recurring headers (e.g.
      corporate names on every section boundary); all but the first are
      removed and the first is flagged ``recurring_header``.
    """
    from private_pageindex.indexing.tree_builder import flatten_tree

    all_nodes = flatten_tree(nodes)
    groups: dict[str, list["TreeNode"]] = {}
    for node in all_nodes:
        key = node.title.strip().lower()
        groups.setdefault(key, []).append(node)

    recurring_keys: set[str] = set()
    for key, group in groups.items():
        if len(group) < 2:
            continue
        if len(group) >= _RECURRING_HEADER_THRESHOLD:
            recurring_keys.add(key)
            group[0].flags["recurring_header"] = True
            for dup in group[1:]:
                dup.flags["recurring_header"] = True
                dup.flags["suppress"] = True
        else:
            for idx, node in enumerate(group):
                node.flags["duplicate_title"] = True
                if idx > 0:
                    occurrence = idx + 1
                    node.title = (
                        f"{node.title} (p{node.start_page}, "
                        f"occurrence {occurrence})"
                    )

    if recurring_keys:
        nodes = _remove_suppressed(nodes)

    return nodes


def _remove_suppressed(nodes: list["TreeNode"]) -> list["TreeNode"]:
    """Recursively remove nodes flagged with ``suppress``."""
    result: list["TreeNode"] = []
    for node in nodes:
        if node.flags.get("suppress"):
            continue
        node.nodes = _remove_suppressed(node.nodes)
        result.append(node)
    return result
