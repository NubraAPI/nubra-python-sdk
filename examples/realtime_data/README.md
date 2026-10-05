# Realtime data examples

All scripts are streaming: they log in with `PHONE_NO` / `MPIN` from `.env`, default to UAT (switch to `NubraEnv.PROD` for production), print for a bounded window (20-25 s) and exit. Ticks need market hours; otherwise they print "No data received - market closed?". Prices arrive as integer paise and are printed as rupees.

| File | One-liner | Type |
|---|---|---|
| `realtime_data/basic_usage.py` | Index ticks via the single `on_market_data` receiver | streaming |
| `index_data/basic_usage.py` | Live index values (NIFTY, HDFCBANK, SENSEX) | streaming |
| `ohlcv_data/basic_usage.py` | Live 1-minute OHLCV candles | streaming |
| `option_chain_data/basic_usage.py` | Live NIFTY option chain for the nearest expiry | streaming |
| `order_book_data/basic_usage.py` | HDFCBANK market depth (best bid/ask) | streaming |
| `greeks_data/basic_usage.py` | Live Greeks for the ATM NIFTY call | streaming |
| `option_chain_data/atm_straddle_monitor.py` | Live NIFTY ATM straddle price (CE + PE LTP) | streaming |
| `index_data/multi_index_ticker.py` | Multi-index table refreshed every 5 s | streaming |
| `ohlcv_data/ohlcv_to_csv.py` | Record 1-minute NIFTY candles to `output/*.csv` | streaming |
| `greeks_data/greeks_alert_watch.py` | ATM CE/PE Greeks with IV / premium move alerts | streaming |
| `order_book_data/depth_imbalance.py` | HDFCBANK bid vs ask quantity imbalance | streaming |

Order/trade updates live in `../trading/realtime_order_updates/basic_usage.py`.
