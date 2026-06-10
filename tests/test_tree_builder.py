from private_pageindex.indexing.tree_builder import build_tree, flatten_tree
from private_pageindex.ingest.pdf_text import ExtractedPage


class FakeEnhancer:
    def __init__(self):
        self.calls = []

    def chat_json(self, system: str, user: str, schema_hint: str | None = None):
        self.calls.append({"system": system, "user": user, "schema_hint": schema_hint})
        if "Safety Requirements" in user:
            return {
                "title": "Safety Requirements",
                "summary": "Rules for protective equipment and safe handling.",
            }
        return {
            "title": "Introduction",
            "summary": "Document overview and purpose.",
        }


def page(page_number: int, text: str) -> ExtractedPage:
    return ExtractedPage(
        page_number=page_number,
        text=text,
        char_count=len(text),
    )


def find_node_by_title(nodes, title: str):
    for node in flatten_tree(nodes):
        if node.title == title:
            return node
    raise AssertionError(f"Node not found: {title}")


def max_depth(nodes) -> int:
    if not nodes:
        return 0
    return max(1 + max_depth(node.nodes) for node in nodes)


class TitleChangingEnhancer:
    def chat_json(self, system: str, user: str, schema_hint: str | None = None):
        return {
            "title": "Extended Methodology",
            "summary": "LLM summary is allowed to update.",
        }


def test_build_tree_detects_numbered_headings_and_nested_sections():
    pages = [
        page(1, "1 Introduction\nThis manual explains the machine."),
        page(2, "2 Safety Requirements\nWear protective equipment."),
        page(3, "2.1 Protective Equipment\nUse goggles and gloves."),
        page(4, "3 Maintenance\nClean the filters weekly."),
    ]

    tree = build_tree(pages, max_pages_per_node=10, llm_client=None)
    flat_nodes = flatten_tree(tree)

    assert [node.node_id for node in flat_nodes] == ["0001", "0002", "0003", "0004"]
    assert [node.title for node in tree] == [
        "Introduction",
        "Safety Requirements",
        "Maintenance",
    ]
    assert tree[1].nodes[0].title == "Protective Equipment"
    assert tree[0].start_page == 1
    assert tree[0].end_page == 1
    assert tree[1].start_page == 2
    assert tree[1].end_page == 3
    assert tree[1].nodes[0].start_page == 3
    assert tree[1].nodes[0].end_page == 3
    assert tree[2].start_page == 4
    assert tree[2].end_page == 4


def test_build_tree_falls_back_to_page_ranges_when_headings_are_weak():
    pages = [
        page(1, "Body text without an obvious section heading."),
        page(2, "More body text without an obvious section heading."),
        page(3, "Continuation text with no heading."),
        page(4, "Final body text with no heading."),
        page(5, "Appendix-like text but not a heading."),
    ]

    tree = build_tree(pages, max_pages_per_node=2, llm_client=None)

    assert [node.title for node in tree] == ["Pages 1-2", "Pages 3-4", "Page 5"]
    assert [(node.start_page, node.end_page) for node in tree] == [
        (1, 2),
        (3, 4),
        (5, 5),
    ]
    assert all(node.summary for node in tree)


def test_build_tree_keeps_every_page_retrievable_with_sparse_text():
    pages = [
        page(1, "1 Overview\nUseful text."),
        page(2, ""),
        page(3, "2 Details\nMore useful text."),
    ]

    tree = build_tree(pages, max_pages_per_node=10, llm_client=None)
    covered_pages = set()
    for node in flatten_tree(tree):
        covered_pages.update(range(node.start_page, node.end_page + 1))

    assert covered_pages == {1, 2, 3}


def test_build_tree_can_use_local_llm_client_to_clean_titles_and_summarize():
    enhancer = FakeEnhancer()
    pages = [
        page(1, "1 Introduction\nThis manual explains the machine."),
        page(2, "2 Safety Requirements\nWear protective equipment."),
    ]

    tree = build_tree(pages, max_pages_per_node=10, llm_client=enhancer)

    assert tree[0].summary == "Document overview and purpose."
    assert tree[1].summary == "Rules for protective equipment and safe handling."
    assert len(enhancer.calls) == 2
    assert all("title" in call["schema_hint"] for call in enhancer.calls)


