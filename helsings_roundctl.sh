#!/usr/bin/env bash
# Start, stop, restart, and inspect helsings_round.py (Seward + scheduled Mina).
#
# Usage (from anywhere):
#   ./helsings_roundctl.sh start|stop|restart|status|logs
#
# Run from the repo root where .env lives.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIDFILE="${REPO_ROOT}/.helsings_round.pid"
LOG="${REPO_ROOT}/helsings_round.log"
MAIN_PATTERN="${REPO_ROOT}/.venv/bin/python3 helsings_round.py"

usage() {
  cat <<EOF
Usage: $(basename "$0") <command>

Commands:
  start    Run helsings_round in the background (append to helsings_round.log)
  stop     Stop the coordinator (SIGTERM, then SIGKILL if needed)
  restart  stop, then start
  status   Show whether the archive runner is running
  logs     Tail helsings_round.log (Ctrl+C to exit)

Only one instance should run at a time (same Telegram bot token).
EOF
}

find_main_pids() {
  pgrep -f "${MAIN_PATTERN}" 2>/dev/null || true
}

pid_alive() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

read_pidfile() {
  if [[ -f "$PIDFILE" ]]; then
    tr -d '[:space:]' <"$PIDFILE"
  fi
}

is_running() {
  local pid
  pid="$(read_pidfile)"
  if pid_alive "$pid"; then
    return 0
  fi
  local pids
  pids="$(find_main_pids)"
  [[ -n "$pids" ]]
}

cmd_status() {
  local pid pids
  pid="$(read_pidfile)"
  if pid_alive "$pid"; then
    echo "running (PID ${pid}, from ${PIDFILE})"
    return 0
  fi
  pids="$(find_main_pids)"
  if [[ -n "$pids" ]]; then
    echo "running (PIDs: ${pids//$'\n'/, }) — no valid PID file; consider: $0 restart"
    return 0
  fi
  echo "stopped"
  return 1
}

cmd_stop() {
  local pid pids waited
  pid="$(read_pidfile)"
  if pid_alive "$pid"; then
    echo "Stopping PID ${pid}..."
    kill -TERM "$pid" 2>/dev/null || true
    waited=0
    while pid_alive "$pid" && (( waited < 12 )); do
      sleep 1
      (( waited += 1 )) || true
    done
    if pid_alive "$pid"; then
      echo "Still running; sending SIGKILL..."
      kill -KILL "$pid" 2>/dev/null || true
    fi
  fi

  pids="$(find_main_pids)"
  if [[ -n "$pids" ]]; then
    echo "Stopping remaining helsings_round process(es)..."
    while read -r p; do
      [[ -n "$p" ]] || continue
      kill -TERM "$p" 2>/dev/null || true
    done <<<"$pids"
    sleep 2
    pids="$(find_main_pids)"
    if [[ -n "$pids" ]]; then
      while read -r p; do
        [[ -n "$p" ]] || continue
        kill -KILL "$p" 2>/dev/null || true
      done <<<"$pids"
    fi
  fi

  rm -f "$PIDFILE"
  if is_running; then
    echo "Failed to stop all processes." >&2
    return 1
  fi
  echo "stopped"
}

cmd_start() {
  if is_running; then
    echo "Already running. Use: $0 status" >&2
    return 1
  fi
  rm -f "$PIDFILE"
  cd "$REPO_ROOT"
  nohup uv run python helsings_round.py >>"$LOG" 2>&1 &
  echo $! >"$PIDFILE"
  sleep 1
  if ! is_running; then
    echo "Failed to start. Check ${LOG}" >&2
    rm -f "$PIDFILE"
    return 1
  fi
  echo "started (PID $(read_pidfile), log: ${LOG})"
}

cmd_restart() {
  cmd_stop || true
  cmd_start
}

cmd_logs() {
  touch "$LOG"
  tail -f "$LOG"
}

main() {
  local cmd="${1:-}"
  case "$cmd" in
    start) cmd_start ;;
    stop) cmd_stop ;;
    restart) cmd_restart ;;
    status) cmd_status ;;
    logs) cmd_logs ;;
    -h|--help|help|"") usage ;;
    *)
      echo "Unknown command: ${cmd}" >&2
      usage >&2
      exit 1
      ;;
  esac
}

main "$@"
