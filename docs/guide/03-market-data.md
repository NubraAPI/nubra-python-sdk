# 3. Market Data

Prices, order-book depth, option chains, historical candles and company fundamentals, all through one `MarketData` object.

[Home](README.md) | [← Previous: Instruments](02-instruments.md) | [Next: Realtime Data →](04-realtime.md)

## In this guide

- Fetch the latest price, previous close and % change for NSE, BSE and MCX symbols.
- Read 5-level market depth and compute spread and bid/ask imbalance.
- Pull an option chain, pick an expiry, and turn it into a DataFrame (PCR, OI walls, IV skew).
- Download historical candles (daily, intraday, monthly) and save them to CSV.
- Read company fundamentals: ratios, cash flow, balance sheet, P&L, corporate actions, shareholding.

## You need

- A working install and `.env`: see [00-setup.md](00-setup.md).
- A logged-in session (`InitNubraSdk(NubraEnv.UAT, env_creds=True)`): see [01-authentication.md](01-authentication.md).
- `pandas` for the DataFrame recipes.

All examples default to UAT and are read-only (`ohlc_to_csv.py` also writes one local CSV). Each file has a comment showing how to switch to `NubraEnv.PROD`.

## Concepts

| Topic | Rule |
|---|---|
| Prices | Integer paise. `116770` = Rs 1167.70. Divide by 100 for rupees. Candle values and option strikes are paise too. |
| Exchanges | `NSE`, `BSE`, `MCX`. `current_price` and `option_chain` support only these three. |
| `symbol` vs `ref_id` | `current_price`, `option_chain` and `historical_data` take a symbol. `quote` (depth) takes a `ref_id`, so resolve it first with `get_instrument_by_symbol` ([02-instruments.md](02-instruments.md)). |
| Option chain expiry | A `YYYYMMDD` string, e.g. `"20261006"`. Omit it for the nearest expiry; `chain.all_expiries` lists the rest. |
| MCX futures | Use the full contract name, e.g. `FUT_CRUDEOIL_20261019`, not bare `CRUDEOIL`. Find it in the MCX instrument master. |
| Dates in history | UTC ISO strings (`2026-10-05T07:02:14.000Z`). Build them relative to now. |

## The examples, in order

All paths below are under `examples/market_data/`. Run from the repo root.

### Current price

#### [current_price/basic_usage.py](../../examples/market_data/current_price/basic_usage.py)

Latest price, previous close and % change for an index and a stock. The first call to make before anything else.

```python
nifty_price = market_data.current_price("NIFTY", exchange="NSE")
reliance_price = market_data.current_price("RELIANCE", exchange="NSE")

def rs(paise):
    # The API returns integer paise; show rupees.
    return "n/a" if paise is None else f"Rs {paise / 100:,.2f}"
```

```
py -3.12 examples/market_data/current_price/basic_usage.py
```

Real output:
```
NIFTY: Rs 22,451.35 | prev close Rs 22,421.95 | change 0.13112152%
RELIANCE: Rs 1,177.20 | prev close Rs 1,167.70 | change 0.81356514%
```

#### [current_price/bse_usage.py](../../examples/market_data/current_price/bse_usage.py)

Same call with `exchange="BSE"` for SENSEX and HDFCBANK. Only the exchange argument changes.

```python
sensex_price = market_data.current_price("SENSEX", exchange="BSE")
hdfc_price = market_data.current_price("HDFCBANK", exchange="BSE")
```

```
py -3.12 examples/market_data/current_price/bse_usage.py
```

Real output:
```
SENSEX: Rs 71,993.75 | prev close Rs 71,909.70 | change 0.116882704%
HDFCBANK: Rs 705.30 | prev close Rs 719.35 | change -1.9531522%
```

#### [current_price/mcx_usage.py](../../examples/market_data/current_price/mcx_usage.py)

MCX needs the full contract name. This example finds the nearest unexpired future in the MCX instrument master, then prices it. Use this pattern for any commodity.

