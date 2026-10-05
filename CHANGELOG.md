# Changelog

All notable changes to the Nubra Python SDK are documented in this file.

The format follows a chronological, versioned history to help users understand feature additions, breaking changes, and upgrade implications.

---

## [0.5.4] - 2026-09-24
Published on PyPI. No release notes were published in the Nubra docs for this version.

## [0.5.3] - 2026-09-15
Published on PyPI. No release notes were published in the Nubra docs for this version.

## [0.5.2] - 2026-09-02
Nubra's website V3 docs were written against this line. Examples in this repo are tested on 0.5.4.

## [0.5.1] - 2026-08-05
Published on PyPI. No release notes were published in the Nubra docs for this version.

## [0.5.0] - 2026-07-10

### Added
- **V3 order flow is the default**
  - V3 payload support for single, multi and strategy (flexi) orders
  - Market orders supported in the V3 order flow
  - Refreshed portfolio, market-data, realtime and trading docs for V3

### Changed
- `InitNubraSdk` and `NubraTrader` no longer take a trading API version argument. Remove `version="V2"` from existing code.

---

## [0.4.5] - 2026-06-18
Earlier V3 UAT release before the 0.5.0 rollout.

## [0.4.4] - 2026-06-09
Earlier V3 UAT release before the 0.4.5 rollout.

## [0.4.3] - 2026-06-04
Published on PyPI. No release notes were published in the Nubra docs for this version.

## [0.4.2] - 2026-05-24
Stable production and public line before the V3 migration.

## [0.4.1] - 2026-05-15
Published on PyPI. No release notes were published in the Nubra docs for this version.

## [0.4.0] - 2026-03-04
Published on PyPI. No release notes were published in the Nubra docs for this version.

## [0.3.9] - 2026-02-26
Published on PyPI. No release notes were published in the Nubra docs for this version.

---

## [0.3.8] - 2026-01-23

### Added
- Index WebSocket now exposes open interest for applicable instruments
- Realtime OI updates for futures and options through the index stream
- `volume_oi` in the index payload when applicable (`None` for spot indices and equities)

---

## [0.3.7]

### Added
- Positions API response includes buy and sell quantity fields for clearer position-level visibility

---

## [0.3.6]

### Added
- **Flexi Basket Modification**
  - Modify existing Flexi basket orders including entry price, exit price, stoploss, timing, and multiplier (subject to order type rules)

- **Get Margin API**
  - Margin estimation for single-leg and multi-leg strategies
  - Portfolio hedge benefits included
  - Final authoritative margin calculation

- **Greeks WebSocket**
  - Real-time streaming of option Greeks (Delta, Gamma, Theta, Vega, IV)
  - Designed for live risk monitoring and strategy management

- **OHLCV WebSocket**
  - Real-time OHLCV candle data via WebSocket
  - Suitable for intraday analytics, indicators, and automated trading systems

---

## [0.3.5]

### Changed
- Internal change to the WebSocket endpoint for market data

### Notes
- From version `0.3.5`, the **new WebSocket endpoint** is used by default
- To continue using the older WebSocket endpoint on `0.3.5`, pass:
  
      socket_v2 = False

- For versions `≤ 0.3.4`, no flag is required — the previous endpoint behavior remains unchanged

---

## [0.3.4]

### Added
- Order tagging support in:
  - Place Order
  - Place Multi Order
  - Place Flexi Order APIs

### Enhanced
- Get Order API now supports filtering by order tag
- Improved real-time order update import mechanism

---

## [0.3.1]

### Breaking Changes
- **Authentication**
  - OTP authentication now requires `.env` files

- **Price Format**
  - All prices and monetary values are represented as **integers in paise**
  - Floating-point rupee values are no longer supported

### Added
- **Trading API V2**
  - New trading APIs introduced under version `V2`
  - Updated parameter structure

> Refer to the Trading API V1 documentation if continuing on V1.

---

## [0.2.5]

### Added
- Portfolio APIs
  - Holdings retrieval with detailed PnL breakdown
  - Position tracking for stocks, futures, and options
  - Funds and margin APIs

- Trading APIs
  - Place single and basket orders
  - Modify existing orders
  - Cancel orders (single and multiple)
  - Order book and order status tracking
  - Support for multiple execution strategies:
    - Market
    - Limit
    - IOC
    - Iceberg
    - Stop-loss

---

## [0.1.1]

### Added
- Initial public release of the Nubra Python SDK
- Historical market data retrieval
- Live market quotes including depth
- Real-time market data via WebSockets
- Option chain data
- Terminal-based authentication with 2FA

---

## Updating the SDK

Upgrade to the latest version from PyPI:

```bash
python -m pip install --upgrade nubra-sdk
```

Check what you have with `python tools/check_sdk_version.py`. Supported versions are listed in [VERSIONS.md](VERSIONS.md).
