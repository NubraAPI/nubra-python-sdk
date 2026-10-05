"""Log out (clear the saved session) and log in again.
Type: read-only (resets your local session only)
Needs: UAT login via PHONE_NO / MPIN in .env; expect a fresh OTP prompt after logout
Expect: "Logged in", "Logged out", then "Logged in again".
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Use NubraEnv.UAT for testing. Switch to NubraEnv.PROD for live usage.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
print("Logged in.")

# logout() clears the active session; the next init needs the full login flow.
nubra.logout()
print("Logged out.")

nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
print("Logged in again.")
