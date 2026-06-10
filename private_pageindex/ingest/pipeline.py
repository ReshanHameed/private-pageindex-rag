"""Indexing pipeline: PDF upload → extraction → tree building → storage."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from private_pageindex.indexing.tree_builder import (
    JsonChatClient,
    TreeNode,
    build_tree,
    flatten_tree,
    validate_tree,
)
from private_pageindex.ingest.pdf_text import (
    ExtractedPage,
    extract_pdf_text,
)
from private_pageindex.storage import LocalStorage, NodeRecord


class PipelineError(RuntimeError):
    """Raised when the indexing pipeline fails."""


@dataclass(frozen=True)
class IndexProgress:
    """Progress update emitted by the indexing pipeline."""

    doc_id: str
    stage: str
    percent: int


class ProgressCallback(Protocol):
    def __call__(self, progress: IndexProgress) -> None:
        """Handle one pipeline progress update."""


@dataclass(frozen=True)
class IndexResult:
    """Result returned after a successful indexing run."""

    doc_id: str
    filename: str
    page_count: int
    node_count: int


def index_pdf(
    file_path: str | Path,
    storage: LocalStorage,
    *,
    llm_client: JsonChatClient | None = None,
    max_pages_per_node: int | None = None,
    existing_doc_id: str | None = None,
    progress_callback: ProgressCallback | None = None,
) -> IndexResult:
    """Index a local text PDF into the private PageIndex storage.

    Steps:
        1. Create a ``processing`` document record.
        2. Copy the PDF into the uploads directory.
        3. Extract page text with PyMuPDF.
        4. Build a PageIndex-style tree.
        5. Persist pages (JSONL), tree (JSON), and node rows.
        6. Mark the document as ``completed``.

    If any step after the document record is created fails, the document is
    marked ``failed`` with the error message preserved.

    Returns an :class:`IndexResult` on success.

    Raises :class:`PipelineError` on failure (the document row will already
    have been marked ``failed`` in storage).
    """
    path = Path(file_path)
    filename = path.name

    # Create or reuse a document record immediately so failures are tracked.
    document = (
        storage.get_document(existing_doc_id)
        if existing_doc_id
        else storage.create_document(filename=filename, status="processing")
    )
    doc_id = document.id
    filename = document.filename

    def emit(stage: str, percent: int) -> None:
        storage.update_document_progress(
            doc_id,
            progress_percent=percent,
            progress_stage=stage,
        )
        if progress_callback:
            progress_callback(IndexProgress(doc_id=doc_id, stage=stage, percent=percent))

    try:
        emit("queued", 0)

        # --- Copy PDF into uploads directory ---------------------------------
        dest = storage.upload_path(doc_id)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if path.resolve() != dest.resolve():
            emit("saving upload", 5)
            shutil.copy2(path, dest)

        # --- Extract page text -----------------------------------------------
        emit("extracting text", 20)
        pages: list[ExtractedPage] = extract_pdf_text(dest)

        # --- Build tree -------------------------------------------------------
        emit("building tree", 45)
        tree: list[TreeNode] = build_tree(
            pages,
            max_pages_per_node=max_pages_per_node,
            llm_client=llm_client,
            progress_callback=emit,
        )

        # --- Persist pages as JSONL -------------------------------------------
        emit("writing artifacts", 70)
        page_dicts = [
            {
                "page_number": page.page_number,
                "text": page.text,
                "char_count": page.char_count,
            }
            for page in pages
        ]
        storage.write_pages(doc_id, page_dicts)

        # --- Persist tree as JSON ---------------------------------------------
        report = validate_tree(tree, pages)
        tree_dict = {
            "doc_id": doc_id,
            "nodes": [node.to_dict() for node in tree],
            "validation": report.to_dict(),
        }
        storage.write_tree(doc_id, tree_dict)

        # --- Insert node rows into SQLite ------------------------------------
        emit("inserting nodes", 85)
        flat_nodes = flatten_tree(tree)
        for node in flat_nodes:
            parent_id = _find_parent_id(node, tree)
            storage.insert_node(
                NodeRecord(
                    doc_id=doc_id,
                    node_id=node.node_id,
                    title=node.title,
                    start_page=node.start_page,
                    end_page=node.end_page,
                    summary=node.summary,
                    parent_node_id=parent_id,
                )
            )

        # --- Mark completed ---------------------------------------------------
        page_count = len(pages)
        node_count = len(flat_nodes)
        storage.update_document_status(
            doc_id, "completed", page_count=page_count
        )
        emit("completed", 100)

        return IndexResult(
            doc_id=doc_id,
            filename=filename,
            page_count=page_count,
            node_count=node_count,
        )

    except Exception as exc:
        error_message = f"{type(exc).__name__}: {exc}"
        storage.update_document_status(doc_id, "failed", error=error_message)
        try:
            emit("failed", storage.get_document(doc_id).progress_percent)
        except Exception:
            pass
        raise PipelineError(
            f"Indexing failed for {filename}: {error_message}"
        ) from exc


def _find_parent_id(
    target: TreeNode,
    roots: list[TreeNode],
) -> str | None:
    """Walk the tree to find the parent node_id for *target*.

    Returns ``None`` when *target* is a root node.
    """
    for root in roots:
        result = _search_parent(target, root, parent_id=None)
        if result is not _SENTINEL:
            return result
    return None


_SENTINEL = object()


def _search_parent(
    target: TreeNode,
    current: TreeNode,
    parent_id: str | None,
) -> str | None | object:
    """Depth-first search returning the parent_id when *target* is found."""
    if current is target:
        return parent_id
    for child in current.nodes:
        result = _search_parent(target, child, parent_id=current.node_id)
        if result is not _SENTINEL:
            return result
    return _SENTINEL
