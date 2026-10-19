# Gamma Hedging in Python with the Nubra SDK (dynamic delta hedging for SENSEX option sellers)

> **For educational and demonstration purposes only. Not investment advice.** This example shows how to use the Nubra Python SDK; it is not a recommendation to buy, sell or hold any instrument. Run it on UAT (sandbox) first.

## What this demonstrates

A short-options position (for example a short straddle or strangle) has a net delta that drifts as the underlying moves. This example keeps that delta near zero by trading the SENSEX future, and polls faster when the position's net gamma is high. It shows how to use the Nubra Python SDK for:

- **Option chain with Greeks**: one `MarketData.option_chain()` call per tick returns each leg's LTP, `delta` and `gamma`.
- **Spot and futures prices**: `MarketData.current_price()` and `MarketData.quote()`.
- **Instruments**: `InstrumentData.get_instruments_dataframe()` to find the nearest SENSEX future and its lot size.
- **Orders**: a multi-leg order (`create_order` with `isMultiLeg`) for the short option structure, and single-leg futures orders for the hedge, all under one `stratTags` tag.
- **Positions and orders**: `NubraPortfolio.positions()` for reconciliation, `NubraTrader.orders()` / `get_order()` / `cancel_orders_sentinel()`.
- Integer-paise prices converted to rupees at one boundary.

It also includes a terminal dashboard (rich) and a browser dashboard served on `127.0.0.1`.

## How gamma-aware hedging works

Each tick, for each strategy:

1. Fetch the option chain and futures quote. Take each short leg's `delta` and `gamma` from the API (Black-Scholes is used only if the API returns none).
2. Compute, in underlying units:
   - `net_delta = sum(leg.delta * qty_lots * lot_size) + futures.qty_lots * futures.lot_size`
   - `net_gamma = sum(leg.gamma * qty_lots * lot_size)` (futures have no gamma)
3. **Delta band**: if `|net_delta| > DELTA_TOLERANCE_LOTS * lot_size`, hedge with `-round(net_delta / lot_size)` futures lots. Otherwise do nothing.
4. **Gamma mode**: if `|net_gamma| >= HIGH_GAMMA_THRESHOLD` the strategy is in `HIGH_GAMMA` mode and is polled every `POLL_INTERVAL_HIGH_GAMMA_SEC` (default 7s); otherwise `NORMAL` mode at `POLL_INTERVAL_NORMAL_SEC` (default 30s). High gamma means delta changes quickly with spot, so it is checked more often.
5. Before any order: the trade is clamped to `MAX_FUTURES_POSITION_LOTS`, then checked against the shared rate limit (`MAX_HEDGE_TRADES_PER_MIN`).
6. A shared **kill switch** stops all hedging after `MAX_CONSECUTIVE_API_ERRORS` consecutive API errors, or if spot moves `CIRCUIT_BREAKER_PCT` percent within `CIRCUIT_BREAKER_WINDOW_SEC`. It stays halted until restart.

At startup each strategy first sells the initial short structure (a straddle at the ATM strike, or a strangle at the strikes closest to `STRANGLE_TARGET_DELTA`), standing in for a position already held. Tagged positions that already exist on the broker can also be attached to the hedger at runtime from the browser dashboard (toggle per tag).

## Setup

Python 3.9+ (tested with 3.12) and a Nubra UAT account.

```bash
cd examples/cookbook/gamma_hedging
pip install -r requirements.txt
cp .env.example .env      # then fill in PHONE_NO and MPIN
```

Run commands from this folder: the SDK reads `.env` from the current working directory. `.env` holds credentials and is git-ignored; never commit it. Every other setting has a default (see `.env.example`).

To check that login works without putting credentials in `.env`:

```bash
python main.py check-login   # prompts for phone number, OTP and MPIN
```

## How to run

UAT (sandbox) is the default environment, and **orders are not sent unless you pass `--place-orders`**.

