#!/usr/bin/env bash
set -e

echo "Starting Operations Assistant Setup..."

# Check for pip
if ! command -v pip &> /dev/null
then
    echo "Error: pip could not be found. Please install Python and pip first."
    exit 1
fi

echo "Installing uv package manager..."
pip install uv

echo "Syncing project dependencies..."
uv sync

echo "Setting up environment variables..."
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "Created .env from .env.example."
    else
        echo "Warning: .env.example not found. Creating empty .env file."
        touch .env
    fi
else
    echo "Note: .env already exists. Skipping."
fi

echo ""
echo "Setup complete!"
echo "NEXT STEPS:"
echo "1. Open the '.env' file and add your GROQ_API_KEY."
echo "2. Start the MCP server: uv run python server/mcp_server.py"
echo "3. Run the Assistant in another terminal: uv run python -m crew.crew \"Your question here\""
