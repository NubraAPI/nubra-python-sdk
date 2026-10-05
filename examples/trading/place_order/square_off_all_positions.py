"""Square off every open position with market orders (UAT cleanup helper).
Type: mutating (UAT) - closes ALL open positions on the account
Needs: UAT login via env creds; market open
Expect: a table of open positions (P&L in rupees), the exit orders sent, then the positions still open.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
import time
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.portfolio.portfolio_data import NubraPortfolio
from nubra_python_sdk.trading.trading_data import NubraTrader

# Use NubraEnv.UAT for testing. Switch to NubraEnv.PROD for live usage (this trades real positions there).
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
portfolio = NubraPortfolio(nubra)
trader = NubraTrader(nubra)


def open_positions():
    result = portfolio.positions()
    if not result or isinstance(result, list) or not result.portfolio:
        return []
    return [p for p in result.portfolio.positions or [] if p.netQuantity and p.status == "OPEN"]


def show(positions):
    print(f"{'symbol':<24} {'net qty':>8} {'avg (Rs)':>10} {'ltp (Rs)':>10} {'P&L (Rs)':>12}")
    for p in positions:
        print(f"{p.symbol:<24} {p.netQuantity:>8} {(p.avgPrice or 0) / 100:>10,.2f} "
              f"{(p.lastTradedPrice or 0) / 100:>10,.2f} {(p.pnl or 0) / 100:>12,.2f}")


positions = open_positions()
if not positions:
    raise SystemExit("No open positions to square off.")
show(positions)

# The SDK sends one opposite-side order per open position (SELL for long, BUY for short).
# at_market_price=True uses MARKET/IOC orders; the default exits at LTP with limit orders.
result = trader.exit_all_positions(at_market_price=True)
for o in result.orders if result else []:
    print(f"Exit order {o.intentOrderId}: {o.status or 'SUBMITTED'}")
    if o.rejectionMsg:
        print("  Rejected:", o.rejectionMsg)

time.sleep(3)
left = open_positions()
print(f"{len(left)} position(s) still open.")
if left:
    show(left)
