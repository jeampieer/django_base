import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("entrypoint", ["wsgi", "asgi"])
def test_deployment_entrypoint_defaults_to_production(entrypoint: str) -> None:
    environment = dict(os.environ)
    environment.pop("DJANGO_SETTINGS_MODULE", None)
    environment["DATABASE_URL"] = "postgres://backend:backend@127.0.0.1:5432/backend"
    command = (
        f"import config.{entrypoint}; from django.conf import settings; "
        "print(settings.SETTINGS_MODULE, settings.DEBUG)"
    )
    result = subprocess.run(
        [sys.executable, "-c", command], cwd=Path(__file__).resolve().parents[2],
        env=environment, text=True, capture_output=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "config.settings.production False"
