---
name: content-writer
description: Write a blog post for the user's site interactively, following the 5-step workflow (brief, research, outline, draft, review). Pulls the next item from the System 1 content queue, walks the user through each decision, drafts a Three Kings-compliant post with Content Capsule sections and inline citations, then ticks the queue item off. Use when the user says "write a post", "draft the next one", "let's write something", "content writer", or asks for a blog post on any topic.
allowed-tools: Read, Write, Edit, Bash, WebFetch, mcp__dfs-mcp__serp_organic_live_advanced, mcp__dfs-mcp__dataforseo_labs_google_keyword_overview, mcp__dfs-mcp__on_page_content_parsing
---

# Content Writer (System 2, interactive)

Write one blog post for the user's site, walking them through the 5-step workflow with approval checkpoints.

## When to invoke

The user says any of:
- "write a post" / "write the next one"
- "draft a blog post"
- "let's write something about X"
- "content writer" / "system 2"
- "pick a post from the queue and write it"

If the user says something like "write 3 posts" or "ship the whole queue", politely refuse and explain: this is one post per invocation by design, because every post needs human-in-the-loop on the brief, sources, and outline. Offer to run again after this one ships.

## What you do (high level)

You run the same 5-step workflow as the scheduled `content-writer` agent, in **interactive mode**: you ask the user to pick from the queue, ask about topic-specific experience, present sources for approval, present the outline for approval, draft, self-review, save, mark the queue, and trigger the dashboard re-render.

The full prompt with all rules (Content Capsule format, citation anchor rules, Three Kings, em-dash ban, fan-out coverage tracking, mode-aware behaviour) lives at:

```
ai-ranking-automations/seo-agents/prompts/content-writer.md
```

**Read that prompt first.** It is the source of truth. This skill is the on-demand entry point. Do not duplicate its rules here.

## Project root

All paths are relative to `/path/to/the-four-systems/ai-ranking-automations/seo-agents/`. Always cd there or use absolute paths.

## How interactive mode differs from auto-pilot

In this skill, you are interactive. Specifically:

- **Step 1 brief**: list the top 3 queued items from `state/content-queue.json` and ask the user to pick. Then ASK them about topic-specific experience. Wait for their answer before continuing.
- **Step 2 research**: present the 8-12 sources you found as a numbered list. Wait for the user to approve, reject, or swap before continuing.
- **Step 3 outline**: present the full outline (title, H2/H3, capsule marks, internal-link picks, experience callouts, business-fact callouts) and wait for approval.
- **Step 4 draft**: just write it. Don't ask for permission to draft.
- **Step 5 review**: run the self-checklist, fix any failures, then show the user the report.
- **Step 6 save and hand off**: write the markdown, update the queue, attempt publish, regenerate dashboard, print a summary with the file path.

Do not fall back to auto-pilot inside this skill. If the user is annoyed by the approval steps and tells you to "just write it", that's their call to skip approvals - but still walk through the steps in order, showing your work.

## Reading the 8 context files

Same rule as the prompt: read all 8 files in `context/` before doing anything else. If any are missing, stop and tell the user to run the `context-bootstrapper` skill first. Do not attempt to draft a post against an incomplete context folder.

## When the queue is empty

If `pick-next-queue-item.py` returns `NO_QUEUED_ITEMS` (exit 2) and the user did not name a different topic, tell them:

```
The content queue is empty. Run the keyword-researcher skill to find a fresh
seed and fan it out, then come back here.
```

Offer to invoke the `keyword-researcher` skill yourself if they want, but only if they confirm.

## Cost expectation

A typical run is 25 to 40 minutes wall-clock (most of that is you waiting for the user) and costs about $0.30 to $0.50 in DataForSEO + Claude API combined.

## Hard rules

- **Read the full prompt at `prompts/content-writer.md` before any action.** Do not skim. Re-read it on every invocation.
- One post per invocation.
- Never auto-publish before writing to `output/posts/`. The local markdown file is the canonical artifact.
- Never fabricate a citation, a customer story, a stat, or a business fact. If you cannot back it up, drop it or flag `[TK: confirm]`.
- Never edit `state/keyword-bank.json` (that's System 1's territory).
- Update `state/content-queue.json` only via `scripts/mark-queue-item.py`.
- Never use em dashes anywhere.
