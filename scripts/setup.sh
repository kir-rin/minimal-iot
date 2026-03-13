#!/bin/bash
set -e

echo "🚀 Setting up development environment with UV..."

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "❌ UV is not installed. Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Source the env file to add uv to PATH
    source "$HOME/.local/bin/env"
fi

echo "✅ UV version: $(uv --version)"

# Check Python version
PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2)
echo "✅ Python version: $PYTHON_VERSION"

# Create virtual environment with UV
echo "📦 Creating virtual environment..."
uv venv

# Install dependencies with dev extras
echo "📦 Installing dependencies..."
uv pip install -e ".[dev]"

# Install the package itself
echo "📦 Installing package in editable mode..."
uv pip install -e .

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Copy .env.example to .env and configure"
echo "  2. Run: uv run python src/main.py"
echo "  3. Or use: ./scripts/run-dev.sh"
