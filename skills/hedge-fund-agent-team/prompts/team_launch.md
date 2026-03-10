# Hedge Fund Agent Team — Launch Prompts

> Copy-paste these prompts into Claude Code to launch the hedge fund agent team.
> Requires: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in settings.json

## Full Team Launch v2 (8 Agents — with Red Team & Historian)

```
Create a hedge fund agent team. Use delegation mode — you are the Portfolio Manager,
coordinate only and never write code yourself. Require plan approval from all agents.

Create output directory first: mkdir -p /tmp/hedge-fund

Spawn 8 teammates in this order:

--- PHASE 0: Context ---
1. **historian** — Historian. Run FIRST before anyone else.
   Review past performance and generate agent credibility context:
   python skills/hedge-fund-agent-team/scripts/historian.py review --days 30
   python skills/hedge-fund-agent-team/scripts/historian.py credibility
   python skills/hedge-fund-agent-team/scripts/historian.py context
   Share credibility scores with all other agents via message.
   Save to /tmp/hedge-fund/historian.json

--- PHASE 1: Independent Research (all parallel) ---
2. **macro** — Macro Analyst. Analyze macro conditions:
   python skills/hedge-fund-agent-team/scripts/fetch_market_data.py --watchlist macro --source yahoo --output /tmp/hedge-fund/macro_data.json
   Classify regime: RISK-ON / RISK-OFF / TRANSITION.
   Identify top 3 macro themes and upcoming catalysts.
   Save to /tmp/hedge-fund/macro.json

3. **quant** — Quant Researcher. Calculate factor scores:
   python skills/hedge-fund-agent-team/scripts/fetch_market_data.py --watchlist us_tech_ai,us_ai_infra,hk_china --source yahoo --period 6mo --output /tmp/hedge-fund/quant_data.json
   Momentum, vol regime, mean-reversion z-scores, correlation matrix.
   Save to /tmp/hedge-fund/quant.json

4. **fundamental** — Fundamental Analyst. Evaluate financials:
   python skills/hedge-fund-agent-team/scripts/fetch_market_data.py --watchlist us_tech_ai,us_ai_infra,hk_china --source yahoo --data-type fundamentals --output /tmp/hedge-fund/fundamental_data.json
   P/E, P/S, EV/EBITDA, revenue growth, FCF yield. Rate each stock.
   Save to /tmp/hedge-fund/fundamental.json

5. **sentiment** — Sentiment Analyst. Gauge market mood:
   python skills/ai-news-digest/scripts/fetch_news.py --hours 48 --format json --output /tmp/hedge-fund/news_raw.json
   Sentiment score per asset (-1.0 to +1.0). Check VIX, fund flows.
   Save to /tmp/hedge-fund/sentiment.json

6. **trader** — Trader & Technical Analyst. Entry/exit timing:
   python skills/hedge-fund-agent-team/scripts/technical_analysis.py --watchlist us_tech_ai,us_ai_infra --source both --output /tmp/hedge-fund/ta.json
   Entry, stop-loss (ATR-based), take-profit, position sizing.
   Challenge fundamental on timing if chart disagrees.
   Save to /tmp/hedge-fund/trader.json

--- PHASE 2: Cross-Challenge ---
7. **red_team** — Red Team Analyst. Wait for Phase 1 agents to finish.
   Read ALL outputs in /tmp/hedge-fund/. Also read historian credibility context.
   For EVERY buy recommendation, produce the strongest possible bear case.
   Find hidden risks, historical precedents of failure, contrarian signals.
   Score each challenge: HIGH/MEDIUM/LOW conviction.
   You are NOT allowed to agree with the team. Find flaws in everything.
   Save to /tmp/hedge-fund/red_team.json

--- PHASE 3: Risk Review (after Red Team) ---
8. **risk** — Risk Manager. VETO POWER. Wait for all agents including Red Team.
   python skills/hedge-fund-agent-team/scripts/portfolio_analytics.py --symbols NVDA,MSFT,GOOGL,META,TSM,AVGO --weights 0.2,0.15,0.15,0.15,0.2,0.15 --stress-test --output /tmp/hedge-fund/risk.json
   Read Red Team challenges — incorporate legitimate risks.
   Check compliance with risk_params. VETO breaching recommendations.
   Save to /tmp/hedge-fund/risk.json

Task dependencies:
- historian: runs FIRST (Phase 0), shares context with everyone
- macro, quant, fundamental, sentiment, trader: PARALLEL (Phase 1)
- red_team: waits for Phase 1 (Phase 2)
- risk: waits for all including red_team (Phase 3)
- PM synthesizes final memo after risk approval (Phase 4)
- historian records all recommendations at the end

After all agents complete:
1. Historian records: python skills/hedge-fund-agent-team/scripts/historian.py record --input /tmp/hedge-fund/
2. PM produces final Investment Memo at /tmp/hedge-fund/investment_memo.md
   Weight recommendations by historian credibility scores.
   Address all Red Team challenges — either refute or adjust.
   Include dissenting views section.
```

## Full Team v1 (6 Agents — Classic)

