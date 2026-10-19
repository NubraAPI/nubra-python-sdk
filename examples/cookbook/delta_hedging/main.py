"""Entry point for the delta hedging example: backtest, hedge, dashboard, scan, watch.

Type: backtest, dashboard and scan are read-only; hedge is streaming; hedge and watch place orders
      only when you pass --place-orders (PROD additionally needs --allow-prod). Default is a dry run.
Needs: UAT login (PHONE_NO / MPIN in .env; the SDK prompts for the OTP); market hours for live prices.
Expect: a progress or status line per cycle with prices and PnL in rupees; see README.md per subcommand.

Usage:
    python main.py backtest  --future-symbol ... --call-symbol ... --equity-symbol ... --lot-size ... \\
                             --start 2025-08-01 --end 2025-08-29 --pnl-target 5000 --pnl-stop-loss -3000
    python main.py hedge     SYMBOL --pnl-target 5000 --pnl-stop-loss -3000 [--place-orders]
    python main.py dashboard [--refresh-seconds 4]
    python main.py scan      [--top-n 15]
    python main.py watch     --max-daily-loss -15000 [--place-orders]
Tested with: nubra-sdk 0.5.4 (UAT)
"""
from __future__ import annotations

import argparse
from pathlib import Path

from hedging.session import ENV_CHOICES, check_order_flags, login
from hedging.state import DEFAULT_STATE_DIR


def _add_env(p: argparse.ArgumentParser) -> None:
    p.add_argument("--env", choices=ENV_CHOICES, default="uat", help="uat (sandbox, default) or prod")


def _add_order_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--place-orders", action="store_true",
                   help="actually send orders (default: dry run that prints what would be sent)")
    p.add_argument("--allow-prod", action="store_true",
                   help="required together with --place-orders when --env prod")


def _add_state_dir(p: argparse.ArgumentParser) -> None:
    p.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR,
                   help=f"folder for position state files (default: {DEFAULT_STATE_DIR})")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Delta hedging with the Nubra Python SDK (long future + short ATM calls). "
                    "For educational and demonstration purposes only; not investment advice.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    bt = sub.add_parser("backtest", help="replay the hedge on historical bars (read-only)")
    _add_env(bt)
    bt.add_argument("--future-symbol", required=True, help="exact historical futures contract name")
    bt.add_argument("--call-symbol", required=True, help="exact historical ATM call contract name")
    bt.add_argument("--equity-symbol", required=True, help="cash equity symbol")
    bt.add_argument("--lot-size", type=int, required=True, help="lot size in effect on those dates")
    bt.add_argument("--start", required=True, help="start date YYYY-MM-DD (or full UTC ISO time)")
    bt.add_argument("--end", required=True, help="end date YYYY-MM-DD (or full UTC ISO time)")
    bt.add_argument("--pnl-target", type=float, required=True, help="positive rupee PnL at which to exit")
    bt.add_argument("--pnl-stop-loss", type=float, required=True, help="zero or negative rupee PnL at which to exit")
    bt.add_argument("--exchange", default="NSE")
    bt.add_argument("--interval", default="5m", help="1s 1m 2m 3m 5m 15m 30m 1h 1d 1w 1mth (default 5m)")
    bt.add_argument("--short-calls", type=int, default=2, help="call lots to short (default 2)")
    bt.add_argument("--future-lots", type=int, default=1, help="future lots to buy (default 1)")
    bt.add_argument("--trigger-pct", type=float, default=1.5, help="percent move that triggers a re-hedge (default 1.5)")
    bt.add_argument("--starting-capital", type=float, default=0.0, help="chart offset only; not used in decisions")
    bt.add_argument("--output-dir", type=Path, default=Path("output"), help="CSV and PNG output folder (default ./output)")

    hd = sub.add_parser("hedge", help="run the hedge on live prices (dry run unless --place-orders)")
    _add_env(hd)
    _add_order_flags(hd)
    _add_state_dir(hd)
    hd.add_argument("symbol", help="F&O underlying, for example one listed on NSE")
    hd.add_argument("--pnl-target", type=float, required=True, help="positive rupee PnL at which to exit")
    hd.add_argument("--pnl-stop-loss", type=float, required=True, help="zero or negative rupee PnL at which to exit")
    hd.add_argument("--exchange", default="NSE")
    hd.add_argument("--expiry", default=None, help="YYYY-MM-DD; default is the nearest future expiry")
    hd.add_argument("--short-calls", type=int, default=2, help="ATM call lots to short (default 2)")
    hd.add_argument("--future-lots", type=int, default=1, help="future lots to buy (default 1)")
    hd.add_argument("--trigger-pct", type=float, default=1.5, help="percent move that triggers a re-hedge (default 1.5)")
    hd.add_argument("--poll-seconds", type=float, default=5.0, help="seconds between checks (default 5)")
    hd.add_argument("--hedge-delivery", choices=("CNC", "IDAY"), default="CNC",
                    help="delivery type of the equity hedge orders (default CNC)")
    hd.add_argument("--max-seconds", type=float, default=None, help="stop after this many seconds (default: run until exit)")

    db = sub.add_parser("dashboard", help="live positions and net Greeks table (read-only)")
    _add_env(db)
    _add_state_dir(db)
    db.add_argument("--refresh-seconds", type=float, default=4.0)
    db.add_argument("--once", action="store_true", help="draw once and exit")

    sc = sub.add_parser("scan", help="rank F&O underlyings by liquidity metrics (read-only)")
    _add_env(sc)
    sc.add_argument("--exchange", default="NSE")
    sc.add_argument("--top-n", type=int, default=15)
    sc.add_argument("--lookback-days", type=int, default=10)
    sc.add_argument("--max-underlyings", type=int, default=None,
                    help="cap how many underlyings to score (bounds historical-data calls)")

    wd = sub.add_parser("watch", help="account-wide loss watchdog (reports only unless --place-orders)")
    _add_env(wd)
    _add_order_flags(wd)
    _add_state_dir(wd)
    wd.add_argument("--max-daily-loss", type=float, required=True, help="zero or negative rupee account PnL limit")
    wd.add_argument("--max-drawdown-pct", type=float, default=None, help="optional percent drawdown from the day's peak equity")
    wd.add_argument("--poll-seconds", type=float, default=10.0)
    wd.add_argument("--max-cycles", type=int, default=None, help="stop after this many polls (default: run until a limit is reached)")
    return parser