```bash
python main.py                      # same as `python main.py run`: dry run on UAT
python main.py run --place-orders   # send the setup and hedge orders to UAT
python main.py run --no-browser     # do not auto-open the browser dashboard
python main.py cancel-open          # list open orders for UNDERLYING (dry run)
python main.py cancel-open --yes    # cancel them
```

In a dry run the program still logs in and reads live market data, but every order is only printed or logged as `DRY RUN`, and the internal position book is updated as if the order had filled at LTP. Reconciliation against broker positions is skipped in a dry run.

Production is refused unless you pass both `--env PROD` and `--allow-prod`. Run on UAT first.

The session stops at `MARKET_CLOSE_TIME` (default 15:30 IST) or on Ctrl+C.

## Dashboards

- **Terminal**: a rich live display, one panel per strategy (spot, net delta vs band, net gamma vs threshold, mode, futures lots, P&L, the decision reasoning for the tick, legs table, recent hedge actions). The header shows the environment and whether orders are enabled.
- **Browser**: http://127.0.0.1:8765 (change with `WEB_DASHBOARD_PORT`). Same data, plus a History panel, a Settings panel (edit thresholds and guardrails live, no restart) and a toggle to attach hedging to tagged positions found on the broker. It is served on localhost only and has no authentication; do not expose the port.

An order is shown as FILLED only when Nubra returned a nonzero fill price; otherwise it is shown as placed/pending, and in a dry run as simulated.

## Files

| File | Purpose |
| --- | --- |
| `main.py` | Entry point: `run`, `check-login`, `cancel-open` subcommands |
| `gamma_hedging/config.py` | Settings from environment variables; per-strategy overrides |
| `gamma_hedging/nubra_client.py` | All SDK calls: instruments, option chain, orders, positions, tag discovery; dry-run handling |
| `gamma_hedging/initial_position.py` | Sells the initial short straddle/strangle and seeds the position book |
| `gamma_hedging/hedger.py` | Per-tick hedge decision (delta band, gamma mode, caps, rate limit) |
| `gamma_hedging/positions.py` | Option legs, futures position, net delta/gamma and P&L |
| `gamma_hedging/greeks.py` | Black-Scholes delta/gamma fallback |
| `gamma_hedging/risk.py` | Hedge rate limiter and position cap |
| `gamma_hedging/safety.py` | Environment guard (UAT default, PROD needs `--allow-prod`) and kill switch |
| `gamma_hedging/dashboard.py` | Terminal dashboard (rich) |
| `gamma_hedging/web_dashboard.py` | Browser dashboard (stdlib HTTP server) |
| `gamma_hedging/settings_control.py`, `tag_control.py` | Thread-safe hand-off of dashboard settings and tag toggles to the main loop |
| `gamma_hedging/logging_utils.py` | Per-session tick CSV and events log under `logs/` |
| `.env.example` | Settings template (credentials left blank) |
| `requirements.txt` | `nubra-sdk`, `python-dotenv`, `rich` |

## Notes

- Prices from the SDK are integer paise; the code converts to rupees for display and back to paise for orders. Futures hedges use whole lots only.
- Greeks come from the option chain. The Black-Scholes fallback assumes `iv` values above 1.5 are percentages; compare it with the API Greeks before trusting it.
- For a LIMIT setup order the `entryPrice` is the signed net premium in paise (negative for a net credit). This path has not been exercised against the exchange in this version; check it on UAT.
- Orders that never fill stay OPEN and accumulate across sessions; `cancel-open` lists and cancels them, matched by underlying because open orders come back without tags.
- The hedge size uses Python's `round`, which rounds exact halves to the nearest even integer.
- Each run writes `logs/session_<timestamp>_ticks.csv` and `..._events.log` (git-ignored).
- The kill switch and caps limit, but do not remove, the risk of automated order placement. Review the order payloads in a dry run before using `--place-orders`.
