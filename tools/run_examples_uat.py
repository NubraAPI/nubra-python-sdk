"""Run every example against the real UAT environment and report pass/fail.

Run from the repo root after `py -3.12 tools/uat_login.py` (reuses the saved session):

    py -3.12 tools/run_examples_uat.py [substring-filter ...]

Safety: examples whose active code references NubraEnv.PROD are skipped, and
examples that need interactive input or change account security (OTP, TOTP,
institutional login) are skipped. stdin is closed so nothing can hang on a prompt.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EXAMPLES = REPO / "examples"
REPORT = REPO / "uat_report.json"
OUT_DIR = REPO / "uat_outputs"
TIMEOUT = 150

INTERACTIVE = ("logout_and_relogin", "otp_login", "institutional_login", "step_1_", "step_2_", "step_3_", "step_4_")
ERROR_MARKERS = ("Traceback (most recent call last)", "[error]", "Connection failed", "NubraValidationError", "Exception in auth_flow")


def redact(text: str) -> str:
    """Hide anything token-like before it is written to disk."""
    return re.sub(r"[A-Za-z0-9._-]{60,}", "<redacted>", text)


def active_code(text: str) -> str:
    return "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#"))


def classify(path: Path) -> str | None:
    """Return a skip reason, or None if the file is safe to run on UAT."""
    code = active_code(path.read_text(encoding="utf-8"))
    if any(k in path.name for k in INTERACTIVE):
        return "interactive/account-security flow"
    if "NubraEnv.PROD" in code:
        return "uses PROD"
    if "NubraEnv.UAT" not in code and "InitNubraSdk" in code:
        return "environment not UAT"
    return None


SNAP = REPO / ".uat_session_snapshot"


def session_files() -> list[Path]:
    return sorted(REPO.glob("auth_data.db*"))


def snapshot_session() -> None:
    """Copy the saved login so examples (which log in from scratch) cannot lose it."""
    shutil.rmtree(SNAP, ignore_errors=True)
    SNAP.mkdir()
    for f in session_files():
        shutil.copy2(f, SNAP / f.name)


def restore_session() -> None:
    for f in session_files():
        f.unlink()
    for f in SNAP.iterdir():
        shutil.copy2(f, REPO / f.name)


def main() -> int:
    filters = sys.argv[1:]
    files = [p for p in sorted(EXAMPLES.rglob("*.py")) if not filters or any(f in p.as_posix() for f in filters)]
    if not session_files():
        print("No saved session. Run tools/uat_login.py first.")
        return 2
    snapshot_session()
    OUT_DIR.mkdir(exist_ok=True)
    results = []
    for p in files:
        rel = p.relative_to(REPO).as_posix()
        skip = classify(p)
        if skip:
            results.append({"file": rel, "status": "SKIP", "detail": skip})
            print(f"SKIP  {rel}  ({skip})")
            continue
        restore_session()
        t0 = time.time()
        try:
            r = subprocess.run([sys.executable, str(p)], cwd=REPO, stdin=subprocess.DEVNULL,
                               capture_output=True, text=True, timeout=TIMEOUT, encoding="utf-8", errors="replace",
                               env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            out = (r.stdout or "") + (r.stderr or "")
            (OUT_DIR / (rel.replace("/", "__") + ".txt")).write_text(redact(out), encoding="utf-8")
            if "440 Client Error" in out or "triggering re-login" in out:
                results.append({"file": rel, "status": "EXPIRED", "detail": "UAT session expired - log in again"})
                print(f"EXPIRED  {rel}: UAT session expired. Re-run tools/uat_login.py, then this script. Stopping.")
                break
            bad = r.returncode != 0 or any(m in out for m in ERROR_MARKERS)
            status = "FAIL" if bad else "PASS"
            detail = redact(out[-1500:] if bad else out[:300])
        except subprocess.TimeoutExpired as e:
            status, detail = "FAIL", f"timeout after {TIMEOUT}s"
        restore_session()
        dt = time.time() - t0
        results.append({"file": rel, "status": status, "secs": round(dt, 1), "detail": detail})
        print(f"{status}  {rel}  ({dt:.1f}s)")
    restore_session()
    REPORT.write_text(json.dumps(results, indent=1), encoding="utf-8")
    c = {s: sum(r["status"] == s for r in results) for s in ("PASS", "FAIL", "SKIP", "EXPIRED")}
    print(f"\n{c}  -> {REPORT.name}")
    return 1 if c["FAIL"] or c["EXPIRED"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
