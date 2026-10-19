# NIFTY Open Interest Dashboard in Python with the Nubra SDK (constituent pressure + OI change + gamma-aware option selection)

> **For educational and demonstration purposes only. Not investment advice.** This example shows how to use the Nubra Python SDK; it is not a recommendation to buy, sell or hold any instrument. Run it on UAT (sandbox) first.

## What it demonstrates

A terminal dashboard and a local web page that combine three live inputs for NIFTY:

- **Constituent pressure**: a weighted score across the NIFTY 50 stocks, built from streamed order-book imbalance, LTP momentum and volume impulse.
- **OI change**: the change in open interest on NIFTY option contracts near 0.45 absolute delta (puts added vs calls added).
- **Gamma-aware option ranking**: which CE or PE contracts rank best on delta, gamma, volume and affordability filters.

The SDK pieces used: `InitNubraSdk`, `InstrumentData` (symbol to `ref_id`), `MarketData.option_chain` (snapshot and expiry list), `NubraDataSocket` (order book, index and option-chain streams) and, only if you opt in, `NubraTrader.create_order`.

## How the readings are computed

All scores are in `[-1, 1]`. Positive is a bullish reading, negative a bearish one. They describe what the data looks like right now; they do not predict anything.

1. **Per-stock pressure** (on every order-book message) = `0.55 * book imbalance + 0.35 * momentum + 0.10 * volume impulse`.
   - Book imbalance = `(bid qty - ask qty) / (bid qty + ask qty)` over the top 5 levels.
   - Momentum = tick-to-tick LTP change x 500, clipped to `[-1, 1]`.
   - Volume impulse = latest volume delta vs 3x its rolling average (capped at 1), signed like the momentum.
2. **Pressure score** = weight-averaged mean of each stock's last 24 pressure values (weights from `nifty50_weights.csv`).
3. **OI score** = `(put OI added - call OI added) / (their sum)` over the 20 contracts closest to 0.45 absolute delta. Only OI increases count.
4. **Bias score** = `0.52 * pressure score + 0.48 * OI score`.
5. **Reading** is `BULLISH` or `BEARISH` only if all hold: `|pressure| >= --min-pressure-abs`, `|OI| >= --min-oi-abs`, both have the same sign, and `|bias| >= --min-score`. Otherwise it is `NEUTRAL` and the reason is shown.
6. **Candidate contract** for a directional reading: a CE if bullish, a PE if bearish. Contracts need traded volume > 0, gamma > 0, and one lot costing at most 95% of `--capital`. The best is the one with `|delta|` closest to 0.42, then higher gamma, volume and open interest.

The dashboard also lists the top 6 CE and PE contracts by the same ranking (affordable first) and a volume-adjusted participation chart of NIFTY against its constituents.

## Setup

1. Python 3.10+ and the SDK:

   ```bash
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` in this folder and fill in `PHONE_NO` and `MPIN`. The SDK reads `.env` from the directory you run `main.py` in. `.env` is git-ignored; never commit it.

## How to run

```bash
python main.py
```

This uses UAT, discovers the nearest upcoming NIFTY expiry from the option chain, prints the terminal dashboard and serves the web dashboard at `http://127.0.0.1:8051` (local only). Press Ctrl+C to stop. Live ticks need market hours.

Useful variations:

```bash
python main.py --expiry 20260528        # pick the expiry yourself (YYYYMMDD)
python main.py --no-dashboard           # log lines instead of the terminal cockpit
python main.py --open-browser           # open the web dashboard automatically
python main.py --max-minutes 30         # stop after 30 minutes
```

Defaults to the UAT sandbox. To use production, pass `--env PROD`.

### Optional order helper

Off by default. Without `--place-orders`, a directional reading with a sized candidate only **prints the order payload it would send** (`[dry-run] would send ...`).

```bash
python main.py --place-orders                      # sends to UAT
python main.py --env PROD --place-orders --allow-prod   # PROD needs both flags
```

`--env PROD --place-orders` without `--allow-prod` is refused at startup. The helper builds one single-leg BUY limit order for the candidate contract, sized to one lot if it passes the capital and risk filters, and stops after `--max-orders` (default 1) per run, with `--order-cooldown-seconds` between orders. In `bracket` mode it adds a stop-loss and target to the order; in `entry` mode it sends the limit entry only. It does not monitor or manage positions afterwards.

## Flags

