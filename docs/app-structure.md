# Estructura y convenciones del backend

Fuente autoritativa para crear módulos de esta plantilla. Ver el patrón y sus
límites en [architecture.md](architecture.md).

## Cuándo crear cada pieza

| Pieza | Cuándo existe | En el ejemplo |
|---|---|---|
| `__init__.py`, `apps.py` | Módulo Django instalado; `ready()` registra policies | Sí |
| `urls.py` | El módulo expone endpoints; prefijo de versión en `config/urls.py` | Sí |
| `models/` | Tiene entidades persistidas; un archivo por modelo | Sí |
| `migrations/` | Desde el primer modelo; toda migración se versiona | Sí |
| `serializers/` | Valida o representa contratos API | Sí |
| `schemas/` | Los metadatos OpenAPI necesitan separación de las views | Sí |
| `api_views/` | Adaptadores HTTP; un archivo por recurso/proceso | Sí |
| `policies.py` | Recurso sujeto a autorización por rol/modelo | Sí |
| `services/` | Primera escritura con reglas de negocio | Sí |
| `selectors/` | Primera lectura compleja entre modelos/agregados | Sí |
| `permissions/` | Primera autorización por objeto o estado | Sí |
| `tasks.py` | Primer punto de entrada Celery; adaptador delgado | Sí |
| `tests/` | Primer comportamiento implementado; separar por flujo | Sí |
| `managers/` | QuerySet reutilizable de un modelo o manager técnico propio | En `users`; no en `example` |
| `management/commands/` | Primer comando operativo; resuelve/valida y llama services | No |
| `public.py` | Primer contrato estable que otro módulo necesita consumir | No |
| `admin.py` | Modelos del panel; CRUD auditado o adaptador a service | Sí |
| `forms.py` | Contratos HTML que necesitan definición propia | Sí |

No crear carpetas vacías para anticipar crecimiento. Los `__init__.py` necesarios
para paquetes Python sí se incluyen. `managers/` no reemplaza los selectores:
no coordina casos de uso ni aloja agregados de varios modelos.

`config/` es el composition root: settings, URL raíz, Celery, ASGI y WSGI.
`core/` contiene únicamente infraestructura compartida y pruebas. `tools/`
contiene la regla de imports, fuera de las aplicaciones de negocio.
No hay `templates/`, `media/`, assets de frontend, `management/` ni `managers/`
vacíos. Archivos o plantillas para documentos/correos se añaden al existir un
caso concreto que los use; no forman parte del ejemplo.

El panel usa las plantillas y estáticos distribuidos con Django. Sus bases
están en `core/admin/`; ver [admin.md](admin.md). El sitio se registra de forma
explícita y solo admite superusuarios activos con acceso staff. Admin y
backends son adaptadores de entrada; formularios no importan services.

## Modelos y migraciones

- Heredar de `core.models.BaseModel`: UUID, `is_active`, `created`, `modified`,
  `created_by` y `updated_by`. Logs/auditoría especializada pueden heredar
  `models.Model`. `users.User` hereda BaseModel; UserSession y SecurityEvent son logs con `models.Model`.
- Campos en inglés; `verbose_name` en español; choices antes de la clase.
- FK del mismo módulo con string `"example.Label"`; auditoría con
  `settings.AUTH_USER_MODEL`. No importar modelos de otro módulo.
- Campos, relaciones y constraints en modelos. Reglas de procesos en services.
- Generar y versionar migraciones con el mismo cambio; nunca crear tablas
  manualmente para evitar una migración.
