"""Watch today's orders by polling and print each status change (no websocket needed).
Type: read-only
Needs: UAT login via env creds. To see changes, place or cancel an order from another script while it runs.
Expect: an initial count, then a line for each new order or status change over 30 seconds (polls every 3s).
Tested with: nubra-sdk 0.5.4 (UAT)
"""
import time
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.trading.trading_data import NubraTrader

# Use NubraEnv.UAT for testing. Switch to NubraEnv.PROD for live usage.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
trader = NubraTrader(nubra)

POLL_SECONDS, RUN_SECONDS = 3, 30


def snapshot():
    result = trader.orders()
    if not result:
        return {}
    return {o.intentOrderId: o for group in result.orders.values() for o in group}


last = snapshot()
print(f"Watching {len(last)} existing order(s) for {RUN_SECONDS}s...")

deadline = time.time() + RUN_SECONDS
while time.time() < deadline:
    time.sleep(POLL_SECONDS)
    current = snapshot()
    now = time.strftime("%H:%M:%S")
    for order_id, o in current.items():
        before = last.get(order_id)
        price = f"Rs {o.entryPrice / 100:,.2f}" if o.entryPrice else "market"
        if before is None:
            print(f"[{now}] NEW     {order_id} {o.side} {o.orderQty} @ {price} -> {o.status}")
        elif before.status != o.status or before.filledQty != o.filledQty:
            print(f"[{now}] CHANGED {order_id} {before.status} -> {o.status}, filled {o.filledQty}/{o.orderQty}")
            if o.rejectionMsg:
                print("  Rejected:", o.rejectionMsg)
    last = current
print("Done.")
