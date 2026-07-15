#!/usr/bin/env bash
# Start backend, frontend, and MCP HTTP server together.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
exec "$ROOT/.venv/bin/python" -m private_pageindex.cli dev "$@"
