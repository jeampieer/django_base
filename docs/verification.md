# Verificación de la plantilla

Verificación realizada el 20 de octubre de 2026. Se usó un entorno virtual
propio con Python 3.11.6, Django 5.2.8 y PostgreSQL 14.17 en una instancia
temporal aislada. No se utilizaron las credenciales ni la base del proyecto padre.
El workflow suministrado configura PostgreSQL 16; no se ejecutó GitHub Actions.

## Resultados

| Comando | Resultado |
|---|---|
| `python -m pip install -r requirements/local.txt` | Dependencias instaladas |
| `python -m pip check` | `No broken requirements found.` |
| `pytest -v` con PostgreSQL | **118 passed**, sin omisiones |
| `pytest -q` con SQLite | **116 passed, 2 skipped**; solo se omiten los tests de concurrencia |
| `lint-imports --no-cache` | **4 kept, 0 broken**; 133 archivos y 222 dependencias |
| `flake8 .` | Sin hallazgos; exit code 0 |
| `python manage.py check` | `System check identified no issues (0 silenced).` |
| `python manage.py makemigrations --check --dry-run` | `No changes detected` |
| `python manage.py show_urls` | 26 rutas registradas |
| `python manage.py spectacular --validate --fail-on-warn` | Documento válido; sin errores ni warnings |

Los comandos de Django se ejecutaron con `config.settings.test`. La migración
inicial se generó con Django. Se incluyen `applications/users/migrations/0001_initial.py`
y la migración de `example`, con dependencia del usuario configurable. No se
modificó ni migró una BD existente para cambiar su usuario.

Los tests cubren CRUD y auditoría, acceso por rol, autorización por objeto,
service sin HTTP, rollback, estado obsoleto, bloqueo concurrente real, agregados
en una consulta, serializers sin consultas, mensajes Celery, JWT, CORS, health,
OpenAPI y arranque WSGI/ASGI con configuración de producción. Los tests nuevos
cubren bootstrap de superusuario, catálogo de roles reemplazable, creación y
edición por services, jerarquía, perfiles propios, revocación de todos los
refresh, intentos desconocidos, persistencia de fallos y lockout, sesiones/eventos
y protección concurrente del último superusuario activo. Catorce casos prueban
la configuración real de import-linter sobre dos módulos artificiales e incluyen
violaciones deliberadas que deben ser rechazadas.

También se verificó una copia independiente de los archivos entregables, sin el
entorno virtual, las caches ni los paquetes del repositorio padre. Los módulos
se resolvieron desde esa copia y pasaron los mismos checks y los 118 tests.

## Alcance de la comprobación

- Los tests Celery corren en modo eager con broker en memoria; no se probó un
  worker conectado a Redis.
- La instalación de producción y el despliegue remoto no se ejecutaron.
- No se probaron otras versiones de Python ni todos los motores PostgreSQL
  admitidos por Django. SQLite ofrece la ejecución rápida y omite el test de
  dos pruebas de bloqueo de filas; PostgreSQL es la verificación completa y la opción de CI.
- No se ejecutaron tests ni migraciones del backend padre. El estado de Git
  muestra únicamente archivos nuevos bajo `template/`.
- La instancia PostgreSQL temporal se detuvo después de la verificación.

## Las siete correcciones documentales

| Problema original | Corrección y ubicación |
|---|---|
| Mapa incompleto o ficticio | Mapa real en `architecture.md`; tabla de creación condicional en `app-structure.md` |
| Services descritos como Python puro | Tests sin HTTP y con BD en `architecture.md`, sección Services y transacciones |
| Lecturas complejas sin lugar definido | `selectors/`, sección Lecturas y representación; ejemplo de estadísticas |
| Transacciones sin dueño | `transaction.atomic` en service; misma sección y ejemplo ejecutable |
| Extracción de módulos prometida sin límites | Regla de imports, contratos automáticos y límites de extracción en `architecture.md` |
| `schemas/` confundido con serializers | Metadatos OpenAPI separados de contratos de ejecución en ambos documentos |
| Referencias que contradicen el patrón | HackSoft como respaldo principal; las otras dos obras como alternativas descartadas |