def cmd_backtest(args) -> None:
    from nubra_python_sdk.marketdata.market_data import MarketData

    from hedging.backtest import BacktestConfig, run_backtest
    from hedging.report import plot_pnl_curve, summarize, write_hedge_log_csv

    cfg = BacktestConfig(
        future_symbol=args.future_symbol.upper(), call_symbol=args.call_symbol.upper(),
        equity_symbol=args.equity_symbol.upper(), lot_size=args.lot_size,
        pnl_target=args.pnl_target, pnl_stop_loss=args.pnl_stop_loss,
        start_date=args.start, end_date=args.end, exchange=args.exchange.upper(),
        num_short_calls=args.short_calls, future_lots=args.future_lots,
        hedge_trigger_pct=args.trigger_pct, interval=args.interval,
        starting_capital=args.starting_capital,
    )
    cfg.validate()
    result = run_backtest(MarketData(login(args.env)), cfg)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_hedge_log_csv(result, args.output_dir / f"{cfg.equity_symbol}_hedges.csv")
    plot_pnl_curve(result, args.output_dir / f"{cfg.equity_symbol}_pnl_curve.png")
    print(summarize(result))
    print(f"\nHedge log and chart written to {args.output_dir.resolve()}")


def cmd_hedge(args) -> None:
    from hedging.hedge_runner import HedgeConfig, HedgeRunner
    from hedging.orders import OrderGate

    cfg = HedgeConfig(
        symbol=args.symbol.upper(), pnl_target=args.pnl_target, pnl_stop_loss=args.pnl_stop_loss,
        exchange=args.exchange.upper(), expiry=args.expiry, num_short_calls=args.short_calls,
        future_lots=args.future_lots, hedge_trigger_pct=args.trigger_pct,
        poll_seconds=args.poll_seconds, hedge_delivery_type=args.hedge_delivery,
        state_dir=args.state_dir,
    )
    cfg.validate()
    check_order_flags(args.env, args.place_orders, args.allow_prod)
    nubra = login(args.env)
    gate = OrderGate(nubra, place_orders=args.place_orders, env_name=args.env, allow_prod=args.allow_prod)
    HedgeRunner(nubra, cfg, gate).run(max_seconds=args.max_seconds)


def cmd_dashboard(args) -> None:
    from hedging.dashboard import Dashboard

    Dashboard(login(args.env), args.state_dir).run(args.refresh_seconds, once=args.once)


def cmd_scan(args) -> None:
    from nubra_python_sdk.marketdata.market_data import MarketData
    from nubra_python_sdk.refdata.instruments import InstrumentData

    from hedging.scanner import format_table, scan

    nubra = login(args.env)
    scores = scan(InstrumentData(nubra), MarketData(nubra), exchange=args.exchange.upper(),
                  top_n=args.top_n, lookback_days=args.lookback_days, max_underlyings=args.max_underlyings)
    print(format_table(scores))


def cmd_watch(args) -> None:
    from hedging.orders import OrderGate
    from hedging.watchdog import WatchConfig, Watchdog

    cfg = WatchConfig(max_daily_loss=args.max_daily_loss, max_drawdown_pct=args.max_drawdown_pct,
                      poll_seconds=args.poll_seconds, state_dir=args.state_dir)
    cfg.validate()
    check_order_flags(args.env, args.place_orders, args.allow_prod)
    nubra = login(args.env)
    gate = OrderGate(nubra, place_orders=args.place_orders, env_name=args.env, allow_prod=args.allow_prod)
    try:
        Watchdog(nubra, cfg, gate).run(max_cycles=args.max_cycles)
    except KeyboardInterrupt:
        print("\nWatchdog stopped.")


COMMANDS = {"backtest": cmd_backtest, "hedge": cmd_hedge, "dashboard": cmd_dashboard,
            "scan": cmd_scan, "watch": cmd_watch}


def main() -> None:
    args = build_parser().parse_args()
    COMMANDS[args.command](args)


if __name__ == "__main__":
    main()
