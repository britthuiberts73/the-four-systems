---
name: onsite-audit
description: Run on-demand onsite SEO health audit using DataForSEO Lighthouse + on_page_instant_pages. Audits the homepage and 2-3 priority URLs from context/audit-urls.txt for performance, accessibility, best practices, SEO, Core Web Vitals, broken canonicals, missing schema, security headers. Use when the user asks for a site speed check, Lighthouse audit, technical SEO health, onsite audit, or "is my site healthy".
allowed-tools: Read, Write, Edit, Bash, mcp__dfs-mcp__on_page_lighthouse, mcp__dfs-mcp__on_page_instant_pages, mcp__dfs-mcp__on_page_content_parsing
---

# Onsite Audit (System 3, on-demand)

Run a Lighthouse + on-page health audit on the user's priority URLs and produce an actionable report.

## When to invoke

The user says any of:
- "onsite audit" / "system 3" / "site health"
- "lighthouse" / "page speed" / "performance audit"
- "is my site healthy" / "check my technical SEO"
- "audit my homepage" / "run an audit"

## What you do

You run the same logic as the scheduled `onsite-audit` agent. The full prompt with workflow, scoring thresholds, state schema, and report format lives at:

```
ai-ranking-automations/seo-agents/prompts/onsite-audit.md
```

**Read that prompt first.** It's the source of truth. Read it on every invocation; do not skim.

## Project root

All paths relative to `/path/to/the-four-systems/ai-ranking-automations/seo-agents/`.

## URL list

The audit targets URLs in `context/audit-urls.txt`. If that file is missing, ask the user for 2-3 URLs (homepage + most-important pages) and offer to write the file. If the file is present, do not silently expand the list.

## Cost expectation

DataForSEO Lighthouse: ~$0.05 per URL.
DataForSEO on_page_instant_pages: ~$0.01 per URL.
3 URLs total: ~$0.18 per run.
Wall clock: 2-4 minutes (Lighthouse runs are slow).

## Hard rules

- **Read `prompts/onsite-audit.md` before doing any work.**
- Only audit URLs in `context/audit-urls.txt`.
- Never invent scores. Real DataForSEO data only.
- Recommendations must reference real Lighthouse audit IDs.
- Write to `state/onsite-audit.json` AND `reports/<date>-onsite-audit.md`.
- Run `python3 scripts/render-html-report.py` at the end so the dashboard reflects the new audit.
- Never use em dashes.
