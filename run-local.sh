#!/usr/bin/env bash
set -euo pipefail

# run-local.sh
# Helper script to run the telegram bot locally
# Usage:
#   ./run-local.sh              - Run the bot
#   ./run-local.sh test         - Run tests
#   ./run-local.sh test-watch   - Run tests in watch mode
#   ./run-local.sh lint         - Run linting
#   ./run-local.sh format       - Format code

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
SECRETS_DIR="$ROOT_DIR/../docker_secrets"
ENV_FILE="$ROOT_DIR/.env"

# Load .env file if it exists
if [ -f "$ENV_FILE" ]; then
  echo "Loading environment from .env file..."
  # Export variables from .env, ignoring comments and empty lines
  set -a
  # shellcheck disable=SC1090
  source <(grep -v '^#' "$ENV_FILE" | grep -v '^$' | sed 's/^/export /')
  set +a
fi

read_secret() {
  local name="$1"
  local f="$SECRETS_DIR/$name"
  if [ -f "$f" ]; then
    # strip trailing newline
    awk '{printf "%s", $0; exit}' "$f"
  else
    echo ""
  fi
}

# Allow overriding via environment, then .env, then docker_secrets
export TELEGRAM_TOKEN="${TELEGRAM_TOKEN:-$(read_secret telegram_bot_token)}"
export OVERSEERR_API_KEY="${OVERSEERR_API_KEY:-$(read_secret overseerr_api_key)}"
export TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-$(read_secret telegram_chat_id)}"
export WEBHOOK_PORT="${WEBHOOK_PORT:-7777}"
export WEBHOOK_TOKEN="${WEBHOOK_TOKEN:-$(read_secret webhook_token)}"
export OVERSEERR_URL="${OVERSEERR_URL:-http://localhost:5055}"
export WEBHOOK_HOST="${WEBHOOK_HOST:-0.0.0.0}"
export WEBHOOK_PATH="${WEBHOOK_PATH:-/overseerr/requests}"

cd "$ROOT_DIR"

# Create and activate venv if needed
if [ ! -d ".venv" ]; then
  echo "Creating virtualenv .venv (python3 must be available)..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

# Install dependencies if not present
pip install --upgrade pip --quiet
pip install -e ".[dev]" --quiet

# Parse command
COMMAND="${1:-run}"

case "$COMMAND" in
  test)
    echo "Running tests..."
    pytest
    ;;
  test-watch)
    echo "Running tests in watch mode..."
    pytest --looponfail
    ;;
  lint)
    echo "Running linting..."
    ruff check .
    ;;
  format)
    echo "Formatting code..."
    black .
    ruff check --fix .
    ;;
  run)
    # Basic validation for running the bot
    if [ -z "$TELEGRAM_TOKEN" ] || [ -z "$OVERSEERR_API_KEY" ] || [ -z "$TELEGRAM_CHAT_ID" ]; then
      echo "❌ Missing required environment variables!"
      echo ""
      echo "Please set up one of the following:"
      echo "  1. Create a .env file (recommended for local testing)"
      echo "     cp .env.example .env"
      echo "     # Then edit .env with your values"
      echo ""
      echo "  2. Provide files in ../docker_secrets:"
      echo "     - telegram_bot_token"
      echo "     - overseerr_api_key"
      echo "     - telegram_chat_id"
      echo ""
      echo "Current values:"
      [ -z "$TELEGRAM_TOKEN" ] && echo "  ❌ TELEGRAM_TOKEN = (missing)" || echo "  ✅ TELEGRAM_TOKEN = (set)"
      [ -z "$OVERSEERR_API_KEY" ] && echo "  ❌ OVERSEERR_API_KEY = (missing)" || echo "  ✅ OVERSEERR_API_KEY = (set)"
      [ -z "$TELEGRAM_CHAT_ID" ] && echo "  ❌ TELEGRAM_CHAT_ID = (missing)" || echo "  ✅ TELEGRAM_CHAT_ID = $TELEGRAM_CHAT_ID"
      exit 1
    fi

    echo "✅ Configuration validated"
    echo ""
    echo "📱 Telegram Bot Configuration:"
    echo "   Webhook: http://$WEBHOOK_HOST:$WEBHOOK_PORT$WEBHOOK_PATH"
    echo "   Overseerr: $OVERSEERR_URL"
    echo ""
    echo "🚀 Starting bot..."
    echo ""

    # Try running as package module (if installed or running from parent), then try top-level module, then fallback to script
    # This avoids ModuleNotFoundError when running from inside the `telegram_bot` directory.
    python -m telegram_bot.bot 2>/dev/null || python -m bot 2>/dev/null || python bot.py
    ;;
  *)
    echo "Unknown command: $COMMAND"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  run          - Run the bot (default)"
    echo "  test         - Run tests"
    echo "  test-watch   - Run tests in watch mode"
    echo "  lint         - Run linting"
    echo "  format       - Format code"
    exit 1
    ;;
esac
