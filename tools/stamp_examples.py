"""Add or refresh a 'Tested with:' line in every example's docstring.

    py -3.12 tools/stamp_examples.py
"""
import re
from pathlib import Path

TESTED_SDK_VERSION = re.search(
    r'TESTED_SDK_VERSION = "([^"]+)"', (Path(__file__).parent / "check_sdk_version.py").read_text(encoding="utf-8")
).group(1)

STAMP = f"Tested with: nubra-sdk {TESTED_SDK_VERSION} (UAT)"
changed = 0
for path in sorted((Path(__file__).resolve().parents[1] / "examples").rglob("*.py")):
    text = path.read_text(encoding="utf-8")
    m = re.match(r'(\s*)("""|\'\'\')(.*?)(\2)', text, re.S)
    if not m:
        continue
    body = re.sub(r"\n?Tested with: nubra-sdk [^\n]*", "", m.group(3)).rstrip()
    new = text[:m.start(3)] + body + "\n" + STAMP + "\n" + text[m.end(3):]
    if new != text:
        path.write_text(new, encoding="utf-8")
        changed += 1
print(f"Stamped {changed} files with: {STAMP}")
