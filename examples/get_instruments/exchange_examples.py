"""Load the NSE, BSE and MCX instrument masters.
Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env
Expect: the last NSE rows, the BSE HDFCBANK record and the last MCX CRUDEOIL rows.
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.refdata.instruments import InstrumentData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Use NubraEnv.UAT for testing. Switch to NubraEnv.PROD for live usage.
# Note: UAT and PROD ref_id values can differ; resolve instruments in each environment.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
instruments = InstrumentData(nubra)

# NSE is the default when exchange is omitted.
nse_df = instruments.get_instruments_dataframe(exchange="NSE")
print(nse_df.tail(10))

# BSE
bse_df = instruments.get_instruments_dataframe(exchange="BSE")
bse_hdfc = instruments.get_instrument_by_symbol("HDFCBANK", exchange="BSE")
# Lookups return a dict with "msg" when the symbol is not found.
print(bse_hdfc["msg"] if isinstance(bse_hdfc, dict) else bse_hdfc)

# MCX
mcx_df = instruments.get_instruments_dataframe(exchange="MCX")
print(mcx_df[mcx_df["asset"] == "CRUDEOIL"].tail(10))
