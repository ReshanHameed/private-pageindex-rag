"""Heading detection for tree building.

Extracts heading candidates from PDF page text using regex patterns,
all-caps detection, title-case detection, and known heading keywords.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from private_pageindex.ingest.pdf_text import ExtractedPage

# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HeadingCandidate:
    page_number: int
    line_index: int
    title: str
    level: int
    source: str
    flags: dict[str, bool] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

NUMBERED_HEADING_RE = re.compile(
    r"^(?P<number>\d+(?:\.\d+)*)(?:[.)])?\s+(?P<title>[A-Za-z][A-Za-z0-9 ,:;/&()'-]{2,120})$"
)
SECTION_HEADING_RE = re.compile(
    r"^Section\s+\d+(?:\s*\([^)]*\))?\s*:\s+.+$",
    re.IGNORECASE,
)
APPENDIX_HEADING_RE = re.compile(
    r"^Appendix\s+[A-Z](?:\s*:\s+.+)?$",
    re.IGNORECASE,
)
APPENDIX_NUMBERED_HEADING_RE = re.compile(
    r"^(?P<number>[A-Z](?:\.\d+)+)\s+(?P<title>.+)$"
)
KNOWN_SINGLE_LINE_HEADINGS = {
    "abstract",
    "references",
    "bibliography",
    "glossary",
    "index",
    "acknowledgements",
    "acknowledgments",
    "appendix",
    "results",
    "discussion",
    "conclusion",
    "methodology",
}
INTENTIONAL_BLANK_MARKERS = (
    "intentionally left blank",
    "page intentionally left blank",
)

MAX_HEADING_SCAN_LINES = 60
MAX_WEAK_HEADING_LINE_INDEX = 1


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_headings(pages: list[ExtractedPage]) -> list[HeadingCandidate]:
    """Scan page text for heading candidates."""
    candidates: list[HeadingCandidate] = []
    seen: set[tuple[int, int, str]] = set()
    for page in pages:
        blank_candidate = _blank_page_candidate(page)
        if blank_candidate is not None:
            candidates.append(blank_candidate)
            continue

        for line_index, raw_line in enumerate(page.text.splitlines()[:MAX_HEADING_SCAN_LINES]):
            line = normalize_line(raw_line)
            if not line:
                continue
            candidate = _candidate_from_line(page.page_number, line, line_index)
            if candidate is None:
                continue
            key = (candidate.page_number, candidate.line_index, candidate.title)
            if key in seen:
                continue
            candidates.append(candidate)
            seen.add(key)
    return candidates


def detect_repeated_headers(
    pages: list[ExtractedPage],
) -> list[HeadingCandidate]:
    """Detect corporate-style PDFs where the same header repeats on many pages.

    If >= 30% of pages share the same first-line text, that text is a recurring
    header.  Skip it and look at the next non-empty line for a section title.
    """
    if len(pages) < 4:
        return []

    first_lines: dict[int, str] = {}
    for p in pages:
        for raw in p.text.splitlines():
            line = normalize_line(raw)
            if line:
                first_lines[p.page_number] = line
                break

    if not first_lines:
        return []

    from collections import Counter
    counts = Counter(first_lines.values())
    most_common_line, most_common_count = counts.most_common(1)[0]
    ratio = most_common_count / len(pages)

    if ratio < _REPEATED_HEADER_RATIO:
        return []

    candidates: list[HeadingCandidate] = []
    for p in pages:
        lines = [normalize_line(raw) for raw in p.text.splitlines() if normalize_line(raw)]
        if not lines:
            continue

        title_line = None
        for line in lines[:5]:
            if line != most_common_line:
                title_line = line
                break

        if title_line and len(title_line) <= 120 and not title_line.endswith("."):
            candidates.append(HeadingCandidate(
                page_number=p.page_number,
                line_index=0,
                title=title_line,
                level=1,
                source="repeated_header",
                flags={},
            ))

    if len(candidates) >= 2:
        return candidates
    return []


# ---------------------------------------------------------------------------
# Helpers (used internally and by tree_builder)
# ---------------------------------------------------------------------------


def normalize_line(line: str) -> str:
    return " ".join(line.strip().split())


def clean_title(title: str) -> str:
    title = re.sub(r"^[\d.() \-]+", "", title.strip())
    title = re.sub(r"\s+", " ", title)
    return title.strip(" :-")


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

_REPEATED_HEADER_RATIO = 0.30


def _candidate_from_line(
    page_number: int,
    line: str,
    line_index: int,
) -> HeadingCandidate | None:
    numbered = NUMBERED_HEADING_RE.match(line)
    if numbered:
        number = numbered.group("number")
        title = clean_title(numbered.group("title"))
        return HeadingCandidate(
            page_number=page_number,
            line_index=line_index,
            title=title,
            level=number.count(".") + 1,
            source="numbered",
            flags={},
        )

    appendix_numbered = APPENDIX_NUMBERED_HEADING_RE.match(line)
    if appendix_numbered:
        number = appendix_numbered.group("number")
        return HeadingCandidate(
            page_number=page_number,
            line_index=line_index,
            title=line.strip(),
            level=_level_from_appendix_number(number),
            source="appendix_numbered",
            flags={},
        )

    if SECTION_HEADING_RE.match(line):
        return HeadingCandidate(
            page_number=page_number,
            line_index=line_index,
            title=line.strip(),
            level=1,
            source="section",
            flags={},
        )

    if (
        line_index <= MAX_WEAK_HEADING_LINE_INDEX
        and APPENDIX_HEADING_RE.match(line)
    ):
        return HeadingCandidate(
            page_number=page_number,
            line_index=line_index,
            title=line.strip(),
            level=1,
            source="appendix",
            flags={},
        )

    if (
        line_index <= MAX_WEAK_HEADING_LINE_INDEX
        and _is_known_single_line_heading(line)
    ):
        return HeadingCandidate(
            page_number=page_number,
            line_index=line_index,
            title=line.strip(),
            level=1,
            source="known_heading",
            flags={},
        )

    if (
        line_index <= MAX_WEAK_HEADING_LINE_INDEX
        and _looks_like_all_caps_heading(line)
    ):
        return HeadingCandidate(
            page_number=page_number,
            line_index=line_index,
            title=clean_title(line),
            level=1,
            source="all_caps",
            flags={},
        )

    if (
        line_index <= MAX_WEAK_HEADING_LINE_INDEX
        and _looks_like_title_heading(line)
    ):
        return HeadingCandidate(
            page_number=page_number,
            line_index=line_index,
            title=clean_title(line),
            level=1,
            source="title_case",
            flags={},
        )

    return None


def _is_known_single_line_heading(line: str) -> bool:
    return line.strip().lower() in KNOWN_SINGLE_LINE_HEADINGS


def _level_from_appendix_number(number: str) -> int:
    return number.count(".") + 1


def _is_blank_page_text(text: str) -> bool:
    clean = " ".join(text.lower().split())
    if not clean:
        return True
    non_empty_lines = [
        line for line in (normalize_line(raw) for raw in text.splitlines()) if line
    ]
    if len(non_empty_lines) > 2:
        return False
    if len(clean) > 160:
        return False
    return any(marker in clean for marker in INTENTIONAL_BLANK_MARKERS)


def _blank_page_candidate(page: ExtractedPage) -> HeadingCandidate | None:
    if not _is_blank_page_text(page.text):
        return None
    return HeadingCandidate(
        page_number=page.page_number,
        line_index=-1,
        title=f"Blank Page {page.page_number}",
        level=1,
        source="blank_page",
        flags={"is_blank": True},
    )


def _looks_like_all_caps_heading(line: str) -> bool:
    letters = [char for char in line if char.isalpha()]
    if len(letters) < 4 or len(line) > 90:
        return False
    uppercase_ratio = sum(char.isupper() for char in letters) / len(letters)
    return uppercase_ratio > 0.8 and not line.endswith(".")


def _looks_like_title_heading(line: str) -> bool:
    words = line.split()
    if not 2 <= len(words) <= 8:
        return False
    if len(line) > 80 or line.endswith((".", ",", ";")):
        return False
    titled_words = sum(word[:1].isupper() for word in words if word[:1].isalpha())
    return titled_words >= max(2, len(words) - 1)
