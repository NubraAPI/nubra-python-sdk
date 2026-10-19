# Nubra Options Cookbook (Python)

> **For educational and demonstration purposes only. Not investment advice.** These examples show how to use the Nubra Python SDK; they are not a recommendation to buy, sell or hold any instrument. Run them on UAT (sandbox) first.

Larger, multi-file recipes that combine several SDK features: login, option chains, Greeks, historical data, live streams and orders. Each folder is self-contained, with its own `README.md`, `requirements.txt`, `.env.example` and a single entry point.

| Recipe | What it shows | Entry point |
| --- | --- | --- |
| [delta_hedging](delta_hedging) | Delta hedging a long future + short ATM calls position: backtest, live Greeks dashboard, liquidity scan, risk watch | `main.py` (subcommands) |
| [gamma_hedging](gamma_hedging) | Gamma-aware dynamic delta hedging for SENSEX option sellers, with terminal and browser dashboards | `main.py` |
| [delta_neutral_backtest](delta_neutral_backtest) | Backtesting a delta-neutral / gamma-hedged short option position on historical data | `run_backtest.py` |
| [open_interest_dashboard](open_interest_dashboard) | NIFTY 50 constituent pressure, option-chain open-interest change and gamma-aware contract ranking on a live dashboard | `main.py` |

## Conventions

- **UAT by default.** `--env prod` is opt-in.
- **Orders are off by default.** Anything that can place, modify or cancel an order prints a dry run unless you pass `--place-orders`; on PROD it also needs `--allow-prod`.
- **Credentials** come from a local `.env` (`PHONE_NO`, `MPIN`). Copy `.env.example` and never commit the real file.
- Prices are integer paise in SDK payloads and printed as rupees.

## Verification status

Each recipe was run against the UAT sandbox on 2026-10-19: the backtests on historical data, the dashboards, scanner, watchdog and hedgers live in dry-run mode with real option chains, Greeks and websocket streams (the `Tested with` line in each entry point refers to these runs).

**Not verified live:** actual order placement, modification and cancellation (`--place-orders`), because the UAT test account had no funds. The payload shapes for those paths were checked against the installed SDK only. UAT also returns no previous open interest, so the open interest dashboard's OI-change score stays at zero there; use PROD data to see it move.
