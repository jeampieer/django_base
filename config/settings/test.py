import os

# Credencial pública exclusivamente de tests, suficiente para firmar JWT de prueba.
os.environ.setdefault("SECRET_KEY", "test-only-secret-key-for-isolated-template-tests-000000")

from .base import *  # noqa: E402

INSTALLED_APPS += ["django_extensions"]

# PostgreSQL si se proporciona; SQLite solo para la ejecución rápida local.
DATABASES = {"default": env.db("TEST_DATABASE_URL", default="sqlite://:memory:")}
DATABASES["default"]["ATOMIC_REQUESTS"] = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