```python
mcx = instruments.get_instruments_dataframe(exchange="MCX")
today = int(date.today().strftime("%Y%m%d"))

def nearest_future(asset):
    futures = mcx[(mcx["asset"] == asset) & (mcx["derivative_type"] == "FUT") & (mcx["expiry"].astype(int) > today)]
    if futures.empty:
        return None
    return futures.sort_values("expiry").iloc[0]["stock_name"]
```

```
py -3.12 examples/market_data/current_price/mcx_usage.py
```

Real output:
```
FUT_CRUDEOIL_20261019: Rs 8,686.00 | prev close Rs 8,916.00 | change -2.579632%
FUT_GOLD_20261204: Rs 149,630.00 | prev close Rs 150,390.00 | change -0.50535274%
```

#### [current_price/watchlist_table.py](../../examples/market_data/current_price/watchlist_table.py)

A multi-symbol watchlist as a DataFrame sorted by % change: your morning scan in one screen. Symbols with no price are collected and reported instead of crashing the loop.

```python
watchlist = [("NIFTY", "NSE"), ("RELIANCE", "NSE"), ("HDFCBANK", "NSE"), ("INFY", "NSE"), ("SENSEX", "BSE")]
for symbol, exchange in watchlist:
    p = market_data.current_price(symbol, exchange=exchange)
    if p is None or not p.price:
        failed.append(f"{exchange}:{symbol}")
        continue
    rows.append({"symbol": symbol, "price": p.price / 100, "prev_close": (p.prev_close or 0) / 100, ...})
table = pd.DataFrame(rows).sort_values("change_%", ascending=False)
```

```
py -3.12 examples/market_data/current_price/watchlist_table.py
```

Real output:
```
  symbol     price  prev_close  change_%
RELIANCE  1,176.80    1,167.70      0.78
   NIFTY 22,449.40   22,421.95      0.12
  SENSEX 71,987.77   71,909.70      0.11
HDFCBANK    705.40      721.20     -2.19
    INFY  1,011.35    1,035.00     -2.29
```

### Market quotes and depth

`quote()` returns the order book. It needs a `ref_id`, so each example resolves the symbol first and handles the `{"msg": ...}` dict returned when a symbol is not found.

#### [market_quotes/basic_usage.py](../../examples/market_data/market_quotes/basic_usage.py)

Top-5 bid/ask levels for HDFCBANK on NSE. Depth shows where resting liquidity sits around the last price.

```python
instrument = instruments.get_instrument_by_symbol("HDFCBANK", exchange="NSE")
if isinstance(instrument, dict):  # not found -> {"msg": ...}
    raise SystemExit(f"Lookup failed: {instrument.get('msg')}")
quote = market_data.quote(ref_id=instrument.ref_id, levels=5)
book = quote.orderBook
```

```
py -3.12 examples/market_data/market_quotes/basic_usage.py
```

Real output:
```
HDFCBANK last traded price: Rs 705.70  volume: 44836878
   BID qty     BID Rs |     ASK Rs    ASK qty
      1880     705.55 |     705.70        450
      7334     705.50 |     705.75       1818
      7641     705.45 |     705.80        972
      6575     705.40 |     705.85       2835
      5096     705.35 |     705.90       2529
```

#### [market_quotes/bse_usage.py](../../examples/market_data/market_quotes/bse_usage.py)

Identical flow on BSE (`exchange="BSE"`). Compare its volume and spread with NSE to see where liquidity is.

```
py -3.12 examples/market_data/market_quotes/bse_usage.py
```

Real output:
```
HDFCBANK last traded price: Rs 705.80  volume: 1667241
   BID qty     BID Rs |     ASK Rs    ASK qty
       443     705.50 |     705.75        300
       357     705.45 |     705.80        579
       621     705.40 |     705.85        297
      1368     705.35 |     705.90        167
       682     705.30 |     705.95        224
```

#### [market_quotes/mcx_usage.py](../../examples/market_data/market_quotes/mcx_usage.py)

Depth for the nearest CRUDEOIL future. The `ref_id` comes straight from the MCX instrument DataFrame instead of a symbol lookup.

