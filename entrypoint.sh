#!/bin/bash

# Default sleep interval is 300 seconds (5 minutes), can be overridden by environment variable
SLEEP_INTERVAL=${SCAN_INTERVAL_SECONDS:-300}

echo "Starting HostPing Bot..."
echo "Base scan interval set to $SLEEP_INTERVAL seconds."

while true; do
    echo "[$(date)] Running spider..."
    scrapy crawl dynamic_spider
    
    # Calculate a random jitter between -30 and +60 seconds to bypass pattern detection
    JITTER=$(( (RANDOM % 91) - 30 ))
    CURRENT_SLEEP=$(( SLEEP_INTERVAL + JITTER ))
    
    # Ensure we sleep at least 10 seconds under any circumstance
    if [ "$CURRENT_SLEEP" -lt 10 ]; then
        CURRENT_SLEEP=10
    fi
    
    echo "[$(date)] Spider finished. Sleeping for $CURRENT_SLEEP seconds (base: $SLEEP_INTERVAL, jitter: $JITTER)..."
    sleep "$CURRENT_SLEEP"
done
