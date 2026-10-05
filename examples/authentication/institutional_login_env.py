"""Institutional login using credentials stored in .env.
Type: read-only
Needs: CLIENT_CODE, EXCHANGE_CLIENT_CODE, USERNAME, PASSWORD, MPIN in .env
Expect: no output; `nubra` is an authenticated client.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Reads CLIENT_CODE, EXCHANGE_CLIENT_CODE, USERNAME, PASSWORD and MPIN
# from a local .env file.
# Use NubraEnv.UAT for testing. Switch to NubraEnv.PROD for live usage.
nubra = InitNubraSdk(NubraEnv.UAT, insti_login=True, env_creds=True)

# Institutional clients can change their password after authentication.
# nubra.reset_password()
