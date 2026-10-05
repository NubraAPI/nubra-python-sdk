"""TOTP setup, step 2 of 4: enable TOTP on the account.
Type: mutating (UAT) - changes account security settings
Needs: interactive UAT login; the secret from step 1 loaded in your authenticator
Expect: the SDK prompts for a TOTP code and enables TOTP.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Use NubraEnv.UAT for testing. Switch to NubraEnv.PROD for live usage.
setup_client = InitNubraSdk(NubraEnv.UAT)
setup_client.totp_enable()
