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
# instruments = InstrumentData(nubra)
# market_data = MarketData(nubra)
# trader = NubraTrader(nubra)

# Fully reset the session when you are done (optional).
# nubra.logout()
