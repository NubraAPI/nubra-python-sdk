"""Local web dashboard: a read-only JSON state endpoint plus one static HTML page."""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .models import IndexState, MarketReading, OptionContract, RuntimeStats, StockState, WebDashboardState
from .option_selection import ranked_contracts
from .pressure import participation_map, top_pressure

HTML_PATH = Path(__file__).with_name("dashboard.html")


def snapshot_payload(
    reading: MarketReading,
    states: dict[int, StockState],
    index_state: IndexState,
    contracts: list[OptionContract],
    stats: RuntimeStats,
    orders_sent: int,
    args: Any,
) -> dict[str, Any]:
    """Everything the page renders, as JSON-serializable data."""

    def age(ts: float | None) -> float | None:
        return None if ts is None else round(time.time() - ts, 1)

    contract = None
    if reading.contract:
        c = reading.contract
        contract = {
            "type": c.option_type, "strike": c.strike, "ltp": c.ltp, "delta": c.delta,
            "gamma": c.gamma, "theta": c.theta, "volume": c.volume, "oi": c.oi,
            "oi_change": c.oi_change, "lot_cost": round(c.lot_cost, 2), "qty": reading.qty,
            "ref_id": c.ref_id,
        }

    pressure_ok = abs(reading.pressure_score) >= args.min_pressure_abs
    oi_ok = abs(reading.oi_score) >= args.min_oi_abs
    agree = reading.pressure_score * reading.oi_score > 0
    agreement_ok = pressure_ok and oi_ok and agree
    score_ok = agreement_ok and abs(reading.score) >= args.min_score
    if not contracts:
        contract_value, contract_need = "no CE/PE feed", "option chain"
    elif not score_ok:
        contract_value, contract_need = "not evaluated", "reading first"
    elif reading.contract and reading.qty > 0:
        contract_value = f"{reading.contract.option_type} {reading.contract.strike:g} x{reading.qty}"
        contract_need = "affordable"
    elif reading.contract:
        contract_value = f"{reading.contract.option_type} {reading.contract.strike:g} excluded"
        contract_need = "risk filter"
    else:
        contract_value, contract_need = "none", "liquid affordable"

    return {
        "clock": datetime.now().strftime("%H:%M:%S"),
        "underlying": "NIFTY",
        "env": args.env,
        "expiry": args.expiry,
        "capital": args.capital,
        "orders": "ON" if args.place_orders else "DRY-RUN",
        "order_mode": args.order_mode.upper(),
        "orders_sent": orders_sent,
        "max_orders": args.max_orders,
        "direction": reading.direction.value,
        "score": round(reading.score, 4),
        "pressure_score": round(reading.pressure_score, 4),
        "oi_score": round(reading.oi_score, 4),
        "reason": reading.reason,
        "candidate": contract,
        "stock_ticks": stats.stock_ticks,
        "index_ticks": stats.index_ticks,
        "option_ticks": stats.option_ticks,
        "option_feed": "OK" if contracts else "WAITING",
        "ce_count": sum(1 for c in contracts if c.option_type == "CE"),
        "pe_count": sum(1 for c in contracts if c.option_type == "PE"),
        "atm": None if not contracts else min(contracts, key=lambda c: abs(abs(c.delta) - 0.5)).strike,
        "ranked_contracts": ranked_contracts(contracts, args.capital),
        "checks": [
            {"name": "Pressure score", "ok": pressure_ok, "value": f"{reading.pressure_score:+.3f}", "need": f">{args.min_pressure_abs:.2f} abs"},
            {"name": "OI change score", "ok": oi_ok, "value": f"{reading.oi_score:+.3f}", "need": f">{args.min_oi_abs:.2f} abs"},
            {"name": "Agreement", "ok": agreement_ok, "value": "same side" if agree else "mixed", "need": "both strong"},
            {"name": "Bias score", "ok": score_ok, "value": f"{reading.score:+.3f}", "need": f">{args.min_score:.2f} abs"},
            {"name": "Candidate contract", "ok": bool(reading.contract and reading.qty > 0), "value": contract_value, "need": contract_need},
        ],
        "option_age": age(stats.last_option_at),
        "stock_age": age(stats.last_stock_at),
        "index_age": age(stats.last_index_at),
        "top_pressure": [
            {"symbol": s, "weight": w, "pressure": round(p, 4)} for s, w, p in top_pressure(states, 8)
        ],
        "participation": participation_map(states, index_state),
        "events": list(stats.events),
    }


def start_web_dashboard(state: WebDashboardState, host: str, port: int) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *args: Any) -> None:
            return

        def _send(self, body: bytes, content_type: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path == "/" or self.path.startswith("/?"):
                self._send(HTML_PATH.read_bytes(), "text/html; charset=utf-8")
            elif self.path.startswith("/api/state"):
                self._send(json.dumps(state.read(), separators=(",", ":")).encode("utf-8"), "application/json")
            else:
                self.send_error(404)

    server = ThreadingHTTPServer((host, port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
