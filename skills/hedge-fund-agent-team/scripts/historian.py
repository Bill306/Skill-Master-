#!/usr/bin/env python3
"""
Hedge Fund Agent Team — Historian Module

Tracks trade recommendations over time, measures actual P&L, and calculates
agent credibility scores based on historical accuracy.

Provides a feedback loop: agents know how accurate their past calls were,
enabling self-calibration and trust-weighted decision making.

Usage:
    # Record new recommendations from an agent team session
    python historian.py record --input /tmp/hedge-fund/trader.json

    # Review past recommendations and calculate P&L
    python historian.py review --days 30

    # Calculate agent credibility scores
    python historian.py credibility

    # Generate performance report
    python historian.py report --days 90

    # Purge old records
    python historian.py purge --older-than 365
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
DATA_DIR = SCRIPT_DIR.parent / "data"
HISTORY_FILE = DATA_DIR / "trade_history.jsonl"
CREDIBILITY_FILE = DATA_DIR / "agent_credibility.json"
REVIEW_LOG = DATA_DIR / "review_log.json"


def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Record Recommendations
# ---------------------------------------------------------------------------


def record_recommendations(input_path, session_id=None):
    """Record trade recommendations from agent outputs into history."""
    ensure_data_dir()

    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found", file=sys.stderr)
        return

    # Try to load all agent outputs from directory or single file
    recommendations = []
    input_path = Path(input_path)

    if input_path.is_dir():
        agent_files = {
            "trader": "trader.json",
            "fundamental": "fundamental.json",
            "quant": "quant.json",
            "macro": "macro.json",
            "sentiment": "sentiment.json",
            "risk": "risk.json",
            "red_team": "red_team.json",
        }
        for agent_name, filename in agent_files.items():
            filepath = input_path / filename
            if filepath.exists():
                _extract_recommendations(filepath, agent_name, recommendations)
    else:
        agent_name = input_path.stem  # e.g., "trader" from "trader.json"
        _extract_recommendations(input_path, agent_name, recommendations)

    if not session_id:
        session_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Append to JSONL history
    recorded = 0
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        for rec in recommendations:
            rec["session_id"] = session_id
            rec["recorded_at"] = datetime.now(timezone.utc).isoformat()
            rec["status"] = "OPEN"  # OPEN -> REVIEWED -> CLOSED
            rec["actual_pnl_pct"] = None
            rec["review_date"] = None
            rec["outcome"] = None  # WIN / LOSS / SCRATCH
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            recorded += 1

    print(f"Recorded {recorded} recommendations (session: {session_id})", file=sys.stderr)
    return recorded


def _extract_recommendations(filepath, agent_name, recommendations):
    """Extract structured recommendations from an agent's output file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"  [WARN] Could not read {filepath}: {e}", file=sys.stderr)
        return

    now = datetime.now(timezone.utc).isoformat()

    # Extract from trader output (trade_plan)
    if "trade_plan" in data:
        for trade in data["trade_plan"]:
            recommendations.append({
                "agent": agent_name,
                "symbol": trade.get("symbol", ""),
                "direction": trade.get("direction", ""),
                "entry_price": trade.get("entry", {}).get("price") if isinstance(trade.get("entry"), dict) else trade.get("entry"),
                "stop_loss": trade.get("stop_loss"),
                "take_profit": trade.get("take_profit"),
                "position_size_pct": trade.get("position_size_pct"),
                "confidence": trade.get("confidence", "MEDIUM"),
                "timeframe": trade.get("timeframe", "SWING"),
                "rationale": trade.get("rationale", ""),
                "timestamp": now,
            })

    # Extract from fundamental output (ratings)
    if "ratings" in data:
        for symbol, rating_data in data["ratings"].items():
            if isinstance(rating_data, dict):
                recommendations.append({
                    "agent": agent_name,
                    "symbol": symbol,
                    "direction": "LONG" if rating_data.get("rating", "").startswith("BUY") or rating_data.get("rating") == "STRONG BUY" else
                                "SHORT" if rating_data.get("rating", "").startswith("SELL") or rating_data.get("rating") == "STRONG SELL" else
                                "NEUTRAL",
                    "entry_price": rating_data.get("current_price"),
                    "stop_loss": None,
                    "take_profit": rating_data.get("fair_value"),
                    "confidence": "HIGH" if "STRONG" in rating_data.get("rating", "") else "MEDIUM",
                    "timeframe": "POSITION",
                    "rationale": rating_data.get("thesis", ""),
                    "timestamp": now,
                })

    # Extract from quant output (top_signals)
    if "top_signals" in data:
        for signal in data["top_signals"]:
            recommendations.append({
                "agent": agent_name,
                "symbol": signal.get("symbol", ""),
                "direction": "LONG" if signal.get("strength", 0) > 0 else "SHORT",
                "entry_price": None,
                "stop_loss": None,
                "take_profit": None,
                "confidence": "HIGH" if abs(signal.get("strength", 0)) > 0.7 else "MEDIUM",
                "timeframe": "SWING",
                "rationale": signal.get("signal", ""),
                "timestamp": now,
            })

    # Extract from macro output (regime)
    if "regime" in data and "asset_implications" in data:
        recommendations.append({
            "agent": agent_name,
            "symbol": "_MACRO_REGIME",
            "direction": data["regime"],
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
            "confidence": str(data.get("confidence", "MEDIUM")),
            "timeframe": "MACRO",
            "rationale": data.get("summary", "")[:500],
            "timestamp": now,
        })

    # Extract from red_team output (challenges)
    if "challenges" in data:
        for challenge in data["challenges"]:
            recommendations.append({
                "agent": "red_team",
                "symbol": challenge.get("symbol", ""),
                "direction": "COUNTER_" + challenge.get("original_direction", ""),
                "entry_price": None,
                "stop_loss": None,
                "take_profit": None,
                "confidence": challenge.get("conviction", "MEDIUM"),
                "timeframe": "REVIEW",
                "rationale": challenge.get("bear_case", ""),
                "timestamp": now,
            })


