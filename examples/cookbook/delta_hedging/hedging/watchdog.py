"""Account-wide loss watchdog, separate from the hedge runner's own PnL limits.

Polls ``NubraPortfolio`` (positions and funds) and, on a confirmed breach of the
account-wide loss limit or intraday drawdown limit, flattens every open
position on the account through the ``OrderGate`` (``exit_all_positions`` with
market orders). Without ``--place-orders`` it only reports what it would flatten.
It stops after a breach: a human should look before anything trades again.
Amounts are rupees.
"""
from __future__ import annotations

import glob
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .orders import OrderGate
from .session import rupees
from .state import DEFAULT_STATE_DIR, STATUS_OPEN, PositionState


@dataclass(frozen=True)
class WatchConfig:
    max_daily_loss: float  # zero or negative rupee account PnL at which to flatten
    max_drawdown_pct: Optional[float] = None  # percent drawdown from the day's peak equity
    poll_seconds: float = 10.0
    state_dir: Path = DEFAULT_STATE_DIR

    def validate(self) -> None:
        if self.max_daily_loss > 0:
            raise SystemExit(f"--max-daily-loss must be zero or negative (for example -15000), got {self.max_daily_loss}")
        if self.max_drawdown_pct is not None and self.max_drawdown_pct <= 0:
            raise SystemExit("--max-drawdown-pct must be positive when set")


def compute_drawdown_pct(peak_equity: float, current_equity: float) -> float:
    if peak_equity <= 0:
        return 0.0
    return (peak_equity - current_equity) / peak_equity * 100.0


class PeakEquityTracker:
    """Day's peak equity, kept in a small JSON file so a restart keeps the real peak."""

    def __init__(self, path: Path, trading_date: str) -> None:
        self._path, self._date = Path(path), trading_date
        self._peak: Optional[float] = None
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if data.get("trading_date") == trading_date and data.get("peak_equity") is not None:
                self._peak = float(data["peak_equity"])
        except (OSError, ValueError):
            pass

    def update(self, equity: float) -> float:
        if self._peak is None or equity > self._peak:
            self._peak = equity
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps({"trading_date": self._date, "peak_equity": equity}), encoding="utf-8")
        return self._peak


def _tracked_refs(state_dir: Path) -> Dict[int, str]:
    tracked: Dict[int, str] = {}
    for path in glob.glob(str(Path(state_dir) / "hedge_state_*.json")):
        try:
            state = PositionState.load(Path(path))
        except (OSError, ValueError):
            continue
        if state is None or state.status != STATUS_OPEN:
            continue
        for ref_id in (state.future_ref_id, *state.call_ref_ids, state.equity_ref_id):
            if ref_id is not None:
                tracked[ref_id] = state.symbol
    return tracked


class Watchdog:
    def __init__(self, nubra, cfg: WatchConfig, gate: OrderGate) -> None:
        from nubra_python_sdk.portfolio.portfolio_data import NubraPortfolio

        self.portfolio = NubraPortfolio(nubra)
        self.cfg = cfg
        self.gate = gate

    def open_positions(self) -> list:
        result = self.portfolio.positions()
        rows = result.portfolio.positions if result and result.portfolio else []
        return [p for p in rows or [] if p.netQuantity and p.status == "OPEN"]

    def account_pnl(self) -> Dict[str, float]:
        """Two independent PnL readings; the worse one is used for the limit check."""
        result = self.portfolio.positions()
        rows = result.portfolio.positions if result and result.portfolio else []
        positions_pnl = sum(rupees(p.pnl) for p in rows or [])
        funds = self.portfolio.funds().portFundsAndMargin
        funds_mtm = rupees((funds.mtmDeriv or 0) + (funds.mtmEqDelivery or 0) + (funds.mtmEqIdayCnc or 0))
        return {"positions": positions_pnl, "funds_mtm": funds_mtm, "account": min(positions_pnl, funds_mtm)}

    def account_equity(self) -> float:
        f = self.portfolio.funds().portFundsAndMargin
        mtm = (f.mtmDeriv or 0) + (f.mtmEqDelivery or 0) + (f.mtmEqIdayCnc or 0)
        return rupees((f.startOfDayFunds or 0) + mtm)

    def run(self, max_cycles: Optional[int] = None) -> None:
        cfg = self.cfg
        tracker = PeakEquityTracker(cfg.state_dir / "watch_peak_equity.json", time.strftime("%Y-%m-%d"))
        print(
            f"Watchdog ({self.gate.mode}): max daily loss Rs {cfg.max_daily_loss:,.2f}, "
            f"max drawdown {cfg.max_drawdown_pct if cfg.max_drawdown_pct is not None else 'off'}%, "
            f"poll {cfg.poll_seconds}s"
        )
        cycles = 0
        while True:
            cycles += 1
            try:
                pnl = self.account_pnl()
                drawdown: Optional[float] = None
                if cfg.max_drawdown_pct is not None:
                    equity = self.account_equity()
                    drawdown = compute_drawdown_pct(tracker.update(equity), equity)
            except Exception as err:
                print(f"Transient error fetching positions/funds ({err}); retrying next cycle.")
                time.sleep(cfg.poll_seconds)
                continue

            dd_text = "off" if drawdown is None else f"{drawdown:.2f}%"
            print(
                f"[{time.strftime('%H:%M:%S')}] account PnL Rs {pnl['account']:,.2f} "
                f"(positions {pnl['positions']:,.2f}, funds MTM {pnl['funds_mtm']:,.2f}) | drawdown {dd_text}"
            )

            reason: Optional[str] = None
            if pnl["account"] <= cfg.max_daily_loss:
                reason = f"account PnL {pnl['account']:.2f} reached max daily loss {cfg.max_daily_loss:.2f}"
            elif drawdown is not None and cfg.max_drawdown_pct is not None and drawdown >= cfg.max_drawdown_pct:
                reason = f"drawdown {drawdown:.2f}% reached limit {cfg.max_drawdown_pct:.2f}%"

            if reason is None:
                if max_cycles is not None and cycles >= max_cycles:
                    print("Reached --max-cycles; stopping.")
                    return
                time.sleep(cfg.poll_seconds)
                continue

            positions = self.open_positions()
            tracked = _tracked_refs(cfg.state_dir)
            print(f"LIMIT REACHED: {reason}. Open positions: {len(positions)}")
            for p in positions:
                owner = tracked.get(p.refId)
                print(f"  {p.symbol:<26} net qty {p.netQuantity:>8} PnL Rs {rupees(p.pnl):>12,.2f}"
                      + (f"  (hedge: {owner})" if owner else ""))
            self.gate.flatten_all(reason)
            print("Watchdog stopping after the limit was reached; review before restarting anything.")
            return
