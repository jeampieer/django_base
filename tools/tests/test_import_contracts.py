import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]


def write_module(root: Path, module: str, source: str = "") -> None:
    parts = module.split(".")
    current = root
    for part in parts[:-1]:
        current /= part
        current.mkdir(exist_ok=True)
        (current / "__init__.py").touch()
    (current / f"{parts[-1]}.py").write_text(source, encoding="utf-8")


@pytest.mark.parametrize("importer,imported,kept", [
    ("applications.first.services.use", "applications.second.services.use", True),
    ("applications.first.services.use", "applications.second.public", True),
    ("applications.first.services.use", "applications.second.models", False),
    ("applications.first.services.use", "applications.second.serializers", False),
    ("applications.first.models", "applications.first.services.use", False),
    ("applications.first.services.use", "applications.first.api_views.entry", False),
    ("applications.first.selectors.read", "applications.first.services.use", False),
    ("applications.first.models", "applications.second.services.use", False),
    ("applications.first.public", "applications.first.models", False),
    ("core.helper", "applications.second.services.use", False),
    ("applications.first.services.use", "applications.users.models", False),
    ("applications.first.services.use", "applications.users.selectors.user", False),
    ("applications.first.services.use", "applications.users.permissions.rules", False),
    ("applications.first.services.use", "applications.users.services.create_user", True),
    ("applications.first.admin", "applications.first.services.use", True),
    ("applications.first.admin", "applications.first.forms", True),
    ("applications.first.backends", "applications.first.services.use", True),
    ("applications.first.services.use", "applications.first.admin", False),
    ("applications.first.models", "applications.first.forms", False),
    ("applications.first.admin", "applications.users.models", False),
    ("applications.first.forms", "applications.first.services.use", False),
    ("applications.first.services.use", "applications.first.forms", False),
])
def test_real_configuration_rejects_violations(tmp_path: Path, importer: str, imported: str, kept: bool) -> None:
    for module in ("applications.first.models", "applications.second.models", "core.helper", "config.settings"):
        write_module(tmp_path, module)
    write_module(tmp_path, imported)
    write_module(tmp_path, importer, f"import {imported}\n")
    configuration = tmp_path / ".importlinter"
    configuration.write_text((ROOT / ".importlinter").read_text(encoding="utf-8"), encoding="utf-8")
    environment = dict(os.environ, PYTHONPATH=os.pathsep.join([str(tmp_path), str(ROOT)]))
    result = subprocess.run(
        [str(Path(sys.executable).with_name("lint-imports")), "--no-cache"],
        cwd=tmp_path, env=environment, text=True, capture_output=True, timeout=30,
    )
    assert (result.returncode == 0) is kept, result.stdout + result.stderr
    assert "KEPT" in result.stdout if kept else "BROKEN" in result.stdout
