from __future__ import annotations

import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

SOURCE_DIRS = [
    "authentication",
    "get_instruments",
    "introduction",
    "market_data",
    "portfolio",
    "realtime_data",
    "release_notes",
    "trading",
    "uat_environment",
]

BUCKET_DIRS = ["examples", "snippets", "schemas"]

SCHEMA_BASENAMES = {
    "reference_response_shape.py",
    "response_shape.py",
    "response_structure.py",
    "sample_response.py",
    "sdk_surface.py",
}

SNIPPET_PATHS = {
    "authentication/basic_usage_02.py",
    "authentication/using_env_variables.py",
    "get_instruments/instruments_master.py",
    "introduction/before_you_install.py",
    "introduction/before_you_install_02.py",
    "introduction/installation.py",
    "introduction/installation_02.py",
    "introduction/installation_03.py",
    "market_data/current_price/accessing_response_fields.py",
    "market_data/historical_market_data/accessing_response_fields.py",
    "market_data/market_quotes/accessing_response_fields.py",
    "market_data/option_chain/accessing_response_fields.py",
    "portfolio/funds/accessing_data.py",
    "portfolio/holdings/accessing_data.py",
    "portfolio/positions/accessing_data.py",
    "realtime_data/realtime_data/common_subscription_pattern.py",
    "release_notes/how_to_update.py",
    "trading/get_order/accessing_data.py",
    "trading/get_order/accessing_data_02.py",
    "trading/get_order/example_order_lifecycle.py",
    "trading/realtime_order_updates/running_in_a_background_thread.py",
}

TEXT_SNIPPET_PATHS = {
    "authentication/using_env_variables.py",
    "introduction/before_you_install.py",
    "introduction/before_you_install_02.py",
    "introduction/installation.py",
    "introduction/installation_02.py",
    "introduction/installation_03.py",
    "market_data/current_price/sample_response.py",
    "release_notes/how_to_update.py",
    "realtime_data/subscription_limits/quick_examples.py",
    "realtime_data/subscription_limits/quick_examples_02.py",
    "realtime_data/subscription_limits/quick_examples_03.py",
}


def classify(rel_path: str) -> str:
    path = Path(rel_path)
    if path.name in SCHEMA_BASENAMES:
        return "schemas"
    if rel_path in SNIPPET_PATHS or rel_path.startswith("realtime_data/subscription_limits/"):
        return "snippets"
    return "examples"


def extension_for(bucket: str) -> str:
    return ".py" if bucket == "examples" else ".md"


def fence_language(rel_path: str, bucket: str) -> str:
    if rel_path == "authentication/using_env_variables.py":
        return "dotenv"
    if rel_path in TEXT_SNIPPET_PATHS:
        return "text"
    return "python" if bucket != "snippets" or rel_path.endswith(".py") else "text"


def to_markdown(rel_path: str, bucket: str, body: str) -> str:
    title = Path(rel_path).stem.replace("_", " ").title()
    language = fence_language(rel_path, bucket)
    bucket_label = "Snippet" if bucket == "snippets" else "Schema Reference"
    return (
        f"# {bucket_label}: {title}\n\n"
        f"Original source path: `{rel_path}`\n\n"
        f"```{language}\n{body.rstrip()}\n```\n"
    )


def transform_example(rel_path: str, body: str) -> str:
    if rel_path != "uat_environment/switching_between_uat_and_live.py":
        body = body.replace("NubraEnv.PROD", "NubraEnv.UAT")

    replacements = {
        "trading/cancel_order/basic_usage.py": (
            'result = trader.cancel_orders_v2(order_ids=[2394981])',
            'ORDER_ID = 0  # Replace with your UAT order id.\n\nresult = trader.cancel_orders_v2(order_ids=[ORDER_ID])',
        ),
        "trading/get_order/get_order_by_id.py": (
            "result = trader.get_order(2394981)",
            'ORDER_ID = 0  # Replace with your UAT order id.\n\nresult = trader.get_order(ORDER_ID)',
        ),
        "trading/modify_order/basic_usage.py": (
            "result = trader.modify_order_v2(\n    order_id=2394981,",
            'ORDER_ID = 0  # Replace with your UAT order id.\n\nresult = trader.modify_order_v2(\n    order_id=ORDER_ID,',
        ),
        "trading/cancel_flexi_order/basic_usage.py": (
            'result = trader.cancel_flexi_order(123456, "NSE")',
            'BASKET_ID = 0  # Replace with your UAT flexi basket id.\n\nresult = trader.cancel_flexi_order(BASKET_ID, "NSE")',
        ),
        "trading/modify_flexi_order/basic_usage.py": (
            "result = trader.mod_flexi_order(\n    basket_id=123456,",
            'BASKET_ID = 0  # Replace with your UAT flexi basket id.\n\nresult = trader.mod_flexi_order(\n    basket_id=BASKET_ID,',
        ),
    }

    if rel_path in replacements:
        old, new = replacements[rel_path]
        body = body.replace(old, new)

    return body


def reset_bucket_dirs() -> None:
    for name in BUCKET_DIRS:
        path = REPO_ROOT / name
        if path.exists():
            shutil.rmtree(path)


def remove_legacy_dirs() -> None:
    for name in SOURCE_DIRS:
        path = REPO_ROOT / name
        if path.exists():
            shutil.rmtree(path)

    manifest_path = REPO_ROOT / "docs_manifest.json"
    if manifest_path.exists():
        manifest_path.unlink()


def main() -> None:
    reset_bucket_dirs()

    for source_dir in SOURCE_DIRS:
        root = REPO_ROOT / source_dir
        if not root.exists():
            continue

        for src in sorted(root.rglob("*.py")):
            rel_path = src.relative_to(REPO_ROOT).as_posix()
            bucket = classify(rel_path)
            dest_rel = Path(bucket) / src.relative_to(REPO_ROOT)
            dest_path = (REPO_ROOT / dest_rel).with_suffix(extension_for(bucket))
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            content = src.read_text(encoding="utf-8")
            if bucket == "examples":
                dest_path.write_text(transform_example(rel_path, content), encoding="utf-8")
            else:
                dest_path.write_text(to_markdown(rel_path, bucket, content), encoding="utf-8")

    remove_legacy_dirs()


if __name__ == "__main__":
    main()
