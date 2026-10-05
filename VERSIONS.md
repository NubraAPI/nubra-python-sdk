# SDK versions

Which `nubra-sdk` release this repo targets, and how to check yours.

| | |
| --- | --- |
| **Examples written and tested against** | `nubra-sdk` **0.5.4** (latest on PyPI, released 2026-09-24) |
| **Environment used for testing** | UAT sandbox (`NubraEnv.UAT`) |
| **Order API** | OMS V3. No version argument on `NubraTrader` or `InitNubraSdk` |
| **Python** | 3.7+ |

## Compatibility

| SDK version | Released | Status | Works with these examples |
| --- | --- | --- | --- |
| 0.5.4 | 2026-09-24 | Current, tested | Yes |
| 0.5.3 | 2026-09-15 | Supported (V3) | Expected, not tested |
| 0.5.2 | 2026-09-02 | Supported (V3), docs baseline | Expected, not tested |
| 0.5.1 | 2026-08-05 | Supported (V3) | Expected, not tested |
| 0.5.0 | 2026-07-10 | First V3-default release | Expected, not tested |
| 0.4.x | 2026-03 to 2026-06 | V3 UAT / V2 production line | No. Examples assume V3 payloads |
| 0.3.x and older | before 2026-03 | Legacy | No. Prices were floats before 0.3.1 |

Full history: [CHANGELOG.md](CHANGELOG.md).

## Check and upgrade

```bash
python tools/check_sdk_version.py          # compares your installed version with this repo and PyPI
python -m pip install --upgrade nubra-sdk  # upgrade to the latest
```

## Keeping this repo current

When a new SDK version ships:

1. Upgrade, then run `python tools/run_examples_uat.py` and fix anything that fails.
2. Update `TESTED_SDK_VERSION` in `tools/check_sdk_version.py`, the table above and `CHANGELOG.md`.
3. Re-stamp the examples: `python tools/stamp_examples.py`.
