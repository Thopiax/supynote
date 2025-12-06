#!/bin/bash
set -euo pipefail

# Sync Supernote from Remote Server Script
# Usage: ./sync_from_server.sh
# Requires: .env file with SUPYNOTE_REMOTE_SERVER and SUPYNOTE_USER_EMAIL configured

# Set working directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Load environment variables
if [ -f "$SCRIPT_DIR/.env" ]; then
    source "$SCRIPT_DIR/.env"
else
    echo "❌ Error: .env file not found. Copy .env.example to .env and configure."
    exit 1
fi

# Verify required environment variables
if [ -z "${SUPYNOTE_REMOTE_SERVER:-}" ]; then
    echo "❌ Error: SUPYNOTE_REMOTE_SERVER not set in .env"
    exit 1
fi

if [ -z "${SUPYNOTE_USER_EMAIL:-}" ]; then
    echo "❌ Error: SUPYNOTE_USER_EMAIL not set in .env"
    exit 1
fi

# Configuration from environment with defaults
REMOTE="${SUPYNOTE_REMOTE_SERVER}/${SUPYNOTE_USER_EMAIL}/Supernote/Note/"
LOCAL_DIR="${SUPYNOTE_CACHE_DIR:-$HOME/.cache/supynote}/Note/"
OUTPUT_DIR="${SUPYNOTE_OUTPUT_DIR:-$HOME/Documents/Supernote}"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "🔄 Syncing from server..."

# Create local directory if it doesn't exist
mkdir -p "$LOCAL_DIR"

# Sync only .note files from server (skip PDFs/markdowns to save bandwidth)
# --info=progress2 shows overall progress instead of per-file (requires rsync 3.1+)
# Use Homebrew rsync if available, fallback to system rsync
RSYNC_CMD="/opt/homebrew/bin/rsync"
if [ ! -x "$RSYNC_CMD" ]; then
    RSYNC_CMD="rsync"
fi

$RSYNC_CMD -avz --info=progress2 \
    --include='*.note' \
    --include='*/' \
    --exclude='*' \
    "${REMOTE}" "${LOCAL_DIR}"

echo ""
echo "📝 Converting files to PDF..."

cd "$PROJECT_ROOT"

# Convert files with parallel workers (PDFs stay alongside .note files in LOCAL_DIR)
# The CLI automatically skips files with up-to-date PDFs
uv run supynote convert "${LOCAL_DIR}" \
    --workers 16

# Merge all PDFs by date and create markdown files
# Note: Merge runs on LOCAL_DIR where both .note and .pdf files exist
echo ""
echo "📅 Merging PDFs by date and creating markdown files..."
uv run supynote merge "${LOCAL_DIR}" \
    --pdf-output "${OUTPUT_DIR}/pdfs" \
    --markdown-output "${OUTPUT_DIR}/markdowns"

echo ""
echo "✅ Complete!"
echo "📁 PDFs:      ${OUTPUT_DIR}/pdfs"
echo "📝 Markdowns: ${OUTPUT_DIR}/markdowns"
