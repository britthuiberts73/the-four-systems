# The Four Systems

Four SEO skills you trigger from Claude Code. Each one updates a shared dashboard. Optional bonus: schedule them with cron / launchd to run hands-off.

1. **Keyword research** with AI fan-out
2. **Content writer** (Three Kings, Content Capsules, inline citations, lint-gated)
3. **Onsite audit** (Lighthouse + on-page health on your homepage and money pages)
4. **Refresh recommender** (finds posts older than 12 months and URLs Google has not indexed, tells you what to do about each)

> **Use Claude Code, not Claude Desktop.** Desktop is a chat UI; it can't run skills against your project files or be invoked by cron. See `docs/00-prerequisites.md` for the full why.

## Quickstart (15 minutes, skill mode only)

1. Clone:

   ```bash
   git clone https://github.com/NicoSKOOL/the-four-systems
   cd the-four-systems
   ```

2. Read prerequisites: `docs/00-prerequisites.md` covers Claude Code, DataForSEO, GSC, Python.

3. Set up credentials and the optional tool allowlist:

   ```bash
   cp .mcp.json.example .mcp.json                                   # add your DataForSEO + GSC creds
   cp .claude/settings.local.json.example .claude/settings.local.json
   ```

4. The skills are already in `.claude/skills/`. They include:
   - `context-bootstrapper` — interviews you to generate the 8 business-context files
   - `keyword-researcher` — System 1
   - `content-writer` — System 2
   - `onsite-audit` — System 3
   - `refresh-recommender` — System 4

5. Bootstrap your business context. Open this folder in Claude Code and say:

   ```
   bootstrap my context folder
   ```

   Claude interviews you for 15-20 minutes, fetches your website, writes all 8 context files into `context/`.

6. Run System 1:

   ```
   research keywords for <your seed>
   ```

7. Open the dashboard:

   ```bash
   open output/keywords/dashboard.html
   ```

That's the whole flow. From here you trigger any of the four skills whenever you need them. The dashboard accumulates run after run.

A reference dashboard with placeholder data is at `dashboard-example.html` so you can see the layout before your first real run.

## Going hands-off (optional bonus)

If you'd rather have the systems run on their own (so you wake up to a full dashboard without invoking anything), each system has a `launchd/com.example.seo-*.plist` you can install. See the "Going hands-off (optional)" section at the bottom of each `docs/0X-*.md` for setup. The trade-off is documented there: scheduled runs use `--dangerously-skip-permissions` because no human is there to approve tool calls.

## Costs

About **$2 to $3 per month** total for all four systems combined, in DataForSEO + Anthropic API spend. See `docs/00-prerequisites.md` for the per-system breakdown.

## Companion video

[YouTube tutorial: The Four Systems](#) (link will be added when the video drops)

## License

MIT. Use this however you want.

## Credits

Built by [@NicoSKOOL](https://github.com/NicoSKOOL). Companion repo to the Your Community community: an AI-SEO operator community on Skool teaching how to build automations like these.
