from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.trading.trading_data import NubraTrader

nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
trader = NubraTrader(nubra, version="V2")

result = trader.flexi_order({
    "exchange": "NSE",
    "basket_name": "OptionBasket",
    "order_type": "ORDER_TYPE_LIMIT",
    "tag": "flexi_example",
    "orders": [
        {
            "ref_id": 69353,
            "order_qty": 1,
            "order_side": "ORDER_SIDE_BUY"
        }
    ],
    "basket_params": {
        "order_side": "ORDER_SIDE_BUY",
        "order_delivery_type": "ORDER_DELIVERY_TYPE_CNC",
        "price_type": "LIMIT",
        "entry_price": 72500,
        "momentum_trigger_price": 72600,
        "exit_price": 74000,
        "stoploss_price": 71000,
        "entry_time": "2026-03-20T09:10:00.000Z",
        "exit_time" : "2026-03-20T09:30:00.000Z",
        "multiplier": 2
    }
})

print(result.basket_id)
