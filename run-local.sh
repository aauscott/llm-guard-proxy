#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$ROOT_DIR/.llm-guard-proxy.pid"
OLLAMA_PID_FILE="$ROOT_DIR/.llm-guard-ollama.pid"
LOG_DIR="$ROOT_DIR/logs"
LOG_FILE="$LOG_DIR/llm-guard-proxy-$(date +%Y%m%d-%H%M%S).log"

HOST="${GUARD_HOST:-0.0.0.0}"
PORT="${GUARD_PORT:-8000}"
export GUARD_POLICY_PATH="${GUARD_POLICY_PATH:-policies/permissive.yaml}"
export GUARD_UPSTREAM_BASE_URL="${GUARD_UPSTREAM_BASE_URL:-http://localhost:11434}"
START_OLLAMA=false
OLLAMA_MODEL="${OLLAMA_MODEL:-}"

usage() {
  cat <<'EOF'
Usage: ./run-local.sh [options]

Options:
  --with-ollama       Start a local Ollama server if one is not already running.
  --model MODEL       Ensure an Ollama model is available locally.
  --upstream URL      Set GUARD_UPSTREAM_BASE_URL.
  --policy PATH       Set GUARD_POLICY_PATH.
  --host HOST         Set the proxy bind host. Default: 0.0.0.0
  --port PORT         Set the proxy port. Default: 8000
  -h, --help          Show this help.

Examples:
  ./run-local.sh --with-ollama --model deepseek-r1:1.5b
  ./run-local.sh --upstream https://api.openai.com
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-ollama)
      START_OLLAMA=true
      shift
      ;;
    --model)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --model"
        exit 1
      fi
      OLLAMA_MODEL="$2"
      shift 2
      ;;
    --upstream)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --upstream"
        exit 1
      fi
      export GUARD_UPSTREAM_BASE_URL="$2"
      shift 2
      ;;
    --policy)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --policy"
        exit 1
      fi
      export GUARD_POLICY_PATH="$2"
      shift 2
      ;;
    --host)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --host"
        exit 1
      fi
      HOST="$2"
      shift 2
      ;;
    --port)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --port"
        exit 1
      fi
      PORT="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      usage
      exit 1
      ;;
  esac
done

ollama_api_available() {
  command -v curl >/dev/null 2>&1 && curl -fsS --max-time 2 http://localhost:11434/api/tags >/dev/null 2>&1
}

ollama_model_installed() {
  local model="$1"
  local tagged_model="$model"
  local list_output

  if [[ "$model" != *:* ]]; then
    tagged_model="$model:latest"
  fi

  if ! list_output="$(ollama list 2>/dev/null)"; then
    return 1
  fi

  while read -r name _; do
    if [[ "$name" == "$model" || "$name" == "$tagged_model" ]]; then
      return 0
    fi
  done <<< "$list_output"

  return 1
}

if [[ -f "$PID_FILE" ]]; then
  existing_pid="$(cat "$PID_FILE")"
  if kill -0 "$existing_pid" 2>/dev/null; then
    echo "llm-guard-proxy is already running with PID $existing_pid."
    echo "Stop it with ./stop-local.sh"
    exit 0
  fi
  rm -f "$PID_FILE"
fi

cd "$ROOT_DIR"
mkdir -p "$LOG_DIR"

if [[ "$START_OLLAMA" == "true" ]]; then
  if ! command -v ollama >/dev/null 2>&1; then
    echo "Could not find ollama. Install Ollama or omit --with-ollama."
    exit 1
  fi

  if ollama_api_available; then
    echo "Ollama is already running at http://localhost:11434."
  else
    OLLAMA_LOG_FILE="$LOG_DIR/ollama-$(date +%Y%m%d-%H%M%S).log"
    echo "Starting Ollama server..."
    echo "Ollama logs: $OLLAMA_LOG_FILE"
    nohup ollama serve >"$OLLAMA_LOG_FILE" 2>&1 &
    echo "$!" >"$OLLAMA_PID_FILE"

    for _ in {1..30}; do
      if ollama_api_available; then
        echo "Ollama started with PID $(cat "$OLLAMA_PID_FILE")."
        break
      fi
      if ! kill -0 "$(cat "$OLLAMA_PID_FILE")" 2>/dev/null; then
        echo "Ollama exited before it became available. Check $OLLAMA_LOG_FILE"
        rm -f "$OLLAMA_PID_FILE"
        exit 1
      fi
      sleep 0.5
    done

    if ! ollama_api_available; then
      echo "Ollama did not become available at http://localhost:11434. Check $OLLAMA_LOG_FILE"
      exit 1
    fi
  fi
fi

if [[ -n "$OLLAMA_MODEL" ]]; then
  if ! command -v ollama >/dev/null 2>&1; then
    echo "Could not find ollama. Install Ollama or omit --model."
    exit 1
  fi
  if ! ollama_api_available; then
    echo "Ollama is not reachable at http://localhost:11434."
    echo "Start Ollama first or use ./run-local.sh --with-ollama --model $OLLAMA_MODEL"
    exit 1
  fi
  if ollama_model_installed "$OLLAMA_MODEL"; then
    echo "Ollama model already installed: $OLLAMA_MODEL"
  else
    echo "Ollama model not found locally. Pulling: $OLLAMA_MODEL"
    ollama pull "$OLLAMA_MODEL"
  fi
fi

if [[ -x "$ROOT_DIR/.venv/bin/uvicorn" ]]; then
  UVICORN="$ROOT_DIR/.venv/bin/uvicorn"
elif command -v uvicorn >/dev/null 2>&1; then
  UVICORN="$(command -v uvicorn)"
else
  echo "Could not find uvicorn."
  echo "Create a virtual environment and install dependencies first:"
  echo "  python3 -m venv .venv"
  echo "  source .venv/bin/activate"
  echo "  pip install -e \".[dev]\""
  exit 1
fi

echo "Starting llm-guard-proxy on http://localhost:$PORT/v1"
echo "Upstream: $GUARD_UPSTREAM_BASE_URL"
echo "Policy: $GUARD_POLICY_PATH"
if [[ -n "$OLLAMA_MODEL" ]]; then
  echo "Ollama model: $OLLAMA_MODEL"
fi
echo "Logs: $LOG_FILE"

nohup "$UVICORN" app.main:app --host "$HOST" --port "$PORT" --reload >"$LOG_FILE" 2>&1 &
echo "$!" >"$PID_FILE"

echo "Started with PID $(cat "$PID_FILE")."
echo "Stop it with ./stop-local.sh"
