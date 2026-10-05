"""TOTP setup, step 4 of 4: disable TOTP on the account.
Type: mutating (UAT) - changes account security settings
Needs: interactive UAT login
Expect: the SDK disables TOTP; OTP login is used again.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Use NubraEnv.UAT for testing. Switch to NubraEnv.PROD for live usage.
nubra = InitNubraSdk(NubraEnv.UAT)
nubra.totp_disable()
