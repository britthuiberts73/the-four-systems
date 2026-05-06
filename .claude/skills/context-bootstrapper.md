---
name: context-bootstrapper
description: Interviews the user about their business and generates the 8 context files needed by Systems 1-4 (site-config, audience, tone-of-voice, experience-notes, services, brand-guidelines, competitors, author). Fetches the user's website first to pre-fill what it can see, then asks only what it cannot infer. Use this when a user is setting up the four systems for the first time, or when they say "set up the context folder", "bootstrap my business info", "create my context files", or "I have a new site, help me onboard".
allowed-tools: Read, Write, Edit, Bash, WebFetch
---

# Context Bootstrapper (System 0 setup helper)

Generate the 8 context files that Systems 1 through 4 read on every run. Instead of making the user write 8 files from scratch, conduct a 15 to 20 minute structured interview, fetch their website to pre-fill what you can see, and write each file to disk as you go.

## Files you will produce

Save all of these to `context/` at the project root. Create the directory if missing.

```
context/
├── site-config.md          ← identity, what the site is, in/out of scope topics
├── audience.md             ← who reads it, what they already know, what they hate
├── tone-of-voice.md        ← voice rules, formatting rules, sample phrases
├── experience-notes.md     ← real wins, stories, opinions, customer situations
├── services.md             ← what the business sells, pricing, what's included
├── brand-guidelines.md     ← banned words, regulated claims, competitor exclusions
├── competitors.md          ← who else ranks, gaps, moat
└── author.md               ← Person/Author schema fields, credentials, sameAs links
```

`publishing.json` is optional and only created if the user has an Astro+Cloudflare setup; ask at the end.

## Workflow

### Phase 1: orient (1 minute)

Greet the user. Tell them:

```
I'll set up your business context folder. The four SEO systems read these files
on every run, so the quality of your content depends entirely on what we put here.

Plan: I'll fetch your website first (homepage + 2-3 blog posts if any), then ask
you about 6 sections of questions. Total time: 15-20 minutes. You can stop and
resume anytime; everything is saved to disk as we go.

What's your website URL?
```

If the user has no website yet, skip Phase 2 and go straight to Phase 3, telling them you'll work from their answers alone.

### Phase 2: website analysis (3 minutes, automatic)

WebFetch the homepage. Then, if a sitemap or obvious blog index exists, WebFetch up to 3 blog posts. Look for:

- **What the business does** (1-line description, value prop)
- **Voice samples** (sentence patterns, formality level, pet phrases, sentence length)
- **Visible audience signals** (who the homepage speaks to)
- **Apparent competitors** (mentioned in copy or comparison pages)
- **Author bylines** (writer name, bio, social links)
- **Services and pricing pages** (URLs, headline products)
- **Existing wins/case studies** (numbers, testimonials, ranking screenshots)

Summarize what you found in 6 to 10 bullet points. End with:

```
This is what I picked up from your site. I'll use these as starting drafts and
ask you to confirm or correct each as we go. Sound good?
```

If the user has no website, skip this phase.

### Phase 3: structured interview (12 to 18 minutes)

Run these sections in order. After each section, write the corresponding file. Show the user the file path and a 5-line preview before moving on. Let them adjust.

**Hard rule for every file you generate: no em dashes anywhere. Use colons, commas, parentheses, or split sentences.**

#### Section A: site-config.md

Confirm or correct:
- One-paragraph description of what the business is, who it's for, what makes it different. Be specific. Push back if the user gives you "we help businesses with X". Ask for: dollars, percent, named tech, named customer types.
- 8-15 in-scope content topics
- 5-10 out-of-scope topics (what you do NOT want the writer to cover)

Write `context/site-config.md` with this skeleton:

```markdown
# Site: <domain>

## What it is
<one paragraph, specific>

## Topics in scope
- <topic 1>
- <topic 2>
...

## Topics out of scope
- <topic>
...
```

