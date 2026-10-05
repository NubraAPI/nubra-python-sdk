"""List today's orders by bucket, plus status/exchange/delivery/tag filters.
Type: read-only
Needs: UAT login via env creds
Expect: a count per bucket (open, executed, ...) and one line per order with price in rupees.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.trading.trading_data import NubraTrader

# Use NubraEnv.UAT for testing. Switch to NubraEnv.PROD for live usage.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
trader = NubraTrader(nubra)

all_orders = trader.orders()
open_orders = trader.orders(status="OPEN")  # OPEN, EXECUTED, REJECTED, GTE, CANCELLED, EXPIRED
nse_orders = trader.orders(exchange="NSE")
iday_orders = trader.orders(delivery_type="IDAY")
tagged_orders = trader.orders(strat_tags="python-sdk-v3-basic-usage")  # one tag or a list of tags

# Orders come grouped by bucket (open, executed, cancelled, rejected, expired, gtt).
for group_name, order_list in all_orders.orders.items():
    print(group_name, len(order_list))
    for order in order_list:
        price = f"Rs {order.entryPrice / 100:.2f}" if order.entryPrice else "market"
        print(order.intentOrderId, order.status, f"{order.filledQty}/{order.orderQty}", price)
        if order.rejectionMsg:
            print("  Rejected:", order.rejectionMsg)
