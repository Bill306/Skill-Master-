#!/usr/bin/env python3
"""
Hedge Fund Agent Team — Technical Analysis Module

Calculates technical indicators for the Trader agent.
Combines local computation (pandas/numpy) with TradingView ratings.

Usage:
    python technical_analysis.py --symbols NVDA,MSFT --source both
    python technical_analysis.py --symbols BTC-USD --source yahoo --period 6mo
    python technical_analysis.py --watchlist us_tech_ai --source tradingview
    python technical_analysis.py --symbols 9988.HK --indicators rsi,macd,bb
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


def load_assets_config(path=None):
    config_path = Path(path) if path else ASSETS_CONFIG
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_symbols(config, watchlists=None, symbols=None):
    assets = []
    if symbols:
        # Try to find matching asset in config for tv_symbol
        all_assets = {}
        for wl in config.get("watchlists", {}).values():
            for a in wl.get("assets", []):
                all_assets[a["symbol"]] = a
        for s in symbols.split(","):
            s = s.strip()
            if s in all_assets:
                assets.append(all_assets[s])
            else:
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
# Local TA Calculations (pandas + numpy)
# ---------------------------------------------------------------------------


def compute_local_ta(symbol, period="6mo", interval="1d"):
    """Compute technical indicators from Yahoo Finance data using pandas."""
    try:
        import numpy as np
        import yfinance as yf
    except ImportError:
        print("Error: yfinance and numpy required", file=sys.stderr)
        return None

    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
    except Exception as e:
        print(f"  [ERROR] {symbol}: {e}", file=sys.stderr)
        return None

    if df.empty or len(df) < 20:
        print(f"  [WARN] {symbol}: insufficient data ({len(df)} bars)", file=sys.stderr)
        return None

    close = df["Close"].values
    high = df["High"].values
    low = df["Low"].values
    volume = df["Volume"].values
    n = len(close)

    result = {"symbol": symbol, "data_points": n, "latest_close": round(float(close[-1]), 4)}

    # --- Moving Averages ---
    def sma(arr, window):
        if len(arr) < window:
            return None
        return float(np.mean(arr[-window:]))

    def ema(arr, window):
        if len(arr) < window:
            return None
        multiplier = 2 / (window + 1)
        ema_val = float(np.mean(arr[:window]))
        for price in arr[window:]:
            ema_val = (float(price) - ema_val) * multiplier + ema_val
        return ema_val

    sma_20 = sma(close, 20)
    sma_50 = sma(close, 50)
    sma_200 = sma(close, 200)
    ema_12 = ema(close, 12)
    ema_26 = ema(close, 26)

    result["moving_averages"] = {
        "sma_20": round(sma_20, 4) if sma_20 else None,
        "sma_50": round(sma_50, 4) if sma_50 else None,
        "sma_200": round(sma_200, 4) if sma_200 else None,
        "ema_12": round(ema_12, 4) if ema_12 else None,
        "ema_26": round(ema_26, 4) if ema_26 else None,
    }

    # MA alignment (bullish = price > sma20 > sma50 > sma200)
    price = float(close[-1])
    if sma_20 and sma_50 and sma_200:
        if price > sma_20 > sma_50 > sma_200:
            ma_alignment = "BULLISH"
        elif price < sma_20 < sma_50 < sma_200:
            ma_alignment = "BEARISH"
        else:
            ma_alignment = "MIXED"
    else:
        ma_alignment = "INSUFFICIENT_DATA"
    result["moving_averages"]["alignment"] = ma_alignment

    # --- RSI (14) ---
    def calc_rsi(prices, window=14):
        if len(prices) < window + 1:
            return None
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = float(np.mean(gains[:window]))
        avg_loss = float(np.mean(losses[:window]))
        for i in range(window, len(deltas)):
            avg_gain = (avg_gain * (window - 1) + float(gains[i])) / window
            avg_loss = (avg_loss * (window - 1) + float(losses[i])) / window
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return round(100 - (100 / (1 + rs)), 2)

    rsi = calc_rsi(close, 14)
    rsi_signal = "NEUTRAL"
    if rsi is not None:
        if rsi >= 70:
            rsi_signal = "OVERBOUGHT"
        elif rsi <= 30:
            rsi_signal = "OVERSOLD"
    result["rsi"] = {"value": rsi, "signal": rsi_signal}

    # --- MACD (12, 26, 9) ---
    if ema_12 and ema_26:
        macd_line = ema_12 - ema_26
        # Approximate signal line from recent MACD values
        macd_values = []
        for i in range(max(0, n - 35), n):
            e12 = ema(close[:i + 1], 12)
            e26 = ema(close[:i + 1], 26)
            if e12 and e26:
                macd_values.append(e12 - e26)

        signal_line = ema(macd_values, 9) if len(macd_values) >= 9 else None
        histogram = (macd_line - signal_line) if signal_line else None

        macd_signal = "NEUTRAL"
        if signal_line:
            if macd_line > signal_line:
                macd_signal = "BUY"
            else:
                macd_signal = "SELL"

        result["macd"] = {
            "macd_line": round(macd_line, 4),
            "signal_line": round(signal_line, 4) if signal_line else None,
            "histogram": round(histogram, 4) if histogram else None,
            "signal": macd_signal,
        }
    else:
        result["macd"] = {"macd_line": None, "signal_line": None, "histogram": None, "signal": "INSUFFICIENT_DATA"}

    # --- Bollinger Bands (20, 2) ---
    if n >= 20:
        bb_sma = float(np.mean(close[-20:]))
        bb_std = float(np.std(close[-20:], ddof=1))
        bb_upper = bb_sma + 2 * bb_std
        bb_lower = bb_sma - 2 * bb_std

        bb_position = "MIDDLE"
        if price >= bb_upper:
            bb_position = "ABOVE_UPPER"
        elif price <= bb_lower:
            bb_position = "BELOW_LOWER"
        elif price > bb_sma + bb_std:
            bb_position = "UPPER"
        elif price < bb_sma - bb_std:
            bb_position = "LOWER"

        result["bollinger_bands"] = {
            "upper": round(bb_upper, 4),
            "middle": round(bb_sma, 4),
            "lower": round(bb_lower, 4),
            "bandwidth": round((bb_upper - bb_lower) / bb_sma * 100, 2),
            "position": bb_position,
        }

    # --- ATR (14) ---
    if n >= 15:
        true_ranges = []
        for i in range(1, min(n, 15)):
            tr = max(
                float(high[-i]) - float(low[-i]),
                abs(float(high[-i]) - float(close[-i - 1])),
                abs(float(low[-i]) - float(close[-i - 1])),
            )
            true_ranges.append(tr)
        atr = sum(true_ranges) / len(true_ranges)
        result["atr"] = {
            "value": round(atr, 4),
            "pct_of_price": round(atr / price * 100, 2),
        }

    # --- Volume Analysis ---
    if n >= 20:
        avg_vol_20 = float(np.mean(volume[-20:]))
        latest_vol = float(volume[-1])
        vol_ratio = latest_vol / avg_vol_20 if avg_vol_20 > 0 else 0

        # OBV (On Balance Volume) trend
        obv = [0.0]
        for i in range(1, n):
            if close[i] > close[i - 1]:
                obv.append(obv[-1] + float(volume[i]))
            elif close[i] < close[i - 1]:
                obv.append(obv[-1] - float(volume[i]))
            else:
                obv.append(obv[-1])

        obv_trend = "FLAT"
        if len(obv) >= 5:
            obv_recent = obv[-5:]
            if obv_recent[-1] > obv_recent[0] * 1.02:
                obv_trend = "INCREASING"
            elif obv_recent[-1] < obv_recent[0] * 0.98:
                obv_trend = "DECREASING"

        result["volume"] = {
            "latest": int(latest_vol),
            "avg_20d": int(avg_vol_20),
            "ratio": round(vol_ratio, 2),
            "signal": "HIGH" if vol_ratio > 1.5 else "LOW" if vol_ratio < 0.5 else "NORMAL",
            "obv_trend": obv_trend,
        }

    # --- Support / Resistance ---
    if n >= 20:
        recent_high = float(np.max(high[-20:]))
        recent_low = float(np.min(low[-20:]))
        pivot = (recent_high + recent_low + price) / 3
        r1 = 2 * pivot - recent_low
        s1 = 2 * pivot - recent_high
        r2 = pivot + (recent_high - recent_low)
        s2 = pivot - (recent_high - recent_low)

        result["support_resistance"] = {
            "pivot": round(pivot, 4),
            "resistance_1": round(r1, 4),
            "resistance_2": round(r2, 4),
            "support_1": round(s1, 4),
            "support_2": round(s2, 4),
            "20d_high": round(recent_high, 4),
            "20d_low": round(recent_low, 4),
        }

    # --- Returns ---
    def calc_return(prices, days):
        if len(prices) < days + 1:
            return None
        return round((float(prices[-1]) / float(prices[-days - 1]) - 1) * 100, 2)

    result["returns"] = {
        "1d": calc_return(close, 1),
        "5d": calc_return(close, 5),
        "1m": calc_return(close, 21),
        "3m": calc_return(close, 63),
    }
    if n > 126:
        result["returns"]["6m"] = calc_return(close, 126)

    # --- Overall Signal ---
    signals = []
    if rsi and rsi <= 30:
        signals.append("BUY")
    elif rsi and rsi >= 70:
        signals.append("SELL")
    else:
        signals.append("NEUTRAL")

    if result.get("macd", {}).get("signal") == "BUY":
        signals.append("BUY")
    elif result.get("macd", {}).get("signal") == "SELL":
        signals.append("SELL")
    else:
        signals.append("NEUTRAL")

    if ma_alignment == "BULLISH":
        signals.append("BUY")
    elif ma_alignment == "BEARISH":
        signals.append("SELL")
    else:
        signals.append("NEUTRAL")

    buy_count = signals.count("BUY")
    sell_count = signals.count("SELL")
    if buy_count > sell_count:
        overall = "BUY"
    elif sell_count > buy_count:
        overall = "SELL"
    else:
        overall = "NEUTRAL"

    # Trend strength
    strength_score = abs(buy_count - sell_count)
    strength = "STRONG" if strength_score >= 2 else "MODERATE" if strength_score == 1 else "WEAK"

    result["signal"] = {
        "overall": overall,
        "strength": strength,
        "components": {"rsi": signals[0], "macd": signals[1], "ma": signals[2]},
    }

    return result


# ---------------------------------------------------------------------------
# TradingView Analysis
# ---------------------------------------------------------------------------


def fetch_tradingview(assets):
    """Fetch TradingView technical analysis ratings."""
    try:
        from tradingview_ta import TA_Handler, Interval
    except ImportError:
        print("Error: tradingview-ta required. pip install tradingview-ta", file=sys.stderr)
        return {}

    results = {}
    for asset in assets:
        tv_sym = asset.get("tv_symbol")
        if not tv_sym:
            continue

        parts = tv_sym.split(":")
        if len(parts) != 2:
            continue
        exchange, ticker = parts

        try:
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
                "recommendation": analysis.summary.get("RECOMMENDATION", ""),
                "buy_signals": analysis.summary.get("BUY", 0),
                "sell_signals": analysis.summary.get("SELL", 0),
                "neutral_signals": analysis.summary.get("NEUTRAL", 0),
                "oscillators_rec": analysis.oscillators.get("RECOMMENDATION", ""),
                "ma_rec": analysis.moving_averages.get("RECOMMENDATION", ""),
                "indicators": {
                    "rsi": analysis.indicators.get("RSI"),
                    "macd_macd": analysis.indicators.get("MACD.macd"),
                    "macd_signal": analysis.indicators.get("MACD.signal"),
                    "bb_upper": analysis.indicators.get("BB.upper"),
                    "bb_lower": analysis.indicators.get("BB.lower"),
                    "sma_50": analysis.indicators.get("SMA50"),
                    "sma_200": analysis.indicators.get("SMA200"),
                    "atr": analysis.indicators.get("ATR"),
                    "close": analysis.indicators.get("close"),
                },
            }
            rec = results[asset["symbol"]]["recommendation"]
            print(f"  {asset['symbol']}: TV={rec}", file=sys.stderr)
        except Exception as e:
            print(f"  [WARN] {asset['symbol']}: {e}", file=sys.stderr)

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Hedge Fund — Technical Analysis")
    parser.add_argument("--symbols", type=str, default=None, help="Comma-separated symbols")
    parser.add_argument("--watchlist", type=str, default=None, help="Watchlist names from assets.yaml")
    parser.add_argument("--source", choices=["yahoo", "tradingview", "both"], default="both", help="Data source for TA")
    parser.add_argument("--period", type=str, default="6mo", help="History period for local TA")
    parser.add_argument("--interval", type=str, default="1d", help="Bar interval")
    parser.add_argument("--output", type=str, default=None, help="Output JSON file")
    parser.add_argument("--config", type=str, default=None, help="Path to assets.yaml")
    args = parser.parse_args()

    config = load_assets_config(args.config)
    assets = resolve_symbols(config, args.watchlist, args.symbols)

    if not assets:
        print("Error: No assets. Specify --watchlist or --symbols.", file=sys.stderr)
        sys.exit(1)

    print(f"Running TA on {len(assets)} assets (source={args.source})...", file=sys.stderr)

    output_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": args.source,
        "asset_count": len(assets),
        "local_ta": {},
        "tradingview": {},
    }

    if args.source in ("yahoo", "both"):
        for asset in assets:
            sym = asset["symbol"]
            print(f"  [{sym}] Computing local TA...", file=sys.stderr)
            ta = compute_local_ta(sym, args.period, args.interval)
            if ta:
                output_data["local_ta"][sym] = ta

    if args.source in ("tradingview", "both"):
        output_data["tradingview"] = fetch_tradingview(assets)

    result = json.dumps(output_data, indent=2, ensure_ascii=False, default=str)

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"\nTA results saved to: {args.output}", file=sys.stderr)
    else:
        print(result)


if __name__ == "__main__":
    main()
