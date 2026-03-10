---
name: hedge-fund-agent-team
description: |
  Simulated hedge fund powered by up to 8 agents: Macro Analyst, Quant Researcher,
  Fundamental Analyst, Sentiment Analyst, Risk Manager, Trader (with TA),
  Red Team (adversarial), and Historian (performance tracking).
  TRIGGER when: user asks about hedge fund simulation, multi-asset portfolio analysis,
  investment research team, trading strategy analysis, or coordinated market research.
  DO NOT TRIGGER when: user asks for simple stock price lookups, basic charting,
  or single-asset analysis that doesn't need a team.
---

# Hedge Fund Agent Team

A simulated hedge fund research & trading operation using Claude Code Agent Teams.
Up to 8 specialized agents collaborate to analyze markets, generate signals, manage risk,
challenge assumptions, and produce actionable trade recommendations across multiple asset classes.

## Architecture

```
Portfolio Manager (Lead — Delegation Mode)
  ├── Macro Analyst        — 宏观经济、利率、央行、地缘政治
  ├── Quant Researcher     — 因子模型、统计套利、量化信号
  ├── Fundamental Analyst  — 财报分析、估值建模、行业研究
  ├── Sentiment Analyst    — 新闻情绪、社交舆情、资金流向
  ├── Risk Manager         — VaR、压力测试、相关性、仓位限制（否决权）
  ├── Trader               — 技术分析、入场/出场时机、执行建议
  ├── Red Team             — 对抗分析、摧毁牛市论点、发现隐藏风险
  └── Historian            — 历史追踪、绩效归因、Agent 可信度评分
```

## Key Features

### Red Team (Adversarial Analysis)
- Systematically attacks every bull thesis from other agents
- Finds historical precedents of similar setups that failed
- Identifies hidden risks: concentration, correlation, liquidity, regulatory
- Scores each challenge by conviction (HIGH/MEDIUM/LOW)
- **Cannot agree with the team** — forced devil's advocate

### Historian (Feedback Loop)
- Records all trade recommendations to `data/trade_history.jsonl`
- Reviews past recommendations, calculates actual P&L
- Produces **agent credibility scores** (Bayesian-adjusted win rate)
- Provides trust-weighting context: "Trader's HIGH confidence calls hit 72%"
- Enables self-calibration over time

### Event-Driven Triggers
- **Price alerts**: Stop-loss breach, 5%+ daily move, gap, unusual volume
- **Volatility**: VIX spike (>20% daily), extreme levels (>30)
- **Calendar**: FOMC, CPI, NFP, earnings dates auto-trigger analysis
- **News**: Sentiment shift detection via AI News Digest integration
- Auto-recommends which team configuration to launch per event

### MCP Integration (Optional)
- **Notion**: Investment journal, trade records, performance reviews
- **Slack**: Real-time alert notifications for CRITICAL/HIGH events

## Data Sources

| Source | Coverage | Setup |
|--------|----------|-------|
| **Yahoo Finance** | US/HK/Global equities, ETFs, crypto, FX, futures | `pip install yfinance` (free) |
| **Longbridge (长桥)** | US/HK/A-share real-time quotes, fundamentals | `pip install longport` + API key |
| **TradingView TA** | Technical indicators for any symbol | `pip install tradingview-ta` (free) |

### API Keys

```bash
# Longbridge (required for real-time HK/A-share data)
export LONGPORT_APP_KEY="your_app_key"
export LONGPORT_APP_SECRET="your_app_secret"
export LONGPORT_ACCESS_TOKEN="your_access_token"
# Get from: https://open.longportapp.com/
```

Yahoo Finance and TradingView TA work without API keys.

## Quick Start

### 1. Install dependencies

```bash
pip install yfinance longport tradingview-ta pyyaml pandas numpy
```

### 2. Launch the agent team

```
# Enable Agent Teams first:
# ~/.claude/settings.json → "env": {"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"}

# Full 8-agent team (with Red Team & Historian):
Create a hedge fund agent team to analyze the current market.
Use delegation mode. Spawn 8 teammates: historian, macro, quant, fundamental,
sentiment, trader, red_team, risk.

# Classic 6-agent team:
Create a hedge fund agent team. Spawn 6 teammates: macro, quant, fundamental,
sentiment, risk, trader.

# Quick 3-agent scan:
Create a hedge fund team, 3 teammates: researcher, risk, trader.
```

See `prompts/team_launch.md` for detailed prompt templates including event-driven scenarios.

## Agent Roles

### Portfolio Manager (Lead)
- Runs in **delegation mode** — coordinates only, never touches code
- Defines investment thesis and asset universe
- Assigns research tasks, reviews agent outputs
- Makes final allocation decisions weighted by historian credibility scores
- Resolves disagreements between agents, addresses Red Team challenges

### Macro Analyst
- Monitors central bank decisions (Fed, ECB, PBoC, BoJ)
- Tracks yield curves, inflation data, PMI, employment
- Assesses geopolitical risks and their market impact
- Produces macro regime classification: Risk-On / Risk-Off / Transition

### Quant Researcher
- Runs factor analysis (momentum, value, quality, volatility)
- Backtests strategies using historical data
- Calculates statistical signals (z-scores, mean reversion, breakout)
- Outputs ranked signal scores per asset

### Fundamental Analyst
- Analyzes earnings reports, revenue growth, margins
- Builds DCF / comparable valuations
- Tracks insider activity, analyst revisions
- Rates: Strong Buy / Buy / Hold / Sell / Strong Sell

### Sentiment Analyst
- Analyzes news sentiment across financial media
- Tracks social media buzz (Reddit, X/Twitter)
- Monitors fund flows (ETF flows, 13F filings, 北向资金)
- Produces sentiment score: -1.0 (extreme fear) to +1.0 (extreme greed)

