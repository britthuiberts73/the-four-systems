# System 1, Keyword Research with AI Fan-Out

> **Before reading this:** complete `system-0-prerequisites.md` first. You need DataForSEO MCP wired, the `context/` folder populated with your 5 business-info files, and Claude Code installed. If you skip System 0 the agent will produce generic output and you will blame the agent.


A scheduled Claude Code agent that takes a seed keyword once a month, generates the AI fan-out (the sub-queries Google AI Overviews and ChatGPT actually decompose your seed into), splits everything by search intent, scores it, and hands a ready-to-write post queue to your Content Writer.

When this is running, you stop guessing what to write about. You open one HTML file and see exactly which posts are next, ranked by opportunity, with internal links and external authorities pre-discovered.

## What you will end up with

- A keyword bank that grows every month: every variation you have ever researched, with volume, KD, intent, and which of your existing pages already covers it.
- A content queue that is the literal handoff to your writer: each item has a primary keyword, a fan-out cluster that becomes the post outline, internal-link targets crawled from your sitemap, and external authority candidates.
- An HTML dashboard you open in a browser to see the whole thing at a glance. The writer ticks off items as it ships them.
- A monthly launchd schedule that runs the whole thing for you. No reminder, no calendar, no Notion task.

## How it runs

**Default: a Claude Code skill (you trigger it).**

Drop one file into `.claude/skills/`. From any Claude Code session in this project, you say "research keywords for X" or "fan out the seed Y" and Claude invokes the skill. The skill enforces strict deduplication: it reads the bank first, refuses to re-research a seed that was last researched within 30 days unless you force it, and never emits a keyword that already exists in your bank. The dashboard accumulates run after run.

This is what most viewers should use. No `--dangerously-skip-permissions`, no plist editing, no surprise monthly bills. You get prompted to approve tool calls the first time, you click Allow, and after that the skill runs cleanly. Cost is pay-per-run, $0 if you don't fire it.

**Optional: hands-off via cron / launchd.**

If you want the system running on its own (the "I'll wake up Monday and the dashboard is full" experience), there's a "Going hands-off" section near the bottom. It uses launchd on macOS or cron on Linux to invoke the same agent in headless mode. Power-user upgrade, not required.

Both modes share the same state files and dashboard. A manual run on May 6 means the scheduled run on June 1 sees those keywords and skips them. The bank is the single source of truth.

## Why monthly, not weekly

Keyword research is not a high-frequency task. The fan-out for one good seed keyword (10 to 15 minutes of Claude time, ~$1 of DataForSEO credits) yields enough content ideas to feed a weekly writer for a month. Running this weekly mostly produces duplicates of what you already have in the bank, and the agent will refuse to re-research a seed within 30 days anyway. Once a month is the right rhythm. Use on-demand for everything else.

## Requirements

You need all of these. I list the cheapest viable option for each.

| Tool | Why | Cost |
| --- | --- | --- |
| **macOS, Linux, or WSL2** | Any modern OS. macOS uses launchd for the optional scheduling step; Linux/WSL2 use cron. | $0 |
| **Claude Code** | The CLI / TUI / IDE extension that runs the skill. Not the Claude Desktop chat app, that won't work for this. Install at https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview | Anthropic API usage, ~$0.30 to $0.80 per run with Sonnet |
| **Anthropic API key** | For Claude Code. `claude /login` prompts you. | Pay-as-you-go |
| **Python 3.10+** | One small script renders the HTML dashboard, no external libs needed. macOS ships with python3. | $0 |
| **Git** | The coordinator auto-commits each run so you have a full audit trail of every keyword discovered. | $0 |
| **DataForSEO account** | The single best source for fan-out, volume, KD, and ChatGPT scrape data. ~$0.10 to $1 per agent run. | $50 minimum top-up, lasts months |
| **A target site with a sitemap.xml** | The agent crawls it to discover internal-link targets and detect coverage. | $0 |

DataForSEO is the only paid dependency you need. If you already have Ahrefs or SEMrush, you cannot use them here: their MCP integrations do not expose the AI fan-out endpoint that ChatGPT scrape gives you. DataForSEO is the cheapest reliable source for that data in 2026.

## Folder structure

You will end up with this layout. Keep these names exactly as written; the scripts reference them.

```
your-project/
├── .mcp.json                              ← DataForSEO MCP wiring
├── coordinator.sh                         ← the runner
├── prompts/
│   └── keyword-researcher.md              ← the agent's instructions
├── context/
│   └── site-config.md                     ← your site's voice, audience, in-scope topics
├── state/
│   ├── keyword-bank.json                  ← rolling keyword database
│   ├── content-queue.json                 ← handoff to the writer
│   ├── seed-keywords.txt                  ← list of seeds, one per line
│   ├── agent-log.json                     ← run history
│   └── .lock                              ← prevents concurrent runs
├── scripts/
│   ├── render-html-report.py              ← builds the dashboard
│   └── tutorial-logger.sh                 ← optional, logs each run
├── output/
│   └── keywords/
│       ├── dashboard.html                 ← THE FILE YOU OPEN
│       ├── 2026-05-06-dashboard.html      ← dated snapshots
│       └── 2026-05-06-<seed>.csv          ← per-run CSV
├── reports/                               ← markdown agent reports per run
└── logs/
```

