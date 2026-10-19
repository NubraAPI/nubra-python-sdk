"""NIFTY open-interest dashboard: constituent pressure, OI change and gamma-aware option ranking.

Type: streaming (read-only by default; optional mutating order helper behind --place-orders)
Needs: UAT login (PHONE_NO / MPIN in .env); market hours for live ticks.
Expect: a terminal dashboard and a local web page (http://127.0.0.1:8051) showing a bias score, the OI-change
        score and the top-ranked CE/PE contracts; without --place-orders any order is only printed (dry run).
Tested with: nubra-sdk 0.5.4 (UAT)
"""
import argparse
import sys

from open_interest_dashboard.orders import check_order_flags


def parse_args(argv):
    p = argparse.ArgumentParser(
        description="NIFTY open-interest dashboard (constituent pressure + OI change + gamma-aware option "
                    "ranking) using the Nubra SDK. For educational use only; not investment advice."
    )
    p.add_argument("--env", choices=["UAT", "PROD"], default="UAT", help="Nubra environment (default UAT).")
    p.add_argument("--expiry", help="NIFTY expiry as YYYYMMDD. Default: nearest upcoming expiry from the option chain.")
    p.add_argument("--capital", type=float, default=5000.0, help="Rupees; contracts whose one-lot cost exceeds 95%% of it are marked unaffordable.")
    p.add_argument("--weights-csv", help="CSV with columns symbol,weight. Defaults to the bundled NIFTY 50 table.")

    g = p.add_argument_group("scoring")
    g.add_argument("--min-score", type=float, default=0.24, help="Minimum |bias score| for a directional reading.")
    g.add_argument("--min-pressure-abs", type=float, default=0.03, help="Minimum |pressure score|.")
    g.add_argument("--min-oi-abs", type=float, default=0.14, help="Minimum |OI change score|.")
    g.add_argument("--decision-interval", type=float, default=10.0, help="Seconds between evaluations.")

    g = p.add_argument_group("display")
    g.add_argument("--dashboard", action=argparse.BooleanOptionalAction, default=True, help="Terminal dashboard (--no-dashboard prints log lines instead).")
    g.add_argument("--dashboard-refresh", type=float, default=1.0)
    g.add_argument("--web-dashboard", action=argparse.BooleanOptionalAction, default=True, help="Local web dashboard.")
    g.add_argument("--web-host", default="127.0.0.1")
    g.add_argument("--web-port", type=int, default=8051)
    g.add_argument("--open-browser", action=argparse.BooleanOptionalAction, default=False)

    g = p.add_argument_group("feeds")
    g.add_argument("--connect-wait", type=float, default=3.0, help="Seconds to wait after opening the websocket.")
    g.add_argument("--option-poll-seconds", type=float, default=15.0, help="REST option-chain fallback interval; 0 disables it.")
    g.add_argument("--max-minutes", type=float, default=0.0, help="0 runs until Ctrl+C.")

    g = p.add_argument_group("optional order helper (off by default)")
    g.add_argument("--place-orders", action="store_true", help="Actually send the order. Without it the payload is only printed (dry run).")
    g.add_argument("--allow-prod", action="store_true", help="Required in addition to --place-orders when --env PROD.")
    g.add_argument("--order-mode", choices=["bracket", "entry"], default="bracket", help="bracket = limit entry + stop-loss + target; entry = limit entry only.")
    g.add_argument("--max-orders", type=int, default=1, help="Orders (or dry-run payloads) per run.")
    g.add_argument("--order-cooldown-seconds", type=float, default=300.0)
    g.add_argument("--risk-fraction", type=float, default=0.08, help="Max reference loss per order as a fraction of --capital.")
    g.add_argument("--stoploss-pct", type=float, default=18.0, help="Stop-loss distance below the contract LTP, in percent.")
    g.add_argument("--target-multiple", type=float, default=1.6, help="Target distance as a multiple of the stop-loss distance.")
    g.add_argument("--entry-limit-buffer-pct", type=float, default=1.5, help="Entry limit placed this percent above the contract LTP.")
    g.add_argument("--only-market-hours", action=argparse.BooleanOptionalAction, default=True, help="Only build orders between 09:16 and 15:10.")
    g.add_argument("--order-tag", default="nifty-oi-dashboard", help="Order tag: letters, digits and hyphens only.")

    g = p.add_argument_group("login")
    g.add_argument("--totp-login", action="store_true", help="Use the SDK's TOTP login flow.")
    g.add_argument("--insti-login", action="store_true", help="Use the SDK's institutional login flow (fields in .env).")

    args = p.parse_args(argv)
    error = check_order_flags(args)
    if error:
        p.error(error)
    if args.allow_prod and not args.place_orders:
        print("[note] --allow-prod has no effect without --place-orders", file=sys.stderr)
    return args


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    from open_interest_dashboard.runner import run  # imported here so --help works without the SDK installed

    raise SystemExit(run(args))
