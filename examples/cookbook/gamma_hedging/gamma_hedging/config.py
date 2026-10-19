"""Configuration, loaded from environment variables (typically a `.env` file;
see `.env.example`).

The Nubra environment (UAT/PROD) and whether orders are actually sent are NOT
configured here. Both are command-line flags on main.py (`--env`,
`--allow-prod`, `--place-orders`).

Multiple strategies: `STRATEGIES` names one or more independent strategies
(comma-separated, default one named `strat1`). Each has its own setup structure,
futures hedge, thresholds and order tag. Every per-strategy setting can be
overridden with a `<NAME>_<KEY>` variable (for example `STRAT2_STRATEGY_TYPE`).
If that is not set it falls back to the plain `<KEY>` variable, then to the
default below. A single-strategy `.env` therefore needs no prefixes.

Some settings are account/session-level and live on `Config` directly:
underlying/exchange, the hedge rate limit, the kill switch settings, and
session/logging settings.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum

from dotenv import load_dotenv

load_dotenv()


def _env_str(name: str, default: str) -> str:
    return os.environ.get(name, default).strip()


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _env_str_over(prefixed_name: str, fallback_name: str, default: str) -> str:
    raw = os.environ.get(prefixed_name)
    if raw is not None and raw.strip() != "":
        return raw.strip()
    return _env_str(fallback_name, default)


def _env_float_over(prefixed_name: str, fallback_name: str, default: float) -> float:
    raw = os.environ.get(prefixed_name)
    if raw is not None and raw.strip() != "":
        return float(raw)
    return _env_float(fallback_name, default)


def _env_int_over(prefixed_name: str, fallback_name: str, default: int) -> int:
    raw = os.environ.get(prefixed_name)
    if raw is not None and raw.strip() != "":
        return int(raw)
    return _env_int(fallback_name, default)


class StrategyType(str, Enum):
    STRADDLE = "STRADDLE"
    STRANGLE = "STRANGLE"


class PriceType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


@dataclass(frozen=True)
class StrategyConfig:
    """One independently hedged strategy. `strat_tag` is sent as `stratTags` on
    every order for this strategy, so Nubra can attribute orders back to it.
    """

    name: str
    strategy_type: StrategyType
    setup_lots: int
    strangle_offset_strikes: int  # fallback only, used if delta data is unavailable
    strangle_target_delta: float  # only used when strategy_type == STRANGLE
    setup_price_type: PriceType
    delta_tolerance_lots: float
    high_gamma_threshold: float
    poll_interval_normal_sec: float
    poll_interval_high_gamma_sec: float
    hedge_price_type: PriceType
    max_futures_position_lots: int
    strat_tag: str


@dataclass(frozen=True)
class Config:
    # Instrument selection (shared across all strategies)
    underlying: str
    exchange: str
    expiry_override: str | None  # YYYYMMDD, or None for the nearest expiry

    strategies: list[StrategyConfig]

    # Risk guardrails, shared across all strategies
    max_hedge_trades_per_min: int
    circuit_breaker_pct: float
    circuit_breaker_window_sec: int
    max_consecutive_api_errors: int

    # Session bounds
    market_close_time: str  # "HH:MM" local
    timezone: str

    # Black-Scholes fallback
    risk_free_rate: float

    log_dir: str

    # How far beyond the reference price to place LIMIT orders so they cross the
    # book instead of resting at our own estimate. 0 = price exactly at the
    # reference. Applies to the setup order and futures hedge orders when their
    # price type is LIMIT.
    aggressive_fill_pct: float

    # Local browser dashboard port (served on 127.0.0.1)
    web_dashboard_port: int

    # Set from the command line in main.py, not from the environment.
    env_name: str = "UAT"
    place_orders: bool = False


def _load_strategy_config(name: str, global_strat_tag: str, is_only_strategy: bool) -> StrategyConfig:
    prefix = name.strip().upper()

    strategy_raw = _env_str_over(f"{prefix}_STRATEGY_TYPE", "STRATEGY_TYPE", "STRADDLE").upper()
    try:
        strategy_type = StrategyType(strategy_raw)
    except ValueError as exc:
        raise ValueError(
            f"{prefix}_STRATEGY_TYPE={strategy_raw!r} is invalid for strategy {name!r}. Use one of: "
            f"{', '.join(s.value for s in StrategyType)}"
        ) from exc

    setup_price_type = PriceType(_env_str_over(f"{prefix}_SETUP_PRICE_TYPE", "SETUP_PRICE_TYPE", "MARKET").upper())
    hedge_price_type = PriceType(_env_str_over(f"{prefix}_HEDGE_PRICE_TYPE", "HEDGE_PRICE_TYPE", "MARKET").upper())

    # One strategy keeps the plain tag; with several, each gets "<tag>-<name>"
    # by default so orders stay attributable per strategy.
    default_tag = global_strat_tag if is_only_strategy else f"{global_strat_tag}-{name}"

    return StrategyConfig(
        name=name,
        strategy_type=strategy_type,
        setup_lots=_env_int_over(f"{prefix}_SETUP_LOTS", "SETUP_LOTS", 1),
        strangle_offset_strikes=_env_int_over(f"{prefix}_STRANGLE_OFFSET_STRIKES", "STRANGLE_OFFSET_STRIKES", 2),
        strangle_target_delta=_env_float_over(f"{prefix}_STRANGLE_TARGET_DELTA", "STRANGLE_TARGET_DELTA", 0.20),
        setup_price_type=setup_price_type,
        # The hedge size is -round(net_delta / lot_size), so a band tighter than
        # half a lot can never produce a different trade.
        delta_tolerance_lots=_env_float_over(f"{prefix}_DELTA_TOLERANCE_LOTS", "DELTA_TOLERANCE_LOTS", 0.5),
        # Net gamma at or above this switches to the faster polling interval.
        high_gamma_threshold=_env_float_over(f"{prefix}_HIGH_GAMMA_THRESHOLD", "HIGH_GAMMA_THRESHOLD", 0.20),
        poll_interval_normal_sec=_env_float_over(f"{prefix}_POLL_INTERVAL_NORMAL_SEC", "POLL_INTERVAL_NORMAL_SEC", 30.0),
        poll_interval_high_gamma_sec=_env_float_over(
            f"{prefix}_POLL_INTERVAL_HIGH_GAMMA_SEC", "POLL_INTERVAL_HIGH_GAMMA_SEC", 7.0
        ),
        hedge_price_type=hedge_price_type,
        max_futures_position_lots=_env_int_over(f"{prefix}_MAX_FUTURES_POSITION_LOTS", "MAX_FUTURES_POSITION_LOTS", 20),
        strat_tag=os.environ.get(f"{prefix}_STRAT_TAG", "").strip() or default_tag,
    )


def load_config() -> Config:
    strategy_names = [s.strip() for s in _env_str("STRATEGIES", "strat1").split(",") if s.strip()]
    if not strategy_names:
        raise ValueError("STRATEGIES must name at least one strategy (comma-separated).")
    if len(set(n.upper() for n in strategy_names)) != len(strategy_names):
        raise ValueError(f"STRATEGIES={strategy_names!r} has duplicate names (case-insensitive); each must be unique.")

    global_strat_tag = _env_str("STRAT_TAG", "gamma-hedge")
    only_one = len(strategy_names) == 1
    strategies = [_load_strategy_config(name, global_strat_tag, only_one) for name in strategy_names]

    return Config(
        underlying=_env_str("UNDERLYING", "SENSEX"),
        exchange=_env_str("EXCHANGE", "BSE"),
        expiry_override=os.environ.get("EXPIRY_OVERRIDE", "").strip() or None,
        strategies=strategies,
        max_hedge_trades_per_min=_env_int("MAX_HEDGE_TRADES_PER_MIN", 4),
        circuit_breaker_pct=_env_float("CIRCUIT_BREAKER_PCT", 1.5),
        circuit_breaker_window_sec=_env_int("CIRCUIT_BREAKER_WINDOW_SEC", 300),
        max_consecutive_api_errors=_env_int("MAX_CONSECUTIVE_API_ERRORS", 3),
        market_close_time=_env_str("MARKET_CLOSE_TIME", "15:30"),
        timezone=_env_str("TIMEZONE", "Asia/Kolkata"),
        risk_free_rate=_env_float("RISK_FREE_RATE", 0.065),
        log_dir=_env_str("LOG_DIR", "logs"),
        aggressive_fill_pct=_env_float("AGGRESSIVE_FILL_PCT", 0.0),
        web_dashboard_port=_env_int("WEB_DASHBOARD_PORT", 8765),
    )
