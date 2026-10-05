"""Show the top-5 order book for the nearest CRUDEOIL MCX future.

Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env (env_creds=True)
Expect: contract name, last traded price and 5 bid / ask levels in rupees
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from datetime import date

from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.refdata.instruments import InstrumentData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# MCX is available on UAT. Switch to NubraEnv.PROD for live usage.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
instruments = InstrumentData(nubra)
market_data = MarketData(nubra)

# Pick the nearest unexpired CRUDEOIL future from the instrument master, e.g. FUT_CRUDEOIL_20261019.
today = int(date.today().strftime("%Y%m%d"))
mcx = instruments.get_instruments_dataframe(exchange="MCX")
futures = mcx[(mcx["asset"] == "CRUDEOIL") & (mcx["derivative_type"] == "FUT") & (mcx["expiry"].astype(int) > today)]
futures = futures.sort_values("expiry")
if futures.empty:
    raise SystemExit("No live CRUDEOIL future found in the MCX instrument master")
ref_id = int(futures.iloc[0]["ref_id"])

# quote() needs a ref_id.
quote = market_data.quote(ref_id=ref_id, levels=5)

if quote is None:
    raise SystemExit("No quote returned (market data unavailable for this instrument)")

book = quote.orderBook
print(f"{futures.iloc[0]['stock_name']} last traded price: Rs {book.last_traded_price / 100:,.2f}  volume: {book.volume}")
print(f"{'BID qty':>10} {'BID Rs':>10} | {'ASK Rs':>10} {'ASK qty':>10}")
for bid, ask in zip(book.bid or [], book.ask or []):
    print(f"{bid.quantity:>10} {bid.price / 100:>10,.2f} | {ask.price / 100:>10,.2f} {ask.quantity:>10}")
