"""Nubra SDK plumbing: login, instrument lookup, expiry discovery and option-chain snapshots."""
from __future__ import annotations

from datetime import date
from typing import Any

from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.refdata.instruments import InstrumentData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

from .config import normalize_symbol
from .models import OptionContract
from .oi_change import parse_option_chain


def login(args: Any) -> Any:
    """Log in with PHONE_NO / MPIN from .env (SDK institutional fields with --insti-login)."""
    # UAT by default. To use production, switch to NubraEnv.PROD (here: --env PROD).
    env = NubraEnv.PROD if args.env == "PROD" else NubraEnv.UAT
    return InitNubraSdk(env, totp_login=args.totp_login, env_creds=True, insti_login=args.insti_login)


def instrument_ref(instruments: InstrumentData, symbol: str) -> int | None:
    """ref_id for an NSE equity symbol, or None if the instrument master does not list it."""
    symbol = normalize_symbol(symbol)
    for key in (symbol, symbol.replace("&", "AND")):
        instrument = instruments.get_instrument_by_symbol(key, exchange="NSE")
        if not isinstance(instrument, dict):  # not found -> {"msg": "..."}
            return int(instrument.ref_id)
    return None


def nearest_expiry(expiries: list[str], today: date | None = None) -> str | None:
    """Earliest expiry (YYYYMMDD string) that is today or later, else None."""
    today_text = (today or date.today()).strftime("%Y%m%d")
    upcoming = sorted(e for e in expiries if e >= today_text)
    return upcoming[0] if upcoming else None


def discover_expiry(market_data: MarketData) -> str:
    """Nearest upcoming NIFTY expiry from the option chain's expiry list."""
    first = market_data.option_chain("NIFTY", exchange="NSE")
    if first is None:
        raise RuntimeError("No NIFTY option chain returned; pass --expiry YYYYMMDD")
    expiry = nearest_expiry(first.chain.all_expiries)
    if expiry is None:
        raise RuntimeError("No upcoming NIFTY expiry found; pass --expiry YYYYMMDD")
    return expiry


def fetch_option_chain_snapshot(market_data: MarketData, expiry: str) -> list[OptionContract]:
    result = market_data.option_chain("NIFTY", expiry=expiry, exchange="NSE")
    return [] if result is None else parse_option_chain(result)
