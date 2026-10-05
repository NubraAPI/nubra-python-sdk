"""Look up instruments by ref_id, symbol, Nubra name and structured filters.
Type: read-only
Needs: UAT login via PHONE_NO / MPIN in .env
Expect: instrument count, then the matching instrument records (prices/strikes in paise).
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from nubra_python_sdk.refdata.instruments import InstrumentData
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# Initialize the SDK client.
# Use NubraEnv.UAT for testing. Switch to NubraEnv.PROD for live usage.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

instruments = InstrumentData(nubra)

# Get all NSE instruments as a pandas DataFrame.
instruments_df = instruments.get_instruments_dataframe(exchange="NSE")
print(f"Total instruments: {len(instruments_df)}")

# Get one instrument by ref_id.
instrument = instruments.get_instrument_by_ref_id(71878, exchange="NSE")
print(instrument)

# Get one instrument by exchange trading symbol.
instrument = instruments.get_instrument_by_symbol("HDFCBANK", exchange="NSE")
# Lookups return a dict with "msg" when nothing is found.
if isinstance(instrument, dict):
    raise SystemExit(f"Symbol lookup failed: {instrument['msg']}")
print(instrument)

# Get one instrument by Nubra internal name.
instrument = instruments.get_instrument_by_nubra_name("STOCK_HDFCBANK.NSECM", exchange="NSE")
print(instrument)

# Fetch matching instruments with structured filters.
# Expiries roll, so pick a live one from the master instead of hardcoding a date.
nifty_opts = instruments_df[(instruments_df["asset"] == "NIFTY") & (instruments_df["derivative_type"] == "OPT")]
if nifty_opts.empty:
    raise SystemExit("No NIFTY options in the instrument master.")
expiry_int = int(nifty_opts["expiry"].astype(int).min())
strikes = sorted(nifty_opts[nifty_opts["expiry"].astype(int) == expiry_int]["strike_price"].astype(int).unique())
expiry = str(expiry_int)
strike = str(strikes[len(strikes) // 2])  # a mid-range strike, in paise

matches = instruments.get_instruments_by_pattern([
    {
        "exchange": "NSE",
        "asset": "NIFTY",
        "derivative_type": "OPT",
        "expiry": expiry,
        "strike_price": strike,
        "option_type": "CE",
        "asset_type": "INDEX_FO"
    }
])
print(matches)
