# Market data examples

All examples default to `NubraEnv.UAT` (comment in each file shows how to switch to PROD) and log in with
`PHONE_NO` / `MPIN` from `.env`. Prices from the API are integer paise; examples print rupees but keep request
payloads as documented. Every example is read-only (`ohlc_to_csv.py` also writes one local CSV).

UAT notes: ~7 months of history; monthly interval is `"1mt"`; expired option contracts return empty series;
MCX futures need full names such as `FUT_CRUDEOIL_20261019`.

## current_price
| File | What it does | Type |
|---|---|---|
| `basic_usage.py` | Latest price, prev close, % change for NIFTY and RELIANCE (NSE) | read-only |
| `bse_usage.py` | Same for SENSEX and HDFCBANK (BSE) | read-only |
| `mcx_usage.py` | Price of the nearest CRUDEOIL and GOLD MCX futures | read-only |
| `watchlist_table.py` | Multi-symbol watchlist table sorted by % change | read-only |

## market_quotes
| File | What it does | Type |
|---|---|---|
| `basic_usage.py` | 5-level order book for HDFCBANK (NSE) | read-only |
| `bse_usage.py` | 5-level order book for HDFCBANK (BSE) | read-only |
| `mcx_usage.py` | 5-level order book for nearest CRUDEOIL future | read-only |
| `depth_imbalance.py` | Bid-ask spread and buy/sell depth imbalance for RELIANCE | read-only |

## option_chain
| File | What it does | Type |
|---|---|---|
| `basic_usage.py` | NIFTY chain summary: spot, ATM, ATM premiums | read-only |
| `bse_usage.py` | SENSEX chain summary (BSE) | read-only |
| `mcx_usage.py` | CRUDEOIL chain summary (MCX) | read-only |
| `option_chain_dataframe.py` | Chain as DataFrame: ATM window, PCR, max-OI support/resistance, IV skew | read-only |
| `nearest_expiry.py` | Helper to pick the nearest upcoming expiry (`YYYYMMDD`) and fetch it | read-only |
| `compare_expiries.py` | Side-by-side ATM straddle, IV, PCR, OI walls for two expiries | read-only |

## historical_market_data
| File | What it does | Type |
|---|---|---|
| `basic_usage.py` | 7 days of daily candles for two stocks | read-only |
| `stocks_data.py` | 3 days of 3-minute RELIANCE candles (IST) | read-only |
| `indices_data.py` | Monthly NIFTY candles | read-only |
| `expired_options_data.py` | Expired NIFTY weekly options with greeks (often empty on UAT) | read-only |
| `ohlc_to_csv.py` | 90 days of daily OHLC plus daily return % saved to CSV | read-only (writes local CSV) |
| `intraday_index_candles.py` | Today's 5-minute NIFTY candles (`intraDay=True`) | read-only |

## company_fundamentals
| File | What it does | Type |
|---|---|---|
| `basic_usage.py` | Tour of every fundamentals call | read-only |
| `key_ratios.py` | INFY key ratios with peers | read-only |
| `cash_flow.py` | INFY cash flow statement | read-only |
| `balance_sheet.py` | HDFCBANK balance sheet | read-only |
| `profit_loss.py` | RELIANCE annual and quarterly P&L | read-only |
| `corporate_actions.py` | TCS corporate actions | read-only |
| `shareholding_pattern.py` | INFY shareholding (looks up fincode first) | read-only |
