# 1. Authentication

Every login flow the SDK supports, from `.env` OTP login to institutional accounts.

[Home](README.md) | [← Previous: 0. Setup](00-setup.md) | [Next: 2. Instruments →](02-instruments.md)

## In this guide

- Log in with `.env` credentials, interactively, or as an institution.
- What the SDK saves between runs and how `logout()` resets it.
- Select UAT or PROD explicitly.
- Create the main clients in one script.

## You need

A working `.env` and Python install from [0. Setup](00-setup.md). All examples here use UAT. Run them from the repo root.

## Login flows at a glance

| Flow | Call | You provide | Example |
| --- | --- | --- | --- |
| `.env` login | `InitNubraSdk(NubraEnv.UAT, env_creds=True)` | `PHONE_NO`, `MPIN` in `.env`; OTP when prompted | `basic_usage.py` |
| Interactive OTP | `InitNubraSdk(NubraEnv.UAT)` | phone, OTP, MPIN typed at prompts | `otp_login.py` |
| Institutional | `InitNubraSdk(NubraEnv.UAT, insti_login=True)` | exchange client code, client code, username, password, MPIN | `institutional_login.py` |

## The examples, in order

### 1. Log in from .env and reuse the client: [`basic_usage.py`](../../examples/authentication/basic_usage.py)

The standard start of any script. The client it returns is passed to every other class, so you log in once per script. Type: read-only.

```python
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

# Reuse the authenticated client across modules.
# Example:
# instruments = InstrumentData(nubra)
# market_data = MarketData(nubra)
# trader = NubraTrader(nubra)
```

Run: `py -3.12 examples/authentication/basic_usage.py`

Real output: none. The example prints nothing; success means no error. (The OTP is prompted unless a valid session is cached.)

### 2. Same call, documented: [`using_env_variables_02.py`](../../examples/authentication/using_env_variables_02.py)

Identical call. It spells out that `PHONE_NO` and `MPIN` come from `.env` and the OTP is still prompted.

```python
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
```

Run: `py -3.12 examples/authentication/using_env_variables_02.py`

Real output: none (the UAT run completed with no output).

### 3. Interactive login: [`otp_login.py`](../../examples/authentication/otp_login.py)

No `.env` needed. The SDK asks for phone number, OTP and MPIN. Useful on a shared machine where you do not want credentials on disk.

```python
nubra = InitNubraSdk(NubraEnv.UAT)
```

Run: `py -3.12 examples/authentication/otp_login.py`

Expect: three prompts (phone, OTP, MPIN), then no output. It needs a human at the keyboard, so there is no recorded run.

### 4. Logout and log in again: [`logout_and_relogin.py`](../../examples/authentication/logout_and_relogin.py)

The SDK saves your session in `auth_data.db` in the current folder, so a second run usually skips the OTP. `logout()` clears it, so the next init goes through the full flow. Use it when switching accounts or environments.

```python
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
print("Logged in.")

# logout() clears the active session; the next init needs the full login flow.
nubra.logout()
print("Logged out.")

nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
print("Logged in again.")
```

Run: `py -3.12 examples/authentication/logout_and_relogin.py`

Expect: "Logged in.", "Logged out.", a fresh OTP prompt, then "Logged in again." (interactive, no recorded run).

### 5. Institutional login: [`institutional_login.py`](../../examples/authentication/institutional_login.py) and [`institutional_login_env.py`](../../examples/authentication/institutional_login_env.py)

For institutional accounts. The first prompts for exchange client code, client code, username, password and MPIN. The second reads `CLIENT_CODE`, `EXCHANGE_CLIENT_CODE`, `USERNAME`, `PASSWORD` and `MPIN` from `.env`.

```python
nubra = InitNubraSdk(NubraEnv.UAT, insti_login=True)
# or, from .env:
nubra = InitNubraSdk(NubraEnv.UAT, insti_login=True, env_creds=True)
```

Run: `py -3.12 examples/authentication/institutional_login.py` or `py -3.12 examples/authentication/institutional_login_env.py`

Expect: no output; `nubra` is an authenticated client. The env version also shows `nubra.reset_password()` (commented out) for changing the password after login. Not run here: it needs an institutional account.

### 6. Choose UAT or PROD explicitly: [`switching_between_uat_and_live.py`](../../examples/uat_environment/switching_between_uat_and_live.py)

The environment is an argument, not a config file, so it is always visible in code. Keep the PROD line commented until you mean it. PROD is real money and needs a live account.

```python
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
print("Connected to the UAT sandbox.")

# PROD: live trading. Uncomment to switch, and keep the environment explicit in code.
# nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)
```

Run: `py -3.12 examples/uat_environment/switching_between_uat_and_live.py`

Real output:

```
Connected to the UAT sandbox.
```

### 7. Create the main clients: [`quick_start.py`](../../examples/introduction/quick_start.py)

One login, then the three classes most scripts need.

```python
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

instruments = InstrumentData(nubra)
market_data = MarketData(nubra)
trader = NubraTrader(nubra)
print("Logged in. Ready: InstrumentData, MarketData, NubraTrader.")
```

Run: `py -3.12 examples/introduction/quick_start.py`

Real output:

```
Logged in. Ready: InstrumentData, MarketData, NubraTrader.
```

## Go further

1. Run `basic_usage.py` twice in a row and note whether the second run asks for an OTP. Then run `logout_and_relogin.py` and compare.
2. Put a wrong MPIN in a scratch `.env`, run an example, and check whether `auth_data.db` is still there (the SDK deletes it on a failed MPIN check). Restore the MPIN afterwards.
3. Write a script that sets an environment variable at the top, picks `NubraEnv.UAT` or `NubraEnv.PROD` from it, and prints which one it chose.

## Common errors

| Error text | Cause | Fix |
| --- | --- | --- |
| HTTP 440 session expired / MPIN re-verification needed | No `.env` to re-verify the MPIN when the saved session lapses | Add `PHONE_NO` and `MPIN` to `.env` and use `env_creds=True` |
| Asked for OTP on every run | `auth_data.db` is stored in the current folder; running from another folder or after `logout()` starts fresh | Run from the repo root; call `logout()` only when you mean to |
| Saved session disappears | The SDK deletes `auth_data.db` if the MPIN check fails | Correct the MPIN and log in again |
| `charmap` codec error on a Windows console | Console encoding | Set `PYTHONIOENCODING=utf-8` |

## Summary

`InitNubraSdk(env, ...)` is the single entry point: `env_creds=True` for `.env`, no flag for prompts, `insti_login=True` for institutions. The session lives in `auth_data.db`; `logout()` clears it. Keep UAT or PROD explicit in code.

[Home](README.md) | [← Previous: 0. Setup](00-setup.md) | [Next: 2. Instruments →](02-instruments.md)
