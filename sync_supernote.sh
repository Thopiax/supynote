#!/bin/bash

# Sync Supernote Script for Alfred
# This script sets up the proper environment and syncs Supernote files

# Set up PATH to include common locations for uv and Python
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export PATH="$HOME/.local/bin:$PATH"
export PATH="$HOME/.cargo/bin:$PATH"
export PATH="/opt/homebrew/bin:$PATH"

# Set working directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Configuration
TIME_RANGE="${1:-week}"  # Default to week if not specified
OUTPUT_DIR="$HOME/Documents/Supernote"  # Final processed output
CACHE_DIR="$SCRIPT_DIR/data"  # Raw files cache
NOTIFICATION_TITLE="Supernote Sync"

# Function to send notification
notify() {
    local message="$1"
    local subtitle="$2"
    
    # Try different notification methods
    if command -v osascript &> /dev/null; then
        osascript -e "display notification \"$message\" with title \"$NOTIFICATION_TITLE\" subtitle \"$subtitle\""
    elif command -v terminal-notifier &> /dev/null; then
        terminal-notifier -title "$NOTIFICATION_TITLE" -subtitle "$subtitle" -message "$message"
    else
        echo "$NOTIFICATION_TITLE: $message"
    fi
}

# Find uv command in common locations
if [ -x "$HOME/.local/bin/uv" ]; then
    UV_CMD="$HOME/.local/bin/uv"
elif [ -x "$HOME/.cargo/bin/uv" ]; then
    UV_CMD="$HOME/.cargo/bin/uv"
elif [ -x "/opt/homebrew/bin/uv" ]; then
    UV_CMD="/opt/homebrew/bin/uv"
elif [ -x "$HOME/.pyenv/shims/uv" ]; then
    UV_CMD="$HOME/.pyenv/shims/uv"
elif command -v uv &> /dev/null; then
    UV_CMD="uv"
else
    notify "❌ uv command not found" "Please install uv first"
    echo "❌ uv command not found. Please install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if Python/supynote is available
if ! $UV_CMD run supynote --help &> /dev/null; then
    notify "⚙️ Setting up Supynote..." "Installing dependencies"
    $UV_CMD sync
    if [ $? -ne 0 ]; then
        notify "❌ Failed to install dependencies" "Check the logs"
        exit 1
    fi
fi

# Start sync
notify "🔄 Starting sync..." "Time range: $TIME_RANGE"
echo "🔄 Starting Supernote sync (time range: $TIME_RANGE)..."

# Create directories if they don't exist
mkdir -p "$OUTPUT_DIR"
mkdir -p "$CACHE_DIR"

# Run the sync command with specified time range
# Raw files go to cache, processed files go to final output
$UV_CMD run supynote --output "$CACHE_DIR" download Note \
    --time-range "$TIME_RANGE" \
    --convert-pdf \
    --merge-by-date \
    --ocr \
    --async \
    --workers 30 \
    --conversion-workers 16 \
    --processed-output "$OUTPUT_DIR" 2>&1

# Check the exit status
if [ $? -eq 0 ]; then
    # Count files
    PDF_COUNT=$(find "$OUTPUT_DIR/pdfs" -name "*.pdf" 2>/dev/null | wc -l | tr -d ' ')
    notify "✅ Sync completed successfully" "$PDF_COUNT merged PDFs created"
    echo "✅ Sync completed successfully!"
    echo "📁 Raw files cached in: $CACHE_DIR"
    echo "📚 Processed files in: $OUTPUT_DIR"
    echo "  📄 Merged PDFs: $OUTPUT_DIR/pdfs"
    echo "  📝 Markdown files: $OUTPUT_DIR/markdowns"
else
    notify "❌ Sync failed" "Check the terminal for details"
    echo "❌ Sync failed. Check the error messages above."
    exit 1
fi