#!/usr/bin/env python3
"""
Hedge Fund Agent Team — Market Data Fetcher

Fetches price data, fundamentals, and quotes from multiple sources:
  - Yahoo Finance (yfinance): Free, global coverage
  - Longbridge (longport): HK/US/CN real-time, requires API key
  - TradingView (tradingview-ta): Free technical ratings

Usage:
    python fetch_market_data.py --watchlist us_tech_ai --source yahoo
    python fetch_market_data.py --watchlist hk_china --source longbridge
    python fetch_market_data.py --symbols NVDA,MSFT --source yahoo --period 6mo
    python fetch_market_data.py --watchlist macro --data-type fundamentals
    python fetch_market_data.py --symbols BTC-USD --source yahoo --interval 1h
"""

import argparse
import json
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


def load_assets_config(path=None):
    """Load asset universe configuration."""
    config_path = Path(path) if path else ASSETS_CONFIG
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_symbols(config, watchlists=None, symbols=None):
    """Resolve watchlist names or raw symbols into asset dicts."""
    assets = []
    if symbols:
        for s in symbols.split(","):
            s = s.strip()
            assets.append({"symbol": s, "tv_symbol": None, "lb_symbol": None})
        return assets

    if not watchlists:
        watchlists = list(config.get("watchlists", {}).keys())
    else:
        watchlists = [w.strip() for w in watchlists.split(",")]

    for wl_name in watchlists:
        wl = config.get("watchlists", {}).get(wl_name, {})
        for asset in wl.get("assets", []):
            assets.append(asset)
    return assets


# ---------------------------------------------------------------------------
# Yahoo Finance
# ---------------------------------------------------------------------------


def fetch_yahoo_prices(assets, period="3mo", interval="1d"):
    """Fetch historical prices from Yahoo Finance."""
    try:
        import yfinance as yf
    except ImportError:
        print("Error: yfinance required. pip install yfinance", file=sys.stderr)
        return {}

    symbols = [a["symbol"] for a in assets]
    print(f"[Yahoo] Fetching prices for {len(symbols)} symbols...", file=sys.stderr)

    results = {}
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period=period, interval=interval)
            if hist.empty:
                print(f"  [WARN] No data for {sym}", file=sys.stderr)
                continue

            records = []
            for idx, row in hist.iterrows():
                records.append({
                    "date": idx.strftime("%Y-%m-%d") if interval == "1d" else idx.isoformat(),
                    "open": round(row["Open"], 4),
                    "high": round(row["High"], 4),
                    "low": round(row["Low"], 4),
                    "close": round(row["Close"], 4),
                    "volume": int(row["Volume"]),
                })

            latest = records[-1] if records else {}
            results[sym] = {
                "symbol": sym,
                "latest_price": latest.get("close"),
                "latest_date": latest.get("date"),
                "period": period,
                "interval": interval,
                "data_points": len(records),
                "history": records,
            }
            print(f"  {sym}: {len(records)} bars, latest ${latest.get('close', 'N/A')}", file=sys.stderr)
        except Exception as e:
            print(f"  [ERROR] {sym}: {e}", file=sys.stderr)

    return results


