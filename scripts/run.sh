#!/bin/bash
# One-click startup script for Local Container Service Platform

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT" || exit 1

echo "========================================================"
echo " Starting Local Container Service Platform with Load Balancing"
echo "========================================================"
python3 app.py
