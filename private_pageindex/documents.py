"""Shared document-level operations used by both the web and MCP layers.

Keeping the deletion cascade in one place ensures the FastAPI routes and the
MCP tools behave identically.
"""

from __future__ import annotations

from private_pageindex.storage import LocalStorage


def delete_document_and_assets(doc_id: str, storage: LocalStorage) -> dict[str, str]:
    """Delete a document and all associated database rows and files.

    Raises :class:`KeyError` when the document does not exist so callers can
    translate that into their own not-found response (HTTP 404 for the web
    app, a tool error for MCP).
    """
    storage.get_document(doc_id)  # raises KeyError if the document is unknown
    storage.delete_document(doc_id)
    return {"status": "success", "message": f"Document {doc_id} has been deleted."}
