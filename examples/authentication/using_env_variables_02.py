"""Log in using PHONE_NO and MPIN from .env.
Type: read-only
Needs: PHONE_NO / MPIN in .env (OTP is still prompted)
Expect: no output; `nubra` is an authenticated client.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Reads PHONE_NO and MPIN from a local .env file (OTP is still prompted).
# Use NubraEnv.UAT for testing. Switch to NubraEnv.PROD for live usage.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
