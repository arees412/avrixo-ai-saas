"""Small deterministic guard, not a substitute for a full secret scanner."""

import re
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
paths = (
    subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
)
patterns = [
    r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}",
    r"gh[pousr]_[A-Za-z0-9]{20,}",
    r"AKIA[0-9A-Z]{16}",
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
]
failures = []
for name in filter(None, paths):
    path = root / name
    if path.name.startswith(".env") and not path.name.endswith(".example"):
        failures.append(f"{name}: tracked environment file")
    if path.is_file() and path.stat().st_size < 2000000:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if any(re.search(pattern, text) for pattern in patterns):
            failures.append(f"{name}: possible secret pattern (value suppressed)")
if failures:
    raise SystemExit("\n".join(failures))
print("Tracked-file environment and secret-pattern checks passed.")
