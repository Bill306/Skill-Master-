# Hedge Fund Agent Team — Launch Prompts

> Copy-paste these prompts into Claude Code to launch the hedge fund agent team.
> Requires: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in settings.json

## Full Team Launch (6 Agents)

```
Create a hedge fund agent team. Use delegation mode — you are the Portfolio Manager,
coordinate only and never write code yourself. Require plan approval from all agents.

Create output directory first: mkdir -p /tmp/hedge-fund

Spawn 6 teammates:

1. **macro** — Macro Analyst. Analyze current macro conditions:
   Run: python skills/hedge-fund-agent-team/scripts/fetch_market_data.py --watchlist macro --source yahoo --output /tmp/hedge-fund/macro_data.json
   Then assess: yield curve, DXY, VIX, gold, oil, USD/CNY.
   Classify regime: RISK-ON / RISK-OFF / TRANSITION.
   Identify top 3 macro themes and upcoming catalysts (FOMC, CPI, etc).
   Save analysis to /tmp/hedge-fund/macro.json

2. **quant** — Quant Researcher. Calculate factor scores and signals:
   Run: python skills/hedge-fund-agent-team/scripts/fetch_market_data.py --watchlist us_tech_ai,us_ai_infra,hk_china --source yahoo --period 6mo --output /tmp/hedge-fund/quant_data.json
   Then calculate: momentum (1M/3M/6M), volatility regime, mean-reversion z-scores,
   relative strength vs sector. Run correlation analysis across all positions.
   Save results to /tmp/hedge-fund/quant.json

3. **fundamental** — Fundamental Analyst. Evaluate company financials:
   Run: python skills/hedge-fund-agent-team/scripts/fetch_market_data.py --watchlist us_tech_ai,us_ai_infra,hk_china --source yahoo --data-type fundamentals --output /tmp/hedge-fund/fundamental_data.json
   Then analyze: P/E, P/S, EV/EBITDA, revenue growth, margins, FCF yield.
   Rate each stock: STRONG BUY / BUY / HOLD / SELL / STRONG SELL.
   Save ratings to /tmp/hedge-fund/fundamental.json

4. **sentiment** — Sentiment Analyst. Gauge market mood:
   Run: python skills/ai-news-digest/scripts/fetch_news.py --hours 48 --format json --output /tmp/hedge-fund/news_raw.json
   Also check VIX level from macro data. Analyze news sentiment for each position.
   Produce sentiment scores (-1.0 fear to +1.0 greed) per asset.
   Save to /tmp/hedge-fund/sentiment.json

5. **risk** — Risk Manager. You have VETO POWER over any trade.
   Wait for all other agents to complete, then:
   Run: python skills/hedge-fund-agent-team/scripts/portfolio_analytics.py --symbols NVDA,MSFT,GOOGL,META,TSM,AVGO --weights 0.2,0.15,0.15,0.15,0.2,0.15 --stress-test --output /tmp/hedge-fund/risk.json
   Review all agent outputs in /tmp/hedge-fund/.
   Check compliance with risk_params in config/assets.yaml.
   VETO any recommendation that breaches limits. Explain what changes are needed.
   Save risk report to /tmp/hedge-fund/risk.json

6. **trader** — Trader & Technical Analyst. Determine entry/exit timing.
   Run: python skills/hedge-fund-agent-team/scripts/technical_analysis.py --watchlist us_tech_ai,us_ai_infra --source both --output /tmp/hedge-fund/ta.json
   Then for each recommended position determine:
   - Entry price, stop-loss (ATR-based), take-profit targets
   - Position size based on risk budget
   - Challenge fundamental analyst on timing if chart disagrees
   Save trade plan to /tmp/hedge-fund/trader.json

Task dependencies:
- macro, quant, fundamental, sentiment: run in PARALLEL (Phase 1)
- trader: can start during Phase 1 (TA is independent) but must check fundamental
  ratings before finalizing trade plan
- risk: must WAIT for all others to complete (Phase 2)
- After risk review: any vetoed trades go back to trader for adjustment (Phase 3)
- PM synthesizes final investment memo after all agents agree (Phase 4)

After all agents complete, produce the final Investment Memo at /tmp/hedge-fund/investment_memo.md
```

## Quick Analysis Mode (3 Agents)

Lower token cost. Good for quick daily check-in.