def test_build_tree_preserves_messy_pdf_boundaries_and_sections():
    pages = [
        page(8, "\n".join([
            "Section 5: Discussion",
            "5.1 Primary Analysis",
            "Body text.",
            "5.1.1 Sub-Analysis Alpha",
            "Body text.",
            "5.1.1.1 Deep Sub-Analysis",
            "Body text.",
            "5.1.1.1.1 Maximum Nesting Depth Test",
            "Body text.",
            "5.2 Secondary Analysis",
            "Body text.",
        ])),
        page(9, "Section 6: Conclusion\nConclusion text."),
        page(10, "References\n[1] Smith, A. (2020). A study."),
        page(11, ""),
        page(12, ""),
        page(13, "[ This page intentionally left blank - Page 11 ]"),
        page(14, "Appendix A: Extended Methodology\nA.1 Sub-appendix with Normal Heading Style\nBody."),
        page(22, "Section 1: Re-Introduction\n1.1 Overview\nBody."),
        page(23, "Abstract\nThis is a third abstract, appearing on page 21 of the document."),
        page(24, "Section 2 (Second Numbering): Alignment Chaos\nBody."),
        page(25, "Glossary\nTerm\nDefinition (Intentionally Wrong)\nAbstract\nA concrete object."),
        page(26, "Index\nThe following index was generated automatically and has not been verified."),
    ]

    tree = build_tree(pages, max_pages_per_node=10, llm_client=None)

    discussion = find_node_by_title(tree, "Section 5: Discussion")
    assert discussion.start_page == 8
    assert discussion.end_page == 8
    assert discussion.nodes
    assert max_depth([discussion]) >= 5

    conclusion = find_node_by_title(tree, "Section 6: Conclusion")
    assert (conclusion.start_page, conclusion.end_page) == (9, 9)

    references = find_node_by_title(tree, "References")
    assert (references.start_page, references.end_page) == (10, 10)

    blank_nodes = [
        node for node in flatten_tree(tree)
        if getattr(node, "flags", {}).get("is_blank")
    ]
    assert {node.start_page for node in blank_nodes} >= {11, 12, 13}

    appendix = find_node_by_title(tree, "Appendix A: Extended Methodology")
    assert appendix.start_page == 14

    abstract = find_node_by_title(tree, "Abstract")
    assert (abstract.start_page, abstract.end_page) == (23, 23)

    section_two = find_node_by_title(tree, "Section 2 (Second Numbering): Alignment Chaos")
    assert (section_two.start_page, section_two.end_page) == (24, 24)

    glossary = find_node_by_title(tree, "Glossary")
    assert (glossary.start_page, glossary.end_page) == (25, 25)

    index = find_node_by_title(tree, "Index")
    assert (index.start_page, index.end_page) == (26, 26)

    promoted_table_terms = [
        node.title
        for node in flatten_tree(tree)
        if node.start_page in {25, 26}
        and node.title
        in {"Definition (Intentionally Wrong)", "Methodology", "Conclusion"}
    ]
    assert promoted_table_terms == []


def test_tree_node_serializes_flags_without_removing_existing_fields():
    node = build_tree(
        [page(1, "References\n[1] Source.")],
        max_pages_per_node=10,
        llm_client=None,
    )[0]

    payload = node.to_dict()

    assert set(["node_id", "title", "start_page", "end_page", "summary", "nodes"]).issubset(payload)
    assert payload["title"] == "References"
    assert "flags" in payload
    assert isinstance(payload["flags"], dict)


def test_llm_enhancement_does_not_remove_structural_title_context():
    pages = [
        page(14, "Appendix A: Extended Methodology\nAppendix body."),
    ]

    tree = build_tree(pages, max_pages_per_node=10, llm_client=TitleChangingEnhancer())

    assert tree[0].title == "Appendix A: Extended Methodology"
    assert tree[0].summary == "LLM summary is allowed to update."


def test_blank_marker_inside_table_of_contents_does_not_make_page_blank():
    pages = [
        page(2, "\n".join([
            "Table of Contents",
            "Section",
            "Title",
            "11",
            "This Section Was Intentionally Left Blank",
            "Appendix A",
            "Acknowledgements",
        ])),
    ]

    tree = build_tree(pages, max_pages_per_node=10, llm_client=None)

    assert tree[0].title == "Table of Contents"
    assert tree[0].flags.get("is_blank") is None
    assert "source" in tree[0].flags  # source metadata is expected
    assert [node.title for node in flatten_tree(tree)] == ["Table of Contents"]


# ---------------------------------------------------------------------------
# Fix 1: Tree normalization tests
# ---------------------------------------------------------------------------


