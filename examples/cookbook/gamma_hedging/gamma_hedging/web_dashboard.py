"""
Local browser dashboard, served at http://127.0.0.1:<port>.

Runs ALONGSIDE the terminal dashboard (`gamma_hedging.dashboard.Dashboard`), not
instead of it - `main.py` calls `.update(views, tick_count, warnings)` on
both every tick. This is a genuinely separate, smaller surface: no new
process, no external dependency (stdlib `http.server` only), just a
second view onto the same `StrategyView` data the terminal one renders.

Design choices, and why:
  - stdlib `ThreadingHTTPServer` in a background daemon thread, rather than
    a framework (Flask/FastAPI/etc.), since there is only one page to serve.
  - The page fetches `/fragment` every ~1.5s via plain JS and swaps it into
    a `<div>`, rather than a `<meta http-equiv="refresh">` full-page
    reload, which would flicker on every tick.
  - All styling is inline in the one HTML page; nothing is loaded from a
    CDN or the network, so this works fully offline.
"""

from __future__ import annotations

import html
import json
import threading
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .config import Config
from .dashboard import StrategyView
from .hedger import HIGH_GAMMA_MODE
from .settings_control import SettingsStore
from .tag_control import TagToggleState

_PAGE_SHELL = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Gamma Hedger</title>
<style>
  :root {{
    color-scheme: dark;
  }}
  body {{
    background: #0d1117;
    color: #e6edf3;
    font-family: "Cascadia Code", "Consolas", "SF Mono", Menlo, monospace;
    font-size: 14px;
    margin: 0;
    padding: 16px 20px 40px 20px;
  }}
  .header {{
    display: flex;
    align-items: center;
    gap: 14px;
    flex-wrap: wrap;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 10px 16px;
    margin-bottom: 14px;
  }}
  .title {{
    font-weight: 700;
    background: #21262d;
    padding: 3px 10px;
    border-radius: 4px;
  }}
  .badge-live {{
    font-weight: 700;
    background: #a35a00;
    color: white;
    padding: 3px 10px;
    border-radius: 4px;
  }}
  .history-btn {{
    font: inherit;
    font-weight: 700;
    background: #21262d;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 3px 10px;
    cursor: pointer;
  }}
  .history-btn:first-of-type {{ margin-left: auto; }}
  .history-btn:hover {{ background: #30363d; }}
  .dim {{ color: #8b949e; }}
  .halted-banner {{
    font-weight: 700;
    background: #b62324;
    color: white;
    padding: 6px 12px;
    border-radius: 4px;
    width: 100%;
  }}
  .strategy {{
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 14px;
  }}
  .strategy.filled {{ border-color: #2ea043; box-shadow: 0 0 0 1px #2ea043; }}
  .strategy.pending {{ border-color: #d29922; box-shadow: 0 0 0 1px #d29922; }}
  .strategy.halted, .strategy.error {{ border-color: #b62324; box-shadow: 0 0 0 1px #b62324; }}
  .strategy.preview {{ border-style: dashed; }}
  .strategy-title {{
    display: flex;
    align-items: center;
    gap: 10px;
    font-weight: 700;
    margin-bottom: 8px;
  }}
  .strategy-title-text {{ flex: 1; }}
  .filled-flag {{ color: #3fb950; }}
  .pending-flag {{ color: #d29922; }}
  .halted-flag, .error-flag {{ color: #f85149; }}
  .stats-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 22px;
    margin-bottom: 8px;
  }}
  .stat-label {{ font-weight: 700; }}
  .green {{ color: #3fb950; }}
  .red {{ color: #f85149; }}
  .yellow {{ color: #d29922; }}
  .mode-badge {{
    padding: 2px 8px;
    border-radius: 4px;
    background: #21262d;
    font-weight: 700;
  }}
  .mode-badge.high-gamma {{ color: #d29922; }}
  .mode-badge.normal {{ color: #3fb950; }}
  .own-actions {{
    background: #161b22;
    border-radius: 6px;
    padding: 6px 12px;
    margin-top: 8px;
    font-size: 13px;
  }}
  .rationale {{
    background: #161b22;
    border-radius: 6px;
    padding: 8px 12px;
    margin-bottom: 10px;
    white-space: pre-wrap;
  }}
  .rationale div {{ margin: 2px 0; }}
  table {{
    width: 100%;
    border-collapse: collapse;
  }}
  th, td {{
    text-align: right;
    padding: 3px 10px;
    white-space: nowrap;
  }}
  th:first-child, td:first-child {{ text-align: left; }}
  th {{ color: #8b949e; font-weight: 600; border-bottom: 1px solid #30363d; }}
  .actions {{
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 10px 16px;
    margin-bottom: 14px;
  }}
  .action-line {{ margin: 2px 0; }}
  .footer {{ color: #8b949e; }}
  .toggle-switch {{
    position: relative;
    display: inline-block;
    width: 38px;
    height: 20px;
    flex-shrink: 0;
  }}
  .toggle-switch input {{ opacity: 0; width: 0; height: 0; }}
  .toggle-slider {{
    position: absolute;
    cursor: pointer;
    top: 0; left: 0; right: 0; bottom: 0;
    background: #30363d;
    border-radius: 20px;
    transition: 0.15s;
  }}
  .toggle-slider::before {{
    position: absolute;
    content: "";
    height: 14px; width: 14px;
    left: 3px; bottom: 3px;
    background: #e6edf3;
    border-radius: 50%;
    transition: 0.15s;
  }}
  .toggle-switch input:checked + .toggle-slider {{ background: #2ea043; }}
  .toggle-switch input:checked + .toggle-slider::before {{ transform: translateX(18px); }}
  .settings-block {{
    border: 1px solid #21262d;
    border-radius: 6px;
    padding: 8px 12px;
    margin-bottom: 10px;
  }}
  .settings-block-title {{ font-weight: 700; margin-bottom: 6px; }}
  .settings-row {{
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    margin: 4px 0;
  }}
  .settings-row label {{ min-width: 220px; color: #8b949e; }}
  .settings-row input {{
    background: #0d1117;
    border: 1px solid #30363d;
    color: #e6edf3;
    border-radius: 4px;
    padding: 2px 6px;
    width: 110px;
    font: inherit;
  }}
  .save-btn {{
    font: inherit;
    font-weight: 700;
    background: #21262d;
    color: #e6edf3;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 3px 10px;
    cursor: pointer;
    margin-top: 4px;
  }}
  .save-btn:hover {{ background: #30363d; }}
  .settings-msg {{ margin-left: 8px; font-size: 13px; }}
</style>
</head>
<body>
<div id="content">{initial}</div>
<script>
// The History panel's open/closed state has to live outside #content:
// /fragment replaces that div's entire innerHTML every 1.5s (so hedge data
// stays live without a full page reload), which would otherwise silently
// re-hide the panel as soon as it was opened.
let historyOpen = false;
let settingsOpen = false;
function toggleHistory() {{
  historyOpen = !historyOpen;
  applyPanelVisibility();
}}
function toggleSettings() {{
  settingsOpen = !settingsOpen;
  applyPanelVisibility();
}}
function applyPanelVisibility() {{
  const h = document.getElementById('history-panel');
  if (h) h.hidden = !historyOpen;
  const s = document.getElementById('settings-panel');
  if (s) s.hidden = !settingsOpen;
}}

// /fragment replaces #content's entire innerHTML every 1.5s so the rest of
// the dashboard (Greeks, P&L, hedge actions) stays live - but that would
// also wipe out anything typed into a Settings input mid-edit, before the
// Save click landed. Snapshotting values before the swap and writing them
// back into the freshly-rendered inputs afterward keeps live data flowing
// everywhere else while an in-progress edit survives untouched.
function _snapshotSettingsInputs() {{
  const snapshot = {{}};
  document.querySelectorAll('#settings-panel .settings-block').forEach(block => {{
    const key = block.dataset.strategy || 'account';
    block.querySelectorAll('input[data-field]').forEach(inp => {{
      snapshot[`${{key}}:${{inp.dataset.field}}`] = inp.value;
    }});
  }});
  return snapshot;
}}
function _restoreSettingsInputs(snapshot) {{
  document.querySelectorAll('#settings-panel .settings-block').forEach(block => {{
    const key = block.dataset.strategy || 'account';
    block.querySelectorAll('input[data-field]').forEach(inp => {{
      const k = `${{key}}:${{inp.dataset.field}}`;
      if (k in snapshot) inp.value = snapshot[k];
    }});
  }});
}}

async function refresh() {{
  try {{
    const settingsSnapshot = _snapshotSettingsInputs();
    const res = await fetch('/fragment', {{cache: 'no-store'}});
    if (res.ok) {{
      document.getElementById('content').innerHTML = await res.text();
      applyPanelVisibility();
      _restoreSettingsInputs(settingsSnapshot);
    }}
  }} catch (e) {{ /* transient fetch error, next tick will retry */ }}
}}
setInterval(refresh, 1500);

async function toggleTag(tag, enabled) {{
  try {{
    await fetch(`/api/tags/${{encodeURIComponent(tag)}}/${{enabled ? 'enable' : 'disable'}}`, {{method: 'POST'}});
  }} catch (e) {{ /* transient - next /fragment refresh will reflect the real state either way */ }}
}}

function _collectFields(container) {{
  const out = {{}};
  container.querySelectorAll('input[data-field]').forEach(inp => {{ out[inp.dataset.field] = inp.value; }});
  return out;
}}

async function saveAccountSettings(btn) {{
  const container = btn.closest('.settings-block');
  const msg = container.querySelector('.settings-msg');
  msg.textContent = 'Saving...';
  msg.className = 'settings-msg dim';
  try {{
    const res = await fetch('/api/settings/account', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify(_collectFields(container)),
    }});
    const data = await res.json();
    if (res.ok) {{
      msg.textContent = 'Saved.';
      msg.className = 'settings-msg green';
    }} else {{
      msg.textContent = data.error || 'Failed.';
      msg.className = 'settings-msg red';
    }}
  }} catch (e) {{
    msg.textContent = 'Network error.';
    msg.className = 'settings-msg red';
  }}
}}

async function saveStrategySettings(btn) {{
  const container = btn.closest('.settings-block');
  const msg = container.querySelector('.settings-msg');
  const strategy = container.dataset.strategy;
  msg.textContent = 'Saving...';
  msg.className = 'settings-msg dim';
  try {{
    const res = await fetch(`/api/settings/strategy/${{encodeURIComponent(strategy)}}`, {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify(_collectFields(container)),
    }});
    const data = await res.json();
    if (res.ok) {{
      msg.textContent = 'Saved.';
      msg.className = 'settings-msg green';
    }} else {{
      msg.textContent = data.error || 'Failed.';
      msg.className = 'settings-msg red';
    }}
  }} catch (e) {{
    msg.textContent = 'Network error.';
    msg.className = 'settings-msg red';
  }}
}}
</script>
</body>
</html>
"""


def _esc(value) -> str:
    return html.escape(str(value))


class WebDashboard:
    def __init__(
        self,
        cfg: Config,
        session_id: str,
        csv_path: str,
        toggle_state: TagToggleState | None = None,
        settings_store: SettingsStore | None = None,
        kill_switch=None,
        rate_limiter=None,
    ):
        self.cfg = cfg
        self.session_id = session_id
        self.csv_path = csv_path
        self.toggle_state = toggle_state
        self.settings_store = settings_store
        self.kill_switch = kill_switch
        self.rate_limiter = rate_limiter
        self._lock = threading.Lock()
        self._fragment_html = "<p class='dim'>Waiting for first tick...</p>"
        self._recent_actions: list[tuple[float, str, str, bool, bool]] = []
        self._reconcile_warnings: list[str] = []
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._start_time = datetime.now()

    def _tags_payload(self) -> dict:
        if self.toggle_state is None:
            return {"tags": []}
        own_names = {s.name for s in self.cfg.strategies}
        enabled = self.toggle_state.enabled_tags()
        discovered = self.toggle_state.discovered_tags()
        tags = []
        for tag, ds in sorted(discovered.items()):
            tags.append(
                {
                    "tag": tag,
                    "option_legs": len(ds.book.legs),
                    "futures_qty_lots": ds.book.futures.qty_lots if ds.book.futures else 0,
                    "already_running": tag in own_names,
                    "enabled": tag in enabled,
                }
            )
        return {"tags": tags}

    def start(self) -> str:
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):  # noqa: A002 - silence default request logging
                pass

            def _write(self, body: bytes, content_type: str) -> None:
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _write_json(self, payload: dict, status: int = 200) -> None:
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:  # noqa: N802 - stdlib method name
                if self.path.startswith("/fragment"):
                    with outer._lock:
                        fragment = outer._fragment_html
                    self._write(fragment.encode("utf-8"), "text/html; charset=utf-8")
                    return
                if self.path.startswith("/api/tags"):
                    self._write_json(outer._tags_payload())
                    return
                with outer._lock:
                    fragment = outer._fragment_html
                page = _PAGE_SHELL.format(initial=fragment)
                self._write(page.encode("utf-8"), "text/html; charset=utf-8")

            def _read_json_body(self) -> dict:
                length = int(self.headers.get("Content-Length", 0) or 0)
                if length <= 0:
                    return {}
                raw = self.rfile.read(length)
                return json.loads(raw) if raw else {}

            def do_POST(self) -> None:  # noqa: N802 - stdlib method name
                parts = [p for p in self.path.split("/") if p]

                # /api/tags/<tag>/enable or /api/tags/<tag>/disable
                if len(parts) == 4 and parts[0] == "api" and parts[1] == "tags" and parts[3] in ("enable", "disable"):
                    tag = urllib.parse.unquote(parts[2])
                    action = parts[3]
                    if outer.toggle_state is None:
                        self._write_json({"error": "toggling is not available"}, status=503)
                        return
                    if action == "enable":
                        outer.toggle_state.enable(tag)
                    else:
                        outer.toggle_state.disable(tag)
                    self._write_json(outer._tags_payload())
                    return

                # /api/settings/account  (JSON body: {field: value, ...})
                if len(parts) == 3 and parts[0] == "api" and parts[1] == "settings" and parts[2] == "account":
                    if outer.settings_store is None:
                        self._write_json({"error": "settings are not available"}, status=503)
                        return
                    try:
                        body = self._read_json_body()
                        applied = {}
                        for field_name, raw_value in body.items():
                            applied[field_name] = outer.settings_store.set_account_field(field_name, raw_value)
                        self._write_json({"applied": applied})
                    except (ValueError, TypeError, json.JSONDecodeError) as exc:
                        self._write_json({"error": str(exc)}, status=400)
                    return

                # /api/settings/strategy/<name>  (JSON body: {field: value, ...})
                if len(parts) == 4 and parts[0] == "api" and parts[1] == "settings" and parts[2] == "strategy":
                    name = urllib.parse.unquote(parts[3])
                    if outer.settings_store is None:
                        self._write_json({"error": "settings are not available"}, status=503)
                        return
                    try:
                        body = self._read_json_body()
                        applied = {}
                        for field_name, raw_value in body.items():
                            applied[field_name] = outer.settings_store.set_strategy_field(name, field_name, raw_value)
                        self._write_json({"applied": applied})
                    except (ValueError, TypeError, json.JSONDecodeError) as exc:
                        self._write_json({"error": str(exc)}, status=400)
                    return

                self._write_json({"error": "not found"}, status=404)

        self._server = ThreadingHTTPServer(("127.0.0.1", self.cfg.web_dashboard_port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return f"http://127.0.0.1:{self.cfg.web_dashboard_port}"

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()

    def update(
        self,
        views: list[StrategyView],
        tick_count: int,
        reconcile_warnings: list[str] | None = None,
    ) -> None:
        for view in views:
            if view.tick.hedge_action:
                self._recent_actions.append(
                    (
                        view.tick.timestamp,
                        view.strat_cfg.name,
                        view.tick.hedge_action,
                        view.tick.hedge_fired,
                        view.tick.hedge_confirmed,
                    )
                )
        # Capped generously (not to 12) so the History panel can show a real
        # session-long count, not just what the quick feed below displays.
        self._recent_actions = self._recent_actions[-2000:]
        for w in reconcile_warnings or []:
            self._reconcile_warnings.append(w)
        self._reconcile_warnings = self._reconcile_warnings[-5:]

        fragment = self._render_fragment(views, tick_count)
        with self._lock:
            self._fragment_html = fragment

    # -- rendering ------------------------------------------------------------

    def _render_fragment(self, views: list[StrategyView], tick_count: int) -> str:
        own_config_names = {s.name for s in self.cfg.strategies}
        rendered_tags = set()
        parts = [self._render_header(views)]
        for v in views:
            # A strategy attached mid-session from a live-discovered tag
            # (see TagToggleState) gets a toggle in its own title so it can
            # be detached the same way it was attached - a `.env`-configured
            # strategy always runs and never gets one.
            show_toggle = v.strat_cfg.name not in own_config_names
            parts.append(self._render_strategy(v, show_toggle=show_toggle))
            rendered_tags.add(v.strat_cfg.name)
        if self.toggle_state is not None:
            for tag, ds in sorted(self.toggle_state.discovered_tags().items()):
                if tag in rendered_tags:
                    continue  # already rendered above with full live tick data
                parts.append(self._render_discovered_preview(tag, ds))
        parts.append(self._render_settings_panel(views))
        parts.append(self._render_history_panel())
        parts.append(self._render_actions())
        parts.append(self._render_footer(views, tick_count))
        return "\n".join(parts)

    @staticmethod
    def _toggle_html(tag: str, checked: bool) -> str:
        # data-tag (HTML-escaped normally) rather than interpolating the tag
        # into inline JS keeps this safe regardless of what characters a
        # user's tag name contains - see toggleTag() in _PAGE_SHELL.
        checked_attr = " checked" if checked else ""
        return (
            f"<label class='toggle-switch'><input type='checkbox' data-tag='{_esc(tag)}'{checked_attr} "
            "onchange=\"toggleTag(this.dataset.tag, this.checked)\"><span class='toggle-slider'></span></label>"
        )

    def _render_header(self, views: list[StrategyView]) -> str:
        elapsed = str(datetime.now() - self._start_time).split(".")[0]
        halted = any(v.tick.halted for v in views)
        banner = ""
        if halted:
            reason = next((v.tick.halted_reason for v in views if v.tick.halted_reason), "")
            banner = f"<div class='halted-banner'>!!! TRADING HALTED - KILL SWITCH ENGAGED (all strategies) !!!<br>Reason: {_esc(reason)}</div>"
        return (
            "<div class='header'>"
            f"<span class='title'>GAMMA HEDGER</span>"
            f"<span>{_esc(self.cfg.underlying)} &middot; {len(views)} strategy(ies)</span>"
            f"<span class='dim'>session={_esc(self.session_id)}</span>"
            f"<span class='dim'>elapsed={elapsed}</span>"
            f"<span class='badge-live'>NUBRA {_esc(self.cfg.env_name)} | "
            f"{'ORDERS ENABLED' if self.cfg.place_orders else 'DRY RUN - NO ORDERS SENT'}</span>"
            "<button class='history-btn' onclick='toggleHistory()'>History</button>"
            "<button class='history-btn' onclick='toggleSettings()'>Settings</button>"
            f"{banner}"
            "</div>"
        )

    def _render_strategy(self, view: StrategyView, show_toggle: bool = False) -> str:
        tick, book, strat_cfg = view.tick, view.book, view.strat_cfg

        css_class = "strategy"
        flag = ""
        if tick.hedge_fired and tick.hedge_dry_run:
            css_class += " pending"
            flag = " <span class='pending-flag'>*** HEDGE SIMULATED - DRY RUN, NO ORDER SENT ***</span>"
        elif tick.hedge_fired and tick.hedge_confirmed:
            css_class += " filled"
            flag = " <span class='filled-flag'>*** HEDGE FILLED ***</span>"
        elif tick.hedge_fired:
            # Order went out and was not rejected, but Nubra has not confirmed
            # a fill: amber, never claimed as FILLED.
            css_class += " pending"
            flag = " <span class='pending-flag'>*** HEDGE PLACED - PENDING FILL ***</span>"
        elif tick.halted:
            css_class += " halted"
            flag = " <span class='halted-flag'>[HALTED]</span>"
        elif tick.error:
            css_class += " error"
            flag = " <span class='error-flag'>[DATA ERROR]</span>"

        spot_str = f"{tick.spot:,.2f}" if tick.spot is not None else "n/a"

        delta_html = "n/a"
        if tick.net_delta is not None:
            tolerance_units = strat_cfg.delta_tolerance_lots * book.futures.lot_size
            delta_class = "green" if abs(tick.net_delta) <= tolerance_units else "red"
            delta_html = f"<span class='{delta_class}'>{tick.net_delta:+,.1f}</span> (band +/-{tolerance_units:,.1f})"

        gamma_html = "n/a"
        if tick.net_gamma is not None:
            gamma_class = "yellow" if tick.mode == HIGH_GAMMA_MODE else "green"
            gamma_html = f"<span class='{gamma_class}'>{tick.net_gamma:+.6f}</span> (thr {strat_cfg.high_gamma_threshold:.6f})"

        mode_class = "high-gamma" if tick.mode == HIGH_GAMMA_MODE else "normal"
        pnl_class = "green" if tick.total_pnl >= 0 else "red"

        stats_row = (
            "<div class='stats-row'>"
            f"<div><span class='stat-label'>Spot</span> {spot_str}</div>"
            f"<div><span class='stat-label'>Net Delta</span> {delta_html}</div>"
            f"<div><span class='stat-label'>Net Gamma</span> {gamma_html}</div>"
            f"<div class='mode-badge {mode_class}'>{_esc(tick.mode)}</div>"
            f"<div><span class='stat-label'>Futures</span> {tick.futures_lots:+d} lot(s)</div>"
            f"<div><span class='stat-label'>Total P&amp;L</span> <span class='{pnl_class}'>{tick.total_pnl:+,.2f}</span></div>"
            "</div>"
        )

        notable = (
            tick.hedge_fired
            or tick.halted
            or tick.error
            or tick.mode_changed
            or any(("BAND BREACHED" in l.upper() or "FAILED" in l.upper()) for l in tick.reasoning)
        )
        if not tick.reasoning:
            rationale = "<div class='dim'>(waiting for first tick...)</div>"
        elif notable:
            lines = []
            for line in tick.reasoning:
                upper = line.upper()
                cls = ""
                if "FAILED" in upper or "BAND BREACHED" in upper:
                    cls = "red"
                elif "FINAL DECISION" in upper and ("BUY" in upper or "SELL" in upper):
                    cls = "green"
                elif "NO TRADE" in upper or "no hedge needed" in line:
                    cls = "green"
                elif "PASSED" in upper:
                    cls = "yellow"
                cls_attr = f" class='{cls}'" if cls else ""
                lines.append(f"<div{cls_attr}>- {_esc(line)}</div>")
            rationale = "".join(lines)
        else:
            rationale = f"<div class='dim'>Delta within band, Gamma -> {_esc(tick.mode)}. No action needed this tick.</div>"

        rows = []
        for leg in book.legs:
            pnl = leg.pnl()
            pnl_cls = "green" if pnl >= 0 else "red"
            rows.append(
                "<tr>"
                f"<td>{_esc(leg.option_type)} {leg.strike:,.0f}</td>"
                f"<td>{leg.qty_lots:+d}</td>"
                f"<td>{leg.entry_price_rupees:,.2f}</td>"
                f"<td>{leg.current_price_rupees:,.2f}</td>"
                f"<td>{leg.delta:+.3f}</td>"
                f"<td>{leg.gamma:+.5f}</td>"
                f"<td class='{pnl_cls}'>{pnl:+,.2f}</td>"
                f"<td>{'api' if leg.greeks_source == 'api' else 'BS'}</td>"
                "</tr>"
            )
        if book.futures is not None:
            fut_pnl = book.futures.total_pnl()
            fut_cls = "green" if fut_pnl >= 0 else "red"
            entry = f"{book.futures.avg_entry_price_rupees:,.2f}" if book.futures.qty_lots else "n/a"
            rows.append(
                "<tr>"
                f"<td>FUT {_esc(view.instruments.underlying)}</td>"
                f"<td>{book.futures.qty_lots:+d}</td>"
                f"<td>{entry}</td>"
                f"<td>{book.futures.current_price_rupees:,.2f}</td>"
                "<td>1.000</td><td>0.000</td>"
                f"<td class='{fut_cls}'>{fut_pnl:+,.2f}</td>"
                "<td>n/a</td>"
                "</tr>"
            )

        table = (
            "<table><thead><tr>"
            "<th>Instrument</th><th>Qty</th><th>Entry</th><th>Current</th>"
            "<th>Delta</th><th>Gamma</th><th>P&amp;L</th><th>Src</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
        )

        own_actions = self._strategy_recent_actions_html(strat_cfg.name)
        toggle = self._toggle_html(strat_cfg.strat_tag, checked=True) if show_toggle else ""

        return (
            f"<div class='{css_class}'>"
            "<div class='strategy-title'>"
            f"<span class='strategy-title-text'>{_esc(strat_cfg.name)} "
            f"({_esc(strat_cfg.strategy_type.value)}, tag={_esc(strat_cfg.strat_tag)}){flag}</span>"
            f"{toggle}"
            "</div>"
            f"{stats_row}"
            f"<div class='rationale'>{rationale}</div>"
            f"{table}"
            f"{own_actions}"
            "</div>"
        )

    def _render_discovered_preview(self, tag: str, ds) -> str:
        """A tag found live on the broker that has not been toggled on yet.

        Same card shape as a running strategy (legs always visible), just
        without live Greeks/current-price/P&L, since
        those only exist once this strategy is actually being ticked.
        """
        enabled = tag in self.toggle_state.enabled_tags() if self.toggle_state is not None else False
        rows = []
        for leg in ds.book.legs:
            rows.append(
                "<tr>"
                f"<td>{_esc(leg.option_type)} {leg.strike:,.0f}</td>"
                f"<td>{leg.qty_lots:+d}</td>"
                f"<td>{leg.entry_price_rupees:,.2f}</td>"
                "<td>n/a</td><td>n/a</td><td>n/a</td><td>n/a</td><td>n/a</td>"
                "</tr>"
            )
        if ds.book.futures is not None and ds.book.futures.qty_lots:
            rows.append(
                "<tr>"
                f"<td>FUT {_esc(ds.instruments.underlying)}</td>"
                f"<td>{ds.book.futures.qty_lots:+d}</td>"
                f"<td>{ds.book.futures.avg_entry_price_rupees:,.2f}</td>"
                "<td>n/a</td><td>n/a</td><td>n/a</td><td>n/a</td><td>n/a</td>"
                "</tr>"
            )
        table = (
            "<table><thead><tr>"
            "<th>Instrument</th><th>Qty</th><th>Entry</th><th>Current</th>"
            "<th>Delta</th><th>Gamma</th><th>P&amp;L</th><th>Src</th>"
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
        )
        return (
            "<div class='strategy preview'>"
            "<div class='strategy-title'>"
            f"<span class='strategy-title-text'>{_esc(tag)} <span class='dim'>(discovered on the broker, not yet attached)</span></span>"
            f"{self._toggle_html(tag, checked=enabled)}"
            "</div>"
            "<div class='rationale'><div class='dim'>Toggle on to start gamma-hedging this position - "
            "Greeks, current price, and P&amp;L will appear once it's attached and ticked.</div></div>"
            f"{table}"
            "</div>"
        )

    def _strategy_recent_actions_html(self, strategy_name: str, limit: int = 5) -> str:
        """This strategy's own hedge-action history, scoped out of the
        shared recent-actions list - mirrors dashboard.py's
        _strategy_recent_actions so both views stay consistent.
        """
        own = [a for a in self._recent_actions if a[1] == strategy_name]
        if not own:
            return ""
        lines = []
        for ts, _name, action, fired, confirmed in reversed(own[-limit:]):
            when = datetime.fromtimestamp(ts).strftime("%H:%M:%S")
            if "FAILED" in action or "ERROR" in action:
                cls = "red"
            elif fired and confirmed:
                cls = "green"
            elif fired:
                cls = "yellow"
            else:
                cls = ""
            cls_attr = f" class='{cls}'" if cls else ""
            marker = "*** " if fired else ""
            lines.append(f"<div class='action-line'><span class='dim'>{when}</span> {marker}<span{cls_attr}>{_esc(action)}</span></div>")
        return "<div class='own-actions'><div class='dim' style='margin-top:6px;'>Recent actions (this strategy):</div>" + "".join(lines) + "</div>"

    _STRATEGY_FIELD_LABELS = {
        "delta_tolerance_lots": "Delta tolerance (lots)",
        "high_gamma_threshold": "High-gamma threshold",
        "poll_interval_normal_sec": "Poll interval, normal mode (sec)",
        "poll_interval_high_gamma_sec": "Poll interval, high-gamma mode (sec)",
        "max_futures_position_lots": "Max futures position (lots)",
    }
    _ACCOUNT_FIELD_LABELS = {
        "max_hedge_trades_per_min": "Max hedge trades / minute",
        "circuit_breaker_pct": "Circuit breaker (%)",
        "circuit_breaker_window_sec": "Circuit breaker window (sec)",
        "max_consecutive_api_errors": "Max consecutive API errors",
    }

    def _render_settings_panel(self, views: list[StrategyView]) -> str:
        """Live-editable thresholds, hidden by default - toggled by the
        header's Settings button. Per-strategy fields are applied via
        SettingsStore -> main.py's loop (dataclasses.replace on that
        strategy's StrategyConfig); account-level fields mutate the live
        KillSwitch/HedgeRateLimiter directly. Either way, no restart needed
        - unlike every .env-driven change.
        """
        if self.settings_store is None:
            return ""

        blocks = []

        account_current = {
            "max_hedge_trades_per_min": self.rate_limiter.max_per_minute if self.rate_limiter else "",
            "circuit_breaker_pct": self.kill_switch.circuit_breaker_pct if self.kill_switch else "",
            "circuit_breaker_window_sec": self.kill_switch.circuit_breaker_window_sec if self.kill_switch else "",
            "max_consecutive_api_errors": self.kill_switch.max_consecutive_api_errors if self.kill_switch else "",
        }
        rows = []
        for field, label in self._ACCOUNT_FIELD_LABELS.items():
            rows.append(
                f"<div class='settings-row'><label>{_esc(label)}</label>"
                f"<input data-field='{_esc(field)}' value='{_esc(account_current[field])}'></div>"
            )
        blocks.append(
            "<div class='settings-block'>"
            "<div class='settings-block-title'>Account-level (shared across all strategies)</div>"
            + "".join(rows)
            + "<button class='save-btn' onclick='saveAccountSettings(this)'>Save</button>"
            "<span class='settings-msg'></span>"
            "</div>"
        )

        for v in views:
            strat_cfg = v.strat_cfg
            rows = []
            for field, label in self._STRATEGY_FIELD_LABELS.items():
                current = getattr(strat_cfg, field)
                rows.append(
                    f"<div class='settings-row'><label>{_esc(label)}</label>"
                    f"<input data-field='{_esc(field)}' value='{_esc(current)}'></div>"
                )
            blocks.append(
                f"<div class='settings-block' data-strategy='{_esc(strat_cfg.name)}'>"
                f"<div class='settings-block-title'>{_esc(strat_cfg.name)}</div>"
                + "".join(rows)
                + "<button class='save-btn' onclick='saveStrategySettings(this)'>Save</button>"
                "<span class='settings-msg'></span>"
                "</div>"
            )

        return (
            "<div id='settings-panel' class='actions' hidden>"
            "<div class='strategy-title-text'>Settings (live - applied without a restart)</div>"
            + "".join(blocks)
            + "</div>"
        )

    def _render_history_panel(self) -> str:
        """Full-session counts and chronological list, hidden by default -
        toggled by the header's History button. Not capped to the last 12
        the quick feed below shows; this is "how many times did X happen,"
        the whole session, for every strategy.
        """
        stats: dict[str, dict[str, int]] = {}
        for _ts, name, action, fired, confirmed in self._recent_actions:
            s = stats.setdefault(name, {"attempts": 0, "filled": 0, "pending": 0, "failed": 0})
            if "FAILED" in action or "ERROR" in action:
                s["failed"] += 1
            elif fired and confirmed:
                s["attempts"] += 1
                s["filled"] += 1
            elif fired:
                s["attempts"] += 1
                s["pending"] += 1

        summary_rows = []
        totals = {"attempts": 0, "filled": 0, "pending": 0, "failed": 0}
        for name, s in sorted(stats.items()):
            for k in totals:
                totals[k] += s[k]
            summary_rows.append(
                "<tr>"
                f"<td>{_esc(name)}</td><td>{s['attempts']}</td><td>{s['filled']}</td>"
                f"<td>{s['pending']}</td><td>{s['failed']}</td>"
                "</tr>"
            )
        summary_rows.append(
            "<tr class='dim'>"
            f"<td>Total</td><td>{totals['attempts']}</td><td>{totals['filled']}</td>"
            f"<td>{totals['pending']}</td><td>{totals['failed']}</td>"
            "</tr>"
        )
        summary_table = (
            "<table><thead><tr>"
            "<th>Strategy</th><th>Hedge attempts</th><th>Filled</th><th>Pending</th><th>Failed</th>"
            "</tr></thead><tbody>" + "".join(summary_rows) + "</tbody></table>"
        )

        if not self._recent_actions:
            full_list = "<div class='dim'>(no hedge actions yet this session)</div>"
        else:
            lines = []
            for ts, name, action, fired, confirmed in reversed(self._recent_actions):
                when = datetime.fromtimestamp(ts).strftime("%H:%M:%S")
                if "FAILED" in action or "ERROR" in action:
                    cls = "red"
                elif fired and confirmed:
                    cls = "green"
                elif fired:
                    cls = "yellow"
                else:
                    cls = ""
                cls_attr = f" class='{cls}'" if cls else ""
                marker = "*** " if fired else ""
                lines.append(f"<div class='action-line'><span class='dim'>{when} [{_esc(name)}]</span> {marker}<span{cls_attr}>{_esc(action)}</span></div>")
            full_list = "".join(lines)

        return (
            "<div id='history-panel' class='actions' hidden>"
            "<div class='strategy-title-text'>Hedge History (all strategies, full session)</div>"
            f"{summary_table}"
            "<div class='dim' style='margin-top:10px;'>Full chronological list:</div>"
            f"<div style='max-height:400px; overflow-y:auto; margin-top:4px;'>{full_list}</div>"
            "</div>"
        )

    def _render_actions(self) -> str:
        if not self._recent_actions and not self._reconcile_warnings:
            body = "<div class='dim'>(no hedge actions yet)</div>"
        else:
            lines = []
            for ts, name, action, fired, confirmed in reversed(self._recent_actions[-12:]):
                when = datetime.fromtimestamp(ts).strftime("%H:%M:%S")
                if "FAILED" in action or "ERROR" in action:
                    cls = "red"
                elif fired and confirmed:
                    cls = "green"
                elif fired:
                    cls = "yellow"
                else:
                    cls = ""
                marker = "*** " if fired else ""
                cls_attr = f" class='{cls}'" if cls else ""
                lines.append(f"<div class='action-line'><span class='dim'>{when} [{_esc(name)}]</span> {marker}<span{cls_attr}>{_esc(action)}</span></div>")
            for w in self._reconcile_warnings:
                lines.append(f"<div class='action-line'><span class='yellow'>RECONCILE</span> {_esc(w)}</div>")
            body = "".join(lines)
        return f"<div class='actions'><div class='strategy-title'>Recent Hedge Actions (all strategies)</div>{body}</div>"

    def _render_footer(self, views: list[StrategyView], tick_count: int) -> str:
        combined_pnl = sum(v.tick.total_pnl for v in views)
        pnl_class = "green" if combined_pnl >= 0 else "red"
        return (
            "<div class='footer'>"
            f"ticks={tick_count} &middot; combined total P&amp;L (all strategies) "
            f"<span class='{pnl_class}'>{combined_pnl:+,.2f}</span> &middot; log: {_esc(self.csv_path)}"
            "</div>"
        )
