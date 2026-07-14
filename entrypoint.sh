#!/bin/bash

# Default sleep interval is 60 seconds, can be overridden by environment variable
SLEEP_INTERVAL=${SCAN_INTERVAL_SECONDS:-60}

echo "Starting HostPing Bot..."
echo "Scan interval set to $SLEEP_INTERVAL seconds."

while true; do
    echo "[$(date)] Running spider..."
    scrapy crawl dynamic_spider
    
    echo "[$(date)] Spider finished. Sleeping for $SLEEP_INTERVAL seconds..."
    sleep "$SLEEP_INTERVAL"
done
