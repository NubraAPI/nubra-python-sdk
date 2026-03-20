from __future__ import annotations

import html
import json
import re
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Iterable
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]

PAGES = [
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/index.html",
        "output_dir": "introduction",
        "page_slug": "introduction",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/release-notes.html",
        "output_dir": "release_notes",
        "page_slug": "release_notes",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/authentication.html",
        "output_dir": "authentication",
        "page_slug": "authentication",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/UATEnvironment.html",
        "output_dir": "uat_environment",
        "page_slug": "uat_environment",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/RateLimits.html",
        "output_dir": "api_rate_limits",
        "page_slug": "api_rate_limits",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/get-instruments.html",
        "output_dir": "get_instruments",
        "page_slug": "get_instruments",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/market-data/current-price.html",
        "output_dir": "market_data/current_price",
        "page_slug": "current_price",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/market-data/market-quotes.html",
        "output_dir": "market_data/market_quotes",
        "page_slug": "market_quotes",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/market-data/historical-market-data.html",
        "output_dir": "market_data/historical_market_data",
        "page_slug": "historical_market_data",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/market-data/option-chain.html",
        "output_dir": "market_data/option_chain",
        "page_slug": "option_chain",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/realtime-data/realtime-data.html",
        "output_dir": "realtime_data/realtime_data",
        "page_slug": "realtime_data",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/realtime-data/index-data.html",
        "output_dir": "realtime_data/index_data",
        "page_slug": "index_data",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/realtime-data/optionchain-data.html",
        "output_dir": "realtime_data/option_chain_data",
        "page_slug": "option_chain_data",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/realtime-data/orderbook-data.html",
        "output_dir": "realtime_data/order_book_data",
        "page_slug": "order_book_data",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/realtime-data/greeks-data.html",
        "output_dir": "realtime_data/greeks_data",
        "page_slug": "greeks_data",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/realtime-data/ohlcv-data.html",
        "output_dir": "realtime_data/ohlcv_data",
        "page_slug": "ohlcv_data",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/realtime-data/subscription-limits.html",
        "output_dir": "realtime_data/subscription_limits",
        "page_slug": "subscription_limits",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/trading/orders/orders.html",
        "output_dir": "trading/overview",
        "page_slug": "trading_overview",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/trading/orders/place-order.html",
        "output_dir": "trading/place_order",
        "page_slug": "place_order",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/trading/orders/place-basket-order.html",
        "output_dir": "trading/place_multi_order",
        "page_slug": "place_multi_order",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/trading/orders/place-flexi-order.html",
        "output_dir": "trading/place_flexi_order",
        "page_slug": "place_flexi_order",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/trading/orders/modify-order.html",
        "output_dir": "trading/modify_order",
        "page_slug": "modify_order",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/trading/orders/modify-flexiorder.html",
        "output_dir": "trading/modify_flexi_order",
        "page_slug": "modify_flexi_order",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/trading/orders/cancel-order.html",
        "output_dir": "trading/cancel_order",
        "page_slug": "cancel_order",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/trading/orders/cancel-flexi-order.html",
        "output_dir": "trading/cancel_flexi_order",
        "page_slug": "cancel_flexi_order",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/trading/orders/get-order.html",
        "output_dir": "trading/get_order",
        "page_slug": "get_order",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/trading/orders/get-basketorder.html",
        "output_dir": "trading/get_flexi_order",
        "page_slug": "get_flexi_order",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/trading/orders/get-margin.html",
        "output_dir": "trading/get_margin",
        "page_slug": "get_margin",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/trading/realtime-order-updates.html",
        "output_dir": "trading/realtime_order_updates",
        "page_slug": "realtime_order_updates",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/trading/portfolio/holdings.html",
        "output_dir": "portfolio/holdings",
        "page_slug": "holdings",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/trading/portfolio/positions.html",
        "output_dir": "portfolio/positions",
        "page_slug": "positions",
    },
    {
        "url": "https://nubra.io/products/api/docs/python-sdk/trading/portfolio/funds.html",
        "output_dir": "portfolio/funds",
        "page_slug": "funds",
    },
]

TOP_LEVEL_OUTPUTS = [
    "introduction",
    "release_notes",
    "authentication",
    "uat_environment",
    "api_rate_limits",
    "get_instruments",
    "market_data",
    "realtime_data",
    "trading",
    "portfolio",
]

