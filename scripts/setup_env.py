"""Create a local configuration without overwriting an existing environment."""

import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
content = (root / ".env.example").read_text(encoding="utf-8")
for placeholder in (
    "REPLACE_WITH_RANDOM_SECRET",
    "REPLACE_WITH_RANDOM_PASSWORD",
    "REPLACE_WITH_RANDOM_DATABASE_PASSWORD",
):
    content = content.replace(placeholder, secrets.token_urlsafe(32))
with (root / ".env").open("x", encoding="utf-8", newline="\n") as target:
    target.write(content)
print("Created .env with random local credentials. Review it before starting services.")
