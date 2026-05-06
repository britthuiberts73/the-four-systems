# System 2, The Content Writer

> **Before reading this:** complete `system-0-prerequisites.md` (run the `context-bootstrapper` skill so all 8 context files exist) and `system-1-setup.md` (so you have items in the content queue). System 2 only writes posts that System 1 queued.

A scheduled or on-demand Claude Code agent that takes one queued item from System 1, walks the 5-step writing workflow (brief, research, outline, draft, review), produces a clean markdown file, and ticks the queue item off so the dashboard shows it shipped.

You get to choose at every run: high-craft mode where you collaborate (30 to 45 min, the highest quality posts you'll get out of an LLM) or auto-pilot mode where it just ships a draft for you to review the next morning.

## What you end up with

- A markdown file at `output/posts/<YYYY-MM-DD>-<slug>.md` with full SEO front-matter.
- The queue item flipped from `queued` to `written` with a green badge on the dashboard and a link to the post.
- An optional auto-publish to Astro+Cloudflare if you have that wired (skipped silently otherwise: most people upload by hand).
- A run report in `reports/` documenting which sources were used, which fan-out variations were covered, and any review-checklist failures that got fixed.

## The 5-step workflow (adopted with 5 amendments)

This builds on the well-known interactive blog-writing workflow:

1. **Brief**: confirm topic, target keyword, takeaway. Ask for any topic-specific personal experience.
2. **Research**: present 8 to 12 high-quality sources. Wait for approval.
3. **Outline**: title (with target keyword), H2/H3, capsule marks, internal-link picks, experience callouts, business-fact callouts. Wait for approval.
4. **Draft**: TL;DR block above intro, Content Capsule on 60-70% of H2s, inline citations only (no reference list), no em dashes, no fabricated experience.
5. **Review**: 16-item self-checklist. Fix any failure. Ship.

What System 2 adds on top:

- **Queue integration**: Step 1 reads the System 1 content queue and offers you the top 3 priorities. Step 6 (new) marks the item written.
- **Two modes**: same prompt, interactive with approvals (skill) or auto-pilot with no approvals (scheduled).
- **Two publish modes**: markdown-only by default, optional Astro auto-publish if `context/publishing.json` exists.
- **Fan-out coverage tracked**: every variation in the queue item's `fan_out_cluster` either becomes a section or gets recorded as `fan_out_dropped: <reason>` in the front-matter. AI Overviews need fan-out coverage; this makes that auditable.

## How it runs

**Default: skill, interactive (high-craft mode).**
You invoke the `content-writer` skill in Claude Code by saying "write the next post" or "let's draft a blog post". Claude lists the top 3 queued items, you pick one, you get asked about topic-specific experience, you approve the source list, you approve the outline, then it drafts. ~30-45 min of light interaction. This is the highest-quality output you'll get from an LLM writer because the human stays in the loop on the three decisions that matter most: topic, sources, outline.

**Optional: scheduled auto-pilot (the "wake up to a draft" experience).**
Same agent, scheduled to run every Tuesday at 10:07 local time. Picks the top queued item, scans `experience-notes.md` for matching stories (engages research-only mode if none match), commits to one source list and one outline without asking, drafts, self-reviews, ships markdown. You read the draft Wednesday morning, tweak anything you don't love, upload. See the "Going hands-off" section near the bottom for setup.

You can run both. Auto-pilot fills the calendar; skill mode is for the few flagship posts each month where you want to inject fresh stories.

## Two publishing modes (independent of A/B)

**Default: markdown-only.** A clean `.md` file with full SEO front-matter lands in `output/posts/`. You upload to WordPress, Webflow, Notion, Ghost, Substack, anywhere. Roughly 90% of users will use this.

**Optional: Astro + git auto-publish.** If `context/publishing.json` exists pointing at a local Astro repo, the writer additionally:
1. Copies the markdown into the Astro repo's content collection
2. Commits on a `claude/post-<slug>` branch (default: draft) or main (if you set `branch_strategy: live`)
3. Pushes to GitHub
4. Cloudflare Pages deploys automatically

If `publishing.json` does not exist, this step silently no-ops. Set it up later when you migrate to Astro; nothing else changes.

## Costs per post

- Claude API (Sonnet, 25-35k tokens for full 5-step run): $0.20 to $0.40
- DataForSEO (SERP scrape for source discovery): $0.05 to $0.10
- WebFetch on 8-12 source URLs: free
- Total per post: $0.30 to $0.50

If you ship 4 posts per month: $1.20 to $2 in writer costs. Combined with System 1 ($1/month), the whole content engine is $2-3/month.

## Setup, step by step

You already did most of the setup in System 0. The new bits are tiny.

### 1. Confirm context files exist

```bash
ls context/
```

You should see all 8 files: `site-config.md`, `audience.md`, `tone-of-voice.md`, `experience-notes.md`, `services.md`, `brand-guidelines.md`, `competitors.md`, `author.md`. If any are missing, run the `context-bootstrapper` skill before continuing. The Content Writer fails loudly if any are missing.

### 2. Drop in the skill

```bash
cp the-four-systems/system-2-content-writer/skill/content-writer.md .claude/skills/
```

That's it. Open Claude Code in your project and say:

```
write the next post
```

Claude picks up the skill, reads all 8 context files, lists the top 3 queued items from `state/content-queue.json`, and walks you through the 5-step interactive flow.

### 3. (Optional) Wire Astro auto-publish

If you have an Astro site on Cloudflare Pages and want auto-deploy, create `context/publishing.json`:

```json
{
  "mode": "astro",
  "repo_path": "~/code/my-astro-site",
  "content_dir": "src/content/blog",
  "branch_strategy": "draft",
  "draft_branch_prefix": "claude/post-",
  "public_url_base": "https://yoursite.com"
}
```

`branch_strategy` options:
- `"draft"` (recommended): every post pushes to a fresh `claude/post-<slug>` branch. You open a PR when you're ready. Cloudflare Pages will deploy the preview. Safe.
- `"live"`: pushes straight to `main`. Cloudflare deploys to production. Faster but no review gate.

If you don't have an Astro site, skip this entirely. The writer outputs markdown and you upload by hand. No code path changes either way.

### 5. First run, recommended path

Don't start with the schedule. Run Mode A first to validate the prompt produces something good for your business:

```
In Claude Code, in your project folder:

> write the next post

Claude:
  Here are the top 3 queued posts:
  1. how to rank in ai overviews (vol 320, KD 25, informational)
  2. how to optimize for ai overviews (vol 110, KD 35, informational)
  ...
  Which one?

You:
  1

[interactive flow continues]
```

If the draft is solid, enable Mode B. If the draft has issues, edit `prompts/content-writer.md` (the source of truth) and `context/tone-of-voice.md` until the output matches what you want. Both modes share the prompt; fixes apply everywhere.

## Reading the output

Every draft has front-matter at the top with everything you need to audit the run:

```yaml
---
id: 2026-05-06-how-to-rank-in-ai-overviews
title: "How to rank in AI Overviews: a 2026 SEO playbook"
slug: how-to-rank-in-ai-overviews
primary_keyword: how to rank in ai overviews
intent: informational
target_word_count: 1800
word_count: 1842
sources_cited:
  - https://blog.google/products/search/...
  - https://developers.google.com/...
internal_links:
  - https://www.your-site.com/blog/query-fan-out-ai-search/
fan_out_covered:
  - how to optimize for ai overviews
  - what is ai overviews
fan_out_dropped:
  - "ai overviews seo: commercial intent, belongs on a product page"
experience_mode: research-only
created_at: 2026-05-06T11:14:00Z
author: "Your Name"
---
```

If `experience_mode` is `research-only`, the writer found no story in `experience-notes.md` matching the topic and avoided all first-person experiential phrasing. To fix: add a relevant story to `experience-notes.md` and re-run.

If `fan_out_dropped` has entries, the writer made a deliberate call to skip those variations. Each comes with a reason. You can override by re-running the post manually with that variation included.

`sources_cited` is the audit trail. Every URL here should appear inline in the post as an `[anchor](url)` markdown link. No reference list at the bottom; that's enforced by the review checklist.

## How the dashboard updates

After every run, `scripts/render-html-report.py` regenerates `output/keywords/dashboard.html`. The queue card for the post you just shipped now shows:

- Green "WRITTEN" badge
- Checkmark on the title
- "Written: <timestamp>" in the meta column
- "View published post →" link to the local markdown file (or live URL if you wired Astro)

So System 1's dashboard is the single place you go to see: what's queued, what's in progress, what's shipped, with links to the drafts. No external project tracker needed.

## Hand-editing the queue

You can edit `state/content-queue.json` by hand at any time. Common edits:

- **Skip a post**: change its `status` to `"skipped"`. Greyed out in dashboard.
- **Reorder**: drag items in the `items` array. The next Mode B run picks `items[0]` where `status="queued"`.
- **Demote**: leave it at `queued` but move it to the bottom.

The writer never reorders the queue. Order is your call.

## Going hands-off (optional)

If you want a draft waiting for you Wednesday morning without invoking the skill yourself, schedule the same agent.

Trade-off: scheduled runs go through `coordinator.sh content-writer` which prepends a `MODE: AUTO` header so the agent commits at every decision point without asking. It uses `--dangerously-skip-permissions` because no human is there to click Allow. Drafts will still be quality-gated by the lint script (em-dashes, banned phrases, anchor lengths, Three Kings). Anything that fails lint gets `status: needs_review` instead of `written`, so the dashboard shows it red and you know to look.

**macOS, launchd:**

```bash
cp the-four-systems/system-2-content-writer/launchd/com.example.seo-content-writer.plist \
   ~/Library/LaunchAgents/

# Edit the path inside ProgramArguments to point at your project
nano ~/Library/LaunchAgents/com.example.seo-content-writer.plist

launchctl load ~/Library/LaunchAgents/com.example.seo-content-writer.plist
launchctl list | grep seo-content-writer
```

Now every Tuesday at 10:07 local, one queued post becomes a draft. If the queue is empty that week, the agent exits cleanly with a `NO_QUEUED_ITEMS` log entry, no error, no spurious dashboard update.

**Linux / WSL2, cron:**

```cron
7 10 * * 2 cd /path/to/seo-agents && ./coordinator.sh content-writer >> /tmp/seo-content-writer.log 2>&1
```

## Costs visibility for the user

After every Mode B run, `reports/<date>-content-writer.md` includes a Cost Summary block:

```
## Cost summary
- Claude tokens (in/out): 18,432 / 4,901
- Estimated Claude API cost: $0.31
- DataForSEO API spend: $0.06
- Run total: $0.37
```

Track these for budgeting. Tutorial viewers will appreciate this transparency.

## Troubleshooting

**"Missing context file"** — One of the 8 files in `context/` is missing. Run the `context-bootstrapper` skill (or create the file by hand) before re-running the writer.

**"No queued items"** — System 1's queue is empty. Run the `keyword-researcher` skill with a fresh seed. The writer cannot draft from nothing.

**Draft has em dashes / banned words** — Update `tone-of-voice.md` and `brand-guidelines.md` to be explicit. The writer reads these every run; if rules aren't there, they aren't enforced. Re-run the post (mark current item `skipped` first).

**Draft is too research-y, not enough personality** — Front-matter says `experience_mode: research-only`? That means `experience-notes.md` had no story matching the post topic. Add one and re-run.

**Auto-publish failed** — Check `context/publishing.json` paths and that the Astro repo's `content_dir` exists. The writer prints any git/push errors to the run report.

**Output reads like generic AI** — Almost always means `tone-of-voice.md` and `experience-notes.md` are too thin. The bootstrapper interview is the time to fill these in properly. You can always re-run the bootstrapper to regenerate one specific file.

## What's next

System 3 (Onsite Audit) runs Lighthouse and on-page health checks against the posts you ship and your money pages. System 4 (Refresh Recommender) reads GSC, scores content decay, and tells you which posts to rewrite. We build those next.
