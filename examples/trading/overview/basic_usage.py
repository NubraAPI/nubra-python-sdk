"""Minimal setup: log in and create the NubraTrader used by every trading example.
Type: read-only
Needs: UAT login via env creds
Expect: a one-line confirmation. No orders are placed.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.trading.trading_data import NubraTrader

# Use NubraEnv.UAT for testing. Switch to NubraEnv.PROD for live usage.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
trader = NubraTrader(nubra)
print("Logged in. NubraTrader is ready (UAT).")
