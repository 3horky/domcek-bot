"""Validate Carlo staging/production env files without printing secrets."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from urllib.parse import unquote, urlparse

IMAGE_DIGEST = re.compile(r"^\S+@sha256:[0-9a-f]{64}$")
DISCORD_IDS = (
    "DISCORD_APPLICATION_ID",
    "DISCORD_GUILD_ID",
    "DISCORD_ADMIN_ROLE_ID",
    "DISCORD_TEAM_MOD_ROLE_ID",
    "DISCORD_PUBLISHER_ROLE_ID",
    "DISCORD_COMMAND_CHANNEL_ID",
    "DISCORD_ANNOUNCEMENT_CHANNEL_ID",
    "DISCORD_MODERATOR_CHANNEL_ID",
    "DISCORD_PROJECTS_CATEGORY_ID",
    "DISCORD_ARCHIVE_CATEGORY_ID",
    "DISCORD_OAUTH_CLIENT_ID",
)
SECRET_FILES = (
    "bot-token",
    "oauth-client-secret",
    "google-service-account.json",
    "session-secret",
)
EXPECTED_CONTAINER_FILES = {
    "SESSION_SECRET_FILE": "/run/project-secrets/session-secret",
    "DISCORD_BOT_TOKEN_FILE": "/run/project-secrets/bot-token",
    "DISCORD_OAUTH_CLIENT_SECRET_FILE": "/run/project-secrets/oauth-client-secret",
    "GOOGLE_SERVICE_ACCOUNT_FILE": "/run/project-secrets/google-service-account.json",
    "BOT_THOUGHTS_FILE": "/run/project-assets/thoughts.txt",
}


def validate_env_file_permissions(paths: tuple[pathlib.Path, ...]) -> list[str]:
    errors: list[str] = []
    for path in paths:
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"konfiguračný env súbor chýba alebo je prázdny: {path}")
        elif path.stat().st_mode & 0o077:
            errors.append(
                f"konfiguračný env súbor {path} musí byť prístupný iba vlastníkovi"
            )
    return errors


def read_env(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text().splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"{path}:{line_number}: neplatný riadok")
        key, value = line.split("=", 1)
        key = key.strip()
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            raise ValueError(f"{path}:{line_number}: neplatný názov premennej")
        if key in values:
            raise ValueError(f"{path}:{line_number}: duplicitná premenná {key}")
        values[key] = value.strip()
    return values


def validate(
    app: dict[str, str],
    deploy: dict[str, str],
    *,
    allow_live: bool,
    check_files: bool,
    expected_environment: str = "production",
    allow_staging_manual_publication: bool = False,
) -> list[str]:
    errors: list[str] = []

    def require(values: dict[str, str], key: str) -> str:
        value = values.get(key, "")
        if not value:
            errors.append(f"chýba {key}")
        return value

    if expected_environment not in {"staging", "production"}:
        raise ValueError("expected_environment must be staging or production")
    if allow_live and expected_environment != "production":
        raise ValueError("allow_live is valid only for production")
    if allow_staging_manual_publication and expected_environment != "staging":
        raise ValueError("allow_staging_manual_publication is valid only for staging")

    if require(app, "APP_ENV") != expected_environment:
        errors.append(f"APP_ENV musí byť {expected_environment}")
    version = require(app, "APP_VERSION")
    if "replace" in version.lower():
        errors.append("APP_VERSION musí byť konkrétny release identifikátor")

    password = require(app, "POSTGRES_PASSWORD")
    if len(password) < 24 or "replace" in password.lower():
        errors.append("POSTGRES_PASSWORD musí byť náhodná hodnota s aspoň 24 znakmi")
    database_url = urlparse(require(app, "DATABASE_URL"))
    if (
        database_url.scheme != "postgresql+asyncpg"
        or database_url.hostname != "db"
        or database_url.username != require(app, "POSTGRES_USER")
        or unquote(database_url.password or "") != password
        or database_url.path != f"/{require(app, 'POSTGRES_DB')}"
    ):
        errors.append(
            "DATABASE_URL musí smerovať na db a zhodovať sa s PostgreSQL menom, "
            "heslom a databázou (heslo v URL percent-enkódovať)"
        )

    host = require(deploy, "CARLO_PUBLIC_HOST")
    if not host or host == "carlo.example.sk" or "://" in host or "/" in host:
        errors.append("CARLO_PUBLIC_HOST musí byť konkrétny hostname bez schémy/cesty")
    for key in ("ALLOWED_ORIGINS", "FRONTEND_BASE_URL", "PUBLIC_MEDIA_BASE_URL"):
        parsed = urlparse(require(app, key))
        if parsed.scheme != "https" or parsed.hostname != host:
            errors.append(f"{key} musí byť HTTPS URL na CARLO_PUBLIC_HOST")
    expected_callback = f"https://{host}/api/v1/auth/discord/callback"
    if require(app, "DISCORD_OAUTH_REDIRECT_URI") != expected_callback:
        errors.append("DISCORD_OAUTH_REDIRECT_URI sa nezhoduje s verejným callbackom")

    for key in DISCORD_IDS:
        value = require(app, key)
        if not value.isdecimal() or int(value or 0) <= 0:
            errors.append(f"{key} musí byť kladné Discord ID")

    mode = require(app, "PUBLICATION_EXECUTION_MODE")
    allowed_modes = {"paused", "shadow", "live"}
    if mode not in allowed_modes:
        errors.append("PUBLICATION_EXECUTION_MODE má neplatnú hodnotu")
    elif expected_environment == "staging" and mode != "shadow":
        errors.append("staging preflight vyžaduje PUBLICATION_EXECUTION_MODE=shadow")
    elif expected_environment == "production":
        if allow_live and mode != "live":
            errors.append("--allow-live vyžaduje PUBLICATION_EXECUTION_MODE=live")
        elif not allow_live and mode == "live":
            errors.append(
                "live režim vyžaduje explicitné --allow-live až pri cutover kroku 16"
            )
        elif not allow_live and mode != "paused":
            errors.append(
                "produkčný preflight pred cutoverom vyžaduje "
                "PUBLICATION_EXECUTION_MODE=paused"
            )

    manual_shadow = app.get("ALLOW_MANUAL_PUBLICATION_IN_SHADOW")
    if expected_environment == "production" and manual_shadow != "false":
        errors.append("ALLOW_MANUAL_PUBLICATION_IN_SHADOW musí byť v produkcii false")
    elif expected_environment == "staging":
        expected_manual = "true" if allow_staging_manual_publication else "false"
        if manual_shadow != expected_manual:
            flag = (
                " s --allow-staging-manual-publication"
                if expected_manual == "true"
                else ""
            )
            errors.append(
                "ALLOW_MANUAL_PUBLICATION_IN_SHADOW musí byť v stagingu"
                f"{flag} {expected_manual}"
            )
    if app.get("DISCORD_SYNC_GUILD_COMMANDS") != "false":
        errors.append("DISCORD_SYNC_GUILD_COMMANDS musí byť pri bežnom štarte false")

    for key in (
        "CARLO_BACKEND_IMAGE",
        "CARLO_FRONTEND_IMAGE",
        "CARLO_POSTGRES_IMAGE",
        "CARLO_CADDY_IMAGE",
    ):
        if not IMAGE_DIGEST.fullmatch(require(deploy, key)):
            errors.append(f"{key} musí obsahovať nemenný @sha256 digest")

    expected_env_file = f".env.{expected_environment}"
    if require(deploy, "CARLO_ENV_FILE") != expected_env_file:
        errors.append(f"CARLO_ENV_FILE musí byť presne {expected_env_file}")

    secrets_dir_value = require(deploy, "CARLO_SECRETS_DIR")
    thoughts_value = require(deploy, "CARLO_THOUGHTS_FILE")
    secrets_dir = pathlib.Path(secrets_dir_value)
    thoughts_file = pathlib.Path(thoughts_value)
    if not secrets_dir.is_absolute():
        errors.append("CARLO_SECRETS_DIR musí byť absolútna cesta")
    if not thoughts_file.is_absolute():
        errors.append("CARLO_THOUGHTS_FILE musí byť absolútna cesta")
    for key, expected in EXPECTED_CONTAINER_FILES.items():
        if require(app, key) != expected:
            errors.append(f"{key} musí smerovať presne na read-only mount {expected}")
    if check_files:
        if not secrets_dir.is_dir():
            errors.append(f"chýba secret adresár {secrets_dir}")
        elif secrets_dir.stat().st_mode & 0o077:
            errors.append(
                f"secret adresár {secrets_dir} musí byť prístupný iba vlastníkovi"
            )
        for name in SECRET_FILES:
            path = secrets_dir / name
            if not path.is_file() or path.stat().st_size == 0:
                errors.append(f"chýba neprázdny secret súbor {path}")
            elif path.stat().st_mode & 0o077:
                errors.append(f"secret súbor {path} musí byť prístupný iba vlastníkovi")
        if not thoughts_file.is_file() or thoughts_file.stat().st_size == 0:
            errors.append(f"chýba neprázdny thoughts súbor {thoughts_file}")
        session_file = secrets_dir / "session-secret"
        if session_file.is_file() and len(session_file.read_bytes().strip()) < 32:
            errors.append("session-secret musí mať aspoň 32 bajtov")
        google_file = secrets_dir / "google-service-account.json"
        if google_file.is_file() and google_file.stat().st_size:
            try:
                google = json.loads(google_file.read_text())
            except (UnicodeDecodeError, json.JSONDecodeError):
                errors.append("google-service-account.json nie je platný JSON")
            else:
                if not isinstance(google, dict) or not all(
                    isinstance(google.get(key), str) and google[key].strip()
                    for key in ("client_email", "private_key")
                ):
                    errors.append(
                        "google-service-account.json nemá client_email a private_key"
                    )

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-env", type=pathlib.Path, required=True)
    parser.add_argument("--deploy-env", type=pathlib.Path, required=True)
    parser.add_argument("--allow-live", action="store_true")
    parser.add_argument("--staging", action="store_true")
    parser.add_argument("--allow-staging-manual-publication", action="store_true")
    parser.add_argument("--check-files", action="store_true")
    args = parser.parse_args()
    if args.allow_live and args.staging:
        parser.error("--allow-live nemožno použiť s --staging")
    if args.allow_staging_manual_publication and not args.staging:
        parser.error("--allow-staging-manual-publication vyžaduje --staging")
    try:
        app_values = read_env(args.app_env)
        deploy_values = read_env(args.deploy_env)
        errors = validate(
            app_values,
            deploy_values,
            allow_live=args.allow_live,
            check_files=args.check_files,
            expected_environment="staging" if args.staging else "production",
            allow_staging_manual_publication=args.allow_staging_manual_publication,
        )
        if args.check_files:
            errors.extend(
                validate_env_file_permissions((args.app_env, args.deploy_env))
            )
    except (OSError, ValueError) as exc:
        print(f"Konfiguráciu nemožno načítať: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    if errors:
        environment = "Staging" if args.staging else "Produkčná"
        print(f"{environment} konfigurácia nie je pripravená:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        raise SystemExit(1)
    environment = "Staging" if args.staging else "Produkčná"
    print(f"{environment} konfigurácia prešla bezpečnostnou kontrolou.")


if __name__ == "__main__":
    main()
