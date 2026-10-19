"""Environment selection and the kill switch.

Environment: UAT (sandbox) is the default. PROD is refused unless the caller
passes `allow_prod=True` (the `--allow-prod` flag in main.py). The environment is
chosen on the command line, never from `.env`.

Order placement is a separate switch: unless `--place-orders` is given, the
client only prints the orders it would send (see `nubra_client.NubraClient`).

KillSwitch: once halted it stays halted for the rest of the process. The only
way out is a restart, which forces a fresh look at what happened.
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field

logger = logging.getLogger("gamma_hedging.safety")


class UnsafeEnvironmentError(RuntimeError):
    """Raised when PROD is requested without the explicit --allow-prod flag."""


def resolve_env(env_name: str, allow_prod: bool):
    """Map "UAT"/"PROD" to a NubraEnv, refusing PROD unless explicitly allowed."""
    from nubra_python_sdk.start_sdk import NubraEnv

    name = env_name.strip().upper()
    if name == "UAT":
        return NubraEnv.UAT
    if name == "PROD":
        if not allow_prod:
            raise UnsafeEnvironmentError(
                "Refusing to use PROD without --allow-prod. Run on UAT (the default) first."
            )
        return NubraEnv.PROD
    raise UnsafeEnvironmentError(f"Unknown environment {env_name!r}; use UAT or PROD.")


@dataclass
class KillSwitch:
    """Tracks conditions that should stop further hedge orders: repeated API
    errors, or an abnormal spot move inside a short window."""

    max_consecutive_api_errors: int
    circuit_breaker_pct: float
    circuit_breaker_window_sec: float

    _halted: bool = False
    _reason: str = ""
    _consecutive_api_errors: int = 0
    # Keyed by underlying, not one shared series: strategies can be on
    # different underlyings, and mixing unrelated spot prices into one series
    # would look like a huge move. Each underlying is only compared with itself.
    _spot_history: dict = field(default_factory=lambda: defaultdict(lambda: deque(maxlen=10_000)))

    @property
    def halted(self) -> bool:
        return self._halted

    @property
    def reason(self) -> str:
        return self._reason

    def halt(self, reason: str) -> None:
        if self._halted:
            return
        self._halted = True
        self._reason = reason
        logger.critical("KILL SWITCH ENGAGED: %s", reason)

    def record_api_error(self, err: Exception) -> None:
        self._consecutive_api_errors += 1
        logger.warning(
            "API error (%d/%d consecutive): %s",
            self._consecutive_api_errors,
            self.max_consecutive_api_errors,
            err,
        )
        if self._consecutive_api_errors >= self.max_consecutive_api_errors:
            self.halt(
                f"{self._consecutive_api_errors} consecutive API errors "
                f"(threshold={self.max_consecutive_api_errors}). Last error: {err}"
            )

    def record_api_success(self) -> None:
        self._consecutive_api_errors = 0

    def record_spot(self, timestamp: float, spot: float, underlying: str) -> None:
        """Feed each observed spot price in for its own underlying; halts hedging
        for every strategy if that underlying moved more than
        `circuit_breaker_pct` percent within `circuit_breaker_window_sec`.
        """
        history = self._spot_history[underlying]
        history.append((timestamp, spot))
        cutoff = timestamp - self.circuit_breaker_window_sec
        while history and history[0][0] < cutoff:
            history.popleft()

        if len(history) < 2:
            return

        window_open = history[0][1]
        if window_open == 0:
            return
        pct_move = abs(spot - window_open) / window_open * 100.0
        if pct_move >= self.circuit_breaker_pct:
            self.halt(
                f"{underlying} spot moved {pct_move:.2f}% within {self.circuit_breaker_window_sec:.0f}s "
                f"(from {window_open:.2f} to {spot:.2f}), threshold={self.circuit_breaker_pct:.2f}%. "
                f"Not hedging into an abnormal move unattended."
            )

    def snapshot(self) -> dict:
        return {
            "halted": self._halted,
            "reason": self._reason,
            "consecutive_api_errors": self._consecutive_api_errors,
        }
