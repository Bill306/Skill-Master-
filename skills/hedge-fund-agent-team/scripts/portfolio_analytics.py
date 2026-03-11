#!/usr/bin/env python3
"""
Hedge Fund Agent Team — Portfolio Analytics & Risk Module

Calculates portfolio-level risk metrics for the Risk Manager agent.
Includes VaR, stress tests, correlation analysis, and compliance checks.

Usage:
    python portfolio_analytics.py --portfolio /tmp/hedge-fund/
    python portfolio_analytics.py --symbols NVDA,MSFT,GOOGL --weights 0.3,0.3,0.4
    python portfolio_analytics.py --symbols BTC-USD,ETH-USD --stress-test
    python portfolio_analytics.py --portfolio /tmp/hedge-fund/ --config assets.yaml
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: PyYAML required. pip install pyyaml", file=sys.stderr)
    sys.exit(1)

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_DIR = SCRIPT_DIR.parent / "config"
ASSETS_CONFIG = CONFIG_DIR / "assets.yaml"


def load_config(path=None):
    config_path = Path(path) if path else ASSETS_CONFIG
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------


def load_returns(symbols, period="1y"):
    """Load daily returns for a list of symbols from Yahoo Finance."""
    try:
        import numpy as np
        import yfinance as yf
    except ImportError:
        print("Error: yfinance and numpy required", file=sys.stderr)
        sys.exit(1)

    print(f"Loading {period} daily returns for {len(symbols)} symbols...", file=sys.stderr)

    all_closes = {}
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period=period, interval="1d")
            if not hist.empty:
                all_closes[sym] = hist["Close"].values
                print(f"  {sym}: {len(hist)} days", file=sys.stderr)
            else:
                print(f"  [WARN] {sym}: no data", file=sys.stderr)
        except Exception as e:
            print(f"  [ERROR] {sym}: {e}", file=sys.stderr)

    # Align to same length (trim to shortest)
    if not all_closes:
        return {}, {}

    min_len = min(len(v) for v in all_closes.values())
    returns = {}
    for sym, closes in all_closes.items():
        trimmed = closes[-min_len:]
        daily_ret = []
        for i in range(1, len(trimmed)):
            if trimmed[i - 1] != 0:
                daily_ret.append((float(trimmed[i]) / float(trimmed[i - 1])) - 1)
            else:
                daily_ret.append(0.0)
        returns[sym] = daily_ret

    return returns, all_closes


# ---------------------------------------------------------------------------
# Risk Metrics
# ---------------------------------------------------------------------------


def calc_var(returns_list, confidence=0.95):
    """Calculate Historical Value at Risk."""
    if not returns_list:
        return None
    sorted_returns = sorted(returns_list)
    index = int((1 - confidence) * len(sorted_returns))
    return round(sorted_returns[max(index, 0)] * 100, 4)  # as percentage


def calc_cvar(returns_list, confidence=0.95):
    """Calculate Conditional VaR (Expected Shortfall)."""
    if not returns_list:
        return None
    sorted_returns = sorted(returns_list)
    index = int((1 - confidence) * len(sorted_returns))
    tail = sorted_returns[: max(index, 1)]
    return round(sum(tail) / len(tail) * 100, 4)


def calc_max_drawdown(returns_list):
    """Calculate maximum drawdown from returns series."""
    if not returns_list:
        return None
    cumulative = [1.0]
    for r in returns_list:
        cumulative.append(cumulative[-1] * (1 + r))

    peak = cumulative[0]
    max_dd = 0.0
    for val in cumulative:
        if val > peak:
            peak = val
        dd = (peak - val) / peak
        if dd > max_dd:
            max_dd = dd

    return round(max_dd * 100, 2)


def calc_sharpe(returns_list, risk_free_annual=0.05):
    """Calculate annualized Sharpe ratio."""
    if not returns_list or len(returns_list) < 2:
        return None
    import numpy as np
    arr = np.array(returns_list)
    daily_rf = risk_free_annual / 252
    excess = arr - daily_rf
    std = np.std(excess, ddof=1)
    if std == 0:
        return 0.0
    return round(float(np.mean(excess) / std * math.sqrt(252)), 4)


def calc_sortino(returns_list, risk_free_annual=0.05):
    """Calculate annualized Sortino ratio."""
    if not returns_list or len(returns_list) < 2:
        return None
    import numpy as np
    arr = np.array(returns_list)
    daily_rf = risk_free_annual / 252
    excess = arr - daily_rf
    downside = arr[arr < daily_rf] - daily_rf
    downside_std = np.std(downside, ddof=1) if len(downside) > 1 else 0.0
    if len(downside) == 0 or downside_std == 0:
        return None
    return round(float(np.mean(excess) / downside_std * math.sqrt(252)), 4)


def calc_beta(returns_list, benchmark_returns):
    """Calculate beta relative to benchmark."""
    if not returns_list or not benchmark_returns:
        return None
    import numpy as np
    min_len = min(len(returns_list), len(benchmark_returns))
    r = np.array(returns_list[-min_len:])
    b = np.array(benchmark_returns[-min_len:])
    cov = np.cov(r, b)
    if cov[1][1] == 0:
        return None
    return round(float(cov[0][1] / cov[1][1]), 4)


def calc_correlation_matrix(returns_dict):
    """Calculate pairwise correlation matrix."""
    import numpy as np
    symbols = list(returns_dict.keys())
    n = len(symbols)
    if n < 2:
        return {}

    min_len = min(len(v) for v in returns_dict.values())
    matrix = {}
    high_corr_pairs = []

    for i in range(n):
        matrix[symbols[i]] = {}
        for j in range(n):
            r1 = returns_dict[symbols[i]][-min_len:]
            r2 = returns_dict[symbols[j]][-min_len:]
            corr = float(np.corrcoef(r1, r2)[0][1])
            matrix[symbols[i]][symbols[j]] = round(corr, 4)
            if i < j and abs(corr) > 0.8:
                high_corr_pairs.append({
                    "pair": [symbols[i], symbols[j]],
                    "correlation": round(corr, 4),
                    "warning": "HIGH" if abs(corr) > 0.9 else "MODERATE",
                })

    return {"matrix": matrix, "high_correlation_pairs": high_corr_pairs}


# ---------------------------------------------------------------------------
# Stress Tests
# ---------------------------------------------------------------------------

STRESS_SCENARIOS = {
    "2008_financial_crisis": {
        "description": "Global financial crisis — equity drawdown",
        "shocks": {
            "equities": -0.50,
            "crypto": -0.70,
            "gold": 0.25,
            "oil": -0.55,
            "bonds": 0.10,
            "vix": 2.50,
        },
    },
    "2020_covid_crash": {
        "description": "COVID-19 market crash — rapid V-shape",
        "shocks": {
            "equities": -0.34,
            "crypto": -0.50,
            "gold": -0.05,
            "oil": -0.65,
            "bonds": 0.15,
            "vix": 3.00,
        },
    },
    "rate_shock_200bps": {
        "description": "Sudden +200bps rate hike — growth selloff",
        "shocks": {
            "equities": -0.20,
            "crypto": -0.30,
            "gold": -0.10,
            "oil": -0.15,
            "bonds": -0.10,
            "vix": 1.50,
        },
    },
    "china_hard_landing": {
        "description": "China economic hard landing — EM contagion",
        "shocks": {
            "equities": -0.15,
            "china_equities": -0.40,
            "crypto": -0.20,
            "gold": 0.10,
            "oil": -0.30,
            "bonds": 0.05,
            "vix": 1.80,
        },
    },
    "ai_bubble_burst": {
        "description": "AI sector correction — semiconductor/tech selloff",
        "shocks": {
            "equities": -0.10,
            "ai_semiconductors": -0.45,
            "ai_software": -0.35,
            "crypto": -0.15,
            "gold": 0.05,
            "bonds": 0.05,
            "vix": 1.60,
        },
    },
}


def classify_asset(symbol, tags=None):
    """Classify an asset for stress test purposes."""
    sym = symbol.upper()
    tags = tags or []

    if "BTC" in sym or "ETH" in sym or "SOL" in sym or "crypto" in tags:
        return "crypto"
    if ".HK" in sym or "china" in tags:
        return "china_equities"
    if any(t in tags for t in ["gpu", "chips", "foundry"]):
        return "ai_semiconductors"
    if any(t in tags for t in ["saas", "cloud", "ai"]):
        return "ai_software"
    if "GC=F" in sym or "gold" in tags:
        return "gold"
    if "CL=F" in sym or "oil" in tags:
        return "oil"
    # Bonds & treasuries: ^TNX (10Y yield), ^TYX (30Y), ^FVX (5Y), TLT, IEF, etc.
    if any(x in sym for x in ["^TNX", "^TYX", "^FVX", "^IRX"]) or "bond" in tags:
        return "bonds"
    if any(x in sym for x in ["TLT", "IEF", "SHY", "BND", "AGG", "GOVT"]) or "treasury" in tags:
        return "bonds"
    if "^VIX" in sym:
        return "vix"
    # Currency pairs
    if "=X" in sym or "DX-Y" in sym or "fx" in tags:
        return "equities"  # No dedicated fx shock, use equities as fallback
    return "equities"


def run_stress_tests(symbols, weights, asset_tags=None):
    """Run stress tests on portfolio."""
    asset_tags = asset_tags or {}
    results = {}

    for scenario_name, scenario in STRESS_SCENARIOS.items():
        portfolio_impact = 0.0
        position_impacts = []

        for i, sym in enumerate(symbols):
            weight = weights[i] if i < len(weights) else 1.0 / len(symbols)
            asset_class = classify_asset(sym, asset_tags.get(sym, []))
            shock = scenario["shocks"].get(asset_class, scenario["shocks"].get("equities", -0.20))
            impact = weight * shock
            portfolio_impact += impact
            position_impacts.append({
                "symbol": sym,
                "weight": round(weight, 4),
                "asset_class": asset_class,
                "shock": round(shock * 100, 1),
                "weighted_impact": round(impact * 100, 2),
            })

        position_impacts.sort(key=lambda x: x["weighted_impact"])
        results[scenario_name] = {
            "description": scenario["description"],
            "portfolio_impact_pct": round(portfolio_impact * 100, 2),
            "worst_positions": position_impacts[:3],
            "severity": "CRITICAL" if portfolio_impact < -0.30 else
                        "HIGH" if portfolio_impact < -0.20 else
                        "MODERATE" if portfolio_impact < -0.10 else "LOW",
        }

    return results


# ---------------------------------------------------------------------------
# Compliance Checks
# ---------------------------------------------------------------------------


def check_compliance(symbols, weights, config, asset_tags=None):
    """Check portfolio against risk parameters from config."""
    risk_params = config.get("risk_params", {})
    asset_tags = asset_tags or {}
    violations = []

    max_pos = risk_params.get("max_position_size", 0.10)
    max_sector = risk_params.get("max_sector_exposure", 0.30)
    max_country = risk_params.get("max_single_country", 0.50)

    # Position size check
    for i, sym in enumerate(symbols):
        w = weights[i] if i < len(weights) else 1.0 / len(symbols)
        if w > max_pos:
            violations.append({
                "type": "POSITION_SIZE",
                "symbol": sym,
                "value": round(w * 100, 1),
                "limit": round(max_pos * 100, 1),
                "message": f"{sym} weight {w*100:.1f}% exceeds {max_pos*100:.0f}% limit",
            })

    # Sector exposure
    sector_weights = {}
    for i, sym in enumerate(symbols):
        w = weights[i] if i < len(weights) else 1.0 / len(symbols)
        tags = asset_tags.get(sym, [])
        sector = classify_asset(sym, tags)
        sector_weights[sector] = sector_weights.get(sector, 0) + w

    for sector, sw in sector_weights.items():
        if sw > max_sector:
            violations.append({
                "type": "SECTOR_EXPOSURE",
                "sector": sector,
                "value": round(sw * 100, 1),
                "limit": round(max_sector * 100, 1),
                "message": f"{sector} exposure {sw*100:.1f}% exceeds {max_sector*100:.0f}% limit",
            })

    # Country concentration
    country_weights = {}
    for i, sym in enumerate(symbols):
        w = weights[i] if i < len(weights) else 1.0 / len(symbols)
        if ".HK" in sym or "china" in asset_tags.get(sym, []):
            country = "China/HK"
        elif any(x in sym for x in ["BTC", "ETH", "SOL", "-USD"]):
            country = "Crypto"
        else:
            country = "US"
        country_weights[country] = country_weights.get(country, 0) + w

    for country, cw in country_weights.items():
        if cw > max_country:
            violations.append({
                "type": "COUNTRY_CONCENTRATION",
                "country": country,
                "value": round(cw * 100, 1),
                "limit": round(max_country * 100, 1),
                "message": f"{country} concentration {cw*100:.1f}% exceeds {max_country*100:.0f}% limit",
            })

    return {
        "position_limit_ok": not any(v["type"] == "POSITION_SIZE" for v in violations),
        "sector_limit_ok": not any(v["type"] == "SECTOR_EXPOSURE" for v in violations),
        "country_limit_ok": not any(v["type"] == "COUNTRY_CONCENTRATION" for v in violations),
        "violation_count": len(violations),
        "violations": violations,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Hedge Fund — Portfolio Analytics & Risk")
    parser.add_argument("--symbols", type=str, default=None, help="Comma-separated symbols")
    parser.add_argument("--watchlist", type=str, default=None, help="Comma-separated watchlist names from assets.yaml")
    parser.add_argument("--weights", type=str, default=None, help="Comma-separated weights (must sum to 1.0)")
    parser.add_argument("--portfolio", type=str, default=None, help="Path to /tmp/hedge-fund/ dir with agent outputs")
    parser.add_argument("--period", type=str, default="1y", help="Historical period for risk calc")
    parser.add_argument("--benchmark", type=str, default="^GSPC", help="Benchmark symbol (default: S&P 500)")
    parser.add_argument("--stress-test", action="store_true", help="Run stress tests")
    parser.add_argument("--output", type=str, default=None, help="Output JSON file")
    parser.add_argument("--config", type=str, default=None, help="Path to assets.yaml")
    args = parser.parse_args()

    config = load_config(args.config)

    # Resolve symbols and weights
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",")]
    elif args.watchlist:
        # Load symbols from watchlist(s) defined in assets.yaml
        watchlist_names = [w.strip() for w in args.watchlist.split(",")]
        symbols = []
        watchlists = config.get("watchlists", {})
        for wl_name in watchlist_names:
            wl = watchlists.get(wl_name, {})
            for asset in wl.get("assets", []):
                sym = asset["symbol"]
                # Skip macro instruments that aren't tradeable
                if sym.startswith("^") and sym not in ("^GSPC", "^NDX", "^HSI"):
                    continue
                if "=F" in sym or "=X" in sym or "DX-Y" in sym:
                    continue
                symbols.append(sym)
        if not symbols:
            print(f"Error: No tradeable symbols found in watchlist(s): {args.watchlist}", file=sys.stderr)
            sys.exit(1)
        print(f"Loaded {len(symbols)} symbols from watchlist(s): {args.watchlist}", file=sys.stderr)
    elif args.portfolio:
        # Try to load from agent outputs
        symbols = extract_symbols_from_portfolio(args.portfolio)
        if not symbols:
            print("Error: Could not extract symbols from portfolio dir. Check that JSON files exist in the directory.", file=sys.stderr)
            sys.exit(1)
    else:
        print("Error: Specify --symbols, --watchlist, or --portfolio", file=sys.stderr)
        sys.exit(1)

    if args.weights:
        weights = [float(w.strip()) for w in args.weights.split(",")]
    else:
        weights = [1.0 / len(symbols)] * len(symbols)  # equal weight

    # Build asset tags lookup
    asset_tags = {}
    for wl in config.get("watchlists", {}).values():
        for a in wl.get("assets", []):
            asset_tags[a["symbol"]] = a.get("tags", [])

    print(f"Analyzing portfolio: {len(symbols)} positions", file=sys.stderr)

    # Load returns
    returns_dict, closes_dict = load_returns(symbols, args.period)
    benchmark_returns_dict, _ = load_returns([args.benchmark], args.period)
    benchmark_ret = benchmark_returns_dict.get(args.benchmark, [])

    # Portfolio returns (weighted)
    portfolio_returns = []
    if returns_dict:
        min_len = min(len(v) for v in returns_dict.values())
        for day in range(min_len):
            day_ret = 0.0
            for i, sym in enumerate(symbols):
                if sym in returns_dict and day < len(returns_dict[sym]):
                    w = weights[i] if i < len(weights) else 1.0 / len(symbols)
                    day_ret += returns_dict[sym][day] * w
            portfolio_returns.append(day_ret)

    # Calculate metrics
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "portfolio": {"symbols": symbols, "weights": [round(w, 4) for w in weights]},
        "portfolio_metrics": {
            "var_95_1d": calc_var(portfolio_returns, 0.95),
            "var_99_1d": calc_var(portfolio_returns, 0.99),
            "cvar_95": calc_cvar(portfolio_returns, 0.95),
            "max_drawdown_pct": calc_max_drawdown(portfolio_returns),
            "sharpe_ratio": calc_sharpe(portfolio_returns),
            "sortino_ratio": calc_sortino(portfolio_returns),
            "beta_sp500": calc_beta(portfolio_returns, benchmark_ret),
            "annualized_return": round(sum(portfolio_returns) / len(portfolio_returns) * 252 * 100, 2) if portfolio_returns else None,
            "annualized_volatility": round(calc_std(portfolio_returns) * math.sqrt(252) * 100, 2) if portfolio_returns else None,
            "data_points": len(portfolio_returns),
        },
        "individual_metrics": {},
    }

    # Per-asset metrics
    for sym in symbols:
        if sym not in returns_dict:
            continue
        ret = returns_dict[sym]
        output["individual_metrics"][sym] = {
            "var_95": calc_var(ret, 0.95),
            "max_drawdown_pct": calc_max_drawdown(ret),
            "sharpe": calc_sharpe(ret),
            "beta": calc_beta(ret, benchmark_ret),
            "annualized_vol": round(calc_std(ret) * math.sqrt(252) * 100, 2),
        }

    # Correlation
    if len(returns_dict) >= 2:
        output["correlation"] = calc_correlation_matrix(returns_dict)

    # Stress tests
    if args.stress_test or args.portfolio:
        output["stress_tests"] = run_stress_tests(symbols, weights, asset_tags)

    # Compliance
    output["compliance"] = check_compliance(symbols, weights, config, asset_tags)

    # Risk score
    var95 = output["portfolio_metrics"]["var_95_1d"]
    max_dd = output["portfolio_metrics"]["max_drawdown_pct"]
    violations = output["compliance"]["violation_count"]

    if var95 is not None and max_dd is not None:
        if var95 < -5 or max_dd > 30 or violations > 2:
            risk_score = "EXTREME"
        elif var95 < -3 or max_dd > 20 or violations > 0:
            risk_score = "HIGH"
        elif var95 < -2 or max_dd > 15:
            risk_score = "ELEVATED"
        elif var95 < -1 or max_dd > 10:
            risk_score = "MODERATE"
        else:
            risk_score = "LOW"
    else:
        risk_score = "UNKNOWN"

    output["risk_score"] = risk_score

    result = json.dumps(output, indent=2, ensure_ascii=False, default=str)

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"\nRisk report saved to: {args.output}", file=sys.stderr)
    else:
        print(result)


def calc_std(returns_list):
    """Standard deviation of returns."""
    if not returns_list or len(returns_list) < 2:
        return 0.0
    mean = sum(returns_list) / len(returns_list)
    variance = sum((r - mean) ** 2 for r in returns_list) / (len(returns_list) - 1)
    return math.sqrt(variance)


def extract_symbols_from_portfolio(portfolio_dir):
    """Extract symbols from agent output files in the portfolio directory."""
    symbols = set()
    portfolio_path = Path(portfolio_dir)

    for json_file in portfolio_path.glob("*.json"):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Look for symbols in various output formats
            for key in ("factor_scores", "ratings", "asset_sentiment", "technical_outlook", "trade_plan"):
                if key in data:
                    if isinstance(data[key], dict):
                        symbols.update(data[key].keys())
                    elif isinstance(data[key], list):
                        for item in data[key]:
                            if isinstance(item, dict) and "symbol" in item:
                                symbols.add(item["symbol"])
        except (json.JSONDecodeError, KeyError):
            continue

    return list(symbols) if symbols else []


if __name__ == "__main__":
    main()