```
Create a hedge fund agent team. Use delegation mode. Require plan approval.

mkdir -p /tmp/hedge-fund

Spawn 6 teammates:

1. **macro** — Macro Analyst. Regime classification, yield curve, DXY, VIX.
   python skills/hedge-fund-agent-team/scripts/fetch_market_data.py --watchlist macro --source yahoo --output /tmp/hedge-fund/macro_data.json
   Save to /tmp/hedge-fund/macro.json

2. **quant** — Quant Researcher. Factor scores, momentum, correlation.
   python skills/hedge-fund-agent-team/scripts/fetch_market_data.py --watchlist us_tech_ai,us_ai_infra,hk_china --source yahoo --period 6mo --output /tmp/hedge-fund/quant_data.json
   Save to /tmp/hedge-fund/quant.json

3. **fundamental** — Fundamental Analyst. Valuations, ratings.
   python skills/hedge-fund-agent-team/scripts/fetch_market_data.py --watchlist us_tech_ai,us_ai_infra,hk_china --source yahoo --data-type fundamentals --output /tmp/hedge-fund/fundamental_data.json
   Save to /tmp/hedge-fund/fundamental.json

4. **sentiment** — Sentiment Analyst. News sentiment, market mood.
   python skills/ai-news-digest/scripts/fetch_news.py --hours 48 --format json --output /tmp/hedge-fund/news_raw.json
   Save to /tmp/hedge-fund/sentiment.json

5. **risk** — Risk Manager (VETO POWER). Wait for all others.
   python skills/hedge-fund-agent-team/scripts/portfolio_analytics.py --symbols NVDA,MSFT,GOOGL,META,TSM,AVGO --stress-test --output /tmp/hedge-fund/risk.json

6. **trader** — Trader & Technical Analyst.
   python skills/hedge-fund-agent-team/scripts/technical_analysis.py --watchlist us_tech_ai,us_ai_infra --source both --output /tmp/hedge-fund/ta.json
   Save to /tmp/hedge-fund/trader.json

macro, quant, fundamental, sentiment, trader: PARALLEL.
risk: waits for all. PM synthesizes final memo.
```

## Quick Analysis Mode (3 Agents)

Lower token cost. Good for quick daily check-in.

```
Create a hedge fund agent team, 3 teammates. Delegation mode.

mkdir -p /tmp/hedge-fund

1. **researcher** — Fetch data and run analysis:
   python skills/hedge-fund-agent-team/scripts/fetch_market_data.py --watchlist us_tech_ai,macro --source yahoo --data-type all --output /tmp/hedge-fund/data.json
   python skills/hedge-fund-agent-team/scripts/technical_analysis.py --watchlist us_tech_ai --source both --output /tmp/hedge-fund/ta.json
   Summarize key findings.

2. **risk** — Risk check:
   python skills/hedge-fund-agent-team/scripts/portfolio_analytics.py --symbols NVDA,MSFT,GOOGL --stress-test --output /tmp/hedge-fund/risk.json

3. **trader** — 3 actionable trade ideas with entry/stop/target.
   Cross-reference researcher findings with TA data.

Researcher first, then risk and trader in parallel.
```

## Event-Driven: Emergency Risk Review

Use when event_monitor detects a CRITICAL alert (VIX spike, stop-loss breach):

```
Create an emergency hedge fund team. Delegation mode, 3 teammates.

mkdir -p /tmp/hedge-fund

CONTEXT: [paste alert from event_monitor.py here]

1. **macro** — Immediate macro assessment:
   What just happened? How does this change the regime?
   python skills/hedge-fund-agent-team/scripts/fetch_market_data.py --watchlist macro --source yahoo --output /tmp/hedge-fund/macro_data.json

2. **risk** — Emergency portfolio check:
   python skills/hedge-fund-agent-team/scripts/event_monitor.py monitor --symbols NVDA,MSFT,GOOGL,META,TSM --check-stops
   python skills/hedge-fund-agent-team/scripts/portfolio_analytics.py --symbols NVDA,MSFT,GOOGL,META,TSM --stress-test --output /tmp/hedge-fund/risk.json
   Which positions need immediate action?

3. **trader** — Execute defensive measures:
   Tighten all stop-losses. Identify hedging opportunities.
   Produce emergency trade plan.

ALL THREE run in parallel. PM synthesizes within 10 minutes.
```

## Event-Driven: Earnings Response

Use when a portfolio stock reports earnings:

```
Create a hedge fund team for [STOCK] earnings analysis. Delegation mode, 4 teammates.

mkdir -p /tmp/hedge-fund

CONTEXT: [STOCK] just reported Q[X] earnings.

1. **fundamental** — Analyze the earnings:
   Revenue vs estimates, EPS vs estimates, guidance, margins.
   How does this change the investment thesis?

2. **sentiment** — Market reaction analysis:
   After-hours price move, analyst reactions, social media sentiment.
   python skills/ai-news-digest/scripts/fetch_news.py --hours 4 --format json --output /tmp/hedge-fund/earnings_news.json

3. **trader** — Technical levels post-earnings:
   New support/resistance from the gap. Adjust stop-loss and targets.
   Should we add, hold, or trim the position?

4. **red_team** — Challenge the knee-jerk reaction:
   Is the market overreacting or underreacting?
   Historical earnings reaction patterns for this stock.

All four parallel. PM decides action within 2 hours.
```

