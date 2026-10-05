"""Fetch equity holdings with per-stock and total P&L in rupees.
Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env
Expect: a holdings table (empty message if none) and portfolio totals.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.portfolio.portfolio_data import NubraPortfolio
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Default is the UAT sandbox. For live usage switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
portfolio = NubraPortfolio(nubra)

result = portfolio.holdings()
pf = result.portfolio if result else None
if pf is None or not pf.holdings:
    raise SystemExit("No holdings found for this account.")

# The API returns integer paise; divide by 100 for rupees.
print(f"{'Symbol':<14}{'Qty':>6}{'Avg Rs':>12}{'LTP Rs':>12}{'Net P&L Rs':>14}")
for h in pf.holdings:
    print(f"{h.symbol:<14}{h.quantity:>6}{(h.avgPrice or 0) / 100:>12,.2f}"
          f"{(h.lastTradedPrice or 0) / 100:>12,.2f}{(h.netPnl or 0) / 100:>14,.2f}")

stats = pf.holdingStats
if stats:
    print(f"Invested Rs {(stats.investedAmount or 0) / 100:,.2f} | "
          f"Current Rs {(stats.currentValue or 0) / 100:,.2f} | "
          f"Total P&L Rs {(stats.totalPnl or 0) / 100:,.2f}")