```
Create a hedge fund agent team, 3 teammates. Delegation mode.

mkdir -p /tmp/hedge-fund

1. **researcher** — Fetch data and run analysis:
   python skills/hedge-fund-agent-team/scripts/fetch_market_data.py --watchlist us_tech_ai,macro --source yahoo --data-type all --output /tmp/hedge-fund/data.json
   python skills/hedge-fund-agent-team/scripts/technical_analysis.py --watchlist us_tech_ai --source both --output /tmp/hedge-fund/ta.json
   Summarize key findings: which stocks look interesting and why.

2. **risk** — Risk check:
   python skills/hedge-fund-agent-team/scripts/portfolio_analytics.py --symbols NVDA,MSFT,GOOGL --stress-test --output /tmp/hedge-fund/risk.json
   Flag any concerns.

3. **trader** — Produce 3 actionable trade ideas with entry/stop/target.
   Cross-reference researcher findings with TA data.
   Save to /tmp/hedge-fund/trades.json

Researcher runs first, then risk and trader in parallel.
```

## Sector Deep Dive

Focus on a specific sector (e.g., AI semiconductors):

```
Create a hedge fund team to do a deep dive on AI semiconductors.
Delegation mode, 4 teammates.

mkdir -p /tmp/hedge-fund

1. **fundamental** — Deep fundamental analysis of NVDA, AMD, AVGO, MRVL, ARM, TSM:
   Fetch fundamentals, compare valuations, rank by quality.

2. **quant** — Factor analysis and relative performance:
   6-month momentum, vol regime, correlation between names.

3. **trader** — Full technical analysis with TradingView ratings:
   python skills/hedge-fund-agent-team/scripts/technical_analysis.py --symbols NVDA,AMD,AVGO,MRVL,ARM,TSM --source both
   Identify best entry points.

4. **risk** — Concentration risk analysis:
   All 6 stocks are semiconductors — what's the correlation risk?
   Run stress test for "AI bubble burst" scenario.
   Are we too concentrated?

Have them debate before producing final recommendations.
```

## Crypto Focus

```
Create a hedge fund team for crypto analysis. Delegation mode, 4 teammates.

mkdir -p /tmp/hedge-fund

1. **macro** — Macro context for crypto:
   DXY, real rates, liquidity conditions, regulatory news

2. **quant** — On-chain and momentum:
   python skills/hedge-fund-agent-team/scripts/fetch_market_data.py --symbols BTC-USD,ETH-USD,SOL-USD --source yahoo --period 1y
   Momentum, volatility regime, BTC dominance, ETH/BTC ratio

3. **trader** — Technical analysis:
   python skills/hedge-fund-agent-team/scripts/technical_analysis.py --symbols BTC-USD,ETH-USD,SOL-USD --source both
   Key levels, trend direction, entry/exit

4. **risk** — Crypto-specific risk:
   python skills/hedge-fund-agent-team/scripts/portfolio_analytics.py --symbols BTC-USD,ETH-USD,SOL-USD --stress-test
   Extreme drawdown scenarios, correlation to equities, position sizing
```

## China / HK Focus

```
Create a hedge fund team for China/HK tech analysis. Delegation mode, 4 teammates.

mkdir -p /tmp/hedge-fund

1. **macro** — China macro:
   PBoC policy, PMI, property sector, USD/CNY, northbound flows

2. **fundamental** — HK-listed tech fundamentals:
   python skills/hedge-fund-agent-team/scripts/fetch_market_data.py --watchlist hk_china --source yahoo --data-type fundamentals
   Alibaba, Tencent, Baidu, Meituan, Xiaomi — who's cheapest, who's growing fastest?

3. **trader** — Technical analysis on HK names:
   python skills/hedge-fund-agent-team/scripts/technical_analysis.py --watchlist hk_china --source both
   HSI trend, individual stock setups

4. **sentiment** — China-specific sentiment:
   python skills/ai-news-digest/scripts/fetch_news.py --hours 48 --lang zh --format json --output /tmp/hedge-fund/cn_news.json
   Policy signals, regulatory tone, retail sentiment
```

## Communication Protocol

During Phase 2 (Cross-Challenge), agents should:

1. **Risk Manager → Everyone**: "Your recommendation for [X] breaches [limit]. Reduce position to [Y]% or provide justification."
2. **Trader → Fundamental**: "Fundamentals support [stock] but chart shows [pattern]. I recommend waiting for pullback to $[X]."
3. **Quant → Sentiment**: "Sentiment is bullish on [stock] but momentum is diverging bearish. Which signal do you trust more?"
4. **Macro → All**: "Regime is shifting to RISK-OFF. All long positions need wider stops or reduced size."

## Settings

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  },
  "teammateMode": "in-process"
}
```
