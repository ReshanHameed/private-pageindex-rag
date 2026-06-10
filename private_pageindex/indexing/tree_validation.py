"""Tree validation: inspect a built tree and report structural quality issues."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from private_pageindex.indexing.heading_detection import NUMBERED_HEADING_RE
from private_pageindex.ingest.pdf_text import ExtractedPage

if TYPE_CHECKING:
    from private_pageindex.indexing.tree_builder import TreeNode


@dataclass
class TreeReport:
    """Quality report for a built tree."""

    flags: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    quality_score: float = 1.0

    def to_dict(self) -> dict:
        return {
            "flags": list(self.flags),
            "warnings": list(self.warnings),
            "quality_score": round(self.quality_score, 2),
        }


def validate_tree(
    nodes: list["TreeNode"],
    pages: list[ExtractedPage] | None = None,
) -> TreeReport:
    """Inspect a built tree and report structural quality issues."""
    from private_pageindex.indexing.tree_builder import flatten_tree

    report = TreeReport()
    all_nodes = flatten_tree(nodes)

    if not all_nodes:
        report.flags.append("empty_tree")
        report.warnings.append("Tree has no nodes.")
        report.quality_score = 0.0
        return report

    # Check: flat tree (no node has children)
    if all(not node.nodes for node in all_nodes):
        report.flags.append("flat_tree")
        report.warnings.append("Tree is completely flat — no node has children.")

    # Check: duplicate titles
    title_counts: dict[str, int] = {}
    for node in all_nodes:
        key = node.title.strip().lower()
        title_counts[key] = title_counts.get(key, 0) + 1
    duplicates = {t: c for t, c in title_counts.items() if c > 1}
    if duplicates:
        report.flags.append("duplicate_title")
        report.warnings.append(
            f"Duplicate titles found: {list(duplicates.keys())[:5]}"
        )

    # Check: title fragments (short titles with no children)
    fragments = [
        node for node in all_nodes
        if len(node.title.split()) <= 1 and not node.nodes
        and not node.flags.get("is_blank")
        and not node.flags.get("is_cover")
        and node.flags.get("source") not in ("numbered", "section", "appendix")
    ]
    if len(fragments) > len(all_nodes) * 0.3:
        report.flags.append("title_fragment")
        report.warnings.append(
            f"{len(fragments)} nodes have very short titles — possible fragments."
        )

    # Check: numbering conflict (mixed sources at root level)
    root_sources = {node.flags.get("source", "") for node in nodes}
    root_sources.discard("")
    if len(root_sources) > 2:
        report.flags.append("numbering_conflict")
        report.warnings.append(
            f"Mixed heading sources at root level: {root_sources}"
        )

    # Check: section restart (numbering resets)
    numbered_titles = []
    for node in nodes:
        match = NUMBERED_HEADING_RE.match(node.title)
        if match:
            numbered_titles.append(match.group("number"))
    if len(numbered_titles) >= 2:
        seen_numbers: set[str] = set()
        for num in numbered_titles:
            if num in seen_numbers:
                report.flags.append("section_restart")
                report.warnings.append(
                    f"Section numbering restarts at '{num}'."
                )
                break
            seen_numbers.add(num)

    # Check: cover noise
    cover_nodes = [n for n in all_nodes if n.flags.get("is_cover")]
    if cover_nodes:
        report.flags.append("cover_noise")
        report.warnings.append("Cover page noise was detected and collapsed.")

    # Check: orphan pages (pages not covered by any node)
    if pages:
        all_page_numbers = {p.page_number for p in pages}
        covered_pages: set[int] = set()
        for node in all_nodes:
            covered_pages.update(range(node.start_page, node.end_page + 1))
        orphans = all_page_numbers - covered_pages
        if orphans:
            sorted_orphans = sorted(orphans)
            report.flags.append("orphan_pages")
            report.warnings.append(
                f"{len(orphans)} page(s) not covered by any node: "
                f"{sorted_orphans[:10]}"
            )

    # Compute quality score
    penalty = len(report.flags) * 0.15
    report.quality_score = max(0.0, round(1.0 - penalty, 2))

    return report
