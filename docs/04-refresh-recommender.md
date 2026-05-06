# System 4, Refresh Recommender

> **Before reading this:** complete `system-0-prerequisites.md`. Specifically: the GSC MCP must be installed and the service account (or OAuth token) must have read access to your GSC property. The Python `certifi` package must be available (it's a transitive dependency of google-api-python-client, so the same venv works).

A scheduled or on-demand Claude Code agent that finds two specific kinds of problems on your existing site, then tells you exactly what to do about each:

1. **Posts older than 10-12 months** that have probably gone stale (dates outdated, stats from before 2024, SERP intent has shifted)
2. **Posts not indexed by Google**: URLs in your sitemap that GSC reports as "Discovered, not indexed", "Crawled, not indexed", "URL is unknown to Google", or have canonical/duplicate issues

The output is a prioritised refresh queue with a specific action per URL. You execute the actions yourself (or via your Your Brand refresh tool). System 4 is a recommender, never an auto-rewriter.

## What it does

Two layers, run as a single coordinator job.

**Layer 1 (Python)**: `scripts/refresh-scorer.py`
1. Discovers the sitemap via `/robots.txt`, then expands sitemap-index files to get every URL.
2. Filters to your blog posts (default: any URL containing `/blog/`, configurable via `--include` or env var).
3. For each URL: fetches the HTML and extracts publication / modification date from JSON-LD `datePublished`, `<meta property="article:published_time">`, or `<time datetime>`.
4. Calls Google Search Console URL Inspection API for indexing status: verdict (PASS/NEUTRAL/FAIL), coverage state, last crawl time, googleCanonical, userCanonical.
5. Flags each URL with one or more of:
   - `not_indexed`: GSC reports the URL is not indexed
   - `index_warning`: partial issue (alternate canonical, soft 404, redirect, duplicate)
   - `stale_12mo`: latest publish/modify date is 365+ days old
   - `aging`: 305-365 days old (heading toward stale)
6. Writes `state/refresh-candidates.json` (machine-readable for the dashboard) and `reports/<date>-refresh-raw.md` (human-readable for b-roll).

**Layer 2 (Claude)**: `prompts/refresh-recommender.md`
Reads the candidates and assigns each one exactly one action:
- `request_indexing`: open GSC, paste the URL into the inspection bar, click Request Indexing. Check robots.txt and `<meta name="robots">` along the way.
- `fix_canonical`: align `<link rel="canonical">` with the URL's actual location, or de-duplicate.
- `refresh`: update dates, refresh stats, re-align to current SERP, add an "Updated YYYY-MM-DD" notice, then submit to GSC for re-indexing.
- `audit_then_decide`: ambiguous combinations get a manual audit recommendation.

Skips URLs already in the System 2 content queue (no double-handling).

Writes `state/refresh-queue.json` (the actions, priority-sorted) and `reports/<date>-refresh-recommender.md` (the human-readable plan with per-URL recommendations).

## Why two layers

Layer 1 is deterministic Python: pull the sitemap, parse dates, hit GSC, score. Same code regardless of site, no judgment calls.

Layer 2 is judgment: which URLs need indexing-request vs canonical fix vs full refresh? Which patterns suggest a template-level problem (e.g. "5 of 8 not-indexed posts share the same template"). Claude is the right tool here.

Splitting them keeps each piece simple and testable. You can rerun Layer 2 against the same Layer 1 data if you want to refine the classifier without re-burning GSC quota.

## How it runs

**Default: a Claude Code skill (you trigger it).** Drop `refresh-recommender.md` into `.claude/skills/`. In Claude Code, say:

```
run refresh recommender
```

Or: `find stale posts`, `check what's not indexed`, `what should I refresh`. ~3 minutes wall clock, ~$0.05 in API spend.

**Optional: hands-off via cron / launchd.** Same agent, scheduled weekly. Drops one refresh report into `reports/` every Wednesday morning at 09:13. See "Going hands-off" near the bottom for setup.

## Costs

- Sitemap fetch: free
- Per-URL HTML fetch (date extraction): free
- Per-URL GSC URL Inspection: free (within quota: ~600/day, 1/sec)
- Claude Layer 2 classification: ~$0.05 per run

Weekly with default 60-URL cap: ~$0.20/month. Cheapest of the four systems.

## Setup

### 1. Confirm GSC URL Inspection access

The script uses `urlInspection.index.inspect`. Test:

```bash
cd ai-ranking-automations/seo-agents
"$HOME/path/to/mcp-gsc/venv/bin/python" -c "
import sys; sys.path.insert(0, '$HOME/path/to/mcp-gsc')
from gsc_server import get_gsc_service
svc = get_gsc_service()
r = svc.urlInspection().index().inspect(body={
  'inspectionUrl': 'https://www.yoursite.com/',
  'siteUrl': 'https://www.yoursite.com/'
}).execute()
print('verdict:', r['inspectionResult']['indexStatusResult'].get('verdict'))
print('coverage:', r['inspectionResult']['indexStatusResult'].get('coverageState'))
"
```

You should see something like `verdict: PASS` and `coverage: Indexed, not submitted in sitemap`.

If GSC returns 403, your service account is not added to your GSC property. Add the `client_email` from your service account JSON to GSC → Settings → Users and permissions, with Restricted access.

### 2. Set the site URL and filter

By default the script hits `https://www.your-site.com/` and filters to URLs containing `/blog/`. Override:

```bash
# Per-run
python scripts/refresh-scorer.py --site https://www.yoursite.com/ --include /blog/ --max-urls 60

# Permanent (env vars)
export REFRESH_SITE=https://www.yoursite.com/
export REFRESH_INCLUDE=/blog/
export REFRESH_MAX_URLS=60
```

`--max-urls` exists because GSC URL Inspection is rate-limited (~600/day). On a 5,000-post site, scan in batches.

### 3. Drop in the skill

```bash
cp the-four-systems/system-4-refresh-recommender/skill/refresh-recommender.md .claude/skills/
```

That's it. In Claude Code: `run refresh recommender`.

## Reading the output

The Refresh Queue tab on the dashboard shows:

- 5 stat tiles: Not indexed, Index warning, Stale (12mo+), Aging (10-12mo), Actions queued
- **Layer 2 table** (the one you act on): URL | Action | Priority | Primary flag | Age | Recommendation | Status
- **Layer 1 table**: raw flagged candidates with coverage state straight from GSC
- **Embedded report**: the full markdown classification with per-action tables

The recommendation column tells you exactly what to do per URL:

> "Discovered but not yet indexed (39d old). Open GSC, inspect the URL, click Request Indexing. While there, confirm the page does not have a `noindex` meta tag and the canonical points to itself."

That's the action. Open GSC, do the click, mark the queue item as completed.

## How status changes

Items start at `status: queued`. When you handle a URL, edit `state/refresh-queue.json` and flip status to `completed` (or `in_progress` for ones you've started but not finished). The dashboard re-renders on every System 1, 2, 3, or 4 run.

Future enhancement: a small CLI command (`mark-refresh-done.py <url>`) to flip status without hand-editing JSON. We'll cover this in a follow-up tutorial.

## Tuning thresholds

The default age thresholds are in `scripts/refresh-scorer.py`:
- `stale_12mo`: age >= 365 days
- `aging`: 305 <= age < 365 days

Tighten by editing those numbers. For high-frequency niches (AI, SEO, finance) you might want stale_6mo at 180 days. For evergreen niches (recipes, woodworking) 540 days might be reasonable.

The flag-to-action mapping is in `prompts/refresh-recommender.md`. Edit there if you want different default actions.

## Going hands-off (optional)

If you'd rather not invoke the skill manually each week, schedule the same agent.

Trade-off: scheduled runs use `--dangerously-skip-permissions` because no human is there to approve tool calls. The agent's scope is narrow (sitemap fetch + GSC URL Inspection + writing to `state/` and `reports/`) and it never edits live content, so the risk is low.

**macOS, launchd:**

```bash
cp the-four-systems/system-4-refresh-recommender/launchd/com.example.seo-refresh-recommender.plist \
   ~/Library/LaunchAgents/

# Edit the path inside ProgramArguments to point at your project
nano ~/Library/LaunchAgents/com.example.seo-refresh-recommender.plist

launchctl load ~/Library/LaunchAgents/com.example.seo-refresh-recommender.plist
launchctl list | grep seo-refresh-recommender
```

Wednesday 09:13 lines up with the weekly content cadence: refresh actions surface mid-week so you can fold them into the rest of your SEO work before next Monday's onsite audit.

**Linux / WSL2, cron:**

```cron
13 9 * * 3 cd /path/to/seo-agents && ./coordinator.sh refresh-recommender >> /tmp/seo-refresh-recommender.log 2>&1
```

## Hard rules baked into the prompt

- Only acts on URLs in `state/refresh-candidates.json`. No invented alerts.
- Skips URLs already in `state/content-queue.json` with status queued/in_progress/needs_review.
- Recommendations cite the exact `coverage_state` from GSC verbatim, no paraphrasing.
- Money pages (commercial pages from `services.md`) get higher priority on the same flags.
- The state file is the source of truth; the markdown report is for humans.

## Troubleshooting

**"could not find a sitemap"** — Your robots.txt does not declare `Sitemap:`, and `/sitemap.xml`, `/sitemap-index.xml`, `/sitemap-0.xml` all 404. Add a Sitemap line to robots.txt or hard-code the path in the script.

**"SSL CERTIFICATE_VERIFY_FAILED"** — Your Python install is missing CA certs. The script uses `certifi` if available; if not, run `pip install certifi` in the GSC venv or use the system Python that ships with macOS.

**"GSC URL Inspection 429"** — Rate limit. Lower `--max-urls` or split the scan across days. URL Inspection allows ~600 calls per property per day.

**"All my posts are flagged not_indexed"** — Common when a site is brand-new and Google is still discovering it. Common patterns: the /blog/ hub itself is unknown to Google (this blocks crawl to all sub-posts), the sitemap is not submitted in GSC, or there's a missing internal link from the homepage. Layer 2 will spot patterns like this and flag them in the report's Notes section.

**"All my posts are flagged stale_12mo"** — Either your site genuinely has not been updated in a year, or the script's date extraction is failing for your platform. Check `state/refresh-candidates.json` `dates.source` field. If it's null, the page has no JSON-LD or article meta tags. Add them.

**"Refresh queue keeps recommending the same URLs even after I fixed them"** — GSC indexing status updates can take days. Re-run after Google re-crawls, the scan will see the new state and the actions will roll off.

## The full loop

You now have all four systems running:

- **System 1** (monthly): keyword research with AI fan-out, populates the content queue
- **System 2** (weekly + on-demand): drafts posts from the queue, ships markdown
- **System 3** (weekly): onsite audit (Lighthouse + on-page health) on your priority URLs
- **System 4** (weekly): finds stale posts and not-indexed URLs, tells you exactly what to do about each

One dashboard. ~$2 to $3 per month total in API spend. One workflow that catches new opportunities AND keeps your existing library indexed and current. Publish once, the systems make sure nothing gets lost.
