# Delta Hedging in Python with the Nubra SDK (long future + short ATM calls)

> **For educational and demonstration purposes only. Not investment advice.** This example shows how to use the Nubra Python SDK; it is not a recommendation to buy, sell or hold any instrument. Run it on UAT (sandbox) first.

A worked example of delta hedging with the [Nubra Python SDK](https://pypi.org/project/nubra-sdk/): hold one future long, short two ATM calls on the same underlying, and keep the net delta near zero by trading the cash equity. It includes a historical replay, a hedge runner (dry run by default), a live Greeks dashboard, a liquidity scan and an account-wide loss watchdog, all behind one `main.py`.

## What it demonstrates

| SDK area | Used for |
|---|---|
| `InitNubraSdk(NubraEnv.UAT, env_creds=True)` | Login from `PHONE_NO` / `MPIN` in `.env` |
| `InstrumentData` | Nearest future, lot size, cash equity `ref_id` |
| `MarketData.option_chain / quote / historical_data` | ATM call and Greeks, last prices, historical bars |
| `NubraDataSocket` (`orderbook`, `greeks` streams) | Live underlying price and call delta |
| `NubraTrader.create_order / get_margin / exit_all_positions` | Multi-leg entry, hedge orders, margin check, flatten |
| `NubraPortfolio.positions / funds` | PnL, positions, margin, account MTM |

## How the hedge works

- **Position:** buy `--future-lots` lots of the nearest future and sell `--short-calls` lots of the ATM call (the strike whose delta is closest to 0.5), as one multi-leg order.
- **Net delta** in shares = future shares (delta 1.0 each) minus `call delta x call shares` for every short call lot, plus the equity hedge already held. A fresh position starts near zero.
- **Re-hedge:** once the underlying has moved at least `--trigger-pct` percent since the last hedge (or entry), net delta is recomputed from live deltas. Positive net delta means sell equity, negative means buy equity, for `round(|net delta|)` shares. Anything under one share is ignored.
- **Exit:** when total PnL (future + short calls + equity hedge) reaches `--pnl-target` or falls to `--pnl-stop-loss`, all legs are closed.
- The decision maths lives in `hedging/logic.py` as pure functions, shared by the replay, the dry run and the live runner.

Prices from the SDK are integer paise; everything printed is in rupees.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env      # Windows: copy .env.example .env
# edit .env: PHONE_NO and MPIN
```

The SDK may ask for an OTP when it logs in. Run all commands from this folder (the SDK reads `.env` from the working directory). Requires Python 3.9+; developed against `nubra-sdk` 0.5.4.

## Running

Every subcommand takes `--env uat|prod` and defaults to **UAT**. `python main.py <command> --help` lists all options.

### Orders are off by default

`hedge` and `watch` are **dry runs**: they print the orders they would send and do not send them. Orders are only sent with `--place-orders`. On PROD, `--place-orders` is refused unless you also pass `--allow-prod`.

### `backtest` (read-only)

Replays the hedge on historical bars. You give it the exact historical contract names.

```bash
python main.py backtest --future-symbol <FUTURE_CONTRACT> --call-symbol <CALL_CONTRACT> \
    --equity-symbol <SYMBOL> --lot-size <LOT> --start 2025-08-01 --end 2025-08-29 \
    --pnl-target 5000 --pnl-stop-loss -3000
```

Prints a summary (entry, exit or "no exit in window", PnL, max drawdown, number of hedges) and writes `output/<SYMBOL>_hedges.csv` and `output/<SYMBOL>_pnl_curve.png`. Fills are at the bar close with no slippage, spread or brokerage, and historical data on UAT can be sparse, so treat it as a check of the rules rather than a result.

### `hedge` (streaming)

```bash
python main.py hedge <SYMBOL> --pnl-target 5000 --pnl-stop-loss -3000            # dry run, UAT
python main.py hedge <SYMBOL> --pnl-target 5000 --pnl-stop-loss -3000 --place-orders   # sends orders (UAT)
```

Resolves the legs, prints the margin check and the entry order, then prints one status line per `--poll-seconds` (underlying price, net delta in shares, equity hedge, PnL). In dry run it tracks a paper position in memory from live prices and writes no state. With `--place-orders` it saves `state/hedge_state_<SYMBOL>.json` so a restart resumes an open position instead of entering again. `--hedge-delivery` sets CNC or IDAY for the equity hedge orders; note that selling shares you do not hold generally needs IDAY. Stop with Ctrl+C (an open position stays open), or bound a run with `--max-seconds`.

### `dashboard` (read-only)

```bash
python main.py dashboard            # redraws every 4 seconds
python main.py dashboard --once     # draw once and exit
```

Open positions with per-position Greeks (from the option chain), net delta, gamma, theta and vega of the whole book (futures and shares count as delta 1.0 per unit), total PnL and available margin.

### `scan` (read-only)

```bash
python main.py scan --top-n 15 --max-underlyings 40
```

Ranks F&O underlyings by liquidity metrics: average daily future volume, future OI trend, ATM call volume and bid-ask spread. The score is only a sort order for liquidity; it says nothing about direction or value. Historical calls are throttled to the documented limit, so a full scan is slow; use `--max-underlyings` to bound it.

### `watch` (account-wide loss limit)

```bash
python main.py watch --max-daily-loss -15000 [--max-drawdown-pct 20]          # reports only
python main.py watch --max-daily-loss -15000 --place-orders                   # flattens on a breach (UAT)
```

Polls positions and funds. On a breach of the loss limit (or the optional drawdown limit) it flattens **every** open position on the account with `exit_all_positions(at_market_price=True)` when `--place-orders` is set, otherwise it prints what it would do. It stops after a breach.

## Files

| Path | Purpose |
|---|---|
| `main.py` | Entry point; argparse subcommands `backtest`, `hedge`, `dashboard`, `scan`, `watch` |
| `hedging/logic.py` | Pure hedge maths: net delta, hedge order, re-hedge trigger, exit rule, PnL |
| `hedging/hedge_runner.py` | Entry, websocket streaming, re-hedge and exit loop |
| `hedging/orders.py` | Order gate: dry run by default, `--place-orders` / `--allow-prod` checks |
| `hedging/market.py` | SDK lookups: nearest future, ATM call, cash equity, last price |
| `hedging/state.py` | Position state saved to JSON for restarts (live runs only) |
| `hedging/backtest.py`, `hedging/report.py` | Historical replay, CSV and chart output |
| `hedging/dashboard.py` | `rich` live positions and Greeks table |
| `hedging/scanner.py` | Liquidity scan |
| `hedging/watchdog.py` | Account-wide loss and drawdown watchdog |
| `hedging/session.py` | SDK login and PROD guard |
| `tests/test_logic.py` | Offline checks: `python -m unittest discover -s tests` |
| `.env.example` | `PHONE_NO` / `MPIN` placeholders |

## Notes

- This is a teaching example. Delta hedging does not remove risk: gamma, vega, gaps, slippage, spreads, charges and margin changes all affect a real position, and a re-hedge only happens when your threshold is crossed.
- Entry and exit use market orders. Hedge orders use `CNC` delivery by default; change it with `--hedge-delivery`.
- The strategy tag on orders is `delta-hedge-<symbol>`.
- Local files (`.env`, `auth_data.db*`, `state/`, `output/`) are in `.gitignore`.
- The scripts and orders were written against the SDK source and docs. Check each subcommand on UAT with small sizes before relying on it; UAT market data and order fills can differ from production.
