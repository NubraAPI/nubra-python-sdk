"""Quick start: log in and create the four main SDK clients.
Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env
Expect: a confirmation line once the clients are created.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.refdata.instruments import InstrumentData
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.trading.trading_data import NubraTrader

# Use NubraEnv.UAT for sandbox testing. Switch to NubraEnv.PROD for live usage.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

instruments = InstrumentData(nubra)
market_data = MarketData(nubra)
trader = NubraTrader(nubra)
print("Logged in. Ready: InstrumentData, MarketData, NubraTrader.")
