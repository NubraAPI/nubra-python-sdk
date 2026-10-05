# Nubra Python SDK: Examples for Algo Trading, Market Data and Options
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/NubraAPI/nubra-python-sdk)

Runnable Python examples for the **Nubra Python SDK V3** (`nubra-sdk` 0.5.x). Place orders, stream live prices, pull option chains and historical candles, and track your portfolio on NSE, BSE and MCX. Every example runs on the UAT sandbox first.

**105 examples** · **8-page guide** · Python 3.7+ · tested on `nubra-sdk` 0.5.4 · UAT sandbox by default · MIT licensed

## Install

```bash
python -m pip install nubra-sdk
# upgrade
python -m pip install --upgrade nubra-sdk
```

## Quick start

```python
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

# NubraEnv.UAT is the sandbox. Switch to NubraEnv.PROD for live trading.
nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)

print(MarketData(nubra).current_price("HDFCBANK", exchange="NSE"))
```

`env_creds=True` reads `PHONE_NO` and `MPIN` from a local `.env` file (keep it out of git):

```dotenv
PHONE_NO="your-phone-number"
MPIN="your-mpin"
```

Without it, the SDK asks for your phone number, OTP and MPIN. See [examples/authentication](examples/authentication) for OTP and institutional login.

## Follow the guide

New here? Go in order. Each page links to the runnable examples and shows real UAT output.

| Step | Page | What you get |
| --- | --- | --- |
| 0 | [Setup](docs/guide/00-setup.md) | Install, `.env`, first run on UAT |
| 1 | [Authentication](docs/guide/01-authentication.md) | OTP, `.env` and institutional login |
| 2 | [Instruments](docs/guide/02-instruments.md) | Find the right contract, expiry and lot size |
| 3 | [Market Data](docs/guide/03-market-data.md) | Prices, depth, option chains, history, fundamentals |
| 4 | [Realtime Data](docs/guide/04-realtime.md) | Live indices, option chains, depth, Greeks, candles |
| 5 | [Trading](docs/guide/05-trading.md) | Single orders, strategies, margin, modify, cancel |
| 6 | [Portfolio](docs/guide/06-portfolio.md) | Funds, holdings, positions and P&L |
| 7 | [Recipes and Next Steps](docs/guide/07-recipes-and-next-steps.md) | Task lookup, worked workflows, going-live checklist |

Start at [the guide home](docs/guide/README.md).

## Find an example by task

| I want to... | Start here |
| --- | --- |
| Log in (OTP, `.env`, institutional) | [examples/authentication](examples/authentication) |
| Get live price, quote or depth for a stock, index or MCX future | [examples/market_data/current_price](examples/market_data/current_price), [market_quotes](examples/market_data/market_quotes) |
| Load an option chain into pandas (ATM, PCR, max OI, IV skew) | [option_chain_dataframe.py](examples/market_data/option_chain/option_chain_dataframe.py) |
| Download historical candles (stocks, indices, expired options) | [examples/market_data/historical_market_data](examples/market_data/historical_market_data) |
| Read company fundamentals (ratios, cash flow, balance sheet) | [examples/market_data/company_fundamentals](examples/market_data/company_fundamentals) |
| Look up instruments, expiries and lot sizes | [examples/get_instruments](examples/get_instruments) |
| Stream live index, option chain, order book, Greeks or OHLCV | [examples/realtime_data](examples/realtime_data) |
| Monitor a live ATM straddle | [atm_straddle_monitor.py](examples/realtime_data/option_chain_data/atm_straddle_monitor.py) |
| Place a single order (limit, market, stop-loss, trailing, iceberg, GTE) | [examples/trading/place_order](examples/trading/place_order) |
| Place a multi-leg strategy (straddle, strangle, spreads, iron condor) | [examples/trading/place_flexi_order](examples/trading/place_flexi_order) |
| Check margin before placing an order | [margin_check_then_place.py](examples/trading/place_order/margin_check_then_place.py) |
| Modify, cancel or square off orders | [modify_order](examples/trading/modify_order), [cancel_order](examples/trading/cancel_order) |
| Track funds, holdings, positions and P&L | [examples/portfolio](examples/portfolio) |
| Switch between sandbox and live | [examples/uat_environment](examples/uat_environment) |

Each folder has its own README with a file-by-file table.

## Repository layout

- [`examples/`](examples): runnable Python examples, grouped by SDK topic
- [`snippets/`](snippets): short code fragments for docs and copy-paste
- [`schemas/`](schemas): response shapes, SDK surface notes and API limits
- [`docs/guide/`](docs/guide): the step-by-step guide
- [`tools/`](tools): helper scripts (syntax validator, UAT login and test runner, SDK version check)
- [`VERSIONS.md`](VERSIONS.md) and [`CHANGELOG.md`](CHANGELOG.md): which SDK version this repo targets and what changed

## Safety

- **Read-only** examples only fetch data.
- **Streaming** examples subscribe for a short, bounded time and then close the socket.
- **Mutating** examples place, modify or cancel orders. Run them on `NubraEnv.UAT` unless you intend live trading.
- Prices are integers in paise (116770 means Rs 1167.70). Examples print rupees for readability and keep request payloads in paise.

## Test the examples on UAT

```bash
python tools/validate_examples.py     # every example parses as Python
python tools/uat_login.py             # one-time interactive UAT login (never touches PROD)
python tools/run_examples_uat.py      # run the examples against UAT, writes uat_report.json
python tools/check_sdk_version.py     # installed SDK vs the version these examples were tested on
```

## Support

- Product and SDK support: `support@nubra.io`
- Security reports: see [SECURITY.md](SECURITY.md)
- Bugs and feature requests: GitHub Issues
- Contributing: [CONTRIBUTING.md](CONTRIBUTING.md)

## License

MIT. See [LICENSE](LICENSE).