#### Section B: audience.md

Ask:
1. "Who is your primary reader? Job title, role, company size."
2. "What do they already know? What can the writer skip explaining?"
3. "What problem brings them to your site?"
4. "What have they tried that didn't work?"
5. "What do they HATE in content? (listicles, vague advice, affiliate spam, beginner explanations, etc.)"

Write `context/audience.md`:

```markdown
# Audience

## Primary persona
- Role: <...>
- Skill level: <assume they know X, do not over-explain Y>
- The problem: <...>
- Already tried: <...>

## What this audience hates
- <...>
```

#### Section C: tone-of-voice.md

Use the voice samples you pulled from the website if any. Confirm or correct:
1. "Should the voice be: direct/punchy, conversational, academic, irreverent, formal?"
2. "Sentence length: short and punchy, medium, long and detailed?"
3. "First person, second person, or impersonal?"
4. "Any phrases you use a lot that should appear in posts?"
5. "Any phrases or formatting habits you HATE? (e.g. emojis, exclamation marks, bolded sentences, listicles)"

Write `context/tone-of-voice.md`:

```markdown
# Tone of voice

## Voice rules
- <rule 1>
- <rule 2>

## Hard formatting rules
- Never use em dashes. Use colons, commas, parentheses, or separate sentences.
- <other formatting bans>

## Sample phrases this voice uses
- "<phrase>"

## Phrases this voice avoids
- "<phrase>"

## Sample paragraph (from existing post or written by user)
> <paste a real sample paragraph the writer should match>
```

The "Never use em dashes" line is included by default. Do not remove it.

#### Section D: experience-notes.md

This is the file that lifts posts out of generic AI content. Be patient and dig.

Ask:
1. "Tell me your top 3 customer wins. Real numbers, real outcomes."
2. "What's a story you tell new customers about why your product/service exists?"
3. "What's a strong opinion you hold about your industry that not everyone agrees with?"
4. "What's a recurring customer situation you've seen that the writer should know about?"
5. "Any rankings or content wins worth citing? (e.g. yoursite.com/blog/X ranks position 6 for 'query Y')"

Critical: do NOT fabricate. If the user has nothing for a section, write "None to date." The writer will engage research-only mode for posts where no relevant story exists.

Write `context/experience-notes.md`:

```markdown
# Experience notes

## Real wins (numbers only)
- <e.g. yoursite.com/blog/X ranks position 6 for "Y", 1,442 impressions in 3 months>

## Origin story
<the why-we-exist story the user tells>

## Strong opinions
- <opinion 1, with the reasoning>

## Recurring customer situations
- <situation>

## Stories the writer can pull from
### <Short title>
<the story, 100-200 words, written in first person>
```

#### Section E: services.md

Ask:
1. "What does the business sell? List products/services."
2. "Pricing? Tiers? What's in each?"
3. "Edge cases the writer should know? (e.g. 'we don't serve EU customers', 'free trial requires a credit card')"
4. "5 customer questions you answer all the time, with your standard answers."

Write `context/services.md`:

```markdown
# Services and offerings

## What we sell
- <product/service 1>: <one-line description>

## Pricing
| Tier | Price | What's included |
| --- | --- | --- |
| ... | ... | ... |

## Edge cases the writer should know
- <case>: <handling>

## Frequently answered questions
### <Question>
<the standard answer in 1-3 sentences>
```

#### Section F: brand-guidelines.md

Ask:
1. "Words or phrases the writer must NEVER use?"
2. "Competitor names that must NEVER appear in your content?"
3. "Brand spellings? (e.g. 'Your Product' not 'Datawise' or 'data wise')"
4. "Regulated claims you cannot make? (e.g. 'cures', 'guaranteed', 'best in the world')"
5. "Formatting rules? (e.g. no all-caps headings, always use British English, US dollars only)"

Write `context/brand-guidelines.md`:

