"""Log in with credentials from .env and keep the client for other modules.
Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env (OTP is prompted unless cached)
Expect: no output; `nubra` is ready to pass to InstrumentData, MarketData, etc.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Use NubraEnv.UAT for testing. Switch to NubraEnv.PROD for live usage.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

# Reuse the authenticated client across modules.
# Example:
# from nubra_python_sdk.refdata.instruments import InstrumentData
# from nubra_python_sdk.marketdata.market_data import MarketData
# from nubra_python_sdk.trading.trading_data import NubraTrader
# instruments = InstrumentData(nubra)
# market_data = MarketData(nubra)
# trader = NubraTrader(nubra)

# Optional. logout() sends POST /logout to the server, deletes the auth_data.db* files
# in the current folder, and clears the in-memory tokens and headers.
# The next InitNubraSdk call needs a full login again.
# nubra.logout()
