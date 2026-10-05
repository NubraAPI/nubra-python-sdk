"""TOTP setup, step 3 of 4: log in with TOTP instead of OTP.
Type: read-only
Needs: TOTP already enabled (step 2)
Expect: no output; `nubra` is an authenticated client.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Use NubraEnv.UAT for testing. Switch to NubraEnv.PROD for live usage.
nubra = InitNubraSdk(NubraEnv.UAT, totp_login=True)