## Setup, step by step

### 1. Create the folder and files

Working folder anywhere on disk. From a terminal:

```bash
mkdir -p seo-agents/{prompts,context,state,scripts,output/keywords,reports,logs}
cd seo-agents
```

### 2. Wire DataForSEO into Claude Code

Get a DataForSEO username and password (their dashboard, top right). Drop them into a `.mcp.json` file at the root of your `seo-agents/` folder:

```json
{
  "mcpServers": {
    "dfs-mcp": {
      "command": "npx",
      "args": ["-y", "dataforseo-mcp-server"],
      "env": {
        "DATAFORSEO_USERNAME": "your-username",
        "DATAFORSEO_PASSWORD": "your-password"
      }
    }
  }
}
```

When Claude Code starts in this folder, it auto-discovers `.mcp.json` and exposes ~70 DataForSEO tools as `mcp__dfs-mcp__*`. Verify with:

```bash
claude -p "List MCP tools whose name starts with mcp__dfs" --dangerously-skip-permissions
```

You should see a long comma-separated list including `mcp__dfs-mcp__ai_optimization_chat_gpt_scraper`, `mcp__dfs-mcp__dataforseo_labs_google_keyword_ideas`, and `mcp__dfs-mcp__dataforseo_labs_bulk_keyword_difficulty`. These are the three the agent uses.

### 3. Write your site config

`context/site-config.md` tells the agent who you are. This is the prompt's source of truth for voice, audience, in-scope topics, and out-of-scope topics. The agent reads this every run.

Write it like a brief to a freelancer: what your site does, who reads it, what topics are in scope, what topics are out of scope, what brand voice rules to follow. Reference your existing wins (real numbers only, never fabricate). 200 to 400 words is enough.

### 4. Seed the state files

Initialise three JSON files with these exact contents:

`state/keyword-bank.json`:
```json
{ "schema_version": 1, "site": "yoursite.com", "last_updated": null, "keywords": [] }
```

`state/content-queue.json`:
```json
{
  "schema_version": 2,
  "status_values": ["queued", "in_progress", "written", "skipped"],
  "items": []
}
```

`state/seed-keywords.txt`: 8 to 12 seeds, one per line. These are broad topics, not long-tail. The agent will fan out from each. Examples for an AI-SEO niche:

```
query fan out ai search
ai overviews seo
content decay detection
programmatic seo with ai
schema markup for ai search
```

### 5. Drop in the agent prompt

The full prompt is reproduced at the bottom of this doc. Save it to `prompts/keyword-researcher.md`. It tells the agent exactly which DataForSEO tools to call, how to score keywords, and how to format the queue items.

### 6. Drop in the coordinator and renderer

Both are reproduced at the bottom of this doc. Save them to:
- `coordinator.sh` (chmod +x)
- `scripts/render-html-report.py` (chmod +x)

### 7. First run as a skill

Save the skill file at `.claude/skills/keyword-researcher.md` in your project. Open Claude Code in this folder, and just say:

```
research keywords for "your seed keyword here"
```

Claude picks up the skill, reads the bank, refuses to re-research seeds touched in the last 30 days, fans out via DataForSEO, scores, classifies by intent, queues priority-1 items for the Content Writer, and updates the dashboard. Total run is 5 to 8 minutes.

The first time it tries to call a tool (DataForSEO MCP, Bash for git commits, Write for state files), Claude Code asks you to approve. Click Allow once, choose "Always allow this tool" if you want, and subsequent runs are friction-free. To skip the approval prompts entirely, copy `.claude/settings.local.json.example` from the repo and tweak.

When the skill finishes, it prints the dashboard path:

```bash
open ai-ranking-automations/seo-agents/output/keywords/dashboard.html
```

You should see stat tiles at the top, queue cards in the middle, and the full bank table at the bottom. Each queue card is collapsed by default; click to expand and see fan-out cluster, internal-link targets, external authority candidates, and notes for the writer.

### Why minute 3 and not 0

Every cron tutorial uses `0 9 * * *`. So every Mac on Earth fires at 09:00:00. Pick an off-minute (3, 7, 13, 23, 47) and you avoid the thundering-herd against shared APIs. Trivial detail, but it matters when you do schedule (next section).

## Reading the output

The dashboard has three sections.

**Stats row.** Six tiles. The two you care about most: "Priority 1" (high-value keywords with no current coverage) and "Queued for writer" (the System 2 backlog). If "Queued" is zero and the bank is full, the agent ran but nothing new cleared priority-1; your seeds are exhausted and you should add more to `seed-keywords.txt`.

**Content queue cards.** Each card is one post the writer will draft, ordered by status (queued first, then in_progress, then written). Click to expand. The fan-out cluster is the post outline, the internal-link targets are pre-resolved URLs from your sitemap, and the notes field is strategic context the agent picked up during research. The writer reads all of this.

