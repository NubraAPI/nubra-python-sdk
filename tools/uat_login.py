"""One-time interactive UAT login for testing the examples.

Run from the repo root so the SDK's session store (auth_data.db) lands here:

    py -3.12 tools/uat_login.py

You will be prompted for phone number, OTP and MPIN (or put PHONE_NO and MPIN
in a local .env and the script will only ask for the OTP). The session is
saved by the SDK and reused by later runs from the same folder.
"""
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

# Hard-wired to UAT on purpose: this script must never log in to PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

# Quick proof the session works.
print(MarketData(nubra).current_price("HDFCBANK", exchange="NSE"))
print("UAT login OK - session saved in auth_data.db")
