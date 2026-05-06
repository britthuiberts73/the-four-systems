#!/usr/bin/env bash
# The Four Systems SEO Agent Coordinator
# Orchestrates individual SEO agents for your-site.com with locking,
# logging, git auto-commit, and tutorial breadcrumbs.
# Usage: ./coordinator.sh <agent-name>

set -euo pipefail

# Ensure launchd has access to required tools
export PATH="/Applications/cmux.app/Contents/Resources/bin:/path/to/.local/bin:/path/to/.npm-global/bin:/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:$PATH"
export HOME="/path/to"

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCK_FILE="$SCRIPT_DIR/state/.lock"
LOCK_TIMEOUT=3600
AGENT_NAME="${1:-}"
LOG_FILE="$SCRIPT_DIR/state/agent-log.json"
REPORT_DIR="$SCRIPT_DIR/reports"
DATE_STAMP="$(date +%Y-%m-%d)"
TIME_STAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
SEED_ARG="${2:-}"

VALID_AGENTS=("keyword-researcher" "content-writer" "onsite-audit" "refresh-recommender")

if [[ -z "$AGENT_NAME" ]]; then
  echo "Usage: $0 <agent-name> [seed-keyword]"
  echo "Agents: ${VALID_AGENTS[*]}"
  exit 1
fi

valid=false
for a in "${VALID_AGENTS[@]}"; do [[ "$AGENT_NAME" == "$a" ]] && valid=true; done
if [[ "$valid" != "true" ]]; then
  echo "Invalid agent: $AGENT_NAME"
  echo "Agents: ${VALID_AGENTS[*]}"
  exit 1
fi

PROMPT_FILE="$SCRIPT_DIR/prompts/$AGENT_NAME.md"
REPORT_FILE="$REPORT_DIR/$DATE_STAMP-$AGENT_NAME.md"

if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "Prompt missing: $PROMPT_FILE"
  exit 1
fi

acquire_lock() {
  if [[ -f "$LOCK_FILE" ]]; then
    local t age now
    t=$(head -1 "$LOCK_FILE" 2>/dev/null || echo 0)
    now=$(date +%s)
    age=$(( now - t ))
    if (( age > LOCK_TIMEOUT )); then
      echo "Stale lock (${age}s). Removing."
      rm -f "$LOCK_FILE"
    else
      echo "Locked by $(tail -1 "$LOCK_FILE") (${age}s ago). Aborting."
      exit 1
    fi
  fi
  echo "$(date +%s)" > "$LOCK_FILE"
  echo "$AGENT_NAME" >> "$LOCK_FILE"
}

release_lock() { rm -f "$LOCK_FILE"; }

log_run() {
  local status="$1" msg="${2:-}" duration="$3"
  [[ ! -s "$LOG_FILE" ]] && echo "[]" > "$LOG_FILE"
  python3 - <<PY
import json
log = json.load(open("$LOG_FILE"))
log.append({
  "agent": "$AGENT_NAME",
  "timestamp": "$TIME_STAMP",
  "status": "$status",
  "message": "$msg",
  "duration_seconds": $duration,
  "report": "$REPORT_FILE",
  "seed": "$SEED_ARG"
})
log = log[-200:]
json.dump(log, open("$LOG_FILE", "w"), indent=2)
PY
}

git_commit() {
  cd "$SCRIPT_DIR"
  if [[ -z "$(git status --porcelain . 2>/dev/null)" ]]; then
    echo "No changes to commit."
    return 1
  fi
  git add -A .
  git commit -m "seo($AGENT_NAME): run $DATE_STAMP" || return 1
  return 0
}

main() {
  echo "================================="
  echo "Agent: $AGENT_NAME"
  echo "Time:  $TIME_STAMP"
  echo "Seed:  ${SEED_ARG:-<none>}"
  echo "================================="

  local start; start=$(date +%s)

  acquire_lock
  trap 'release_lock' EXIT

  # Auth check
  if ! claude auth status 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); exit(0 if d.get('loggedIn') else 1)" 2>/dev/null; then
    echo "ERROR: claude CLI not authenticated."
    log_run "error" "auth failure" 0
    exit 1
  fi

  cd "$SCRIPT_DIR"  # so .mcp.json (dfs-mcp) is discovered

  echo "Running prompt: $PROMPT_FILE"
  echo "Report:         $REPORT_FILE"
  echo "---------------------------------"

  local exit_code=0

  # refresh-recommender is a hybrid agent: Python pulls GSC decay, then Claude classifies.
  if [[ "$AGENT_NAME" == "refresh-recommender" ]]; then
    local gsc_venv="/path/to/the-four-systems/SEO-Access/mcp-gsc/venv/bin/python"
    local py_bin="$gsc_venv"
    [[ ! -x "$py_bin" ]] && py_bin="python3"
    echo "Phase 1: sitemap + GSC indexing scan..."
    "$py_bin" "$SCRIPT_DIR/scripts/refresh-scorer.py" 2>&1 | tee "$REPORT_FILE"
    local layer1_exit=${PIPESTATUS[0]}
    if [[ $layer1_exit -ne 0 ]]; then
      log_run "error" "layer 1 GSC pull failed (exit $layer1_exit)" "0"
      exit $layer1_exit
    fi
    echo ""
    echo "Phase 2: Claude classification..."
  fi

  local prompt_body
  prompt_body="$(cat "$PROMPT_FILE")"
  if [[ -n "$SEED_ARG" ]]; then
    prompt_body="SEED_KEYWORD: $SEED_ARG"$'\n\n'"$prompt_body"
  fi
  # All scheduled (coordinator-driven) runs of agents that have an interactive
  # mode get the AUTO header so the prompt knows not to ask the user anything.
  if [[ "$AGENT_NAME" == "content-writer" ]]; then
    prompt_body="MODE: AUTO"$'\n\n'"$prompt_body"
  fi

  claude -p "$prompt_body" \
    --dangerously-skip-permissions \
    2>&1 | tee -a "$REPORT_FILE" || exit_code=$?

  local end duration
  end=$(date +%s); duration=$(( end - start ))

  echo "---------------------------------"

  if [[ $exit_code -ne 0 ]]; then
    log_run "error" "exit $exit_code" "$duration"
    bash "$SCRIPT_DIR/scripts/tutorial-logger.sh" "$AGENT_NAME" "ERROR" "exit $exit_code" "$REPORT_FILE" || true
    exit $exit_code
  fi

  # Regenerate the user-facing HTML dashboard for any agent that touched state
  if [[ "$AGENT_NAME" == "keyword-researcher" || "$AGENT_NAME" == "content-writer" ]]; then
    python3 "$SCRIPT_DIR/scripts/render-html-report.py" || echo "Warning: HTML render failed"
  fi

  if git_commit; then
    log_run "success" "committed" "$duration"
  else
    log_run "success" "no-op" "$duration"
  fi

  bash "$SCRIPT_DIR/scripts/tutorial-logger.sh" "$AGENT_NAME" "OK" "${duration}s" "$REPORT_FILE" || true

  echo "Done in ${duration}s."
}

main
