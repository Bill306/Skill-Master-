---
name: ai-news-digest
description: |
  Generate a curated AI news digest with today's most noteworthy developments in artificial intelligence.
  TRIGGER when: user asks for AI news, today's AI updates, AI industry digest, what's new in AI,
  AI headlines, latest AI developments, AI briefing, AI news summary, or anything related to
  fetching and summarizing current AI/ML news and trends.
  DO NOT TRIGGER when: user asks about general tech news unrelated to AI, historical AI topics,
  or AI coding/implementation help.
---

# AI News Digest Skill

Generate a comprehensive, well-structured daily digest of the most important AI news and developments.

## How It Works

1. **Fetch** news from multiple curated RSS feeds covering the AI/ML ecosystem
2. **Filter** articles from the past 24 hours (configurable)
3. **Deduplicate** similar stories across sources
4. **Categorize** news into thematic sections
5. **Summarize** each article with key takeaways using AI
6. **Format** into a clean, readable digest

## Usage

Run the news fetcher script to gather today's AI news:

```bash
python skills/ai-news-digest/scripts/fetch_news.py
```

### Options

```bash
# Fetch news from the last N hours (default: 24)
python skills/ai-news-digest/scripts/fetch_news.py --hours 48

# Output as JSON for further processing
python skills/ai-news-digest/scripts/fetch_news.py --format json

# Output as Markdown (default)
python skills/ai-news-digest/scripts/fetch_news.py --format markdown

# Filter by category
python skills/ai-news-digest/scripts/fetch_news.py --category "LLM,Research"

# Limit number of articles
python skills/ai-news-digest/scripts/fetch_news.py --limit 20

# Save to file
python skills/ai-news-digest/scripts/fetch_news.py --output digest.md

# Use Chinese language output
python skills/ai-news-digest/scripts/fetch_news.py --lang zh
```

## News Categories

Articles are automatically classified into these categories:

| Category | Description |
|----------|-------------|
| **LLM & Foundation Models** | New model releases, benchmarks, capabilities |
| **Research & Papers** | Notable papers, breakthroughs, academic work |
| **Industry & Business** | Funding, acquisitions, partnerships, strategy |
| **Products & Tools** | New AI products, developer tools, platforms |
| **Policy & Regulation** | AI governance, safety, ethics, legislation |
| **Open Source** | Open-source releases, community projects |
| **Applications** | Real-world AI use cases and deployments |

## Output Format

The digest is formatted as a structured Markdown document:

```markdown
# AI News Digest - [Date]

## Key Headlines
> Top 3-5 most impactful stories of the day

## LLM & Foundation Models
### [Article Title](url)
**Source**: source_name | **Published**: time
Summary of the article with key points...

## Research & Papers
...

## Quick Bits
- Brief mentions of smaller but noteworthy items
```

## Data Sources

The skill aggregates from 25+ curated sources. See `config/feeds.yaml` for the full list.

| Source Type | Examples |
|-------------|----------|
| **AI Labs** | OpenAI, Google AI, Anthropic, DeepMind, Meta AI |
| **News Aggregators** | Techmeme |
| **Tech Media** | TechCrunch, The Verge, MIT Tech Review, VentureBeat |
| **Social / X (Twitter)** | AI key voices (EN), AI中文圈 (ZH) — requires `X_BEARER_TOKEN` |
| **Community** | Hacker News, r/MachineLearning, r/LocalLLaMA, Hugging Face |
| **Research** | arXiv cs.AI, arXiv cs.CL, Papers With Code |
| **Newsletters** | Ben's Bites, The Batch (Andrew Ng) |
| **Chinese Sources** | 机器之心, 量子位, AI科技评论 |

### X (Twitter) Setup

**Option 1 — AttentionVC API (recommended):**

AttentionVC provides curated X/Twitter intelligence with momentum detection and trending analysis.

```bash
export ATTENTIONVC_API_KEY="avc_your_key"
```

Get an API key from [attentionvc.ai](https://www.attentionvc.ai/). Provides rising articles, trending topics, and outlier detection endpoints optimized for AI content discovery.

**Option 2 — X API v2 (fallback):**

```bash
export X_BEARER_TOKEN="your_twitter_api_v2_bearer_token"
```

Get a bearer token from the [X Developer Portal](https://developer.x.com/). Without either token, X feeds are silently skipped.

Feeds can be customized by editing the configuration file.

## Guidelines

- Always attribute sources with links to original articles
- Highlight genuinely significant developments over clickbait
- Provide context for why a story matters
- Note connections between related stories
- Flag unverified claims or rumors explicitly
- Prefer primary sources (company blogs, papers) over secondary reporting
- Include both English and Chinese language sources for comprehensive coverage
