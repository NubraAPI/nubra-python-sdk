"""
Live-updating terminal dashboard (rich).

Uses `rich.live.Live` so the display re-renders in place each tick instead of
scrolling. Mode switches and hedge triggers are color-coded.

Each strategy gets its own bordered section (decision rationale, stats and
positions table). The kill switch is shared, so the halted banner appears once
in the top-level header.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .config import Config, StrategyConfig
from .hedger import HIGH_GAMMA_MODE, TickResult
from .nubra_client import SetupInstruments
from .positions import Book


@dataclass(frozen=True)
class StrategyView:
    """One strategy's full state for a single dashboard refresh."""

    strat_cfg: StrategyConfig
    tick: TickResult
    book: Book
    instruments: SetupInstruments


class Dashboard:
    def __init__(self, cfg: Config, session_id: str, csv_path: str):
        self.cfg = cfg
        self.session_id = session_id
        self.csv_path = csv_path
        self.recent_actions: deque[tuple[float, str, str, bool, bool]] = deque(maxlen=12)
        self.reconcile_warnings: deque[str] = deque(maxlen=5)
        self.console = Console()
        self.live = Live(console=self.console, refresh_per_second=4, screen=False, transient=False)
        self._start_time = datetime.now()

    def __enter__(self) -> "Dashboard":
        self.live.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.live.stop()

    def update(
        self,
        views: list[StrategyView],
        tick_count: int,
        reconcile_warnings: list[str] | None = None,
    ) -> None:
        for view in views:
            if view.tick.hedge_action:
                self.recent_actions.append(
                    (
                        view.tick.timestamp,
                        view.strat_cfg.name,
                        view.tick.hedge_action,
                        view.tick.hedge_fired,
                        view.tick.hedge_confirmed,
                    )
                )
        for w in reconcile_warnings or []:
            self.reconcile_warnings.append(w)

        self.live.update(self._render(views, tick_count))

    def _render(self, views: list[StrategyView], tick_count: int):
        return Group(
            self._header(views),
            *[self._strategy_section(v) for v in views],
            self._recent_actions_panel(),
            self._totals_footer(views, tick_count),
        )

    def _header(self, views: list[StrategyView]) -> Panel:
        elapsed = datetime.now() - self._start_time
        title = Text()
        title.append(" GAMMA HEDGER ", style="bold white on grey23")
        title.append(f"  {self.cfg.underlying}  {len(views)} strategy(ies)", style="bold cyan")
        title.append("   session=" + self.session_id, style="dim")
        title.append(f"   elapsed={str(elapsed).split('.')[0]}", style="dim")

        body = Text()
        orders = "ORDERS ENABLED" if self.cfg.place_orders else "DRY RUN - NO ORDERS SENT"
        body.append(f" NUBRA {self.cfg.env_name} | {orders} ", style="bold white on dark_orange3")

        halted = any(v.tick.halted for v in views)
        if halted:
            reason = next((v.tick.halted_reason for v in views if v.tick.halted_reason), "")
            body.append("\n\n")
            body.append(" !!! TRADING HALTED - KILL SWITCH ENGAGED (all strategies) !!! ", style="bold white on red")
            body.append(f"\n   Reason: {reason}", style="red")

        return Panel(body, title=title, border_style="grey70")

    def _strategy_section(self, view: StrategyView) -> Panel:
        tick, book, strat_cfg = view.tick, view.book, view.strat_cfg

        head = Table.grid(padding=(0, 2), expand=True)
        for _ in range(6):
            head.add_column(justify="left")
        spot_str = f"{tick.spot:,.2f}" if tick.spot is not None else "n/a"

        delta_str, delta_style = "n/a", "white"
        if tick.net_delta is not None:
            tolerance_units = strat_cfg.delta_tolerance_lots * book.futures.lot_size
            delta_style = "green" if abs(tick.net_delta) <= tolerance_units else "bold red"
            delta_str = f"{tick.net_delta:+,.1f} (band +/-{tolerance_units:,.1f})"

        gamma_str, gamma_style = "n/a", "white"
        if tick.net_gamma is not None:
            gamma_style = "bold yellow" if tick.mode == HIGH_GAMMA_MODE else "green"
            gamma_str = f"{tick.net_gamma:+.6f} (thr {strat_cfg.high_gamma_threshold:.6f})"

        mode_style = "bold yellow on grey23" if tick.mode == HIGH_GAMMA_MODE else "bold green on grey23"
        pnl_style = "green" if tick.total_pnl >= 0 else "red"

        head.add_row(
            Text(f"Spot {spot_str}", style="bold"),
            Text(f"Net Delta {delta_str}", style=delta_style),
            Text(f"Net Gamma {gamma_str}", style=gamma_style),
            Text(f" {tick.mode} ", style=mode_style),
            Text(f"Futures {tick.futures_lots:+d} lot(s)", style="bold"),
            Text(f"Total P&L {tick.total_pnl:+,.2f}", style=pnl_style),
        )

        # Most ticks are uneventful (delta in band, no mode change), and several
        # multi-line rationale panels can be taller than one screen. Collapse to
        # a single summary line unless something notable happened, then show the
        # full step-by-step reasoning.
        notable = (
            tick.hedge_fired
            or tick.halted
            or tick.error
            or tick.mode_changed
            or any(("BAND BREACHED" in l.upper() or "FAILED" in l.upper()) for l in tick.reasoning)
        )

        why_body = Text()
        if not tick.reasoning:
            why_body.append("(waiting for first tick...)", style="dim")
        elif notable:
            for line in tick.reasoning:
                upper = line.upper()
                style = "white"
                if "FAILED" in upper or "BAND BREACHED" in upper:
                    style = "bold red"
                elif "FINAL DECISION" in upper and ("BUY" in upper or "SELL" in upper):
                    style = "bold green"
                elif "NO TRADE" in upper or "no hedge needed" in line:
                    style = "green"
                elif "PASSED" in upper:
                    style = "yellow"
                why_body.append("- ", style="dim")
                why_body.append(line + "\n", style=style)
        else:
            why_body.append(
                f"Delta within band, Gamma -> {tick.mode}. No action needed this tick.",
                style="dim",
            )

        positions = Table(show_lines=False, expand=True, box=None, pad_edge=False)
        positions.add_column("Instrument", no_wrap=True)
        positions.add_column("Qty", justify="right", no_wrap=True)
        positions.add_column("Entry", justify="right", no_wrap=True)
        positions.add_column("Current", justify="right", no_wrap=True)
        positions.add_column("Delta", justify="right", no_wrap=True)
        positions.add_column("Gamma", justify="right", no_wrap=True)
        positions.add_column("P&L", justify="right", no_wrap=True)
        positions.add_column("Src", justify="center", no_wrap=True)

        for leg in book.legs:
            pnl = leg.pnl()
            positions.add_row(
                f"{leg.option_type} {leg.strike:,.0f}",
                f"{leg.qty_lots:+d}",
                f"{leg.entry_price_rupees:,.2f}",
                f"{leg.current_price_rupees:,.2f}",
                f"{leg.delta:+.3f}",
                f"{leg.gamma:+.5f}",
                Text(f"{pnl:+,.2f}", style="green" if pnl >= 0 else "red"),
                "api" if leg.greeks_source == "api" else "BS",
            )

        if book.futures is not None:
            fut_pnl = book.futures.total_pnl()
            positions.add_row(
                "FUT " + view.instruments.underlying,
                f"{book.futures.qty_lots:+d}",
                f"{book.futures.avg_entry_price_rupees:,.2f}" if book.futures.qty_lots else "n/a",
                f"{book.futures.current_price_rupees:,.2f}",
                "1.000",
                "0.000",
                Text(f"{fut_pnl:+,.2f}", style="green" if fut_pnl >= 0 else "red"),
                "n/a",
            )

        own_actions = self._strategy_recent_actions(strat_cfg.name)
        body = Group(head, why_body, positions, own_actions) if own_actions is not None else Group(head, why_body, positions)

        if tick.hedge_fired and tick.hedge_dry_run:
            border = "bold yellow"
            flag = " *** HEDGE SIMULATED - DRY RUN, NO ORDER SENT ***"
        elif tick.hedge_fired and tick.hedge_confirmed:
            border = "bold green"
            flag = " *** HEDGE FILLED ***"
        elif tick.hedge_fired:
            # An order went out and was not rejected, but Nubra has not
            # confirmed a fill: amber, and never claimed as FILLED.
            border = "bold yellow"
            flag = " *** HEDGE PLACED - PENDING FILL ***"
        elif tick.halted:
            border = "red"
            flag = " [HALTED]"
        elif tick.error:
            border = "red"
            flag = " [DATA ERROR]"
        else:
            border = "grey70"
            flag = ""

        title = f" {strat_cfg.name}  ({strat_cfg.strategy_type.value}, tag={strat_cfg.strat_tag}){flag} "
        return Panel(body, title=title, border_style=border)

    def _strategy_recent_actions(self, strategy_name: str, limit: int = 5) -> Text | None:
        """This strategy's own hedge-action history, scoped out of the
        shared `recent_actions` deque, so one strategy's trail can be read
        without the other strategies' actions interleaved.
        """
        own = [a for a in self.recent_actions if a[1] == strategy_name]
        if not own:
            return None
        body = Text("Recent actions (this strategy):\n", style="bold dim")
        for ts, _name, action, fired, confirmed in reversed(own[-limit:]):
            when = datetime.fromtimestamp(ts).strftime("%H:%M:%S")
            if "FAILED" in action or "ERROR" in action:
                style = "bold red"
            elif fired and confirmed:
                style = "bold green"
            elif fired:
                style = "bold yellow"
            else:
                style = "white"
            marker = "*** " if fired else "    "
            body.append(f"{when}  {marker}", style="dim")
            body.append(action + "\n", style=style)
        return body

    def _recent_actions_panel(self) -> Panel:
        body = Text()
        if not self.recent_actions and not self.reconcile_warnings:
            body.append("(no hedge actions yet)", style="dim")
        for ts, strategy_name, action, fired, confirmed in reversed(self.recent_actions):
            when = datetime.fromtimestamp(ts).strftime("%H:%M:%S")
            if "FAILED" in action or "ERROR" in action:
                style = "bold red"
            elif fired and confirmed:
                style = "bold green"
            elif fired:
                # Placed but not yet confirmed filled - amber, not green.
                style = "bold yellow"
            else:
                style = "white"
            marker = "*** " if fired else "    "
            body.append(f"{when}  [{strategy_name}]  {marker}", style="dim")
            body.append(action + "\n", style=style)
        for w in self.reconcile_warnings:
            body.append("RECONCILE  ", style="bold magenta")
            body.append(w + "\n", style="magenta")
        return Panel(body, title="Recent Hedge Actions (all strategies)", border_style="grey70")

    def _totals_footer(self, views: list[StrategyView], tick_count: int) -> Text:
        combined_pnl = sum(v.tick.total_pnl for v in views)
        pnl_style = "green" if combined_pnl >= 0 else "red"
        text = Text(f"ticks={tick_count}   ")
        text.append("combined total P&L (all strategies) ", style="bold")
        text.append(f"{combined_pnl:+,.2f}", style=pnl_style)
        text.append(f"   log: {self.csv_path}   Ctrl+C to stop", style="dim")
        return text