def fetch_yahoo_fundamentals(assets):
    """Fetch fundamental data from Yahoo Finance."""
    try:
        import yfinance as yf
    except ImportError:
        print("Error: yfinance required. pip install yfinance", file=sys.stderr)
        return {}

    symbols = [a["symbol"] for a in assets if not a["symbol"].startswith("^") and "=F" not in a["symbol"]]
    print(f"[Yahoo] Fetching fundamentals for {len(symbols)} symbols...", file=sys.stderr)

    results = {}
    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            info = ticker.info

            results[sym] = {
                "symbol": sym,
                "name": info.get("longName", info.get("shortName", sym)),
                "sector": info.get("sector", "N/A"),
                "industry": info.get("industry", "N/A"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "ps_ratio": info.get("priceToSalesTrailing12Months"),
                "pb_ratio": info.get("priceToBook"),
                "ev_ebitda": info.get("enterpriseToEbitda"),
                "revenue": info.get("totalRevenue"),
                "revenue_growth": info.get("revenueGrowth"),
                "gross_margins": info.get("grossMargins"),
                "operating_margins": info.get("operatingMargins"),
                "profit_margins": info.get("profitMargins"),
                "free_cash_flow": info.get("freeCashflow"),
                "debt_to_equity": info.get("debtToEquity"),
                "return_on_equity": info.get("returnOnEquity"),
                "current_price": info.get("currentPrice", info.get("regularMarketPrice")),
                "52w_high": info.get("fiftyTwoWeekHigh"),
                "52w_low": info.get("fiftyTwoWeekLow"),
                "avg_volume": info.get("averageVolume"),
                "dividend_yield": info.get("dividendYield"),
                "beta": info.get("beta"),
                "analyst_target": info.get("targetMeanPrice"),
                "analyst_recommendation": info.get("recommendationKey"),
            }
            print(f"  {sym}: {results[sym]['name']} — PE={results[sym]['pe_ratio']}, MCap={results[sym]['market_cap']}", file=sys.stderr)
        except Exception as e:
            print(f"  [ERROR] {sym}: {e}", file=sys.stderr)

    return results


# ---------------------------------------------------------------------------
# Longbridge
# ---------------------------------------------------------------------------


def fetch_longbridge_quotes(assets):
    """Fetch real-time quotes from Longbridge API."""
    app_key = os.environ.get("LONGPORT_APP_KEY")
    app_secret = os.environ.get("LONGPORT_APP_SECRET")
    access_token = os.environ.get("LONGPORT_ACCESS_TOKEN")

    if not all([app_key, app_secret, access_token]):
        print("[Longbridge] SKIP: LONGPORT_APP_KEY/SECRET/ACCESS_TOKEN not set", file=sys.stderr)
        return {}

    try:
        from longport.openapi import Config, QuoteContext
    except ImportError:
        print("Error: longport required. pip install longport", file=sys.stderr)
        return {}

    lb_symbols = [a.get("lb_symbol") for a in assets if a.get("lb_symbol")]
    if not lb_symbols:
        print("[Longbridge] No lb_symbol configured for these assets", file=sys.stderr)
        return {}

    print(f"[Longbridge] Fetching quotes for {len(lb_symbols)} symbols...", file=sys.stderr)

    try:
        config = Config(
            app_key=app_key,
            app_secret=app_secret,
            access_token=access_token,
        )
        ctx = QuoteContext(config)
        quotes = ctx.quote(lb_symbols)

        results = {}
        for q in quotes:
            sym = q.symbol
            results[sym] = {
                "symbol": sym,
                "last_done": float(q.last_done) if q.last_done else None,
                "prev_close": float(q.prev_close_price) if q.prev_close_price else None,
                "open": float(q.open) if q.open else None,
                "high": float(q.high) if q.high else None,
                "low": float(q.low) if q.low else None,
                "volume": int(q.volume) if q.volume else 0,
                "turnover": float(q.turnover) if q.turnover else 0,
                "timestamp": q.timestamp.isoformat() if q.timestamp else None,
            }
            chg = ""
            if results[sym]["last_done"] and results[sym]["prev_close"]:
                pct = (results[sym]["last_done"] / results[sym]["prev_close"] - 1) * 100
                chg = f" ({pct:+.2f}%)"
            print(f"  {sym}: ${results[sym]['last_done']}{chg}", file=sys.stderr)

        return results
    except Exception as e:
        print(f"[Longbridge] ERROR: {e}", file=sys.stderr)
        return {}


def fetch_longbridge_fundamentals(assets):
    """Fetch fundamental data from Longbridge (capital flow, broker queue)."""
    app_key = os.environ.get("LONGPORT_APP_KEY")
    app_secret = os.environ.get("LONGPORT_APP_SECRET")
    access_token = os.environ.get("LONGPORT_ACCESS_TOKEN")

    if not all([app_key, app_secret, access_token]):
        print("[Longbridge] SKIP: credentials not set", file=sys.stderr)
        return {}

    try:
        from longport.openapi import Config, QuoteContext
    except ImportError:
        return {}

    lb_symbols = [a.get("lb_symbol") for a in assets if a.get("lb_symbol")]
    if not lb_symbols:
        return {}

    print(f"[Longbridge] Fetching capital flow for {len(lb_symbols)} symbols...", file=sys.stderr)

    try:
        config = Config(
            app_key=app_key,
            app_secret=app_secret,
            access_token=access_token,
        )
        ctx = QuoteContext(config)

        results = {}
        for sym in lb_symbols:
            try:
                flow = ctx.capital_flow(sym)
                results[sym] = {
                    "symbol": sym,
                    "capital_flow": [
                        {"inflow": float(f.inflow), "timestamp": f.timestamp.isoformat()}
                        for f in (flow or [])[:10]
                    ],
                }
            except Exception as e:
                print(f"  [WARN] {sym} capital flow: {e}", file=sys.stderr)

        return results
    except Exception as e:
        print(f"[Longbridge] ERROR: {e}", file=sys.stderr)
        return {}


# ---------------------------------------------------------------------------
# TradingView
# ---------------------------------------------------------------------------


def fetch_tradingview_analysis(assets):
    """Fetch technical analysis ratings from TradingView."""
    try:
        from tradingview_ta import TA_Handler, Interval
    except ImportError:
        print("Error: tradingview-ta required. pip install tradingview-ta", file=sys.stderr)
        return {}

    tv_assets = [(a, a.get("tv_symbol")) for a in assets if a.get("tv_symbol")]
    if not tv_assets:
        print("[TradingView] No tv_symbol configured for these assets", file=sys.stderr)
        return {}

    print(f"[TradingView] Fetching analysis for {len(tv_assets)} symbols...", file=sys.stderr)

    results = {}
    for asset, tv_sym in tv_assets:
        try:
            parts = tv_sym.split(":")
            if len(parts) != 2:
                continue
            exchange, ticker = parts

            handler = TA_Handler(
                symbol=ticker,
                screener="america" if exchange in ("NASDAQ", "NYSE", "SP") else
                         "hongkong" if exchange == "HKEX" else
                         "crypto" if exchange == "BINANCE" else
                         "cfd" if exchange in ("TVC", "COMEX", "NYMEX", "FX") else
                         "america",
                exchange=exchange,
                interval=Interval.INTERVAL_1_DAY,
            )
            analysis = handler.get_analysis()

            results[asset["symbol"]] = {
                "symbol": asset["symbol"],
                "tv_symbol": tv_sym,
                "summary": {
                    "recommendation": analysis.summary.get("RECOMMENDATION", ""),
                    "buy": analysis.summary.get("BUY", 0),
                    "sell": analysis.summary.get("SELL", 0),
                    "neutral": analysis.summary.get("NEUTRAL", 0),
                },
                "oscillators": {
                    "recommendation": analysis.oscillators.get("RECOMMENDATION", ""),
                    "buy": analysis.oscillators.get("BUY", 0),
                    "sell": analysis.oscillators.get("SELL", 0),
                    "neutral": analysis.oscillators.get("NEUTRAL", 0),
                },
                "moving_averages": {
                    "recommendation": analysis.moving_averages.get("RECOMMENDATION", ""),
                    "buy": analysis.moving_averages.get("BUY", 0),
                    "sell": analysis.moving_averages.get("SELL", 0),
                    "neutral": analysis.moving_averages.get("NEUTRAL", 0),
                },
                "indicators": {
                    "rsi": analysis.indicators.get("RSI"),
                    "macd_macd": analysis.indicators.get("MACD.macd"),
                    "macd_signal": analysis.indicators.get("MACD.signal"),
                    "bb_upper": analysis.indicators.get("BB.upper"),
                    "bb_lower": analysis.indicators.get("BB.lower"),
                    "ema_20": analysis.indicators.get("EMA20"),
                    "sma_50": analysis.indicators.get("SMA50"),
                    "sma_200": analysis.indicators.get("SMA200"),
                    "atr": analysis.indicators.get("ATR"),
                    "adx": analysis.indicators.get("ADX"),
                    "cci": analysis.indicators.get("CCI20"),
                    "stoch_k": analysis.indicators.get("Stoch.K"),
                    "stoch_d": analysis.indicators.get("Stoch.D"),
                    "williams_r": analysis.indicators.get("W.R"),
                    "volume": analysis.indicators.get("volume"),
                    "close": analysis.indicators.get("close"),
                },
            }
            rec = results[asset["symbol"]]["summary"]["recommendation"]
            print(f"  {asset['symbol']}: {rec} (B:{analysis.summary.get('BUY',0)} S:{analysis.summary.get('SELL',0)} N:{analysis.summary.get('NEUTRAL',0)})", file=sys.stderr)
        except Exception as e:
            print(f"  [WARN] {asset.get('symbol', tv_sym)}: {e}", file=sys.stderr)

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Hedge Fund — Market Data Fetcher")
    parser.add_argument("--watchlist", type=str, default=None, help="Comma-separated watchlist names from assets.yaml")
    parser.add_argument("--symbols", type=str, default=None, help="Comma-separated ticker symbols (override watchlist)")
    parser.add_argument("--source", choices=["yahoo", "longbridge", "tradingview", "all"], default="yahoo", help="Data source")
    parser.add_argument("--data-type", choices=["prices", "fundamentals", "all"], default="prices", help="Type of data to fetch")
    parser.add_argument("--period", type=str, default="3mo", help="History period for Yahoo (1d,5d,1mo,3mo,6mo,1y,2y,5y)")
    parser.add_argument("--interval", type=str, default="1d", help="Bar interval (1m,5m,15m,1h,1d,1wk,1mo)")
    parser.add_argument("--output", type=str, default=None, help="Output JSON file path")
    parser.add_argument("--config", type=str, default=None, help="Path to assets.yaml config")
    args = parser.parse_args()

    config = load_assets_config(args.config)
    assets = resolve_symbols(config, args.watchlist, args.symbols)

    if not assets:
        print("Error: No assets to fetch. Specify --watchlist or --symbols.", file=sys.stderr)
        sys.exit(1)

    print(f"Resolved {len(assets)} assets", file=sys.stderr)

    all_data = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source": args.source,
        "data_type": args.data_type,
        "asset_count": len(assets),
    }

    sources = [args.source] if args.source != "all" else ["yahoo", "longbridge", "tradingview"]

    for source in sources:
        if source == "yahoo":
            if args.data_type in ("prices", "all"):
                all_data["yahoo_prices"] = fetch_yahoo_prices(assets, args.period, args.interval)
            if args.data_type in ("fundamentals", "all"):
                all_data["yahoo_fundamentals"] = fetch_yahoo_fundamentals(assets)

        elif source == "longbridge":
            all_data["longbridge_quotes"] = fetch_longbridge_quotes(assets)
            if args.data_type in ("fundamentals", "all"):
                all_data["longbridge_fundamentals"] = fetch_longbridge_fundamentals(assets)

        elif source == "tradingview":
            all_data["tradingview_analysis"] = fetch_tradingview_analysis(assets)

    output = json.dumps(all_data, indent=2, ensure_ascii=False, default=str)

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"\nData saved to: {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
