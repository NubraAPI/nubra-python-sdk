"""Initial short option structure.

For each strategy in `cfg.strategies`, sell a short straddle or strangle (one
multi-leg order) and seed an in-memory `Book` from the result. This stands in for
a short-options position already held going into expiry day. The hedger then
manages the futures hedge against that book.

Without `--place-orders` the order is only printed and the book is seeded from the
current option prices (see `NubraClient.place_setup_strategy`).
"""

from __future__ import annotations

import logging

from .config import Config, StrategyConfig
from .nubra_client import NubraClient, SetupInstruments
from .positions import Book, FuturesPosition, OptionLeg

logger = logging.getLogger("gamma_hedging.initial_position")


def run_setup(cfg: Config, strat_cfg: StrategyConfig, client: NubraClient) -> tuple[Book, SetupInstruments]:
    instruments = client.resolve_setup_instruments(strat_cfg)

    logger.info(
        "[%s] Setting up initial short %s: %d lot(s) each leg, expiry=%s",
        strat_cfg.name,
        strat_cfg.strategy_type.value,
        strat_cfg.setup_lots,
        instruments.expiry,
    )
    fills = client.place_setup_strategy(strat_cfg, instruments)

    fills_by_ref_id = {fill.ref_id: fill for fill in fills}
    legs = []
    for leg_spec in instruments.legs:
        fill = fills_by_ref_id.get(leg_spec.ref_id)
        if fill is None:
            raise RuntimeError(f"[{strat_cfg.name}] Setup placement did not return a fill for ref_id={leg_spec.ref_id}")
        legs.append(
            OptionLeg(
                ref_id=leg_spec.ref_id,
                option_type=leg_spec.option_type,
                strike=leg_spec.strike,
                lot_size=leg_spec.lot_size,
                qty_lots=fill.filled_qty_lots,
                entry_price_rupees=fill.avg_fill_price_rupees,
                current_price_rupees=fill.avg_fill_price_rupees,
            )
        )
        logger.info(
            "[%s] Setup leg %s: %s strike=%.2f qty_lots=%d entry_price=%.2f",
            strat_cfg.name,
            fill.status_word(),
            leg_spec.option_type,
            leg_spec.strike,
            fill.filled_qty_lots,
            fill.avg_fill_price_rupees,
        )

    futures = FuturesPosition(ref_id=instruments.futures.ref_id, lot_size=instruments.futures.lot_size)
    return Book(legs=legs, futures=futures), instruments
