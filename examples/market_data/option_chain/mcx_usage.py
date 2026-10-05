"""Fetch the nearest-expiry option chain for CRUDEOIL on MCX and print a summary.

Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env (env_creds=True)
Expect: spot, ATM strike, expiries, ATM call/put premium in rupees, strike count
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# MCX option chains are available on UAT. Switch to NubraEnv.PROD for live usage.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
market_data = MarketData(nubra)

# Pass the underlying symbol. Optionally add expiry="YYYYMMDD".
result = market_data.option_chain("CRUDEOIL", exchange="MCX")

if result is None:
    raise SystemExit("No option chain returned (check symbol / exchange / expiry)")

chain = result.chain
atm = chain.at_the_money_strike  # strikes and prices are in paise
print(f"{chain.asset} expiry {chain.expiry} | spot Rs {chain.current_price / 100:,.2f} | ATM strike {atm / 100:,.0f}")
print(f"Strikes: {len(chain.ce)} calls / {len(chain.pe)} puts | expiries: {chain.all_expiries}")

atm_ce = next((o for o in chain.ce if o.strike_price == atm), None)
atm_pe = next((o for o in chain.pe if o.strike_price == atm), None)
if atm_ce and atm_pe:
    print(f"ATM CE Rs {atm_ce.last_traded_price / 100:,.2f} (OI {atm_ce.open_interest}) | "
          f"ATM PE Rs {atm_pe.last_traded_price / 100:,.2f} (OI {atm_pe.open_interest})")
else:
    print("ATM strike not present on both sides of the chain")
