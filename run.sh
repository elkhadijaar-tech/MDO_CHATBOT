#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
echo "=== MDO CHATBOT - Assistant MDO / ESTC Casablanca ==="
PY=python3
command -v "$PY" >/dev/null 2>&1 || PY=python
if ! command -v "$PY" >/dev/null 2>&1; then echo "[ERREUR] Python introuvable (3.10+ requis)."; exit 1; fi
"$PY" -c 'import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)' || { echo "[ERREUR] Python 3.10+ requis."; exit 1; }
[ -d .venv ] || "$PY" -m venv .venv
. .venv/bin/activate
python -m pip install --disable-pip-version-check -q -r requirements.txt
python -m app.setup
echo "Adresse : http://127.0.0.1:5000"
python -m app
