"""Show how to pick UAT (sandbox) or PROD (live) explicitly.
Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env (PROD needs a live account)
Expect: a line naming the environment in use.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# UAT: sandbox testing (default for these examples).
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
print("Connected to the UAT sandbox.")

# PROD: live trading. Uncomment to switch, and keep the environment explicit in code.
# nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)
