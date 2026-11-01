#!/usr/bin/env bash
# Installation automatique de WebCognitive Engine (Linux / macOS)
#
# Lancement :  bash install.sh            (ou : bash install.sh llama3.2:3b pour un modèle plus léger)
# Chaque étape est sautée si elle est déjà faite : on peut relancer le script sans risque.
set -euo pipefail
cd "$(dirname "$0")"
MODELE="${1:-mistral}"

etape() { printf '\n\033[36m[%s/6] %s\033[0m\n' "$1" "$2"; }
ok()    { printf '      \033[32mOK\033[0m  %s\n' "$1"; }
arret() { printf '\n  \033[31mERREUR :\033[0m %s\n' "$1"; exit 1; }

echo "=== Installation de WebCognitive Engine ==="

etape 1 "Python"
PYTHON=""
for candidat in python3.12 python3 python; do
  if command -v "$candidat" >/dev/null 2>&1 && "$candidat" -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then
    PYTHON="$candidat"; break
  fi
done
[ -n "$PYTHON" ] || arret "Python 3.10 ou plus est introuvable (https://www.python.org/downloads/)."
ok "$($PYTHON --version)"

etape 2 "Environnement virtuel et dépendances"
[ -x .venv/bin/python ] || "$PYTHON" -m venv .venv
.venv/bin/python -m pip install --upgrade pip --quiet
.venv/bin/python -m pip install -r requirements.txt --quiet || arret "installation des dépendances impossible"
ok "dépendances installées"

etape 3 "Ollama (LLM local)"
if ! command -v ollama >/dev/null 2>&1; then
  if [ "$(uname)" = "Linux" ]; then
    echo "      installation d'Ollama…"; curl -fsSL https://ollama.com/install.sh | sh
  else
    arret "Ollama n'est pas installé : https://ollama.com/download (ou : brew install ollama), puis relancez."
  fi
fi
if ! curl -fs http://127.0.0.1:11434/api/tags >/dev/null; then
  (ollama serve >/dev/null 2>&1 &)
  for _ in $(seq 30); do curl -fs http://127.0.0.1:11434/api/tags >/dev/null && break; sleep 1; done
fi
curl -fs http://127.0.0.1:11434/api/tags >/dev/null || arret "Ollama ne démarre pas (essayez : ollama serve)."
ok "Ollama répond"

etape 4 "Modèle de langage « $MODELE »"
ollama pull "$MODELE" || arret "téléchargement du modèle impossible"
ok "modèle prêt"

etape 5 "Vecteurs du corpus"
if [ ! -f data/embeddings/embeddings.npy ]; then
  echo "      calcul en cours : 5 à 10 minutes…"
  .venv/bin/python scripts/build_embeddings.py || arret "le calcul des vecteurs a échoué"
fi
ok "vecteurs prêts"

etape 6 "Base vectorielle ChromaDB"
.venv/bin/python scripts/build_vectordb.py || arret "le remplissage de la base a échoué"
ok "base prête"

printf '\n\033[32m=== Installation terminée ===\033[0m\n'
[ "$MODELE" = "mistral" ] || echo "Modèle choisi : export WEBCOGNITIVE_LLM=$MODELE avant de lancer."
echo "Pour démarrer : bash lancer.sh   puis ouvrir http://127.0.0.1:8000/"
