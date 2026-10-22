# Extracción del framework

Todo el trabajo está contenido en esta plantilla. El código y la documentación
del origen se conservaron sin cambios. Es una extracción adaptada y tipada,
no una copia íntegra del framework.

## Qué se conserva y adapta

| Origen | En la plantilla | Adaptación |
|---|---|---|
| `core/models/base.py` | Mismo archivo y clase | UUID, timestamps, auditoría, save con usuario, soft delete y restore; tipado |
| `core/api/responses.py` | Mismo archivo y factory | Mismo envoltorio y helpers esenciales; se omiten helpers sin uso |
| `core/api/views/{base,list,detail,filter}.py` | Mismas clases públicas | CRUD individual, filtrado, paginación, PUT parcial y soft delete; métodos compactados |
| `core/api/{filters,pagination}.py` | Mismos componentes | Listas de campos cerradas por defecto y validación estructural de filtros |
| `core/api/mixins/` | RolePermissionMixin y SoftDeleteViewMixin | Subconjunto para BaseModel; aplica filtrado de campos de salida y actor en el borrado |
| `core/auth/{policy,registry,permission_manager}.py` | Mismas responsabilidades | Catálogo, niveles y capacidades de roles configurados en settings; sin nombres del negocio |
| `core/auth/permissions.py` | IsSuperAdmin | Conservado; se añade HasModelPolicy para denegar lecturas sin policy |
| `core/auth/checks.py` y `core/apps.py` | Checks de policies | Subconjunto sin jerarquías ni campos del negocio |
| `core/api/exceptions.py` | Manejador global genérico | DRF, 404, filtros, integridad y errores internos; sin mensajes por constraint del negocio |
| `core/api/views/health.py` | HealthCheckView y PingView | ApiResponse, 503 para dependencias fallidas y sin detalles internos públicos |
| JWT y auth original | `applications/users/api_views/authentication.py` y services | Conserva duraciones y refresh sin rotación; casos de autenticación separados de representación |
| `core/admin/` | `BaseModelAdmin` y base de solo lectura | Panel nativo, auditoría colapsable y formatos; sin historial/import-export; integración con services |

`core/api/openapi.py` es un helper documental nuevo para describir el envoltorio
real. `core/auth/roles.py` y `HasModelPolicy` son adaptaciones explícitas, no
funciones que se atribuyan al origen. No introducen reglas del negocio nuevo.

## Qué queda fuera

- Campos de identidad del negocio y jerarquías concretas del origen, MFA,
  firmas, dispositivos y respuestas que expandían entidades de otros módulos.
- Traducciones de constraints de negocio en `core/utils/db_errors.py`.
- Views de sincronización/documentación de negocio y helpers PDF/Excel,
  uploads, validadores geográficos y de archivos: no tienen uso en el ejemplo.
- Historial/import-export, storage, push, correo, schedulers y backends de
  resultados Celery: no son necesarios para los patrones pedidos.
- Helpers sin consumidores, bulk CRUD, managers de soft delete y logging/middleware
  extendidos: se documenta un subconjunto verificable en lugar de copiarlos sin uso.
- El AutoSchema dependiente de los roles del origen: sustituido por metadatos
  OpenAPI explícitos y compatibles con los roles genéricos.

La identidad ahora es `users.User`, con BaseModel y manager propio. Se extrajeron
y generalizaron UserSession, SecurityEvent, bloqueo de cuenta, contraseña,
logout, rol y estado. Los eventos no incluyen operaciones de otros dominios.
Crear/actualizar usuarios se trasladó desde serializers a services; los permisos
por jerarquía también se revalidan allí. Se eliminaron los adaptadores JWT
anteriores de core para mantener una única implementación en users.

La ampliación del admin se documenta en [admin.md](admin.md): mantiene el patrón
visual y reutilizable del origen, adaptando nombres del usuario, límites
transaccionales, seguridad, borrado lógico y operaciones con services. El
proyecto de origen se usa únicamente como referencia y no se modifica.

## Hallazgos estáticos en el original

Estos puntos se observaron al leer el código; no se ejecutó ni se corrigió el
backend original como parte de esta tarea:

1. `validate_filter_fields` devuelve los filtros recibidos si no existe lista de
   campos; en la plantilla se deniegan campos no autorizados incluso con lista vacía.
2. Las vistas CRUD leídas no invocan el filtrado de campos de respuesta del
   RolePermissionMixin ni deniegan expresamente lecturas sin policy. La plantilla
   añade la comprobación de acceso y aplica ese filtrado a cada respuesta CRUD.
3. El DELETE de la vista base no pasa el usuario al mixin de soft delete; aquí se
   pasa para conservar el actor de auditoría.
4. Health/Ping construyen `Response` directamente y el health considera opcional
   una falla de cache. Aquí usan ApiResponse y comunican la dependencia fallida.
5. El serializer JWT de core importa módulos de identidad de negocio y el helper
   de integridad contiene mensajes de constraints específicos; se excluyeron esos
   acoplamientos.
6. `docs/auth.md` no existe; la documentación está repartida en backend, modules
   y models. Parte describe TOTP local mientras el código actual usa MFA externo.
7. La creación y edición originales incluyen reglas en serializers; el modelo
   RegisteredDevice también contiene procesos. No se copiaron esas ubicaciones
   de lógica a la plantilla.

La extracción conserva el contrato general de las vistas base, pero no promete
equivalencia exacta en esos puntos corregidos ni en las funciones omitidas.
