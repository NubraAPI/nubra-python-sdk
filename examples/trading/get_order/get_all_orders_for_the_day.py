from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.trading.trading_data import NubraTrader

nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
trader = NubraTrader(nubra, version="V2")

result = trader.orders()
live_orders = trader.orders(live=True)
executed_orders = trader.orders(executed=True)
tagged_orders = trader.orders(tag="example_single_order")