```python
ref_id = int(futures.iloc[0]["ref_id"])
quote = market_data.quote(ref_id=ref_id, levels=5)
```

```
py -3.12 examples/market_data/market_quotes/mcx_usage.py
```

Real output:
```
FUT_CRUDEOIL_20261019 last traded price: Rs 8,682.00  volume: 1151900
   BID qty     BID Rs |     ASK Rs    ASK qty
       200   8,683.00 |   8,686.00        400
       500   8,682.00 |   8,687.00        500
       800   8,681.00 |   8,688.00        600
       400   8,680.00 |   8,689.00       1300
       400   8,679.00 |   8,690.00        300
```

#### [market_quotes/depth_imbalance.py](../../examples/market_data/market_quotes/depth_imbalance.py)

Turns depth into two numbers a trader uses: spread, and the bid/ask quantity imbalance across 5 levels. Positive means buyers are heavier. It exits cleanly if the book is empty (market closed).

```python
best_bid, best_ask = book.bid[0].price, book.ask[0].price  # paise
bid_qty = sum(level.quantity for level in book.bid)
ask_qty = sum(level.quantity for level in book.ask)
imbalance = (bid_qty - ask_qty) / (bid_qty + ask_qty) * 100 if bid_qty + ask_qty else 0.0
```

```
py -3.12 examples/market_data/market_quotes/depth_imbalance.py
```

Real output:
```
RELIANCE LTP Rs 1,176.70
Best bid Rs 1,176.60 | best ask Rs 1,176.70 | spread Rs 0.10
Depth (5 levels): bid qty 1,872 vs ask qty 6,461 | imbalance -55.1% (sellers heavier)
```

### Option chain

`option_chain(symbol, expiry=None, exchange=...)` returns `result.chain` with `ce` and `pe` lists, `current_price`, `at_the_money_strike`, `expiry` and `all_expiries`. Strikes and premiums are paise.

#### [option_chain/basic_usage.py](../../examples/market_data/option_chain/basic_usage.py)

NIFTY chain summary: spot, ATM strike, and ATM call/put premium with open interest. Gives you the ATM straddle cost at a glance.

```python
result = market_data.option_chain("NIFTY", exchange="NSE")
chain = result.chain
atm = chain.at_the_money_strike  # strikes and prices are in paise
atm_ce = next((o for o in chain.ce if o.strike_price == atm), None)
atm_pe = next((o for o in chain.pe if o.strike_price == atm), None)
```

```
py -3.12 examples/market_data/option_chain/basic_usage.py
```

Real output (expiries list shortened here):
```
NIFTY expiry 20261006 | spot Rs 22,449.50 | ATM strike 22,450
Strikes: 91 calls / 91 puts | expiries: ['20261006', '20261013', '20261019', '20261027', ...]
ATM CE Rs 112.70 (OI 9141860) | ATM PE Rs 90.75 (OI 10574525)
```

#### [option_chain/bse_usage.py](../../examples/market_data/option_chain/bse_usage.py)

SENSEX chain on BSE: `option_chain("SENSEX", exchange="BSE")`. Same code, different exchange.

```
py -3.12 examples/market_data/option_chain/bse_usage.py
```

Real output (expiries list shortened here):
```
SENSEX expiry 20261008 | spot Rs 71,983.16 | ATM strike 72,000
Strikes: 144 calls / 144 puts | expiries: ['20261008', '20261015', '20261022', '20261029', ...]
ATM CE Rs 560.70 (OI 720540) | ATM PE Rs 449.55 (OI 925980)
```

#### [option_chain/mcx_usage.py](../../examples/market_data/option_chain/mcx_usage.py)

CRUDEOIL chain on MCX: `option_chain("CRUDEOIL", exchange="MCX")`. The bare asset name is correct here; full contract names are for futures prices and quotes.

```
py -3.12 examples/market_data/option_chain/mcx_usage.py
```

