# Get Instruments examples

Default environment is UAT. Switch to `NubraEnv.PROD` for live usage. Prices and strikes in the master are in paise.

Notes:

- `exchange` accepts the string `"NSE"` or `ExchangeEnum.NSE`. Two `ExchangeEnum` classes exist (`nubra_python_sdk.marketdata.validation` and `nubra_python_sdk.trading.trading_enum`); both are str-enums with `NSE`, `BSE`, `MCX`.
- `tick_size` is in paise. Round every order price to a multiple of it (see `to_tick()` in the trading examples).
- `get_instruments_by_pattern` takes a dict or a list of dicts; `expiry` (`YYYYMMDD`) and `strike_price` (paise) are accepted as int or digit string, and `asset_type` is optional (e.g. `INDEX_FO`).

| File | What it does | Type |
| --- | --- | --- |
| `basic_usage.py` | Look up by ref_id, symbol, Nubra name and filters | read-only |
| `exchange_examples.py` | Load NSE, BSE and MCX instrument masters | read-only |
| `filtered_lookup_example.py` | Filter by exchange, asset and derivative type | read-only |
| `find_instrument_by_name.py` | Search stocks by partial name or symbol | read-only |
| `upcoming_expiries.py` | List expiries and lot size for an underlying | read-only |
| `nearest_future.py` | Nearest-expiry futures for NSE and MCX (full MCX contract names) | read-only |
| `index_master.py` | Download the public index master CSV (no login) | read-only |