- `AUTH_USER_MODEL` ya es `users.User`. No cambiarlo después de migrar una BD;
  seguir las instrucciones de [auth.md](auth.md#modelo-y-primera-migración).

## Serializers y schemas

CRUD: `<Model>Serializer` y `<Model>DetailSerializer`. Si no hay relaciones que
expandir, el segundo puede heredar del primero sin añadir campos. En procesos:
`<UseCase>InputSerializer` y `<UseCase>OutputSerializer`, propios del endpoint.

`id`, `created`, `modified`, `created_by`, `updated_by` siempre de solo lectura.
También son de solo lectura los campos controlados por un service. No hacer
consultas explícitas ni activar validadores implícitos que consulten la BD.
La salida usa entidades con sus relaciones ya precargadas.

`schemas/` solo contiene `extend_schema`, `extend_schema_view`, parámetros y
descripciones de respuestas. Puede importar serializers; los serializers no
importan `schemas/`. No se validan datos de ejecución en esa carpeta.

## Views y URLs

CRUD: `CustomListView`, `CustomDetailView`, `CustomFilterView`; declarar modelo,
serializers y listas explícitas `allowed_filters`, `allowed_excludes` y
`allowed_order_by`. Una lista de filtros vacía prohíbe filtrar campos. DELETE
desactiva; no alterna el estado. PUT conserva la actualización parcial del core
de origen. No hay bulk create/update en este subconjunto.

Proceso: `APIView` → input serializer → resolver entidad → permisos de objeto →
service → output serializer → `ApiResponse`. No `transaction.atomic`, reglas de
dominio ni `Response(...)` directamente. Consultas simples para resolver y
precarga pueden estar en el adaptador; consultas complejas van a selectors.

Las vistas de usuarios heredan las bases CRUD. Sobrescriben la orquestación de
escritura para llamar services: crear identidad, hashear contraseñas, autorizar
por jerarquía, revocar refresh y auditar son casos de negocio. El serializer de
usuario no crea ni actualiza cuentas.

Recursos en plural, `filter/` antes del detalle y `<uuid:pk>` para recursos
propios. Acción: `<recurso>/<uuid:pk>/<accion>/`. El filtro POST requiere permiso
de lectura. Una `APIView` debe invocar `check_object_permissions` expresamente.

## Services, selectors y tareas

Un archivo por caso de uso, clase con nombre de acción:

```python
class FinalizeEntryService:
    def __init__(self, *, actor: User, entry: Entry) -> None:
        ...

    @transaction.atomic
    def execute(self, *, summary: str) -> Entry:
        ...
```

El service importa modelos propios directamente y lanza excepciones DRF/Django;
la view las propaga al manejador global. No usa request, códigos HTTP ni
serializers. La transacción cubre validaciones dependientes del estado y escrituras.

Selectors con argumentos keyword-only, retorno tipado y solo lecturas. Exponer
selectores a otro módulo exige una interfaz pública explícita; no importar el
selector interno desde fuera.

Las tareas solo validan argumentos serializables, resuelven entidades mediante
selectores y llaman al service. Esa resolución mínima fue autorizada para
mantener services sin PKs. El service conserva todas las reglas, incluido el
acceso cuando se invoca sin HTTP. No decorar toda tarea con una transacción ni
reintentar ciegamente una operación no idempotente.
Si la entidad dejó de existir, registrar un log y terminar sin error, incluso
si desaparece entre la resolución y la ejecución del service.

## Policies, permisos y pruebas

Policy por modelo con `model_label = "example.Entry"`; registrar en `ready()`.
Roles no configurados y modelos sin registro deniegan el acceso. El adaptador de
roles vive en `core/auth/roles.py` y consulta `USER_ROLES`; `is_staff` no otorga
permisos de API. Las policies declaran una capacidad y sus perfiles de acceso;
settings asigna capacidades a los roles concretos. `is_superuser` selecciona el
perfil de superusuario de la policy, siempre que la cuenta esté activa.
La autorización por estado
vive en `permissions/<recurso>.py`, sin efectos secundarios.

En `users`, `permissions/rules.py` comparte predicados puros de autorización
entre permisos HTTP, policies y services. Las escrituras revalidan esos
predicados sobre entidades bloqueadas para no confiar en un estado obsoleto.
Ver [auth.md](auth.md) para jerarquía, estados y revocación.

Tests por flujo: `test_<recurso>_list.py`, `test_<recurso>_detail.py`,
`test_<recurso>_filter.py`, `test_<caso>_service.py`, `test_<lectura>_selector.py`
y `test_tasks.py`. Usar pytest-django y model-bakery. Los tests de services y
selectores usan BD sin HTTP; los de endpoints verifican el contrato real.
La concurrencia debe probarse con PostgreSQL. Los fixtures compartidos están
en el `conftest.py` raíz de la plantilla.

Cada módulo nuevo queda cubierto automáticamente por `.importlinter`. Mantener
`__init__.py` simples: reexportar modelos propios dentro de `models/` es válido;
usar `public.py` para reexportar modelos está prohibido.