| Flag | Default | Meaning |
| --- | --- | --- |
| `--env {UAT,PROD}` | `UAT` | Nubra environment. |
| `--expiry YYYYMMDD` | nearest upcoming | NIFTY expiry. |
| `--capital` | `5000` | Rupees; a lot costing more than 95% of this is marked unaffordable. |
| `--weights-csv` | bundled table | CSV with `symbol,weight`. |
| `--min-score` | `0.24` | Minimum absolute bias score for a directional reading. |
| `--min-pressure-abs` | `0.03` | Minimum absolute pressure score. |
| `--min-oi-abs` | `0.14` | Minimum absolute OI score. |
| `--decision-interval` | `10` | Seconds between evaluations. |
| `--dashboard` / `--no-dashboard` | on | Terminal dashboard. |
| `--dashboard-refresh` | `1` | Terminal redraw interval, seconds. |
| `--web-dashboard` / `--no-web-dashboard` | on | Local web dashboard. |
| `--web-host`, `--web-port` | `127.0.0.1`, `8051` | Where the web dashboard listens. |
| `--open-browser` | off | Open the web dashboard on start. |
| `--connect-wait` | `3` | Seconds to wait after opening the websocket. |
| `--option-poll-seconds` | `15` | REST option-chain fallback interval; `0` disables it. |
| `--max-minutes` | `0` | `0` runs until Ctrl+C. |
| `--place-orders` | off | Actually send the order (otherwise dry run). |
| `--allow-prod` | off | Required with `--place-orders` when `--env PROD`. |
| `--order-mode {bracket,entry}` | `bracket` | Limit entry with stop-loss and target, or limit entry only. |
| `--max-orders` | `1` | Orders (or dry-run payloads) per run. |
| `--order-cooldown-seconds` | `300` | Minimum gap between orders. |
| `--risk-fraction` | `0.08` | Max reference loss per order as a fraction of `--capital`. |
| `--stoploss-pct` | `18` | Stop-loss distance below the contract LTP, percent. |
| `--target-multiple` | `1.6` | Target distance as a multiple of the stop-loss distance. |
| `--entry-limit-buffer-pct` | `1.5` | Entry limit placed this percent above the contract LTP. |
| `--only-market-hours` / `--no-only-market-hours` | on | Only build orders between 09:16 and 15:10. |
| `--order-tag` | `nifty-oi-dashboard` | Order tag (letters, digits, hyphens). |
| `--totp-login`, `--insti-login` | off | Alternative SDK login flows. |

Prices from the SDK are integer paise; the dashboards show rupees and order payloads use paise.

## Files

| File | What it does |
| --- | --- |
| `main.py` | Entry point: argparse, order-flag safety check, starts the run loop. |
| `open_interest_dashboard/config.py` | Score weights, thresholds and the weights-table loader. |
| `open_interest_dashboard/nifty50_weights.csv` | Bundled NIFTY 50 weights (`symbol,weight`, percent); update it when the index is rebalanced. |
| `open_interest_dashboard/models.py` | Data containers and paise/rupee helpers. |
| `open_interest_dashboard/pressure.py` | Constituent pressure and the participation map. |
| `open_interest_dashboard/oi_change.py` | Option-chain parsing and the OI score. |
| `open_interest_dashboard/option_selection.py` | Delta/gamma/affordability ranking and one-lot sizing. |
| `open_interest_dashboard/reading.py` | Blends the scores into a `MarketReading`. |
| `open_interest_dashboard/terminal_dashboard.py` | Terminal rendering. |
| `open_interest_dashboard/web_dashboard.py`, `dashboard.html` | Local web server and page. |
| `open_interest_dashboard/orders.py` | Optional order payload builder and safety checks. |
| `open_interest_dashboard/feeds.py` | Login, instrument lookup, expiry discovery, option-chain snapshot. |
| `open_interest_dashboard/runner.py` | Streams data, scores it, redraws, runs the optional order helper. |
| `requirements.txt`, `.env.example`, `.gitignore` | Dependencies, credential placeholders, ignored files. |

## Notes

- The bundled weights table is a point-in-time snapshot. Stocks the instrument master does not list are skipped with a warning.
- The REST option-chain poll fills the contract tables when the option stream is quiet.
- Status: not yet verified in a live UAT session. The scoring, ranking and payload-building functions were checked offline with synthetic data and the order payload was validated against the installed SDK model.
