"""List strategy (multi-leg) orders for a strat tag with their legs.
Type: read-only
Needs: UAT login via env creds; an earlier strategy order with this tag
Expect: one line per strategy order, then its legs. Prints nothing if the tag has no strategy orders.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.trading.trading_data import NubraTrader

# Use NubraEnv.UAT for testing. Switch to NubraEnv.PROD for live usage.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
trader = NubraTrader(nubra)

STRATEGY_TAG = "python-sdk-v3-nifty-buy-straddle"  # tag used when the strategy was placed

# Strategy orders are fetched with the normal orders() call; filter by tag.
result = trader.orders(strat_tags=STRATEGY_TAG)

for group_name, order_list in result.orders.items():
    for order in order_list:
        if not order.isMulti:
            continue
        print(group_name, order.intentOrderId, order.status, f"net Rs {(order.entryPrice or 0) / 100:.2f}", order.stratTags)
        if order.rejectionMsg:
            print("  Rejected:", order.rejectionMsg)
        for leg in order.legs:
            print("  leg", leg.refId, leg.unitQty, leg.orderQty, leg.filledQty)
