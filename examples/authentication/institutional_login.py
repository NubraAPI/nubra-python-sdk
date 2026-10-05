"""Institutional login with interactive prompts.
Type: read-only
Needs: institutional account; you type exchange client code, client code, username, password, MPIN
Expect: no output; `nubra` is an authenticated client.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Institutional login: exchange client code, client code, username,
# password and MPIN. The SDK prompts for these values.
# Use NubraEnv.UAT for testing. Switch to NubraEnv.PROD for live usage.
nubra = InitNubraSdk(NubraEnv.UAT, insti_login=True)
