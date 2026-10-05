# Schema Reference: Sdk Surface

Original source path: `authentication/sdk_surface.py`

```python
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# NubraEnv.UAT for sandbox testing, NubraEnv.PROD for live usage.
InitNubraSdk(
    env: NubraEnv,
    env_creds: bool = False,
    insti_login: bool = False,
)

# Session helpers on the initialized client:
# nubra.logout()          # clears the active session
# nubra.reset_password()  # institutional clients only (insti_login=True)
```

Authentication modes:

| Mode | Trigger | Inputs |
| --- | --- | --- |
| OTP login | default | phone number, OTP, MPIN |
| Institutional login | `insti_login=True` | exchange client code, client code, username, password, MPIN |
| `.env` assisted | `env_creds=True` | `PHONE_NO`/`MPIN` (OTP login) or `CLIENT_CODE`/`EXCHANGE_CLIENT_CODE`/`USERNAME`/`PASSWORD`/`MPIN` (institutional) |
