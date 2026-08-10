"""API executable entrypoint."""

from __future__ import annotations

import uvicorn

from domcek_bot.config import ProcessKind, load_settings
from domcek_bot.infrastructure.api_factory import create_runtime_app


def run() -> None:
    settings = load_settings(ProcessKind.API)
    uvicorn.run(
        create_runtime_app(),
        host=settings.api_host,
        port=settings.api_port,
        log_config=None,
    )


if __name__ == "__main__":
    run()
