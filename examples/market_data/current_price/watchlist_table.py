"""Print a multi-symbol watchlist with price and % change.

Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env (env_creds=True)
Expect: table of symbol, price, previous close (rupees) and % change, sorted by % change
Tested with: nubra-sdk 0.5.4 (UAT)
"""
import pandas as pd
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Default is the UAT sandbox. For live usage switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
market_data = MarketData(nubra)

watchlist = [("NIFTY", "NSE"), ("RELIANCE", "NSE"), ("HDFCBANK", "NSE"), ("INFY", "NSE"), ("SENSEX", "BSE")]

rows, failed = [], []
for symbol, exchange in watchlist:
    p = market_data.current_price(symbol, exchange=exchange)
    if p is None or not p.price:
        failed.append(f"{exchange}:{symbol}")
        continue
    rows.append({
        "symbol": symbol,
        "price": p.price / 100,  # API returns paise
        "prev_close": (p.prev_close or 0) / 100,
        "change_%": p.change if p.change is not None else
                    (round((p.price - p.prev_close) / p.prev_close * 100, 2) if p.prev_close else None),
    })

if rows:
    table = pd.DataFrame(rows).sort_values("change_%", ascending=False)
    print(table.to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
if failed:
    print(f"No price for: {', '.join(failed)}")
