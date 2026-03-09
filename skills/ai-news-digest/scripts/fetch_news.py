#!/usr/bin/env python3
"""
AI News Digest - Fetch and curate today's AI news from RSS feeds.

Usage:
    python fetch_news.py                    # Default: last 24h, markdown output
    python fetch_news.py --hours 48         # Last 48 hours
    python fetch_news.py --format json      # JSON output
    python fetch_news.py --category LLM     # Filter by category
    python fetch_news.py --limit 15         # Limit articles
    python fetch_news.py --lang zh          # Chinese output
    python fetch_news.py --output digest.md # Save to file
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path

try:
    import feedparser
except ImportError:
    print("Error: feedparser is required. Install with: pip install feedparser")
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install with: pip install pyyaml")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_DIR = SCRIPT_DIR.parent / "config"
FEEDS_CONFIG = CONFIG_DIR / "feeds.yaml"


def load_config() -> dict:
    """Load feed configuration from YAML file."""
    with open(FEEDS_CONFIG, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Feed Fetching
# ---------------------------------------------------------------------------


def fetch_feed(feed_info: dict, settings: dict) -> list[dict]:
    """Fetch and parse a single RSS feed, returning normalized articles."""
    url = feed_info["url"]
    feedparser.USER_AGENT = settings.get("user_agent", "AI-News-Digest/1.0")

    try:
        parsed = feedparser.parse(url)
    except Exception as e:
        print(f"  [WARN] Failed to fetch {feed_info['name']}: {e}", file=sys.stderr)
        return []

    if parsed.bozo and not parsed.entries:
        print(
            f"  [WARN] Feed error for {feed_info['name']}: {parsed.bozo_exception}",
            file=sys.stderr,
        )
        return []

    articles = []
    max_per_feed = settings.get("max_per_feed", 10)

    for entry in parsed.entries[:max_per_feed]:
        article = normalize_entry(entry, feed_info)
        if article:
            articles.append(article)

    return articles


def normalize_entry(entry: dict, feed_info: dict) -> dict | None:
    """Normalize a feedparser entry into a standard article dict."""
    title = entry.get("title", "").strip()
    if not title:
        return None

    link = entry.get("link", "")
    summary = entry.get("summary", entry.get("description", ""))
    # Strip HTML tags from summary
    summary = re.sub(r"<[^>]+>", "", summary).strip()
    # Truncate long summaries
    if len(summary) > 500:
        summary = summary[:497] + "..."

    # Parse published date
    published = None
    for date_field in ("published_parsed", "updated_parsed"):
        tp = entry.get(date_field)
        if tp:
            try:
                published = datetime(*tp[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                pass
            break

    if published is None:
        # Fallback: use current time (article will be included but marked)
        published = datetime.now(timezone.utc)

    return {
        "title": title,
        "link": link,
        "summary": summary,
        "published": published,
        "source": feed_info["name"],
        "category": feed_info.get("category", "Uncategorized"),
        "language": feed_info.get("language", "en"),
        "priority": feed_info.get("priority", 3),
    }


# ---------------------------------------------------------------------------
# Filtering & Deduplication
# ---------------------------------------------------------------------------


def filter_by_time(articles: list[dict], hours: int) -> list[dict]:
    """Keep only articles published within the last N hours."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    return [a for a in articles if a["published"] >= cutoff]


def filter_by_category(articles: list[dict], categories: list[str]) -> list[dict]:
    """Filter articles by category (case-insensitive partial match)."""
    cats_lower = [c.lower() for c in categories]
    return [
        a
        for a in articles
        if any(c in a["category"].lower() for c in cats_lower)
    ]


def deduplicate(articles: list[dict], threshold: float = 0.6) -> list[dict]:
    """Remove near-duplicate articles based on title similarity."""
    if not articles:
        return articles

    unique = [articles[0]]
    for article in articles[1:]:
        is_dup = False
        for existing in unique:
            similarity = SequenceMatcher(
                None, article["title"].lower(), existing["title"].lower()
            ).ratio()
            if similarity >= threshold:
                # Keep the one from higher-priority source
                if article["priority"] < existing["priority"]:
                    unique.remove(existing)
                    unique.append(article)
                is_dup = True
                break
        if not is_dup:
            unique.append(article)
    return unique


def auto_categorize(article: dict, categories_config: list[dict]) -> str:
    """Re-categorize article based on keyword matching if needed."""
    text = (article["title"] + " " + article["summary"]).lower()
    best_cat = article["category"]
    best_score = 0

    for cat_info in categories_config:
        score = sum(1 for kw in cat_info["keywords"] if kw in text)
        if score > best_score:
            best_score = score
            best_cat = cat_info["name"]

    return best_cat


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

LABELS_ZH = {
    "AI News Digest": "AI 今日资讯",
    "Key Headlines": "今日要闻",
    "Quick Bits": "快讯速览",
    "Source": "来源",
    "Published": "发布时间",
    "No articles found": "未找到相关文章",
    "articles from": "篇文章，来自",
    "sources": "个来源",
    "LLM & Foundation Models": "大模型与基础模型",
    "Research & Papers": "研究与论文",
    "Industry & Business": "产业与商业",
    "Products & Tools": "产品与工具",
    "Policy & Regulation": "政策与监管",
    "Open Source": "开源动态",
    "Applications": "应用落地",
}


def translate_label(label: str, lang: str) -> str:
    if lang == "zh":
        return LABELS_ZH.get(label, label)
    return label


