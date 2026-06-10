from __future__ import annotations

import contextlib
import json
import sqlite3
import uuid
from collections.abc import Generator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass(frozen=True)
class DocumentRecord:
    id: str
    filename: str
    status: str
    page_count: int | None
    error: str | None = None
    created_at: str | None = None
    progress_percent: int = 0
    progress_stage: str | None = None
    started_at: str | None = None
    finished_at: str | None = None

    @property
    def elapsed_seconds(self) -> int | None:
        if not self.started_at:
            return None
        try:
            started = datetime.fromisoformat(self.started_at)
            finished = (
                datetime.fromisoformat(self.finished_at)
                if self.finished_at
                else datetime.now(UTC)
            )
        except ValueError:
            return None
        return max(0, int((finished - started).total_seconds()))


@dataclass(frozen=True)
class NodeRecord:
    doc_id: str
    node_id: str
    title: str
    start_page: int
    end_page: int
    summary: str | None
    parent_node_id: str | None


@dataclass(frozen=True)
class ChatSessionRecord:
    id: str
    doc_id: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class ChatRecord:
    id: str
    session_id: str
    doc_id: str
    question: str
    answer: str
    created_at: str | None = None


@dataclass(frozen=True)
class RetrievalStepRecord:
    chat_id: str
    step_index: int
    action: str
    node_id: str | None
    pages: str | None
    reason: str
    id: int | None = None


