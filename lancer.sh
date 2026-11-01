#!/usr/bin/env bash
# Démarre WebCognitive Engine (Linux / macOS) puis ouvrez http://127.0.0.1:8000/
cd "$(dirname "$0")"
[ -x .venv/bin/python ] || { echo "Lancez d'abord : bash install.sh"; exit 1; }
curl -fs http://127.0.0.1:11434/api/tags >/dev/null || (ollama serve >/dev/null 2>&1 &)
.venv/bin/python scripts/serve_api.py
