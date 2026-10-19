"""Hedge runner: enter long future + short ATM calls, re-hedge with the cash equity, exit on PnL limits.

Flow: resolve the legs with the SDK, enter the structure as one multi-leg
order, stream the equity price and call Greeks over the SDK websocket, and
every poll cycle recompute net delta once the underlying has moved past the
trigger since the last hedge. The decisions come from ``hedging.logic``.

Dry-run (the default) keeps a paper position in memory and prints the orders it
would send. ``--place-orders`` sends them through ``OrderGate``.
"""
from __future__ import annotations

import re
import threading
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import logic
from .market import HedgeLegs, last_price, resolve_legs
from .orders import OrderGate
from .session import rupees
from .state import (
    DEFAULT_STATE_DIR,
    STATUS_CLOSED,
    STATUS_EXITING,
    STATUS_OPEN,
    PositionState,
    state_file_path,
)

FALLBACK_ATM_DELTA = 0.5
"""Used only if a hedge check fires before any live delta tick has arrived."""


@dataclass(frozen=True)
class HedgeConfig:
    symbol: str
    pnl_target: float
    pnl_stop_loss: float
    exchange: str = "NSE"
    expiry: Optional[str] = None
    num_short_calls: int = 2
    future_lots: int = 1
    hedge_trigger_pct: float = 1.5
    poll_seconds: float = 5.0
    hedge_delivery_type: str = "CNC"  # CNC or IDAY, for the equity hedge orders
    state_dir: Path = DEFAULT_STATE_DIR

    def validate(self) -> None:
        if self.pnl_target <= 0:
            raise SystemExit(f"--pnl-target must be positive, got {self.pnl_target}")
        if self.pnl_stop_loss > 0:
            raise SystemExit(
                f"--pnl-stop-loss must be zero or negative (for example -3000), got {self.pnl_stop_loss}"
            )
        if self.num_short_calls < 1 or self.future_lots < 1:
            raise SystemExit("--short-calls and --future-lots must be at least 1")