class LocalStorage:
    """Local SQLite and filesystem persistence for private PageIndex data."""

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)
        self.db_path = self.data_dir / "private_pageindex.db"

    def initialize(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.documents_dir.mkdir(parents=True, exist_ok=True)

        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    status TEXT NOT NULL,
                    page_count INTEGER,
                    created_at TEXT NOT NULL,
                    error TEXT,
                    progress_percent INTEGER NOT NULL DEFAULT 0,
                    progress_stage TEXT,
                    started_at TEXT,
                    finished_at TEXT
                );

                CREATE TABLE IF NOT EXISTS nodes (
                    doc_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    start_page INTEGER NOT NULL,
                    end_page INTEGER NOT NULL,
                    summary TEXT,
                    parent_node_id TEXT,
                    PRIMARY KEY (doc_id, node_id),
                    FOREIGN KEY (doc_id) REFERENCES documents(id)
                );

                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    doc_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (doc_id) REFERENCES documents(id)
                );

                CREATE TABLE IF NOT EXISTS chats (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    doc_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(id),
                    FOREIGN KEY (doc_id) REFERENCES documents(id)
                );

                CREATE TABLE IF NOT EXISTS retrieval_steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL,
                    step_index INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    node_id TEXT,
                    pages TEXT,
                    reason TEXT NOT NULL,
                    FOREIGN KEY (chat_id) REFERENCES chats(id)
                );

                CREATE INDEX IF NOT EXISTS idx_retrieval_steps_chat_id ON retrieval_steps(chat_id);
                CREATE INDEX IF NOT EXISTS idx_chats_session_id ON chats(session_id);
                CREATE INDEX IF NOT EXISTS idx_chats_doc_id ON chats(doc_id);
                CREATE INDEX IF NOT EXISTS idx_chat_sessions_doc_id ON chat_sessions(doc_id);
                """
            )
            self._migrate_documents_table(conn)
            self._migrate_chats_table(conn)

    def _migrate_chats_table(self, conn: sqlite3.Connection) -> None:
        columns = [row["name"] for row in conn.execute("PRAGMA table_info(chats)")]
        if "session_id" not in columns:
            conn.execute("ALTER TABLE chats ADD COLUMN session_id TEXT")
            
            # Group existing chats by doc_id and create a default session
            docs_with_chats = conn.execute("SELECT DISTINCT doc_id FROM chats WHERE session_id IS NULL").fetchall()
            for row in docs_with_chats:
                doc_id = row["doc_id"]
                session_id = str(uuid.uuid4())
                now = _utc_now_iso()
                conn.execute(
                    """
                    INSERT INTO chat_sessions (id, doc_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (session_id, doc_id, now, now),
                )
                conn.execute(
                    "UPDATE chats SET session_id = ? WHERE doc_id = ? AND session_id IS NULL",
                    (session_id, doc_id),
                )

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def documents_dir(self) -> Path:
        return self.data_dir / "documents"

    def upload_path(self, doc_id: str, suffix: str = ".pdf") -> Path:
        return self.uploads_dir / f"{doc_id}{suffix}"

    def document_dir(self, doc_id: str) -> Path:
        return self.documents_dir / doc_id

    def pages_path(self, doc_id: str) -> Path:
        return self.document_dir(doc_id) / "pages.jsonl"

    def tree_path(self, doc_id: str) -> Path:
        return self.document_dir(doc_id) / "tree.json"

    def create_document(
        self,
        filename: str,
        status: str,
        page_count: int | None = None,
        error: str | None = None,
        doc_id: str | None = None,
    ) -> DocumentRecord:
        now = _utc_now_iso()
        progress_percent = 100 if status in {"completed", "failed"} else 0
        progress_stage = status
        record = DocumentRecord(
            id=doc_id or str(uuid.uuid4()),
            filename=filename,
            status=status,
            page_count=page_count,
            error=error,
            created_at=now,
            progress_percent=progress_percent,
            progress_stage=progress_stage,
            started_at=now,
            finished_at=now if status in {"completed", "failed"} else None,
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO documents (
                    id, filename, status, page_count, created_at, error,
                    progress_percent, progress_stage, started_at, finished_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.filename,
                    record.status,
                    record.page_count,
                    record.created_at,
                    record.error,
                    record.progress_percent,
                    record.progress_stage,
                    record.started_at,
                    record.finished_at,
                ),
            )
        return record

    def update_document_status(
        self,
        doc_id: str,
        status: str,
        *,
        page_count: int | None = None,
        error: str | None = None,
    ) -> None:
        progress_percent = 100 if status in {"completed", "failed"} else None
        progress_stage = status if status in {"completed", "failed"} else None
        finished_at = _utc_now_iso() if status in {"completed", "failed"} else None
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE documents
                SET status = ?,
                    page_count = COALESCE(?, page_count),
                    error = ?,
                    progress_percent = COALESCE(?, progress_percent),
                    progress_stage = COALESCE(?, progress_stage),
                    finished_at = COALESCE(?, finished_at)
                WHERE id = ?
                """,
                (
                    status,
                    page_count,
                    error,
                    progress_percent,
                    progress_stage,
                    finished_at,
                    doc_id,
                ),
            )

    def update_document_progress(
        self,
        doc_id: str,
        *,
        progress_percent: int,
        progress_stage: str,
    ) -> None:
        bounded_percent = max(0, min(100, progress_percent))
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE documents
                SET progress_percent = ?,
                    progress_stage = ?
                WHERE id = ?
                """,
                (bounded_percent, progress_stage, doc_id),
            )

    def get_document(self, doc_id: str) -> DocumentRecord:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, filename, status, page_count, error, created_at,
                       progress_percent, progress_stage, started_at, finished_at
                FROM documents
                WHERE id = ?
                """,
                (doc_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Document not found: {doc_id}")
        return DocumentRecord(**dict(row))

    def list_documents(self) -> list[DocumentRecord]:
        """Return all documents ordered by creation time (newest first)."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, filename, status, page_count, error, created_at,
                       progress_percent, progress_stage, started_at, finished_at
                FROM documents
                ORDER BY created_at DESC, ROWID DESC
                """
            ).fetchall()
        return [DocumentRecord(**dict(row)) for row in rows]

    def recover_interrupted_documents(self) -> int:
        """Mark any documents stuck in ``processing`` as ``failed``.

        Returns the number of documents recovered.  This is intended to
        be called once during application startup after an unclean
        shutdown.
        """
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE documents
                SET status = 'failed',
                    error = 'Indexing was interrupted by a server restart.',
                    progress_percent = 100,
                    progress_stage = 'failed',
                    finished_at = COALESCE(finished_at, created_at)
                WHERE status = 'processing'
                """
            )
            if cursor.rowcount > 0:
                conn.commit()
        return int(cursor.rowcount)

    def insert_node(self, record: NodeRecord) -> NodeRecord:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO nodes (
                    doc_id, node_id, title, start_page, end_page, summary, parent_node_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.doc_id,
                    record.node_id,
                    record.title,
                    record.start_page,
                    record.end_page,
                    record.summary,
                    record.parent_node_id,
                ),
            )
        return record

    def list_nodes(self, doc_id: str) -> list[NodeRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT doc_id, node_id, title, start_page, end_page, summary, parent_node_id
                FROM nodes
                WHERE doc_id = ?
                ORDER BY start_page, node_id
                """,
                (doc_id,),
            ).fetchall()
        return [NodeRecord(**dict(row)) for row in rows]

    def create_chat_session(self, doc_id: str) -> ChatSessionRecord:
        record = ChatSessionRecord(
            id=str(uuid.uuid4()),
            doc_id=doc_id,
            created_at=_utc_now_iso(),
            updated_at=_utc_now_iso(),
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO chat_sessions (id, doc_id, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (record.id, record.doc_id, record.created_at, record.updated_at),
            )
        return record

    def list_chat_sessions(self, doc_id: str) -> list[ChatSessionRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, doc_id, created_at, updated_at
                FROM chat_sessions
                WHERE doc_id = ?
                ORDER BY updated_at DESC
                """,
                (doc_id,),
            ).fetchall()
        return [ChatSessionRecord(**dict(row)) for row in rows]

    def delete_chat_session(self, session_id: str) -> bool:
        """Delete a chat session and all its associated chats and retrieval steps."""
        with self._connect() as conn:
            # Delete retrieval steps linked to chats in this session
            conn.execute(
                """
                DELETE FROM retrieval_steps 
                WHERE chat_id IN (
                    SELECT id FROM chats WHERE session_id = ?
                )
                """,
                (session_id,)
            )
            # Delete chats in this session
            conn.execute("DELETE FROM chats WHERE session_id = ?", (session_id,))
            # Delete the session itself
            cur = conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            return cur.rowcount > 0

    def insert_chat(self, doc_id: str, session_id: str, question: str, answer: str) -> ChatRecord:
        now = _utc_now_iso()
        record = ChatRecord(
            id=str(uuid.uuid4()),
            session_id=session_id,
            doc_id=doc_id,
            question=question,
            answer=answer,
            created_at=now,
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO chats (id, session_id, doc_id, question, answer, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.session_id,
                    record.doc_id,
                    record.question,
                    record.answer,
                    record.created_at,
                ),
            )
            conn.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
                (now, session_id),
            )
        return record

    def list_chats(
        self, session_id: str, *, limit: int | None = None
    ) -> list[ChatRecord]:
        query = """
            SELECT id, session_id, doc_id, question, answer, created_at
            FROM chats
            WHERE session_id = ?
            ORDER BY created_at DESC
        """
        params: tuple[str, ...] | tuple[str, int] = (session_id,)
        if limit is not None:
            query += " LIMIT ?"
            params = (session_id, limit)
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [ChatRecord(**dict(row)) for row in rows]

    def get_chat(self, chat_id: str) -> ChatRecord:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, session_id, doc_id, question, answer, created_at
                FROM chats
                WHERE id = ?
                """,
                (chat_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Chat not found: {chat_id}")
        return ChatRecord(**dict(row))

    def insert_retrieval_step(
        self, record: RetrievalStepRecord
    ) -> RetrievalStepRecord:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO retrieval_steps (
                    chat_id, step_index, action, node_id, pages, reason
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record.chat_id,
                    record.step_index,
                    record.action,
                    record.node_id,
                    record.pages,
                    record.reason,
                ),
            )
            step_id = int(cursor.lastrowid)
        return RetrievalStepRecord(
            id=step_id,
            chat_id=record.chat_id,
            step_index=record.step_index,
            action=record.action,
            node_id=record.node_id,
            pages=record.pages,
            reason=record.reason,
        )

    def list_retrieval_steps(self, chat_id: str) -> list[RetrievalStepRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, chat_id, step_index, action, node_id, pages, reason
                FROM retrieval_steps
                WHERE chat_id = ?
                ORDER BY step_index, id
                """,
                (chat_id,),
            ).fetchall()
        return [RetrievalStepRecord(**dict(row)) for row in rows]

    def count_retrieval_steps(self, chat_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS count FROM retrieval_steps WHERE chat_id = ?",
                (chat_id,),
            ).fetchone()
        return int(row["count"])

    def delete_document(self, doc_id: str) -> None:
        """Delete a document and all associated data (DB rows + files).

        Cascading order:
            1. retrieval_steps (via chat IDs)
            2. chats
            3. nodes
            4. documents row
            5. uploaded PDF file
            6. document data directory (pages.jsonl, tree.json)
        """
        import shutil

        with self._connect() as conn:
            # Delete retrieval steps for all chats belonging to this document
            conn.execute(
                "DELETE FROM retrieval_steps WHERE chat_id IN "
                "(SELECT id FROM chats WHERE doc_id = ?)",
                (doc_id,),
            )
            conn.execute("DELETE FROM chats WHERE doc_id = ?", (doc_id,))
            conn.execute("DELETE FROM chat_sessions WHERE doc_id = ?", (doc_id,))
            conn.execute("DELETE FROM nodes WHERE doc_id = ?", (doc_id,))
            conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))

        # Remove uploaded PDF
        upload = self.upload_path(doc_id)
        if upload.exists():
            upload.unlink()

        # Remove document data directory (pages.jsonl, tree.json, etc.)
        doc_dir = self.document_dir(doc_id)
        if doc_dir.exists():
            shutil.rmtree(doc_dir, ignore_errors=True)

    def cleanup_orphan_records(self) -> dict[str, int]:
        """Remove chat and trace rows that no longer belong to live documents."""
        with self._connect() as conn:
            trace_cursor = conn.execute(
                """
                DELETE FROM retrieval_steps
                WHERE chat_id NOT IN (SELECT id FROM chats)
                   OR chat_id IN (
                       SELECT chats.id
                       FROM chats
                       LEFT JOIN documents ON documents.id = chats.doc_id
                       WHERE documents.id IS NULL
                   )
                """
            )
            chat_cursor = conn.execute(
                """
                DELETE FROM chats
                WHERE doc_id NOT IN (SELECT id FROM documents)
                """
            )
            session_cursor = conn.execute(
                """
                DELETE FROM chat_sessions
                WHERE doc_id NOT IN (SELECT id FROM documents)
                """
            )
        return {
            "retrieval_steps": int(trace_cursor.rowcount),
            "chats": int(chat_cursor.rowcount),
            "chat_sessions": int(session_cursor.rowcount),
        }

    def write_pages(self, doc_id: str, pages: list[dict[str, Any]]) -> None:
        path = self.pages_path(doc_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            for page in pages:
                file.write(json.dumps(page, ensure_ascii=False) + "\n")

    def read_pages(self, doc_id: str) -> list[dict[str, Any]]:
        path = self.pages_path(doc_id)
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def write_tree(self, doc_id: str, tree: dict[str, Any]) -> None:
        path = self.tree_path(doc_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(tree, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def read_tree(self, doc_id: str) -> dict[str, Any]:
        return json.loads(self.tree_path(doc_id).read_text(encoding="utf-8"))

    @contextlib.contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _migrate_documents_table(self, conn: sqlite3.Connection) -> None:
        existing_columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(documents)").fetchall()
        }
        migrations = {
            "progress_percent": "ALTER TABLE documents ADD COLUMN progress_percent INTEGER NOT NULL DEFAULT 0",
            "progress_stage": "ALTER TABLE documents ADD COLUMN progress_stage TEXT",
            "started_at": "ALTER TABLE documents ADD COLUMN started_at TEXT",
            "finished_at": "ALTER TABLE documents ADD COLUMN finished_at TEXT",
        }
        for column_name, sql in migrations.items():
            if column_name not in existing_columns:
                conn.execute(sql)
        conn.execute(
            """
            UPDATE documents
            SET progress_stage = COALESCE(progress_stage, status),
                started_at = COALESCE(started_at, created_at),
                progress_percent = CASE
                    WHEN status IN ('completed', 'failed') THEN 100
                    ELSE progress_percent
                END,
                finished_at = CASE
                    WHEN status IN ('completed', 'failed')
                    THEN COALESCE(finished_at, created_at)
                    ELSE finished_at
                END
            """
        )