def test_multiline_title_fragments_are_merged():
    """Two all-caps fragment lines on the same page should merge into one node."""
    pages = [
        page(1, "RESEARCH REPORT ON ARTIFICIAL\nINTELLIGENCE\nSome body text."),
        page(2, "1 Introduction\nIntroduction text."),
        page(3, "2 Methods\nMethod details."),
    ]

    tree = build_tree(pages, max_pages_per_node=10, llm_client=None)
    root_titles = [node.title for node in tree]

    # The two fragments should be merged into one
    assert any("RESEARCH REPORT" in t and "INTELLIGENCE" in t for t in root_titles), \
        f"Expected merged title, got: {root_titles}"
    # The merged node should have the merged_title flag
    merged = [n for n in tree if n.flags.get("merged_title")]
    assert len(merged) == 1


def test_cover_page_noise_is_suppressed():
    """Page 1 with many short heading candidates and little text → single cover node."""
    # Use enough short lines from varied heading-detection sources so that
    # fragment merging doesn't collapse them below the cover threshold (3).
    pages = [
        page(1, "\n".join([
            "Annual Report",
            "Fiscal Year 2025",
            "Acme Corporation",
            "Confidential",
            "New York Office",
            "DRAFT",
        ])),
        page(2, "1 Introduction\nBody text."),
        page(3, "2 Financial Summary\nBody text."),
    ]

    tree = build_tree(pages, max_pages_per_node=10, llm_client=None)

    # Page 1 should be collapsed: either as a single cover node or merged+cover
    page1_nodes = [n for n in tree if n.start_page == 1]
    assert len(page1_nodes) == 1
    node = page1_nodes[0]
    assert node.flags.get("is_cover") or node.flags.get("merged_title")

    # Real sections on later pages are preserved
    other_nodes = [n for n in tree if n.start_page > 1]
    assert any("Introduction" in n.title for n in other_nodes)


def test_normalization_does_not_merge_real_headings():
    """Two numbered headings on the same page must NOT be merged."""
    pages = [
        page(1, "1 Overview\n1.1 Background\nBody text for both sections."),
        page(2, "2 Details\nMore body text."),
    ]

    tree = build_tree(pages, max_pages_per_node=10, llm_client=None)
    flat = flatten_tree(tree)

    # Numbered headings should stay separate
    titles = [n.title for n in flat]
    assert "Overview" in titles
    assert "Background" in titles
    # No merged_title flag on numbered headings
    assert not any(n.flags.get("merged_title") for n in flat)


# ---------------------------------------------------------------------------
# Fix 2: Duplicate heading handling tests
# ---------------------------------------------------------------------------


def test_duplicate_titles_are_flagged_and_disambiguated():
    """Two sections with the same title should be flagged and the second
    disambiguated with page context."""
    pages = [
        page(1, "1 Objectives\nFirst objectives section."),
        page(2, "2 Overview\nOverview text."),
        page(3, "3 Objectives\nSecond objectives section."),
    ]

    tree = build_tree(pages, max_pages_per_node=10, llm_client=None)
    flat = flatten_tree(tree)

    obj_nodes = [n for n in flat if "Objectives" in n.title]
    assert len(obj_nodes) == 2
    # Both should have duplicate_title flag
    assert all(n.flags.get("duplicate_title") for n in obj_nodes)
    # Second occurrence should have disambiguation suffix
    second = [n for n in obj_nodes if n.start_page == 3][0]
    assert "p3" in second.title
    assert "occurrence" in second.title


def test_recurring_corporate_headers_are_suppressed():
    """A company name repeated on 3+ section boundaries should be treated
    as a recurring header — only the first is kept."""
    pages = [
        page(1, "ACME CORPORATION\n1 Introduction\nIntro text."),
        page(3, "ACME CORPORATION\n2 Products\nProduct text."),
        page(5, "ACME CORPORATION\n3 Financials\nFinancials text."),
    ]

    tree = build_tree(pages, max_pages_per_node=10, llm_client=None)
    flat = flatten_tree(tree)

    acme_nodes = [n for n in flat if "ACME CORPORATION" in n.title.upper()]
    # Only the first occurrence should survive
    assert len(acme_nodes) <= 1
    # Real sections should still exist
    titles = [n.title for n in flat]
    assert any("Introduction" in t for t in titles)
    assert any("Products" in t for t in titles)
    assert any("Financials" in t for t in titles)


# ---------------------------------------------------------------------------
# Fix 3: Flat-tree fallback improvement tests
# ---------------------------------------------------------------------------