ARTICLE_RE = re.compile(
    r'<article class="md-content__inner md-typeset">(.*?)</article>',
    re.S,
)
HEADING_OR_CODE_RE = re.compile(
    r'(?P<heading><h(?P<level>[1-6])[^>]*>(?P<heading_html>.*?)</h(?P=level)>)'
    r"|(?P<code><div class=\"[^\"]*highlight[^\"]*\"><pre><span></span><code>(?P<code_html>.*?)</code></pre></div>)",
    re.S,
)


def fetch(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; NubraPythonSdkDocsSync/1.0)"
        },
    )
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8")


def strip_tags(raw_html: str) -> str:
    return re.sub(r"<[^>]+>", "", raw_html)


def clean_text(raw_html: str) -> str:
    text = html.unescape(strip_tags(raw_html))
    return (
        text.replace("¶", "")
        .replace("ś", "")
        .replace("\xa0", " ")
        .strip()
    )


def slugify(value: str) -> str:
    value = clean_text(value).lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    if not value:
        return "snippet"
    if value[0].isdigit():
        return f"step_{value}"
    return value


def iter_tokens(article_html: str) -> Iterable[dict[str, str | int]]:
    for match in HEADING_OR_CODE_RE.finditer(article_html):
        if match.group("heading"):
            yield {
                "kind": "heading",
                "level": int(match.group("level")),
                "text": clean_text(match.group("heading_html")),
            }
        else:
            code = html.unescape(strip_tags(match.group("code_html")))
            yield {"kind": "code", "text": code.strip("\n")}


def build_page_output(page: dict[str, str]) -> dict[str, object]:
    article_match = ARTICLE_RE.search(fetch(page["url"]))
    if not article_match:
        raise RuntimeError(f"Could not locate article content for {page['url']}")

    article_html = article_match.group(1)
    page_title = page["page_slug"].replace("_", " ").title()
    current_heading = page["page_slug"]
    heading_counts: dict[str, int] = defaultdict(int)
    files: list[dict[str, str]] = []

    for token in iter_tokens(article_html):
        if token["kind"] == "heading":
            level = int(token["level"])
            if level == 1:
                page_title = str(token["text"])
            elif level >= 2:
                current_heading = slugify(str(token["text"]))
            continue

        block_name = current_heading or page["page_slug"]
        heading_counts[block_name] += 1
        suffix = f"_{heading_counts[block_name]:02d}" if heading_counts[block_name] > 1 else ""
        filename = f"{block_name}{suffix}.py"
        files.append(
            {
                "filename": filename,
                "content": str(token["text"]) + "\n",
            }
        )

    return {
        "title": page_title,
        "url": page["url"],
        "output_dir": page["output_dir"],
        "files": files,
    }


def write_page(page_output: dict[str, object]) -> dict[str, object]:
    output_dir = REPO_ROOT / str(page_output["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    file_entries = []
    files = list(page_output["files"])
    if files:
        for file_data in files:
            file_path = output_dir / str(file_data["filename"])
            file_path.write_text(str(file_data["content"]), encoding="utf-8")
            file_entries.append(file_path.relative_to(REPO_ROOT).as_posix())
    else:
        readme_path = output_dir / "README.md"
        readme_path.write_text(
            "\n".join(
                [
                    f"# {page_output['title']}",
                    "",
                    f"Source: {page_output['url']}",
                    "",
                    "This docs page currently has no extractable code blocks to mirror into `.py` files.",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        file_entries.append(readme_path.relative_to(REPO_ROOT).as_posix())

    return {
        "title": page_output["title"],
        "url": page_output["url"],
        "output_dir": page_output["output_dir"],
        "files": file_entries,
        "code_block_count": len(files),
    }


def reset_generated_tree() -> None:
    for relative_dir in TOP_LEVEL_OUTPUTS:
        path = REPO_ROOT / relative_dir
        if path.exists():
            shutil.rmtree(path)


def main() -> None:
    reset_generated_tree()

    manifest = {"pages": []}
    for page in PAGES:
        page_output = build_page_output(page)
        manifest["pages"].append(write_page(page_output))

    manifest_path = REPO_ROOT / "docs_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
