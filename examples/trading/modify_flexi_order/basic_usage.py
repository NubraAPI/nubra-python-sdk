from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.trading.trading_data import NubraTrader

nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
trader = NubraTrader(nubra, version="V2")

BASKET_ID = 0  # Replace with your UAT flexi basket id.

result = trader.mod_flexi_order(
    basket_id=BASKET_ID,
    request={
        "exchange": "NSE",
        "orders": [{"ref_id": 69353}],
        "basket_params": {
            "order_side": "ORDER_SIDE_BUY",
            "order_delivery_type": "ORDER_DELIVERY_TYPE_CNC",
            "price_type": "LIMIT",
            "multiplier": 2,
            "entry_price": 72000,
        }
    }
)

print(result)
