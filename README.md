# Nubra Python SDK Samples

This repository is the official Nubra Python SDK sample and reference repo.

It is organized so users can quickly tell what is runnable and what is only reference material:

- `examples/` contains end-to-end Python examples
- `snippets/` contains partial snippets and supporting fragments
- `schemas/` contains response shapes, SDK surface notes, and reference docs

## Structure

- [examples](/c:/Users/Aryan/Desktop/projects/active/Nubra%20dox/nubra-python-sdk/examples)
- [snippets](/c:/Users/Aryan/Desktop/projects/active/Nubra%20dox/nubra-python-sdk/snippets)
- [schemas](/c:/Users/Aryan/Desktop/projects/active/Nubra%20dox/nubra-python-sdk/schemas)

Examples are grouped by SDK topic:

- authentication
- get_instruments
- introduction
- market_data
- portfolio
- realtime_data
- trading
- uat_environment

## Install

Install the SDK in your local environment before running any example:

```powershell
py -m pip install nubra-sdk
```

To upgrade:

```powershell
py -m pip install --upgrade nubra-sdk
```

## Authentication

Most examples assume you authenticate with environment-backed credentials:

```python
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

nubra = InitNubraSdk(NubraEnv.UAT, env_creds=True)
```

Reference snippets for authentication flows are available under:

- [examples/authentication](/c:/Users/Aryan/Desktop/projects/active/Nubra%20dox/nubra-python-sdk/examples/authentication)
- [snippets/authentication](/c:/Users/Aryan/Desktop/projects/active/Nubra%20dox/nubra-python-sdk/snippets/authentication)

## Example Safety

Use the examples with the following categories in mind:

- `Read-only`: Fetches data only. Safe for general exploration.
- `Streaming`: Opens live sockets or background listeners. Safe for testing, but may run continuously until stopped.
- `Mutating`: Places, modifies, or cancels orders. Run these only in `NubraEnv.UAT` unless you intentionally want live behavior.

Repository conventions:

- Only runnable examples stay as `.py`
- Partial snippets are stored as `.md`
- Response and schema references are stored as `.md`
- Examples default to `NubraEnv.UAT` unless the file is specifically about environment switching
- Order-id based trading examples use placeholders instead of real hardcoded IDs

## Validation

Use the lightweight validator to make sure everything under `examples/` still parses as Python:

```powershell
py tools/validate_examples.py
```

Key files:

- [tools/validate_examples.py](/c:/Users/Aryan/Desktop/projects/active/Nubra%20dox/nubra-python-sdk/tools/validate_examples.py)
- [examples/trading/place_order/basic_usage.py](/c:/Users/Aryan/Desktop/projects/active/Nubra%20dox/nubra-python-sdk/examples/trading/place_order/basic_usage.py)
- [snippets/market_data/current_price/accessing_response_fields.md](/c:/Users/Aryan/Desktop/projects/active/Nubra%20dox/nubra-python-sdk/snippets/market_data/current_price/accessing_response_fields.md)
- [schemas/realtime_data/option_chain_data/response_shape.md](/c:/Users/Aryan/Desktop/projects/active/Nubra%20dox/nubra-python-sdk/schemas/realtime_data/option_chain_data/response_shape.md)

## Support

For support and coordination:

- Product and SDK support: `support@nubra.io`
- Security reports: see [SECURITY.md](/c:/Users/Aryan/Desktop/projects/active/Nubra%20dox/nubra-python-sdk/SECURITY.md)
- Bugs and feature requests: use GitHub Issues

## Contributing

Contribution guidelines are available in [CONTRIBUTING.md](/c:/Users/Aryan/Desktop/projects/active/Nubra%20dox/nubra-python-sdk/CONTRIBUTING.md).

## License

This repository is licensed under the MIT License. See [LICENSE](/c:/Users/Aryan/Desktop/projects/active/Nubra%20dox/nubra-python-sdk/LICENSE).
