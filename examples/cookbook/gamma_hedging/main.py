"""Gamma-aware dynamic delta hedging for SENSEX option sellers, with a terminal and a browser dashboard.

Type: mutating (dry run by default; sends orders only with --place-orders)
Needs: UAT login (PHONE_NO / MPIN in .env); market hours for live prices; `pip install -r requirements.txt`
Expect: a live terminal dashboard plus a browser dashboard on http://127.0.0.1:8765 showing net delta,
        net gamma, the monitoring mode (NORMAL / HIGH_GAMMA), futures position and P&L per strategy.
        Without --place-orders every order is only printed/logged ("DRY RUN") and the position book is
        updated as if filled at LTP. Stops at MARKET_CLOSE_TIME or on Ctrl+C.

Subcommands:
    python main.py run                    # (default) run the hedging session
    python main.py run --place-orders     # actually send orders (UAT)
    python main.py check-login            # interactive login check (prompts for phone, OTP, MPIN)
    python main.py cancel-open            # list open orders for the underlying (dry run)
    python main.py cancel-open --yes      # cancel them

Every strategy in the STRATEGIES list in `.env` runs independently (own setup structure, own futures
hedge, own thresholds) and shares one kill switch and one hedge rate limiter. See README.md.
Tested with: nubra-sdk 0.5.4 (UAT)
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
import webbrowser
from dataclasses import dataclass, replace
from datetime import datetime
from zoneinfo import ZoneInfo

from gamma_hedging.config import Config, PriceType, StrategyConfig, StrategyType, load_config
from gamma_hedging.dashboard import Dashboard, StrategyView
from gamma_hedging.hedger import NORMAL_MODE, maybe_reconcile, run_tick
from gamma_hedging.initial_position import run_setup
from gamma_hedging.logging_utils import SessionLogger, configure_logging, new_session_id
from gamma_hedging.nubra_client import NubraClient, SetupInstruments, build_live_client
from gamma_hedging.positions import Book
from gamma_hedging.risk import HedgeRateLimiter
from gamma_hedging.safety import KillSwitch, UnsafeEnvironmentError, resolve_env
from gamma_hedging.settings_control import SettingsStore
from gamma_hedging.tag_control import TagToggleState
from gamma_hedging.web_dashboard import WebDashboard

# Tags found live on the broker are re-discovered every tick. Discovery is one
# read-only orders() call (not subject to the hedge rate limiter), and a long lag
# between placing a tag and seeing it offered for attachment is worse than the
# extra call.
TAG_DISCOVERY_EVERY_N_TICKS = 1


def _synthesize_attached_strategy_config(base_tag: str) -> StrategyConfig:
    """Default thresholds for a strategy attached to an existing tagged position.

    There is no `<NAME>_...` block in `.env` for a tag discovered live, so these
    defaults apply (they can be edited from the dashboard's Settings panel).
    """
    return StrategyConfig(
        name=base_tag,
        strategy_type=StrategyType.STRADDLE,  # label only; attached books skip setup
        setup_lots=0,  # unused: attached strategies never run setup
        strangle_offset_strikes=0,
        strangle_target_delta=0.20,
        setup_price_type=PriceType.LIMIT,
        delta_tolerance_lots=0.5,
        high_gamma_threshold=0.20,
        poll_interval_normal_sec=30.0,
        poll_interval_high_gamma_sec=7.0,
        hedge_price_type=PriceType.LIMIT,
        max_futures_position_lots=20,
        strat_tag=base_tag,
    )


@dataclass
class RunningStrategy:
    strat_cfg: StrategyConfig
    book: Book
    instruments: SetupInstruments
    mode: str = NORMAL_MODE
    # True for a strategy attached mid-session from a discovered tag; only these
    # are removed when the tag is toggled off in the dashboard.
    attached: bool = False


def _run_all_setups(cfg: Config, client: NubraClient, logger: logging.Logger) -> list[RunningStrategy]:
    running: list[RunningStrategy] = []
    for strat_cfg in cfg.strategies:
        logger.info("Running setup for strategy %r (%d of %d)...", strat_cfg.name, len(running) + 1, len(cfg.strategies))
        book, instruments = run_setup(cfg, strat_cfg, client)
        running.append(RunningStrategy(strat_cfg=strat_cfg, book=book, instruments=instruments))
    return running


# -- subcommand: run ---------------------------------------------------------------------


def cmd_run(args: argparse.Namespace) -> int:
    cfg = replace(load_config(), env_name=args.env.upper(), place_orders=args.place_orders)
    session_id = new_session_id()
    events_path = configure_logging(cfg, session_id, console=False)
    logger = logging.getLogger("gamma_hedging.main")

    strategy_names = [s.name for s in cfg.strategies]
    mode_text = "ORDERS ENABLED" if cfg.place_orders else "DRY RUN (no orders will be sent)"
    logger.info(
        "Starting gamma hedger session=%s env=%s %s underlying=%s exchange=%s strategies=%s",
        session_id, cfg.env_name, mode_text, cfg.underlying, cfg.exchange, strategy_names,
    )
    print(f"Gamma hedger starting - Nubra {cfg.env_name} - {mode_text} - strategies={strategy_names}")
    print(f"Events log: {events_path}")

    try:
        nubra = build_live_client(cfg.env_name, args.allow_prod)
        client = NubraClient(cfg, nubra)
    except UnsafeEnvironmentError as exc:
        logger.critical("Environment check failed: %s", exc)
        print(f"\nFATAL: {exc}\n", file=sys.stderr)
        return 1

    try:
        running = _run_all_setups(cfg, client, logger)
    except Exception as exc:  # noqa: BLE001
        logger.critical("Setup phase failed: %s", exc, exc_info=True)
        print(f"\nFATAL during setup: {exc}\n", file=sys.stderr)
        return 1

    # Shared across all strategies: one abnormal move or one run of API errors
    # halts every strategy, and one rate limiter covers the account as a whole.
    kill_switch = KillSwitch(
        max_consecutive_api_errors=cfg.max_consecutive_api_errors,
        circuit_breaker_pct=cfg.circuit_breaker_pct,
        circuit_breaker_window_sec=cfg.circuit_breaker_window_sec,
    )
    rate_limiter = HedgeRateLimiter(max_per_minute=cfg.max_hedge_trades_per_min)
    session_logger = SessionLogger(cfg, session_id)

    tick_count = 0
    tz = ZoneInfo(cfg.timezone)
    close_h, close_m = (int(x) for x in cfg.market_close_time.split(":"))

    toggle_state = TagToggleState()
    settings_store = SettingsStore()
    web_dash = WebDashboard(
        cfg,
        session_id,
        session_logger.csv_path,
        toggle_state=toggle_state,
        settings_store=settings_store,
        kill_switch=kill_switch,
        rate_limiter=rate_limiter,
    )
    web_url = web_dash.start()
    logger.info("Web dashboard listening on %s", web_url)
    print(f"Web dashboard: {web_url}")
    if not args.no_browser:
        try:
            webbrowser.open(web_url)
        except Exception as exc:  # noqa: BLE001 - a browser-launch failure must not stop the session
            logger.warning("Could not auto-open the web dashboard in a browser: %s", exc)

    try:
        with Dashboard(cfg, session_id, session_logger.csv_path) as dash:
            while True:
                now_local = datetime.now(tz)
                close_dt = now_local.replace(hour=close_h, minute=close_m, second=0, microsecond=0)
                if now_local >= close_dt:
                    logger.info("Market close reached (%s %s); stopping.", cfg.market_close_time, cfg.timezone)
                    break

                if tick_count % TAG_DISCOVERY_EVERY_N_TICKS == 0:
                    toggle_state.set_discovered(client.discover_tagged_strategies())

                # Apply settings edited in the dashboard since the last tick.
                strategy_changes, account_changes = settings_store.drain_pending()
                for rs in running:
                    changes = strategy_changes.get(rs.strat_cfg.name)
                    if changes:
                        rs.strat_cfg = replace(rs.strat_cfg, **changes)
                        logger.info("[%s] Settings updated from dashboard: %s", rs.strat_cfg.name, changes)
                if "max_hedge_trades_per_min" in account_changes:
                    rate_limiter.max_per_minute = account_changes["max_hedge_trades_per_min"]
                if "circuit_breaker_pct" in account_changes:
                    kill_switch.circuit_breaker_pct = account_changes["circuit_breaker_pct"]
                if "circuit_breaker_window_sec" in account_changes:
                    kill_switch.circuit_breaker_window_sec = account_changes["circuit_breaker_window_sec"]
                if "max_consecutive_api_errors" in account_changes:
                    kill_switch.max_consecutive_api_errors = account_changes["max_consecutive_api_errors"]
                if account_changes:
                    logger.info("Account-level settings updated from dashboard: %s", account_changes)

                # Attach / detach discovered tags according to the dashboard toggles.
                enabled_tags = toggle_state.enabled_tags()
                discovered_tags = toggle_state.discovered_tags()
                existing_names = {rs.strat_cfg.name for rs in running}
                for tag in enabled_tags:
                    if tag in existing_names:
                        continue
                    ds = discovered_tags.get(tag)
                    if ds is None:
                        continue
                    running.append(
                        RunningStrategy(
                            strat_cfg=_synthesize_attached_strategy_config(tag),
                            book=ds.book,
                            instruments=ds.instruments,
                            attached=True,
                        )
                    )
                    existing_names.add(tag)
                    logger.info(
                        "Attached gamma hedging to tag %r: %d option leg(s), futures qty_lots=%s",
                        tag,
                        len(ds.book.legs),
                        ds.book.futures.qty_lots if ds.book.futures else 0,
                    )
                for rs in running:
                    if rs.attached and rs.strat_cfg.name not in enabled_tags:
                        logger.info("Detached gamma hedging from tag %r (toggled off).", rs.strat_cfg.name)
                running[:] = [rs for rs in running if not (rs.attached and rs.strat_cfg.name not in enabled_tags)]

                views: list[StrategyView] = []
                for rs in running:
                    tick = run_tick(cfg, rs.strat_cfg, client, rs.instruments, rs.book, kill_switch, rate_limiter, rs.mode)
                    rs.mode = tick.mode
                    session_logger.log_tick(tick)
                    views.append(StrategyView(strat_cfg=rs.strat_cfg, tick=tick, book=rs.book, instruments=rs.instruments))

                tick_count += 1
                # In a dry run the internal books are simulated, so comparing them
                # with broker positions would only produce false mismatches.
                warnings = maybe_reconcile(client, [rs.book for rs in running], tick_count) if cfg.place_orders else []
                dash.update(views, tick_count, warnings)
                web_dash.update(views, tick_count, warnings)

                # The shared loop runs at the tightest interval any strategy
                # currently needs (e.g. one in HIGH_GAMMA while others are NORMAL).
                time.sleep(min(v.tick.next_poll_interval_sec for v in views))
    except KeyboardInterrupt:
        logger.info("Stopped by user (Ctrl+C) after %d ticks.", tick_count)
    finally:
        session_logger.close()
        web_dash.stop()

    print(f"\nSession ended after {tick_count} ticks.")
    print(f"Tick log:   {session_logger.csv_path}")
    print(f"Events log: {events_path}")
    return 0


# -- subcommand: check-login -----------------------------------------------------------------


def cmd_check_login(args: argparse.Namespace) -> int:
    """Interactive login: prompts for phone number, OTP and MPIN instead of reading .env."""
    from nubra_python_sdk.start_sdk import InitNubraSdk

    # The SDK's login prompts contain emoji; a legacy Windows console codepage
    # would raise UnicodeEncodeError before the prompt shows.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

    try:
        env = resolve_env(args.env, args.allow_prod)
    except UnsafeEnvironmentError as exc:
        print(f"\nFATAL: {exc}\n", file=sys.stderr)
        return 1

    print(f"Logging into Nubra {args.env.upper()} interactively.")
    print("You will be asked for your phone number, then an OTP, then your MPIN.\n")
    InitNubraSdk(env, env_creds=False)
    print("\nLogin succeeded.")
    print("To run unattended, put PHONE_NO and MPIN in .env (see .env.example).")
    return 0


# -- subcommand: cancel-open -------------------------------------------------------------------


def _describe_order(order) -> str:
    legs = getattr(order, "legs", None) or []
    if legs:
        names = ", ".join(getattr(getattr(leg, "refData", None), "displayName", "?") for leg in legs)
    else:
        names = getattr(getattr(order, "refData", None), "displayName", "?")
    return (
        f"intentOrderId={getattr(order, 'intentOrderId', '?')} "
        f"status={getattr(order, 'status', '?')} "
        f"isMulti={getattr(order, 'isMulti', '?')} "
        f"legs=[{names}]"
    )


def cmd_cancel_open(args: argparse.Namespace) -> int:
    """List (and with --yes, cancel) every OPEN order for the configured underlying.

    Orders that never fill sit as OPEN orders and accumulate across sessions. They
    are matched by the instrument's underlying (UNDERLYING in .env), not by tag,
    because open orders come back without stratTags.
    """
    cfg = replace(load_config(), env_name=args.env.upper())
    try:
        client = NubraClient(cfg, build_live_client(cfg.env_name, args.allow_prod))
    except UnsafeEnvironmentError as exc:
        print(f"\nFATAL: {exc}\n", file=sys.stderr)
        return 1

    to_cancel = client.find_open_orders(cfg.underlying)
    if not to_cancel:
        print(f"No open orders found for underlying={cfg.underlying!r}. Nothing to do.")
        return 0

    print(f"Found {len(to_cancel)} open order(s) for underlying={cfg.underlying!r}:\n")
    for order in to_cancel:
        print(f"  {_describe_order(order)}")

    if not args.yes:
        print("\nDry run only - nothing cancelled. Re-run with --yes to cancel these.")
        return 0

    # One at a time, with a short delay and retries: a batch cancel can hit a
    # transient "cancellation is temporarily unavailable" error, and per-order
    # calls keep partial failures visible.
    print()
    succeeded, failed = 0, 0
    for order in to_cancel:
        order_id = order.intentOrderId
        try:
            client.cancel_order_with_retry(order_id)
            succeeded += 1
            print(f"  cancelled intentOrderId={order_id}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"  FAILED intentOrderId={order_id}: {exc}")
        time.sleep(0.3)

    print(f"\n{succeeded} cancelled, {failed} failed out of {len(to_cancel)}.")
    return 0 if failed == 0 else 1


# -- CLI ---------------------------------------------------------------------------------------


def _add_env_flags(p: argparse.ArgumentParser) -> None:
    # UAT by default. To use production, pass --env PROD together with --allow-prod.
    p.add_argument("--env", choices=["UAT", "PROD", "uat", "prod"], default="UAT", help="Nubra environment (default: UAT)")
    p.add_argument("--allow-prod", action="store_true", help="required in addition to --env PROD; PROD is refused without it")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gamma hedging for SENSEX option sellers (dynamic delta hedging with futures).",
    )
    sub = parser.add_subparsers(dest="command", metavar="{run,check-login,cancel-open}")

    p_run = sub.add_parser("run", help="run the hedging session (default command; dry run unless --place-orders)")
    _add_env_flags(p_run)
    p_run.add_argument(
        "--place-orders",
        action="store_true",
        help="actually send the setup and hedge orders; without it orders are only printed/logged (dry run)",
    )
    p_run.add_argument("--no-browser", action="store_true", help="do not open the browser dashboard automatically")
    p_run.set_defaults(func=cmd_run)

    p_login = sub.add_parser("check-login", help="interactive login check (prompts for phone, OTP and MPIN)")
    _add_env_flags(p_login)
    p_login.set_defaults(func=cmd_check_login)

    p_cancel = sub.add_parser("cancel-open", help="list open orders for UNDERLYING; cancel them with --yes")
    _add_env_flags(p_cancel)
    p_cancel.add_argument("--yes", action="store_true", help="actually cancel the listed orders (default is a dry run)")
    p_cancel.set_defaults(func=cmd_cancel_open)

    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # `python main.py` and `python main.py --place-orders` mean `run ...`.
    if not argv or (argv[0].startswith("-") and argv[0] not in ("-h", "--help")):
        argv.insert(0, "run")
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
