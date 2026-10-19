"""Log in with an authenticator-app TOTP code instead of an SMS OTP.

Type: read-only
Needs: a UAT account with TOTP already enabled; PHONE_NO / MPIN in .env (env_creds=True); you type the 6-digit TOTP
Expect: a "Enter TOTP" prompt, then "Login successful"; `nubra` is an authenticated client.

Pass totp_login=True and the SDK asks for the current 6-digit code from your authenticator app, then verifies the MPIN.
To enable TOTP on an account the SDK provides `nubra.totp_generate_secret()` (returns the secret to add to your
authenticator app) and `nubra.totp_enable()` (asks for the MPIN and a first TOTP code to confirm). Run those once,
deliberately: they change the account's login settings. For unattended runs see totp_login_headless.py.
"""
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# UAT by default. To use production, switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, totp_login=True, env_creds=True)
