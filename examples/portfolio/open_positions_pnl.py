"""Open positions P&L table, sorted from worst to best.
Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env
Expect: a table of open positions with avg prices, LTP and P&L in rupees, plus the total.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.portfolio.portfolio_data import NubraPortfolio
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Default is the UAT sandbox. For live usage switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
portfolio = NubraPortfolio(nubra)

result = portfolio.positions()
pf = result.portfolio if result else None
open_pos = [p for p in (pf.positions if pf else []) if (p.netQuantity or 0) != 0]
if not open_pos:
    raise SystemExit("No open positions.")

# Prices are integer paise; divide by 100 for rupees.
r = lambda paise: (paise or 0) / 100
print(f"{'Symbol':<26}{'Qty':>6}{'Buy avg':>10}{'Sell avg':>10}{'LTP':>10}{'P&L Rs':>12}")
for p in sorted(open_pos, key=lambda x: x.pnl or 0):
    print(f"{p.symbol:<26}{p.netQuantity:>6}{r(p.avgBuyPrice):>10,.2f}"
          f"{r(p.avgSellPrice):>10,.2f}{r(p.lastTradedPrice):>10,.2f}{r(p.pnl):>12,.2f}")
print(f"Total P&L (all positions): Rs {r(pf.positionStats.totalPnl):,.2f}")