Real output:
```
CRUDEOIL expiry 20261015 | spot Rs 8,687.00 | ATM strike 8,700
Strikes: 37 calls / 37 puts | expiries: ['20261015', '20261117', '20261216']
ATM CE Rs 333.70 (OI 3134) | ATM PE Rs 344.30 (OI 4055)
```

#### [option_chain/option_chain_dataframe.py](../../examples/market_data/option_chain/option_chain_dataframe.py)

Flattens the chain into a strike-aligned DataFrame (calls and puts side by side), shows an ATM window, then computes the numbers option traders watch: put/call ratio by OI, max-OI support and resistance, and IV skew.

```python
def side(options, tag):
    df = pd.DataFrame([o.model_dump() for o in options], columns=["strike_price", *FIELDS])
    return df.rename(columns={k: f"{tag}_{v}" for k, v in FIELDS.items()})

df = side(chain.ce, "ce").merge(side(chain.pe, "pe"), on="strike_price", how="outer").sort_values("strike_price")
```

```
py -3.12 examples/market_data/option_chain/option_chain_dataframe.py
```

Real output (first 8 lines; the script prints 11 strikes, then PCR, support/resistance and skew):
```
NIFTY expiry 20261006 | spot 22,446.25 | ATM strike 22,450
     ce_oi    ce_iv  ce_ltp  strike  pe_ltp    pe_iv    pe_oi
  732810.0 0.229287  295.45 22200.0   26.25 0.228142 10848955
  498940.0 0.223565  252.00 22250.0   34.20 0.222802  5524545
 2318095.0 0.218836  213.75 22300.0   44.00 0.217844 13440505
 1602770.0 0.213190  175.95 22350.0   56.85 0.212656  7130760
 7159555.0 0.208003  141.00 22400.0   73.35 0.208537 18098730
 9097140.0 0.203731  109.45 22450.0   93.85 0.203807 10668450
```

#### [option_chain/nearest_expiry.py](../../examples/market_data/option_chain/nearest_expiry.py)

Reusable helper: pick the earliest expiry that is today or later, then fetch that chain explicitly. `YYYYMMDD` strings sort correctly as plain strings.

```python
def nearest_expiry(expiries, today=None):
    """Earliest expiry (YYYYMMDD string) that is today or later, else None."""
    today = (today or date.today()).strftime("%Y%m%d")
    upcoming = sorted(e for e in expiries if e >= today)
    return upcoming[0] if upcoming else None
```

```
py -3.12 examples/market_data/option_chain/nearest_expiry.py
```

Real output (expiry list shortened here):
```
All expiries: ['20261006', '20261013', '20261019', '20261027', '20261103', ...]
Nearest expiry: 20261006 (NIFTY)
Spot Rs 22,446.80 | ATM strike 22,450
```

#### [option_chain/compare_expiries.py](../../examples/market_data/option_chain/compare_expiries.py)

Two upcoming expiries side by side: ATM straddle price, average ATM IV, PCR, and the max-OI strikes. Shows how premium and positioning differ between the near and next expiry.

```python
expiries = sorted(e for e in first.chain.all_expiries if e >= today)[:2]
result = market_data.option_chain("NIFTY", expiry=expiry, exchange="NSE")  # YYYYMMDD string
...
rows = {e: summarise(e) for e in expiries}
print(pd.DataFrame(rows).to_string())
```

```
py -3.12 examples/market_data/option_chain/compare_expiries.py
```

Real output:
```
                              20261006      20261013
spot                      22447.400000  22447.400000
ATM strike                22450.000000  22450.000000
ATM straddle Rs             203.200000    422.650000
ATM IV (avg)                  0.203693      0.157273
PCR (OI)                      0.740000      0.880000
Resistance (max call OI)  22600.000000  24000.000000
Support (max put OI)      22400.000000  20500.000000
```

### Historical data

`historical_data(payload)` takes a dict: `exchange`, `type` (`STOCK`, `INDEX`, `OPT`), `values` (symbols), `fields`, `startDate`/`endDate` (UTC), `interval`, `intraDay`, `realTime`. Each field is a list of points with `.timestamp` (ns) and `.value`. A bad payload returns a `NubraValidationError` object rather than raising, so every example checks `isinstance`.

