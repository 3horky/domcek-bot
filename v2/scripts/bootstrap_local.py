#!/usr/bin/env python3
"""Create ignored local configuration without exposing existing credentials."""

from __future__ import annotations

import os
import secrets
import shutil
from pathlib import Path


V2_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = V2_ROOT.parent
ENV_EXAMPLE = V2_ROOT / ".env.example"
ENV_FILE = V2_ROOT / ".env"
LOCAL_SECRETS = V2_ROOT / ".local-secrets"
SESSION_SECRET = LOCAL_SECRETS / "session-secret"
REQUIRED_PROJECT_SECRETS = (
    REPOSITORY_ROOT / "secrets" / "bot-token",
    REPOSITORY_ROOT / "secrets" / "animatori-504814-9c7b8298f7f4.json",
)


def ensure_private_file(path: Path) -> None:
    path.chmod(0o600)


def main() -> int:
    missing = [path for path in REQUIRED_PROJECT_SECRETS if not path.is_file()]
    if missing:
        relative = ", ".join(str(path.relative_to(REPOSITORY_ROOT)) for path in missing)
        raise SystemExit(f"Chýbajú lokálne credentials: {relative}")

    LOCAL_SECRETS.mkdir(mode=0o700, parents=True, exist_ok=True)
    LOCAL_SECRETS.chmod(0o700)
    if not SESSION_SECRET.exists():
        SESSION_SECRET.write_text(secrets.token_urlsafe(48), encoding="utf-8")
    ensure_private_file(SESSION_SECRET)

    if not ENV_FILE.exists():
        shutil.copyfile(ENV_EXAMPLE, ENV_FILE)
    ensure_private_file(ENV_FILE)

    for path in REQUIRED_PROJECT_SECRETS:
        ensure_private_file(path)

    print("Lokálna E1 konfigurácia je pripravená; hodnoty tajomstiev neboli vypísané.")
    return os.EX_OK


if __name__ == "__main__":
    raise SystemExit(main())
