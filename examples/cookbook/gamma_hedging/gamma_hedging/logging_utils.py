"""Per-session logging.

Each run writes two files under `LOG_DIR`, named with the same session timestamp:
  - `session_<ts>_ticks.csv`   one row per (tick, strategy): timestamp, strategy,
                                spot, net delta/gamma, mode, hedge action, futures
                                position and P&L estimate.
  - `session_<ts>_events.log`  human-readable log: startup, every order request
                                (or dry-run order), mode switches, warnings,
                                kill-switch triggers, errors.
"""

from __future__ import annotations

import csv
import logging
import os
from datetime import datetime

from .config import Config
from .hedger import TickResult

CSV_FIELDS = [
    "timestamp_iso",
    "epoch",
    "strategy",
    "spot",
    "net_delta",
    "net_gamma",
    "mode",
    "hedge_action",
    "hedge_fired",
    "hedge_confirmed",
    "hedge_dry_run",
    "futures_lots",
    "options_pnl",
    "futures_pnl",
    "total_pnl",
    "halted",
    "error",
]


def new_session_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def configure_logging(cfg: Config, session_id: str, console: bool) -> str:
    os.makedirs(cfg.log_dir, exist_ok=True)
    events_path = os.path.join(cfg.log_dir, f"session_{session_id}_events.log")

    root = logging.getLogger("gamma_hedging")
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    file_handler = logging.FileHandler(events_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s"))
    root.addHandler(file_handler)

    if console:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(logging.Formatter("%(levelname)-8s %(name)s: %(message)s"))
        root.addHandler(stream_handler)

    return events_path


class SessionLogger:
    def __init__(self, cfg: Config, session_id: str):
        os.makedirs(cfg.log_dir, exist_ok=True)
        self.csv_path = os.path.join(cfg.log_dir, f"session_{session_id}_ticks.csv")
        self._file = open(self.csv_path, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=CSV_FIELDS)
        self._writer.writeheader()
        self._file.flush()

    def log_tick(self, tick: TickResult) -> None:
        self._writer.writerow(
            {
                "timestamp_iso": datetime.fromtimestamp(tick.timestamp).isoformat(timespec="seconds"),
                "epoch": f"{tick.timestamp:.3f}",
                "strategy": tick.strategy_name,
                "spot": f"{tick.spot:.2f}" if tick.spot is not None else "",
                "net_delta": f"{tick.net_delta:.4f}" if tick.net_delta is not None else "",
                "net_gamma": f"{tick.net_gamma:.6f}" if tick.net_gamma is not None else "",
                "mode": tick.mode,
                "hedge_action": tick.hedge_action or "",
                "hedge_fired": tick.hedge_fired,
                "hedge_confirmed": tick.hedge_confirmed,
                "hedge_dry_run": tick.hedge_dry_run,
                "futures_lots": tick.futures_lots,
                "options_pnl": f"{tick.options_pnl:.2f}",
                "futures_pnl": f"{tick.futures_pnl:.2f}",
                "total_pnl": f"{tick.total_pnl:.2f}",
                "halted": tick.halted,
                "error": tick.error,
            }
        )
        self._file.flush()

    def close(self) -> None:
        self._file.close()
