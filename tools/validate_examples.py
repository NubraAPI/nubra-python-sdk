from __future__ import annotations

import ast
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_ROOT = REPO_ROOT / "examples"


def main() -> int:
    failures: list[tuple[Path, Exception]] = []

    for path in sorted(EXAMPLES_ROOT.rglob("*.py")):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except Exception as exc:  # pragma: no cover - direct script utility
            failures.append((path.relative_to(REPO_ROOT), exc))

    if failures:
        print("Validation failed for these example files:")
        for path, exc in failures:
            print(f"- {path.as_posix()}: {type(exc).__name__}: {exc}")
        return 1

    print(f"Validated {len(list(EXAMPLES_ROOT.rglob('*.py')))} example files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