| Interval | Meaning |
|---|---|
| `3m`, `5m` | Intraday candles (these examples) |
| `1d` | Daily |
| `1mt` | Monthly (UAT accepts `1mt`, not the docs' `1mth`) |

#### [historical_market_data/basic_usage.py](../../examples/market_data/historical_market_data/basic_usage.py)

Seven days of daily candles for two stocks. Dates are computed from now, so it keeps working.

```python
end = datetime.now(timezone.utc)
FMT = "%Y-%m-%dT%H:%M:%S.000Z"
result = market_data.historical_data({
    "exchange": "NSE", "type": "STOCK", "values": ["ASIANPAINT", "HDFCBANK"],
    "fields": ["open", "high", "low", "close", "cumulative_volume"],
    "startDate": (end - timedelta(days=7)).strftime(FMT), "endDate": end.strftime(FMT),
    "interval": "1d", "intraDay": False, "realTime": False
})
```

```
py -3.12 examples/market_data/historical_market_data/basic_usage.py
```

Real output (first symbol):
```
Market time: 2026-10-05T07:02:14Z

ASIANPAINT (Rs)
              open    high     low   close   volume
2026-09-28  2437.9  2441.6  2412.9  2420.0  1097754
2026-09-29  2417.5  2425.3  2381.0  2415.0   909789
2026-09-30  2410.0  2430.5  2390.0  2402.6   553695
2026-10-01  2391.0  2420.0  2377.0  2407.0  1005836
2026-10-05  2407.0  2407.0  2340.0  2340.5   432065
```

#### [historical_market_data/stocks_data.py](../../examples/market_data/historical_market_data/stocks_data.py)

Three days of 3-minute RELIANCE candles, converted from UTC to IST. Intraday timestamps are only readable once localised.

```python
idx = pd.to_datetime([p.timestamp for p in tsp_list], unit="ns", utc=True).tz_convert("Asia/Kolkata")
```

```
py -3.12 examples/market_data/historical_market_data/stocks_data.py
```

Real output (first 6 lines):
```
RELIANCE: 70 candles of 3m
                             open    high     low   close   volume    symbol
2026-10-05 12:03:00+05:30  1177.2  1178.3  1177.1  1177.9  8735216  RELIANCE
2026-10-05 12:06:00+05:30  1177.9  1177.9  1176.5  1176.8  8778349  RELIANCE
2026-10-05 12:09:00+05:30  1176.7  1177.4  1176.3  1177.3  8818164  RELIANCE
2026-10-05 12:12:00+05:30  1177.3  1177.7  1176.0  1176.8  8859845  RELIANCE
```

#### [historical_market_data/indices_data.py](../../examples/market_data/historical_market_data/indices_data.py)

Monthly NIFTY candles for the past year (`"type": "INDEX"`). Note the `1mt` interval.

```python
"startDate": (end - timedelta(days=365)).strftime(FMT),
"endDate": end.strftime(FMT),
"interval": "1mt",  # monthly candles: UAT accepts "1mt" (the docs say "1mth")
```

```
py -3.12 examples/market_data/historical_market_data/indices_data.py
```

Real output (the first row is 2026-03 because UAT holds about 7 months):
```
                open      high       low     close       volume symbol
2026-03-01  23197.75  23465.35  22283.85  22331.40   4400700163  NIFTY
2026-04-01  22899.00  24601.70  22182.55  23997.55  10475408317  NIFTY
2026-05-01  24063.55  24482.10  23262.55  23547.75   9175950716  NIFTY
2026-06-01  23654.50  24261.60  23070.15  23865.75   9224063711  NIFTY
2026-07-01  23897.65  24530.90  23606.30  23767.45   6926846919  NIFTY
2026-08-01  24343.45  24378.60  23993.60  24080.40   3698976573  NIFTY
2026-09-01  24077.55  24143.15  22569.65  22620.45   6850792892  NIFTY
2026-10-01  22543.70  22621.80  22217.30  22450.50    728042873  NIFTY
```

#### [historical_market_data/expired_options_data.py](../../examples/market_data/historical_market_data/expired_options_data.py)

Expired option contracts with greeks (`theta`, `delta`, `gamma`, `vega`, `iv_mid`) and open interest, using `"type": "OPT"`. The contract names and dates are fixed on purpose. Expired contracts return empty on UAT, so expect the empty-series message there.

```python
instruments = ["NIFTY2692222500CE", "NIFTY2691522500CE"]
"fields": ["open", "high", "low", "close", "cumulative_volume",
           "theta", "delta", "gamma", "vega", "iv_mid", "cumulative_oi"],
```

```
py -3.12 examples/market_data/historical_market_data/expired_options_data.py
```

Real output:
```
NIFTY2692222500CE Historical data with greeks
  empty series (expired contracts are often not available on UAT)

NIFTY2691522500CE Historical data with greeks
  empty series (expired contracts are often not available on UAT)
```

#### [historical_market_data/ohlc_to_csv.py](../../examples/market_data/historical_market_data/ohlc_to_csv.py)

90 days of RELIANCE daily candles, a daily return column, and a CSV you can load into Excel or a backtester. This is the only example that writes a file (`reliance_daily_ohlc.csv` in the current directory).

```python
df["daily_return_%"] = (df["close"].pct_change() * 100).round(2)
out = Path(f"{SYMBOL.lower()}_daily_ohlc.csv")
df.to_csv(out)
```

```
py -3.12 examples/market_data/historical_market_data/ohlc_to_csv.py
```

Real output (last 5 rows of the table):
```
2026-09-28  1218.0  1219.7  1197.0  1197.6  13602349           -2.32
2026-09-29  1193.8  1198.3  1181.8  1182.0  24191416           -1.30
2026-09-30  1182.0  1196.5  1181.7  1187.0  16376789            0.42
2026-10-01  1180.1  1183.9  1160.8  1167.7  16771221           -1.63
2026-10-05  1167.7  1186.0  1167.7  1176.7   9150253            0.77
```

#### [historical_market_data/intraday_index_candles.py](../../examples/market_data/historical_market_data/intraday_index_candles.py)

Today's 5-minute NIFTY candles with `intraDay=True` (current session only). It exits with a message when the market is closed or before the open.

```python
"interval": "5m",
"intraDay": True,  # today's session only
```

```
py -3.12 examples/market_data/historical_market_data/intraday_index_candles.py
```

Real output (first 6 lines of the tail):
```
                               open      high       low     close     volume
2026-10-05 11:45:00+05:30  22467.65  22474.50  22455.60  22460.50  199726515
2026-10-05 11:50:00+05:30  22461.30  22468.60  22440.10  22459.50  205729433
2026-10-05 11:55:00+05:30  22461.65  22473.05  22433.40  22434.15  210012714
2026-10-05 12:00:00+05:30  22435.40  22452.45  22415.45  22449.75  214616461
2026-10-05 12:05:00+05:30  22451.00  22451.00  22397.50  22415.15  219145515
```

### Company fundamentals

Seven small scripts under [company_fundamentals/](../../examples/market_data/company_fundamentals/). Each calls one method and prints typed result objects. Statements come back as `FinancialsData` with `dates` (`YYYYMM`) and `data` rows (`label`, `values`, optional `children`). Pass `fundamentals_type=FundamentalsTypeEnum.CONSOLIDATED` and `limit`/`offset` to page through periods.

| File | Call | What you get |
|---|---|---|
| [basic_usage.py](../../examples/market_data/company_fundamentals/basic_usage.py) | all six calls | Every fundamentals method in one script; reuses the `fincode` from `key_ratios` for shareholding |
| [key_ratios.py](../../examples/market_data/company_fundamentals/key_ratios.py) | `key_ratios("INFY", peers="TCS,WIPRO", ...)` | P/E, P/B, ROE, EPS, dividend yield, market cap, with peers |
| [cash_flow.py](../../examples/market_data/company_fundamentals/cash_flow.py) | `cash_flow("INFY", limit=5)` | Cash flow statement rows |
| [balance_sheet.py](../../examples/market_data/company_fundamentals/balance_sheet.py) | `balance_sheet("HDFCBANK", limit=5)` | Balance sheet rows with child breakdowns |
| [profit_loss.py](../../examples/market_data/company_fundamentals/profit_loss.py) | `profit_loss("RELIANCE", result_type=ResultTypeEnum.ANNUAL / QUARTERLY)` | Annual and quarterly P&L |
| [corporate_actions.py](../../examples/market_data/company_fundamentals/corporate_actions.py) | `corp_actions("TCS")` | Corporate actions with `action_type`, `record_date`, `upcoming_event` |
| [shareholding_pattern.py](../../examples/market_data/company_fundamentals/shareholding_pattern.py) | `shareholding_pattern(fincode, limit=4)` | Holding by category per quarter (institutions with FII/DII children). Takes a `fincode`, so look it up from `key_ratios` first |

Key excerpt (`shareholding_pattern.py`):

```python
fincode = ratios.result.keyratios_shareholding.fincode
response = market_data.shareholding_pattern(fincode, limit=4, offset=0)
```

```
py -3.12 examples/market_data/company_fundamentals/key_ratios.py
py -3.12 examples/market_data/company_fundamentals/shareholding_pattern.py
```

Real output (`corporate_actions.py`, first entry):
```
Board Meeting
Board_Meeting
True
None
```

Real output (`balance_sheet.py`, first lines): the statement dates, then the raw rows (cut short here).
```
['202603', '202503']
[FinancialRow(label='Assets', is_key_ratio=False, values=[FinancialValue(date='202603', value=4908040840000000, ...
```

The other scripts print similarly structured objects, and most also print the full response. Values come back in the API's raw units, so check the scale before comparing against another source.

## Go further

1. Extend `watchlist_table.py` with your own 10 symbols, including one MCX future found via `get_instruments_dataframe`, and add a column for the move from previous close in rupees.
2. Add a threshold alert to `depth_imbalance.py`: print `WATCH` when the imbalance is beyond +/-50% and the spread is wider than one tick.
3. Use `nearest_expiry` to feed the second expiry into `option_chain_dataframe.py`, and compare PCR and max-OI strikes with `compare_expiries.py`.
4. Change `ohlc_to_csv.py` to fetch `5m` candles with `intraDay=True` and save an end-of-day CSV with the day's range.

## Common errors

| Error | Cause | Fix |
|---|---|---|
| Empty series for old dates | UAT keeps about 7 months of history; fixed old dates return empty | Build `startDate`/`endDate` relative to `datetime.now(timezone.utc)` |
| HTTP 500 invalid query interval | Monthly interval written as `1mth` (the docs' spelling) | Use `"1mt"` on UAT |
| Empty series for expired option contracts | Expired contracts return empty on UAT | Treat as no data on UAT |
| `ticker not found` | Symbol was demerged or renamed (e.g. `TATAMOTORS`) | Look up the current symbol in the instrument master ([02-instruments.md](02-instruments.md)) |
| `Invalid asset name` | Bare MCX name such as `GOLD` used for a future | Use the full contract name, e.g. `FUT_GOLD_20261204` |
| `get_instrument_by_symbol` returns a dict with `msg` | Symbol or exchange not found | Check `isinstance(instrument, dict)` before using `.ref_id` |
| `historical_data` returns a `NubraValidationError` object, no exception | Bad payload | Check `isinstance(result, NubraValidationError)` and print it |
| `current_price` / `option_chain` fail on another exchange | Only NSE, BSE and MCX are supported | Use one of those three |

## Summary

Prices are integer paise; divide by 100. `current_price`, `option_chain` and `historical_data` take symbols, `quote` takes a `ref_id`, and MCX futures need full contract names. History payloads use UTC dates relative to now, and failures come back as values (`None`, a dict with `msg`, `NubraValidationError`) that you must check.

[Home](README.md) | [← Previous: Instruments](02-instruments.md) | [Next: Realtime Data →](04-realtime.md)
