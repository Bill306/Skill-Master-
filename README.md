# Skill-Master

A collection of Agent Skills for Claude Code and other AI assistants.

## Skills

### AI News Digest (`/ai-news-digest`)

Generate a curated daily digest of the most important AI news and developments.

**Features:**
- Aggregates 25+ curated RSS feeds from AI labs, tech media, research blogs, and communities
- Automatic categorization into 7 thematic sections
- Near-duplicate detection and removal
- Multi-language support (English & Chinese)
- LLM-powered intelligent summarization
- Multiple output formats (Markdown, JSON, HTML email)

**Quick Start:**

```bash
cd skills/ai-news-digest
pip install -r requirements.txt

# Fetch today's AI news
python scripts/fetch_news.py

# Fetch and summarize with AI
python scripts/fetch_news.py --format json | python scripts/summarize_news.py

# Chinese output
python scripts/fetch_news.py --lang zh
```

See [skills/ai-news-digest/SKILL.md](skills/ai-news-digest/SKILL.md) for full documentation.

## Project Structure

```
Skill-Master-/
├── README.md
└── skills/
    └── ai-news-digest/
        ├── SKILL.md              # Skill definition & instructions
        ├── requirements.txt      # Python dependencies
        ├── config/
        │   └── feeds.yaml        # RSS feed sources & settings
        ├── scripts/
        │   ├── fetch_news.py     # News fetcher & formatter
        │   └── summarize_news.py # LLM-powered summarizer
        └── templates/
            └── digest_email.html # HTML email template
```

## Adding New Skills

Create a new directory under `skills/` with a `SKILL.md` file:

```
skills/my-new-skill/
├── SKILL.md
└── ...
```

See [Anthropic Skills Documentation](https://github.com/anthropics/skills) for the skill format specification.