### Risk Manager
- Calculates portfolio VaR (Value at Risk) at 95%/99% confidence
- Runs stress tests (2008 crisis, COVID crash, rate shock, AI bubble burst)
- Monitors correlation matrix for concentration risk
- Enforces position limits and drawdown thresholds
- Has **veto power** on trades exceeding risk parameters
- Incorporates Red Team challenges into risk assessment

### Trader (with Technical Analysis)
- Runs technical indicators: RSI, MACD, Bollinger Bands, moving averages
- Identifies support/resistance levels, chart patterns
- Determines entry/exit timing and position sizing
- Challenges Fundamental Analyst on timing
- Produces executable trade recommendations with entry/stop/target

### Red Team (Adversarial Analyst)
- **Cannot agree** — forced to find flaws in every recommendation
- Produces bear case for every long, bull case for every short
- Finds historical precedents of failure
- Identifies portfolio-level systemic risks
- Scores challenges: HIGH (real risk) / MEDIUM (possible) / LOW (stretch)

### Historian (Performance Tracker)
- Runs first (Phase 0) to provide credibility context
- Records all recommendations after team completes
- Reviews past P&L: win/loss/scratch per agent
- Calculates Bayesian-adjusted credibility scores
- Advises PM on trust-weighting: which agents to trust more

## Workflow

```
Phase 0: Context (Historian)
  historian reviews past performance → shares credibility scores with all agents

Phase 1: Independent Research (parallel)
  macro, quant, fundamental, sentiment, trader fetch data and analyze

Phase 2: Cross-Challenge (inter-agent messaging)
  - Red Team attacks every bull thesis
  - Trader challenges Fundamental on timing
  - Quant validates/contradicts Sentiment signals
  - Macro context constrains all recommendations
  - Historian shares trust weights

Phase 3: Risk Review
  - Risk Manager incorporates Red Team challenges
  - Compliance check, stress tests
  - VETO non-compliant recommendations

Phase 4: Consensus & Decision (PM synthesizes)
  - Weight recommendations by credibility scores
  - Address all Red Team challenges (refute or adjust)
  - Produce final investment memo with dissenting views
  - Historian records all recommendations for future review
```

## Event-Driven Responses

The event monitor detects conditions and recommends team configurations:

| Event | Severity | Auto-Launch | Team Config |
|-------|----------|-------------|-------------|
| Stop-loss breach | CRITICAL | Yes | trader + risk |
| VIX spike (>20%) | CRITICAL | Yes | macro + risk + trader |
| Large move (>5%) | HIGH | No (PM confirms) | fundamental + sentiment + trader |
| Earnings report | HIGH | No | fundamental + trader + sentiment + red_team |
| FOMC/CPI release | HIGH | No | macro + quant + risk + trader |
| Unusual volume | MEDIUM | No | quant + sentiment |

```bash
# Check all events
python scripts/event_monitor.py check --config config/assets.yaml

# Monitor specific positions
python scripts/event_monitor.py monitor --symbols NVDA,MSFT --check-stops

# Check economic calendar
python scripts/event_monitor.py calendar --days 7
```

## Output

The team produces a structured investment memo:

```markdown
# Investment Memo — [Date]

## Market Regime: [Risk-On / Risk-Off / Transition]
Macro summary...

## Agent Credibility (from Historian)
| Agent | Win Rate | Score | Trust Weight |
|-------|----------|-------|--------------|

## Trade Recommendations
| # | Asset | Direction | Entry | Stop | Target | Size | Confidence | Credibility-Adj |
|---|-------|-----------|-------|------|--------|------|------------|-----------------|

## Red Team Challenges
| # | Target | Challenge | Conviction | PM Response |
|---|--------|-----------|------------|-------------|

## Risk Report
VaR, stress tests, compliance, Red Team risks incorporated...

## Dissenting Views
Unresolved disagreements, minority opinions...
```

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/fetch_market_data.py` | Fetch prices, fundamentals from Yahoo/Longbridge/TradingView |
| `scripts/technical_analysis.py` | Calculate TA indicators (RSI, MACD, BB, MA, support/resistance) |
| `scripts/portfolio_analytics.py` | Portfolio risk metrics (VaR, Sharpe, drawdown, stress tests) |
| `scripts/historian.py` | Trade history tracking, P&L review, agent credibility scores |
| `scripts/event_monitor.py` | Event detection, price alerts, auto-trigger recommendations |

## Configuration

| File | Purpose |
|------|---------|
| `config/assets.yaml` | Asset universe (30+ assets), watchlists, risk parameters |
| `config/agents.yaml` | 8 agent role definitions, spawn prompts, communication protocol |
| `config/events.yaml` | Event trigger definitions, MCP integration, monitoring schedule |
| `data/trade_history.jsonl` | Persistent trade recommendation log (auto-created) |
| `data/agent_credibility.json` | Agent credibility scores (auto-created) |

## Team Configurations

| Config | Agents | Tokens | Best For |
|--------|--------|--------|----------|
| **Full v2** | 8 (all) | ~150-200K | Comprehensive weekly analysis |
| **Full v1** | 6 (no red team/historian) | ~80-120K | Standard analysis |
| **Quick** | 3 (researcher/risk/trader) | ~40-60K | Daily check-in |
| **Emergency** | 3 (macro/risk/trader) | ~30-50K | VIX spike, stop breach |
| **Earnings** | 4 (fundamental/sentiment/trader/red_team) | ~60-80K | Post-earnings reaction |
| **Sector** | 4 (fundamental/quant/trader/risk) | ~60-80K | Deep dive |
| **Weekly Review** | 3 (historian/red_team/risk) | ~40-60K | Friday performance review |