def strat_tag(symbol: str) -> str:
    """One tag per order, hyphens only."""
    slug = re.sub(r"[^a-z0-9]+", "-", symbol.lower()).strip("-")
    return f"delta-hedge-{slug}"[:64]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class HedgeRunner:
    def __init__(self, nubra, cfg: HedgeConfig, gate: OrderGate) -> None:
        from nubra_python_sdk.marketdata.market_data import MarketData
        from nubra_python_sdk.portfolio.portfolio_data import NubraPortfolio
        from nubra_python_sdk.refdata.instruments import InstrumentData

        self.nubra = nubra
        self.cfg = cfg
        self.gate = gate
        self.instruments = InstrumentData(nubra)
        self.market_data = MarketData(nubra)
        self.portfolio = NubraPortfolio(nubra)
        self.state_path = state_file_path(cfg.symbol, cfg.state_dir)
        self.state: Optional[PositionState] = None

        self._lock = threading.Lock()
        self._ltp: Dict[int, Tuple[float, float]] = {}  # ref_id -> (rupees, monotonic time)
        self._delta: Dict[int, float] = {}

    # ---- persistence (live runs only) -------------------------------------------------
    def _save(self) -> None:
        if self.gate.live and self.state is not None:
            self.state.save(self.state_path)

    # ---- websocket callbacks (run on the SDK's socket thread) --------------------------
    def _on_orderbook(self, msg) -> None:
        ltp = getattr(msg, "last_traded_price", None)
        if getattr(msg, "ref_id", None) and ltp:
            with self._lock:
                self._ltp[msg.ref_id] = (ltp / 100.0, time.monotonic())

    def _on_greeks(self, msg) -> None:
        ref_id = getattr(msg, "ref_id", None)
        if not ref_id:
            return
        with self._lock:
            if getattr(msg, "delta", None) is not None:
                self._delta[ref_id] = msg.delta
            ltp = getattr(msg, "last_traded_price", None)
            if ltp:
                self._ltp[ref_id] = (ltp / 100.0, time.monotonic())

    def _price(self, ref_id: Optional[int]) -> Optional[float]:
        """Latest streamed price in rupees, falling back to a REST quote when stale."""
        if ref_id is None:
            return None
        with self._lock:
            hit = self._ltp.get(ref_id)
        if hit and time.monotonic() - hit[1] <= max(3 * self.cfg.poll_seconds, 10):
            return hit[0]
        return last_price(self.market_data, ref_id)

    # ---- entry ---------------------------------------------------------------------------
    def _entry_order(self, legs: HedgeLegs) -> dict:
        return {
            "isMultiLeg": True,
            "qty": legs.lot_size,  # one strategy unit; leg direction comes from unitQty
            "side": "BUY",  # strategy side is always BUY; sign of unitQty sets each leg
            "deliveryType": "CNC",
            "priceType": "MARKET",
            "validityType": "IOC",
            "executionMode": "ENTRY",
            "legs": [
                {"refId": legs.future_ref_id, "unitQty": self.cfg.future_lots},
                {"refId": legs.call_ref_id, "unitQty": -self.cfg.num_short_calls},
            ],
            "stratTags": [strat_tag(self.cfg.symbol)],
        }

    def _margin_precheck(self, order: dict) -> bool:
        """Print funds required vs available. Returns False if funds are short."""
        try:
            funds = self.gate.trader.get_margin({"requestType": "NEW", "orders": [order]})
            required = funds.totalFundsRequired or 0
            available = self.portfolio.funds().portFundsAndMargin.netMarginAvailable or 0
        except Exception as err:  # margin check is advisory in dry-run
            print(f"Margin check unavailable: {err}")
            return True
        print(f"Funds required: Rs {rupees(required):,.2f} | available: Rs {rupees(available):,.2f}")
        return required <= available

    def enter(self) -> PositionState:
        cfg = self.cfg
        legs = resolve_legs(self.instruments, self.market_data, cfg.symbol, cfg.exchange, cfg.expiry)
        print(
            f"Legs: future {legs.future_symbol} (lot {legs.lot_size}, expiry {legs.expiry}), "
            f"short {cfg.num_short_calls} x call strike {legs.call_strike:,.2f} "
            f"(ref_id {legs.call_ref_id}, delta {legs.call_delta}), "
            f"underlying Rs {legs.underlying_price or 0:,.2f}"
        )
        if legs.equity_ref_id is None:
            raise SystemExit(f"Could not find the cash equity instrument for {cfg.symbol}; cannot hedge.")

        order = self._entry_order(legs)
        enough = self._margin_precheck(order)
        if self.gate.live and not enough:
            raise SystemExit("Not placing: available funds are below the funds required.")

        responses = self.gate.send([order], "entry (long future + short ATM calls)")
        intent_id = None
        if responses:
            first = responses[0]
            intent_id = first.intentOrderId
            if first.rejectionMsg or (first.status or "").upper() == "REJECTED":
                raise SystemExit("Entry order was rejected; no position opened.")

        entry_future = last_price(self.market_data, legs.future_ref_id) or 0.0
        underlying = legs.underlying_price or last_price(self.market_data, legs.equity_ref_id) or legs.call_strike
        state = PositionState(
            symbol=cfg.symbol,
            exchange=cfg.exchange,
            status=STATUS_OPEN,
            future_ref_id=legs.future_ref_id,
            future_qty_lots=cfg.future_lots,
            future_lot_size=legs.lot_size,
            call_ref_ids=[legs.call_ref_id] * cfg.num_short_calls,
            call_qty_lots_each=1,
            call_strike=legs.call_strike,
            call_lot_size=legs.lot_size,
            equity_ref_id=legs.equity_ref_id,
            strategy_intent_order_id=intent_id,
            entry_timestamp=_now_iso(),
            entry_underlying_price=underlying,
            last_hedge_underlying_price=underlying,
            entry_future_price=entry_future,
            entry_call_price=legs.call_ltp,
        )
        self.state = state
        self._save()
        print(f"Position OPEN ({self.gate.mode}) for {cfg.symbol}, intentOrderId={intent_id}")
        return state

    # ---- per-cycle logic -----------------------------------------------------------------
    def _net_delta(self, state: PositionState) -> float:
        with self._lock:
            deltas = [self._delta.get(r, FALLBACK_ATM_DELTA) for r in state.call_ref_ids]
        call_qty = [logic.lots_to_shares(state.call_qty_lots_each, state.call_lot_size)] * len(deltas)
        fut_qty = logic.lots_to_shares(state.future_qty_lots, state.future_lot_size)
        return logic.compute_net_delta_shares(fut_qty, deltas, call_qty, state.equity_hedge_shares)

    def _total_pnl(self, state: PositionState, underlying: float) -> Optional[float]:
        """Live: sum of broker position PnL for our contracts. Dry-run: paper PnL."""
        if self.gate.live:
            refs = {state.future_ref_id, *state.call_ref_ids}
            if state.equity_ref_id is not None:
                refs.add(state.equity_ref_id)
            result = self.portfolio.positions()
            rows = result.portfolio.positions if result and result.portfolio else []
            return sum(rupees(p.pnl) for p in rows or [] if p.refId in refs)
        fut_price = self._price(state.future_ref_id)
        call_price = self._price(state.call_ref_ids[0])
        if fut_price is None or call_price is None:
            return None
        return logic.mark_to_market_pnl(
            entry_future_price=state.entry_future_price or fut_price,
            future_price=fut_price,
            future_qty_shares=logic.lots_to_shares(state.future_qty_lots, state.future_lot_size),
            entry_call_price=state.entry_call_price or call_price,
            call_price=call_price,
            short_call_qty_shares=logic.lots_to_shares(
                state.call_qty_lots_each * len(state.call_ref_ids), state.call_lot_size
            ),
            equity_hedge_shares=state.equity_hedge_shares,
            equity_avg_hedge_price=state.equity_avg_hedge_price,
            equity_price=underlying,
            realized_hedge_pnl=state.cumulative_hedge_realized_pnl,
        )

    def _leg_order(self, ref_id: int, qty: int, side: str, delivery: str) -> dict:
        return {
            "isMultiLeg": False,
            "refId": ref_id,
            "qty": qty,
            "side": side,
            "deliveryType": delivery,
            "priceType": "MARKET",
            "validityType": "IOC",
            "executionMode": "ENTRY",
        }

    def _maybe_rehedge(self, state: PositionState, underlying: float) -> None:
        cfg = self.cfg
        ref_price = state.last_hedge_underlying_price or underlying
        if not logic.should_check_rehedge(ref_price, underlying, cfg.hedge_trigger_pct):
            return
        net_delta = self._net_delta(state)
        hedge = logic.compute_hedge_order(net_delta)
        if hedge is None:
            state.last_hedge_underlying_price = underlying
            self._save()
            return
        side, qty = hedge
        print(f"Re-hedge: {side} {qty} shares (net delta {net_delta:,.2f}, price Rs {underlying:,.2f})")
        order = self._leg_order(state.equity_ref_id, qty, side, cfg.hedge_delivery_type)
        fill_price = underlying
        try:
            responses = self.gate.send([order], "equity hedge")
        except Exception as err:
            print(f"Hedge order failed: {err}")
            return
        if responses:
            first = responses[0]
            if first.rejectionMsg or (first.status or "").upper() == "REJECTED":
                print("Hedge order rejected; not recorded.")
                return
            fill_price = rupees(first.filledPrice) if first.filledPrice else underlying
        signed = qty if side == "BUY" else -qty
        state.record_hedge_trade(
            timestamp=_now_iso(),
            side=side,
            qty=qty,
            price=fill_price,
            underlying_price=underlying,
            net_delta_before=net_delta,
            net_delta_after=net_delta + signed,
        )
        self._save()

    def _exit_orders(self, state: PositionState) -> List[dict]:
        fut_qty = logic.lots_to_shares(state.future_qty_lots, state.future_lot_size)
        orders = [self._leg_order(state.future_ref_id, fut_qty, "SELL", "CNC")]
        for ref_id, count in Counter(state.call_ref_ids).items():
            qty = logic.lots_to_shares(state.call_qty_lots_each * count, state.call_lot_size)
            orders.append(self._leg_order(ref_id, qty, "BUY", "CNC"))
        if state.equity_hedge_shares != 0 and state.equity_ref_id is not None:
            side = "SELL" if state.equity_hedge_shares > 0 else "BUY"
            orders.append(
                self._leg_order(state.equity_ref_id, abs(state.equity_hedge_shares), side, self.cfg.hedge_delivery_type)
            )
        return orders

    def _exit(self, state: PositionState, reason: str) -> None:
        state.status = STATUS_EXITING
        self._save()
        try:
            self.gate.send(self._exit_orders(state), f"exit ({reason})")
        except Exception as err:
            print(f"Exit order placement failed: {err}. Position left EXITING; check it manually.")
            raise
        state.status = STATUS_CLOSED
        state.exit_timestamp = _now_iso()
        state.exit_reason = reason
        self._save()
        print(f"Position CLOSED ({self.gate.mode}): {reason}")

    def _cycle(self, state: PositionState) -> bool:
        """One poll cycle. Returns True once the position has been exited."""
        underlying = self._price(state.equity_ref_id)
        if underlying is None:
            print("No underlying price yet (market closed?); waiting.")
            return False
        self._maybe_rehedge(state, underlying)
        pnl = self._total_pnl(state, underlying)
        stamp = datetime.now().strftime("%H:%M:%S")
        pnl_text = "-" if pnl is None else f"{pnl:,.2f}"
        print(
            f"[{stamp}] underlying Rs {underlying:,.2f} | net delta {self._net_delta(state):,.1f} sh | "
            f"equity hedge {state.equity_hedge_shares:+d} sh | hedges {len(state.hedge_trades)} | PnL Rs {pnl_text}"
        )
        if pnl is None:
            return False
        should_exit, reason = logic.evaluate_exit(pnl, self.cfg.pnl_target, self.cfg.pnl_stop_loss)
        if should_exit:
            self._exit(state, reason)
            return True
        return False

    # ---- main loop -----------------------------------------------------------------------
    def run(self, max_seconds: Optional[float] = None) -> None:
        from nubra_python_sdk.ticker import websocketdata

        cfg = self.cfg
        print(f"Mode: {self.gate.mode} | symbol {cfg.symbol} | state file {self.state_path if self.gate.live else '(none, dry-run)'}")

        state: Optional[PositionState] = PositionState.load(self.state_path) if self.gate.live else None
        if state is None or state.status == STATUS_CLOSED:
            state = self.enter()
        elif state.status == STATUS_OPEN:
            print(f"Resuming existing OPEN position for {cfg.symbol} from {self.state_path}")
            self.state = state
        else:
            raise SystemExit(
                f"State file for {cfg.symbol} is in status {state.status!r}. Check broker positions and "
                "orders, then fix or delete the state file before restarting."
            )

        socket = websocketdata.NubraDataSocket(
            client=self.nubra,
            on_orderbook_data=self._on_orderbook,
            on_greeks_data=self._on_greeks,
            on_connect=lambda m: print("[status]", m),
            on_close=lambda r: print(f"Closed: {r}"),
            on_error=lambda e: print(f"Error: {e}"),
        )
        socket.connect()
        book_refs = [str(r) for r in (state.equity_ref_id, state.future_ref_id) if r is not None]
        socket.subscribe(book_refs, data_type="orderbook")
        socket.subscribe([str(r) for r in sorted(set(state.call_ref_ids))], data_type="greeks")

        started = time.monotonic()
        try:
            while True:
                if self._cycle(state):
                    break
                if max_seconds is not None and time.monotonic() - started >= max_seconds:
                    print("Reached --max-seconds; stopping (position, if any, is left as is).")
                    break
                time.sleep(cfg.poll_seconds)
        except KeyboardInterrupt:
            print("\nStopped. An OPEN position stays open; rerun to resume monitoring it.")
        finally:
            try:
                socket.close()
            except Exception:
                pass