## Event-Driven: FOMC/CPI Response

```
Create a hedge fund team for FOMC decision analysis. Delegation mode, 4 teammates.

mkdir -p /tmp/hedge-fund

CONTEXT: Fed just announced [DECISION].

1. **macro** — Full macro implications:
   Rate path expectations, dot plot changes, forward guidance tone.
   How does this change the regime?

2. **quant** — Historical pattern matching:
   How did markets react to similar decisions in the past?
   Which sectors/assets benefit or suffer?

3. **risk** — Portfolio stress test under new rate assumptions:
   python skills/hedge-fund-agent-team/scripts/portfolio_analytics.py --symbols NVDA,MSFT,GOOGL,META,TSM --stress-test
   Does our portfolio need rebalancing?

4. **trader** — Execution plan:
   Which positions to adjust? New entries from the reaction?
   Watch for post-FOMC reversal pattern (common).

macro first (5 min), then quant+risk+trader parallel.
```

## Sector Deep Dive

```
Create a hedge fund team for AI semiconductor deep dive. Delegation mode, 4 teammates.

mkdir -p /tmp/hedge-fund

1. **fundamental** — NVDA, AMD, AVGO, MRVL, ARM, TSM valuations.
2. **quant** — 6-month momentum, vol regime, inter-stock correlation.
3. **trader** — Technical analysis + TradingView ratings:
   python skills/hedge-fund-agent-team/scripts/technical_analysis.py --symbols NVDA,AMD,AVGO,MRVL,ARM,TSM --source both
4. **risk** — Concentration risk. "AI bubble burst" stress test.

Debate before producing final recommendations.
```

## Crypto Focus

```
Create a hedge fund team for crypto. Delegation mode, 4 teammates.

mkdir -p /tmp/hedge-fund

1. **macro** — DXY, real rates, liquidity conditions, regulatory news
2. **quant** — BTC-USD, ETH-USD, SOL-USD momentum, vol, correlations
3. **trader** — Technical analysis, key levels, entry/exit
4. **risk** — Extreme drawdown scenarios, correlation to equities
```

## China / HK Focus

```
Create a hedge fund team for China/HK tech. Delegation mode, 4 teammates.

mkdir -p /tmp/hedge-fund

1. **macro** — PBoC policy, PMI, property sector, USD/CNY, northbound flows
2. **fundamental** — Alibaba, Tencent, Baidu, Meituan, Xiaomi valuations
3. **trader** — HK stock technicals + HSI trend
4. **sentiment** — Chinese news sentiment:
   python skills/ai-news-digest/scripts/fetch_news.py --hours 48 --lang zh --format json --output /tmp/hedge-fund/cn_news.json
```

## Weekly Review (Historian-Led)

Run every Friday to track performance:

```
Create a hedge fund team for weekly review. Delegation mode, 3 teammates.

mkdir -p /tmp/hedge-fund

1. **historian** — Review all trades from the past week:
   python skills/hedge-fund-agent-team/scripts/historian.py review --days 7
   python skills/hedge-fund-agent-team/scripts/historian.py credibility
   python skills/hedge-fund-agent-team/scripts/historian.py report --days 7
   Which calls were right? Which were wrong? Why?

2. **red_team** — Post-mortem on losing trades:
   What signals did the team miss? Were Red Team challenges ignored that should
   have been heeded? Identify systematic biases.

3. **risk** — Portfolio health check:
   python skills/hedge-fund-agent-team/scripts/portfolio_analytics.py --symbols NVDA,MSFT,GOOGL,META,TSM --stress-test
   Current risk exposure, any drift from target allocation.

historian first, then red_team and risk parallel.
PM produces weekly performance memo.
```

## Communication Protocol

### Phase 0 (Context)
- **Historian → All**: "Here are credibility scores. Trader has 72% win rate on HIGH confidence calls. Macro has been too bearish — discount regime calls by 20%."

### Phase 2 (Cross-Challenge)
- **Risk Manager → Everyone**: "Position [X] breaches 10% limit. Reduce to 8% or justify."
- **Trader → Fundamental**: "Valuation supports [stock] but chart says wait for pullback to $X."
- **Quant → Sentiment**: "Sentiment bullish but momentum diverging. Which signal to trust?"
- **Macro → All**: "Regime shifting to RISK-OFF. Widen all stops."
- **Red Team → Fundamental**: "Your NVDA bull case assumes 40% datacenter growth but here's why that's already priced in..."
- **Red Team → Trader**: "You're buying at resistance. 3 of last 5 similar setups failed."
- **Historian → PM**: "Red Team was right on 5 of 8 challenges last month. Take their high-conviction challenges seriously."

### Phase 3 (Resolution)
- **PM → Red Team**: "Your challenge on NVDA is noted but team consensus overrides. Reducing size from 8% to 5% as compromise."
- **PM → Trader**: "Risk vetoed the SMCI position. Remove from trade plan."

## Settings

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  },
  "teammateMode": "in-process"
}
```
