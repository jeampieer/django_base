# Plantilla de backend Django/DRF

Backend REST con arquitectura modular por capas y Service Layer. Python ≥ 3.10
(verificado con 3.11), Django 5.2.8, DRF 3.16.1, PostgreSQL y Celery 5.5.3.
Código en inglés y documentación en español. No requiere el repositorio padre.
Incluye `users` como módulo base y `example` como demostración de integración.

## Crear un proyecto nuevo

Desde la raíz del repositorio que contiene esta carpeta:

```bash
rsync -a --exclude='.venv' --exclude='.runtime' --exclude='__pycache__' \
  --exclude='.pytest_cache' --exclude='.import_linter_cache' \
  template/ ../nuevo-backend/
cd ../nuevo-backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements/local.txt
cp .env.example .env
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

Usa la clave generada como `SECRET_KEY` en `.env`. Ajusta las URLs de PostgreSQL y
Redis, `ALLOWED_HOSTS` y los orígenes CORS. La configuración solo lee el `.env`
de este proyecto y las variables de su proceso; no busca archivos en carpetas padre.

**Antes del primer migrate**, define los roles del proyecto en
`config/settings/base.py`. `AUTH_USER_MODEL` ya es `users.User`, con UUID y
auditoría. Si una copia anterior ya tiene una BD migrada con `auth.User`, cambiar
ese setting requiere migraciones complejas: esta entrega no convierte ni borra
esa BD. Para un proyecto nuevo sin datos, usa una base vacía. Ver [auth.md](docs/auth.md).

Si necesitas servicios locales y tienes Docker, puedes crear instancias dedicadas:

```bash
docker run --name backend-postgres -d -p 5432:5432 \
  -e POSTGRES_USER=backend -e POSTGRES_PASSWORD=backend -e POSTGRES_DB=backend postgres:16
docker exec backend-postgres createdb -U backend backend_test_source
docker run --name backend-redis -d -p 6379:6379 redis:7
python manage.py migrate
python manage.py createsuperuser --username fictional.root --email root@example.test
python manage.py runserver
```

El usuario de tests necesita permiso `CREATEDB`. Usa una instancia de desarrollo
dedicada; pytest crea y elimina una base con prefijo `test_`.

En otra terminal del proyecto, con el entorno virtual activo:

```bash
DJANGO_SETTINGS_MODULE=config.settings.local celery -A config worker --loglevel=info
```

## Autenticación y ejemplo

El comando solicita nombres, apellidos y contraseña. El username y correo
mostrados son ficticios: sustitúyelos por los datos del nuevo proyecto. Crea un
superusuario activo con el rol configurado en `USER_SUPERUSER_ROLE`.

User utiliza username como login, email único, first_name, last_name, un rol,
UUID y auditoría. Los nombres concretos de roles se configuran en settings;
`is_staff` no concede permisos de API. Ejemplo ficticio incluido:

```python
USER_ROLES = {
    "MANAGER": {"label": "Gestor (ejemplo)", "level": 10,
                "permissions": ["users.manage", "example.write"]},
    "MEMBER": {"label": "Miembro (ejemplo)", "level": 20, "permissions": []},
}
USER_DEFAULT_ROLE = "MEMBER"
USER_SUPERUSER_ROLE = "MANAGER"
```

Menor nivel significa mayor jerarquía. Gestores administran roles inferiores;
miembros editan su propio nombre/email y contraseña. Superusuarios administran
todas las cuentas. No se permite autodesactivación ni perder el último
superusuario activo. Para cambiar códigos, niveles o capacidades no se editan
policies ni modelos; renombrar un código ya persistido exige migrar esos datos.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/token/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"fictional.root","password":"contraseña-del-nuevo-proyecto"}'
```

Usa `data.access` de la respuesta como `Authorization: Bearer <access>`. El refresh
se envía a `POST /api/v1/auth/token/refresh/` con `{"refresh":"..."}`. Se conserva
la configuración de origen: access de una hora, refresh de siete días, sin
rotación. El refresh devuelve únicamente un access nuevo.