def format_time(dt: datetime) -> str:
    """Format datetime for display."""
    now = datetime.now(timezone.utc)
    diff = now - dt
    if diff.total_seconds() < 3600:
        mins = int(diff.total_seconds() / 60)
        return f"{mins}m ago"
    elif diff.total_seconds() < 86400:
        hours = int(diff.total_seconds() / 3600)
        return f"{hours}h ago"
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def format_markdown(articles: list[dict], lang: str = "en") -> str:
    """Format articles as a Markdown digest."""
    if not articles:
        return f"# {translate_label('AI News Digest', lang)} - {datetime.now().strftime('%Y-%m-%d')}\n\n_{translate_label('No articles found', lang)}_\n"

    lines = []
    date_str = datetime.now().strftime("%Y-%m-%d")
    lines.append(f"# {translate_label('AI News Digest', lang)} - {date_str}\n")

    # Count stats
    sources = set(a["source"] for a in articles)
    lines.append(
        f"> {len(articles)} {translate_label('articles from', lang)} {len(sources)} {translate_label('sources', lang)}\n"
    )

    # Key Headlines (top 5 by priority)
    top = sorted(articles, key=lambda a: (a["priority"], -a["published"].timestamp()))[:5]
    lines.append(f"## {translate_label('Key Headlines', lang)}\n")
    for a in top:
        lines.append(f"- **[{a['title']}]({a['link']})** — {a['source']}")
    lines.append("")

    # Group by category
    by_category = defaultdict(list)
    for a in articles:
        by_category[a["category"]].append(a)

    # Sort categories by total priority
    cat_order = sorted(
        by_category.keys(),
        key=lambda c: min(a["priority"] for a in by_category[c]),
    )

    for cat in cat_order:
        cat_articles = sorted(
            by_category[cat], key=lambda a: (a["priority"], -a["published"].timestamp())
        )
        cat_label = translate_label(cat, lang)
        lines.append(f"## {cat_label}\n")

        for a in cat_articles:
            lines.append(f"### [{a['title']}]({a['link']})\n")
            lines.append(
                f"**{translate_label('Source', lang)}**: {a['source']} | "
                f"**{translate_label('Published', lang)}**: {format_time(a['published'])}\n"
            )
            if a["summary"]:
                lines.append(f"{a['summary']}\n")
            lines.append("---\n")

    return "\n".join(lines)


def format_json(articles: list[dict]) -> str:
    """Format articles as JSON."""

    def serialize(a: dict) -> dict:
        return {
            "title": a["title"],
            "link": a["link"],
            "summary": a["summary"],
            "published": a["published"].isoformat(),
            "source": a["source"],
            "category": a["category"],
            "language": a["language"],
            "priority": a["priority"],
        }

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_articles": len(articles),
        "sources": list(set(a["source"] for a in articles)),
        "articles": [serialize(a) for a in articles],
    }
    return json.dumps(output, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="AI News Digest - Fetch today's AI news from curated RSS feeds"
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Fetch articles from the last N hours (default: 24)",
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)",
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="Filter by category (comma-separated, e.g. 'LLM,Research')",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit total number of articles (0 = no limit)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Save output to file",
    )
    parser.add_argument(
        "--lang",
        choices=["en", "zh"],
        default="en",
        help="Output language (default: en)",
    )
    parser.add_argument(
        "--feeds-config",
        type=str,
        default=None,
        help="Path to custom feeds.yaml config",
    )
    args = parser.parse_args()

    # Load config
    global FEEDS_CONFIG
    if args.feeds_config:
        FEEDS_CONFIG = Path(args.feeds_config)
    config = load_config()
    settings = config.get("settings", {})
    feeds = config.get("feeds", [])
    categories_config = config.get("categories", [])

    if not feeds:
        print("Error: No feeds configured.", file=sys.stderr)
        sys.exit(1)

    # Fetch all feeds
    all_articles = []
    print(f"Fetching {len(feeds)} feeds...", file=sys.stderr)

    for i, feed in enumerate(feeds, 1):
        print(
            f"  [{i}/{len(feeds)}] {feed['name']}...",
            file=sys.stderr,
            end="",
            flush=True,
        )
        articles = fetch_feed(feed, settings)
        print(f" {len(articles)} articles", file=sys.stderr)
        all_articles.extend(articles)

    print(f"\nTotal raw articles: {len(all_articles)}", file=sys.stderr)

    # Filter by time
    all_articles = filter_by_time(all_articles, args.hours)
    print(f"After time filter ({args.hours}h): {len(all_articles)}", file=sys.stderr)

    # Auto-categorize
    if categories_config:
        for a in all_articles:
            a["category"] = auto_categorize(a, categories_config)

    # Filter by category
    if args.category:
        cats = [c.strip() for c in args.category.split(",")]
        all_articles = filter_by_category(all_articles, cats)
        print(f"After category filter: {len(all_articles)}", file=sys.stderr)

    # Deduplicate
    dedup_threshold = settings.get("dedup_threshold", 0.6)
    all_articles = deduplicate(all_articles, threshold=dedup_threshold)
    print(f"After deduplication: {len(all_articles)}", file=sys.stderr)

    # Sort by priority then recency
    all_articles.sort(key=lambda a: (a["priority"], -a["published"].timestamp()))

    # Limit
    if args.limit > 0:
        all_articles = all_articles[: args.limit]

    # Format output
    if args.format == "json":
        output = format_json(all_articles)
    else:
        output = format_markdown(all_articles, lang=args.lang)

    # Output
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"\nDigest saved to: {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
