# Agent Team Prompt: AI News Digest

> Use this prompt to launch an Agent Team for generating a high-quality AI news digest.
> Requires: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in settings.json

## Quick Start

Copy-paste this into Claude Code to launch the team:

```
Create an agent team to generate today's AI news digest. Use delegation mode so you only coordinate.

Spawn 4 teammates:

1. **en-collector** — Fetch all English AI news sources.
   Run: `python skills/ai-news-digest/scripts/fetch_news.py --hours 24 --format json --output /tmp/ai-news-en.json --lang en`
   Then read /tmp/ai-news-en.json and report the article count and source list.

2. **zh-collector** — Fetch all Chinese AI news sources.
   Run: `python skills/ai-news-digest/scripts/fetch_news.py --hours 24 --format json --output /tmp/ai-news-zh.json --lang zh`
   Then read /tmp/ai-news-zh.json and report the article count and source list.

3. **analyst** — Wait for en-collector and zh-collector to finish. Then:
   - Read both /tmp/ai-news-en.json and /tmp/ai-news-zh.json
   - Cross-deduplicate stories that appear in both EN and ZH sources
   - Identify the top 5 most impactful stories (cross-source verification: stories covered by 3+ sources rank higher)
   - For each top story, write a 2-3 sentence analysis explaining WHY it matters
   - Identify connections between stories (e.g., "Story A and Story B are both about X trend")
   - Classify stories into: Breaking, Important, Noteworthy, Quick Bits
   - Save analysis to /tmp/ai-news-analysis.json
   Require plan approval before proceeding.

4. **reviewer** — Wait for analyst to finish. Then:
   - Read /tmp/ai-news-analysis.json
   - Challenge the analyst's top 5 picks: are they truly impactful or just clickbait?
   - Verify cross-language consistency (do EN and ZH sources agree on facts?)
   - Check for missing context or unverified claims
   - Send feedback to analyst if any issues found
   - Once satisfied, format the final digest as Markdown and save to digest-YYYY-MM-DD.md

Task dependencies:
- en-collector and zh-collector run in parallel (no dependencies)
- analyst depends on both collectors completing
- reviewer depends on analyst completing
```

## Customization

### Fewer tokens (3-teammate version)

Drop the reviewer for lower cost. The analyst handles formatting directly:

```
Create an agent team for today's AI digest. Delegation mode.

Spawn 3 teammates:
1. **en-collector** — Run fetch_news.py --format json --output /tmp/ai-news-en.json
2. **zh-collector** — Run fetch_news.py --format json --output /tmp/ai-news-zh.json --lang zh
3. **analyst** — Wait for collectors. Cross-deduplicate, rank top stories, write analysis with 2-sentence summaries, format final Markdown digest.

Collectors run in parallel. Analyst waits for both.
```

### Deep research mode (5-teammate version)

Add a researcher for arXiv paper analysis:

```
Create an agent team for today's AI digest with deep research. Delegation mode.

Spawn 5 teammates:
1. **en-collector** — Fetch English sources
2. **zh-collector** — Fetch Chinese sources
3. **paper-researcher** — Focus on arXiv papers from today. For each notable paper:
   read the abstract, explain the key contribution in plain language,
   and assess real-world impact (high/medium/low).
4. **analyst** — Wait for all 3 collectors. Cross-reference, rank, analyze.
   Require plan approval.
5. **reviewer** — Quality check and final formatting.
```

### Topic-focused mode

For tracking a specific topic (e.g., AI Agents):

```
Create an agent team to research "AI Agents" specifically.

Spawn 3 teammates:
1. **collector** — Run fetch_news.py --format json --output /tmp/ai-agents.json
   then filter articles mentioning "agent", "agentic", "MCP", "tool use"
2. **analyst** — Analyze the agent ecosystem: what's launching, what's trending,
   competitive dynamics between OpenAI/Anthropic/Google agent platforms
3. **critic** — Challenge the analyst's conclusions. Are these real trends
   or hype? What evidence supports each claim?

Have them debate before producing the final report.
```

## Architecture Notes

### Why Agent Teams (not Subagents)

| Phase | Subagent | Agent Team |
|-------|----------|------------|
| Parallel fetch | ✅ Works | ✅ Works |
| Cross-source analysis | ❌ No inter-agent discussion | ✅ Analyst reads all data |
| Quality debate | ❌ Can only report up | ✅ Reviewer challenges analyst |
| Human intervention | ❌ Must go through main agent | ✅ Direct teammate messaging |

The key value of Agent Teams here is the **analyst ↔ reviewer feedback loop**.
A subagent can only return results — it can't question another subagent's work
or be questioned back.

### Token Budget Estimates

| Configuration | Estimated Tokens | Best For |
|---------------|-----------------|----------|
| 3-teammate (no reviewer) | ~50K-80K | Daily quick digest |
| 4-teammate (with reviewer) | ~80K-120K | High-quality weekly digest |
| 5-teammate (with researcher) | ~120K-180K | Deep research report |

### File Flow

```
fetch_news.py → /tmp/ai-news-en.json  ─┐
fetch_news.py → /tmp/ai-news-zh.json  ─┤→ analyst → /tmp/ai-news-analysis.json
                                        │→ reviewer → digest-YYYY-MM-DD.md
```

## Settings Required

Add to your `~/.claude/settings.json`:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  },
  "teammateMode": "in-process"
}
```

For split-pane mode (requires tmux):
```json
{
  "teammateMode": "tmux"
}
```
