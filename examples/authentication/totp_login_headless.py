"""Log in with a TOTP code generated in code (pyotp), so a scheduled or headless process needs no typing.

Type: read-only
Needs: a UAT account with TOTP enabled; PHONE_NO / MPIN in .env; TOTP_SECRET (the base32 secret) in the environment;
       `pip install pyotp`
Expect: "Login successful" with no prompt; `nubra` is an authenticated client.

The SDK's totp_login=True flow reads the code with input(). This example answers only that one prompt with a code
from pyotp and leaves every other prompt untouched, so a missing PHONE_NO / MPIN still fails loudly instead of hanging.
It is an adaptation, not an SDK feature: the SDK has no built-in hook for supplying the code.

Keep TOTP_SECRET in an environment variable or a secrets manager, never in source or in git. Anyone holding the
secret and your MPIN can log in as you.
"""
import builtins
import os

import pyotp
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

secret = os.environ.get("TOTP_SECRET")
if not secret:
    raise SystemExit("Set the TOTP_SECRET environment variable (the base32 secret from your authenticator setup).")

_original_input = builtins.input


def input_with_totp(prompt=""):
    if "TOTP" in str(prompt):
        return pyotp.TOTP(secret).now()
    return _original_input(prompt)


builtins.input = input_with_totp
try:
    # UAT by default. To use production, switch to NubraEnv.PROD.
    nubra = InitNubraSdk(NubraEnv.UAT, totp_login=True, env_creds=True)
finally:
    builtins.input = _original_input
