from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.trading.trading_data import NubraTrader

nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
trader = NubraTrader(nubra, version="V2")

margin = trader.get_margin({
    "with_portfolio": True,
    "with_legs": False,
    "is_basket": False,
    "order_req": {
        "exchange": "NSE",
        "orders": [
            {
                "ref_id": 1755599,
                "order_type": "ORDER_TYPE_REGULAR",
                "price_type": "LIMIT",
                "order_qty": 75,
                "order_price": 24500,
                "order_side": "ORDER_SIDE_BUY",
                "order_delivery_type": "ORDER_DELIVERY_TYPE_CNC",
                "validity_type": "IOC",
                "request_type": "ORDER_REQUEST_NEW"
            }
        ]
    }
})

print(margin.total_margin)
