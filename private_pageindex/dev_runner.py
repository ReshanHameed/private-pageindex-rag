"""Start backend, frontend, Ollama, and optional MCP HTTP server for local development."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import httpx


@dataclass(frozen=True)
class DevService:
    name: str
    command: list[str]
    cwd: Path
    managed: bool = True


def is_ollama_reachable(base_url: str) -> bool:
    """Return True when the Ollama HTTP API responds."""
    url = f"{base_url.rstrip('/')}/api/tags"
    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.get(url)
            return response.status_code == 200
    except Exception:
        return False


def wait_for_ollama(base_url: str, timeout: float = 20.0) -> bool:
    """Poll until Ollama becomes reachable or the timeout expires."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if is_ollama_reachable(base_url):
            return True
        time.sleep(0.5)
    return False


def build_dev_services(
    *,
    project_root: Path,
    python_executable: str,
    host: str,
    port: int,
    mcp_host: str,
    mcp_port: int,
    with_frontend: bool = True,
    with_mcp_http: bool = True,
) -> list[DevService]:
    """Return the subprocess definitions for the dev stack."""
    services: list[DevService] = [
        DevService(
            name="backend",
            command=[
                python_executable,
                "-m",
                "uvicorn",
                "private_pageindex.web.app:app",
                "--reload",
                "--host",
                host,
                "--port",
                str(port),
            ],
            cwd=project_root,
        ),
    ]

    if with_frontend:
        npm = shutil.which("npm")
        if npm is None:
            raise RuntimeError(
                "npm was not found on PATH. Install Node.js or pass --no-frontend."
            )
        services.append(
            DevService(
                name="frontend",
                command=[npm, "run", "dev"],
                cwd=project_root / "frontend",
            )
        )

    if with_mcp_http:
        services.append(
            DevService(
                name="mcp-http",
                command=[
                    python_executable,
                    "-m",
                    "private_pageindex.cli",
                    "serve-mcp",
                    "--http",
                    "--host",
                    mcp_host,
                    "--port",
                    str(mcp_port),
                ],
                cwd=project_root,
            )
        )

    return services


def run_dev_stack(
    *,
    host: str | None = None,
    port: int | None = None,
    mcp_host: str | None = None,
    mcp_port: int | None = None,
    with_frontend: bool = True,
    with_mcp_http: bool = True,
    with_ollama: bool = True,
) -> None:
    """Spawn the dev services and keep them alive until interrupted."""
    from private_pageindex.config import get_settings

    settings = get_settings()
    project_root = Path(__file__).resolve().parent.parent
    srv_host = host or os.environ.get("HOST", "127.0.0.1")
    try:
        srv_port = port or int(os.environ.get("PORT", "8000"))
    except ValueError:
        srv_port = 8000
    http_host = mcp_host or settings.mcp_http_host
    http_port = mcp_port or settings.mcp_http_port
    ollama_url = settings.ollama_base_url

    try:
        services = build_dev_services(
            project_root=project_root,
            python_executable=sys.executable,
            host=srv_host,
            port=srv_port,
            mcp_host=http_host,
            mcp_port=http_port,
            with_frontend=with_frontend,
            with_mcp_http=with_mcp_http,
        )
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    processes: list[tuple[str, subprocess.Popen[bytes], bool]] = []
    creationflags = 0
    if sys.platform == "win32" and hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

    print("Starting Private PageIndex RAG dev stack...")
    print()

    if with_ollama:
        if is_ollama_reachable(ollama_url):
            print(f"  = ollama: already running at {ollama_url}")
        else:
            ollama_bin = shutil.which("ollama")
            if ollama_bin is None:
                print(
                    f"  ! ollama: not found on PATH and {ollama_url} is unreachable",
                    file=sys.stderr,
                )
                print(
                    "    Install Ollama or start it manually, then rerun dev.",
                    file=sys.stderr,
                )
            else:
                print(f"  + ollama: {ollama_bin} serve")
                ollama_proc = subprocess.Popen(
                    [ollama_bin, "serve"],
                    cwd=project_root,
                    creationflags=creationflags,
                )
                processes.append(("ollama", ollama_proc, True))
                print(f"    waiting for Ollama at {ollama_url}...")
                if not wait_for_ollama(ollama_url):
                    print(
                        "    Ollama did not become reachable in time. Stopping.",
                        file=sys.stderr,
                    )
                    for _, proc, _ in reversed(processes):
                        if proc.poll() is None:
                            proc.terminate()
                    raise SystemExit(1)
                print("    Ollama is ready.")

    for service in services:
        print(f"  + {service.name}: {' '.join(service.command)}")
        proc = subprocess.Popen(
            service.command,
            cwd=service.cwd,
            creationflags=creationflags,
        )
        processes.append((service.name, proc, service.managed))

    print()
    if with_ollama:
        print(f"  Ollama:       {ollama_url}")
    print(f"  Backend API:  http://{srv_host}:{srv_port}")
    if with_frontend:
        print("  Frontend UI:  http://localhost:5173")
    if with_mcp_http:
        print(f"  MCP HTTP:     http://{http_host}:{http_port}/mcp")
    print("  stdio MCP:    per-agent only (Claude Desktop / Cursor launch their own)")
    print()
    print("Press Ctrl+C to stop managed services.")
    print()

    def stop_all() -> None:
        print("\nStopping dev services...")
        for name, proc, managed in reversed(processes):
            if managed and proc.poll() is None:
                proc.terminate()
        for name, proc, managed in processes:
            if not managed or proc.poll() is not None:
                continue
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2)

    try:
        while True:
            for name, proc, _managed in processes:
                code = proc.poll()
                if code is not None:
                    print(
                        f"\n{name} exited with code {code}. Stopping remaining services...",
                        file=sys.stderr,
                    )
                    stop_all()
                    raise SystemExit(code if code != 0 else 1)
            time.sleep(0.5)
    except KeyboardInterrupt:
        stop_all()
