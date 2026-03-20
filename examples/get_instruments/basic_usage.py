from nubra_python_sdk.refdata.instruments import InstrumentData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Initialize the SDK client.
# Use NubraEnv.UAT for testing and NubraEnv.UAT for production.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

instruments = InstrumentData(nubra)

# Get all instruments as a pandas DataFrame.
instruments_df = instruments.get_instruments_dataframe()
print(f"Total instruments: {len(instruments_df)}")

# Get one instrument by ref_id.
instrument = instruments.get_instrument_by_ref_id(71878)
print(instrument)

# Get one instrument by exchange trading symbol.
instrument = instruments.get_instrument_by_symbol("HDFCBANK", exchange="BSE")
print(instrument)

# Get one instrument by Nubra internal name.
instrument = instruments.get_instrument_by_nubra_name("STOCK_HDFCBANK.NSECM")
print(instrument)

# Fetch matching instruments with structured filters.
matches = instruments.get_instruments_by_pattern([
    {
        "exchange": "NSE",
        "asset": "NIFTY",
        "derivative_type": "OPT",
        "expiry": "20260217",
        "strike_price": "2580000",
        "option_type": "CE",
        "asset_type": "INDEX_FO"
    }
])
print(matches)
