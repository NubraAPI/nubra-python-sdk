# 2. Instruments

Find the exact contract you want, by symbol, name, filter, expiry or index, before you ask for prices or place orders.

[Home](README.md) | [← Previous: 1. Authentication](01-authentication.md) | [Next: 3. Market data →](03-market-data.md)

## In this guide

- Load the instrument master per exchange (NSE, BSE, MCX) as a pandas DataFrame.
- Look up one instrument by `ref_id`, symbol or Nubra name.
- Filter by asset and derivative type, or search by partial name.
- List upcoming expiries and find the nearest future.
- Download the public index master without logging in.

## You need

A UAT login from [1. Authentication](01-authentication.md) (`env_creds=True`). All examples are read-only. `index_master.py` needs only internet.

## Key ideas

| Idea | Detail |
| --- | --- |
| Instrument master | A table of every tradable contract on an exchange. `InstrumentData(nubra).get_instruments_dataframe(exchange="NSE")` returns it. |
| `ref_id` | Numeric id of a contract. UAT and PROD `ref_id` values can differ, so resolve them in each environment. |
| `stock_name` | Exchange trading symbol, e.g. `HDFCBANK`, `NIFTY26O0623250CE`, `FUT_CRUDEOIL_20261019`. |
| `nubra_name` | Nubra's internal name, e.g. `STOCK_HDFCBANK.NSECM`, `OPT_NIFTY_20261006_CE_2325000`. |
| `derivative_type` | `STOCK`, `FUT` or `OPT`. |
| `expiry` | Integer `YYYYMMDD`, e.g. `20261006`. |
| Paise | Strikes, `tick_size` and `underlying_prev_close` are integer paise. `underlying_prev_close=72120` is Rs 721.20; `strike_price=2325000` is 23,250. |
| `exchange` | Accepts the string `"NSE"` or `ExchangeEnum.NSE`. Two `ExchangeEnum` classes exist (`nubra_python_sdk.marketdata.validation` and `nubra_python_sdk.trading.trading_enum`); both are str-enums with `NSE`, `BSE`, `MCX`. |
| `tick_size` | In paise. Every order price must be rounded to a multiple of it (see `to_tick()` in the [trading examples](../../examples/trading/place_order/basic_usage.py)). |
| `get_instruments_by_pattern` | Takes a dict or a list of dicts. Keys (all optional): `exchange`, `asset`, `derivative_type`, `asset_type`, `expiry`, `strike_price`, `option_type`, `isin`. `expiry` (`YYYYMMDD`) and `strike_price` (paise) are accepted as an int or a digit string. `asset_type` is optional, e.g. `INDEX_FO` for index options. |
| Not found | Lookups return a **dict with a `msg` key**, not an exception. Check `isinstance(result, dict)`. |

## The examples, in order

### 1. Look up by ref_id, symbol, name and filters: [`basic_usage.py`](../../examples/get_instruments/basic_usage.py)

The tour of every lookup method. Use `get_instrument_by_symbol` when you know the ticker, `get_instrument_by_ref_id` when you stored an id, and `get_instruments_by_pattern` to pin down an option by strike and expiry. Strikes are paise, so the example picks a real expiry from the master instead of hardcoding one.

```python
instruments_df = instruments.get_instruments_dataframe(exchange="NSE")
# ref_id values can differ between environments; resolve it with get_instrument_by_symbol.
instrument = instruments.get_instrument_by_ref_id(71878, exchange="NSE")
instrument = instruments.get_instrument_by_symbol("HDFCBANK", exchange="NSE")
# Lookups return a dict with "msg" when nothing is found.
if isinstance(instrument, dict):
    raise SystemExit(f"Symbol lookup failed: {instrument['msg']}")
instrument = instruments.get_instrument_by_nubra_name("STOCK_HDFCBANK.NSECM", exchange="NSE")
matches = instruments.get_instruments_by_pattern([
    {"exchange": "NSE", "asset": "NIFTY", "derivative_type": "OPT",
     "expiry": expiry, "strike_price": strike, "option_type": "CE",
     "asset_type": "INDEX_FO"}
])
```

Run: `py -3.12 examples/get_instruments/basic_usage.py`

Real output (trimmed, long lines shortened):

```
Total instruments: 83147
ref_id=71878 ... stock_name='RELIANCE' nubra_name='STOCK_RELIANCE.NSECM' lot_size=1 ... tick_size=10 underlying_prev_close=116770
ref_id=71496 ... stock_name='HDFCBANK' nubra_name='STOCK_HDFCBANK.NSECM' lot_size=1 ... tick_size=5 underlying_prev_close=72120
[InstrumentDataWrapper(ref_id=1722304, option_type='CE', token=40749, stock_name='NIFTY26O0623250CE',
  nubra_name='OPT_NIFTY_20261006_CE_2325000', lot_size=65, asset='NIFTY', exchange='NSE',
  derivative_type='OPT', asset_type='INDEX_FO', tick_size=5, underlying_prev_close=2242195,
  strike_price=2325000, expiry=20261006)]
```

