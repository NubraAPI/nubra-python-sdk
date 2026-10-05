"""Print today's orders as a readable table (id, symbol, side, qty, price in rupees, status).
Type: read-only
Needs: UAT login via env creds
Expect: one row per order, newest first, then a count by status. Rejected orders show the reason.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from collections import Counter
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.trading.trading_data import NubraTrader

# Use NubraEnv.UAT for testing. Switch to NubraEnv.PROD for live usage.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
trader = NubraTrader(nubra)

result = trader.orders()
orders = [o for group in result.orders.values() for o in group] if result else []
if not orders:
    raise SystemExit("No orders today.")

print(f"{'order id':>12}  {'symbol':<22} {'side':<4} {'qty':>6}  {'price (Rs)':>11}  status")
for o in sorted(orders, key=lambda o: o.intentOrderId, reverse=True):
    if o.isMulti:
        symbol = f"strategy ({len(o.legs)} legs)"
    else:
        symbol = o.refData.displayName if o.refData and o.refData.displayName else str(o.refId)
    price = f"{o.entryPrice / 100:,.2f}" if o.entryPrice else "market"
    print(f"{o.intentOrderId:>12}  {symbol[:22]:<22} {o.side or '-':<4} {o.orderQty or 0:>6}  {price:>11}  {o.status}")
    if o.rejectionMsg:
        print(f"{'':>14}reason: {o.rejectionMsg}")

print(dict(Counter(o.status for o in orders)))
