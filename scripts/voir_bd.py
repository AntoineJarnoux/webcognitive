#!/usr/bin/env python3
"""
Affiche le contenu de la base ChromaDB : nombre de segments, puis un segment
avec son texte, ses métadonnées et le début de son vecteur.

Usage :
    python scripts/voir_bd.py                 # le segment html01_0087 (DNS)
    python scripts/voir_bd.py pdf02_0014      # un autre segment
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from webcognitive import config, vectordb  # noqa: E402

chunk_id = sys.argv[1] if len(sys.argv) > 1 else "html01_0087"
col = vectordb.get_collection(vectordb.get_client())
if col is None:
    sys.exit("Base vide : lancez python scripts/build_vectordb.py")

print(f"Base : {config.VECTORDB_DIR}")
print(f"Collection « {col.name} » : {col.count()} segments\n")
r = col.get(ids=[chunk_id], include=["documents", "metadatas", "embeddings"])
if not r["ids"]:
    sys.exit(f"Segment inconnu : {chunk_id}")
vector = r["embeddings"][0]
print(f"id          : {chunk_id}")
print(f"texte       : {r['documents'][0]}\n")
print("métadonnées :")
for key, value in r["metadatas"][0].items():
    print(f"   {key:<12} {value}")
print(f"\nvecteur     : {len(vector)} coordonnées")
print("   " + ", ".join(f"{x:.4f}" for x in vector[:8]) + ", …")
