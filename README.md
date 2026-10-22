# django_base — API

Este proyecto es el resultado de años de trabajo refinando y mejorando la
arquitectura de mis proyectos backend con Django. Reúne esa experiencia en una
base reutilizable para nuevos proyectos.

Plantilla reutilizable de backend REST con Django y Django REST Framework.
Incluye autenticación, gestión de usuarios y un módulo de ejemplo para construir
nuevos proyectos con arquitectura modular por capas y Service Layer.
Incluye un panel Django Admin nativo para gestión interna y auditoría.
Código en inglés; documentación en español.

---

## ¿Qué ofrece esta plantilla?

| Módulo | Uso | Descripción |
| --- | --- | --- |
| `users` | Base de identidad | Usuarios, roles configurables, JWT, sesiones y eventos de seguridad |
| `example` | Demostración | Etiquetas y entradas: CRUD, filtros, estadísticas, finalización y tarea Celery |

---

## Stack

| Capa | Tecnología |
| --- | --- |
| Framework | Python ≥ 3.10 (CI: 3.11) · Django 5.2.8 · DRF 3.16.1 |
| Autenticación | JWT mediante djangorestframework-simplejwt |
| Base de datos | PostgreSQL; SQLite para tests rápidos |
| Tareas | Celery 5.5.3 · broker Redis |
| Documentación API | OpenAPI JSON mediante drf-spectacular |
| Tests | pytest · pytest-django · pytest-cov · model-bakery |
| Calidad | flake8==7.1.1 · import-linter==2.15 |

---

## Arquitectura

**Arquitectura Modular por Capas con Service Layer.** Cada módulo es dueño de sus
modelos, serializers, vistas, services, selectors, permisos y pruebas.
El CRUD simple usa las vistas base de `core/`; los procesos con reglas de negocio
usan services, responsables también de las transacciones.

| Documento | Qué contiene |
| --- | --- |
| [Arquitectura](docs/architecture.md) | Responsabilidades, transacciones y límites entre módulos |
| [Estructura de aplicaciones](docs/app-structure.md) | Carpetas, convenciones y patrones de implementación |

---

## Inicio rápido

### Requisitos previos

Python ≥ 3.10 y PostgreSQL para desarrollo. Redis se utiliza como broker si
ejecutas el worker Celery; la API usa caché local en memoria. Docker es opcional.

### Preparar el entorno

Desde la raíz de este repositorio:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements/local.txt
cp .env.example .env
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

Copia la clave generada a `SECRET_KEY` en `.env` y ajusta las conexiones locales.
La configuración lee únicamente el `.env` de este proyecto y las variables
del proceso.

### Variables de entorno para desarrollo

Valores de ejemplo, que debes adaptar a tu entorno:

```dotenv
DJANGO_SETTINGS_MODULE=config.settings.local
SECRET_KEY=replace-with-a-random-secret-at-least-50-characters-long
DATABASE_URL=postgres://backend:backend@127.0.0.1:5432/backend
TEST_DATABASE_URL=postgres://backend:backend@127.0.0.1:5432/backend_test_source
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

Consulta las demás variables en [.env.example](.env.example).
La cuenta de tests necesita permiso `CREATEDB`; usa una base dedicada.

<details>
<summary>Servicios locales con Docker (opcional)</summary>

Estos contenedores usan las credenciales locales del ejemplo:

```bash
docker run --name backend-postgres -d -p 5432:5432 \
  -e POSTGRES_USER=backend -e POSTGRES_PASSWORD=backend -e POSTGRES_DB=backend postgres:16
docker run --name backend-redis -d -p 6379:6379 redis:7
```

Cuando PostgreSQL esté listo, crea la base indicada en `TEST_DATABASE_URL`:

```bash
docker exec backend-postgres createdb -U backend backend_test_source
```

</details>

### Base de datos y servidor

Antes del primer `migrate`, revisa los roles de `config/settings/base.py`.
`AUTH_USER_MODEL` ya es `users.User`; cambiarlo sobre una base existente requiere
un plan de migración específico. Consulta [usuarios y autenticación](docs/auth.md).

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

El panel está en `http://127.0.0.1:8000/admin/`; usa la cuenta creada con
`createsuperuser`. Solo admite superusuarios activos con acceso staff y rol
configurado. Usuarios, etiquetas y entradas se gestionan desde formularios
nativos; intentos de acceso y eventos de seguridad son de solo lectura.
Consulta [Django Admin](docs/admin.md) para el patrón reutilizable y sus límites.

### Worker Celery

En otra terminal, con el entorno virtual activo y Redis disponible:

```bash
DJANGO_SETTINGS_MODULE=config.settings.local celery -A config worker --loglevel=info
```

---

## Endpoints principales

