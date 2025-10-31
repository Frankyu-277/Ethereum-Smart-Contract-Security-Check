#!/usr/bin/env bash
set -euo pipefail
echo "== solc doctor =="
echo "[whoami] $(whoami)"
echo "[HOME] $HOME"
echo "[PATH] $PATH"
echo "---- which solc ----"
command -v solc || true
echo "---- solc --version ----"
solc --version || true
echo "---- solc-select versions ----"
solc-select versions || true
echo "---- ~/.solc-select ----"
ls -l "$HOME/.solc-select" || true
echo "---- ~/.solc-select/current ----"
ls -l "$HOME/.solc-select/current" || true
echo "---- ~/.solc-select/artifacts ----"
ls -l "$HOME/.solc-select/artifacts" || true
