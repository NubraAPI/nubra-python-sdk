from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.trading.trading_data import NubraTrader

nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
trader = NubraTrader(nubra, version="V2")

result = trader.multi_order([
    {
        "ref_id": 12345,
        "order_type": "ORDER_TYPE_REGULAR",
        "order_qty": 1,
        "order_side": "ORDER_SIDE_BUY",
        "order_delivery_type": "ORDER_DELIVERY_TYPE_CNC",
        "validity_type": "DAY",
        "price_type": "LIMIT",
        "order_price": 15000,
        "exchange": "NSE"
    },
    {
        "ref_id": 23456,
        "order_type": "ORDER_TYPE_REGULAR",
        "order_qty": 1,
        "order_side": "ORDER_SIDE_SELL",
        "order_delivery_type": "ORDER_DELIVERY_TYPE_IDAY",
        "validity_type": "DAY",
        "price_type": "LIMIT",
        "order_price": 24500,
        "exchange": "NSE"
    }
])

print(result.orders)
