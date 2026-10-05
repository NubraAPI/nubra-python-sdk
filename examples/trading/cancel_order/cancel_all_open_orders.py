"""Cancel every open order on the account in one go (UAT cleanup helper).
Type: mutating (UAT) - cancels ALL open orders, not only ones from these examples
Needs: UAT login via env creds. Set TAG below to cancel only orders carrying that strat tag.
Expect: a table of the open orders being cancelled, the cancel acknowledgement, then how many are still open.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
import time
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.trading.trading_data import NubraTrader

# Use NubraEnv.UAT for testing. Switch to NubraEnv.PROD for live usage (this cancels real orders there).
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
trader = NubraTrader(nubra)

TAG = None  # e.g. "python-sdk-v3-basic-usage" to limit the cleanup to one tag
TERMINAL = ("EXECUTED", "REJECTED", "CANCELLED", "EXPIRED")


def working_orders():
    result = trader.orders(strat_tags=TAG) if TAG else trader.orders()
    if not result:
        return []
    # Everything not finished: OPEN orders plus pending GTE (good-till-expiry) orders.
    return [o for group in result.orders.values() for o in group if o.status not in TERMINAL]


open_orders = working_orders()
if not open_orders:
    print("No open orders to cancel.")
    raise SystemExit(0)  # nothing to do is a normal outcome, not an error

print(f"{'order id':>12}  {'side':<4} {'qty':>5}  {'price':>12}  status")
for o in open_orders:
    price = f"Rs {o.entryPrice / 100:,.2f}" if o.entryPrice else "market"
    print(f"{o.intentOrderId:>12}  {o.side or '-':<4} {o.orderQty or 0:>5}  {price:>12}  {o.status}")

ids = [o.intentOrderId for o in open_orders]
for i in range(0, len(ids), 20):  # cancel in small batches
    print("Cancel:", trader.cancel_orders_sentinel([{"orderId": oid} for oid in ids[i:i + 20]]))

time.sleep(3)
left = working_orders()
print(f"Cancelled {len(ids) - len(left)} of {len(ids)}; {len(left)} still open.")
for o in left:  # e.g. an order the exchange was still processing; run again in a few seconds
    print("  still open:", o.intentOrderId, o.status, o.rejectionMsg or "")
