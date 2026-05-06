# System 3, Onsite Audit

> **Before reading this:** complete `system-0-prerequisites.md`. Specifically: DataForSEO MCP must be wired into your project's `.mcp.json`. The audit uses `mcp__dfs-mcp__on_page_lighthouse` and `mcp__dfs-mcp__on_page_instant_pages`.

A scheduled or on-demand Claude Code agent that runs Google Lighthouse plus DataForSEO's on-page health checks against your homepage and 2-3 priority URLs, then produces a focused, actionable report: site verdict (green/amber/red), per-URL scores across Performance / Accessibility / Best Practices / SEO, Core Web Vitals, template-level issues that affect multiple pages, and a prioritised "fix these next" list.

This is your weekly site health check. Not content quality (that's System 4): purely technical onsite health. Speed, accessibility, schema, canonicals, meta tags, security headers, broken links, image alt text.

## What it does

For each URL in `context/audit-urls.txt` (default: homepage + 2 most-important pages), the agent:

1. **Lighthouse scan** via `mcp__dfs-mcp__on_page_lighthouse`. Captures the four headline scores (0-100), Core Web Vitals (LCP, CLS, TBT/INP), and the top failing audits per category with estimated savings.
2. **On-page instant audit** via `mcp__dfs-mcp__on_page_instant_pages`. Adds: broken internal/external links, missing or duplicate H1/title/meta description, canonical issues, schema.org presence and validity, mixed content / HTTPS, image alt coverage, content-to-code ratio.
3. **Aggregate**. Computes site-level rollups: average scores per category, issues that appear on multiple URLs (template-level fixes), money-page alerts (any commercial page from `services.md` with a category < 90).
4. **Verdict**. Each URL and the overall site get one of:
   - **Green**: all 4 categories ≥ 90, no critical on-page issues
   - **Amber**: any category 70-89, or any on-page issue
   - **Red**: any category < 70, or a money page in amber/red, or mixed content / canonical / schema-broken

Output: `state/onsite-audit.json` (machine-readable, drives the dashboard) and `reports/<date>-onsite-audit.md` (human-readable with prioritised next actions).

## Why this rather than running Lighthouse myself

Lighthouse from the command line gives you a single audit at a single moment. This system gives you:

- **Trended scores** in JSON state, so the dashboard shows weekly changes
- **Template-level rollups**: "3 pages have render-blocking resources" beats running Lighthouse 3 times and noticing the pattern by hand
- **Money-page alerts**: every audit knows which page is your `/pricing/` and tightens the threshold
- **Recommended next actions** sorted by impact: not "here are 47 things Lighthouse found", but "fix these 3 in this order, the first two affect every page"
- **Auto-runs weekly**, so you're never finding out about regressions a month later

Plus you don't need to install Lighthouse locally. DataForSEO runs it on their infrastructure and returns the JSON.

## How it runs

**Default: a Claude Code skill (you trigger it).** Drop `onsite-audit.md` into `.claude/skills/`. In Claude Code, say:

```
run an onsite audit
```

Or: `lighthouse audit`, `site speed check`, `is my site healthy`, `audit my homepage`. ~3 minutes wall clock, ~$0.18 in DataForSEO + Claude API. Click Allow on the first DataForSEO MCP call (or pre-allow in `.claude/settings.local.json`) and the skill runs cleanly.

**Optional: hands-off via cron / launchd.** Same agent, scheduled weekly to drop one audit report into `reports/` every Monday at 09:17. The dashboard's Onsite Audit tab refreshes automatically. See "Going hands-off" near the bottom for setup.

## Costs

- DataForSEO Lighthouse: ~$0.05 per URL
- DataForSEO `on_page_instant_pages`: ~$0.01 per URL
- Claude analysis: ~$0.05 per run
- 3 URLs total: **~$0.18 per audit**, ~$0.75/month if weekly

This is the cheapest of the four systems by some margin. Lighthouse is slow but cheap.

## Setup

### 1. Confirm DataForSEO MCP is wired

You did this in System 0. Verify quickly:

```bash
cd ai-ranking-automations/seo-agents
claude -p "List MCP tools whose name starts with mcp__dfs-mcp__on_page" --dangerously-skip-permissions
```

You should see `mcp__dfs-mcp__on_page_lighthouse`, `mcp__dfs-mcp__on_page_instant_pages`, and `mcp__dfs-mcp__on_page_content_parsing` in the list.

### 2. Set the URLs to audit

Edit `context/audit-urls.txt`:

```
# One URL per line. Lines starting with # are ignored.
# Recommended: homepage + 2 most-important pages.
https://www.yoursite.com/
https://www.yoursite.com/pricing/
https://www.yoursite.com/blog/your-most-important-post/
```

Keep the list short. Each URL is ~$0.06 in API spend. Auditing 30 URLs every week is wasteful: most issues are template-level and surface from any 2-3 pages. Audit your money pages plus a representative blog post.

### 3. Drop in the skill

```bash
cp the-four-systems/system-3-onsite-audit/skill/onsite-audit.md .claude/skills/
```

In Claude Code: `run onsite audit`. Claude reads `audit-urls.txt`, calls Lighthouse and instant_pages on each URL, computes the rollup, writes the state file, writes the markdown report, regenerates the dashboard.

## Reading the output

Open `reports/<date>-onsite-audit.md`. Top of the file:

```
# Onsite Audit, yoursite.com, 2026-05-06

## Site rollup
- Verdict: amber
- Average performance: 84
- Average accessibility: 95
- Average best practices: 96
- Average SEO: 100
- Pages audited: 3
```

Then per-page scores, template-level issues (the highest-leverage fixes — one change lifts every page that shares the template), money-page alerts (commercial pages with any category below 90), and finally the actual to-do list:

```
## Recommended next actions (priority order)
1. Fix render-blocking resources on homepage and pricing. Two-page fix lifts both Lighthouse Performance and Core Web Vitals.
2. Properly size images on the pricing page. Replace the 1920x1080 hero with a srcset.
3. Add meta description to the homepage <head>. SEO score will hit 100.
```

That's the file you actually act on. The rest is data.

## Dashboard tab

The Onsite Audit tab at `output/keywords/dashboard.html` shows:
- 5 stat tiles: site verdict (green/amber/red), avg Performance, avg Accessibility, avg Best Practices, avg SEO
- Per-URL table with all four scores color-coded (green ≥90, amber 70-89, red <70), Core Web Vitals (LCP in seconds, CLS), and issue count
- Money page alerts (any commercial URL in amber or red)
- Template-level issues ranked by affected URLs
- The full markdown report inline so you can read everything in one place

## Tuning thresholds

The default verdict thresholds are in `prompts/onsite-audit.md`:
- Green: all categories ≥ 90
- Amber: any category 70-89
- Red: any category < 70

To tighten or loosen, edit the prompt's "Apply thresholds" section. Re-run; nothing else changes.

## Going hands-off (optional)

If you'd rather not invoke the skill manually each week, schedule the same agent.

Trade-off: scheduled runs use `--dangerously-skip-permissions` because no human is there to approve tool calls. For this agent the scope is narrow (DataForSEO MCP + writing to `state/` + writing to `reports/`), so the risk is low.

**macOS, launchd:**

```bash
cp the-four-systems/system-3-onsite-audit/launchd/com.example.seo-onsite-audit.plist \
   ~/Library/LaunchAgents/

# Edit the path inside ProgramArguments to point at your project
nano ~/Library/LaunchAgents/com.example.seo-onsite-audit.plist

launchctl load ~/Library/LaunchAgents/com.example.seo-onsite-audit.plist
launchctl list | grep seo-onsite-audit
```

Monday at 09:17 (off the :00 mark) so refresh issues found Monday get fixed before next Monday's audit.

**Linux / WSL2, cron:**

```cron
17 9 * * 1 cd /path/to/seo-agents && ./coordinator.sh onsite-audit >> /tmp/seo-onsite-audit.log 2>&1
```

## Hard rules baked into the prompt

- The agent only audits URLs in `context/audit-urls.txt`. No auto-discovery.
- Per-URL findings reference real Lighthouse audit IDs (`render-blocking-resources`, `unused-css-rules`, `uses-text-compression`). No paraphrased pseudo-issues.
- Recommendations must be actionable. "Improve performance" is not acceptable. "Inline the critical CSS for the hero, defer the rest" is.
- Money pages (commercial pages from `services.md`) get tighter scoring: any category below 90 escalates the verdict.
- Real DataForSEO data only. Null metrics stay null.

## Troubleshooting

**"DataForSEO returned an error"** — Most common cause: invalid URL or site blocking the Lighthouse runner. Check that the URL loads in a browser and doesn't require auth.

**"Lighthouse run timed out"** — Increase the timeout in the agent prompt or DataForSEO's task wait. Some slow pages need 60+ seconds.

**"All my scores are 100 but the site feels slow"** — Lighthouse doesn't measure everything. Watch real-user CWV in GSC's Core Web Vitals report. If lab scores are 100 but field data is amber/red, look at TTFB (server response) and bundle size on real devices. The Lighthouse score is necessary, not sufficient.

**"Money page alerts firing on a non-commercial URL"** — Edit `context/services.md` to clarify which URLs are commercial. The agent reads that file every run.

**"Same template issue appears every audit and never gets fixed"** — That's the system working. Now go fix it. Once shipped, the next audit will reflect the improvement.

## What's next

System 4 (Refresh Recommender) does the content-quality counterpart: reads GSC, scores decay on every URL, and tells you which posts to rewrite. We build that next.
