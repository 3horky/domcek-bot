import json
from pathlib import Path

from scripts.validate_production_config import validate, validate_env_file_permissions


def _app() -> dict[str, str]:
    password = "a-very-long-production-password"
    values = {
        "APP_ENV": "production",
        "APP_VERSION": "2026.08.10-1",
        "POSTGRES_USER": "carlo",
        "POSTGRES_DB": "carlo",
        "POSTGRES_PASSWORD": password,
        "DATABASE_URL": f"postgresql+asyncpg://carlo:{password}@db:5432/carlo",
        "ALLOWED_ORIGINS": "https://carlo.domcek.example",
        "FRONTEND_BASE_URL": "https://carlo.domcek.example",
        "PUBLIC_MEDIA_BASE_URL": "https://carlo.domcek.example",
        "DISCORD_OAUTH_REDIRECT_URI": (
            "https://carlo.domcek.example/api/v1/auth/discord/callback"
        ),
        "PUBLICATION_EXECUTION_MODE": "paused",
        "ALLOW_MANUAL_PUBLICATION_IN_SHADOW": "false",
        "DISCORD_SYNC_GUILD_COMMANDS": "false",
        "SESSION_SECRET_FILE": "/run/project-secrets/session-secret",
        "DISCORD_BOT_TOKEN_FILE": "/run/project-secrets/bot-token",
        "DISCORD_OAUTH_CLIENT_SECRET_FILE": "/run/project-secrets/oauth-client-secret",
        "GOOGLE_SERVICE_ACCOUNT_FILE": "/run/project-secrets/google-service-account.json",
        "BOT_THOUGHTS_FILE": "/run/project-assets/thoughts.txt",
    }
    values.update({key: "123456789" for key in _discord_ids()})
    return values


def _deploy() -> dict[str, str]:
    digest = "a" * 64
    return {
        "CARLO_PUBLIC_HOST": "carlo.domcek.example",
        "CARLO_BACKEND_IMAGE": f"registry.example/backend@sha256:{digest}",
        "CARLO_FRONTEND_IMAGE": f"registry.example/frontend@sha256:{digest}",
        "CARLO_POSTGRES_IMAGE": f"postgres@sha256:{digest}",
        "CARLO_CADDY_IMAGE": f"caddy@sha256:{digest}",
        "CARLO_ENV_FILE": ".env.production",
        "CARLO_SECRETS_DIR": "/srv/carlo/secrets",
        "CARLO_THOUGHTS_FILE": "/srv/carlo/thoughts.txt",
    }


