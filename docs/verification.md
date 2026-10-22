# Verificación de la plantilla

## Cobertura de líneas

Instala las dependencias de `requirements/local.txt`, incluido
`pytest-cov==7.0.0`, y ejecuta desde la raíz:

```bash
# Verificación completa, con TEST_DATABASE_URL apuntando a PostgreSQL aislado.
pytest --cov --cov-report=term-missing

# Verificación rápida; omite dos pruebas de concurrencia.
TEST_DATABASE_URL=sqlite://:memory: pytest --cov --cov-report=term-missing
```

[.coveragerc](../.coveragerc) centraliza los paquetes `applications` y `core`,
las exclusiones y el mínimo global de líneas mediante `fail_under = 85`.
Para ajustar el umbral, edita únicamente ese valor. CI ejecuta el mismo comando
completo con PostgreSQL y hereda el mínimo sin repetirlo en sus argumentos.
`pytest.ini` conserva la configuración de descubrimiento de tests.

Se omiten migraciones, tests, fixtures `conftest.py`, settings y `manage.py`.
Los archivos sin líneas ejecutables, como los `__init__.py` vacíos, se ocultan
con `skip_empty`; los `__init__.py` con código sí se miden. La selección de
paquetes también deja fuera `config/`, `tools/` y dependencias externas, sin
cambiar los tests descubiertos por pytest, incluidos los de `tools/`.
La medición incluye archivos de los paquetes
seleccionados aunque ningún test los importe. El reporte muestra dos decimales
y las líneas pendientes por archivo.

Todo código nuevo de un módulo incluye tests de comportamiento: services sin
HTTP, autorización, errores, rollback y contratos de endpoints, según aplique.
El mínimo global no sustituye esa obligación. Una ejecución parcial como
`pytest applications/users/tests/ -v` sirve durante el desarrollo; para validar
la entrega se ejecuta la suite completa con cobertura. Si queda por debajo del
mínimo, se informa el porcentaje por paquete y los comportamientos que requieren
pruebas, sin rebajar el umbral ni añadir tests artificiales.

`.coverage`, `.coverage.*`, `htmlcov/` y `coverage.xml` están ignorados por Git.
La verificación aislada usa un venv nuevo, solo las dependencias declaradas y
configuración basada en `.env.example`, sin credenciales existentes. Los
artefactos se guardan fuera del repositorio y se eliminan junto con el entorno
y la instancia PostgreSQL al terminar.

## Django Admin: verificación del 22 de octubre de 2026

Se ejecutó la integración en Python 3.11.6, Django 5.2.8 y PostgreSQL 14.17,
con un entorno virtual nuevo y las dependencias declaradas. PostgreSQL usó un
cluster temporal aislado en el puerto 55439, sin credenciales ni bases del
proyecto de referencia o de Alvia. No se modificó el origen Iperc.

| Comprobación | Resultado |
| --- | --- |
| `python -m pip check` | Sin dependencias incompatibles |
| `flake8 .` | Sin hallazgos |
| `lint-imports --no-cache` | 5 contratos conservados, 0 rotos |
| `python manage.py check` | Sin errores |
| `python manage.py makemigrations --check --dry-run` | Sin cambios pendientes |
| `python manage.py show_urls` | 68 rutas; incluye `/admin/` y operaciones individuales |
| `python manage.py spectacular --validate --fail-on-warn --format openapi-json` | Válido, sin warnings |
| `python manage.py collectstatic --noinput` | 168 archivos recopilados correctamente |
| `pytest --cov --cov-report=term-missing` con PostgreSQL | **170 passed**, sin omisiones; **96,34 %** |

Los comandos Django utilizaron `config.settings.test`. Se incluyen pruebas de
acceso real al panel, CSRF, bloqueo persistente, campos protegidos, CRUD auditado,
rollback del formulario de usuarios, contraseñas, revocación de sesiones web,
auditoría de solo lectura, finalización y límites de imports. La API mantiene
JWT como autenticación y rechaza peticiones autenticadas solo con la cookie
del panel. Las pruebas de concurrencia se ejecutaron sobre PostgreSQL.

Se revisaron visualmente login, índice, listado de usuarios, formulario nativo,
auditoría colapsable y cambio de contraseña en Chrome, usando una base SQLite
temporal y una cuenta ficticia. Los estáticos y las plantillas nativas se
renderizaron correctamente. La nueva migración de usuarios y las migraciones
estándar de admin/sesiones se aplicaron correctamente en esa base vacía.

No se ejecutaron GitHub Actions ni un despliegue remoto; el workflow mantiene
PostgreSQL 16. El backend de sesiones de BD y la dependencia del adaptador
respecto de Django 5.2.8 se explican en [admin.md](admin.md). Los recursos de
revisión, datos y servidores temporales se retiran al finalizar.

## Verificación con cobertura: 21 de octubre de 2026

