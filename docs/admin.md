# Django Admin

El panel interno está disponible en `/admin/` en todos los entornos. Usa los
formularios, widgets y estilos nativos de Django y `BaseModelAdmin`, adaptado
del patrón de Iperc. No requiere historial ni importación/exportación.

## Arranque y acceso

Con `.env` configurado y una base propia del proyecto:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Acceder a `http://127.0.0.1:8000/admin/`. Se exige una cuenta activa con
`is_staff=True`, `is_superuser=True` y un rol configurado. Un rol de negocio
por sí solo no da acceso. Los superusuarios se crean con `createsuperuser`.

El sitio registra explícitamente cinco modelos desde `config/admin.py`; no
habilita editores de grupos, permisos ni tokens de terceros. La API sigue
aceptando solo JWT: una cookie administrativa no autentica endpoints REST.

El backend del admin reutiliza `AuthenticateUserService`: conserva intentos,
bloqueo configurable, limpieza de contadores y último acceso, sin emitir JWT.
Un acceso con credenciales válidas sin privilegios registra
`ADMIN_ACCESS_DENIED`. Los errores públicos son genéricos. La API conserva el
contrato y la transacción de `LoginService`.

Logout, cambio de contraseña y desactivación revocan las sesiones web del
usuario además de los refresh JWT. El backend de sesiones de BD inspecciona
las sesiones vigentes por `_auth_user_id`; un despliegue con muchas sesiones
puede necesitar un índice explícito usuario-sesión. Un cambio propio de
contraseña exige la actual y cierra también la sesión del panel. Los access
JWT mantienen la vigencia descrita en [auth.md](auth.md).

## Modelos y operaciones

| Modelo | Operaciones |
| --- | --- |
| Usuario | Crear, editar perfil/rol/estado y cambiar contraseña mediante services |
| Etiqueta | CRUD simple auditado; activar/desactivar mediante `is_active` |
| Entrada | CRUD simple auditado y finalización individual mediante service |
| Intento de autenticación | Listado y detalle de solo lectura |
| Evento de seguridad | Listado y detalle de solo lectura |

No hay eliminación física ni acciones masivas. Los privilegios técnicos,
grupos, permisos y auditoría no se editan; un POST manipulado no puede
concederlos. `UpdateUserFromAdminService` coordina perfil, rol y estado con
los services existentes en una única transacción. Ante un fallo se revierten
todos los cambios y eventos del envío. La protección contra autodesactivación
y pérdida del último superusuario sigue en el service.

Estado de finalización, resumen y fecha de una entrada son de solo lectura.
«Finalizar entrada» abre un formulario nativo y llama a `FinalizeEntryService`:
incluso un superusuario debe ser autor y cumplir las validaciones de estado y
etiqueta activa.

## Base reutilizable

```python
from django.contrib import admin
from core.admin import BaseModelAdmin
from .models import Label


@admin.register(Label)
class LabelAdmin(BaseModelAdmin):
    list_display = ("name", "format_is_active", "format_created", "format_created_by")
    list_filter = ("is_active", "created")
    search_fields = ("name",)
    fieldsets = (("Información", {"fields": ("name", "is_active")}),)
```

`BaseModelAdmin` aporta identificador, fechas y actores de solo lectura; una
única sección «Auditoría» colapsable sin mutar los fieldsets; y guardado CRUD
mediante `save_with_user`, siguiendo la auditoría de `BaseModel`.

Sus métodos públicos son `format_created`, `format_modified`,
`format_created_by`, `format_updated_by` y `format_is_active`. Las fechas usan
la zona activa y los valores HTML se escapan.

Un admin con reglas delega desde `save_model` a un service, sin coordinar allí
varias escrituras. Para cambios combinados usa un service coordinador. No se
guardan relaciones ni inlines fuera del límite del service.
`ReadOnlyModelAdmin` es la base de registros que no admiten mutación.

El adaptador reutiliza `_changeform_view` de Django **5.2.8**, omitiendo únicamente
el `atomic` exterior de `changeform_view`. Las transacciones de negocio siguen
perteneciendo al service. Los errores se reinyectan en el formulario sin
reintentar escrituras. Al actualizar Django, revisar este punto y sus tests.
Los registros técnicos `LogEntry` y las sesiones son infraestructura Django;
no sustituyen `SecurityEvent`. Los logs del admin se escriben tras el service.

Para nuevas apps, registrar sus clases explícitamente desde el composition root
y probar el flujo administrativo. Los contratos de capas incluyen admin,
formularios y backends. `core/admin` no importa aplicaciones ni configuración.

## Producción

```bash
DJANGO_SETTINGS_MODULE=config.settings.production python manage.py migrate
DJANGO_SETTINGS_MODULE=config.settings.production python manage.py collectstatic --noinput
```

Servir `/static/` desde `STATIC_ROOT` (`staticfiles/`) mediante el servidor web
del despliegue. Gunicorn no sirve estos archivos automáticamente. El directorio
recopilado se excluye de Git. Se mantienen las cookies seguras de producción;
el acceso al panel debe realizarse mediante HTTPS.
