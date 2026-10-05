"""TOTP setup, step 1 of 4: generate a TOTP secret.
Type: mutating (UAT) - changes account security settings
Needs: interactive UAT login (phone, OTP, MPIN)
Expect: prints the TOTP secret; add it to your authenticator app. Keep it private.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Use NubraEnv.UAT for testing. Switch to NubraEnv.PROD for live usage.
setup_client = InitNubraSdk(NubraEnv.UAT)
secret = setup_client.totp_generate_secret()
print("TOTP Secret:", secret)
