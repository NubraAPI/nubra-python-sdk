"""Show the top-5 order book (market depth) for HDFCBANK on BSE.

Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env (env_creds=True)
Expect: last traded price and 5 bid / ask levels in rupees
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.refdata.instruments import InstrumentData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Default is the UAT sandbox. For live usage switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
instruments = InstrumentData(nubra)
market_data = MarketData(nubra)

# quote() needs a ref_id, so resolve the symbol first.
instrument = instruments.get_instrument_by_symbol("HDFCBANK", exchange="BSE")
if isinstance(instrument, dict):  # not found -> {"msg": ...}
    raise SystemExit(f"Lookup failed: {instrument.get('msg')}")
quote = market_data.quote(ref_id=instrument.ref_id, levels=5)

if quote is None:
    raise SystemExit("No quote returned (market data unavailable for this instrument)")

book = quote.orderBook
print(f"HDFCBANK last traded price: Rs {book.last_traded_price / 100:,.2f}  volume: {book.volume}")
print(f"{'BID qty':>10} {'BID Rs':>10} | {'ASK Rs':>10} {'ASK qty':>10}")
for bid, ask in zip(book.bid or [], book.ask or []):
    print(f"{bid.quantity:>10} {bid.price / 100:>10,.2f} | {ask.price / 100:>10,.2f} {ask.quantity:>10}")
