#!/usr/bin/env python3
"""
AI News Digest - Summarize fetched news using an LLM.

This script takes the JSON output from fetch_news.py and generates
an AI-curated summary with insights and analysis.

Usage:
    python fetch_news.py --format json | python summarize_news.py
    python summarize_news.py --input news.json --output digest.md
    python summarize_news.py --input news.json --lang zh
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Support multiple LLM providers
PROVIDER_CONFIGS = {
    "anthropic": {
        "env_key": "ANTHROPIC_API_KEY",
        "default_model": "claude-sonnet-4-20250514",
    },
    "openai": {
        "env_key": "OPENAI_API_KEY",
        "default_model": "gpt-4o",
    },
}


def build_prompt(articles_json: dict, lang: str = "en") -> str:
    """Build the summarization prompt from articles data."""

    articles_text = json.dumps(articles_json["articles"], indent=2, ensure_ascii=False)

    if lang == "zh":
        return f"""你是一位资深AI行业分析师。请根据以下今日AI新闻数据，生成一份专业的「AI今日值得关注」资讯摘要。

要求：
1. **今日要闻**：挑选最重要的3-5条新闻，每条用2-3句话概述其重要性
2. **趋势洞察**：从今天的新闻中提炼1-2个值得关注的行业趋势
3. **分类速览**：按类别列出所有新闻的一句话摘要
4. **值得深读**：推荐2-3篇值得仔细阅读的文章，说明理由

格式要求：
- 使用Markdown格式
- 保留原文链接
- 语言简洁专业，避免废话
- 对重要数字和细节保持准确

今日新闻数据：
{articles_text}"""
    else:
        return f"""You are a senior AI industry analyst. Based on the following AI news data from today,
generate a professional "AI News Digest" summary.

Requirements:
1. **Key Headlines**: Select the 3-5 most important stories, summarize each in 2-3 sentences explaining their significance
2. **Trend Insights**: Extract 1-2 notable industry trends from today's news
3. **Category Overview**: List all news items with one-line summaries grouped by category
4. **Deep Reads**: Recommend 2-3 articles worth reading in detail, with reasons

Format:
- Use Markdown
- Preserve original article links
- Be concise and professional
- Maintain accuracy for numbers and key details

Today's news data:
{articles_text}"""


def summarize_with_anthropic(prompt: str, model: str) -> str:
    """Summarize using Anthropic's Claude API."""
    try:
        import anthropic
    except ImportError:
        print("Error: anthropic package required. Install with: pip install anthropic", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic()
    message = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def summarize_with_openai(prompt: str, model: str) -> str:
    """Summarize using OpenAI's API."""
    try:
        import openai
    except ImportError:
        print("Error: openai package required. Install with: pip install openai", file=sys.stderr)
        sys.exit(1)

    client = openai.OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4096,
    )
    return response.choices[0].message.content


def main():
    parser = argparse.ArgumentParser(
        description="Summarize AI news using an LLM"
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="Input JSON file (default: read from stdin)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file (default: stdout)",
    )
    parser.add_argument(
        "--provider",
        choices=["anthropic", "openai"],
        default="anthropic",
        help="LLM provider (default: anthropic)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model name (default: provider's default)",
    )
    parser.add_argument(
        "--lang",
        choices=["en", "zh"],
        default="en",
        help="Output language (default: en)",
    )
    args = parser.parse_args()

    # Read input
    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            news_data = json.load(f)
    else:
        news_data = json.load(sys.stdin)

    if not news_data.get("articles"):
        print("No articles to summarize.", file=sys.stderr)
        sys.exit(0)

    # Build prompt
    prompt = build_prompt(news_data, lang=args.lang)

    # Select model
    provider_config = PROVIDER_CONFIGS[args.provider]
    model = args.model or provider_config["default_model"]

    print(f"Summarizing {len(news_data['articles'])} articles with {args.provider}/{model}...", file=sys.stderr)

    # Generate summary
    if args.provider == "anthropic":
        summary = summarize_with_anthropic(prompt, model)
    elif args.provider == "openai":
        summary = summarize_with_openai(prompt, model)

    # Output
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(summary)
        print(f"Summary saved to: {args.output}", file=sys.stderr)
    else:
        print(summary)


if __name__ == "__main__":
    main()
