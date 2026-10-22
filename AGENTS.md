# AGENTS.md — Plantilla backend Django/DRF

Backend REST reutilizable con arquitectura modular por capas y Service Layer.
Incluye `users` como módulo base de identidad y `example` como demostración.
Código en inglés; documentación en español.

---

## Lectura obligatoria

Todo agente que trabaje en cualquier parte del repositorio debe empezar por el
[índice](docs/INDEX.md) y leer íntegramente todos los documentos de `docs/` antes
de planificar o modificar el proyecto, incluidos los que se añadan después.

Cumple estrictamente sus reglas: `docs/` prevalece sobre resúmenes y patrones
del código existente, respetando instrucciones explícitas del usuario. Si dos
documentos se contradicen, consulta antes de implementar la parte afectada.

---

## Stack técnico

| Capa | Tecnología |
| --- | --- |
| Framework y API | Python ≥ 3.10 (CI: 3.11), Django 5.2.8, DRF 3.16.1 |
| Autenticación | JWT mediante djangorestframework-simplejwt |
| Base de datos | PostgreSQL; SQLite para pruebas rápidas |
| Tareas | Celery 5.5.3 con broker Redis |
| Tests | pytest, pytest-django, pytest-cov y model-bakery |
| Documentación API | drf-spectacular; OpenAPI JSON |
| Calidad | flake8==7.1.1 e import-linter==2.15 |

---

## Estructura del repositorio

```text
applications/
  users/            identidad, autenticación y auditoría
  example/          ejemplo de integración
core/               infraestructura compartida
config/             settings, URLs, Celery, ASGI y WSGI
requirements/       base.txt · local.txt · production.txt
tools/              contratos de imports y sus pruebas
docs/               índice y guías técnicas
.github/workflows/  comprobaciones de CI
```

Un módulo como `applications/example/` contiene `models/`, `migrations/`,
`serializers/`, `schemas/`, `api_views/`, `services/`, `selectors/`,
`permissions/` y `tests/`, además de `apps.py`, `policies.py`, `urls.py` y
`tasks.py`. Crea piezas opcionales únicamente cuando exista un caso concreto.

---

## Arquitectura

CRUD simple: vistas base del core. Procesos con reglas de negocio: services.
La [arquitectura](docs/architecture.md) define responsabilidades, transacciones
y límites entre módulos; [app-structure](docs/app-structure.md) es la fuente
autoritativa de convenciones y patrones.

---

## Entorno de desarrollo

Ejecuta desde la raíz del repositorio:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements/local.txt
cp .env.example .env
```

Configura una clave propia y las URLs locales de PostgreSQL y Redis en `.env`.
`manage.py` selecciona `config.settings.local`. Antes de la primera migración,
revisa el usuario configurable y los roles según [auth](docs/auth.md).

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

Para iniciar el worker en otra terminal con el entorno activo:

```bash
DJANGO_SETTINGS_MODULE=config.settings.local celery -A config worker --loglevel=info
```

---

## Tests

Los tests viven en `tests/test_*.py` de cada módulo; los fixtures compartidos,
en `conftest.py`. Usa pytest-django y model-bakery; prueba services sin HTTP,
autorización, rollback y contratos de endpoints. Todo código nuevo de un módulo
incluye tests de su comportamiento. La suite completa mide `applications` y
`core` y exige un mínimo global de cobertura de líneas del 85 %, configurable
únicamente en [.coveragerc](.coveragerc). Consulta sus exclusiones y el alcance
de la medición en [verificación](docs/verification.md).

```bash
TEST_DATABASE_URL=sqlite://:memory: pytest --cov --cov-report=term-missing
TEST_DATABASE_URL=sqlite://:memory: pytest applications/users/tests/ -v
```

SQLite omite dos pruebas de concurrencia. La comprobación completa requiere
PostgreSQL mediante `TEST_DATABASE_URL` y `pytest --cov --cov-report=term-missing`,
como en CI. La ejecución de un módulo sirve para desarrollo y no sustituye la
comprobación global de cobertura. Los tests Celery usan modo eager y broker en
memoria, sin Redis ni worker externo.

---

## Convenciones obligatorias

- Cuatro espacios, snake_case para archivos/funciones y PascalCase para clases;
  líneas de hasta 120 caracteres según `.flake8`.
- Modelos basados en `BaseModel`; logs/auditoría pueden usar `models.Model`.
  Campos en inglés y `verbose_name` en español; auditoría de solo lectura.
- Serializers sin consultas; lecturas complejas en selectors. Respuestas de
  negocio mediante `ApiResponse`; recursos plurales con UUID.

Los patrones completos están en [app-structure](docs/app-structure.md).

---

## Cómo agregar una nueva feature

Para un módulo nuevo, sigue el [checklist](docs/new-module-checklist.md):
define su límite, registra la app, añade modelos y migraciones, elige CRUD o
service, registra policies y rutas y prueba los flujos. Versiona las migraciones
junto con los cambios de modelos; evita carpetas opcionales vacías.

---

## Reglas que nunca romper

- Services con argumentos keyword-only y entidades ya resueltas, sin `request`.
- `transaction.atomic` pertenece al service; no habilitar `ATOMIC_REQUESTS`.
- Tareas Celery delgadas: pueden resolver entidades mediante selectors y llamar
  al service; no contienen reglas de negocio ni escrituras directas.
- Consume otros módulos mediante sus services o interfaces públicas explícitas;
  no importes sus modelos ni otros componentes internos.
- Referencia usuarios mediante `settings.AUTH_USER_MODEL` y `get_user_model()`.
- `core/` no depende de `applications/` ni `config/`; justifica explícitamente
  sus cambios en la descripción de la entrega.

Consulta el detalle y las excepciones en [arquitectura](docs/architecture.md).

---

## Verificación antes de dar una tarea por terminada

Tests, flake8 e import-linter deben pasar; también los checks de CI:

```bash
flake8 .
lint-imports --no-cache
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py check
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py makemigrations --check --dry-run
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py show_urls
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py spectacular --validate --fail-on-warn --format openapi-json
pytest --cov --cov-report=term-missing
```

Consulta el alcance de [verificación](docs/verification.md). Reporta resultados
actuales, fallos y omisiones; los resultados históricos no validan cambios nuevos.

---

## Documentación y mantenimiento

Consulta el [índice general](docs/INDEX.md). Si cambia la estructura, una
convención o un contrato, actualiza el documento correspondiente y el índice
cuando cambie su inventario.

Conserva commits con prefijo de tipo, como `feat:`. Las PRs describen el
comportamiento, enlazan incidencias pertinentes y reportan comprobaciones.
No incluyas secretos ni archivos generados.
