#!/bin/bash
set -euo pipefail

# Only run in remote Claude Code on the web environments
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

echo '{"async": true, "asyncTimeout": 300000}'

# Install ffmpeg
if ! command -v ffmpeg &> /dev/null; then
  apt-get update -qq 2>/dev/null || true
  apt-get install -y -qq ffmpeg 2>/dev/null || true
fi

# Install system docopt (required by kokoro's dependency gruut)
apt-get install -y -qq python3-docopt 2>/dev/null || true

# Install Python dependencies
pip install --quiet \
  google-api-python-client \
  google-auth-httplib2 \
  google-auth-oauthlib \
  requests \
  Pillow \
  numpy \
  edge-tts \
  soundfile

# Kokoro TTS (optional — pipeline falls back to Edge TTS if unavailable)
pip install --quiet kokoro 2>/dev/null || true

# Set UTF-8 encoding to prevent encoding crashes
echo 'export PYTHONIOENCODING=utf-8' >> "$CLAUDE_ENV_FILE"
echo 'export PYTHONUTF8=1' >> "$CLAUDE_ENV_FILE"

echo "Session setup complete."
