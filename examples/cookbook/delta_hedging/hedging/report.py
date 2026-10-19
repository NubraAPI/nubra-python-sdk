"""CSV, PNG and text reporting for a ``BacktestResult``. Amounts are rupees."""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import List, Union

from .backtest import BacktestResult

PathLike = Union[str, Path]


def write_hedge_log_csv(result: BacktestResult, path: PathLike) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["timestamp", "side", "qty", "price", "net_delta_before", "net_delta_after"])
        for t in result.trades:
            writer.writerow([t.timestamp, t.side, t.qty, t.price, t.net_delta_before, t.net_delta_after])


def _curve_index(result: BacktestResult, timestamp: str) -> int:
    for i, point in enumerate(result.curve):
        if point.timestamp == timestamp:
            return i
    target = datetime.fromisoformat(timestamp).timestamp()
    return min(
        range(len(result.curve)),
        key=lambda i: abs(datetime.fromisoformat(result.curve[i].timestamp).timestamp() - target),
    )


def _drawdown_series(values: List[float]) -> List[float]:
    peak, out = float("-inf"), []
    for v in values:
        peak = max(peak, v)
        out.append(v - peak)
    return out


def plot_pnl_curve(result: BacktestResult, path: PathLike) -> bool:
    """Write a PnL + drawdown chart. Returns False if matplotlib is not installed."""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib is not installed; skipping the chart (pip install matplotlib).")
        return False

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    offset = result.config.starting_capital  # chart baseline only
    x = [p.timestamp for p in result.curve]
    y = [p.total_pnl + offset for p in result.curve]

    fig, (ax_pnl, ax_dd) = plt.subplots(2, 1, figsize=(11, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    ax_pnl.plot(x, y, color="#2563eb", linewidth=1.5, label="Cumulative PnL (Rs)")
    ax_pnl.axhline(0, color="#94a3b8", linewidth=0.8)
    if result.trades:
        ax_pnl.scatter(
            [t.timestamp for t in result.trades],
            [y[_curve_index(result, t.timestamp)] for t in result.trades],
            color="#f59e0b", marker="^", s=40, zorder=3, label="Equity hedge",
        )
    if result.exit_timestamp is not None:
        i = _curve_index(result, result.exit_timestamp)
        ax_pnl.scatter([x[i]], [y[i]], color="#111827", marker="X", s=120, zorder=4, label=f"Exit: {result.exit_reason}")
    else:
        ax_pnl.text(0.99, 0.02, "No exit within the window", transform=ax_pnl.transAxes, ha="right", va="bottom", fontsize=9)
    ax_pnl.set_ylabel("PnL (Rs)")
    ax_pnl.set_title(f"Replay: {result.config.equity_symbol}")
    ax_pnl.legend(loc="upper left", fontsize=8)

    dd = _drawdown_series(y)
    ax_dd.fill_between(x, dd, 0, color="#dc2626", alpha=0.3)
    ax_dd.set_ylabel("Drawdown (Rs)")
    ax_dd.set_xlabel("Time (UTC)")
    step = max(1, len(x) // 8)
    ticks = list(range(0, len(x), step))
    ax_dd.set_xticks([x[i] for i in ticks])
    ax_dd.set_xticklabels([x[i] for i in ticks], rotation=30, ha="right", fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return True


def summarize(result: BacktestResult) -> str:
    cfg = result.config
    lines = [
        f"Replay: {cfg.equity_symbol} ({cfg.future_symbol} / {cfg.call_symbol})",
        f"Window: {cfg.start_date} -> {cfg.end_date} @ {cfg.interval} ({result.bars_used} bars used)",
        f"Entry:  {result.entry_timestamp}  underlying=Rs {result.entry_equity_price:,.2f}  "
        f"future=Rs {result.entry_future_price:,.2f}  call=Rs {result.entry_call_price:,.2f} "
        f"(delta {result.entry_call_delta:.3f})",
    ]
    if result.unresolved:
        lines.append(f"Exit:   none; window ended at {result.curve[-1].timestamp} with PnL Rs {result.final_pnl:,.2f}")
    else:
        lines.append(f"Exit:   {result.exit_timestamp}  reason={result.exit_reason}  PnL Rs {result.exit_pnl:,.2f}")
    lines.append(f"Final PnL: Rs {result.final_pnl:,.2f}")
    if cfg.starting_capital:
        lines.append(f"Final PnL incl. chart offset {cfg.starting_capital:,.2f}: Rs {result.final_pnl + cfg.starting_capital:,.2f}")
    lines.append(f"Max drawdown: Rs {result.max_drawdown:,.2f}")
    lines.append(f"Equity hedge trades: {len(result.trades)}")
    if result.target_hit is not None:
        lines.append("Exit rule fired: " + ("PnL target" if result.target_hit else "stop-loss"))
    return "\n".join(lines)