# ---------------------------------------------------------------------------
# Review Past Recommendations
# ---------------------------------------------------------------------------


def review_recommendations(days=30):
    """Review open recommendations and calculate actual P&L."""
    try:
        import yfinance as yf
    except ImportError:
        print("Error: yfinance required for P&L calculation", file=sys.stderr)
        return

    if not HISTORY_FILE.exists():
        print("No history found. Run 'record' first.", file=sys.stderr)
        return

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    records = _load_history()
    updated = []
    reviewed_count = 0

    # Group by symbol to batch price lookups
    symbols_needed = set()
    for rec in records:
        if rec["status"] == "OPEN" and rec.get("entry_price") and rec.get("symbol", "").startswith("_") is False:
            symbols_needed.add(rec["symbol"])

    # Fetch current prices
    current_prices = {}
    for sym in symbols_needed:
        try:
            ticker = yf.Ticker(sym)
            info = ticker.info
            price = info.get("currentPrice", info.get("regularMarketPrice"))
            if price:
                current_prices[sym] = float(price)
        except Exception:
            pass

    print(f"Fetched prices for {len(current_prices)}/{len(symbols_needed)} symbols", file=sys.stderr)

    for rec in records:
        if rec["status"] != "OPEN":
            updated.append(rec)
            continue

        entry = rec.get("entry_price")
        symbol = rec.get("symbol", "")
        direction = rec.get("direction", "")

        if not entry or symbol.startswith("_") or symbol not in current_prices:
            updated.append(rec)
            continue

        current = current_prices[symbol]
        entry = float(entry)

        # Calculate P&L
        if direction == "LONG":
            pnl_pct = (current / entry - 1) * 100
        elif direction == "SHORT":
            pnl_pct = (1 - current / entry) * 100
        else:
            updated.append(rec)
            continue

        rec["actual_pnl_pct"] = round(pnl_pct, 2)
        rec["current_price"] = current
        rec["review_date"] = datetime.now(timezone.utc).isoformat()

        # Check if stop-loss or take-profit hit
        stop = rec.get("stop_loss")
        tp = rec.get("take_profit")
        tp_targets = tp if isinstance(tp, list) else [tp] if tp else []

        if stop and direction == "LONG" and current <= float(stop):
            rec["status"] = "CLOSED"
            rec["outcome"] = "LOSS"
            rec["close_reason"] = "STOP_LOSS_HIT"
        elif stop and direction == "SHORT" and current >= float(stop):
            rec["status"] = "CLOSED"
            rec["outcome"] = "LOSS"
            rec["close_reason"] = "STOP_LOSS_HIT"
        elif tp_targets and direction == "LONG" and current >= float(tp_targets[0]):
            rec["status"] = "CLOSED"
            rec["outcome"] = "WIN"
            rec["close_reason"] = "TAKE_PROFIT_HIT"
        elif tp_targets and direction == "SHORT" and current <= float(tp_targets[0]):
            rec["status"] = "CLOSED"
            rec["outcome"] = "WIN"
            rec["close_reason"] = "TAKE_PROFIT_HIT"
        else:
            rec["status"] = "REVIEWED"
            if pnl_pct > 1:
                rec["outcome"] = "WIN"
            elif pnl_pct < -1:
                rec["outcome"] = "LOSS"
            else:
                rec["outcome"] = "SCRATCH"

        reviewed_count += 1
        updated.append(rec)

    # Rewrite history file
    _save_history(updated)
    print(f"Reviewed {reviewed_count} recommendations", file=sys.stderr)

    # Print summary
    wins = sum(1 for r in updated if r.get("outcome") == "WIN")
    losses = sum(1 for r in updated if r.get("outcome") == "LOSS")
    scratches = sum(1 for r in updated if r.get("outcome") == "SCRATCH")
    total_reviewed = wins + losses + scratches
    win_rate = wins / total_reviewed * 100 if total_reviewed > 0 else 0

    summary = {
        "review_date": datetime.now(timezone.utc).isoformat(),
        "period_days": days,
        "total_records": len(updated),
        "reviewed": reviewed_count,
        "wins": wins,
        "losses": losses,
        "scratches": scratches,
        "win_rate_pct": round(win_rate, 1),
    }

    print(json.dumps(summary, indent=2))
    return summary


