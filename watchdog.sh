#!/bin/bash

# kvchClaw Watchdog
# Monitors the bot and restarts if it dies

LOGFILE="$HOME/myclaw/watchdog.log"
BOTDIR="$HOME/myclaw"
PYTHON="$HOME/myclaw/venv/bin/python"
SCRIPT="$BOTDIR/main.py"
MAX_RESTARTS=10
RESTART_COUNT=0
RESTART_WINDOW=3600  # 1 hour in seconds
WINDOW_START=$(date +%s)

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOGFILE"
}

log "🚀 kvchClaw Watchdog Started"
log "Monitoring: $SCRIPT"
while true; do
    # Check if we've exceeded restart limit in window
    NOW=$(date +%s)
    ELAPSED=$((NOW - WINDOW_START))
    
    if [ $ELAPSED -gt $RESTART_WINDOW ]; then
        # Reset window
        RESTART_COUNT=0
        WINDOW_START=$NOW
        log "↺ Restart counter reset"
    fi
    
    if [ $RESTART_COUNT -ge $MAX_RESTARTS ]; then
        log "❌ Too many restarts ($MAX_RESTARTS in 1 hour). Stopping watchdog."
        log "Please check the logs and fix the issue manually."
        exit 1
    fi

    log "▶ Starting kvchClaw..."
    
    # Run the bot
    cd "$BOTDIR"
    source venv/bin/activate
    "$PYTHON" "$SCRIPT" >> "$LOGFILE" 2>&1
    EXIT_CODE=$?
    
   log "⚠️ kvchClaw stopped with exit code: $EXIT_CODE"
    
    # If network error — wait longer before restart
    if [ $EXIT_CODE -eq 1 ]; then
        log "🌐 Possible network issue — waiting 30 seconds..."
        sleep 30
    else
        sleep 5
    fi
    
    RESTART_COUNT=$((RESTART_COUNT + 1))
    log "↺ Restart $RESTART_COUNT/$MAX_RESTARTS"
done
