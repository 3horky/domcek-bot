#!/usr/bin/env python3
"""Fail when repository candidates contain common credential artifacts."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_NAMES = {
    "bot-token",
    "oauth-client-secret",
    "service-account.json",
    "google-calendar-staging.json",
}
PRIVATE_KEY_MARKER = "-----BEGIN " + "PRIVATE KEY-----"


def candidate_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [ROOT / item.decode() for item in result.stdout.split(b"\0") if item]


def has_service_account_secret(text: str) -> bool:
    try:
        value = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return False
    return isinstance(value, dict) and value.get("type") == "service_account" and bool(
        value.get("private_key")
    )


def main() -> int:
    findings: list[str] = []
    for path in candidate_files():
        relative = path.relative_to(ROOT)
        if path.name in FORBIDDEN_NAMES or "secrets" in relative.parts:
            findings.append(f"zakázaná cesta: {relative}")
            continue
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if PRIVATE_KEY_MARKER in text or has_service_account_secret(text):
            findings.append(f"credential obsah: {relative}")

    if findings:
        print("Kontrola tajomstiev zlyhala:")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("Kontrola tajomstiev prešla.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
