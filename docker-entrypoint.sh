#!/usr/bin/env bash
set -e

# Docker Entrypoint Script for JARVIS AI Assistant

if [ "$1" = "test" ] || [ "$1" = "--test" ]; then
    shift
    echo "Executing test suite inside container..."
    if [ -f "/app/run-tests.sh" ]; then
        exec /app/run-tests.sh "$@"
    else
        exec pytest "$@"
    fi
elif [ "$1" = "--server" ] || [ "$1" = "server" ]; then
    shift
    echo "Starting Neural Hub Server mode on 0.0.0.0:8000..."
    exec uvicorn ai.modules.server.server_module:app --host 0.0.0.0 --port 8000 "$@"
elif [ "$1" = "bash" ] || [ "$1" = "sh" ]; then
    exec "$@"
else
    echo "Starting Interactive AI Assistant CLI..."
    exec /app/run.sh "$@"
fi