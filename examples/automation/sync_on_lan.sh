#!/bin/bash
# Auto-sync wrapper: gate by trusted SSID, dedupe with flock, then invoke sync_from_lan.sh.
#
# Env (via .env next to this script, or shell):
#   SUPYNOTE_TRUSTED_SSIDS  Comma-separated SSID allowlist (e.g. "HomeWifi,Office")
#   SUPYNOTE_DEVICE_IP      Optional: skip discovery, use this IP
#   SUPYNOTE_SYNC_INTERFACE Network interface (default: en0)
#
# Exit codes: 0 = synced, 10 = untrusted SSID, 11 = device not found, 12 = already running.

set -u

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
[ -f "$SCRIPT_DIR/.env" ] && source "$SCRIPT_DIR/.env"

LOG_FILE="${SUPYNOTE_SYNC_LOG:-$SCRIPT_DIR/sync.log}"
LOCK_FILE="${TMPDIR:-/tmp}/supynote-sync.lock"
IFACE="${SUPYNOTE_SYNC_INTERFACE:-en0}"
TIME_RANGE="${1:-2weeks}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"; }

# 1. SSID gate
if [ -z "${SUPYNOTE_TRUSTED_SSIDS:-}" ]; then
    log "ABORT: SUPYNOTE_TRUSTED_SSIDS not set"
    exit 10
fi

CURRENT_SSID="$(ipconfig getsummary "$IFACE" 2>/dev/null | awk -F 'SSID : ' '/SSID : / {print $2; exit}')"
if [ -z "$CURRENT_SSID" ]; then
    log "ABORT: could not read SSID on $IFACE (Location Services?)"
    exit 10
fi

case ",$SUPYNOTE_TRUSTED_SSIDS," in
    *",$CURRENT_SSID,"*) ;;
    *)
        log "ABORT: SSID '$CURRENT_SSID' not in allowlist"
        exit 10
        ;;
esac

# 2. Single-flight via flock (non-blocking)
exec 9>"$LOCK_FILE"
if ! /usr/bin/flock -n 9; then
    log "ABORT: another sync already running"
    exit 12
fi

# 3. Quick device reachability check (skip full LAN scan if IP pinned)
if [ -n "${SUPYNOTE_DEVICE_IP:-}" ]; then
    if ! /usr/bin/nc -z -w 2 "$SUPYNOTE_DEVICE_IP" 8089 2>/dev/null; then
        log "ABORT: device $SUPYNOTE_DEVICE_IP:8089 unreachable"
        exit 11
    fi
fi

# 4. Hand off to existing sync script
log "SSID '$CURRENT_SSID' trusted — running sync ($TIME_RANGE)"
exec "$SCRIPT_DIR/sync_from_lan.sh" "$TIME_RANGE"