```markdown
# Brand guidelines

## Banned words and phrases
- <word>
- <phrase>

## Competitor names that must not appear
- <competitor>

## Brand spelling and capitalization
- "Brand Name" (not "brand name" or "BrandName")

## Regulated claims to avoid
- <claim type>

## Formatting rules
- <rule>
```

#### Section G: competitors.md

Ask:
1. "Top 3 direct competitors? (same product space)"
2. "Top 3 indirect competitors? (different product, same audience reading their blog)"
3. "What topics have they covered well that you should not duplicate without a fresh angle?"
4. "What topics are NOT well covered by anyone in your space?"

Write `context/competitors.md` matching the structure already in `system-0-prerequisites.md`.

#### Section H: author.md

Ask:
1. "Who is the byline author for posts? Name, title."
2. "Email for the Person schema (can be a public one)."
3. "Avatar URL if you have one."
4. "List 3 to 5 verifiable credentials. (Years of experience, conferences spoken at, books, public companies you worked at, certifications.)"
5. "Public social profile URLs for sameAs schema: X, LinkedIn, GitHub, etc."
6. "Two to three sentence bio in third person."

Write `context/author.md`:

```markdown
# Author

## Identity
- Name: <...>
- Title: <...>
- Email: <...>
- Avatar URL: <...>

## Credentials
- <verifiable credential>

## Social profiles for sameAs schema
- <url>

## Public bio (used as Author schema "description")
<2-3 sentences in third person>
```

### Phase 4: optional publishing config (1 minute)

Ask:
```
Do you have an Astro website you want the Content Writer to auto-publish to?
(If you're on WordPress, Webflow, Notion, Ghost, or anywhere else, just say no.
We'll output markdown files you upload manually.)
```

If yes:
- Ask for the local path to the Astro repo
- Ask for the content collection directory (default: `src/content/blog/`)
- Ask for the front-matter schema (or read it from `src/content/config.ts` if accessible)
- Ask whether to push to main (live immediately) or to a draft branch (review first). Recommend draft branch.

Write `context/publishing.json`:

```json
{
  "mode": "astro",
  "repo_path": "/Users/.../my-astro-site",
  "content_dir": "src/content/blog",
  "branch_strategy": "draft",
  "draft_branch_prefix": "claude/post-"
}
```

If no: do not create the file. The Content Writer will default to markdown-only mode.

### Phase 5: summary (30 seconds)

Print a final summary:

```
Done. Your context folder:

✓ context/site-config.md (<N> lines)
✓ context/audience.md
✓ context/tone-of-voice.md
✓ context/experience-notes.md
✓ context/services.md
✓ context/brand-guidelines.md
✓ context/competitors.md
✓ context/author.md
✓ context/publishing.json (or skipped)

You can edit any of these by hand at any time. To regenerate one specific file,
run /context-bootstrapper and ask "regenerate <filename>".

Next step: System 1 setup. Open Content/youtube-tutorial-the-four-systems/system-1-setup.md.
```

## Re-run mode (regenerating one file)

If the user invokes the skill and says "regenerate experience-notes.md" or similar, skip phases 1, 2, 4, 5 and go directly to the relevant section in Phase 3. Read the existing file first so you can preserve content the user had right and only update what they want changed.

## Hard rules

- **No em dashes** in any generated file. Ever. Use colons, commas, parentheses, or split sentences.
- **No fabrication.** If the user has no answer for something, write "None to date" or "TK: <what they need to add>". Never invent stats, customer names, or credentials.
- **No emojis** in generated files unless the user's tone-of-voice explicitly says emojis are part of the brand voice.
- **Read before write.** If a context file already exists, read it first and merge intelligently rather than overwriting wholesale.
- **One file at a time.** Save after each section so a stopped session preserves progress.
- **Be specific.** Push back on vague answers. "We help businesses succeed" is not acceptable. "We sell a $19/month Cloudflare-Workers SEO dashboard to AI-SEO operators" is.
