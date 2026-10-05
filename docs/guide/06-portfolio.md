# 6. Portfolio

Read funds, holdings and positions, and turn raw paise into a readable P&L view.

[Home](README.md) | [← Previous: Trading](05-trading.md) | [Next: Recipes and Next Steps →](07-recipes-and-next-steps.md)

## In this guide

- Fetch funds and margin with `portfolio.funds()`
- Fetch equity holdings with `portfolio.holdings()`
- Fetch open and closed positions with `portfolio.positions()`
- Combine all three into one summary and a worst-first P&L table

## You need

- A UAT login through `PHONE_NO` / `MPIN` in `.env`.
- Optional: orders placed in [Trading](05-trading.md), so positions are not empty.

All five examples are read-only and default to `NubraEnv.UAT`. The API returns money as integer paise. Every example divides by 100 and prints rupees.

| Call | Result object | Key fields |
| --- | --- | --- |
| `portfolio.funds()` | `result.portFundsAndMargin` | `netMarginAvailable`, `totalMarginBlocked`, `totalCollateral`, `brokerage` |
| `portfolio.holdings()` | `result.portfolio.holdings`, `.holdingStats` | `avgPrice`, `lastTradedPrice`, `netPnl`, `investedAmount`, `currentValue`, `totalPnl`, `dayPnl` |
| `portfolio.positions()` | `result.portfolio.positions`, `.positionStats` | `netQuantity`, `avgBuyPrice`, `avgSellPrice`, `pnl`, `realisedPnl`, `unrealisedPnl`, `totalPnl` |

## Setup

`NubraPortfolio` is built from the client returned by `InitNubraSdk(...)`:

```python
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.portfolio.portfolio_data import NubraPortfolio

nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
portfolio = NubraPortfolio(nubra)
```

## The examples, in order

### Funds

[examples/portfolio/funds/basic_usage.py](../../examples/portfolio/funds/basic_usage.py)

Prints start-of-day funds, net margin available, margin blocked, collateral and brokerage.

```python
result = portfolio.funds()
pfm = result.portFundsAndMargin if result else None
if pfm is None:
    raise SystemExit("No funds data returned for this account.")

# The API returns integer paise; divide by 100 for rupees.
rupees = lambda paise: f"Rs {(paise or 0) / 100:,.2f}"
print(f"Net margin available:  {rupees(pfm.netMarginAvailable)}")
print(f"Total margin blocked:  {rupees(pfm.totalMarginBlocked)}")
```

```
py -3.12 examples/portfolio/funds/basic_usage.py
```

Real output:

```
Client:                <client-code>
Start-of-day funds:    Rs -71.51
Net margin available:  Rs -544,547.21
Total margin blocked:  Rs 490,908.17
Total collateral:      Rs 91.00
Brokerage:             Rs 848.52
```

### Holdings

[examples/portfolio/holdings/basic_usage.py](../../examples/portfolio/holdings/basic_usage.py)

Prints one row per holding plus invested amount, current value and total P&L.

```python
result = portfolio.holdings()
pf = result.portfolio if result else None
if pf is None or not pf.holdings:
    raise SystemExit("No holdings found for this account.")

for h in pf.holdings:
    print(f"{h.symbol:<14}{h.quantity:>6}{(h.avgPrice or 0) / 100:>12,.2f}"
          f"{(h.lastTradedPrice or 0) / 100:>12,.2f}{(h.netPnl or 0) / 100:>14,.2f}")
```

```
py -3.12 examples/portfolio/holdings/basic_usage.py
```

Real output:

```
Symbol           Qty      Avg Rs      LTP Rs    Net P&L Rs
YESBANK            8       22.89       21.02        -14.96
Invested Rs 183.12 | Current Rs 168.16 | Total P&L Rs -14.96
```

### Positions

[examples/portfolio/positions/basic_usage.py](../../examples/portfolio/positions/basic_usage.py)

Lists every position for the day, including closed ones (`netQuantity` of 0), with P&L and the total from `positionStats`.

```python
result = portfolio.positions()
pf = result.portfolio if result else None
if pf is None or not pf.positions:
    raise SystemExit("No positions found for this account.")

for p in pf.positions:
    print(f"{p.symbol:<26}{p.netQuantity or 0:>8}"
          f"{(p.lastTradedPrice or 0) / 100:>12,.2f}{(p.pnl or 0) / 100:>12,.2f}")
print(f"Total P&L Rs {(pf.positionStats.totalPnl or 0) / 100:,.2f}")
```

