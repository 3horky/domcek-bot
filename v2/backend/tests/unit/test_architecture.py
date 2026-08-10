from __future__ import annotations

import ast
from pathlib import Path


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)
    return modules


def test_api_and_application_do_not_import_orm_or_postgresql_adapters() -> None:
    source_root = Path(__file__).parents[2] / "src" / "domcek_bot"
    forbidden = {
        "domcek_bot.infrastructure.models",
        "domcek_bot.infrastructure.repositories",
        "domcek_bot.infrastructure.unit_of_work",
    }

    violations: list[str] = []
    for layer in ("api", "application"):
        for path in (source_root / layer).rglob("*.py"):
            imported = _imported_modules(path)
            for module in sorted(imported & forbidden):
                violations.append(f"{path.relative_to(source_root)} imports {module}")

    assert violations == []
