# Tools

Scripts for checking and maintaining the repo. Run them from the repo root.

| Script | What it does | When to run it |
|---|---|---|
| `check_sdk_version.py` | Prints the installed `nubra-sdk` version, the version the examples were tested on, and the latest on PyPI. | Before running examples, and after upgrading the SDK. |
| `uat_login.py` | One-time interactive UAT login (hard-wired to UAT) that saves the session in `auth_data.db` in the current folder. | Once, before `run_examples_uat.py`. |
| `run_examples_uat.py` | Runs every example against UAT and reports pass/fail. Skips examples that reference `NubraEnv.PROD` or need interactive input; stdin is closed so nothing hangs. Accepts optional substring filters. | After editing examples, following `uat_login.py`. It runs the order-placing examples on UAT. |
| `validate_examples.py` | Parses every `.py` file under `examples/` and lists syntax errors. Does not log in or run anything. | After editing examples, before committing. |
| `stamp_examples.py` | Adds or refreshes the "Tested with: nubra-sdk X (UAT)" line in each example docstring, using the version in `check_sdk_version.py`. | After re-testing the examples on a new SDK version. |
| `sync_python_sdk_docs.py` | Maintainer script used to publish the repo's documentation. | Maintainers only. Not needed to use the SDK. |
| `restructure_official_repo.py` | Maintainer script used to publish the repo layout (`examples`, `snippets`, `schemas`). | Maintainers only. Not needed to use the SDK. |
