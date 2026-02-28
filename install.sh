#!/usr/bin/env bash
set -euo pipefail

REPO="https://github.com/stephen-kruger/OpenClawPlaylister.git"
SKILL_DIR="${HOME}/.openclaw/workspace/skills/playlister"

echo "Installing playlister skill for OpenClaw..."

if [ -d "$SKILL_DIR" ]; then
  echo "  Updating existing installation at ${SKILL_DIR}..."
  git -C "$SKILL_DIR" pull --ff-only
else
  echo "  Cloning into ${SKILL_DIR}..."
  mkdir -p "$(dirname "$SKILL_DIR")"
  git clone "$REPO" "$SKILL_DIR"
fi

if command -v openclaw &>/dev/null; then
  echo "  Restarting OpenClaw gateway..."
  openclaw gateway restart
else
  echo "  Note: 'openclaw' not found on PATH — restart the gateway manually."
fi

echo ""
echo "✓ playlister installed. Ask your OpenClaw agent to 'set up my podcast playlist' to get started."

