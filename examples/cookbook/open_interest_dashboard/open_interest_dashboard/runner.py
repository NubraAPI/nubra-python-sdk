"""Main loop: stream data, score it, redraw the dashboards, and (optionally) send one order."""
from __future__ import annotations

import queue
import threading
import time
import webbrowser
from datetime import datetime
from typing import Any

from nubra_python_sdk.marketdata.market_data import MarketData
from nubra_python_sdk.refdata.instruments import InstrumentData
from nubra_python_sdk.ticker import websocketdata
from nubra_python_sdk.trading.trading_data import NubraTrader

from .config import load_weights
from .feeds import discover_expiry, fetch_option_chain_snapshot, instrument_ref, login
from .models import (
    Direction, IndexState, MarketReading, OptionContract, RuntimeStats, StockState,
    WebDashboardState, first_attr,
)
from .oi_change import parse_option_chain
from .orders import build_order_payload, describe_response, market_is_open
from .pressure import stock_pressure, update_index_state
from .reading import build_reading
from .terminal_dashboard import render_dashboard
from .web_dashboard import snapshot_payload, start_web_dashboard


def run(args: Any) -> int:
    weights = load_weights(args.weights_csv)
    nubra = login(args)
    instruments = InstrumentData(nubra)
    market_data = MarketData(nubra)
    order_client = NubraTrader(nubra) if args.place_orders else None
    if not args.expiry:
        args.expiry = discover_expiry(market_data)
        print(f"[expiry] using nearest NIFTY expiry {args.expiry}")

    stats = RuntimeStats()
    web_state = WebDashboardState() if args.web_dashboard else None
    web_server = None
    if web_state is not None:
        web_server = start_web_dashboard(web_state, args.web_host, args.web_port)
        url = f"http://{args.web_host}:{args.web_port}"
        print(f"[dashboard] {url}")
        if args.open_browser:
            webbrowser.open(url)

    def emit(message: str) -> None:
        stats.events.append(f"{datetime.now():%H:%M:%S} {message}")
        if not args.dashboard:
            print(message)

    states: dict[int, StockState] = {}
    missing: list[str] = []
    for symbol, weight in weights:
        ref_id = instrument_ref(instruments, symbol)
        if ref_id is None:
            missing.append(symbol)
        else:
            states[ref_id] = StockState(symbol=symbol, weight=weight, ref_id=ref_id)
    if missing:
        emit(f"[warn] no ref_id for {len(missing)} symbols: {', '.join(missing[:12])}")
    if not states:
        raise RuntimeError("No NIFTY stock ref_ids resolved from the instrument master.")

    contracts: list[OptionContract] = []
    index_state = IndexState()
    events: queue.Queue[tuple[str, Any]] = queue.Queue()
    stop_event = threading.Event()

    def on_connect(msg: str) -> None:
        stats.socket_status = msg
        events.put(("status", f"[socket] {msg}"))

    def on_close(msg: str) -> None:
        stats.socket_status = f"closed: {msg}"
        events.put(("status", f"[socket closed] {msg}"))

    def on_error(msg: str) -> None:
        stats.socket_status = f"error: {msg}"
        events.put(("status", f"[socket error] {msg}"))

    def poll_option_chain() -> None:
        """REST fallback so the contract tables fill even when the option stream is quiet."""
        warned_empty = False
        while not stop_event.is_set():
            try:
                snapshot = fetch_option_chain_snapshot(market_data, args.expiry)
                if snapshot:
                    warned_empty = False
                    events.put(("option_snapshot", snapshot))
                elif not warned_empty:
                    warned_empty = True
                    events.put(("status", "[warn] REST option-chain snapshot returned no CE/PE rows"))
            except Exception as exc:
                events.put(("status", f"[warn] REST option-chain snapshot failed: {exc}"))
            stop_event.wait(max(1.0, args.option_poll_seconds))

    socket = websocketdata.NubraDataSocket(
        client=nubra,
        on_index_data=lambda msg: events.put(("index", msg)),
        on_orderbook_data=lambda msg: events.put(("orderbook", msg)),
        on_option_data=lambda msg: events.put(("option", msg)),
        on_connect=on_connect,
        on_close=on_close,
        on_error=on_error,
    )
    socket.connect()
    time.sleep(args.connect_wait)
    socket.subscribe(list(states), data_type="orderbook")
    socket.subscribe(["NIFTY"], data_type="index", exchange="NSE")
    socket.subscribe([f"NIFTY:{args.expiry}"], data_type="option", exchange="NSE")
    poll_thread: threading.Thread | None = None
    if args.option_poll_seconds > 0:
        poll_thread = threading.Thread(target=poll_option_chain, name="option-chain-poll", daemon=True)
        poll_thread.start()
    mode = "orders ON" if args.place_orders else "dry-run (no orders sent)"
    emit(f"[ready] tracking {len(states)} stocks and NIFTY:{args.expiry}; {mode}")

    reading = MarketReading(Direction.NEUTRAL, 0.0, 0.0, 0.0, "warming up")
    orders_sent = 0
    last_order_at = 0.0
    last_eval_at = 0.0
    last_render_at = 0.0
    started_at = time.time()

    def publish() -> None:
        if web_state is not None:
            web_state.update(snapshot_payload(reading, states, index_state, contracts, stats, orders_sent, args))

    def render() -> None:
        if args.dashboard:
            render_dashboard(reading, states, list(contracts), stats, orders_sent, args)

    publish()
    try:
        while True:
            if args.max_minutes and (time.time() - started_at) > args.max_minutes * 60:
                break
            try:
                kind, msg = events.get(timeout=1.0)
            except queue.Empty:
                kind, msg = "", None

            if kind == "orderbook":
                for item in first_attr(msg, ["instruments"], None) or [msg]:
                    ref_id = first_attr(item, ["ref_id"])
                    if ref_id is not None and int(ref_id) in states:
                        state = states[int(ref_id)]
                        state.pressure.append(stock_pressure(item, state))
                        stats.stock_ticks += 1
                        stats.last_stock_at = time.time()
            elif kind == "index":
                updated = False
                for item in first_attr(msg, ["indexes"], None) or first_attr(msg, ["instruments"], None) or [msg]:
                    name = str(first_attr(item, ["indexname", "symbol", "asset"], "NIFTY") or "NIFTY").upper()
                    if "NIFTY" in name and update_index_state(item, index_state):
                        updated = True
                if updated:
                    stats.index_ticks += 1
                    stats.last_index_at = time.time()
            elif kind == "option":
                parsed = parse_option_chain(msg)
                stats.option_ticks += 1
                if parsed:
                    contracts = parsed
                    stats.last_option_at = time.time()
                else:
                    emit("[warn] option stream packet had no CE/PE rows; relying on REST snapshots")
            elif kind == "option_snapshot":
                contracts = msg or []
                stats.option_ticks += 1
                stats.last_option_at = time.time()
            elif kind == "status" and msg:
                emit(str(msg))
            publish()

            if time.time() - last_eval_at < args.decision_interval:
                if time.time() - last_render_at >= args.dashboard_refresh:
                    render()
                    last_render_at = time.time()
                continue
            last_eval_at = time.time()

            reading = build_reading(
                states, contracts, args.capital, args.min_score, args.risk_fraction,
                args.min_pressure_abs, args.min_oi_abs, args.stoploss_pct,
            )
            emit(
                f"[{datetime.now():%H:%M:%S}] {reading.direction.value:<7} bias={reading.score:+.3f} "
                f"pressure={reading.pressure_score:+.3f} oi={reading.oi_score:+.3f} "
                f"orders={orders_sent}/{args.max_orders} reason={reading.reason}"
            )
            publish()

            # Optional order helper: only a directional reading with a sized candidate gets here.
            if reading.qty > 0 and reading.contract is not None:
                if orders_sent >= args.max_orders:
                    pass
                elif time.time() - last_order_at < args.order_cooldown_seconds:
                    pass
                elif args.only_market_hours and not market_is_open():
                    emit("[skip] outside the 09:16-15:10 order window")
                else:
                    tick = getattr(instruments.get_instrument_by_ref_id(reading.contract.ref_id), "tick_size", None) or 5
                    payload = build_order_payload(reading, args, tick_size=tick)
                    if args.place_orders and order_client is not None:
                        emit(f"[order] sending {payload}")
                        try:
                            emit(f"[order] response: {describe_response(order_client.create_order(payload))}")
                        except Exception as exc:
                            emit(f"[order] failed: {exc}")
                    else:
                        emit(f"[dry-run] would send {payload}")
                    orders_sent += 1
                    last_order_at = time.time()
                    publish()
            render()
            last_render_at = time.time()
    except KeyboardInterrupt:
        print("\n[stopped] Ctrl+C")
    finally:
        stop_event.set()
        try:
            socket.close()
        except Exception:
            pass
        if poll_thread is not None:
            poll_thread.join(timeout=2.0)
        if web_server is not None:
            web_server.shutdown()
    return 0