# ---------------------------------------------------------------------------
# Agent Credibility Scores
# ---------------------------------------------------------------------------


def calculate_credibility():
    """Calculate credibility scores for each agent based on history."""
    if not HISTORY_FILE.exists():
        print("No history found.", file=sys.stderr)
        return

    records = _load_history()
    agent_stats = {}

    for rec in records:
        agent = rec.get("agent", "unknown")
        outcome = rec.get("outcome")
        pnl = rec.get("actual_pnl_pct")

        if agent not in agent_stats:
            agent_stats[agent] = {
                "total_calls": 0,
                "reviewed_calls": 0,
                "wins": 0,
                "losses": 0,
                "scratches": 0,
                "total_pnl_pct": 0.0,
                "high_confidence_wins": 0,
                "high_confidence_total": 0,
                "pnl_history": [],
            }

        agent_stats[agent]["total_calls"] += 1

        if outcome:
            agent_stats[agent]["reviewed_calls"] += 1
            if outcome == "WIN":
                agent_stats[agent]["wins"] += 1
            elif outcome == "LOSS":
                agent_stats[agent]["losses"] += 1
            else:
                agent_stats[agent]["scratches"] += 1

        if pnl is not None:
            agent_stats[agent]["total_pnl_pct"] += pnl
            agent_stats[agent]["pnl_history"].append(pnl)

        if rec.get("confidence") == "HIGH":
            agent_stats[agent]["high_confidence_total"] += 1
            if outcome == "WIN":
                agent_stats[agent]["high_confidence_wins"] += 1

    # Calculate credibility scores
    credibility = {}
    for agent, stats in agent_stats.items():
        reviewed = stats["reviewed_calls"]
        if reviewed == 0:
            score = 50.0  # default neutral
        else:
            win_rate = stats["wins"] / reviewed
            # Bayesian-adjusted: pull toward 50% with small samples
            # Score = (wins + 2) / (reviewed + 4) — Laplace smoothing
            adj_win_rate = (stats["wins"] + 2) / (reviewed + 4)

            # Bonus for high-confidence accuracy
            hc_total = stats["high_confidence_total"]
            hc_bonus = 0
            if hc_total >= 3:
                hc_rate = stats["high_confidence_wins"] / hc_total
                hc_bonus = (hc_rate - 0.5) * 10  # -5 to +5 bonus

            # P&L factor
            avg_pnl = stats["total_pnl_pct"] / reviewed
            pnl_factor = min(max(avg_pnl / 5, -10), 10)  # clamp

            score = adj_win_rate * 100 + hc_bonus + pnl_factor
            score = min(max(score, 0), 100)

        credibility[agent] = {
            "score": round(score, 1),
            "rating": "EXCELLENT" if score >= 75 else
                      "GOOD" if score >= 60 else
                      "AVERAGE" if score >= 45 else
                      "BELOW_AVERAGE" if score >= 30 else
                      "POOR",
            "total_calls": stats["total_calls"],
            "reviewed_calls": reviewed,
            "win_rate_pct": round(stats["wins"] / reviewed * 100, 1) if reviewed > 0 else None,
            "avg_pnl_pct": round(stats["total_pnl_pct"] / reviewed, 2) if reviewed > 0 else None,
            "high_confidence_accuracy": round(stats["high_confidence_wins"] / stats["high_confidence_total"] * 100, 1) if stats["high_confidence_total"] > 0 else None,
            "sample_size": "SUFFICIENT" if reviewed >= 10 else "LIMITED" if reviewed >= 5 else "INSUFFICIENT",
        }

    # Save credibility file
    ensure_data_dir()
    output = {
        "calculated_at": datetime.now(timezone.utc).isoformat(),
        "agents": credibility,
        "note": "Scores use Laplace smoothing — small samples pull toward 50%. Scores become more reliable after 10+ reviewed calls.",
    }

    with open(CREDIBILITY_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(json.dumps(output, indent=2, ensure_ascii=False))
    return output


# ---------------------------------------------------------------------------
# Performance Report
# ---------------------------------------------------------------------------


def generate_report(days=90):
    """Generate a comprehensive performance report."""
    if not HISTORY_FILE.exists():
        print("No history found.", file=sys.stderr)
        return

    records = _load_history()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Filter to period
    period_records = []
    for r in records:
        try:
            ts = datetime.fromisoformat(r["timestamp"])
            if ts >= cutoff:
                period_records.append(r)
        except (KeyError, ValueError):
            period_records.append(r)

    if not period_records:
        print("No records in the specified period.", file=sys.stderr)
        return

    # Aggregate stats
    by_agent = {}
    by_symbol = {}
    by_direction = {"LONG": [], "SHORT": []}
    by_confidence = {"HIGH": [], "MEDIUM": [], "LOW": []}
    by_session = {}

    for r in period_records:
        agent = r.get("agent", "unknown")
        symbol = r.get("symbol", "unknown")
        direction = r.get("direction", "")
        confidence = r.get("confidence", "MEDIUM")
        session = r.get("session_id", "unknown")
        pnl = r.get("actual_pnl_pct")

        for group, key, val in [
            (by_agent, agent, r),
            (by_symbol, symbol, r),
            (by_session, session, r),
        ]:
            if key not in group:
                group[key] = []
            group[key].append(r)

        if direction in by_direction and pnl is not None:
            by_direction[direction].append(pnl)
        if confidence in by_confidence and pnl is not None:
            by_confidence[confidence].append(pnl)

    def _stats(records_list):
        reviewed = [r for r in records_list if r.get("outcome")]
        pnls = [r["actual_pnl_pct"] for r in reviewed if r.get("actual_pnl_pct") is not None]
        wins = sum(1 for r in reviewed if r.get("outcome") == "WIN")
        return {
            "total": len(records_list),
            "reviewed": len(reviewed),
            "wins": wins,
            "losses": sum(1 for r in reviewed if r.get("outcome") == "LOSS"),
            "win_rate": round(wins / len(reviewed) * 100, 1) if reviewed else None,
            "avg_pnl": round(sum(pnls) / len(pnls), 2) if pnls else None,
            "best_trade": round(max(pnls), 2) if pnls else None,
            "worst_trade": round(min(pnls), 2) if pnls else None,
        }

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period_days": days,
        "total_recommendations": len(period_records),
        "sessions": len(by_session),
        "overall": _stats(period_records),
        "by_agent": {k: _stats(v) for k, v in by_agent.items()},
        "by_symbol": {k: _stats(v) for k, v in sorted(by_symbol.items(), key=lambda x: len(x[1]), reverse=True)[:10]},
        "by_direction": {
            k: {"count": len(v), "avg_pnl": round(sum(v) / len(v), 2) if v else None}
            for k, v in by_direction.items()
        },
        "by_confidence": {
            k: {"count": len(v), "avg_pnl": round(sum(v) / len(v), 2) if v else None}
            for k, v in by_confidence.items()
        },
    }

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_history():
    """Load all records from JSONL history file."""
    records = []
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    return records


