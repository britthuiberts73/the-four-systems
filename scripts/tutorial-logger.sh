#!/usr/bin/env bash
# Append a tutorial breadcrumb every coordinator run.
# Usage: tutorial-logger.sh <agent> <status> <duration_or_msg> <report_path>

set -euo pipefail

AGENT="${1:-unknown}"
STATUS="${2:-?}"
DETAIL="${3:-}"
REPORT="${4:-}"

LOG_DIR="/path/to/the-four-systems/Content/youtube-tutorial-the-four-systems"
LOG_FILE="$LOG_DIR/build-log.md"

mkdir -p "$LOG_DIR"
[[ ! -f "$LOG_FILE" ]] && cat > "$LOG_FILE" <<'EOF'
# The Four Systems: Build Log

Auto-appended by every coordinator run. Use this as the source for the YouTube tutorial script.

EOF

TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"

{
  echo ""
  echo "## $TIMESTAMP — $AGENT — $STATUS ($DETAIL)"
  echo ""
  echo "- Report: \`${REPORT}\`"

  # Attach a one-line summary if the report exists
  if [[ -f "$REPORT" ]]; then
    SUMMARY="$(grep -m1 -E '^## Summary|^# ' "$REPORT" 2>/dev/null | head -1 || true)"
    [[ -n "$SUMMARY" ]] && echo "- First heading: $SUMMARY"
    LINES="$(wc -l < "$REPORT" | tr -d ' ')"
    echo "- Report lines: $LINES"
  fi

  # Per-agent extras
  case "$AGENT" in
    keyword-researcher)
      LATEST_CSV="$(ls -t "/path/to/the-four-systems/ai-ranking-automations/seo-agents/output/keywords/" 2>/dev/null | head -1 || true)"
      [[ -n "$LATEST_CSV" ]] && echo "- B-roll: screen-record opening \`output/keywords/$LATEST_CSV\`"
      QUEUE_LEN="$(python3 -c "import json; print(len(json.load(open('/path/to/the-four-systems/ai-ranking-automations/seo-agents/state/content-queue.json'))['items']))" 2>/dev/null || echo '?')"
      echo "- Content queue length: $QUEUE_LEN items"
      ;;
    content-writer)
      echo "- B-roll: screen-record the published post URL on your-site.com"
      ;;
    vital-signs)
      echo "- B-roll: screen-record \`state/vital-signs-queue.json\` opening in editor"
      ;;
    refresh-recommender)
      echo "- B-roll: GSC chart of one decaying URL on screen + the report file"
      ;;
  esac

} >> "$LOG_FILE"
