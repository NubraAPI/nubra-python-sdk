"""Fetch open and closed positions with P&L in rupees.
Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env
Expect: a positions table (empty message if none) and total P&L.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.portfolio.portfolio_data import NubraPortfolio
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Default is the UAT sandbox. For live usage switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
portfolio = NubraPortfolio(nubra)

result = portfolio.positions()
pf = result.portfolio if result else None
if pf is None or not pf.positions:
    raise SystemExit("No positions found for this account.")

# The API returns integer paise; divide by 100 for rupees.
print(f"{'Symbol':<26}{'Net Qty':>8}{'LTP Rs':>12}{'P&L Rs':>12}")
for p in pf.positions:
    print(f"{p.symbol:<26}{p.netQuantity or 0:>8}"
          f"{(p.lastTradedPrice or 0) / 100:>12,.2f}{(p.pnl or 0) / 100:>12,.2f}")
print(f"Total P&L Rs {(pf.positionStats.totalPnl or 0) / 100:,.2f}")
