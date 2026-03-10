---
name: hedge-fund-agent-team
description: |
  Simulated hedge fund powered by a 6-agent team: Macro Analyst, Quant Researcher,
  Fundamental Analyst, Sentiment Analyst, Risk Manager, and Trader (with Technical Analysis).
  TRIGGER when: user asks about hedge fund simulation, multi-asset portfolio analysis,
  investment research team, trading strategy analysis, or coordinated market research.
  DO NOT TRIGGER when: user asks for simple stock price lookups, basic charting,
  or single-asset analysis that doesn't need a team.
---

# Hedge Fund Agent Team

A simulated hedge fund research & trading operation using Claude Code Agent Teams.
6 specialized agents collaborate to analyze markets, generate signals, manage risk,
and produce actionable trade recommendations across multiple asset classes.

## Architecture

```
Portfolio Manager (Lead — Delegation Mode)
  ├── Macro Analyst        — 宏观经济、利率、央行、地缘政治
  ├── Quant Researcher     — 因子模型、统计套利、量化信号
  ├── Fundamental Analyst  — 财报分析、估值建模、行业研究
  ├── Sentiment Analyst    — 新闻情绪、社交舆情、资金流向
  ├── Risk Manager         — VaR、压力测试、相关性、仓位限制
  └── Trader               — 技术分析、入场/出场时机、执行建议
```

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

Create a hedge fund agent team to analyze the current market.
Use delegation mode. Spawn 6 teammates: macro, quant, fundamental, sentiment, risk, trader.
Load the configuration from skills/hedge-fund-agent-team/config/agents.yaml.
```

See `prompts/team_launch.md` for detailed prompt templates.

## Agent Roles

### Portfolio Manager (Lead)
- Runs in **delegation mode** — coordinates only, never touches code
- Defines investment thesis and asset universe
- Assigns research tasks, reviews agent outputs
- Makes final allocation decisions based on team consensus
- Resolves disagreements between agents

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
- Runs stress tests (2008 crisis, COVID crash, rate shock scenarios)
- Monitors correlation matrix for concentration risk
- Enforces position limits and drawdown thresholds
- Has **veto power** on trades exceeding risk parameters

### Trader (with Technical Analysis)
- Runs technical indicators: RSI, MACD, Bollinger Bands, moving averages
- Identifies support/resistance levels, chart patterns
- Determines entry/exit timing and position sizing
- Produces executable trade recommendations with:
  - Direction (Long/Short)
  - Entry price / Stop-loss / Take-profit
  - Position size (% of portfolio)
  - Confidence level

## Workflow

```
Phase 1: Data Collection (parallel)
  All agents fetch relevant data using scripts/fetch_market_data.py

Phase 2: Independent Analysis (parallel)
  Each agent produces their analysis in /tmp/hedge-fund/{agent-name}.json

Phase 3: Cross-Challenge (inter-agent messaging)
  - Risk Manager reviews all recommendations for risk violations
  - Trader challenges Fundamental Analyst on timing
  - Quant validates/contradicts Sentiment signals
  - Macro context filters all recommendations

Phase 4: Consensus & Decision (Lead synthesizes)
  PM collects all inputs, resolves conflicts, produces:
  - Final trade recommendations
  - Portfolio allocation update
  - Risk report
```

## Output

The team produces a structured investment memo:

```markdown
# Investment Memo — [Date]

## Market Regime: [Risk-On / Risk-Off / Transition]
Macro summary...

## Trade Recommendations
| # | Asset | Direction | Entry | Stop | Target | Size | Confidence |
|---|-------|-----------|-------|------|--------|------|------------|
| 1 | NVDA  | Long      | $142  | $135 | $160   | 5%   | High       |

## Portfolio Summary
Current allocation, sector exposure, risk metrics...

## Risk Report
VaR, stress tests, correlation warnings...

## Dissenting Views
Any unresolved disagreements between agents...
```

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/fetch_market_data.py` | Fetch prices, fundamentals from Yahoo/Longbridge/TradingView |
| `scripts/technical_analysis.py` | Calculate TA indicators (RSI, MACD, BB, MA, support/resistance) |
| `scripts/portfolio_analytics.py` | Portfolio risk metrics (VaR, Sharpe, drawdown, correlation) |

## Configuration

- `config/assets.yaml` — Asset universe, watchlists, sector mapping
- `config/agents.yaml` — Agent role definitions, prompts, tool permissions
