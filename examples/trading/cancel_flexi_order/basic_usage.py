from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.trading.trading_data import NubraTrader

nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
trader = NubraTrader(nubra, version="V2")

BASKET_ID = 0  # Replace with your UAT flexi basket id.

result = trader.cancel_flexi_order(BASKET_ID, "NSE")
print(result)
