"""Measure bid-ask spread and order-book imbalance from 5-level market depth.

Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env (env_creds=True)
Expect: best bid/ask (rupees), spread, total bid vs ask quantity and an imbalance %
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.refdata.instruments import InstrumentData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Default is the UAT sandbox. For live usage switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
instruments = InstrumentData(nubra)
market_data = MarketData(nubra)

SYMBOL = "RELIANCE"
instrument = instruments.get_instrument_by_symbol(SYMBOL, exchange="NSE")
if isinstance(instrument, dict):  # not found -> {"msg": ...}
    raise SystemExit(f"Lookup failed: {instrument.get('msg')}")

quote = market_data.quote(ref_id=instrument.ref_id, levels=5)
if quote is None:
    raise SystemExit("No quote returned (market data unavailable for this instrument)")

book = quote.orderBook
if not book.bid or not book.ask:
    raise SystemExit(f"{SYMBOL}: order book is empty (market closed or no resting orders)")

best_bid, best_ask = book.bid[0].price, book.ask[0].price  # paise
bid_qty = sum(level.quantity for level in book.bid)
ask_qty = sum(level.quantity for level in book.ask)
imbalance = (bid_qty - ask_qty) / (bid_qty + ask_qty) * 100 if bid_qty + ask_qty else 0.0

print(f"{SYMBOL} LTP Rs {book.last_traded_price / 100:,.2f}")
print(f"Best bid Rs {best_bid / 100:,.2f} | best ask Rs {best_ask / 100:,.2f} | "
      f"spread Rs {(best_ask - best_bid) / 100:,.2f}")
print(f"Depth (5 levels): bid qty {bid_qty:,} vs ask qty {ask_qty:,} | imbalance {imbalance:+.1f}% "
      f"({'buyers heavier' if imbalance > 0 else 'sellers heavier' if imbalance < 0 else 'balanced'})")