Here `116770` is Rs 1167.70 (RELIANCE previous close) and the NIFTY lot size is 65.

### 2. Filter by exchange, asset and derivative type: [`filtered_lookup_example.py`](../../examples/get_instruments/filtered_lookup_example.py)

`get_instruments(...)` takes keyword filters and returns a list. Handy when you know the underlying but not the exact contract.

```python
results = instruments.get_instruments(
    exchange="NSE",
    asset="HDFCBANK",
    derivative_type="STOCK",
)

if not results:
    raise SystemExit("No instruments matched these filters.")
print(f"{len(results)} match(es). First: {results[0]}")
```

Run: `py -3.12 examples/get_instruments/filtered_lookup_example.py`

Real output:

```
1 match(es). First: ref_id=71496 option_type='N/A' token=1333 stock_name='HDFCBANK' nubra_name='STOCK_HDFCBANK.NSECM' lot_size=1 asset='HDFCBANK' exchange='NSE' derivative_type='STOCK' isin='INE040A01034' asset_type='STOCKS' tick_size=5 underlying_prev_close=72120 strike_price=None expiry=None
```

### 3. NSE, BSE and MCX masters: [`exchange_examples.py`](../../examples/get_instruments/exchange_examples.py)

Same API, different `exchange`. NSE is the default if you omit it. On MCX you filter by `asset`, such as `CRUDEOIL`, to see its contracts and options.

```python
nse_df = instruments.get_instruments_dataframe(exchange="NSE")
bse_hdfc = instruments.get_instrument_by_symbol("HDFCBANK", exchange="BSE")
print(bse_hdfc["msg"] if isinstance(bse_hdfc, dict) else bse_hdfc)
mcx_df = instruments.get_instruments_dataframe(exchange="MCX")
print(mcx_df[mcx_df["asset"] == "CRUDEOIL"].tail(10))
```

Run: `py -3.12 examples/get_instruments/exchange_examples.py`

Real output (trimmed; the NSE and MCX tables are wide, only the BSE record and the start of the MCX table are shown):

```
ref_id=845149 strike_price=None option_type='N/A' token=500180 stock_name='HDFCBANK' nubra_name='STOCK_HDFCBANK_EQ_A.BSECM' lot_size=1 asset='HDFCBANK' expiry=None exchange='BSE' derivative_type='STOCK' isin='INE040A01034' asset_type='STOCKS' tick_size=5 underlying_prev_close=71935
        ref_id  strike_price  ...  asset_code  zanskar_id
11803  1734034        885000  ...  OFCRUDEOIL     11803.0
11804  1734035        880000  ...  OFCRUDEOIL     11804.0
```

Note the BSE `nubra_name` ends in `.BSECM`; NSE ends in `.NSECM`.

### 4. Search by partial name: [`find_instrument_by_name.py`](../../examples/get_instruments/find_instrument_by_name.py)

When you do not remember the exact symbol, filter the DataFrame on `stock_name` or `asset`. `tick_size` is in paise (5 = Rs 0.05), and it is the price step you must respect when ordering.

```python
df = instruments.get_instruments_dataframe(exchange="NSE")
cash = df[df["derivative_type"] == "STOCK"]
hits = cash[
    cash["stock_name"].str.contains(QUERY, case=False, na=False)
    | cash["asset"].str.contains(QUERY, case=False, na=False)
]
```

Run: `py -3.12 examples/get_instruments/find_instrument_by_name.py`

Real output (first rows):

```
23 match(es) for 'HDFC':
 ref_id stock_name      asset  lot_size  tick_size
  71287   HDFCLIFE   HDFCLIFE         1          5
  71496   HDFCBANK   HDFCBANK         1          5
  72163    HDFCAMC    HDFCAMC         1         10
  72872 HDFCNEXT50 HDFCNEXT50         1          1
  72873 HDFCNIF100 HDFCNIF100         1          1
```

The script then resolves the first hit exactly and prints `First match ref_id: 71287`. A fuzzy search returns ETFs too; pick by `stock_name`, not by position.

### 5. Upcoming expiries and lot size: [`upcoming_expiries.py`](../../examples/get_instruments/upcoming_expiries.py)

Groups futures and options by expiry date with days left, lot size and contract count. Set `UNDERLYING` and `EXCHANGE` at the top (for example `BANKNIFTY`, or `MCX` with `CRUDEOIL`).

```python
UNDERLYING = "NIFTY"  # try BANKNIFTY, RELIANCE ...
EXCHANGE = "NSE"      # or "MCX" with e.g. "CRUDEOIL"
df = instruments.get_instruments_dataframe(exchange=EXCHANGE)
fno = df[(df["asset"] == UNDERLYING) & (df["derivative_type"].isin(["FUT", "OPT"]))].copy()
fno["expiry"] = fno["expiry"].astype(int)
```

