"""Contract-symbol and expiry-date helpers (pure functions, no network).

Symbol conventions used by this example (verify a new underlying yourself;
an unknown symbol returns an empty series rather than an error):
  weekly option : <UND><YY><month 1-9/O/N/D><DD><strike><CE|PE>  e.g. NIFTY2670725700CE
  monthly option: <UND><YY><MMM><strike><CE|PE>                  e.g. NIFTY26JUN25300CE
  futures       : <UND><YY><MMM>FUT                              e.g. NIFTY26SEPFUT
The monthly expiry is the last occurrence of the expiry weekday in the month.
"""
import pandas as pd

MONTH_ABBR = {1: "JAN", 2: "FEB", 3: "MAR", 4: "APR", 5: "MAY", 6: "JUN",
              7: "JUL", 8: "AUG", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DEC"}
MONTH_DIGIT = {10: "O", 11: "N", 12: "D"}


def is_monthly_expiry(expiry: pd.Timestamp) -> bool:
    """True if `expiry` is the last occurrence of its weekday in the month."""
    return (expiry + pd.Timedelta(days=7)).month != expiry.month


def option_symbol(underlying: str, expiry: pd.Timestamp, strike: int, option_type: str) -> str:
    assert option_type in ("CE", "PE")
    yy = expiry.strftime("%y")
    if is_monthly_expiry(expiry):
        code = f"{yy}{MONTH_ABBR[expiry.month]}"
    else:
        code = f"{yy}{MONTH_DIGIT.get(expiry.month, str(expiry.month))}{expiry.strftime('%d')}"
    return f"{underlying}{code}{int(strike)}{option_type}"


def monthly_expiry(year: int, month: int, weekday: int) -> pd.Timestamp:
    """Last date in the month falling on `weekday` (Mon=0 ... Sun=6)."""
    last = pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(0)
    return last - pd.Timedelta(days=(last.weekday() - weekday) % 7)


def front_futures(underlying: str, on_date: pd.Timestamp, weekday: int) -> tuple[str, pd.Timestamp]:
    """Nearest not-yet-expired monthly futures contract as of `on_date`.

    Returns (symbol, contract_expiry). A contract is held until its own expiry
    date, so on the monthly expiry day the expiring contract is still used.
    """
    exp = monthly_expiry(on_date.year, on_date.month, weekday)
    if exp < on_date:
        nxt = on_date + pd.offsets.MonthBegin(1)
        exp = monthly_expiry(nxt.year, nxt.month, weekday)
    return f"{underlying}{exp.strftime('%y')}{MONTH_ABBR[exp.month]}FUT", exp


def round_to_strike_step(spot: float, step: int) -> int:
    return int(round(spot / step) * step)


def expiries_between(start: pd.Timestamp, end: pd.Timestamp, weekday: int) -> list:
    """Every date in [start, end] that falls on the expiry weekday.

    Exchange holidays are not modelled: an expiry that was shifted by a holiday
    simply returns no data and is reported as skipped.
    """
    return [d for d in pd.date_range(start, end, freq="D") if d.weekday() == weekday]


def entry_day_for(expiry: pd.Timestamp) -> pd.Timestamp:
    """Previous weekday (Mon-Fri) before the expiry date."""
    d = expiry - pd.Timedelta(days=1)
    while d.weekday() >= 5:
        d -= pd.Timedelta(days=1)
    return d
