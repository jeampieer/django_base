import os

from celery import Celery

# Importar config desde WSGI/ASGI no debe seleccionar el entorno local.
# manage.py ya selecciona local; el worker local lo recibe explícitamente.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

app = Celery("backend")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
