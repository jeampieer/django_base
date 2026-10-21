from .base import *

DEBUG = True
INSTALLED_APPS += ["django_extensions"]
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
DATABASES = {"default": env.db("DATABASE_URL")}
