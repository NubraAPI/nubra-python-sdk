"""Scoring weights, thresholds and the bundled NIFTY 50 weights table."""
from __future__ import annotations

import csv
from pathlib import Path

WEIGHTS_CSV = Path(__file__).with_name("nifty50_weights.csv")

# Older tickers that the instrument master may list under a new symbol.
SYMBOL_ALIASES = {"TATAMOTORS": "TMPV"}

# Per-stock pressure = BOOK * order-book imbalance + MOMENTUM * LTP momentum + VOLUME * volume impulse.
BOOK_WEIGHT = 0.55
MOMENTUM_WEIGHT = 0.35
VOLUME_WEIGHT = 0.10
MOMENTUM_GAIN = 500.0  # tick-to-tick return multiplier before clipping to [-1, 1]
BOOK_LEVELS = 5        # depth levels summed on each side

# Bias score = PRESSURE_BLEND * pressure score + OI_BLEND * OI score.
PRESSURE_BLEND = 0.52
OI_BLEND = 0.48

# Contracts near this |delta| are used for the OI score; the ranking prefers this |delta|.
OI_DELTA_CENTER = 0.45
OI_CONTRACT_COUNT = 20
RANK_DELTA_CENTER = 0.42
AFFORDABLE_FRACTION = 0.95  # lot cost must be <= capital * this
WATCH_COUNT = 6             # contracts listed per side


def normalize_symbol(symbol: str) -> str:
    symbol = symbol.strip().upper()
    return SYMBOL_ALIASES.get(symbol, symbol)


def load_weights(path: str | Path | None = None) -> list[tuple[str, float]]:
    """Read a CSV with columns symbol,weight (percent). Defaults to the bundled table."""
    path = Path(path) if path else WEIGHTS_CSV
    rows: list[tuple[str, float]] = []
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            symbol = normalize_symbol(row.get("symbol") or row.get("Symbol") or "")
            weight = row.get("weight") or row.get("Weight") or row.get("weight_pct")
            if symbol and weight is not None:
                rows.append((symbol, float(str(weight).replace("%", ""))))
    if not rows:
        raise ValueError(f"No weights loaded from {path}")
    return rows
