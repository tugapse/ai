#!/bin/bash

echo "JARVIS Watchdog Initialized. Press Ctrl+C to stop."

# This is the magic line. It traps the Ctrl+C signal (SIGINT) 
# and forces the bash script to exit completely.
trap "echo -e '\n[!] Manual shutdown detected. Exiting watchdog...'; exit 0" SIGINT

while true; do
    echo "[$(date)] Starting AI Engine..."
    
    # Run the engine. The script will pause right here and wait for it.
    $AI_ENGINE --server
    
    # Capture the exit code (our "catch" block)
    EXIT_CODE=$?

    # If the process was killed by Ctrl+C, the exit code is usually 130
    if [ $EXIT_CODE -eq 130 ]; then
        echo "Process terminated by user."
        break
    elif [ $EXIT_CODE -ne 0 ]; then
        echo "[!] WARNING: Engine crashed (Exit code: $EXIT_CODE). Restarting in 3 seconds..."
        sleep 3
    else
        echo "[*] Engine stopped cleanly. Restarting..."
        sleep 1
    fi
done