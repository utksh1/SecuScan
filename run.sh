#!/bin/zsh
set -euo pipefail

cd "$(dirname "$0")/backend"
mkdir -p ../data

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

uvicorn secuscan.api:app --host 127.0.0.1 --port 8081

