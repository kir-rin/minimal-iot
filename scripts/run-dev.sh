#!/bin/bash
set -e

echo "🚀 Starting development server with UV..."

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "❌ UV not found. Please run ./scripts/setup.sh first"
    exit 1
fi

# Run the development server using UV
echo "✅ Running with UV..."
uv run python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