def _discord_ids() -> tuple[str, ...]:
    return (
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


def test_valid_paused_production_configuration() -> None:
    assert validate(_app(), _deploy(), allow_live=False, check_files=False) == []


def test_live_mode_requires_explicit_cutover_flag() -> None:
    app = _app()
    app["PUBLICATION_EXECUTION_MODE"] = "live"
    errors = validate(app, _deploy(), allow_live=False, check_files=False)
    assert errors == [
        "live režim vyžaduje explicitné --allow-live až pri cutover kroku 16"
    ]
    assert validate(app, _deploy(), allow_live=True, check_files=False) == []


def test_preflight_phase_rejects_shadow_and_allow_live_requires_live() -> None:
    app = _app()
    app["PUBLICATION_EXECUTION_MODE"] = "shadow"
    assert validate(app, _deploy(), allow_live=False, check_files=False) == [
        "produkčný preflight pred cutoverom vyžaduje PUBLICATION_EXECUTION_MODE=paused"
    ]

    app["PUBLICATION_EXECUTION_MODE"] = "paused"
    assert validate(app, _deploy(), allow_live=True, check_files=False) == [
        "--allow-live vyžaduje PUBLICATION_EXECUTION_MODE=live"
    ]


def test_manual_shadow_publication_is_never_valid_in_production() -> None:
    app = _app()
    app["ALLOW_MANUAL_PUBLICATION_IN_SHADOW"] = "true"
    assert validate(app, _deploy(), allow_live=False, check_files=False) == [
        "ALLOW_MANUAL_PUBLICATION_IN_SHADOW musí byť v produkcii false"
    ]


def test_staging_requires_shadow_and_disables_manual_publication_by_default() -> None:
    app = _app()
    app["APP_ENV"] = "staging"
    app["PUBLICATION_EXECUTION_MODE"] = "shadow"
    deploy = _deploy()
    deploy["CARLO_ENV_FILE"] = ".env.staging"
    assert (
        validate(
            app,
            deploy,
            allow_live=False,
            check_files=False,
            expected_environment="staging",
        )
        == []
    )

    app["PUBLICATION_EXECUTION_MODE"] = "paused"
    errors = validate(
        app,
        deploy,
        allow_live=False,
        check_files=False,
        expected_environment="staging",
    )
    assert errors == ["staging preflight vyžaduje PUBLICATION_EXECUTION_MODE=shadow"]


def test_staging_manual_publication_requires_explicit_preflight_flag() -> None:
    app = _app()
    app["APP_ENV"] = "staging"
    app["PUBLICATION_EXECUTION_MODE"] = "shadow"
    app["ALLOW_MANUAL_PUBLICATION_IN_SHADOW"] = "true"
    deploy = _deploy()
    deploy["CARLO_ENV_FILE"] = ".env.staging"
    errors = validate(
        app,
        deploy,
        allow_live=False,
        check_files=False,
        expected_environment="staging",
    )
    assert errors == ["ALLOW_MANUAL_PUBLICATION_IN_SHADOW musí byť v stagingu false"]
    assert (
        validate(
            app,
            deploy,
            allow_live=False,
            check_files=False,
            expected_environment="staging",
            allow_staging_manual_publication=True,
        )
        == []
    )


def test_environment_specific_env_file_is_required() -> None:
    deploy = _deploy()
    deploy["CARLO_ENV_FILE"] = ".env.staging"
    errors = validate(_app(), deploy, allow_live=False, check_files=False)
    assert errors == ["CARLO_ENV_FILE musí byť presne .env.production"]


def test_mismatched_database_url_and_mutable_image_are_rejected() -> None:
    app = _app()
    app["DATABASE_URL"] = "postgresql+asyncpg://carlo:wrong@db:5432/carlo"
    deploy = _deploy()
    deploy["CARLO_BACKEND_IMAGE"] = "registry.example/backend:latest"
    errors = validate(app, deploy, allow_live=False, check_files=False)
    assert any(error.startswith("DATABASE_URL") for error in errors)
    assert any(error.startswith("CARLO_BACKEND_IMAGE") for error in errors)


def test_secret_mount_paths_are_exact() -> None:
    app = _app()
    app["SESSION_SECRET_FILE"] = "/tmp/session-secret"
    errors = validate(app, _deploy(), allow_live=False, check_files=False)
    assert any(
        error.startswith("SESSION_SECRET_FILE musí smerovať") for error in errors
    )


def test_secret_permissions_length_and_google_json_are_validated(
    tmp_path: Path,
) -> None:
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    secrets.chmod(0o700)
    files = {
        "bot-token": b"bot-token-value",
        "oauth-client-secret": b"oauth-value",
        "google-service-account.json": json.dumps(
            {"client_email": "carlo@example.test", "private_key": "private"}
        ).encode(),
        "session-secret": b"s" * 32,
    }
    for name, content in files.items():
        path = secrets / name
        path.write_bytes(content)
        path.chmod(0o600)
    thoughts = tmp_path / "thoughts.txt"
    thoughts.write_text("Ahojte")
    deploy = _deploy()
    deploy["CARLO_SECRETS_DIR"] = str(secrets)
    deploy["CARLO_THOUGHTS_FILE"] = str(thoughts)
    assert validate(_app(), deploy, allow_live=False, check_files=True) == []

    (secrets / "session-secret").write_text("short")
    (secrets / "bot-token").chmod(0o640)
    (secrets / "google-service-account.json").write_text("not-json")
    errors = validate(_app(), deploy, allow_live=False, check_files=True)
    assert any("iba vlastníkovi" in error for error in errors)
    assert "session-secret musí mať aspoň 32 bajtov" in errors
    assert "google-service-account.json nie je platný JSON" in errors


def test_env_files_and_secret_directory_must_be_owner_only(tmp_path: Path) -> None:
    app_env = tmp_path / ".env.production"
    deploy_env = tmp_path / ".env.deploy"
    app_env.write_text("APP_ENV=production\n")
    deploy_env.write_text("CARLO_PUBLIC_HOST=carlo.example.test\n")
    app_env.chmod(0o600)
    deploy_env.chmod(0o600)
    assert validate_env_file_permissions((app_env, deploy_env)) == []

    app_env.chmod(0o640)
    errors = validate_env_file_permissions((app_env, deploy_env))
    assert errors == [
        f"konfiguračný env súbor {app_env} musí byť prístupný iba vlastníkovi"
    ]

    secrets = tmp_path / "open-secrets"
    secrets.mkdir(mode=0o755)
    deploy = _deploy()
    deploy["CARLO_SECRETS_DIR"] = str(secrets)
    errors = validate(_app(), deploy, allow_live=False, check_files=True)
    assert any(
        "secret adresár" in error and "iba vlastníkovi" in error for error in errors
    )
