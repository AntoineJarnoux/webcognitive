#!/usr/bin/env python3
"""
Étape 4 : lance l'API REST en local.

Usage :
    python scripts/serve_api.py              # http://127.0.0.1:8000/docs
    python scripts/serve_api.py --reload     # redémarre à chaque modification du code
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

import uvicorn  # noqa: E402

from webcognitive import config  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Serveur de l'API WebCognitive.")
    parser.add_argument("--host", default=config.API_HOST)
    parser.add_argument("--port", type=int, default=config.API_PORT)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    print(f"Documentation interactive : http://{args.host}:{args.port}/docs")
    uvicorn.run("webcognitive.api:app", host=args.host, port=args.port, reload=args.reload,
                app_dir=str(SRC), reload_dirs=[str(SRC)] if args.reload else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
