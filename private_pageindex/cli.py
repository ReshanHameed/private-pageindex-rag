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
    serve_parser = subparsers.add_parser("serve", help="Start the local web server.")
    serve_parser.add_argument("--host", type=str, default=None, help="Host address to bind to.")
    serve_parser.add_argument("--port", type=int, default=None, help="Port to bind to.")

    # serve-mcp
    mcp_parser = subparsers.add_parser(
        "serve-mcp",
        help="Start the MCP server for external agents (stdio by default).",
    )
    mcp_parser.add_argument(
        "--http",
        action="store_true",
        help="Run as a shared streamable-HTTP server instead of stdio.",
    )
    mcp_parser.add_argument("--host", type=str, default=None, help="HTTP bind host.")
    mcp_parser.add_argument("--port", type=int, default=None, help="HTTP bind port.")

    # dev
    dev_parser = subparsers.add_parser(
        "dev",
        help="Start Ollama, backend, frontend, and MCP HTTP server together for local development.",
    )
    dev_parser.add_argument("--host", type=str, default=None, help="Backend bind host.")
    dev_parser.add_argument("--port", type=int, default=None, help="Backend bind port.")
    dev_parser.add_argument(
        "--mcp-host",
        type=str,
        default=None,
        help="MCP HTTP bind host (default from settings).",
    )
    dev_parser.add_argument(
        "--mcp-port",
        type=int,
        default=None,
        help="MCP HTTP bind port (default from settings).",
    )
    dev_parser.add_argument(
        "--no-frontend",
        action="store_true",
        help="Skip the Vite frontend dev server.",
    )
    dev_parser.add_argument(
        "--no-mcp",
        action="store_true",
        help="Skip the shared MCP HTTP server.",
    )
    dev_parser.add_argument(
        "--no-ollama",
        action="store_true",
        help="Do not start Ollama (use when it is already running elsewhere).",
    )

    args = parser.parse_args(argv)

    if args.command == "ingest":
        _cmd_ingest(args.pdf_path)
    elif args.command == "ask":
        _cmd_ask(args.doc_id, args.question)
    elif args.command == "serve":
        _cmd_serve(args.host, args.port)
    elif args.command == "serve-mcp":
        _cmd_serve_mcp(args.http, args.host, args.port)
    elif args.command == "dev":
        _cmd_dev(
            host=args.host,
            port=args.port,
            mcp_host=args.mcp_host,
            mcp_port=args.mcp_port,
            with_frontend=not args.no_frontend,
            with_mcp_http=not args.no_mcp,
            with_ollama=not args.no_ollama,
        )


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


def _cmd_serve(host: str | None = None, port: int | None = None) -> None:
    """Start the local web server."""
    import os
    import uvicorn

    settings = get_settings()
    srv_host = host or os.environ.get("HOST", "127.0.0.1")
    try:
        srv_port = port or int(os.environ.get("PORT", "8000"))
    except ValueError:
        srv_port = 8000

    print(f"Starting Private PageIndex RAG on http://{srv_host}:{srv_port}")
    print(f"Ollama endpoint: {settings.ollama_base_url}")
    print(f"Model: {settings.ollama_model}")
    print(f"Data directory: {settings.data_dir}")
    print()

    is_docker = os.environ.get("DOCKER_ENV") == "true"
    uvicorn.run(
        "private_pageindex.web.app:app",
        host=srv_host,
        port=srv_port,
        reload=not is_docker,
    )


def _cmd_serve_mcp(http: bool, host: str | None, port: int | None) -> None:
    """Start the MCP server so external agents can drive the pipeline."""
    try:
        from private_pageindex.mcp_server import serve as serve_mcp
    except ModuleNotFoundError as exc:
        print(
            "The MCP server requires the 'mcp' package. Install it with:\n"
            "  pip install -e .[mcp]",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    settings = get_settings()
    mode = "streamable HTTP" if http else "stdio"
    # Log to stderr: in stdio mode, stdout is the JSON-RPC protocol channel.
    print(f"Starting Private PageIndex RAG MCP server ({mode}).", file=sys.stderr)
    print(f"Ollama endpoint: {settings.ollama_base_url}", file=sys.stderr)
    print(f"Data directory:  {settings.data_dir}", file=sys.stderr)
    print(f"Inbox directory: {settings.inbox_dir}", file=sys.stderr)
    if http:
        bind_host = host or settings.mcp_http_host
        bind_port = port or settings.mcp_http_port
        auth = "on" if (settings.mcp_auth_token or "").strip() else "off"
        print(
            f"HTTP endpoint:   http://{bind_host}:{bind_port}/mcp  (auth: {auth})",
            file=sys.stderr,
        )
    print(file=sys.stderr)

    serve_mcp(http=http, host=host, port=port)


def _cmd_dev(
    host: str | None,
    port: int | None,
    mcp_host: str | None,
    mcp_port: int | None,
    *,
    with_frontend: bool,
    with_mcp_http: bool,
    with_ollama: bool,
) -> None:
    """Start Ollama, backend, frontend, and optional MCP HTTP server together."""
    from private_pageindex.dev_runner import run_dev_stack

    run_dev_stack(
        host=host,
        port=port,
        mcp_host=mcp_host,
        mcp_port=mcp_port,
        with_frontend=with_frontend,
        with_mcp_http=with_mcp_http,
        with_ollama=with_ollama,
    )


if __name__ == "__main__":
    main()