Run: `py -3.12 examples/get_instruments/upcoming_expiries.py`

Real output (first 8 lines; the run date was 2026-10-05):

```
NIFTY (NSE) expiries:
Expiry        Days  Lot size  Contracts  Types
2026-10-06       1        65        488  OPT
2026-10-13       8        65        472  OPT
2026-10-19      14        65        464  OPT
2026-10-27      22        65        517  FUT/OPT
2026-11-03      29        65        464  OPT
2026-11-23      49        65        501  FUT/OPT
```

Only the monthly expiries (`FUT/OPT`) have a future. Weekly expiries are options only.

### 6. Nearest future: [`nearest_future.py`](../../examples/get_instruments/nearest_future.py)

Finds the nearest live futures contract for an NSE stock and two MCX commodities. MCX contracts are addressed by their full name, like `FUT_CRUDEOIL_20261019`, never by the bare asset `GOLD`.

```python
fut = df[(df["asset"] == asset) & (df["derivative_type"] == "FUT") & (pd.to_numeric(df["expiry"], errors="coerce") >= today)]
if fut.empty:
    return None
return fut.sort_values("expiry").iloc[0]
```

Run: `py -3.12 examples/get_instruments/nearest_future.py`

Real output:

```
NSE HDFCBANK: HDFCBANK26OCTFUT | expiry 2026-10-27 | lot 650 | ref_id 1642524
MCX CRUDEOIL: FUT_CRUDEOIL_20261019 | expiry 2026-10-19 | lot 100 | ref_id 1439763
MCX GOLD: FUT_GOLD_20261005 | expiry 2026-10-05 | lot 100 | ref_id 1318615
```

The GOLD contract expired on the day of the run, so check the `expiry` before relying on "nearest".

### 7. Index master, no login: [`index_master.py`](../../examples/get_instruments/index_master.py)

A public CSV of all indices (exchange, symbol and name). It uses plain `requests`, so no SDK login is needed. Use it to find the exact index symbol before requesting index data.

```python
INDEX_URL = "https://api.nubra.io/public/indexes?format=csv"

response = requests.get(INDEX_URL, timeout=10)
response.raise_for_status()
```

Run: `py -3.12 examples/get_instruments/index_master.py`

Real output (first 4 lines):

```
Total indices fetched: 181
{'EXCHANGE': 'BSE', 'INDEX_SYMBOL': 'SENSEX50', 'ZANSKAR_INDEX_SYMBOL': 'SENSEX50', 'INDEX_NAME': 'Bse Sensex 50'}
{'EXCHANGE': 'BSE', 'INDEX_SYMBOL': 'ENERGY', 'ZANSKAR_INDEX_SYMBOL': 'ENERGY', 'INDEX_NAME': 'Bse Energy'}
{'EXCHANGE': 'BSE', 'INDEX_SYMBOL': 'TELCOM', 'ZANSKAR_INDEX_SYMBOL': 'TELCOM', 'INDEX_NAME': 'BSE Telecommunication'}
```

## Go further

1. Change `QUERY` in `find_instrument_by_name.py` to `TATA`, and filter the hits to `tick_size == 5`.
2. Run `upcoming_expiries.py` with `UNDERLYING = "BANKNIFTY"`, then with `EXCHANGE = "MCX"` and `UNDERLYING = "CRUDEOIL"`. Compare lot sizes.
3. Using the master DataFrame, print the `ref_id` of the nearest NIFTY monthly future and convert its `underlying_prev_close` from paise to rupees.

## Common errors

| Error text | Cause | Fix |
| --- | --- | --- |
| `Invalid asset name` for MCX `GOLD` | MCX contracts are addressed by full contract name, not the bare asset | Use the full name such as `FUT_GOLD_20261204`; find it with `nearest_future.py` |
| Result is a dict with `msg` instead of an instrument | `get_instrument_by_symbol`, `_by_ref_id` and `_by_nubra_name` return a dict when nothing matches, and do not raise | Check `isinstance(result, dict)` and print `result["msg"]` |
| `ref_id` from one environment fails in another | UAT and PROD `ref_id` values can differ | Re-resolve the instrument in the environment you are using |
| Asked to log in again | The SDK keeps the session in `auth_data.db` in the current folder, and deletes it if the MPIN check fails | Run from the repo root; check the MPIN in `.env` |
| `charmap` codec error when printing tables | Windows console encoding | Set `PYTHONIOENCODING=utf-8` |

## Summary

Load the master with `get_instruments_dataframe`, then narrow it with the `get_instrument_by_*` methods, `get_instruments` or plain pandas. Expiries are `YYYYMMDD` integers, money fields are paise, and a not-found lookup is a dict with `msg`. Use full contract names on MCX.

[Home](README.md) | [← Previous: 1. Authentication](01-authentication.md) | [Next: 3. Market data →](03-market-data.md)