```
py -3.12 examples/portfolio/positions/basic_usage.py
```

Real output (first rows only; the full run listed 16 positions):

```
Symbol                     Net Qty      LTP Rs      P&L Rs
RELIANCE                        -4    1,177.00        7.10
ICICIBANK                       18    1,315.50      -36.40
NIFTY26O0622500PE                0      110.80     -425.75
NIFTY26O0622450PE               65       87.75   -1,371.50
NIFTY26O0622400PE               65       68.95    1,699.75
NIFTY26O0622400PE               65       68.95    1,339.00
...
Total P&L Rs 6,334.20
```

### Portfolio summary

[examples/portfolio/portfolio_summary.py](../../examples/portfolio/portfolio_summary.py)

Calls all three endpoints once and prints a one-screen summary. Open exposure is computed locally as the sum of `|netQuantity| x LTP` over open positions.

```python
funds = portfolio.funds()
holdings = portfolio.holdings()
positions = portfolio.positions()

open_pos = [x for x in p.positions if (x.netQuantity or 0) != 0]
# Exposure = |net qty| x LTP for each open position.
exposure = sum(abs(x.netQuantity) * (x.lastTradedPrice or 0) for x in open_pos)
```

```
py -3.12 examples/portfolio/portfolio_summary.py
```

Real output:

```
FUNDS
  Margin available : Rs    -544,553.95
  Margin used      : Rs     490,914.91
  Collateral       : Rs          91.00
HOLDINGS
  Invested         : Rs         183.12
  Current value    : Rs         168.40
  Total P&L        : Rs         -14.72
  Day P&L          : Rs           2.40
POSITIONS
  Open positions   : 14
  Open exposure    : Rs      83,760.15
```

The run continued with realised, unrealised and total P&L lines for positions.

### Open positions P&L

[examples/portfolio/open_positions_pnl.py](../../examples/portfolio/open_positions_pnl.py)

Filters out flat positions and sorts by P&L, worst first, with buy average, sell average and LTP.

```python
open_pos = [p for p in (pf.positions if pf else []) if (p.netQuantity or 0) != 0]
if not open_pos:
    raise SystemExit("No open positions.")

for p in sorted(open_pos, key=lambda x: x.pnl or 0):
    print(f"{p.symbol:<26}{p.netQuantity:>6}{r(p.avgBuyPrice):>10,.2f}"
          f"{r(p.avgSellPrice):>10,.2f}{r(p.lastTradedPrice):>10,.2f}{r(p.pnl):>12,.2f}")
```

```
py -3.12 examples/portfolio/open_positions_pnl.py
```

Real output (first rows only; the full run listed 14 open positions):

```
Symbol                       Qty   Buy avg  Sell avg       LTP      P&L Rs
NIFTY26O0622600CE            130     62.05     61.30     45.80   -2,161.25
NIFTY26O0622450PE             65     98.55     88.25     93.50     -997.75
NIFTY26O0622700CE             65     30.65      0.00     22.70     -516.75
NIFTY26O0622550CE            130     65.82     67.00     62.85     -234.00
NIFTY26O0622650CE             65     34.35      0.00     32.20     -139.75
ICICIBANK                     18  1,317.35  1,315.80  1,314.20      -59.80
...
Total P&L (all positions): Rs 7,306.50
```

## Go further

- Write the open-positions table to CSV (compare `examples/market_data/historical_market_data/ohlc_to_csv.py`).
- Run `portfolio_summary.py` before and after a UAT order from [Trading](05-trading.md) and compare margin used.
- Print a warning line when `netMarginAvailable` is negative.

## Common errors

| Symptom | Cause | Fix |
| --- | --- | --- |
| Funds show a tiny balance and a negative `Net margin available` | The UAT account holds about no funds, and test orders from [Trading](05-trading.md) block margin | Expected in UAT. Read it as margin used exceeding funds. |
| `No holdings found for this account.` or `HOLDINGS: none` | Empty account | The examples print this and exit. |
| `No open positions.` | Every position has `netQuantity` of 0 | Open a position in UAT, then re-run. |
| Numbers look 100x too large | Values are integer paise | Divide by 100 before printing. |

## Summary

Funds, holdings and positions each come from one `NubraPortfolio` call. Values are paise, and `holdingStats` / `positionStats` carry the totals. Combine the three calls for a one-screen summary.

[Home](README.md) | [← Previous: Trading](05-trading.md) | [Next: Recipes and Next Steps →](07-recipes-and-next-steps.md)
