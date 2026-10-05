# 0. Setup

Install the Nubra Python SDK, create your `.env`, and run your first example safely against the UAT sandbox.

[Home](README.md) | [Next: 1. Authentication →](01-authentication.md)

## In this guide

- What the Nubra SDK is and the difference between UAT (sandbox) and PROD (live).
- How to install it and keep your credentials in a `.env` file that never gets committed.
- How to run any example in this repo, and how to tell read-only, streaming and mutating examples apart.
- The paise rule: every price in the SDK is an integer in paise.
- Where things live in the repo and what the helper tools do.

## You need

Requires Python 3.7+ (examples tested on 3.12). You also need internet access and a Nubra UAT account (phone number, MPIN, and the OTP sent to your phone). Nothing else.

This repo holds runnable examples, the guide, snippets and response schemas. The SDK installs from PyPI as `nubra-sdk` and imports as `nubra_python_sdk`; its source code is not in this repo.

## What is the Nubra SDK?

`nubra-sdk` (version 0.5.4 at the time of writing; this repo targets the V3 SDK) is a Python library for Nubra's trading platform. After one login you get a client that you hand to a few small classes:

| Class | Use it for | Guide |
| --- | --- | --- |
| `InstrumentData` | Look up stocks, futures, options, indices | [2. Instruments](02-instruments.md) |
| `MarketData` | Prices, quotes, historical candles, option chains | [3. Market Data](03-market-data.md) |
| `NubraTrader` | Place, modify, cancel and read orders | [5. Trading](05-trading.md) |
| WebSocket classes | Streaming prices, Greeks, order book, order updates | [4. Realtime Data](04-realtime.md) |

## UAT vs PROD

- **UAT** is a sandbox. Safe to experiment, orders do not hit the real market. All examples in this repo use `NubraEnv.UAT`.
- **PROD** is live trading with real money.

Every example contains this comment right above the login line:

```python
# Use NubraEnv.UAT for testing. Switch to NubraEnv.PROD for live usage.
```

To go live you change `NubraEnv.UAT` to `NubraEnv.PROD` in your own code. Keep the environment explicit in code, never guess. Note that UAT and PROD `ref_id` values can differ, so always resolve instruments again in each environment.

## Install

```bash
python -m pip install nubra-sdk
# upgrade later
python -m pip install --upgrade nubra-sdk
```

On Windows these guides use the Python launcher: `py -3.12 -m pip install nubra-sdk`. The examples also use `pandas` (for DataFrames) and `requests`; install them if pip does not pull them in for you.

## Create your `.env`

In the repo root (the folder you will run commands from), create a file called `.env`:

```
PHONE_NO=<your 10 digit phone number>
MPIN=<your MPIN>
```

Rules:

- Never commit `.env`. This repo's `.gitignore` already excludes `.env`, `auth_data.db*` and `uat_outputs/`.
- Never paste your MPIN, OTP or tokens into code, screenshots or chats.
- The examples then log in with `InitNubraSdk(NubraEnv.UAT, env_creds=True)`. You will still type an OTP the first time (see [1. Authentication](01-authentication.md)).

## Run an example

From the repo root:

```bash
py -3.12 examples/introduction/quick_start.py     # Windows
python examples/introduction/quick_start.py       # macOS / Linux
```

Always run from the repo root. The SDK stores your session in a file called `auth_data.db` in the **current folder**, so running from different folders means logging in again.

Real output of the quick start:

```
Logged in. Ready: InstrumentData, MarketData, NubraTrader.
```

If your Windows console shows a `charmap` codec error when printing, run `set PYTHONIOENCODING=utf-8` (cmd) or `$env:PYTHONIOENCODING = "utf-8"` (PowerShell) first.

## The paise rule

Prices, strikes and money values come back as **integers in paise**. Divide by 100 for rupees.

```
116770 paise  =  Rs 1167.70
tick_size 5   =  Rs 0.05
```

When you place orders later, you also pass integer paise, snapped to the contract's `tick_size`. Do not use floats for prices.

## Example types

Every example starts with a docstring that tells you what it is:

- **read-only**: only fetches data. Safe to run any time on UAT.
- **streaming**: opens a WebSocket and prints live ticks. Stop it with Ctrl+C.
- **mutating**: changes something (places or cancels orders, changes security settings). On UAT this is sandbox-only; read the docstring before you run it.

Each docstring also has `Needs:` (what you must have) and `Expect:` (what you will see).

## Repo map

```
examples/          105 runnable examples, one folder per topic, each with a README
  authentication/  login flows (see [1. Authentication](01-authentication.md))
  get_instruments/ instrument master lookups (guide 2)
  introduction/    quick_start.py
  uat_environment/ UAT vs PROD switch
  market_data/ portfolio/ realtime_data/ trading/
docs/guide/        these guides
tools/             helper scripts (below)
snippets/ schemas/ copy-paste snippets and request/response schemas
```

## Helper tools

All run from the repo root.

- `tools/uat_login.py`: one-time interactive UAT login. It is hard-wired to UAT, saves the session in `auth_data.db`, and prints a current price to prove it works. Run `py -3.12 tools/uat_login.py` before using the runner below.
- `tools/run_examples_uat.py`: runs every example against UAT and reports pass/fail. It skips anything that references `NubraEnv.PROD` and anything interactive (OTP, institutional login). Optional substring filters: `py -3.12 tools/run_examples_uat.py get_instruments`.
- `tools/validate_examples.py`: parses every example file for syntax errors, no network needed.

## Go further

1. Create `.env`, then run `examples/introduction/quick_start.py` and confirm you see the "Logged in" line.
2. Check that `git status` does not list `.env` or `auth_data.db*`.
3. Convert a price from `get_instruments/basic_usage.py` (e.g. `underlying_prev_close=72120` is Rs 721.20) and check it against your broker app.

## Common errors

| Error text | Cause | Fix |
| --- | --- | --- |
| HTTP 440 session expired / MPIN re-verification needed | No usable `.env` or saved session, so the SDK cannot re-verify your MPIN | Create `.env` with `PHONE_NO` and `MPIN`, or run `tools/uat_login.py` again |
| You are asked to log in every time | The SDK keeps the session in `auth_data.db` in the current folder, and you ran from a different folder | Always run from the repo root |
| Session suddenly gone | The SDK deletes `auth_data.db` if the MPIN check fails | Fix the MPIN in `.env` and log in again |
| `charmap` codec error on a Windows console | Console encoding cannot print some characters | Set `PYTHONIOENCODING=utf-8` |

## Summary

- Nubra SDK = one login, then `InstrumentData`, `MarketData`, `NubraTrader` and streams.
- UAT is the safe default; PROD is a deliberate switch.
- Credentials live in `.env`, which is never committed. Prices are integer paise.
- Run examples from the repo root; the session lives in `auth_data.db` there.

[Home](README.md) | [Next: 1. Authentication →](01-authentication.md)