def test_repeated_headers_detected_in_corporate_pdf():
    """Pages with the same company name as first line should be detected
    and section titles extracted from line 2."""
    pages = [
        page(1, "ACME INC\nQ1 Revenue Report\nRevenue was $10M."),
        page(2, "ACME INC\nOperating Expenses\nExpenses were $5M."),
        page(3, "ACME INC\nNet Income\nNet income was $5M."),
        page(4, "ACME INC\nCash Flow Statement\nCash flow details."),
        page(5, "ACME INC\nBalance Sheet\nAssets and liabilities."),
    ]

    tree = build_tree(pages, max_pages_per_node=10, llm_client=None)
    flat = flatten_tree(tree)
    titles = [n.title for n in flat]

    # Should have section titles from line 2, not just "Pages 1-5"
    assert any("Revenue" in t for t in titles)
    assert any("Expenses" in t or "Operating" in t for t in titles)


def test_fallback_creates_two_level_tree_for_large_documents():
    """25 pages with no headings should produce parent groups with page children."""
    pages = [
        page(i, f"Body text for page {i}, no headings at all present here.")
        for i in range(1, 26)
    ]

    tree = build_tree(pages, max_pages_per_node=3, llm_client=None)
    flat = flatten_tree(tree)

    # Should have parent nodes with children (two-level structure)
    parents_with_children = [n for n in tree if n.nodes]
    assert len(parents_with_children) >= 1
    # Total node count should be > page count (parents + children)
    assert len(flat) > len(tree)


def test_fallback_stays_flat_for_small_documents():
    """5 pages with no headings should produce simple flat nodes (no regression)."""
    pages = [
        page(1, "Body text without any heading."),
        page(2, "More body text without heading."),
        page(3, "Continuation text with no heading."),
        page(4, "Final body text with no heading."),
        page(5, "Appendix-like text but not a heading."),
    ]

    tree = build_tree(pages, max_pages_per_node=2, llm_client=None)

    assert [node.title for node in tree] == ["Pages 1-2", "Pages 3-4", "Page 5"]
    assert all(not node.nodes for node in tree)  # flat, no children


# ---------------------------------------------------------------------------
# Fix 4: Tree validation tests
# ---------------------------------------------------------------------------

from private_pageindex.indexing.tree_builder import validate_tree


def test_validate_tree_reports_clean_tree():
    """A well-structured tree should get score 1.0 and no flags."""
    pages = [
        page(1, "1 Introduction\nThis manual explains the machine."),
        page(2, "2 Safety Requirements\nWear protective equipment."),
        page(3, "2.1 Protective Equipment\nUse goggles and gloves."),
        page(4, "3 Maintenance\nClean the filters weekly."),
    ]

    tree = build_tree(pages, max_pages_per_node=10, llm_client=None)
    report = validate_tree(tree, pages)

    assert report.quality_score == 1.0
    assert report.flags == []
    assert report.warnings == []


def test_validate_tree_detects_duplicates_and_flat_structure():
    """A flat tree with duplicate titles should report flags and low score."""
    pages = [
        page(1, "Body text only, no headings here."),
        page(2, "More body text, still no headings."),
        page(3, "Even more body text, nothing here."),
    ]

    tree = build_tree(pages, max_pages_per_node=2, llm_client=None)
    report = validate_tree(tree, pages)

    assert "flat_tree" in report.flags
    assert report.quality_score < 1.0
    assert len(report.warnings) > 0


def test_validation_report_stored_in_tree_json():
    """The ingest pipeline should store a validation report in tree.json."""
    import tempfile
    from pathlib import Path
    from private_pageindex.storage import LocalStorage
    from private_pageindex.ingest.pipeline import index_pdf

    # Create a temp PDF using fitz
    import fitz
    tmp_dir = Path(tempfile.mkdtemp())
    pdf_path = tmp_dir / "test.pdf"
    doc = fitz.open()
    p = doc.new_page()
    p.insert_text((72, 72), "1 Introduction\nSample text.")
    doc.save(str(pdf_path))
    doc.close()

    storage = LocalStorage(tmp_dir / "data")
    storage.initialize()

    result = index_pdf(pdf_path, storage, llm_client=None)
    tree = storage.read_tree(result.doc_id)

    assert "validation" in tree
    assert "quality_score" in tree["validation"]
    assert "flags" in tree["validation"]
    assert isinstance(tree["validation"]["quality_score"], float)

    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Fix 5: Front-matter node for orphan pages
