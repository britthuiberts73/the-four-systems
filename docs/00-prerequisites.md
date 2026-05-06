# System 0, Prerequisites

Before you build any of the four systems, set up the toolchain and the business-info folder. This is the part of the tutorial nobody tells you about and it is the difference between systems that work for you and systems that produce generic AI slop.

You do this once. It takes about 30 minutes. You never touch most of it again.

## Why Claude Code, not Claude Desktop

If your first instinct was to try the Claude Desktop app: stop. Desktop is a chat UI. It can't run a skill against your project files, can't be invoked by cron or launchd, and uses a different MCP surface (Settings → Connectors instead of project-local `.mcp.json`). You will hit blockers within 10 minutes.

Use Claude Code: the CLI / TUI / VS Code / JetBrains extensions. Same model, different surface. Designed for project-level work and automation. Free to install, the API costs are the same.

In the four-systems tutorial:
- **Skills** (the default mode) run inside an interactive Claude Code session. You say "research keywords for X" and the skill fires. You approve tool calls the first time, after that they auto-allow.
- **Optional scheduled mode** (covered in each system's "Going hands-off" section) calls `claude -p ... --dangerously-skip-permissions` from launchd or cron. Headless. No user in the loop.

Either way, Claude Code is the only client that works.

## Part A: Tools to install

| Tool | Why | How |
| --- | --- | --- |
| **macOS, Linux, or WSL2** | Skills run on any modern OS. Optional scheduled mode uses launchd on Mac or cron on Linux/WSL2. | Already have it. |
| **Claude Code** | The CLI / TUI / IDE extension. Skills run inside an interactive session; optional scheduled mode uses `claude -p` headless. **Not the Claude Desktop chat app, that won't work.** | https://docs.anthropic.com/en/docs/agents-and-tools/claude-code |
| **Anthropic API key** | Powers Claude Code. Pay-as-you-go. Budget $5 to $15/month for the four systems combined. | `claude /login` |
| **Python 3.10+** | A few small scripts (HTML renderer, GSC pulls, refresh scorer). No external libraries. | macOS ships with it. |
| **Node.js 18+** | DataForSEO MCP runs via `npx`. | https://nodejs.org or `brew install node` |
| **Git** | Every agent auto-commits its run, so you have a full audit trail. | `brew install git` |
| **uv (optional but recommended)** | Fast Python virtualenv for the GSC MCP server. | `pip install uv` |

Smoke test before continuing:

```bash
claude --version          # >= 2.x
python3 --version         # >= 3.10
node --version            # >= 18
git --version             # any modern
```

If `claude` is not on your PATH, the scheduled jobs will fail silently. Fix the PATH before continuing.

### Optional: pre-allow common tools so the skills run friction-free

Without this, the first time a skill calls `Bash`, `Write`, or an MCP tool, Claude Code asks you to approve it. Choose "Always allow this tool" and the prompt stops. Or set up the allowlist once and skip the prompts entirely.

Drop a `.claude/settings.local.json` at your project root:

```json
{
  "permissions": {
    "allow": [
      "Read",
      "Write",
      "Edit",
      "Bash(./coordinator.sh:*)",
      "Bash(python3 scripts/*)",
      "Bash(git status)",
      "Bash(git add:*)",
      "Bash(git commit:*)",
      "Bash(open:*)",
      "Bash(launchctl list:*)",
      "WebFetch",
      "mcp__dfs-mcp__*",
      "mcp__gsc__*"
    ]
  }
}
```

These rules cover everything the four systems do: read/write project files, run the coordinator and the renderer, commit changes, fetch web pages, hit DataForSEO and GSC. Anything outside this allowlist still prompts. You can tighten or loosen as you go.

A copy of this file ships in the repo as `.claude/settings.local.json.example`.

## Part B: MCP connections

The four systems use exactly two MCP servers. You wire both at the project root in a `.mcp.json` file. When Claude Code starts in a folder containing this file, it auto-loads the servers.

### MCP 1: DataForSEO (`dfs-mcp`) — required for Systems 1, 2, 3, 4

Used for: AI fan-out, search volume, keyword difficulty, related keywords, SERP scraping, ChatGPT scraper, content gap analysis.

**Account:** https://dataforseo.com → sign up → top-up $50 (lasts months for this workload).

**Get credentials:** Dashboard → top-right → API Access. The username is your email, the password is shown once on signup (or rotate from the dashboard).

**Cost:** ~$0.30 per System 1 run (monthly), ~$0.10 per System 2 run (weekly), ~$0.18 per System 3 run (weekly Lighthouse + on-page audit), ~$0.05 per System 4 run (weekly GSC decay scoring). Roughly $2 to $3 per month total.

**Wire it:**

```json
{
  "mcpServers": {
    "dfs-mcp": {
      "command": "npx",
      "args": ["-y", "dataforseo-mcp-server"],
      "env": {
        "DATAFORSEO_USERNAME": "you@example.com",
        "DATAFORSEO_PASSWORD": "your-password"
      }
    }
  }
}
```

Verify:

```bash
claude -p "List MCP tools whose name starts with mcp__dfs" --dangerously-skip-permissions
```

You should see ~70 tools listed. Critical ones the systems use: `mcp__dfs-mcp__ai_optimization_chat_gpt_scraper`, `mcp__dfs-mcp__dataforseo_labs_google_keyword_ideas`, `mcp__dfs-mcp__dataforseo_labs_google_keyword_suggestions`, `mcp__dfs-mcp__dataforseo_labs_bulk_keyword_difficulty`, `mcp__dfs-mcp__serp_organic_live_advanced`.

### MCP 2: Google Search Console (`mcp-gsc`) — required for System 4 (refresh recommender)

System 3 (onsite audit) does NOT need GSC: it uses DataForSEO's `on_page_lighthouse` and `on_page_instant_pages` only. System 4 (refresh recommender) is the one that reads GSC for impression delta, position drift, and CTR outliers.

If you skip GSC entirely, Systems 1, 2, 3 still work. You just lose the decay-detection loop in System 4.


Used for: pulling 28-day query/page metrics, detecting decay, flagging position 5-15 pages, indexing status.

You have two install paths.

**Path 1, official Google Search Console MCP server (recommended):**

```bash
git clone https://github.com/openworkspace-ai/mcp-gsc.git ~/seo-tools/mcp-gsc
cd ~/seo-tools/mcp-gsc
uv venv && uv sync
```

You need a Google service account with read access to your GSC property:
1. https://console.cloud.google.com → create or pick a project
2. Enable the "Google Search Console API"
3. APIs & Services → Credentials → Create credentials → Service account
4. Download the JSON key, save as `~/seo-tools/mcp-gsc/service_account_credentials.json`
5. https://search.google.com/search-console → Settings → Users and permissions → add the service account email as a Restricted user

**Path 2, OAuth-based (simpler if you don't want service accounts):** Skip this for now, the systems all use service accounts.

Wire it into your project's `.mcp.json` next to `dfs-mcp`:

```json
{
  "mcpServers": {
    "dfs-mcp": { "...": "..." },
    "gsc": {
      "command": "uv",
      "args": ["run", "--directory", "/Users/you/seo-tools/mcp-gsc", "python", "gsc_server.py"]
    }
  }
}
```

Verify:

```bash
claude -p "List MCP tools whose name starts with mcp__gsc" --dangerously-skip-permissions
```

You should see search analytics, sitemaps, URL inspection, and indexing tools.

### What about Webflow, Notion, ClickUp, Slack?

Not needed for the four systems. If you publish to Webflow you can add `webflow-mcp` to System 2 later, but for the tutorial we publish to a static site (Astro, Hugo, Next.js, anything markdown-based) and skip Webflow.

## Part C: The business-info folder

This is the most important 20 minutes of setup. The agents are only as smart as the brief you give them. Generic input produces generic output.

You have two ways to do this:

**Easy path (recommended): run the bootstrapper skill.** The repo ships with a `context-bootstrapper` skill that interviews you for 15 to 20 minutes, fetches your website to pre-fill what it can see, and writes all 8 files for you. Drop the skill file at `.claude/skills/context-bootstrapper.md`, open Claude Code in your project, and say:

```
bootstrap my context folder
```

Or:

```
set up the business info files for the four systems
```

Claude picks up the skill automatically (because of its `description` field), greets you, asks for your URL, fetches your homepage and a couple of blog posts if you have them, then walks you through 8 sections of questions. After each section the file is saved to disk, so a stopped session preserves progress. To regenerate a single file later, run the skill and say "regenerate experience-notes.md".

**Manual path:** create the 8 files by hand using the templates below. Slower but exposes more of what's going on.

Either way, the final folder looks like this:

```
context/
├── site-config.md          ← REQUIRED — what the site is, in/out of scope topics
├── audience.md             ← REQUIRED — who reads it, what they already know, what they hate
├── tone-of-voice.md        ← REQUIRED — voice rules, formatting rules, sample phrases
├── experience-notes.md     ← REQUIRED — real wins, stories, opinions, customer situations
├── services.md             ← REQUIRED — what the business sells, pricing, edge cases
├── brand-guidelines.md     ← REQUIRED — banned words, regulated claims, competitors to exclude
├── competitors.md          ← REQUIRED — who else ranks, content gaps
├── author.md               ← REQUIRED — Person/Author schema for E-E-A-T
└── publishing.json         ← OPTIONAL — only if auto-publishing to an Astro site
```

### `context/site-config.md`

Identity and scope. Read by every agent every run. Voice rules live in `tone-of-voice.md` (separate file).

```markdown
# Site: yoursite.com

## What it is
One paragraph. What you sell, who buys it, what makes it different. Be specific.
Bad: "We help businesses with SEO."
Good: "Your Product is a Cloudflare-Workers-based dashboard that flags
content decay and indexing problems for AI-SEO operators. $19/month, 200 paid users."

## Topics in scope
List 8 to 15 topics this site is allowed to cover. The agents will reject
fan-out variations that don't match.

## Topics out of scope
Equally important. List things that look related but you don't want to write
about. Black hat, beginner content, tangents.
```

### `context/tone-of-voice.md`

The voice the Content Writer matches. Critical for non-generic output.

```markdown
# Tone of voice

## Voice rules
- Direct, concrete, practical. No fluff, no hype, no emojis.
- Senior operator talking to operators.
- Short sentences. Specific numbers. Real examples over generic claims.

## Hard formatting rules
- Never use em dashes. Use colons, commas, parentheses, or separate sentences.
- No exclamation marks.
- No "in conclusion", "in today's world", "it's important to note".

## Sample phrases this voice uses
- "Real numbers, real outcomes."
- "Here is what actually works."

## Phrases this voice avoids
- "Game changer"
- "Synergy"
- "Best in class"

## Sample paragraph (real example from existing post)
> Most SEO is reactive. You notice traffic dropped, you go looking. This is the
> opposite. The system tells me what's wrong, and Claude is already fixing it
> before I open the dashboard.
```

### `context/services.md`

What the business actually sells. The Content Writer references this verbatim for any business-specific factual claim.

```markdown
# Services and offerings

## What we sell
- Your Product: $19/month, monitors GSC for decay and indexing issues
- Free fan-out tool at /free-tools/fan-out-queries/

## Pricing
| Tier | Price | What's included |
| --- | --- | --- |
| Free | $0 | Fan-out tool, 1 site, weekly check |
| Pro | $19/mo | Unlimited sites, daily check, alert API |

## Edge cases the writer should know
- We do not serve enterprise (>1000 URLs). Direct them to a partner.
- Free tier requires Google account, no credit card.

## Frequently answered questions
### How is this different from Ahrefs?
Your Brand focuses on decay and indexing alerts, not keyword research.
We complement Ahrefs, we don't replace it.
```

### `context/brand-guidelines.md`

Hard rules the writer must follow. Without this file, the agent silently violates constraints.

```markdown
# Brand guidelines

## Banned words and phrases
- "game changer"
- "best in the world"
- "guaranteed rankings"

## Competitor names that must not appear
- DirectRivalA
- DirectRivalB

## Brand spelling and capitalization
- "Your Product" (not "Datawise" or "data wise")

## Regulated claims to avoid
- Do not promise specific ranking positions or traffic numbers.
- Do not claim Google partnership we do not have.

## Formatting rules
- US English spelling.
- USD pricing.
- No all-caps headings.
```

### `context/audience.md`

Who reads your content, what they already know, what they care about.

```markdown
# Audience

## Primary persona
- Job title or role
- Skill level (assume they know X, do not over-explain Y)
- What problem brings them to your site
- What they have already tried
- What they are willing to pay for

## What this audience hates
- Listicles with no opinion
- "What is SEO" intro paragraphs
- Vague advice
- Affiliate spam disguised as guides
```

### `context/competitors.md`

Who ranks for your keywords. The Keyword Researcher uses this to skip topics where competitors have a moat, the Content Writer uses it to differentiate.

```markdown
# Competitors

## Direct (same product space)
- competitorA.com — strengths, weaknesses, gaps
- competitorB.com — same

## Indirect (different product, same audience)
- ahrefs.com/blog — comprehensive but corporate, slow on AI topics
- searchengineland.com — news, not how-to

## Their content moat
List the topics where competitors have 5+ posts already ranking. The
Content Writer will avoid these unless we have a genuinely new angle.

## Their content gap
Topics nobody is covering well. This is where Systems 1 and 2 should focus.
```

### `context/experience-notes.md`

Real wins, stories, opinions, recurring customer situations. This is the file that lifts your posts above generic AI content. The Content Writer pulls first-person stories from here when relevant; if the file has nothing matching the post topic, the writer automatically engages research-only mode (no fabricated experience, no "in my experience" phrasing).

```markdown
# Experience notes

## Real wins (numbers only)
- yoursite.com/blog/X ranks position 6 for "query Y" (GSC, last 28 days)
- yoursite.com/blog/Z, 1,442 impressions in 3 months, position 7

## Origin story
Why we built this product. The story you tell new customers.

## Strong opinions
- AI Overviews are not a Google update, they're a content distribution change.
  Sites that treat them like an algorithm tweak miss the structural shift.

## Recurring customer situations
- Agencies bring us pages stuck at position 11-15 for 6+ months.
  Pattern: thin content + outdated dates. Fix: refresh + reindex.

## Stories the writer can pull from
### The first decay alert
Last September, our own homepage dropped 30% impressions in two weeks.
Old me would have noticed in November. The decay alert pinged me on day 14.
Fixed it in an afternoon. That's why we built the alert system.
```

### `context/author.md`

For E-E-A-T schema and AI Overviews citation worthiness. AI Overviews preferentially cite authors with verifiable bylines.

```markdown
# Author

## Identity
- Name: Jane Doe
- Title: Founder, Your Product
- Email: jane@your-site.com
- Avatar URL: https://yoursite.com/img/jane.jpg

## Credentials (only verifiable ones)
- 8 years SEO at <publicly listed companies>
- Speaker at <conference, year>
- Author of <book or major publication>

## Social profiles for sameAs schema
- https://x.com/janedoe
- https://www.linkedin.com/in/janedoe/
- https://github.com/janedoe

## Public bio (used as Author schema "description")
Two to three sentences. Third person.
```

The Content Writer reads this every run and emits a Person + Author schema block in every published post.

## Part C.5: Run the bootstrapper (if you took the easy path)

Drop the bootstrapper skill into your project's `.claude/skills/` directory. The file is in the public repo at `system-0-prerequisites/skill/context-bootstrapper.md`.

```bash
mkdir -p .claude/skills
cp the-four-systems/system-0-prerequisites/skill/context-bootstrapper.md .claude/skills/
```

Open Claude Code in your project and say: `bootstrap my context folder`.

15 to 20 minutes later you have all 8 files (plus optional `publishing.json`) populated with answers from your interview, voice samples picked up from your existing site, and zero em dashes.

Edit any file by hand at any time. The agents re-read them on every run.

## Part D: First-time verification

Before you build System 1, prove the toolchain works:

```bash
mkdir -p test-prereq && cd test-prereq

# 1. Drop your .mcp.json here

# 2. Confirm both MCPs load
claude -p "List MCP tools whose name contains 'dfs' or 'gsc'. Just count them and print the count." \
  --dangerously-skip-permissions

# 3. Confirm DataForSEO is alive
claude -p "Use mcp__dfs-mcp__dataforseo_labs_google_keyword_overview to look up search volume for the keyword 'test'. Print the volume only." \
  --dangerously-skip-permissions

# 4. Confirm GSC is alive (replace yoursite.com)
claude -p "Use mcp__gsc to fetch the top 5 queries for yoursite.com over the last 7 days. Print as a markdown table." \
  --dangerously-skip-permissions
```

If any of those fail, fix the underlying problem before building System 1. Debugging MCP issues inside an agent run is much harder than debugging them from a one-shot.

## Part E: The repo plan (for tutorial viewers)

The four systems live in a public repo so anyone watching the YouTube tutorial can clone it, drop their `.mcp.json` and `context/` files in, and run.

**Repo:** `github.com/example/the-four-systems` (planned, public, MIT)

**Layout:**

```
the-four-systems/
├── README.md                          ← quickstart + link to YouTube
├── system-0-prerequisites.md          ← THIS FILE
├── system-1-keyword-research/
│   ├── README.md
│   ├── coordinator.sh
│   ├── prompts/keyword-researcher.md
│   ├── scripts/render-html-report.py
│   ├── scripts/tutorial-logger.sh
│   ├── state/                         ← schema-only seed JSONs (empty arrays)
│   ├── launchd/com.example.seo-keyword-researcher.plist
│   └── skill/keyword-researcher.md    ← drop into .claude/skills/
├── system-2-content-writer/
│   └── ...
├── system-3-onsite-audit/
│   └── ...
├── system-4-refresh-recommender/
│   └── ...
├── context-templates/                 ← blank versions of the 8 business-info files
│   ├── site-config.md.example
│   ├── audience.md.example
│   ├── tone-of-voice.md.example
│   ├── experience-notes.md.example
│   ├── services.md.example
│   ├── brand-guidelines.md.example
│   ├── competitors.md.example
│   ├── author.md.example
│   └── publishing.json.example        ← optional, for Astro auto-publish
├── system-0-prerequisites/
│   └── skill/
│       └── context-bootstrapper.md    ← drop into .claude/skills/
└── .mcp.json.example                  ← redact your real creds
```

The viewer's flow:
1. Clone the repo
2. Copy `.mcp.json.example` → `.mcp.json`, fill in DataForSEO + GSC creds
3. Drop both skills into `.claude/skills/`:
   - `system-0-prerequisites/skill/context-bootstrapper.md`
   - `system-1-keyword-research/skill/keyword-researcher.md`
4. In Claude Code, say `bootstrap my context folder`. The bootstrapper interviews you for 15-20 min, fetches your website, and writes all 8 context files.
5. In Claude Code, say `research keywords for <your seed>`. Open the dashboard. Ship.

We will publish the repo when System 1 ships in the tutorial. Future systems get added one by one as the video covers them.

## What to do next

Once Parts A through D check out, go to **system-1-setup.md**.
