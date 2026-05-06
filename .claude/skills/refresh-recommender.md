---
name: refresh-recommender
description: Run on-demand GSC health scan for the user's site. Pulls 28-day vs 28-day GSC data, flags decaying pages, pages stuck at positions 5-15, pages dropped out of the top 10, and CTR outliers. Then classifies each alert as refresh / quick_fix / new_page / ignore and routes refresh-class alerts to System 4. Use when the user asks for an SEO health check, vital signs, decay scan, GSC audit, or "what's broken on the site".
allowed-tools: Read, Write, Edit, Bash
---

# Vital Signs (System 3, on-demand)

Pull live GSC data, flag pages with quality issues, classify each alert, and route refresh candidates to System 4. The whole point: the system tells you what's broken on the site before you go looking.

## When to invoke

The user says any of:
- "vital signs" / "system 3" / "GSC scan" / "health check"
- "what's decaying" / "what's broken on my site"
- "find pages stuck at position 11"
- "decay scan" / "audit my GSC"

## What you do

You run the scheduled `refresh-recommender` agent's logic interactively. Two phases:

**Phase 1, GSC pull (Python).** Run the layer-1 Python script to pull 28-day current vs 28-day previous from GSC, compute flags, and write `state/refresh-recommender-queue.json` plus a raw markdown report. Use the project's GSC venv:

```bash
cd ai-ranking-automations/seo-agents
"/path/to/the-four-systems/SEO-Access/mcp-gsc/venv/bin/python" scripts/gsc-refresh-recommender.py
```

Show the user the totals (pages scanned, alerts found, breakdown by flag).

**Phase 2, classification (you).** Read `state/refresh-recommender-queue.json` and the prompt at:

```
ai-ranking-automations/seo-agents/prompts/refresh-recommender.md
```

That prompt is the source of truth for classification logic. Follow it exactly. Read it on every invocation; do not skim.

In interactive mode, show the user each top-priority alert and your proposed classification before queuing. Get a quick yes/no per item. After a few approvals where the user agrees with you, you can batch the rest. Always show the final tally.

## Output

Same output as the scheduled run:
- `state/refresh-queue.json` updated with `refresh`-classified items (System 4 picks these up)
- `reports/<date>-refresh-recommender.md` written with the full classification breakdown
- One-line summary printed: `Vital Signs complete. N refreshes queued, M quick fixes flagged, K new-page suggestions for System 1.`

Tell the user where to look:
- "Quick fixes you can do today: see `reports/<date>-refresh-recommender.md` under the Quick fixes table."
- "Refreshes queued for System 4: see `state/refresh-queue.json`. Run `refresh-recommender` to get the prioritized rewrite list."

## Cost

GSC API: free (within quotas; this query is well under).
Claude API for classification: ~$0.05 per run.
Python pull: 30-60 seconds.
Claude pass: 1-3 minutes.

Total ~3 minutes wall clock, $0.05.

## Hard rules

- **Read the prompt at `prompts/refresh-recommender.md` before doing classification work.** Source of truth.
- Never invent alerts. Only classify what's in `refresh-recommender-queue.json`.
- Never modify `keyword-bank.json` or `content-queue.json`. The only state file you write to is `refresh-queue.json`.
- If GSC auth fails, stop and tell the user how to fix (run `claude /login` for the GSC MCP server, or re-authorise the OAuth flow).
- Never use em dashes in any generated text.
