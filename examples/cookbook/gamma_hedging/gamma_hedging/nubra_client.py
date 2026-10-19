"""Thin wrapper around the Nubra Python SDK (`nubra_python_sdk`).

This is the only module that talks to Nubra:
  - auth / client init     InitNubraSdk(NubraEnv.UAT, env_creds=True)
  - instruments            InstrumentData.get_instruments_dataframe / get_instrument_by_ref_id
  - option chain + Greeks  MarketData.option_chain  (one call per tick covers every leg's LTP and Greeks)
  - spot / futures LTP     MarketData.current_price / MarketData.quote
  - orders                 NubraTrader.create_order (single-leg hedge, multi-leg setup), get_order, orders, cancel_orders_sentinel
  - positions snapshot     NubraPortfolio.positions

Price units: all monetary values in the SDK are integer paise (strike_price,
last_traded_price, entryPrice, filledPrice, tick_size, ...). Values read from the
SDK are converted to rupees at this module's boundary with `paise_to_rupees()`,
and orders are sent back out in paise. Nothing above this module sees paise.

Order placement is OFF by default. With `cfg.place_orders` False, the
`place_*` methods build the exact payload, log it, and return a simulated fill at the
current price instead of calling `create_order()`. Pass `--place-orders` in
main.py to actually send orders.

Greeks: the option-chain snapshot returns `delta` and `gamma` per contract. The
Black-Scholes fallback in `gamma_hedging.greeks` is used only for a leg whose
Greeks come back as None.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from .config import Config, PriceType, StrategyConfig
from .greeks import black_scholes_greeks, normalize_iv
from .positions import Book, FuturesPosition, OptionLeg
from .safety import resolve_env

logger = logging.getLogger("gamma_hedging.nubra_client")

PAISE_PER_RUPEE = 100
DEFAULT_TICK_PAISE = 5  # Rs 0.05

# Upper bound on how far AGGRESSIVE_FILL_PCT may push a futures LIMIT price away
# from the reference. A large bump can be rejected by the exchange price-band
# check (ORDER_PRICE_ABOVE_HIGH_PRICE_RANGE); 0.5% still crosses a normal touch
# spread while staying well inside typical bands.
FUTURES_AGGRESSIVE_PCT_CAP = 0.5


def paise_to_rupees(value) -> float:
    if value is None:
        return 0.0
    return float(value) / PAISE_PER_RUPEE


def rupees_to_paise(value: float) -> int:
    return round(value * PAISE_PER_RUPEE)


def to_tick(price_paise: float, tick_paise: int) -> int:
    """Round a paise price to the nearest multiple of the tick size (paise)."""
    tick = tick_paise or DEFAULT_TICK_PAISE
    return int(round(price_paise / tick) * tick)


# -- data shapes passed between this module and hedger.py / initial_position.py ----


@dataclass(frozen=True)
class LegSpec:
    ref_id: int
    option_type: str  # "CE" or "PE"
    strike: float
    lot_size: int
    tick_size: int = DEFAULT_TICK_PAISE  # paise


@dataclass(frozen=True)
class FuturesSpec:
    ref_id: int
    lot_size: int
    tick_size: int = DEFAULT_TICK_PAISE  # paise


@dataclass(frozen=True)
class SetupInstruments:
    legs: list[LegSpec]
    futures: FuturesSpec
    expiry: str  # YYYYMMDD
    strike_interval: float
    # The underlying/exchange this strategy's legs belong to. A strategy attached
    # from a discovered tag can be on a different underlying than cfg.underlying,
    # so get_market_tick() must fetch THIS underlying's option chain.
    underlying: str
    exchange: str


@dataclass(frozen=True)
class DiscoveredStrategy:
    """A strategy reconstructed from the executed orders under one stratTag on the
    broker, rather than one set up by this process (see discover_tagged_strategies)."""

    base_tag: str
    book: Book
    instruments: SetupInstruments


@dataclass(frozen=True)
class LegTick:
    ref_id: int
    ltp_rupees: float
    delta: float
    gamma: float
    greeks_source: str  # "api" or "black_scholes"


@dataclass(frozen=True)
class MarketTick:
    timestamp: float
    spot_rupees: float
    futures_ltp_rupees: float
    legs: dict[int, LegTick]


@dataclass(frozen=True)
class FillResult:
    ref_id: int
    filled_qty_lots: int  # signed: +buy, -sell
    avg_fill_price_rupees: float
    order_id: object = None
    # True only when Nubra returned a nonzero filledPrice. False means the order
    # was accepted but may still be resting; avg_fill_price_rupees is then the
    # latest LTP, a placeholder for book-keeping, not an execution price.
    confirmed: bool = False
    # True when no order was sent (dry run); the price is the current LTP.
    dry_run: bool = False

    def status_word(self) -> str:
        if self.dry_run:
            return "DRY RUN (no order sent)"
        if self.confirmed:
            return "FILLED"
        return "PLACED (status=OPEN, NOT YET CONFIRMED FILLED)"


def build_live_client(env_name: str, allow_prod: bool):
    """Create the SDK client for the requested environment (UAT by default).
    Credentials come from PHONE_NO / MPIN in .env (env_creds=True)."""
    from nubra_python_sdk.start_sdk import InitNubraSdk

    env = resolve_env(env_name, allow_prod)  # UAT by default; PROD only with --allow-prod
    logger.info("Initializing Nubra SDK client against environment=%s", env)
    return InitNubraSdk(env, env_creds=True)


class NubraClient:
    """Instrument resolution, market data and order placement."""

    def __init__(self, cfg: Config, nubra):
        from nubra_python_sdk.marketdata.market_data import MarketData
        from nubra_python_sdk.portfolio.portfolio_data import NubraPortfolio
        from nubra_python_sdk.refdata.instruments import InstrumentData
        from nubra_python_sdk.trading.trading_data import NubraTrader

        self.cfg = cfg
        self.nubra = nubra
        self.instruments = InstrumentData(nubra)
        self.market_data = MarketData(nubra)
        self.trader = NubraTrader(nubra)
        self.portfolio = NubraPortfolio(nubra)
        self._tz = ZoneInfo(cfg.timezone)

    # -- instrument resolution -------------------------------------------------

    def _select_strangle_strikes(self, chain, atm: float, strike_interval_native: float, strat_cfg: StrategyConfig):
        """Pick strangle strikes by target delta (for example the ~20-delta call
        and put) rather than a fixed strike offset from ATM, so the exposure is
        consistent across different IV levels.

        Falls back to a fixed strike-count offset if the chain has no delta data.
        """
        target = strat_cfg.strangle_target_delta

        ce_candidates = [o for o in chain.ce if o.delta is not None]
        pe_candidates = [o for o in chain.pe if o.delta is not None]
        if not ce_candidates or not pe_candidates:
            logger.warning(
                "[%s] option_chain() returned no delta data for CE/PE - falling back to a fixed "
                "strike-count offset (STRANGLE_OFFSET_STRIKES=%d).",
                strat_cfg.name,
                strat_cfg.strangle_offset_strikes,
            )
            offset = strat_cfg.strangle_offset_strikes * strike_interval_native
            ce_opt = min(chain.ce, key=lambda o: abs(o.strike_price - (atm + offset)))
            pe_opt = min(chain.pe, key=lambda o: abs(o.strike_price - (atm - offset)))
            return ce_opt, pe_opt

        # Call delta is positive, put delta is negative.
        ce_opt = min(ce_candidates, key=lambda o: abs(o.delta - target))
        pe_opt = min(pe_candidates, key=lambda o: abs(o.delta - (-target)))
        logger.info(
            "[%s] Delta-targeted strangle selection (target=%.2f): CE strike=%.2f (delta=%.3f), "
            "PE strike=%.2f (delta=%.3f)",
            strat_cfg.name,
            target,
            paise_to_rupees(ce_opt.strike_price),
            ce_opt.delta,
            paise_to_rupees(pe_opt.strike_price),
            pe_opt.delta,
        )
        return ce_opt, pe_opt

    def resolve_setup_instruments(self, strat_cfg: StrategyConfig) -> SetupInstruments:
        cfg = self.cfg
        chain_result = self.market_data.option_chain(
            cfg.underlying, exchange=cfg.exchange, expiry=cfg.expiry_override or ""
        )
        if chain_result is None:
            raise RuntimeError(
                f"option_chain() returned nothing for {cfg.underlying}/{cfg.exchange} "
                f"(expiry={cfg.expiry_override or 'nearest'})."
            )
        chain = chain_result.chain
        if not chain.ce or not chain.pe:
            raise RuntimeError(
                f"option_chain() returned no CE/PE rows for {cfg.underlying}/{cfg.exchange} "
                f"(expiry={cfg.expiry_override or 'nearest'}). Cannot resolve setup instruments."
            )

        strikes = sorted({opt.strike_price for opt in chain.ce} | {opt.strike_price for opt in chain.pe})
        gaps = [b - a for a, b in zip(strikes, strikes[1:]) if b - a > 0]
        strike_interval_native = min(gaps) if gaps else 0

        atm = self._resolve_atm_strike(chain, strikes)

        if strat_cfg.strategy_type.value == "STRADDLE":
            ce_opt = min(chain.ce, key=lambda o: abs(o.strike_price - atm))
            pe_opt = min(chain.pe, key=lambda o: abs(o.strike_price - atm))
        else:  # STRANGLE
            ce_opt, pe_opt = self._select_strangle_strikes(chain, atm, strike_interval_native, strat_cfg)

        if ce_opt.lot_size != pe_opt.lot_size:
            logger.warning(
                "CE lot_size (%s) != PE lot_size (%s) for the same expiry; using CE's lot_size.",
                ce_opt.lot_size,
                pe_opt.lot_size,
            )

        ce_leg = LegSpec(
            ref_id=ce_opt.ref_id,
            option_type="CE",
            strike=paise_to_rupees(ce_opt.strike_price),
            lot_size=ce_opt.lot_size,
            tick_size=self._safe_tick_size(ce_opt.ref_id),
        )
        pe_leg = LegSpec(
            ref_id=pe_opt.ref_id,
            option_type="PE",
            strike=paise_to_rupees(pe_opt.strike_price),
            lot_size=pe_opt.lot_size,
            tick_size=self._safe_tick_size(pe_opt.ref_id),
        )

        futures = self._resolve_futures_spec()

        expiry = chain.expiry or cfg.expiry_override
        if not expiry:
            raise RuntimeError("Could not determine expiry for setup instruments.")

        logger.info(
            "[%s] Resolved setup instruments: underlying=%s expiry=%s strategy=%s "
            "CE strike=%.2f (ref_id=%s) PE strike=%.2f (ref_id=%s) lot_size=%s strike_interval=%.2f "
            "futures ref_id=%s lot_size=%s",
            strat_cfg.name,
            cfg.underlying,
            expiry,
            strat_cfg.strategy_type.value,
            ce_leg.strike,
            ce_leg.ref_id,
            pe_leg.strike,
            pe_leg.ref_id,
            ce_leg.lot_size,
            paise_to_rupees(strike_interval_native),
            futures.ref_id,
            futures.lot_size,
        )

        return SetupInstruments(
            legs=[ce_leg, pe_leg],
            futures=futures,
            expiry=expiry,
            strike_interval=paise_to_rupees(strike_interval_native),
            underlying=cfg.underlying,
            exchange=cfg.exchange,
        )

    def _resolve_atm_strike(self, chain, strikes: list[int]) -> int:
        """ATM strike from the dedicated current_price() endpoint plus the listed
        strikes. The chain's own `at_the_money_strike` / `current_price` fields have
        been observed to come back stale or zero in UAT while current_price() was
        correct, so they are only a fallback if current_price() fails.
        """
        cfg = self.cfg
        try:
            spot_native = self.market_data.current_price(cfg.underlying, exchange=cfg.exchange).price
        except Exception as exc:  # noqa: BLE001
            spot_native = None
            logger.warning("current_price() failed while resolving ATM strike: %s", exc)

        if spot_native:
            atm = min(strikes, key=lambda s: abs(s - spot_native))
            logger.info(
                "ATM strike resolved from current_price()=%.2f -> nearest listed strike %.2f",
                paise_to_rupees(spot_native),
                paise_to_rupees(atm),
            )
            return atm

        if chain.at_the_money_strike:
            logger.warning(
                "current_price() returned nothing usable; falling back to option_chain()'s "
                "at_the_money_strike=%s. Check it against a real spot reading.",
                chain.at_the_money_strike,
            )
            return chain.at_the_money_strike

        raise RuntimeError("Could not determine an ATM strike from either current_price() or the option chain.")

    def _resolve_futures_spec(self, underlying: str | None = None, exchange: str | None = None) -> FuturesSpec:
        underlying = underlying or self.cfg.underlying
        exchange = exchange or self.cfg.exchange
        df = self.instruments.get_instruments_dataframe(exchange=exchange)
        futures = df[(df["asset"] == underlying) & (df["derivative_type"] == "FUT")].sort_values("expiry")
        if futures.empty:
            raise RuntimeError(f"No {underlying} futures contract found on {exchange}.")
        row = futures.iloc[0]  # nearest expiry
        return FuturesSpec(
            ref_id=int(row["ref_id"]),
            lot_size=int(row["lot_size"]),
            tick_size=int(row["tick_size"]) if row.get("tick_size") else DEFAULT_TICK_PAISE,
        )

    def _safe_tick_size(self, ref_id: int, exchange: str | None = None) -> int:
        try:
            instrument = self.instruments.get_instrument_by_ref_id(ref_id, exchange=exchange or self.cfg.exchange)
            return int(instrument.tick_size) if instrument and instrument.tick_size else DEFAULT_TICK_PAISE
        except Exception as exc:  # noqa: BLE001 - tick_size is only needed for LIMIT pricing
            logger.debug("Could not resolve tick_size for ref_id=%s: %s", ref_id, exc)
            return DEFAULT_TICK_PAISE

    # -- market data --------------------------------------------------------------

    def get_market_tick(self, instruments: SetupInstruments) -> MarketTick:
        # Use this strategy's own underlying/exchange: a strategy attached from a
        # discovered tag may be on a different one than cfg.underlying.
        underlying, exchange = instruments.underlying, instruments.exchange
        chain_result = self.market_data.option_chain(underlying, exchange=exchange, expiry=instruments.expiry)
        if chain_result is None:
            raise RuntimeError(f"option_chain() returned nothing for {underlying}/{exchange} expiry={instruments.expiry}")
        chain = chain_result.chain
        spot = paise_to_rupees(chain.current_price)
        if not chain.current_price:
            # The chain's embedded current_price can read 0 in UAT; use the
            # dedicated endpoint instead of showing a spot of 0.00.
            try:
                spot = paise_to_rupees(self.market_data.current_price(underlying, exchange=exchange).price)
            except Exception as exc:  # noqa: BLE001
                logger.warning("current_price() fallback failed while chain.current_price was empty: %s", exc)

        by_ref_id = {opt.ref_id: opt for opt in list(chain.ce) + list(chain.pe)}

        time_to_expiry_years = self._time_to_expiry_years(instruments.expiry)

        legs: dict[int, LegTick] = {}
        for leg in instruments.legs:
            row = by_ref_id.get(leg.ref_id)
            if row is None:
                logger.warning("option_chain() did not include ref_id=%s (%s); skipping this tick's leg data.", leg.ref_id, leg.option_type)
                continue

            ltp = paise_to_rupees(row.last_traded_price)
            delta, gamma, source = row.delta, row.gamma, "api"
            if delta is None or gamma is None:
                bs = black_scholes_greeks(
                    spot=spot,
                    strike=leg.strike,
                    time_to_expiry_years=time_to_expiry_years,
                    iv_decimal=normalize_iv(row.iv or 0.0),
                    risk_free_rate=self.cfg.risk_free_rate,
                    option_type=leg.option_type,
                )
                delta, gamma, source = bs.delta, bs.gamma, "black_scholes"
                logger.debug("API Greeks missing for ref_id=%s; used Black-Scholes fallback.", leg.ref_id)

            legs[leg.ref_id] = LegTick(ref_id=leg.ref_id, ltp_rupees=ltp, delta=delta, gamma=gamma, greeks_source=source)

        futures_quote = self.market_data.quote(ref_id=instruments.futures.ref_id, levels=1)
        futures_ltp = paise_to_rupees(futures_quote.orderBook.last_traded_price)

        return MarketTick(timestamp=time.time(), spot_rupees=spot, futures_ltp_rupees=futures_ltp, legs=legs)

    def _time_to_expiry_years(self, expiry_yyyymmdd: str) -> float:
        expiry_date = datetime.strptime(expiry_yyyymmdd, "%Y%m%d").date()
        close_h, close_m = (int(x) for x in self.cfg.market_close_time.split(":"))
        expiry_dt = datetime(expiry_date.year, expiry_date.month, expiry_date.day, close_h, close_m, tzinfo=self._tz)
        seconds_left = max((expiry_dt - datetime.now(self._tz)).total_seconds(), 1.0)
        return seconds_left / (365.0 * 24 * 3600)

    # -- order placement ----------------------------------------------------------

    def place_setup_strategy(self, strat_cfg: StrategyConfig, instruments: SetupInstruments) -> list[FillResult]:
        """Sell the setup structure as one multi-leg order (both legs short)."""
        lot_size = instruments.legs[0].lot_size
        qty = lot_size * strat_cfg.setup_lots

        payload = {
            "isMultiLeg": True,
            "qty": qty,
            "side": "BUY",  # strategy-level side is always BUY; leg direction comes from the sign of unitQty
            "deliveryType": "CNC",  # required for the multi-leg strategy shape
            "priceType": strat_cfg.setup_price_type.value,
            "validityType": "IOC" if strat_cfg.setup_price_type == PriceType.MARKET else "DAY",
            "executionMode": "ENTRY",
            "legs": [{"refId": leg.ref_id, "unitQty": -1} for leg in instruments.legs],
            # Same tag as the hedge order, so Nubra's tag portfolio shows the
            # option legs and the futures hedge as one position.
            "stratTags": [strat_cfg.strat_tag],
        }

        # Current prices are needed for a LIMIT price and for the dry-run fill.
        tick = None
        if strat_cfg.setup_price_type == PriceType.LIMIT or not self.cfg.place_orders:
            tick = self.get_market_tick(instruments)
        if strat_cfg.setup_price_type == PriceType.LIMIT:
            # entryPrice is the signed net premium in paise: negative for a net credit.
            net_credit_paise = sum(
                rupees_to_paise(tick.legs[leg.ref_id].ltp_rupees) for leg in instruments.legs if leg.ref_id in tick.legs
            )
            if self.cfg.aggressive_fill_pct > 0:
                # Accept a smaller credit so the order crosses the book.
                net_credit_paise *= 1 - self.cfg.aggressive_fill_pct / 100
            tick_paise = instruments.legs[0].tick_size
            payload["entryPrice"] = min(-to_tick(net_credit_paise, tick_paise), -tick_paise)

        if not self.cfg.place_orders:
            print(f"[{strat_cfg.name}] DRY RUN - would send setup order (use --place-orders to send): {payload}")
            logger.warning("[%s] DRY RUN - setup order not sent: %s", strat_cfg.name, payload)
            return [
                FillResult(
                    ref_id=leg.ref_id,
                    filled_qty_lots=-strat_cfg.setup_lots,
                    avg_fill_price_rupees=tick.legs[leg.ref_id].ltp_rupees if leg.ref_id in tick.legs else 0.0,
                    dry_run=True,
                )
                for leg in instruments.legs
            ]

        logger.info("[%s] Placing setup strategy order: %s", strat_cfg.name, payload)
        result = self.trader.create_order(payload)
        return self._fills_from_strategy_response(result, instruments, strat_cfg.setup_lots, strat_cfg.name)

    def _fills_from_strategy_response(
        self, result, instruments: SetupInstruments, setup_lots: int, strategy_name: str
    ) -> list[FillResult]:
        orders = getattr(result, "orders", None) or []
        if not orders:
            raise RuntimeError(f"create_order() for the setup strategy returned no orders: {result!r}")

        strategy_order = orders[0]
        intent_order_id = strategy_order.intentOrderId
        polled = self._poll_for_fill(intent_order_id)

        leg_source = polled if polled is not None else strategy_order
        status = str(getattr(leg_source, "status", "")).upper()
        if any(bad in status for bad in ("REJECT", "CANCEL", "EXPIRE")):
            rejection_msg = getattr(leg_source, "rejectionMsg", None) or "(no reason given by Nubra)"
            raise RuntimeError(
                f"[{strategy_name}] Setup order intentOrderId={intent_order_id} came back {status}, "
                f"not filled: {rejection_msg}. No position was established; not seeding the book."
            )

        leg_rows = {row.refId: row for row in (leg_source.legs or [])}

        fills = []
        for leg in instruments.legs:
            row = leg_rows.get(leg.ref_id)
            confirmed = row is not None and bool(row.filledPrice)
            if confirmed:
                avg_price = paise_to_rupees(row.filledPrice)
            else:
                logger.warning(
                    "[%s] Setup leg ref_id=%s has no confirmed fill price yet (status=%s); using the last "
                    "LTP as a placeholder entry price. Check get_order() before trusting P&L.",
                    strategy_name,
                    leg.ref_id,
                    getattr(leg_source, "status", "unknown"),
                )
                tick = self.get_market_tick(instruments)
                avg_price = tick.legs[leg.ref_id].ltp_rupees if leg.ref_id in tick.legs else 0.0
            fills.append(
                FillResult(
                    ref_id=leg.ref_id,
                    filled_qty_lots=-setup_lots,  # both legs are sold in the setup structure
                    avg_fill_price_rupees=avg_price,
                    order_id=intent_order_id,
                    confirmed=confirmed,
                )
            )
        return fills

    def _reference_price_for_limit(self, futures: FuturesSpec, side: str) -> int:
        """Reference price (paise) for a LIMIT order: the side of the book we
        would cross (best ask for a BUY, best bid for a SELL), then LTP, then the
        other side. Returns 0 only if every source is empty."""
        book = self.market_data.quote(ref_id=futures.ref_id, levels=1).orderBook
        ltp = book.last_traded_price or 0
        best_ask = book.ask[0].price if book.ask else 0
        best_bid = book.bid[0].price if book.bid else 0
        candidates = [best_ask, ltp, best_bid] if side == "BUY" else [best_bid, ltp, best_ask]
        return next((p for p in candidates if p and p > 0), 0)

    def place_futures_order(self, strat_cfg: StrategyConfig, futures: FuturesSpec, signed_qty_lots: int) -> FillResult:
        qty = abs(signed_qty_lots) * futures.lot_size
        side = "BUY" if signed_qty_lots > 0 else "SELL"

        payload = {
            "refId": futures.ref_id,
            "qty": qty,
            "side": side,
            "deliveryType": "IDAY",
            "priceType": strat_cfg.hedge_price_type.value,
            "validityType": "IOC" if strat_cfg.hedge_price_type == PriceType.MARKET else "DAY",
            "isMultiLeg": False,
            "executionMode": "ENTRY",
            "stratTags": [strat_cfg.strat_tag],  # same tag as the option legs
        }

        tick_paise = futures.tick_size or DEFAULT_TICK_PAISE
        if strat_cfg.hedge_price_type == PriceType.LIMIT:
            ref_paise = self._reference_price_for_limit(futures, side)
            if ref_paise <= 0:
                logger.warning(
                    "[%s] No usable reference price (LTP/bid/ask all empty) for futures ref_id=%s; this LIMIT "
                    "order will likely be rejected.",
                    strat_cfg.name,
                    futures.ref_id,
                )
                limit_paise = tick_paise
            elif self.cfg.aggressive_fill_pct > 0:
                # Cross the book by a small, capped buffer so the order fills
                # instead of resting at the reference price.
                effective_pct = min(self.cfg.aggressive_fill_pct, FUTURES_AGGRESSIVE_PCT_CAP)
                factor = 1 + effective_pct / 100 if side == "BUY" else 1 - effective_pct / 100
                limit_paise = max(to_tick(ref_paise * factor, tick_paise), tick_paise)
                logger.warning(
                    "[%s] AGGRESSIVE_FILL_PCT=%.1f%% requested, capped to %.1f%% for futures -> %s at %.2f "
                    "(reference %.2f)",
                    strat_cfg.name,
                    self.cfg.aggressive_fill_pct,
                    effective_pct,
                    side,
                    paise_to_rupees(limit_paise),
                    paise_to_rupees(ref_paise),
                )
            else:
                limit_paise = to_tick(ref_paise, tick_paise)
            payload["entryPrice"] = limit_paise

        if not self.cfg.place_orders:
            ltp = paise_to_rupees(self.market_data.quote(ref_id=futures.ref_id, levels=1).orderBook.last_traded_price)
            logger.warning("[%s] DRY RUN - futures hedge order not sent: %s", strat_cfg.name, payload)
            return FillResult(
                ref_id=futures.ref_id,
                filled_qty_lots=signed_qty_lots,
                avg_fill_price_rupees=ltp,
                dry_run=True,
            )

        logger.info("[%s] Placing futures hedge order: %s", strat_cfg.name, payload)
        result = self.trader.create_order(payload)
        orders = getattr(result, "orders", None) or []
        if not orders:
            raise RuntimeError(f"create_order() for the futures hedge returned no orders: {result!r}")

        order = orders[0]
        polled = self._poll_for_fill(order.intentOrderId)
        final = polled if polled is not None else order
        status = str(getattr(final, "status", "")).upper()
        if any(bad in status for bad in ("REJECT", "CANCEL", "EXPIRE")):
            rejection_msg = getattr(final, "rejectionMsg", None) or "(no reason given by Nubra)"
            raise RuntimeError(
                f"Futures hedge order intentOrderId={order.intentOrderId} came back {status}, not filled: "
                f"{rejection_msg}"
            )

        confirmed = bool(final.filledPrice)
        if confirmed:
            avg_price = paise_to_rupees(final.filledPrice)
        else:
            logger.warning(
                "[%s] Futures hedge order intentOrderId=%s has no confirmed fill price yet (status=%s); "
                "using LTP as a placeholder.",
                strat_cfg.name,
                order.intentOrderId,
                getattr(final, "status", "unknown"),
            )
            quote = self.market_data.quote(ref_id=futures.ref_id, levels=1)
            avg_price = paise_to_rupees(quote.orderBook.last_traded_price)

        return FillResult(
            ref_id=futures.ref_id,
            filled_qty_lots=signed_qty_lots,
            avg_fill_price_rupees=avg_price,
            order_id=order.intentOrderId,
            confirmed=confirmed,
        )

    def _poll_for_fill(self, intent_order_id: int, timeout_sec: float = 5.0, interval_sec: float = 0.5):
        deadline = time.monotonic() + timeout_sec
        last = None
        while time.monotonic() < deadline:
            try:
                matches = self.trader.get_order(intent_order_id)
            except Exception as exc:  # noqa: BLE001
                logger.debug("get_order(%s) failed while polling for fill: %s", intent_order_id, exc)
                time.sleep(interval_sec)
                continue
            if matches:
                last = matches[0]
                status = str(getattr(last, "status", "")).upper()
                if "EXECUT" in status or (getattr(last, "filledQty", 0) or 0) > 0:
                    return last
            time.sleep(interval_sec)
        return last

    # -- open-order cleanup -----------------------------------------------------------

    def find_open_orders(self, underlying: str) -> list:
        """Open orders (any session) whose instrument's underlying matches.

        Matched by underlying, not by stratTags: open orders come back with
        `stratTags=None` from orders(status="OPEN"); tags are only populated on
        terminal orders.
        """
        result = self.trader.orders(status="OPEN")
        groups = getattr(result, "orders", None) or {}
        if not isinstance(groups, dict):
            return []

        def matches(order) -> bool:
            legs = getattr(order, "legs", None) or []
            for leg in legs:
                ref_data = getattr(leg, "refData", None)
                if ref_data is not None and getattr(ref_data, "asset", None) == underlying:
                    return True
            ref_data = getattr(order, "refData", None)
            return ref_data is not None and getattr(ref_data, "asset", None) == underlying

        return [order for items in groups.values() for order in items if matches(order)]

    def cancel_order_with_retry(self, intent_order_id: int, attempts: int = 3, delay_sec: float = 1.5) -> None:
        """Cancel one order, retrying: the exchange can answer "cancellation is
        temporarily unavailable while the request is being processed"."""
        last_exc: Exception | None = None
        for _ in range(attempts):
            try:
                self.trader.cancel_orders_sentinel([{"orderId": intent_order_id}])
                return
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                time.sleep(delay_sec)
        assert last_exc is not None
        raise last_exc

    # -- reconciliation -------------------------------------------------------------

    def reconcile_positions(self, books: list) -> list[str]:
        """Compare broker-reported positions with the internal books, summed
        across ALL strategies (two strategies on the same futures contract share
        one broker position). An early warning only, not a guardrail."""
        warnings: list[str] = []
        try:
            result = self.portfolio.positions()
        except Exception as exc:  # noqa: BLE001
            return [f"reconcile_positions: positions() call failed: {exc}"]

        broker_net_by_ref_id = {}
        for pos in result.portfolio.positions or []:
            ref_id = getattr(pos, "refId", None)
            if ref_id is not None:
                broker_net_by_ref_id[ref_id] = getattr(pos, "netQuantity", 0)

        expected_by_ref_id: dict[int, int] = {}
        labels_by_ref_id: dict[int, str] = {}
        for book in books:
            for leg in book.legs:
                expected_by_ref_id[leg.ref_id] = expected_by_ref_id.get(leg.ref_id, 0) + leg.qty_lots * leg.lot_size
                labels_by_ref_id.setdefault(leg.ref_id, f"{leg.option_type} {leg.strike}")
            if book.futures is not None:
                ref_id = book.futures.ref_id
                expected_by_ref_id[ref_id] = expected_by_ref_id.get(ref_id, 0) + book.futures.qty_lots * book.futures.lot_size
                labels_by_ref_id.setdefault(ref_id, "FUT")

        for ref_id, expected in expected_by_ref_id.items():
            actual = broker_net_by_ref_id.get(ref_id, 0)
            if actual != expected:
                warnings.append(
                    f"Position mismatch for ref_id={ref_id} ({labels_by_ref_id.get(ref_id, '?')}), "
                    f"summed across all strategies: internal books={expected}, broker={actual}"
                )

        for w in warnings:
            logger.warning(w)
        return warnings

    # -- live tag discovery ---------------------------------------------------------

    @staticmethod
    def _base_tag(tag: str) -> str:
        """Strip a "-setup"/"-hedge" suffix so the option legs and the futures
        hedge of one strategy, if placed under two literal tags, are discovered as
        ONE strategy. A tag with neither suffix is used as-is."""
        if tag.endswith("-setup"):
            return tag[: -len("-setup")]
        if tag.endswith("-hedge"):
            return tag[: -len("-hedge")]
        return tag

    def discover_tagged_strategies(self) -> dict[str, DiscoveredStrategy]:
        """Reconstruct every strategy currently live on the broker from its
        stratTag by replaying every EXECUTED order's fills, including strategies
        this process did not set up. This backs the dashboard's "attach hedging
        to this tagged position" toggle.

        Only orders(status="EXECUTED") is usable: still-OPEN orders come back with
        `stratTags=None`. A tag whose fills net to flat is dropped.
        """
        try:
            result = self.trader.orders(status="EXECUTED")
        except Exception as exc:  # noqa: BLE001
            logger.warning("discover_tagged_strategies: orders() call failed: %s", exc)
            return {}

        groups = getattr(result, "orders", None) or {}
        if not isinstance(groups, dict):
            return {}
        all_orders = [o for items in groups.values() for o in items]
        all_orders.sort(key=lambda o: getattr(o, "intentOrderId", 0))

        # Per base tag, per ref_id, fills are replayed in order. FuturesPosition is
        # reused purely as a weighted-average accumulator (it handles flips
        # through zero); the math is the same for options.
        by_tag: dict[str, dict[int, FuturesPosition]] = {}
        meta_by_ref_id: dict[int, dict] = {}

        def _accumulator(base_tag: str, ref_id: int, lot_size: int) -> FuturesPosition:
            refs = by_tag.setdefault(base_tag, {})
            acc = refs.get(ref_id)
            if acc is None:
                acc = FuturesPosition(ref_id=ref_id, lot_size=lot_size)
                refs[ref_id] = acc
            return acc

        def _parse_strike_expiry(nubra_name: str) -> tuple[float, str]:
            # e.g. "OPT_NIFTY_20260908_CE_2380000" -> (strike in rupees, expiry)
            parts = (nubra_name or "").split("_")
            if len(parts) >= 5 and parts[0] == "OPT":
                return float(parts[4]) / PAISE_PER_RUPEE, parts[2]
            return 0.0, ""

        for order in all_orders:
            tags = getattr(order, "stratTags", None) or []
            if not tags:
                continue
            base_tag = self._base_tag(tags[0])

            legs = getattr(order, "legs", None)
            if legs:
                for leg in legs:
                    ref_data = getattr(leg, "refData", None)
                    if ref_data is None:
                        continue
                    lot_size = ref_data.lotSize or 1
                    unit_qty = getattr(leg, "unitQty", 0) or 0
                    filled_qty = getattr(leg, "filledQty", 0) or 0
                    filled_price = getattr(leg, "filledPrice", None)
                    if not unit_qty or not filled_qty or not filled_price:
                        continue
                    signed_lots = (1 if unit_qty > 0 else -1) * (filled_qty / lot_size)
                    acc = _accumulator(base_tag, leg.refId, lot_size)
                    acc.apply_fill(round(signed_lots), paise_to_rupees(filled_price))
                    meta_by_ref_id.setdefault(
                        leg.refId,
                        {
                            "derivative_type": ref_data.derivativeType,
                            "option_type": ref_data.optionType,
                            "asset": ref_data.asset,
                            "exchange": ref_data.exchange,
                            "lot_size": lot_size,
                            "strike_expiry": _parse_strike_expiry(ref_data.zanskarName),  # SDK field holding the instrument name
                        },
                    )
            else:
                ref_data = getattr(order, "refData", None)
                ref_id = getattr(order, "refId", None)
                filled_qty = getattr(order, "filledQty", 0) or 0
                filled_price = getattr(order, "filledPrice", None)
                if ref_id is None or ref_data is None or not filled_qty or not filled_price:
                    continue
                lot_size = ref_data.lotSize or 1
                side = getattr(order, "side", "BUY")
                signed_lots = (1 if side == "BUY" else -1) * (filled_qty / lot_size)
                acc = _accumulator(base_tag, ref_id, lot_size)
                acc.apply_fill(round(signed_lots), paise_to_rupees(filled_price))
                meta_by_ref_id.setdefault(
                    ref_id,
                    {
                        "derivative_type": ref_data.derivativeType,
                        "option_type": None,
                        "asset": ref_data.asset,
                        "exchange": ref_data.exchange,
                        "lot_size": lot_size,
                        "strike_expiry": (0.0, ""),
                    },
                )

        discovered: dict[str, DiscoveredStrategy] = {}
        for base_tag, refs in by_tag.items():
            legs: list[LegSpec] = []
            book_legs: list[OptionLeg] = []
            futures_spec: FuturesSpec | None = None
            book_futures: FuturesPosition | None = None
            expiry = ""
            underlying: str | None = None
            exchange: str | None = None

            for ref_id, acc in refs.items():
                if acc.qty_lots == 0:
                    continue
                meta = meta_by_ref_id.get(ref_id, {})
                asset, asset_exchange = meta.get("asset"), meta.get("exchange")
                if asset and underlying is None:
                    # The strategy's underlying is whatever its own legs are,
                    # taken from the first leg found.
                    underlying, exchange = asset, asset_exchange
                elif asset and asset != underlying:
                    logger.warning(
                        "discover_tagged_strategies: tag %r mixes underlyings (%s and %s); the spot/Greeks "
                        "model assumes one underlying per strategy, so ref_id=%s (%s) is skipped.",
                        base_tag,
                        underlying,
                        asset,
                        ref_id,
                        asset,
                    )
                    continue
                if meta.get("derivative_type") == "FUT":
                    futures_spec = FuturesSpec(
                        ref_id=ref_id, lot_size=acc.lot_size, tick_size=self._safe_tick_size(ref_id, exchange)
                    )
                    book_futures = acc
                else:
                    strike, leg_expiry = meta.get("strike_expiry", (0.0, ""))
                    expiry = expiry or leg_expiry
                    legs.append(
                        LegSpec(
                            ref_id=ref_id,
                            option_type=meta.get("option_type") or "?",
                            strike=strike,
                            lot_size=acc.lot_size,
                            tick_size=self._safe_tick_size(ref_id, exchange),
                        )
                    )
                    book_legs.append(
                        OptionLeg(
                            ref_id=ref_id,
                            option_type=meta.get("option_type") or "?",
                            strike=strike,
                            lot_size=acc.lot_size,
                            qty_lots=acc.qty_lots,
                            entry_price_rupees=acc.avg_entry_price_rupees,
                            current_price_rupees=acc.avg_entry_price_rupees,
                        )
                    )

            if not book_legs and (book_futures is None or book_futures.qty_lots == 0):
                continue  # nothing live under this tag anymore

            underlying = underlying or self.cfg.underlying
            exchange = exchange or self.cfg.exchange

            if futures_spec is None:
                # Option legs but no futures fill yet: resolve this strategy's own
                # underlying's future to hedge with once attached.
                futures_spec = self._resolve_futures_spec(underlying=underlying, exchange=exchange)
                book_futures = FuturesPosition(ref_id=futures_spec.ref_id, lot_size=futures_spec.lot_size)

            if not expiry:
                # Futures-only tag: use the futures contract's own expiry so
                # option_chain() still has a valid expiry to query.
                try:
                    inst = self.instruments.get_instrument_by_ref_id(futures_spec.ref_id, exchange=exchange)
                    expiry = str(getattr(inst, "expiry", "")) or ""
                except Exception:  # noqa: BLE001
                    expiry = ""

            strikes = sorted({leg.strike for leg in legs})
            gaps = [b - a for a, b in zip(strikes, strikes[1:]) if b - a > 0]
            strike_interval = min(gaps) if gaps else 50.0

            book = Book(legs=book_legs, futures=book_futures)
            instruments = SetupInstruments(
                legs=legs,
                futures=futures_spec,
                expiry=expiry,
                strike_interval=strike_interval,
                underlying=underlying,
                exchange=exchange,
            )
            discovered[base_tag] = DiscoveredStrategy(base_tag=base_tag, book=book, instruments=instruments)

        return discovered
