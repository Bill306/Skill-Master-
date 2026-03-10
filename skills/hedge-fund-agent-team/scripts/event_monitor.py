#!/usr/bin/env python3
"""
Hedge Fund Agent Team — Event Monitor & Auto-Trigger

Monitors market events and conditions, triggers appropriate agent team responses.
Integrates with MCP servers (Notion, Slack) for logging and alerts.

Events:
  - Scheduled: FOMC, CPI, NFP, earnings dates
  - Price-based: stop-loss breach, breakout, gap, unusual volume
  - Volatility: VIX spike, correlation break
  - News: breaking news sentiment shift (via ai-news-digest)

Usage:
    # Check all events and report triggers
    python event_monitor.py check --config events.yaml

    # Monitor a specific portfolio for price alerts
    python event_monitor.py monitor --symbols NVDA,MSFT --check-stops

    # Check upcoming economic calendar
    python event_monitor.py calendar --days 7

    # Generate alert payload (for MCP/Slack/Notion integration)
    python event_monitor.py alert --event "VIX_SPIKE" --data '{"vix": 35.2}'
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: PyYAML required. pip install pyyaml", file=sys.stderr)
    sys.exit(1)

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_DIR = SCRIPT_DIR.parent / "config"
DATA_DIR = SCRIPT_DIR.parent / "data"
EVENTS_CONFIG = CONFIG_DIR / "events.yaml"
ALERTS_LOG = DATA_DIR / "alerts.jsonl"


def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_events_config(path=None):
    config_path = Path(path) if path else EVENTS_CONFIG
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Price & Volume Monitors
# ---------------------------------------------------------------------------


def check_price_alerts(symbols, history_file=None):
    """Check for price-based events: stop breach, breakout, gaps, unusual volume."""
    try:
        import yfinance as yf
    except ImportError:
        print("Error: yfinance required", file=sys.stderr)
        return []

    alerts = []

    # Load open positions from history for stop-loss checking
    open_positions = {}
    if history_file and Path(history_file).exists():
        with open(history_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line.strip())
                    if rec.get("status") == "OPEN" and rec.get("stop_loss"):
                        open_positions[rec["symbol"]] = rec
                except json.JSONDecodeError:
                    continue

    for sym in symbols:
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="5d", interval="1d")
            if hist.empty or len(hist) < 2:
                continue

            current = float(hist["Close"].iloc[-1])
            prev_close = float(hist["Close"].iloc[-2])
            volume_today = float(hist["Volume"].iloc[-1])
            avg_volume = float(hist["Volume"].mean())
            day_high = float(hist["High"].iloc[-1])
            day_low = float(hist["Low"].iloc[-1])

            # --- Stop-loss breach ---
            if sym in open_positions:
                pos = open_positions[sym]
                stop = float(pos["stop_loss"])
                direction = pos.get("direction", "LONG")
                if direction == "LONG" and current <= stop:
                    alerts.append({
                        "type": "STOP_LOSS_BREACH",
                        "severity": "CRITICAL",
                        "symbol": sym,
                        "message": f"{sym} breached stop-loss: current ${current:.2f} <= stop ${stop:.2f}",
                        "data": {"current": current, "stop": stop, "direction": direction},
                        "action": "CLOSE_POSITION",
                    })
                elif direction == "SHORT" and current >= stop:
                    alerts.append({
                        "type": "STOP_LOSS_BREACH",
                        "severity": "CRITICAL",
                        "symbol": sym,
                        "message": f"{sym} breached stop-loss: current ${current:.2f} >= stop ${stop:.2f}",
                        "data": {"current": current, "stop": stop, "direction": direction},
                        "action": "CLOSE_POSITION",
                    })

            # --- Gap detection ---
            gap_pct = (float(hist["Open"].iloc[-1]) / prev_close - 1) * 100
            if abs(gap_pct) >= 3.0:
                gap_dir = "UP" if gap_pct > 0 else "DOWN"
                alerts.append({
                    "type": "PRICE_GAP",
                    "severity": "HIGH" if abs(gap_pct) >= 5.0 else "MEDIUM",
                    "symbol": sym,
                    "message": f"{sym} gapped {gap_dir} {abs(gap_pct):.1f}%",
                    "data": {"gap_pct": round(gap_pct, 2), "direction": gap_dir},
                    "action": "ANALYZE",
                })

            # --- Large daily move ---
            daily_change_pct = (current / prev_close - 1) * 100
            if abs(daily_change_pct) >= 5.0:
                alerts.append({
                    "type": "LARGE_MOVE",
                    "severity": "HIGH",
                    "symbol": sym,
                    "message": f"{sym} moved {daily_change_pct:+.1f}% today",
                    "data": {"change_pct": round(daily_change_pct, 2), "current": current},
                    "action": "ANALYZE",
                })

            # --- Unusual volume ---
            if avg_volume > 0:
                vol_ratio = volume_today / avg_volume
                if vol_ratio >= 2.5:
                    alerts.append({
                        "type": "UNUSUAL_VOLUME",
                        "severity": "MEDIUM",
                        "symbol": sym,
                        "message": f"{sym} volume {vol_ratio:.1f}x average",
                        "data": {"volume": int(volume_today), "avg_volume": int(avg_volume), "ratio": round(vol_ratio, 1)},
                        "action": "INVESTIGATE",
                    })

            # --- New 52-week high/low ---
            info = ticker.info
            high_52w = info.get("fiftyTwoWeekHigh")
            low_52w = info.get("fiftyTwoWeekLow")
            if high_52w and current >= high_52w * 0.98:
                alerts.append({
                    "type": "NEAR_52W_HIGH",
                    "severity": "LOW",
                    "symbol": sym,
                    "message": f"{sym} near 52-week high (${current:.2f} vs ${high_52w:.2f})",
                    "data": {"current": current, "52w_high": high_52w},
                    "action": "MONITOR",
                })
            if low_52w and current <= low_52w * 1.02:
                alerts.append({
                    "type": "NEAR_52W_LOW",
                    "severity": "MEDIUM",
                    "symbol": sym,
                    "message": f"{sym} near 52-week low (${current:.2f} vs ${low_52w:.2f})",
                    "data": {"current": current, "52w_low": low_52w},
                    "action": "INVESTIGATE",
                })

        except Exception as e:
            print(f"  [WARN] {sym}: {e}", file=sys.stderr)

    return alerts


# ---------------------------------------------------------------------------
# Volatility Monitor
# ---------------------------------------------------------------------------


def check_volatility_alerts():
    """Check VIX level and volatility regime changes."""
    try:
        import yfinance as yf
    except ImportError:
        return []

    alerts = []

    try:
        vix = yf.Ticker("^VIX")
        hist = vix.history(period="1mo", interval="1d")
        if hist.empty:
            return alerts

        current_vix = float(hist["Close"].iloc[-1])
        avg_vix = float(hist["Close"].mean())
        prev_vix = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else current_vix

        # VIX spike (>20% daily increase)
        vix_change = (current_vix / prev_vix - 1) * 100 if prev_vix > 0 else 0
        if vix_change >= 20:
            alerts.append({
                "type": "VIX_SPIKE",
                "severity": "CRITICAL",
                "symbol": "^VIX",
                "message": f"VIX spiked {vix_change:.0f}% to {current_vix:.1f}",
                "data": {"vix": current_vix, "change_pct": round(vix_change, 1), "prev": prev_vix},
                "action": "EMERGENCY_REVIEW",
            })

        # VIX level thresholds
        if current_vix >= 30:
            alerts.append({
                "type": "VIX_EXTREME",
                "severity": "CRITICAL",
                "symbol": "^VIX",
                "message": f"VIX at extreme level: {current_vix:.1f} (fear mode)",
                "data": {"vix": current_vix, "regime": "EXTREME_FEAR"},
                "action": "RISK_REVIEW",
            })
        elif current_vix >= 20:
            alerts.append({
                "type": "VIX_ELEVATED",
                "severity": "HIGH",
                "symbol": "^VIX",
                "message": f"VIX elevated: {current_vix:.1f}",
                "data": {"vix": current_vix, "regime": "ELEVATED"},
                "action": "MONITOR",
            })

    except Exception as e:
        print(f"  [WARN] VIX check failed: {e}", file=sys.stderr)

    return alerts


# ---------------------------------------------------------------------------
# Economic Calendar
# ---------------------------------------------------------------------------

# Key recurring events (approximate — actual dates should be fetched from calendar API)
ECONOMIC_EVENTS = [
    {"name": "FOMC Decision", "frequency": "6 weeks", "impact": "CRITICAL", "agents": ["macro", "risk", "trader"]},
    {"name": "US CPI", "frequency": "monthly", "impact": "HIGH", "agents": ["macro", "quant"]},
    {"name": "US NFP (Jobs)", "frequency": "monthly (1st Friday)", "impact": "HIGH", "agents": ["macro"]},
    {"name": "US PCE", "frequency": "monthly", "impact": "HIGH", "agents": ["macro"]},
    {"name": "China PMI", "frequency": "monthly", "impact": "MEDIUM", "agents": ["macro", "sentiment"]},
    {"name": "PBoC Rate Decision", "frequency": "monthly", "impact": "HIGH", "agents": ["macro"]},
    {"name": "ECB Decision", "frequency": "6 weeks", "impact": "MEDIUM", "agents": ["macro"]},
    {"name": "BoJ Decision", "frequency": "8 weeks", "impact": "MEDIUM", "agents": ["macro"]},
    {"name": "US GDP", "frequency": "quarterly", "impact": "MEDIUM", "agents": ["macro", "quant"]},
    {"name": "Options Expiry (OPEX)", "frequency": "monthly (3rd Friday)", "impact": "MEDIUM", "agents": ["trader", "risk"]},
]


def check_calendar(days_ahead=7):
    """Check for upcoming economic events (basic keyword check via news)."""
    events = []
    today = datetime.now(timezone.utc).date()

    for event in ECONOMIC_EVENTS:
        events.append({
            "event": event["name"],
            "impact": event["impact"],
            "frequency": event["frequency"],
            "relevant_agents": event["agents"],
            "note": "Check financial calendar for exact date",
        })

    # Try to find actual earnings dates for watchlist stocks
    try:
        import yfinance as yf
        from pathlib import Path

        config_path = CONFIG_DIR / "assets.yaml"
        if config_path.exists():
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)

            earnings_upcoming = []
            for wl in config.get("watchlists", {}).values():
                for asset in wl.get("assets", []):
                    sym = asset["symbol"]
                    if sym.startswith("^") or "=F" in sym or "-USD" in sym:
                        continue
                    try:
                        ticker = yf.Ticker(sym)
                        cal = ticker.calendar
                        if cal is not None and not cal.empty:
                            for col in cal.columns:
                                val = cal[col].iloc[0] if len(cal) > 0 else None
                                if hasattr(val, "date"):
                                    earn_date = val.date()
                                    if today <= earn_date <= today + timedelta(days=days_ahead):
                                        earnings_upcoming.append({
                                            "event": f"Earnings: {sym}",
                                            "date": earn_date.isoformat(),
                                            "impact": "HIGH",
                                            "relevant_agents": ["fundamental", "trader", "sentiment"],
                                        })
                    except Exception:
                        pass

            events.extend(earnings_upcoming)
    except Exception as e:
        print(f"  [WARN] Earnings calendar check: {e}", file=sys.stderr)

    return events


# ---------------------------------------------------------------------------
# Alert Generation (for MCP integration)
# ---------------------------------------------------------------------------


def generate_alert_payload(alerts):
    """Generate structured alert payloads for MCP servers (Notion, Slack)."""
    if not alerts:
        return None

    # Sort by severity
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    alerts.sort(key=lambda a: severity_order.get(a.get("severity", "LOW"), 9))

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_alerts": len(alerts),
        "critical": sum(1 for a in alerts if a.get("severity") == "CRITICAL"),
        "high": sum(1 for a in alerts if a.get("severity") == "HIGH"),

        # Slack-formatted message
        "slack_message": _format_slack(alerts),

        # Notion page properties
        "notion_properties": {
            "title": f"Market Alert — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "severity": alerts[0]["severity"] if alerts else "LOW",
            "alert_count": len(alerts),
            "symbols_affected": list(set(a.get("symbol", "") for a in alerts)),
        },

        # Raw alerts for programmatic use
        "alerts": alerts,

        # Recommended agent team response
        "recommended_action": _recommend_action(alerts),
    }

    return payload


def _format_slack(alerts):
    """Format alerts as Slack-compatible message."""
    severity_emoji = {"CRITICAL": "🚨", "HIGH": "⚠️", "MEDIUM": "📊", "LOW": "ℹ️"}
    lines = [f"*Market Alerts* — {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}"]
    lines.append(f"_{len(alerts)} alert(s)_\n")

    for a in alerts[:10]:  # limit to 10
        emoji = severity_emoji.get(a.get("severity", "LOW"), "📌")
        lines.append(f"{emoji} *[{a.get('severity', '')}]* {a.get('message', '')}")

    return "\n".join(lines)


def _recommend_action(alerts):
    """Based on alerts, recommend which agent team configuration to launch."""
    critical = [a for a in alerts if a.get("severity") == "CRITICAL"]
    types = set(a.get("type", "") for a in alerts)

    if any(a["type"] == "VIX_SPIKE" for a in critical):
        return {
            "action": "EMERGENCY_RISK_REVIEW",
            "team": "quick_3_agent",
            "prompt": "Emergency risk review — VIX spike detected. Assess portfolio exposure, check all stop-losses, recommend hedges.",
            "agents_needed": ["macro", "risk", "trader"],
        }

    if any(a["type"] == "STOP_LOSS_BREACH" for a in alerts):
        symbols = [a["symbol"] for a in alerts if a["type"] == "STOP_LOSS_BREACH"]
        return {
            "action": "STOP_LOSS_EXECUTION",
            "team": "trader_only",
            "prompt": f"Stop-loss breached for {', '.join(symbols)}. Execute exits and reassess positions.",
            "agents_needed": ["trader", "risk"],
        }

    if "LARGE_MOVE" in types or "PRICE_GAP" in types:
        symbols = [a["symbol"] for a in alerts if a["type"] in ("LARGE_MOVE", "PRICE_GAP")]
        return {
            "action": "OPPORTUNITY_ANALYSIS",
            "team": "full_team",
            "prompt": f"Large price movement detected in {', '.join(symbols)}. Full team analysis needed.",
            "agents_needed": ["fundamental", "quant", "sentiment", "trader"],
        }

    return {
        "action": "ROUTINE_MONITORING",
        "team": "none",
        "prompt": "No urgent action needed. Continue routine monitoring.",
        "agents_needed": [],
    }


# ---------------------------------------------------------------------------
# Full Check
# ---------------------------------------------------------------------------


def run_full_check(config, symbols=None):
    """Run all event monitors and return combined alerts."""
    all_alerts = []

    # Resolve symbols
    if not symbols:
        symbols = []
        for wl in config.get("watchlists", {}).values():
            for asset in wl.get("assets", []):
                symbols.append(asset["symbol"])

    # 1. Price alerts
    print("Checking price alerts...", file=sys.stderr)
    history_file = DATA_DIR / "trade_history.jsonl"
    price_alerts = check_price_alerts(
        symbols,
        str(history_file) if history_file.exists() else None,
    )
    all_alerts.extend(price_alerts)
    print(f"  → {len(price_alerts)} price alerts", file=sys.stderr)

    # 2. Volatility
    print("Checking volatility...", file=sys.stderr)
    vol_alerts = check_volatility_alerts()
    all_alerts.extend(vol_alerts)
    print(f"  → {len(vol_alerts)} volatility alerts", file=sys.stderr)

    # 3. Generate payload
    payload = generate_alert_payload(all_alerts)

    # 4. Log alerts
    if all_alerts:
        ensure_data_dir()
        with open(ALERTS_LOG, "a", encoding="utf-8") as f:
            for alert in all_alerts:
                alert["checked_at"] = datetime.now(timezone.utc).isoformat()
                f.write(json.dumps(alert, ensure_ascii=False) + "\n")

    return payload


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Hedge Fund — Event Monitor & Auto-Trigger")
    sub = parser.add_subparsers(dest="command")

    # Check
    p_check = sub.add_parser("check", help="Run all event monitors")
    p_check.add_argument("--symbols", type=str, default=None, help="Comma-separated symbols to monitor")
    p_check.add_argument("--config", type=str, default=None, help="Path to events.yaml or assets.yaml")

    # Monitor specific symbols
    p_monitor = sub.add_parser("monitor", help="Monitor specific symbols for alerts")
    p_monitor.add_argument("--symbols", required=True, help="Comma-separated symbols")
    p_monitor.add_argument("--check-stops", action="store_true", help="Check stop-loss levels")

    # Calendar
    p_cal = sub.add_parser("calendar", help="Check upcoming economic events")
    p_cal.add_argument("--days", type=int, default=7, help="Days ahead to check")

    # Alert
    p_alert = sub.add_parser("alert", help="Generate alert payload for MCP")
    p_alert.add_argument("--event", required=True, help="Event type")
    p_alert.add_argument("--data", type=str, default="{}", help="JSON event data")

    args = parser.parse_args()

    if args.command == "check":
        config_path = args.config or str(CONFIG_DIR / "assets.yaml")
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        symbols = [s.strip() for s in args.symbols.split(",")] if args.symbols else None
        payload = run_full_check(config, symbols)
        if payload:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print("No alerts triggered.")

    elif args.command == "monitor":
        symbols = [s.strip() for s in args.symbols.split(",")]
        history_file = str(DATA_DIR / "trade_history.jsonl") if args.check_stops else None
        alerts = check_price_alerts(symbols, history_file)
        alerts.extend(check_volatility_alerts())
        if alerts:
            payload = generate_alert_payload(alerts)
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print("No alerts.")

    elif args.command == "calendar":
        events = check_calendar(args.days)
        print(json.dumps(events, indent=2, ensure_ascii=False))

    elif args.command == "alert":
        data = json.loads(args.data)
        alert = {
            "type": args.event,
            "severity": "HIGH",
            "symbol": data.get("symbol", ""),
            "message": f"Manual alert: {args.event}",
            "data": data,
            "action": "ANALYZE",
        }
        payload = generate_alert_payload([alert])
        print(json.dumps(payload, indent=2, ensure_ascii=False))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
