# Nubra Python SDK

Official Python SDK for Nubra Trading & Market Data APIs.

The Nubra API provides programmatic access to Nubra’s trading infrastructure, enabling developers, algorithmic traders, and institutions to build robust trading systems with ease.

The Python SDK offers a high-level, intuitive interface to Nubra’s APIs, allowing you to focus on strategy and application logic without managing low-level REST requests, authentication flows, or request handling.

For teams that require direct HTTP-level integrations, Nubra also provides a complete suite of REST APIs.

---

## Version Notice (Important)

The Nubra Python SDK is currently on **Version 2 (V2)**.

V2 introduces major improvements across:
- Stability and performance
- Authentication and session handling
- Market data access
- Trading and order workflows

⚠️ **V1 of the SDK will be deprecated soon.**  
If you are currently using V1, we strongly recommend migrating to V2 to ensure compatibility and continued support.

---

## Features

- Easy-to-use Python interface
- Comprehensive market data access
- Real-time quotes and option Greeks
- Historical market data retrieval
- Option chain snapshots
- Full order management:
  - Regular orders
  - Cover orders (CO)
  - Flexi orders
  - Basket orders
- Positions, holdings, and funds APIs
- Secure MPIN-based authentication
- Built for algorithmic trading and automation
- Production-grade performance and reliability

---

## Getting Started

### Prerequisites

Before using the Nubra Python SDK, ensure the following are installed on your system.

---

### 1. Install Python

- Download Python from: https://www.python.org/downloads/
- During installation (especially on Windows), ensure **“Add Python to PATH”** is checked.

Verify the installation:

**macOS / Linux**
```bash
python3 --version
```

**Windows**
```bash
python --version
```

You should see a version like `Python 3.x.x`.

---

### 2. (Optional) Install Visual Studio Code

VS Code is recommended for writing and running Python scripts.

- Download: https://code.visualstudio.com/download
- Install the **Python** extension from the Extensions panel.

---

## Installation

Install the Nubra Python SDK using `pip`.

### macOS / Linux
```bash
pip3 install --index-url https://test.pypi.org/simple/ \
--extra-index-url https://pypi.org/simple \
nubra-sdk
```

### Windows
```bash
pip install --index-url https://test.pypi.org/simple/ \
--extra-index-url https://pypi.org/simple \
nubra-sdk
```

---

## Environments

| Environment | Purpose |
|------------|---------|
| UAT | Strategy validation, dry runs, and testing |
| PROD | Live trading |

---

## Strategy Validation (UAT)

The SDK supports UAT environments for validating trading logic, simulating order flows, and testing integrations safely before deploying to production.

This allows developers to verify correctness, performance, and error handling without placing live trades.

---

## Examples

Runnable examples and sample scripts are available here:

https://github.com/NubraHQ/nubra-python-sdk-examples

---

## Support

If you encounter issues or have questions:

- Email: support@nubra.io
- SDK bugs & feature requests: GitHub Issues (recommended)

---

## License

MIT License
