from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.trading.trading_data import NubraTrader

nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
trader = NubraTrader(nubra, version="V2")

ORDER_ID = 0  # Replace with your UAT order id.

result = trader.modify_order_v2(
    order_id=ORDER_ID,
    request={
        "order_price": 134400,
        "order_qty": 1,
        "exchange": "NSE",
        "order_type": "ORDER_TYPE_STOPLOSS",
        "algo_params": {"trigger_price": 134390},
    },
)

print(result)
