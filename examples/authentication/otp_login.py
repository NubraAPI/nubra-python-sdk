"""Interactive phone + OTP + MPIN login.
Type: read-only
Needs: a UAT account; you type phone number, OTP and MPIN when prompted
Expect: no output; `nubra` is an authenticated client.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Use NubraEnv.UAT for testing. Switch to NubraEnv.PROD for live usage.
# The SDK prompts for phone number, OTP and MPIN.
nubra = InitNubraSdk(NubraEnv.UAT)
