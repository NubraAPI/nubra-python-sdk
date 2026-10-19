"""The hedging decision, run once per tick per strategy.

Delta/gamma convention:
  Net Delta = sum(leg.delta * leg.qty_lots * lot_size) over option legs
              + futures.qty_lots * futures.lot_size
  Net Gamma = sum(leg.gamma * leg.qty_lots * lot_size) over option legs
              (futures contribute 0 gamma)

Both are in underlying units, not lots. One futures lot contributes exactly
`lot_size` units of delta, so the offsetting trade in whole lots is
`hedge_qty_lots = -round(net_delta / lot_size)`.

The tolerance band (`DELTA_TOLERANCE_LOTS`) is converted to the same units with
`* lot_size` before comparing with net delta.

Net gamma only selects the polling interval: at or above the high-gamma
threshold the strategy is polled faster (HIGH_GAMMA mode), otherwise at the
normal interval (NORMAL mode).

Every strategy in `cfg.strategies` gets its own `run_tick()` call with its own
`StrategyConfig` and `Book`. The kill switch and the hedge rate limiter are
shared across strategies.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from .config import Config, StrategyConfig
from .nubra_client import NubraClient, SetupInstruments
from .positions import Book
from .risk import HedgeRateLimiter, clamp_to_position_cap
from .safety import KillSwitch

logger = logging.getLogger("gamma_hedging.hedger")

NORMAL_MODE = "NORMAL"
HIGH_GAMMA_MODE = "HIGH_GAMMA"


@dataclass
class TickResult:
    strategy_name: str
    timestamp: float
    spot: float | None
    net_delta: float | None
    net_gamma: float | None
    mode: str
    mode_changed: bool
    hedge_action: str | None
    futures_lots: int
    options_pnl: float
    futures_pnl: float
    total_pnl: float
    next_poll_interval_sec: float
    halted: bool
    halted_reason: str
    error: bool = False
    reasoning: list[str] = field(default_factory=list)
    # hedge_fired: an order was submitted (or simulated) and not rejected. It does
    # NOT mean confirmed filled; hedge_confirmed is true only when Nubra returned a
    # nonzero fill price. hedge_dry_run: no order was sent (simulated at LTP).
    hedge_fired: bool = False
    hedge_confirmed: bool = False
    hedge_dry_run: bool = False


def compute_hedge_qty_lots(net_delta: float, futures_lot_size: int) -> int:
    if futures_lot_size == 0:
        return 0
    return -round(net_delta / futures_lot_size)


def determine_mode(net_gamma: float, strat_cfg: StrategyConfig) -> str:
    return HIGH_GAMMA_MODE if abs(net_gamma) >= strat_cfg.high_gamma_threshold else NORMAL_MODE


def run_tick(
    cfg: Config,
    strat_cfg: StrategyConfig,
    client: NubraClient,
    instruments: SetupInstruments,
    book: Book,
    kill_switch: KillSwitch,
    rate_limiter: HedgeRateLimiter,
    previous_mode: str,
) -> TickResult:
    now = time.time()

    try:
        market_tick = client.get_market_tick(instruments)
    except Exception as exc:  # noqa: BLE001 - a market-data failure counts toward the kill switch, not a crash
        kill_switch.record_api_error(exc)
        return TickResult(
            strategy_name=strat_cfg.name,
            timestamp=now,
            spot=None,
            net_delta=None,
            net_gamma=None,
            mode=previous_mode,
            mode_changed=False,
            hedge_action=f"MARKET DATA ERROR: {exc}",
            futures_lots=book.futures_lots(),
            options_pnl=book.options_pnl(),
            futures_pnl=book.futures_pnl(),
            total_pnl=book.total_pnl(),
            next_poll_interval_sec=strat_cfg.poll_interval_normal_sec,
            halted=kill_switch.halted,
            halted_reason=kill_switch.reason,
            error=True,
            reasoning=[f"Could not fetch market data this tick: {exc}. Skipping the hedge decision entirely."],
        )

    kill_switch.record_api_success()
    kill_switch.record_spot(market_tick.timestamp, market_tick.spot_rupees, instruments.underlying)

    for leg in book.legs:
        leg_tick = market_tick.legs.get(leg.ref_id)
        if leg_tick is not None:
            leg.current_price_rupees = leg_tick.ltp_rupees
            leg.delta = leg_tick.delta
            leg.gamma = leg_tick.gamma
            leg.greeks_source = leg_tick.greeks_source

    if book.futures is not None:
        book.futures.current_price_rupees = market_tick.futures_ltp_rupees

    net_delta = book.net_delta()
    net_gamma = book.net_gamma()
    mode = determine_mode(net_gamma, strat_cfg)
    mode_changed = mode != previous_mode
    if mode_changed:
        logger.warning(
            "[%s] MONITORING MODE SWITCH: %s -> %s (net_gamma=%.6f, threshold=%.6f) -> poll interval now %.1fs",
            strat_cfg.name,
            previous_mode,
            mode,
            net_gamma,
            strat_cfg.high_gamma_threshold,
            strat_cfg.poll_interval_high_gamma_sec if mode == HIGH_GAMMA_MODE else strat_cfg.poll_interval_normal_sec,
        )

    hedge_action = None
    hedge_fired = False
    hedge_confirmed = False
    hedge_dry_run = False
    lot_size = book.futures.lot_size if book.futures is not None else 0
    tolerance_units = strat_cfg.delta_tolerance_lots * lot_size if lot_size else 0.0
    delta_breached = lot_size > 0 and abs(net_delta) > tolerance_units

    # Built up whether or not a trade fires: the explanation of why the hedger did
    # or did not act this tick, shown on the dashboards and in the events log.
    reasoning: list[str] = [
        f"Net Delta {net_delta:+.1f} vs tolerance band +/-{tolerance_units:.1f} "
        f"({'BAND BREACHED' if delta_breached else 'within band - no hedge needed'})",
        f"Net Gamma {net_gamma:+.6f} vs high-gamma threshold {strat_cfg.high_gamma_threshold:.6f} "
        f"-> monitoring mode {mode}",
    ]

    if kill_switch.halted:
        hedge_action = f"HALTED - no hedging: {kill_switch.reason}"
        reasoning.append(f"Kill switch engaged ({kill_switch.reason}) - no hedge trades will be placed.")
    elif delta_breached:
        desired_trade_lots = compute_hedge_qty_lots(net_delta, lot_size)
        reasoning.append(
            f"Hedge required: -round(net_delta / lot_size) = -round({net_delta:+.1f} / {lot_size}) "
            f"= {desired_trade_lots:+d} lot(s) of futures"
        )
        if desired_trade_lots == 0:
            reasoning.append("Rounds to 0 lots - nothing to trade this tick.")
        else:
            clamped_trade_lots, cap_warning = clamp_to_position_cap(
                book.futures.qty_lots, desired_trade_lots, strat_cfg.max_futures_position_lots
            )
            if cap_warning:
                reasoning.append(cap_warning)

            if clamped_trade_lots == 0:
                hedge_action = cap_warning or "Hedge trade suppressed: already at position cap"
                reasoning.append("Final decision: NO TRADE - already at the futures position cap.")
            elif not rate_limiter.allow(now):
                hedge_action = (
                    f"Hedge trade skipped (net_delta={net_delta:+.1f}, would trade "
                    f"{clamped_trade_lots:+d} lot(s)): rate limit "
                    f"{cfg.max_hedge_trades_per_min}/min reached"
                )
                reasoning.append(
                    f"Final decision: NO TRADE - rate limit ({cfg.max_hedge_trades_per_min}/min, shared "
                    f"across all strategies) reached."
                )
            else:
                action_word = "sending" if cfg.place_orders else "DRY RUN - simulating"
                reasoning.append(
                    f"Passed position-cap and rate-limit checks -> {action_word} {clamped_trade_lots:+d} "
                    f"lot(s) futures order."
                )
                try:
                    fill = client.place_futures_order(strat_cfg, instruments.futures, clamped_trade_lots)
                    book.futures.apply_fill(fill.filled_qty_lots, fill.avg_fill_price_rupees)
                    rate_limiter.record(now)
                    kill_switch.record_api_success()
                    hedge_fired = True
                    hedge_confirmed = fill.confirmed
                    hedge_dry_run = fill.dry_run
                    side = "BUY" if clamped_trade_lots > 0 else "SELL"
                    status_word = fill.status_word()
                    hedge_action = (
                        f"{side} {abs(clamped_trade_lots)} lot(s) futures {status_word} @ {fill.avg_fill_price_rupees:.2f} "
                        f"(net_delta was {net_delta:+.1f}, tolerance {tolerance_units:.1f})"
                    )
                    if cap_warning:
                        hedge_action += f" [{cap_warning}]"
                    reasoning.append(
                        f"Final decision: {side} {abs(clamped_trade_lots)} lot(s) order {status_word} "
                        f"@ {fill.avg_fill_price_rupees:.2f}."
                    )
                    if fill.dry_run:
                        reasoning.append(
                            "Dry run: the position book was updated as if filled at LTP, but nothing was "
                            "sent to Nubra. Use --place-orders to send orders."
                        )
                    elif not fill.confirmed:
                        reasoning.append(
                            "Not yet a confirmed fill - Nubra accepted the order but has not matched it. "
                            "Check the order status in Nubra before treating this as a real position."
                        )
                    logger.info("[%s] %s", strat_cfg.name, hedge_action)
                except Exception as exc:  # noqa: BLE001
                    kill_switch.record_api_error(exc)
                    hedge_action = f"HEDGE ORDER FAILED: {exc}"
                    reasoning.append(f"Final decision: order FAILED - {exc}")
    else:
        reasoning.append("Final decision: no hedge needed this tick.")

    logger.info("[%s] Tick decision: %s", strat_cfg.name, " | ".join(reasoning))

    return TickResult(
        strategy_name=strat_cfg.name,
        timestamp=market_tick.timestamp,
        spot=market_tick.spot_rupees,
        net_delta=book.net_delta(),
        net_gamma=net_gamma,
        mode=mode,
        mode_changed=mode_changed,
        hedge_action=hedge_action,
        futures_lots=book.futures_lots(),
        options_pnl=book.options_pnl(),
        futures_pnl=book.futures_pnl(),
        total_pnl=book.total_pnl(),
        next_poll_interval_sec=(
            strat_cfg.poll_interval_high_gamma_sec if mode == HIGH_GAMMA_MODE else strat_cfg.poll_interval_normal_sec
        ),
        halted=kill_switch.halted,
        halted_reason=kill_switch.reason,
        reasoning=reasoning,
        hedge_fired=hedge_fired,
        hedge_confirmed=hedge_confirmed,
        hedge_dry_run=hedge_dry_run,
    )


def maybe_reconcile(client: NubraClient, books: list[Book], tick_count: int, every_n: int = 20) -> list[str]:
    """Every `every_n` ticks, cross-check the internal books (summed across all
    strategies) against broker positions. An early warning for logs/dashboards."""
    if tick_count == 0 or tick_count % every_n != 0:
        return []
    return client.reconcile_positions(books)