| Método | URL | Descripción |
| --- | --- | --- |
| POST | `/api/v1/auth/token/` | Login con username y password; devuelve access, refresh y perfil |
| POST | `/api/v1/auth/token/refresh/` | Obtener un access nuevo mediante refresh |
| GET | `/api/v1/auth/me/` | Consultar el perfil propio |
| GET · POST | `/api/v1/users/` | Listar y crear usuarios |
| POST | `/api/v1/users/filter/` | Filtrar usuarios según el alcance del actor |
| GET · PUT · PATCH · DELETE | `/api/v1/users/<uuid>/` | Consultar, editar perfil y desactivar |
| POST | `/api/v1/users/change-password/` | Cambiar la contraseña propia |
| GET · POST | `/api/v1/example/labels/` | Listar y crear etiquetas |
| GET · POST | `/api/v1/example/entries/` | Listar y crear entradas |
| POST | `/api/v1/example/entries/<uuid>/finalize/` | Finalizar una entrada mediante su service |
| GET | `/health/ping/` | Comprobar el proceso; público |
| GET | `/health/` | Comprobar base de datos y caché; público |
| GET | `/api/schema/` | Documento OpenAPI JSON; requiere superusuario |

El login entrega los tokens en `data.access` y `data.refresh`.
Envía el access como `Authorization: Bearer <access>`.
El [contrato de autenticación](docs/auth.md) detalla permisos, revocación y
los demás endpoints de usuarios.

---

## Tests y calidad

```bash
TEST_DATABASE_URL=sqlite://:memory: pytest --cov --cov-report=term-missing
flake8 .
lint-imports --no-cache
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py check
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py spectacular --validate --fail-on-warn --format openapi-json
```

SQLite omite dos pruebas de concurrencia. Para ejecutarlas, configura
`TEST_DATABASE_URL` con PostgreSQL y usa `pytest --cov --cov-report=term-missing`, como en
[CI](.github/workflows/ci.yml). Las pruebas de Celery usan modo eager y broker
en memoria; no necesitan Redis ni worker externo.

La cobertura de líneas mide `applications` y `core`, con mínimo global del 85 %
configurado únicamente en [.coveragerc](.coveragerc). Todo código nuevo de un
módulo incluye tests de comportamiento; revisa las líneas pendientes del reporte.

Consulta el alcance y los resultados históricos en [verificación](docs/verification.md).

---

## Migraciones

Versiona las migraciones junto con los cambios de modelos para reproducir el
esquema entre entornos:

```bash
python manage.py makemigrations
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py makemigrations --check --dry-run
python manage.py migrate
```

---

## Producción

Configura una clave propia, PostgreSQL, hosts y CORS del despliegue, y Redis
si utilizas Celery. TLS termina en la infraestructura; ajusta
`SECURE_SSL_REDIRECT` al esquema real del proxy.

```bash
python -m pip install -r requirements/production.txt
DJANGO_SETTINGS_MODULE=config.settings.production python manage.py migrate
DJANGO_SETTINGS_MODULE=config.settings.production python manage.py collectstatic --noinput
DJANGO_SETTINGS_MODULE=config.settings.production gunicorn config.wsgi:application
DJANGO_SETTINGS_MODULE=config.settings.production celery -A config worker --loglevel=info
```

Servir `/static/` desde `staticfiles/` mediante la infraestructura del despliegue;
Gunicorn no sirve los estáticos del panel. El acceso de producción utiliza HTTPS.

---

## Documentación

| Tema | Documento |
| --- | --- |
| Índice completo | [docs/INDEX.md](docs/INDEX.md) |
| Arquitectura | [docs/architecture.md](docs/architecture.md) |
| Convenciones | [docs/app-structure.md](docs/app-structure.md) |
| Usuarios, autenticación y permisos | [docs/auth.md](docs/auth.md) |
| Django Admin | [docs/admin.md](docs/admin.md) |
| Crear un módulo | [docs/new-module-checklist.md](docs/new-module-checklist.md) |
| Alcance del framework | [docs/core-extraction.md](docs/core-extraction.md) |
| Verificación | [docs/verification.md](docs/verification.md) |

---

## Estado y alcance

La plantilla entrega una API JSON y un panel Django Admin nativo, con `users`
como base y `example` como referencia.
Al crear un proyecto, sustituye el ejemplo por tus módulos, adapta el título
OpenAPI en `config/settings/base.py` y el nombre de Celery en `config/celery.py`.
Sigue el [checklist de módulos](docs/new-module-checklist.md).

---

## Desarrollo con agentes

[AGENTS.md](AGENTS.md) reúne las reglas de trabajo del repositorio.
Todo agente debe leer íntegramente la documentación de `docs/` antes de
planificar o modificar el proyecto, empezando por su [índice](docs/INDEX.md).

---

## Autor

Desarrollado por [Jeampieer](https://portfolio-jeampieer.vercel.app/).
