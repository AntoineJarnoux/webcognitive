#!/usr/bin/env python3
"""
Lance l'application en local : API REST (étapes 4-5) et interface web (étape 6).

Usage :
    python scripts/serve_api.py              # interface : http://127.0.0.1:8000/  ·  API : /docs
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
    print(f"Interface web             : http://{args.host}:{args.port}/")
    print(f"Documentation de l'API    : http://{args.host}:{args.port}/docs")
    uvicorn.run("webcognitive.api:app", host=args.host, port=args.port, reload=args.reload,
                app_dir=str(SRC), reload_dirs=[str(SRC)] if args.reload else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
