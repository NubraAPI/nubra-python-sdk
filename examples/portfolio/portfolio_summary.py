"""One-screen portfolio summary: funds, holdings and positions combined.
Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env
Expect: margin used/available, holdings value and P&L, positions P&L and open exposure in rupees.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.portfolio.portfolio_data import NubraPortfolio
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Default is the UAT sandbox. For live usage switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
portfolio = NubraPortfolio(nubra)

funds = portfolio.funds()
holdings = portfolio.holdings()
positions = portfolio.positions()

rs = lambda paise: f"Rs {(paise or 0) / 100:>14,.2f}"  # API values are integer paise

pfm = funds.portFundsAndMargin if funds else None
if pfm:
    print("FUNDS")
    print(f"  Margin available : {rs(pfm.netMarginAvailable)}")
    print(f"  Margin used      : {rs(pfm.totalMarginBlocked)}")
    print(f"  Collateral       : {rs(pfm.totalCollateral)}")

h = holdings.portfolio if holdings else None
if h and h.holdingStats:
    print("HOLDINGS")
    print(f"  Invested         : {rs(h.holdingStats.investedAmount)}")
    print(f"  Current value    : {rs(h.holdingStats.currentValue)}")
    print(f"  Total P&L        : {rs(h.holdingStats.totalPnl)}")
    print(f"  Day P&L          : {rs(h.holdingStats.dayPnl)}")
else:
    print("HOLDINGS: none")

p = positions.portfolio if positions else None
if p and p.positions:
    open_pos = [x for x in p.positions if (x.netQuantity or 0) != 0]
    # Exposure = |net qty| x LTP for each open position.
    exposure = sum(abs(x.netQuantity) * (x.lastTradedPrice or 0) for x in open_pos)
    print("POSITIONS")
    print(f"  Open positions   : {len(open_pos)}")
    print(f"  Open exposure    : {rs(exposure)}")
    print(f"  Realised P&L     : {rs(p.positionStats.realisedPnl)}")
    print(f"  Unrealised P&L   : {rs(p.positionStats.unrealisedPnl)}")
    print(f"  Total P&L        : {rs(p.positionStats.totalPnl)}")
else:
    print("POSITIONS: none")
