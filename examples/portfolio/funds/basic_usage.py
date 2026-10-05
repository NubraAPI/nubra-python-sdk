"""Fetch funds and margin, and print the key figures in rupees.
Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env
Expect: available margin, margin blocked, collateral and brokerage in rupees.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.portfolio.portfolio_data import NubraPortfolio
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Default is the UAT sandbox. For live usage switch to NubraEnv.PROD.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
portfolio = NubraPortfolio(nubra)

result = portfolio.funds()
pfm = result.portFundsAndMargin if result else None
if pfm is None:
    raise SystemExit("No funds data returned for this account.")

# The API returns integer paise; divide by 100 for rupees.
rupees = lambda paise: f"Rs {(paise or 0) / 100:,.2f}"
print(f"Client:                {pfm.clientCode}")
print(f"Start-of-day funds:    {rupees(pfm.startOfDayFunds)}")
print(f"Net margin available:  {rupees(pfm.netMarginAvailable)}")
print(f"Total margin blocked:  {rupees(pfm.totalMarginBlocked)}")
print(f"Total collateral:      {rupees(pfm.totalCollateral)}")
print(f"Brokerage:             {rupees(pfm.brokerage)}")