Se verificó una copia independiente de los entregables con un venv nuevo,
Python 3.11.6, Django 5.2.8, pytest 9.0.1, pytest-cov 7.0.0 y su dependencia
transitiva coverage.py 7.16.2. Solo se instalaron las dependencias declaradas en
`requirements/local.txt` y sus transitivas. La copia usó `.env.example` sin
secretos y una instancia temporal de PostgreSQL 14.17, sin bases existentes.

| Comprobación | Resultado actual |
|---|---|
| `python -m pip check` | Sin dependencias incompatibles |
| `flake8 .` | Sin hallazgos; código 0 |
| `lint-imports --no-cache` | 4 contratos conservados, 0 rotos; 133 archivos, 222 dependencias |
| `python manage.py check` | Sin errores |
| `python manage.py makemigrations --check --dry-run` | Sin cambios |
| `python manage.py show_urls` | 26 rutas |
| `python manage.py spectacular --validate --fail-on-warn --format openapi-json` | Válido, sin warnings |
| `pytest --cov --cov-report=term-missing` con PostgreSQL | **118 passed**, sin omisiones; **95,80 %**, código 0 |
| `pytest --cov --cov-report=term-missing` con SQLite | **116 passed, 2 skipped**; **95,74 %**, código 0 |

Los comandos Django usaron `config.settings.test`. El documento OpenAPI y los
datos de cobertura se guardaron fuera del repositorio. La cobertura por paquete
se calculó sumando líneas ejecutables y pendientes, sin promediar porcentajes
de archivos. Estos son los resultados con PostgreSQL:

| Paquete | Líneas ejecutables | Sin cubrir | Cobertura |
|---|---:|---:|---:|
| `applications` | 1037 | 20 | **98,07 %** |
| `applications/example` | 284 | 0 | **100,00 %** |
| `applications/users` | 753 | 20 | **97,34 %** |
| `core` | 534 | 46 | **91,39 %** |
| **Total (`applications` + `core`)** | **1571** | **66** | **95,80 %** |

Las filas de los módulos desglosan `applications`; no se suman otra vez al total.
Se comprobaron las exclusiones sobre los datos de cobertura y el reporte:
19 archivos sin código ejecutable quedaron ocultos y los `__init__.py` con
código siguieron medidos.

Se leyó el comando de tests del workflow y se ejecutó localmente sin repetir ni
sobrescribir el umbral. La suite completa superó el 85 %. Como control negativo,
se ejecutó ese mismo comando seleccionando únicamente
`applications/example/tests/test_label_statistics_selector.py`: el test pasó,
pero la cobertura global fue **16,87 %** y pytest devolvió **código 1** por no
alcanzar el mínimo heredado. No se añadieron ni modificaron tests.

El workflow conserva PostgreSQL 16. No se ejecutó GitHub Actions ni se probó
esa versión localmente; se verificaron sus comandos con PostgreSQL 14.17.
Se comprobó que Git ignora `.coverage`, `.coverage.*`, `htmlcov/` y `coverage.xml`.
La instancia PostgreSQL se detuvo y se eliminaron el venv, la copia, los logs
y los artefactos temporales al terminar.

## Verificación histórica: 20 de octubre de 2026

Se usó un entorno virtual
propio con Python 3.11.6, Django 5.2.8 y PostgreSQL 14.17 en una instancia
temporal aislada. No se utilizaron las credenciales ni la base del proyecto padre.
El workflow suministrado configura PostgreSQL 16; no se ejecutó GitHub Actions.

### Resultados históricos

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

### Alcance de la comprobación histórica

- Los tests Celery corren en modo eager con broker en memoria; no se probó un
  worker conectado a Redis.
- La instalación de producción y el despliegue remoto no se ejecutaron.
- No se probaron otras versiones de Python ni todos los motores PostgreSQL
  admitidos por Django. SQLite ofrece la ejecución rápida y omite el test de
  dos pruebas de bloqueo de filas; PostgreSQL es la verificación completa y la opción de CI.
- No se ejecutaron tests ni migraciones del backend padre. El estado de Git
  muestra únicamente archivos nuevos bajo `template/`.
- La instancia PostgreSQL temporal se detuvo después de la verificación.

### Las siete correcciones documentales

| Problema original | Corrección y ubicación |
|---|---|
| Mapa incompleto o ficticio | Mapa real en `architecture.md`; tabla de creación condicional en `app-structure.md` |
| Services descritos como Python puro | Tests sin HTTP y con BD en `architecture.md`, sección Services y transacciones |
| Lecturas complejas sin lugar definido | `selectors/`, sección Lecturas y representación; ejemplo de estadísticas |
| Transacciones sin dueño | `transaction.atomic` en service; misma sección y ejemplo ejecutable |
| Extracción de módulos prometida sin límites | Regla de imports, contratos automáticos y límites de extracción en `architecture.md` |
| `schemas/` confundido con serializers | Metadatos OpenAPI separados de contratos de ejecución en ambos documentos |
| Referencias que contradicen el patrón | HackSoft como respaldo principal; las otras dos obras como alternativas descartadas |
