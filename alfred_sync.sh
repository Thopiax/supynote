#!/bin/bash

# Simple Alfred Sync Script
# Usage: ./alfred_sync.sh [week|2weeks|month|all]

# Hard-coded paths for Alfred environment
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$HOME/.cargo/bin"

# Change to script directory
cd "$(dirname "$0")"

# Configuration
TIME_RANGE="${1:-week}"
OUTPUT_DIR="$HOME/Documents/Supernote"

# Find uv command
if [ -x "$HOME/.local/bin/uv" ]; then
    UV="$HOME/.local/bin/uv"
elif [ -x "$HOME/.cargo/bin/uv" ]; then
    UV="$HOME/.cargo/bin/uv"
elif [ -x "/opt/homebrew/bin/uv" ]; then
    UV="/opt/homebrew/bin/uv"
elif [ -x "$HOME/.pyenv/shims/uv" ]; then
    UV="$HOME/.pyenv/shims/uv"
elif command -v uv &> /dev/null; then
    UV="uv"
else
    echo "❌ uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

# Run sync
echo "🔄 Syncing Supernote ($TIME_RANGE)..."

$UV run supynote --output "$OUTPUT_DIR" download Note \
    --time-range "$TIME_RANGE" \
    --convert-pdf \
    --merge-by-date \
    --async \
    --workers 30 \
    --conversion-workers 16

if [ $? -eq 0 ]; then
    echo "✅ Sync completed!"
    
    # Try to send notification
    osascript -e 'display notification "Supernote sync completed" with title "Supernote"' 2>/dev/null || true
else
    echo "❌ Sync failed."
    osascript -e 'display notification "Supernote sync failed" with title "Supernote"' 2>/dev/null || true
    exit 1
fi