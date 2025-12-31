# Changelog

All notable changes to the Nubra Python SDK are documented in this file.

The format follows a chronological, versioned history to help users understand feature additions, breaking changes, and upgrade implications.

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
  - TOTP and OTP authentication now require `.env` files

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
- TOTP Authentication
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

To upgrade to the latest version:

Uninstall the older Nubra Python using 
```bash
pip uninstall nubra-sdk
```
Install the Nubra Python SDK using `pip`.

### macOS / Linux
```bash
pip3 install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple nubra-sdk
```

### Windows
```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple nubra-sdk
```
---

## Version Support

| Version | Status   | Python Support |
|--------|----------|----------------|
| 0.3.6  | Current  | Python 3.7+    |
| 0.3.5  | Previous | Python 3.7+    |
| 0.2.5  | Legacy   | Python 3.7+    |
