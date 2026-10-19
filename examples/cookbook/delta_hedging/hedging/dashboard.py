"""Live terminal dashboard: positions, per-position Greeks and net book Greeks.

Read-only. Polls ``NubraPortfolio.positions()`` / ``funds()`` on a fixed
interval and fetches Greeks for option positions from the option chain
(``MarketData.option_chain``), then redraws in place with ``rich``. Futures and
cash equity rows count as delta 1.0 per unit so the net delta is the whole
book's delta in shares. Amounts are rupees.
"""
from __future__ import annotations

import glob
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .session import rupees
from .state import DEFAULT_STATE_DIR, STATUS_CLOSED, PositionState


def _fmt(value: Optional[float], decimals: int = 2) -> str:
    return "-" if value is None else f"{value:,.{decimals}f}"


@dataclass
class Greeks:
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None


@dataclass
class Row:
    ref_id: Optional[int]
    symbol: str
    exchange: str
    asset: str
    kind: str  # OPT / FUT / STOCK
    net_qty: float
    ltp: float
    avg_price: float
    pnl: float
    pnl_chg: float
    greeks: Greeks = field(default_factory=Greeks)
    hedge_state: Optional[PositionState] = None


def load_hedge_states(state_dir: Path = DEFAULT_STATE_DIR) -> Dict[int, PositionState]:
    """Map each ref_id of every non-closed saved hedge to its state."""
    mapping: Dict[int, PositionState] = {}
    for path in glob.glob(str(Path(state_dir) / "hedge_state_*.json")):
        try:
            state = PositionState.load(Path(path))
        except (OSError, ValueError):
            continue
        if state is None or state.status == STATUS_CLOSED:
            continue
        for ref_id in (state.future_ref_id, *state.call_ref_ids, state.equity_ref_id):
            if ref_id is not None:
                mapping[ref_id] = state
    return mapping