**Keyword bank table.** Every keyword you have ever researched, sortable. Color-coded priority (red 1, amber 2, grey 3). The "Coverage" column links to existing pages on your site that already target the keyword (so you do not re-write them).

## How the writer ticks off completed posts

When System 2 (the Content Writer) runs and ships a post, it updates the matching queue item:

```json
{
  "id": "2026-05-06-how-to-rank-in-ai-overviews",
  "status": "written",
  "written_at": "2026-05-08T11:14:00Z",
  "post_url": "https://yoursite.com/blog/how-to-rank-in-ai-overviews/",
  "primary_keyword": "how to rank in ai overviews",
  ...
}
```

The dashboard re-renders on every coordinator run, so the next time anything fires (even an unrelated agent), the green "WRITTEN" badge and the link to the live post appear on that card. This is the hand-back loop: System 1 hands work to System 2, System 2 reports back to the same queue, System 1 sees what's been done and what is still open.

If you want to skip an item (for example, you decided not to write that post after all), edit `state/content-queue.json` by hand and set `"status": "skipped"`. The dashboard will show it greyed out.

## Going hands-off (optional)

If you'd rather have the system run without you remembering to invoke it, schedule the same agent via launchd (macOS) or cron (Linux/WSL). The skill and the scheduled run share state; the bank, the queue, and the dashboard don't care which path triggered the work.

This step is optional. If you skip it, you simply invoke the skill manually each month. Most users get fine results that way.

**Trade-off to know going in.** Scheduled runs use `claude -p ... --dangerously-skip-permissions` because no human is there to click Allow on tool calls. The flag bypasses every permission prompt for that single invocation. For a tightly-scoped agent like this one (it only touches its own folder + DataForSEO + git), the risk is low. For a general-purpose agent, you'd want to be more cautious. Make the call deliberately.

**macOS, launchd:**

Save this plist as `~/Library/LaunchAgents/com.<yourname>.seo-keyword-researcher.plist`. Replace the path inside ProgramArguments with your actual project path.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.yourname.seo-keyword-researcher</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>-c</string>
    <string>cd "/path/to/seo-agents" &amp;&amp; ./coordinator.sh keyword-researcher</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Day</key><integer>1</integer>
    <key>Hour</key><integer>9</integer>
    <key>Minute</key><integer>3</integer>
  </dict>
  <key>StandardOutPath</key><string>/tmp/seo-kw-researcher.stdout</string>
  <key>StandardErrorPath</key><string>/tmp/seo-kw-researcher.stderr</string>
</dict>
</plist>
```

Load it once:

```bash
launchctl load ~/Library/LaunchAgents/com.yourname.seo-keyword-researcher.plist
launchctl list | grep seo-keyword-researcher
```

If your Mac is asleep at 09:03 on the 1st, launchd runs the job the next time the Mac wakes. This is why we use launchd over cron on macOS.

**Linux / WSL2, cron:**

```cron
3 9 1 * * cd /path/to/seo-agents && ./coordinator.sh keyword-researcher >> /tmp/seo-kw-researcher.log 2>&1
```

The coordinator prepends the right PATH for cron-spawned shells; check the top of `coordinator.sh` if you need to adjust for your environment.

After installing the schedule, watch `/tmp/seo-kw-researcher.stderr` for the next few runs. If anything errors, debugging is the same as a manual `./coordinator.sh keyword-researcher` invocation.

## Costs per run

Real numbers from the May 6, 2026 run on seed "query fan out ai search":

- Duration: 6.7 minutes
- DataForSEO calls: ~12 (one chat_gpt_scraper, one keyword_ideas, three keyword_suggestions, one bulk_keyword_difficulty for 35 keywords, plus a sitemap fetch)
- DataForSEO spend: ~$0.30
- Claude API spend (Sonnet): ~$0.40
- Total: under $1 per monthly run, ~$10/year

If you run it weekly instead of monthly the cost goes 4x but the new-keyword yield goes maybe 1.2x. Monthly is the right cadence.

## Troubleshooting

**"claude CLI not authenticated"** — Run `claude /login` once in a normal terminal session. The credentials persist for the launchd-spawned shell.

**"Lock file present"** — A previous run crashed mid-flight. The coordinator auto-clears locks older than 1 hour, but you can `rm state/.lock` to clear immediately.

**"DataForSEO 401"** — Your username/password in `.mcp.json` are wrong. They are an account login, not an API token, and the password is case-sensitive.

**Seeds keep producing the same keywords** — Your bank is saturated for those topics. Add fresh seeds to `seed-keywords.txt`. The agent rotates seeds based on `last_researched` so older seeds get re-explored after a few months as DataForSEO's data refreshes.

**Dashboard shows nothing** — Open `state/keyword-bank.json`. If it is empty `{"keywords": []}`, the agent has not run successfully yet. Check `reports/` for the latest run's markdown report.

## What's next

System 1 only finds the work. System 2 (the Content Writer) reads `content-queue.json` on its own monthly schedule, drafts the post, and marks the item written. We build that next.

---

# Appendix, full file contents to copy

(Coordinator script, agent prompt, HTML renderer, and seed file are all in the project repo at `ai-ranking-automations/seo-agents/`. Copy them as-is.)