| Endpoint | Uso |
|---|---|
| `/health/ping/` | GET público: proceso activo |
| `/health/` | GET público: BD y cache; 503 si fallan |
| `/api/schema/` | GET: OpenAPI JSON, requiere superusuario |
| `/api/v1/auth/me/` | GET: perfil propio |
| `/api/v1/auth/logout/` | POST: revoca refresh de todas las sesiones |
| `/api/v1/users/` | GET paginado / POST mediante service |
| `/api/v1/users/filter/` | POST de lectura con el alcance del actor |
| `/api/v1/users/<uuid>/` | GET, PUT/PATCH de perfil y DELETE que solo desactiva |
| `/api/v1/users/<uuid>/activate/` | POST de activación explícita |
| `/api/v1/users/<uuid>/deactivate/` | POST de desactivación explícita |
| `/api/v1/users/change-password/` | POST propio: current_password y new_password |
| `/api/v1/users/<uuid>/change-password/` | POST: reseteo autorizado con new_password |
| `/api/v1/users/<uuid>/change-role/` | POST: role autorizado por jerarquía |
| `/api/v1/users/<uuid>/sessions/` | GET: intentos de autenticación paginados |
| `/api/v1/users/<uuid>/security-events/` | GET: eventos paginados como actor/destinatario |
| `/api/v1/example/labels/` | GET paginado y POST; CRUD sin service |
| `/api/v1/example/labels/filter/` | POST de lectura con filtros JSON |
| `/api/v1/example/labels/<uuid>/` | GET, PUT/PATCH parcial y DELETE lógico |
| `/api/v1/example/labels/statistics/` | GET agregado, `?minimum_entries=1` |
| `/api/v1/example/entries/` | GET y POST; crear con `title` y `label` (UUID) |
| `/api/v1/example/entries/filter/` | POST de lectura con filtros JSON |
| `/api/v1/example/entries/<uuid>/` | GET, PUT/PATCH parcial y DELETE lógico |
| `/api/v1/example/entries/<uuid>/finalize/` | POST con `{"summary":"Listo"}`; llama al service |

Flujo de ejemplo: crear una etiqueta con `{"name":"General"}`, crear una entrada
con su UUID, y finalizarla como su autor con la capacidad `example.write`. Debe estar activa, en
borrador y asociada a una etiqueta activa. Estado, resumen y fecha de finalización
no son editables por CRUD. Repetir la finalización se rechaza.

La tarea `applications.example.tasks.finalize_entry` recibe `entry_id` y `actor_id`
como UUID en texto, además de `summary`; valida, resuelve entidades y llama al
mismo service. Si falta una entidad, registra el caso y termina sin error.
No programa reintentos automáticos: la finalización no es
idempotente. Si se encola desde una escritura, hacerlo mediante
`transaction.on_commit` en el service que controla esa escritura.

Las respuestas de aplicación tienen `success`, `status`, `message`, `data` y
`meta`; los errores incluyen `error`. La paginación vive en `meta.pagination`.
El endpoint OpenAPI entrega el documento estándar directamente.

Se incluyen UserSession y SecurityEvent genéricos. Los logins fallidos también
se registran; los bloqueos se configuran con USER_LOCKOUT_THRESHOLD y
USER_LOCKOUT_SECONDS. Logout y cambio de contraseña revocan todos los refresh;
los access existentes conservan su vigencia. Desactivar una cuenta bloquea
access y refresh. El [contrato completo de auth](docs/auth.md) describe cada caso.

## Verificar

Ejecutar desde la raíz del proyecto copiado, con el entorno virtual activo:

```bash
flake8 .
lint-imports --no-cache
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py check
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py makemigrations --check --dry-run
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py show_urls
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py spectacular \
  --validate --fail-on-warn --format openapi-json --file schema.json
pytest -v
```

La configuración de pytest selecciona `config.settings.test`. Con
`TEST_DATABASE_URL` se ejecuta contra PostgreSQL; sin esa variable y sin `.env`
que la defina utiliza SQLite en memoria. Para forzar el modo rápido:

```bash
TEST_DATABASE_URL=sqlite://:memory: pytest -v
```

SQLite omite las dos pruebas de bloqueo concurrente, porque no implementa
`select_for_update`. La CI usa PostgreSQL y ejecuta ambas. Los tests de
Celery usan modo eager y broker en memoria; no requieren un worker ni Redis.

El workflow incluido en `.github/workflows/ci.yml` queda activo al copiar la
plantilla a la raíz del nuevo repositorio. GitHub no descubre workflows anidados
en `template/.github/` dentro del repositorio de origen. La configuración incluye
flake8, cuatro contratos de imports, checks, validación OpenAPI y pytest.

## Producción y alcance

```bash
python -m pip install -r requirements/production.txt
DJANGO_SETTINGS_MODULE=config.settings.production python manage.py migrate
DJANGO_SETTINGS_MODULE=config.settings.production gunicorn config.wsgi:application
DJANGO_SETTINGS_MODULE=config.settings.production celery -A config worker --loglevel=info
```

Configura una clave propia, PostgreSQL, Redis, hosts y CORS mediante variables
del entorno. TLS debe terminar en la infraestructura de despliegue; ajusta
`SECURE_SSL_REDIRECT` al esquema real del proxy.

Se omiten admin, Swagger/Redoc HTML, templates, media y estáticos. Aunque el
origen tiene administración, cargas de archivos y documentos generados, el
ejemplo no los necesita. OpenAPI sigue disponible en JSON para clientes externos.

Para adaptar: sustituir el módulo `example`, actualizar el título OpenAPI y el
nombre de la app Celery, definir las reglas del negocio nuevo y crear su primera
migración antes de desplegar. No se incluyen datos iniciales.

- [Arquitectura](docs/architecture.md)
- [Estructura y convenciones](docs/app-structure.md)
- [Usuarios, roles y autenticación](docs/auth.md)
- [Checklist de un módulo nuevo](docs/new-module-checklist.md)
- [Extracción y hallazgos del origen](docs/core-extraction.md)
- [Verificación realizada](docs/verification.md)
