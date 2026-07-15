# Start backend, frontend, and MCP HTTP server together.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
& "$Root\.venv\Scripts\python.exe" -m private_pageindex.cli dev @args
