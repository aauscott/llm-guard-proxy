#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$ROOT_DIR/.llm-guard-proxy.pid"
OLLAMA_PID_FILE="$ROOT_DIR/.llm-guard-ollama.pid"
STOP_OLLAMA=false

usage() {
  cat <<'EOF'
Usage: ./stop-local.sh [options]

Options:
  --ollama    Also stop the Ollama server if it was started by ./run-local.sh.
  --all       Stop the proxy and the script-managed Ollama server.
  -h, --help  Show this help.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ollama|--all)
      STOP_OLLAMA=true
      shift
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

stop_pid_file() {
  local pid_file="$1"
  local label="$2"

  if [[ ! -f "$pid_file" ]]; then
    echo "No $label PID file found."
    return 0
  fi

  local pid
  pid="$(cat "$pid_file")"

  if ! kill -0 "$pid" 2>/dev/null; then
    echo "No running process found for $label PID $pid. Removing stale PID file."
    rm -f "$pid_file"
    return 0
  fi

  echo "Stopping $label with PID $pid..."
  kill "$pid"

  for _ in {1..20}; do
    if ! kill -0 "$pid" 2>/dev/null; then
      rm -f "$pid_file"
      echo "Stopped $label."
      return 0
    fi
    sleep 0.25
  done

  echo "$label did not stop after 5 seconds. Sending SIGKILL..."
  kill -9 "$pid" 2>/dev/null || true
  rm -f "$pid_file"
  echo "Stopped $label."
}

stop_pid_file "$PID_FILE" "llm-guard-proxy"

if [[ "$STOP_OLLAMA" == "true" ]]; then
  stop_pid_file "$OLLAMA_PID_FILE" "Ollama"
fi
