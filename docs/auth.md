# Usuarios, autenticación y autorización

## Modelo y primera migración

La plantilla define `AUTH_USER_MODEL = "users.User"` antes de la primera
migración. `users/migrations/0001_initial.py` crea User, UserSession y
SecurityEvent; la migración de `example` depende del usuario configurable.
Se verifica sobre una BD vacía. No se ejecuta una conversión desde `auth.User`.

**Si ya migraste una copia anterior de la plantilla con otro usuario, no basta
con cambiar el setting ni ejecutar migrate.** En un proyecto nuevo sin datos,
usa una BD vacía. Con datos existentes se necesita un plan específico de
migración de tablas, FK, historial y datos; esta plantilla no lo ejecuta.
Referencia: [Django: cambio de usuario a mitad de proyecto](https://docs.djangoproject.com/en/5.2/topics/auth/customizing/#changing-to-a-custom-user-model-mid-project).

User hereda AbstractBaseUser, PermissionsMixin y BaseModel: UUID, username de
login, email único, first_name, last_name, un role, estado y auditoría. Incluye
last_login, last_password_change, failed_login_attempts y locked_until por los
casos de seguridad acordados. El email usa la unicidad de Django/BD y normaliza
el dominio; no se añade una regla nueva de unicidad insensible a mayúsculas.

No hay campos de empresa, área, documentos, avatar ni firmas. UserSession y
SecurityEvent son registros de auditoría con `models.Model`, accesibles por API
solo para lectura. No almacenan contraseñas ni tokens en sus datos de contexto.

## Catálogo configurable de roles

No hay tabla Role: se conserva un campo `User.role`. Los códigos, etiquetas,
jerarquía y capacidades están en `config/settings/base.py`, mediante USER_ROLES.
Los dos códigos incluidos son **ejemplos ficticios**, reemplazables:

```python
USER_ROLES = {
    "MANAGER": {"label": "Gestor (ejemplo)", "level": 10,
                "permissions": ["users.manage", "example.write"]},
    "MEMBER": {"label": "Miembro (ejemplo)", "level": 20, "permissions": []},
}
USER_DEFAULT_ROLE = "MEMBER"
USER_SUPERUSER_ROLE = "MANAGER"
```

Menor `level` significa mayor jerarquía; solo se gestionan niveles estrictamente
inferiores. `USER_DEFAULT_ROLE` se asigna a nuevas cuentas normales;
`USER_SUPERUSER_ROLE` es el rol inicial del comando createsuperuser. Los códigos
no están fijados en modelos ni policies. `choices` y default usan callables que
leen settings; agregar un código no genera una migración de estructura. Renombrar
o eliminar un código ya persistido sí requiere migrar los usuarios afectados.

Las capacidades son contratos entre configuración y policies:

| Capacidad | Efecto |
|---|---|
| `users.manage` | Crear y gestionar usuarios de roles inferiores; no superusuarios |
| `example.write` | Escribir recursos del ejemplo y finalizar una entrada propia |
| Sin esas capacidades | Perfil/contraseña propios; lectura de recursos del ejemplo |

Una policy declara `capability`, `privileged_access`, `authenticated_access` y
`superuser_access`. Los perfiles contienen CreatePolicy/ReadPolicy/UpdatePolicy
y delete, manteniendo el registry y PermissionManager del framework original.
Los roles desconocidos y modelos sin policy no obtienen acceso. Los checks
validan catálogo, defaults, configuración de bloqueo y campos de las policies.

## Matriz y permisos por objeto

| Actor | Gestión permitida |
|---|---|
| Superusuario activo | Todas las cuentas, incluidos otros superusuarios |
| Gestor con `users.manage` | Crear/asignar roles inferiores y gestionar esas cuentas; su propio perfil/contraseña |
| Miembro | Consultar su propio perfil, sesiones y eventos; editar nombre/email y cambiar su contraseña |

Los gestores no pueden gestionar pares ni asignar un rol de su mismo nivel o
superior. `is_staff` se conserva como bandera técnica de Django; no concede
permisos de API. `is_superuser` prevalece sobre el rol. La API nunca permite
escribir is_staff, is_superuser, groups ni user_permissions. Los superusuarios
se crean con el comando de bootstrap.

`UserPolicy` limita acciones, campos y queryset. `CanEditUser` y `CanManageUser`
comprueban objetos; los services vuelven a autorizar con el actor y destinatario
releídos bajo bloqueo. Los predicados puros compartidos viven en
`permissions/rules.py`. Acceder a un usuario fuera del queryset devuelve 404.

No se permite autodesactivación ni perder el último superusuario activo. El
service de estado bloquea actores, destinatarios y superusuarios activos en un
orden común; el test de PostgreSQL verifica dos desactivaciones cruzadas
concurrentes. DELETE solo desactiva; activate/deactivate son acciones explícitas
e idempotentes. No existe eliminación física por API.

## Endpoints

Todos llevan prefijo `/api/v1/`. Salvo login/refresh/verify, requieren JWT.

| Método | Ruta | Contrato |
|---|---|---|
| POST | `auth/token/` | username/password → access, refresh y perfil |
| POST | `auth/token/refresh/` | refresh → access nuevo, sin rotación |
| POST | `auth/token/verify/` | token → valid; verifica firma/vigencia y blacklist de refresh |
| GET | `auth/me/` | Perfil derivado del JWT; no acepta ID |
| POST | `auth/logout/` | Revoca refresh de todas las sesiones del usuario |
| GET / POST | `users/` | Lista paginada / creación mediante service |
| POST | `users/filter/` | Filtro de lectura con el mismo alcance por rol |
| GET / PUT / PATCH / DELETE | `users/<uuid>/` | Leer / actualizar perfil / desactivar |
| POST | `users/change-password/` | Contraseña propia; requiere current_password y new_password |
| POST | `users/<uuid>/change-password/` | Reseteo autorizado; para la propia cuenta también exige contraseña actual |
| POST | `users/<uuid>/change-role/` | Asignación autorizada de role |
| POST | `users/<uuid>/activate/` | Activa, cuerpo vacío |
| POST | `users/<uuid>/deactivate/` | Desactiva, cuerpo vacío |
| GET | `users/<uuid>/sessions/` | Intentos de autenticación paginados |
| GET | `users/<uuid>/security-events/` | Eventos como actor o destinatario, paginados |

Creación recibe username, email, first_name, last_name, password y role opcional.
El perfil solo admite sus campos autorizados; rol, contraseña y estado requieren
su caso de uso. Los serializers de entrada y salida de procesos están separados,
no consultan BD y no escriben modelos. Campos desconocidos/no autorizados del
CRUD se ignoran según el comportamiento del framework.

## Contraseñas, auditoría y JWT

Los services validan fortaleza mediante Django, guardan hashes y agrupan la
escritura con el evento en una transacción. Cambiar la propia contraseña exige
la actual y una nueva distinta. Un gestor puede resetear la de un usuario de
rol inferior sin conocerla. Cambiar contraseña y desactivar revocan todos los
refresh del destinatario. Logout además marca las sesiones exitosas abiertas
con logout_at; la desactivación hace lo mismo.

Se conservan access de una hora y refresh de siete días, sin rotación. La
blacklist usa la [app existente de SimpleJWT](https://django-rest-framework-simplejwt.readthedocs.io/en/stable/blacklist_app.html).
Logout y cambio de contraseña revocan refresh; los access ya emitidos conservan
su vigencia. Una cuenta desactivada no puede usar access ni refresh porque se
comprueba el estado del usuario. Un cambio de rol afecta inmediatamente a las
autorizaciones de access existentes: la identidad se carga de la BD en cada
request; no se guarda el rol en el token. Verify valida el token, no sustituye
la comprobación de usuario y permisos de los endpoints protegidos.

Los intentos de login válidos en formato siempre crean UserSession, incluidos
usuario inexistente (user=null), cuenta inactiva y cuenta bloqueada. Solo una
contraseña incorrecta de cuenta activa incrementa el contador. Los parámetros
USER_LOCKOUT_THRESHOLD y USER_LOCKOUT_SECONDS son configurables (ejemplo: 10 y
1800). Al expirar el bloqueo empieza una nueva ventana; un login exitoso limpia
el contador y actualiza last_login. Los errores públicos son genéricos.

Login confirma la transacción del intento antes de lanzar AuthenticationFailed;
la view no contiene transacciones ni reglas de autenticación. No habilitar
ATOMIC_REQUESTS ni envolver el login en otra transacción que revierta su auditoría.
Los registros sin usuario no aparecen en una ruta por UUID; se consultan en BD.
UserSession representa intentos de autenticación, no un inventario exacto de
tokens todavía válidos.

## Panel administrativo

`/admin/` ofrece la gestión interna con formularios nativos; requiere usuario
activo, staff y superusuario con rol configurado. Comparte autenticación,
bloqueo y auditoría con la API sin emitir JWT. El motivo `ADMIN_ACCESS_DENIED`
identifica credenciales válidas sin acceso al panel. Los intentos de acceso y
eventos se consultan en solo lectura.

Los cambios combinados de perfil, rol y estado se coordinan en una transacción
del service. Contraseñas y finalización usan sus casos de uso específicos.
Logout, cambio de contraseña y desactivación revocan también sesiones web;
el cambio propio de contraseña cierra la sesión actual. La cookie del admin
no autentica la API. Ver [admin.md](admin.md) para operaciones y despliegue.

## Conexión con otros módulos

FK: `settings.AUTH_USER_MODEL`. Resolución de identidad: `get_user_model()` de
Django. Nunca importar `applications.users.models` ni sus internals desde otro
módulo. Para ejecutar operaciones de usuarios se consumen sus services con
entidades resueltas. No fue necesaria una excepción de import-linter; las
pruebas verifican los imports permitidos y prohibidos de `users`.

`example` utiliza las mismas policies/capacidades y el usuario UUID. Su tarea
recibe ambos IDs como texto UUID; si falta entrada o actor, registra un log y
termina sin error. No contiene reglas de negocio ni transacciones.
