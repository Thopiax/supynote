#!/bin/bash

# Sync Supernote from LAN Device Script
# Downloads directly from Supernote device on local network
# Usage: ./sync_from_lan.sh [time_range]
# Requires: .env file with configuration

# Set up PATH to include common locations for uv and Python
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export PATH="$HOME/.local/bin:$PATH"
export PATH="$HOME/.cargo/bin:$PATH"
export PATH="/opt/homebrew/bin:$PATH"

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

# Configuration (with defaults from .env or fallbacks)
TIME_RANGE="${1:-2weeks}"  # Default to 2weeks if not specified
OUTPUT_DIR="${SUPYNOTE_OUTPUT_DIR:-$HOME/Documents/Supernote}"
CACHE_DIR="${SUPYNOTE_CACHE_DIR:-$SCRIPT_DIR/../../data}"
LOG_FILE="$SCRIPT_DIR/sync.log"

# Function to output notification for Alfred
notify_alfred() {
    # Output the message directly for Alfred to capture
    echo -n "$1"
}

# Function to log with timestamp
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Start logging
log_message "Starting sync with time range: $TIME_RANGE"

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
    notify_alfred "❌ Sync Failed: uv command not found"
    log_message "ERROR: uv command not found"
    exit 1
fi

# Navigate to project root (two levels up from script directory)
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# Check if Python/supynote is available
if ! $UV_CMD run supynote --help &> /dev/null 2>&1; then
    notify_alfred "⚙️ Installing Supynote dependencies..."
    log_message "Installing dependencies..."
    $UV_CMD sync >> "$LOG_FILE" 2>&1
    if [ $? -ne 0 ]; then
        notify_alfred "❌ Sync Failed: Could not install dependencies"
        log_message "ERROR: Failed to install dependencies"
        exit 1
    fi
fi

# Create directories if they don't exist
mkdir -p "$OUTPUT_DIR"
mkdir -p "$CACHE_DIR"

# Track start time
START_TIME=$(date +%s)

# Run the sync command with specified time range
log_message "Running supynote download command..."
$UV_CMD run supynote --output "$CACHE_DIR" download Note \
    --time-range "$TIME_RANGE" \
    --convert-pdf \
    --merge-by-date \
    --ocr \
    --async \
    --workers 30 \
    --conversion-workers 16 \
    --processed-output "$OUTPUT_DIR" >> "$LOG_FILE" 2>&1

SYNC_EXIT_CODE=$?

# Calculate elapsed time
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
MINUTES=$((ELAPSED / 60))
SECONDS=$((ELAPSED % 60))

# Check the exit status and prepare notification
if [ $SYNC_EXIT_CODE -eq 0 ]; then
    # Count files for status details
    PDF_COUNT=$(find "$OUTPUT_DIR/pdfs" -name "*.pdf" -mmin -$((ELAPSED/60 + 1)) 2>/dev/null | wc -l | tr -d ' ')
    MD_COUNT=$(find "$OUTPUT_DIR/markdowns" -name "*.md" -mmin -$((ELAPSED/60 + 1)) 2>/dev/null | wc -l | tr -d ' ')

    # Format time string
    if [ $MINUTES -gt 0 ]; then
        TIME_STR="${MINUTES}m ${SECONDS}s"
    else
        TIME_STR="${SECONDS}s"
    fi

    # Create success notification
    if [ $PDF_COUNT -gt 0 ] || [ $MD_COUNT -gt 0 ]; then
        notify_alfred "✅ Supernote Synced: ${PDF_COUNT} PDFs, ${MD_COUNT} markdowns (${TIME_STR})"
    else
        notify_alfred "✅ Supernote Synced: No new files in ${TIME_RANGE} (${TIME_STR})"
    fi

    log_message "SUCCESS: Sync completed. PDFs: $PDF_COUNT, Markdowns: $MD_COUNT, Time: $TIME_STR"
else
    # Try to extract error details from log
    ERROR_DETAIL=$(tail -n 5 "$LOG_FILE" | grep -E "Error|Failed|Exception" | head -n 1 | cut -c 1-50)

    if [ -n "$ERROR_DETAIL" ]; then
        notify_alfred "❌ Supernote Sync Failed: ${ERROR_DETAIL}..."
    else
        notify_alfred "❌ Supernote Sync Failed (exit code: ${SYNC_EXIT_CODE})"
    fi

    log_message "ERROR: Sync failed with exit code $SYNC_EXIT_CODE"
    exit 1
fi