# ---------------------------------------------------------------------------


def test_front_matter_node_covers_pages_before_first_heading():
    """Pages before the first numbered heading should get a Front Matter node."""
    pages = [
        # Pages 1-3 are body text that does NOT trigger heading detection
        # (long paragraphs, no all-caps short lines, no numbered headings)
        page(1, "This project report on health monitoring system was submitted by "
                "Reshan Hameed H (960122243033), Bagathesh M.V (960122243301), and "
                "Aravinth Selva P (960122243007) at Annai Vailankanni College of "
                "Engineering, Kanyakumari under Anna University Chennai."),
        page(2, "Certified that this project report is the bonafide work of the "
                "above-mentioned students who carried out the project work under "
                "the supervision of Mrs. S. Sangeetha, Assistant Professor in the "
                "Department of AI and DS."),
        page(3, "This paper presents an intelligent health monitoring system that "
                "integrates artificial intelligence with multiple biomedical sensors "
                "to enable continuous and real-time patient monitoring using ESP32 "
                "microcontroller and various sensors."),
        page(4, "1 Introduction\nHealth monitoring is important for early detection."),
        page(5, "2 Literature Review\nPrevious studies have shown the benefits of AI."),
    ]

    tree = build_tree(pages, max_pages_per_node=10, llm_client=None)
    flat = flatten_tree(tree)

    # First node should be Front Matter covering pages 1-3
    assert tree[0].title == "Front Matter"
    assert tree[0].start_page == 1
    assert tree[0].end_page == 3
    assert tree[0].flags.get("is_front_matter") is True

    # Real sections should follow
    assert any("Introduction" in n.title for n in flat)
    assert any("Literature Review" in n.title for n in flat)

    # All pages should be covered
    covered = set()
    for node in flat:
        covered.update(range(node.start_page, node.end_page + 1))
    assert covered == {1, 2, 3, 4, 5}


def test_no_front_matter_when_headings_start_on_page_one():
    """No Front Matter node should be created when headings start on page 1."""
    pages = [
        page(1, "1 Introduction\nThis manual explains the machine."),
        page(2, "2 Safety\nWear protective equipment."),
    ]

    tree = build_tree(pages, max_pages_per_node=10, llm_client=None)

    assert tree[0].title != "Front Matter"
    assert not any(n.flags.get("is_front_matter") for n in flatten_tree(tree))


def test_validate_tree_detects_orphan_pages():
    """Validation should flag pages not covered by any tree node."""
    from private_pageindex.indexing.tree_builder import TreeNode

    # Manually create a tree that skips pages 1-2
    nodes = [
        TreeNode(
            node_id="0001",
            title="Chapter 1",
            start_page=3,
            end_page=5,
            summary="Chapter text.",
        )
    ]
    all_pages = [
        page(1, "Title page text."),
        page(2, "Certificate text."),
        page(3, "Chapter 1 text."),
        page(4, "More chapter text."),
        page(5, "End of chapter."),
    ]

    report = validate_tree(nodes, all_pages)

    assert "orphan_pages" in report.flags
    assert any("2 page(s) not covered" in w for w in report.warnings)
    assert report.quality_score < 1.0


def test_summary_includes_extracted_entities():
    """Verify that _deterministic_summary extracts and appends key entities like emails and phone numbers."""
    pages = [
        page(1, "1 Objectives\nFor support, contact admin@example.com or call 555-019-9999. Visit www.example.com for more info.")
    ]
    tree = build_tree(pages, max_pages_per_node=10, llm_client=None)

    assert "admin@example.com" in tree[0].summary
    assert "555-019-9999" in tree[0].summary
    assert "www.example.com" in tree[0].summary


def test_build_tree_calls_progress_callback():
    progresses = []
    def callback(stage: str, percent: int):
        progresses.append((stage, percent))

    pages = [
        page(1, "1 Introduction\nThis manual explains the machine."),
        page(2, "2 Safety Requirements\nWear protective equipment."),
    ]

    enhancer = FakeEnhancer()
    build_tree(pages, max_pages_per_node=10, llm_client=enhancer, progress_callback=callback)

    assert len(progresses) > 0
    stages = [p[0] for p in progresses]
    percentages = [p[1] for p in progresses]

    assert "detecting headings" in stages
    assert any("enhancing node" in s for s in stages)
    # Check that percentages are between 45 and 68 during the build_tree phase
    assert all(45 <= p <= 68 for p in percentages)
