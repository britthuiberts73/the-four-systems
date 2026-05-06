---
name: keyword-researcher
description: Run on-demand keyword research with AI fan-out for your-site.com. Generates 25-40 fan-out variations from a seed keyword, scores intent and priority via DataForSEO, dedupes against the existing keyword bank, and queues priority-1 items for the Content Writer. Updates the HTML dashboard at the end. Use when the user asks to research keywords, find content ideas, generate fan-out queries, expand a seed, or fill the content queue.
allowed-tools: Read, Write, Edit, Bash, WebFetch, mcp__dfs-mcp__ai_optimization_chat_gpt_scraper, mcp__dfs-mcp__dataforseo_labs_google_keyword_ideas, mcp__dfs-mcp__dataforseo_labs_google_keyword_suggestions, mcp__dfs-mcp__dataforseo_labs_google_related_keywords, mcp__dfs-mcp__dataforseo_labs_google_keyword_overview, mcp__dfs-mcp__dataforseo_labs_bulk_keyword_difficulty, mcp__dfs-mcp__dataforseo_labs_search_intent
---

# Keyword Researcher (System 1, on-demand)

Run keyword research for your-site.com using AI fan-out, with strict deduplication against the rolling keyword bank so the same topics are never researched twice.

## When to invoke

Use when the user asks to:
- Research keywords or fan out a seed
- Fill the content queue
- Expand topical coverage
- Find new content ideas
- Generate the AI fan-out for a topic

Also invoke unprompted when the user mentions a topic and asks "should we write about this" or "what would rank for X".

## How to interpret the user's request

The user will give you a seed keyword OR ask you to pick one. Decide:

1. **Explicit seed given** ("research X", "fan out Y") → use that seed verbatim.
2. **No seed given** → read `ai-ranking-automations/seo-agents/state/seed-keywords.txt` and `state/keyword-bank.json`. Pick the seed whose `last_researched` date in `keyword-bank.json -> seeds_researched[]` is oldest (or never). If every seed was researched in the last 30 days, tell the user that and ask if they want to add a new seed or force a re-research.
3. **Force re-research requested** ("re-run on X", "ignore the bank") → proceed but tell the user how many duplicates they're about to create.

## Workflow

You are running the same logic as the scheduled `keyword-researcher` agent, but interactively. The full prompt with research methodology, scoring rules, and output schema lives at:

```
ai-ranking-automations/seo-agents/prompts/keyword-researcher.md
```

**Read that prompt first.** Follow it exactly. Do not duplicate its instructions here; this skill is the on-demand entry point, the prompt file is the source of truth.

### Project root

All paths are relative to `/path/to/the-four-systems/ai-ranking-automations/seo-agents/`. Always cd there or use absolute paths.

### Strict dedup rules (this is the whole point)

Before calling any DataForSEO tool, load the existing bank into memory:

```python
import json
bank = json.load(open(".../state/keyword-bank.json"))
existing_keywords = {k["keyword"].lower().strip() for k in bank["keywords"]}
existing_seeds = {s["seed"].lower().strip(): s["last_researched"] for s in bank.get("seeds_researched", [])}
```

Then:

1. **Seed-level dedup.** If the seed (case-insensitive, trimmed) is in `existing_seeds` and `last_researched` is within 30 days, stop and ask the user: "Seed already researched on YYYY-MM-DD. Re-run anyway, pick a different seed, or add to seed-keywords.txt?". Do not proceed without confirmation.

2. **Keyword-level dedup.** After fetching fan-out variations, filter out any keyword (case-insensitive) already in `existing_keywords`. Never write a duplicate row to the bank. Never queue a duplicate post.

3. **Queue-level dedup.** Before appending to `content-queue.json`, check both `id` and `primary_keyword` against existing items. Skip if either matches. Even items with `status: "written"` count, do not re-queue something already shipped.

4. **Coverage dedup.** Run the sitemap check (WebFetch `https://www.your-site.com/sitemap.xml`) against new keywords. If a keyword's slug obviously matches a live URL, set `covered_by` and drop priority to 3. The Content Writer will not pick those up.

Report the dedup outcome at the end of the run: "Researched N variations, M new (after dedup), K queued for writer."

### When the run finishes

1. Append all NEW (deduped) keywords to `state/keyword-bank.json`. Update `last_updated` and `seeds_researched`.
2. Append qualifying priority-1 items to `state/content-queue.json` with the schema-v2 fields (`id`, `status: "queued"`, `written_at: null`, `post_url: null`).
3. Write the per-run CSV to `output/keywords/<YYYY-MM-DD>-<seed-slug>.csv`.
4. Regenerate the dashboard:
   ```bash
   python3 scripts/render-html-report.py
   ```
5. **Tell the user where the dashboard is** and offer to open it:
   ```
   Dashboard: output/keywords/dashboard.html
   Open with: open ai-ranking-automations/seo-agents/output/keywords/dashboard.html
   ```
6. Print a one-paragraph summary: seed used, fan-out evaluated, new keywords added, items queued, and the top 3 queued titles.

### Do not

- Do not commit to git. The user is running this interactively and may want to review before committing.
- Do not modify the prompt at `prompts/keyword-researcher.md`. That is the scheduled agent's source of truth, this skill should stay aligned with it.
- Do not start a second seed in the same run. One seed per invocation, even on-demand.
- Do not fabricate volume, KD, or CPC. If DataForSEO returns null, leave null.

## Cost expectation

A typical run is 5 to 8 minutes wall-clock and costs about $0.30 to $0.80 in DataForSEO + Claude API combined. Tell the user this if they ask.

## Relationship to the scheduled agent

This skill and the launchd-scheduled coordinator both write to the same `state/` files and regenerate the same dashboard. You can safely run the skill on-demand at any point; the next scheduled monthly run will see what you researched and skip those topics. The bank is the single source of truth.

If the user wants to schedule a recurring monthly run (instead of on-demand only), point them at:
```
ai-ranking-automations/seo-agents/launchd/com.example.seo-keyword-researcher.plist
```
And tell them to `launchctl load` it.
