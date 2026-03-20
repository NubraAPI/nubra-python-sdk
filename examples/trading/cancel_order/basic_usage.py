from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.trading.trading_data import NubraTrader

nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
trader = NubraTrader(nubra, version="V2")

ORDER_ID = 0  # Replace with your UAT order id.

result = trader.cancel_orders_v2(order_ids=[ORDER_ID])
print(result)