def _save_history(records):
    """Overwrite history file with updated records."""
    ensure_data_dir()
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def purge_old(older_than_days):
    """Remove records older than N days."""
    records = _load_history()
    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    kept = []
    purged = 0
    for r in records:
        try:
            ts = datetime.fromisoformat(r["timestamp"])
            if ts >= cutoff:
                kept.append(r)
            else:
                purged += 1
        except (KeyError, ValueError):
            kept.append(r)

    _save_history(kept)
    print(f"Purged {purged} records older than {older_than_days} days. {len(kept)} remaining.", file=sys.stderr)


def get_context_for_agents():
    """Generate a context summary that agents can use to calibrate their analysis.

    Call this at team startup and inject into agent spawn prompts.
    """
    output = {
        "has_history": HISTORY_FILE.exists(),
        "credibility": None,
        "recent_performance": None,
    }

    if CREDIBILITY_FILE.exists():
        with open(CREDIBILITY_FILE, "r", encoding="utf-8") as f:
            output["credibility"] = json.load(f)

    if HISTORY_FILE.exists():
        records = _load_history()
        recent = [r for r in records if r.get("outcome")][-20:]  # last 20 reviewed
        if recent:
            wins = sum(1 for r in recent if r["outcome"] == "WIN")
            output["recent_performance"] = {
                "last_n": len(recent),
                "win_rate": round(wins / len(recent) * 100, 1),
                "recent_calls": [
                    {
                        "agent": r.get("agent"),
                        "symbol": r.get("symbol"),
                        "direction": r.get("direction"),
                        "outcome": r.get("outcome"),
                        "pnl_pct": r.get("actual_pnl_pct"),
                    }
                    for r in recent[-5:]
                ],
            }

    return output


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Hedge Fund — Trade History & Agent Credibility")
    sub = parser.add_subparsers(dest="command")

    # Record
    p_record = sub.add_parser("record", help="Record recommendations from agent outputs")
    p_record.add_argument("--input", required=True, help="Path to agent output file or /tmp/hedge-fund/ dir")
    p_record.add_argument("--session-id", default=None, help="Session identifier")

    # Review
    p_review = sub.add_parser("review", help="Review open recommendations and calculate P&L")
    p_review.add_argument("--days", type=int, default=30, help="Review period in days")

    # Credibility
    sub.add_parser("credibility", help="Calculate agent credibility scores")

    # Report
    p_report = sub.add_parser("report", help="Generate performance report")
    p_report.add_argument("--days", type=int, default=90, help="Report period in days")

    # Context
    sub.add_parser("context", help="Generate context for agent spawn prompts")

    # Purge
    p_purge = sub.add_parser("purge", help="Purge old records")
    p_purge.add_argument("--older-than", type=int, required=True, help="Days threshold")

    args = parser.parse_args()

    if args.command == "record":
        record_recommendations(args.input, args.session_id)
    elif args.command == "review":
        review_recommendations(args.days)
    elif args.command == "credibility":
        calculate_credibility()
    elif args.command == "report":
        generate_report(args.days)
    elif args.command == "context":
        ctx = get_context_for_agents()
        print(json.dumps(ctx, indent=2, ensure_ascii=False))
    elif args.command == "purge":
        purge_old(args.older_than)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
