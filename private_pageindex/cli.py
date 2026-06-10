"""CLI entry point for private PageIndex RAG.

Usage:

    python -m private_pageindex.cli ingest <pdf_path>
    python -m private_pageindex.cli ask <doc_id> "<question>"
    python -m private_pageindex.cli serve
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from private_pageindex.config import get_settings
from private_pageindex.ingest.pipeline import IndexResult, PipelineError, index_pdf
from private_pageindex.llm.ollama import OllamaClient, OllamaError
from private_pageindex.retrieval.answering import generate_answer
from private_pageindex.retrieval.tree_search import search_tree
from private_pageindex.storage import LocalStorage, RetrievalStepRecord


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="private_pageindex",
        description="Fully private local PageIndex-style RAG for text PDFs.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ingest
    ingest_parser = subparsers.add_parser("ingest", help="Index a local text PDF.")
    ingest_parser.add_argument("pdf_path", type=str, help="Path to a local .pdf file.")

    # ask
    ask_parser = subparsers.add_parser("ask", help="Ask a question about an indexed document.")
    ask_parser.add_argument("doc_id", type=str, help="Document ID from a previous ingest.")
    ask_parser.add_argument("question", type=str, help="The question to ask.")

    # serve
    subparsers.add_parser("serve", help="Start the local web server.")

    args = parser.parse_args(argv)

    if args.command == "ingest":
        _cmd_ingest(args.pdf_path)
    elif args.command == "ask":
        _cmd_ask(args.doc_id, args.question)
    elif args.command == "serve":
        _cmd_serve()


def _cmd_ingest(pdf_path: str) -> None:
    """Index a local PDF file."""
    settings = get_settings()
    storage = LocalStorage(settings.data_dir)
    storage.initialize()

    path = Path(pdf_path)
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    llm_client: OllamaClient | None = None
    try:
        llm_client = OllamaClient(timeout=120)
    except Exception:
        print("Warning: could not create Ollama client; indexing without LLM enhancement.")

    try:
        result: IndexResult = index_pdf(path, storage, llm_client=llm_client)
    except PipelineError as exc:
        print(f"Indexing failed: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        if llm_client:
            llm_client.close()

    print(f"Indexed: {result.filename}")
    print(f"  doc_id:     {result.doc_id}")
    print(f"  pages:      {result.page_count}")
    print(f"  tree nodes: {result.node_count}")


def _cmd_ask(doc_id: str, question: str) -> None:
    """Ask a question about an indexed document."""
    settings = get_settings()
    storage = LocalStorage(settings.data_dir)
    storage.initialize()

    try:
        document = storage.get_document(doc_id)
    except KeyError:
        print(f"Error: document not found: {doc_id}", file=sys.stderr)
        sys.exit(1)

    if document.status != "completed":
        print(f"Error: document status is '{document.status}', not 'completed'.", file=sys.stderr)
        sys.exit(1)

    tree = storage.read_tree(doc_id)
    pages = storage.read_pages(doc_id)

    llm_client = OllamaClient(timeout=120)
    try:
        # Tree search
        retrieval = search_tree(question, tree, pages, llm_client)

        # Answer
        answer_result = generate_answer(question, retrieval.retrieved_pages, llm_client)

        # Store chat + trace
        chat = storage.insert_chat(doc_id, question, answer_result.answer)
        all_steps = retrieval.trace + [answer_result.trace_step]
        for idx, step in enumerate(all_steps):
            storage.insert_retrieval_step(RetrievalStepRecord(
                chat_id=chat.id,
                step_index=idx,
                action=step.action,
                node_id=step.node_id,
                pages=step.pages,
                reason=step.reason,
            ))
    except OllamaError as exc:
        print(f"Ollama error: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        llm_client.close()

    print(f"\nQuestion: {question}")
    print(f"\nAnswer: {answer_result.answer}")
    print(f"\nRetrieved {len(retrieval.selected_node_ids)} node(s), "
          f"{len(retrieval.retrieved_pages)} page(s).")
    print(f"Chat ID: {chat.id}")


def _cmd_serve() -> None:
    """Start the local web server."""
    import uvicorn

    settings = get_settings()
    print(f"Starting Private PageIndex RAG on http://127.0.0.1:8000")
    print(f"Ollama endpoint: {settings.ollama_base_url}")
    print(f"Model: {settings.ollama_model}")
    print(f"Data directory: {settings.data_dir}")
    print()
    uvicorn.run(
        "private_pageindex.web.app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
