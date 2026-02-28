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
echo "✓ playlister installed."
echo ""
echo "┌─────────────────────────────────────────────────────────────────┐"
echo "│              Next step: connect your Spotify account            │"
echo "└─────────────────────────────────────────────────────────────────┘"
echo ""
echo "  1. Go to https://developer.spotify.com/dashboard and create an app."
echo "     Set the Redirect URI to:  https://pulse.ae:8888/callback"
echo ""
echo "  2. On the 'Users and Access' tab, add your own Spotify email so"
echo "     the app has permission to create playlists."
echo ""
echo "  3. Run the setup command:"
echo "     python3 ${SKILL_DIR}/scripts/podcast_playlist.py setup"
echo ""
echo "     You will be prompted to:"
echo "       a) Enter your Client ID and Client Secret"
echo "       b) Open an authorization URL in your browser"
echo "       c) Paste the redirect URL back into the terminal"
echo ""
echo "  4. Add your first topic and build your playlist:"
echo "     python3 ${SKILL_DIR}/scripts/podcast_playlist.py add-topic \"machine learning\""
echo "     python3 ${SKILL_DIR}/scripts/podcast_playlist.py refresh"
echo ""
echo "  Or just ask your OpenClaw agent: 'set up my podcast playlist'"
echo ""