class Dashboard:
    def __init__(self, nubra, state_dir: Path = DEFAULT_STATE_DIR) -> None:
        from nubra_python_sdk.marketdata.market_data import MarketData
        from nubra_python_sdk.portfolio.portfolio_data import NubraPortfolio
        from nubra_python_sdk.refdata.instruments import InstrumentData

        self.market_data = MarketData(nubra)
        self.portfolio = NubraPortfolio(nubra)
        self.instruments = InstrumentData(nubra)
        self.state_dir = Path(state_dir)

    def _chain_greeks(self, keys: set) -> Dict[Tuple[str, str, str], Dict[int, Greeks]]:
        """One option-chain call per (asset, exchange, expiry) covers every strike."""
        out: Dict[Tuple[str, str, str], Dict[int, Greeks]] = {}
        for asset, exchange, expiry in keys:
            try:
                result = self.market_data.option_chain(asset, expiry=expiry, exchange=exchange)
            except Exception:
                continue
            if result is None:
                continue
            out[(asset, exchange, expiry)] = {
                o.ref_id: Greeks(o.delta, o.gamma, o.theta, o.vega)
                for o in (*result.chain.ce, *result.chain.pe)
            }
        return out

    def _rows(self, positions, hedge_by_ref: Dict[int, PositionState]) -> List[Row]:
        meta = {}
        keys = set()
        for p in positions:
            if (p.derivativeType or "").upper() == "OPT" and p.refId is not None:
                info = self.instruments.get_instrument_by_ref_id(p.refId)
                if info is not None and not isinstance(info, dict) and info.expiry:
                    meta[p.refId] = (p.asset, p.exchange, str(info.expiry))
                    keys.add(meta[p.refId])
        chain_greeks = self._chain_greeks(keys)

        rows: List[Row] = []
        for p in positions:
            kind = (p.derivativeType or "").upper()
            greeks = Greeks()
            if kind in ("FUT", "STOCK"):
                greeks = Greeks(delta=1.0)  # one unit of future or share = delta 1.0
            elif p.refId in meta:
                greeks = chain_greeks.get(meta[p.refId], {}).get(p.refId, Greeks())
            rows.append(
                Row(
                    ref_id=p.refId,
                    symbol=p.symbol,
                    exchange=p.exchange,
                    asset=p.asset,
                    kind=kind or "-",
                    net_qty=p.netQuantity or 0,
                    ltp=rupees(p.lastTradedPrice),
                    avg_price=rupees(p.avgPrice),
                    pnl=rupees(p.pnl),
                    pnl_chg=p.pnlChg or 0.0,
                    greeks=greeks,
                    hedge_state=hedge_by_ref.get(p.refId) if p.refId is not None else None,
                )
            )
        rows.sort(key=lambda r: (r.asset, r.symbol))
        return rows

    @staticmethod
    def _greek_cell(value: Optional[float], decimals: int = 4) -> Text:
        if value is None:
            return Text("-", style="dim")
        return Text(f"{value:.{decimals}f}", style="green" if value >= 0 else "red")

    def _table(self, rows: List[Row]) -> Table:
        table = Table(title="Positions", expand=True)
        for name, right in [("Symbol", False), ("Exch", False), ("Type", False), ("Net Qty", True), ("LTP", True),
                            ("Avg Px", True), ("Delta", True), ("Gamma", True), ("Theta", True), ("Vega", True),
                            ("PnL", True), ("PnL %", True), ("Hedge", False)]:
            table.add_column(name, justify="right" if right else "left")
        if not rows:
            table.add_row(*(["-"] * 13))
            return table
        last_asset = None
        for r in rows:
            if last_asset is not None and r.asset != last_asset:
                table.add_section()
            last_asset = r.asset
            style = "green" if r.pnl >= 0 else "red"
            tag = "-"
            if r.hedge_state is not None:
                tag = f"yes {len(r.hedge_state.hedge_trades)} hedges @ {_fmt(r.hedge_state.last_hedge_underlying_price, 0)}"
            table.add_row(
                r.symbol, r.exchange, r.kind, f"{r.net_qty:,.0f}", _fmt(r.ltp), _fmt(r.avg_price),
                self._greek_cell(r.greeks.delta), self._greek_cell(r.greeks.gamma, 6),
                self._greek_cell(r.greeks.theta), self._greek_cell(r.greeks.vega),
                Text(_fmt(r.pnl), style=style), Text(f"{_fmt(r.pnl_chg)}%", style=style), tag,
            )
        return table

    @staticmethod
    def _net(rows: List[Row], attr: str) -> float:
        return sum(getattr(r.greeks, attr) * r.net_qty for r in rows if getattr(r.greeks, attr) is not None)

    def _summary(self, rows: List[Row], stats, funds) -> Panel:
        total = rupees(stats.totalPnl) if stats and stats.totalPnl is not None else sum(r.pnl for r in rows)
        style = "green" if total >= 0 else "red"
        pnl_text = f"[{style}]{_fmt(total)}[/{style}]"
        if stats and stats.totalPnlChg is not None:
            pnl_text += f" ({stats.totalPnlChg:.2f}%)"
        grid = Table.grid(padding=(0, 4), expand=True)
        for _ in range(4):
            grid.add_column(justify="left")
        grid.add_row(
            f"[bold]NET DELTA[/bold] {self._net(rows, 'delta'):,.2f}",
            f"[bold]NET GAMMA[/bold] {self._net(rows, 'gamma'):,.6f}",
            f"[bold]NET THETA[/bold] {self._net(rows, 'theta'):,.2f}",
            f"[bold]NET VEGA[/bold] {self._net(rows, 'vega'):,.2f}",
        )
        grid.add_row(
            f"[bold]TOTAL PNL[/bold] {pnl_text}",
            f"[bold]AVAILABLE MARGIN[/bold] {_fmt(rupees(funds.netMarginAvailable) if funds else None)}",
            f"[bold]OPEN POSITIONS[/bold] {len(rows)}",
            f"[bold]HEDGED POSITIONS[/bold] {sum(1 for r in rows if r.hedge_state is not None)}",
        )
        return Panel(grid, title="Net book Greeks (in shares)", border_style="cyan")

    def build_view(self) -> RenderableType:
        result = self.portfolio.positions()
        pf = result.portfolio if result else None
        open_positions = [p for p in (pf.positions if pf else []) or [] if (p.netQuantity or 0) != 0]
        funds_result = self.portfolio.funds()
        funds = funds_result.portFundsAndMargin if funds_result else None
        rows = self._rows(open_positions, load_hedge_states(self.state_dir))
        return Group(self._summary(rows, pf.positionStats if pf else None, funds), self._table(rows))

    def run(self, refresh_seconds: float = 4.0, once: bool = False) -> None:
        console = Console()
        if once:
            console.print(self.build_view())
            return
        try:
            with Live(console=console, refresh_per_second=4) as live:
                while True:
                    try:
                        view = self.build_view()
                    except Exception as err:
                        view = Panel(Text(f"Refresh failed: {err}", style="red"), title="Summary", border_style="red")
                    live.update(view)
                    time.sleep(refresh_seconds)
        except KeyboardInterrupt:
            console.print("\n[dim]Dashboard stopped.[/dim]")
