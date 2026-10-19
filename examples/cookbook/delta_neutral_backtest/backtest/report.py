"""Console tables and CSV output for backtest results (no plotting, no PDF)."""
from pathlib import Path

import pandas as pd


def rupees(x: float) -> str:
    return f"{'-' if x < 0 else ''}Rs.{abs(x):,.0f}"


def print_run(r) -> None:
    print(f"  {r.label:<10} P&L={rupees(r.final_pnl):>12}  max_drawdown={rupees(r.max_drawdown):>10}  "
          f"worst={rupees(r.worst_pnl):>11}  max|net_delta|={r.max_abs_net_delta:7.1f}"
          + ("  [stop-loss hit]" if r.stopped_out else ""))
    if r.hedged:
        print(f"             futures trades={len([t for t in r.trades if 'close' not in t.reason]):3d}  "
              f"slippage={rupees(r.slippage_cost)}  fees={rupees(r.total_fees)}  "
              f"P&L before hedge cost={rupees(r.final_gross_pnl)}  hedge cost={rupees(r.hedging_cost)}")
        if r.confirmation_blocked_bars or r.cooldown_blocked_bars:
            print(f"             breach bars={r.breach_bars}  held back by confirmation={r.confirmation_blocked_bars}  "
                  f"held back by cooldown={r.cooldown_blocked_bars}")


def write_outputs(results: list, out_dir: str) -> None:
    """results: list of (ExpiryData, {'unhedged': RunResult, 'hedged': RunResult})."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows, trades, paths = [], [], []
    for data, runs in results:
        for r in runs.values():
            rows.append({"expiry": data.label, "strike": data.strike, **r.summary_row()})
            for t in r.trades:
                trades.append({"expiry": data.label, "run": r.label, "time_utc": t.time, "lots": t.lots,
                               "exec_price": t.exec_price, "mid_price": t.mid_price, "fee": t.fee,
                               "net_delta_before": round(t.net_delta_before, 2),
                               "position_after": t.position_after, "reason": t.reason})
            for i, ts in enumerate(r.times):
                paths.append({"expiry": data.label, "run": r.label, "time_utc": ts, "pnl": r.pnl_path[i],
                              "net_delta": r.net_delta_path[i], "net_gamma": r.net_gamma_path[i]})
    pd.DataFrame(rows).to_csv(out / "pnl_summary.csv", index=False)
    pd.DataFrame(trades).to_csv(out / "hedge_trades.csv", index=False)
    pd.DataFrame(paths).to_csv(out / "pnl_paths.csv", index=False)
    print(f"\nWrote pnl_summary.csv, hedge_trades.csv, pnl_paths.csv to {out}/")


def print_totals(results: list) -> None:
    for key in ("unhedged", "hedged"):
        rs = [runs[key] for _, runs in results]
        if not rs:
            continue
        pnl = [r.final_pnl for r in rs]
        print(f"  {key:<9} expiries={len(rs)}  total P&L={rupees(sum(pnl))}  "
              f"worst expiry={rupees(min(pnl))}  total premium collected={rupees(sum(r.premium_collected for r in rs))}")
