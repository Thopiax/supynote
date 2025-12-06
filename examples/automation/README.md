# Automation Examples

This directory contains example scripts for automating Supynote workflows.

## Quick Setup

### 1. Configure Environment Variables

Copy `.env.example` to `.env` and configure your values:

```bash
cd examples/automation
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# For sync_from_server.sh - syncing from remote Supernote Private Cloud
SUPYNOTE_REMOTE_SERVER=user@your-server.com:/path/to/supernote_data
SUPYNOTE_USER_EMAIL=your-email@example.com

# For sync_from_lan.sh - syncing directly from device (optional)
# SUPYNOTE_IP=192.168.1.100

# Output directories (optional - uses these defaults)
SUPYNOTE_OUTPUT_DIR=$HOME/Documents/Supernote
SUPYNOTE_CACHE_DIR=$HOME/.cache/supynote
```

**Important:** `SUPYNOTE_CACHE_DIR` is where `.note` files are temporarily stored during sync. Default is `~/.cache/supynote/Note/`. The script automatically creates this directory.

### 2. Setup SSH Access (for sync_from_server.sh only)

Add your SSH key to macOS Keychain to avoid password prompts:

```bash
# Add SSH config
cat >> ~/.ssh/config << 'EOF'
Host supernote-server
    HostName your-server.com
    User your-username
    UseKeychain yes
    AddKeysToAgent yes
EOF

# Add key to Keychain (enter passphrase once)
ssh-add --apple-use-keychain ~/.ssh/id_ed25519

# Test connection
ssh supernote-server "echo Connection successful"
```

### 3. Install Modern rsync (for sync_from_server.sh)

The sync script uses `--info=progress2` which requires rsync 3.1+. macOS ships with rsync 2.6.9, so install the modern version:

```bash
brew install rsync
```

The script will automatically use the Homebrew version if available.

### 4. Run the Scripts

```bash
# Sync from server
./sync_from_server.sh

# Or sync from LAN device
./sync_from_lan.sh week
```

### 5. Automate with launchd (macOS)

To run the sync automatically every hour:

```bash
# Copy the launchd plist to ~/Library/LaunchAgents/
cp com.supynote.sync.plist ~/Library/LaunchAgents/

# Load the agent (starts immediately and runs hourly)
launchctl load ~/Library/LaunchAgents/com.supynote.sync.plist

# Check if it's running
launchctl list | grep supynote

# View logs
tail -f ~/Library/Logs/supynote-sync.log
```

**To stop automatic sync:**
```bash
launchctl unload ~/Library/LaunchAgents/com.supynote.sync.plist
```

**To change the schedule:** Edit `com.supynote.sync.plist` and change `StartInterval`:
- 3600 = every hour
- 1800 = every 30 minutes
- 7200 = every 2 hours

Then reload:
```bash
launchctl unload ~/Library/LaunchAgents/com.supynote.sync.plist
launchctl load ~/Library/LaunchAgents/com.supynote.sync.plist
```

## Scripts

### sync_from_lan.sh
Syncs directly from your Supernote device on local network (LAN).

**Use when:** Your Supernote is on the same WiFi network as your computer.

**Features:**
- Direct device connection over LAN
- Time-range filtering (week, 2weeks, month, all)
- PDF conversion and OCR
- Desktop notifications
- Can be triggered from Alfred workflow

**Usage:**
```bash
./sync_from_lan.sh [time_range]

# Examples:
./sync_from_lan.sh week      # Last week only
./sync_from_lan.sh 2weeks    # Last 2 weeks (default)
./sync_from_lan.sh all       # Everything
```

### sync_from_server.sh
Syncs from a Supernote Private Cloud server (remote rsync).

**Use when:** You have a Supernote Private Cloud server running and want to sync from it instead of directly from the device.

**Features:**
- Rsync from remote server over SSH
- Incremental sync (only changed files)
- Progress bar showing transfer status
- Automatic PDF conversion and markdown generation
- Only processes files that changed since last sync

**Usage:**
```bash
# Configure .env first with your remote server details
./sync_from_server.sh
```

**Configuration in `.env`:**
```bash
# SSH connection format: user@hostname:/path/to/supernote_data
SUPYNOTE_REMOTE_SERVER=user@your-server.com:/path/to/supernote_data
SUPYNOTE_USER_EMAIL=your-email@example.com
```

## Choosing the Right Script

| Scenario | Script to Use |
|----------|---------------|
| Supernote on same WiFi | `sync_from_lan.sh` |
| Remote server, always-on sync | `sync_from_server.sh` |
| Alfred hotkey trigger | `sync_from_lan.sh` |
| Automated cron job | `sync_from_server.sh` |

## Integration with Alfred

To integrate with Alfred on macOS:

1. Create a new Workflow in Alfred
2. Add a "Run Script" action with:
   ```bash
   cd /path/to/supynote-cli/examples/automation
   ./sync_from_lan.sh 2weeks
   ```
3. Add a "Post Notification" action to display the result
4. Assign a hotkey to trigger the workflow

The script outputs a status message suitable for Alfred's notification system.
