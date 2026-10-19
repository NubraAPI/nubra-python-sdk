# Authentication examples

Default environment is UAT. Switch to `NubraEnv.PROD` for live usage.

| File | What it does | Type |
| --- | --- | --- |
| `basic_usage.py` | Log in from `.env` and reuse the client | read-only |
| `using_env_variables_02.py` | Log in with PHONE_NO / MPIN from `.env` | read-only |
| `otp_login.py` | Interactive phone + OTP + MPIN login | read-only |
| `logout_and_relogin.py` | Clear the session with `logout()` and log in again | read-only |
| `institutional_login.py` | Institutional login with prompts | read-only |
| `institutional_login_env.py` | Institutional login from `.env` | read-only |
| `totp_login.py` | Log in with an authenticator-app TOTP code (`totp_login=True`) | read-only |
| `totp_login_headless.py` | Supply the TOTP code from `pyotp` so a scheduled process needs no typing | read-only |
