# Delta-Neutral and Gamma-Hedge Backtesting in Python with the Nubra SDK

> **For educational and demonstration purposes only. Not investment advice.** This example shows how to use the Nubra Python SDK; it is not a recommendation to buy, sell or hold any instrument. Backtest results are historical simulations and do not indicate future results. Run it on UAT (sandbox) first.

## What it demonstrates

- Pulling 1-minute historical option (with greeks and best bid/ask), futures and index data through `MarketData.historical_data()`.
- Replaying a short ATM straddle over each weekly expiry, once unhedged and once with a futures delta hedge, on the same price data.
- Measuring what the hedge costs: spread (slippage), per-lot fees, drawdown and residual delta.

It is read-only. It only requests historical data and never places orders.

## How the backtest works

For every expiry date in the requested range (default weekday: Tuesday, override with `--expiry-weekday`):

1. **Entry**: on the previous weekday at `--entry-time` (IST, default 09:20), pick the ATM strike (spot rounded to `--strike-step`) and sell 1 lot CE + 1 lot PE at that minute's mid price, `(bid + ask) / 2`.
2. **Option legs**: never adjusted. They are marked at mid each minute and cash-settled at the expiry-day close, using the last index close as a settlement proxy (not the exchange's official settlement average).
3. **Net delta** each minute = `sum(-leg delta) * lot_size + futures_lots * lot_size`. Net gamma is computed and reported only.
4. **Rebalance rule (hedged run)**: if `|net delta| > --delta-threshold` lots, trade `-round(net delta / lot_size)` futures lots in the front-month contract, clamped to `--max-futures-lots`. The condition is checked once per 1-minute bar.
5. **Costs**: futures buys fill at the ask, sells at the bid, plus `--fee-per-lot` per lot traded (a flat assumption, not a broker fee schedule). The result also shows the same trades filled at mid with no fees, so the hedge cost is isolated. Option legs are filled at mid, with no option spread, brokerage or taxes. No margin or capital model is included.
6. **Optional policy filters**: `--confirmation-bars N` (breach must persist N bars), `--cooldown-minutes M` (block an opposite-direction hedge for M minutes unless the breach exceeds `--cooldown-override` times the threshold), and `--stop-loss-multiple X` (close everything once option P&L falls to -X times the premium collected). All are off by default and apply to the hedged run; the stop applies to both runs.
7. Any open futures position is squared off at the final bar (or the stop bar).

Futures contract: nearest monthly contract that has not yet expired (a contract is used up to and including its own expiry date).

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env     # then fill in PHONE_NO and MPIN
```

Credentials are read from `.env` only. Never commit it.

## Run

```bash
# Dry look at the options
python run_backtest.py --help

# One month of weekly expiries on UAT (expired contracts are often empty there)
python run_backtest.py --start 2026-09-01 --end 2026-09-30

# Production history, caching downloads to ./cache, with the optional policy filters
python run_backtest.py --env prod --start 2026-06-01 --end 2026-09-08 \
    --delta-threshold 0.5 --confirmation-bars 3 --cooldown-minutes 5 --stop-loss-multiple 1.5 \
    --cache-dir cache
```

Check `--lot-size` against the current instrument master; lot sizes change over time and scale every rupee figure.

## Output

Per expiry the console prints the strike, premium collected, and for the unhedged and hedged runs: P&L, max drawdown, worst P&L, largest `|net delta|`, and for the hedged run the trade count, slippage, fees and hedge cost. Expiries with missing data are listed as skipped (for example holiday-shifted expiries, since holidays are not modelled). Totals follow. CSVs are written to `output/`:

- `pnl_summary.csv`: one row per expiry and run.
- `hedge_trades.csv`: every futures trade with prices, fee, net delta before the trade and the reason.
- `pnl_paths.csv`: per-minute P&L, net delta and net gamma.

## Files

| File | Purpose |
| --- | --- |
| `run_backtest.py` | Command-line entry point: builds data for each expiry, runs both variants, prints and saves results |
| `backtest/engine.py` | Simulation logic (pure functions over DataFrames; no network) |
| `backtest/data.py` | Historical data fetch via the SDK, paise to rupees, optional CSV cache |
| `backtest/symbols.py` | Option/futures symbol construction and expiry-date helpers |
| `backtest/report.py` | Console summaries and CSV writers |
| `.env.example` | Placeholder credentials |
| `requirements.txt` | Python dependencies |

## What this example leaves out

This is a focused extract: one hedge-backtest engine for one position type. It has no web UI, no PDF/HTML reporting, no database-backed cache (only an optional CSV cache), no margin or capital model, no holiday calendar, no other position types, and no intra-minute (sub-bar) hedge timing. Historical data availability depends on the environment: UAT often has little or no expired-contract history.
