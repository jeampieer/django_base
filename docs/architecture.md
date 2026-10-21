# Arquitectura del Backend

## Patrón

**Arquitectura Modular por Capas con Service Layer.** Organización vertical por
módulo de negocio, con capas internas por responsabilidad. Los modelos Django
representan los datos y conceptos del dominio; las reglas de los casos de uso
viven en services que importan directamente sus propios modelos.

La dirección es entrada HTTP/tarea → service → selector/modelos. Un CRUD simple
usa las vistas base y el ORM sin añadir un service artificial.

## Mapa de módulos

La plantilla incluye `config/`, `core/`, `applications/users/`, `applications/example/`, `requirements/`,
`tools/`, `docs/` y `.github/workflows/`. El módulo de ejemplo tiene estas piezas:

```text
example/
├── apps.py                 registro de policies
├── urls.py                 rutas del módulo
├── policies.py             autorización por rol/modelo
├── tasks.py                adaptador Celery
├── models/                 Label y Entry
├── migrations/             esquema versionado
├── serializers/            contratos de entrada/salida
├── schemas/                metadatos OpenAPI
├── api_views/              adaptadores HTTP y CRUD
├── services/               finalizar una entrada
├── selectors/              estadísticas y resolución de entidades
├── permissions/            autorización por autor/estado
└── tests/                  flujos, service, selector, permisos y tarea
```

`managers/`, `management/commands/`, `public.py` y `admin.py` no existen en el
ejemplo. Las condiciones para crearlos y la lista de piezas posibles se definen
en [app-structure.md](app-structure.md#cuándo-crear-cada-pieza). Ninguna carpeta
opcional se genera vacía.

`users` es el módulo base de identidad: usuario propio con UUID y auditoría,
manager de bootstrap, roles configurables, JWT, gestión de cuentas, sesiones y
eventos de seguridad. Incluye `managers/` porque lo utiliza; no tiene tareas,
comandos propios, firmas, dispositivos ni MFA. Su detalle está en [auth.md](auth.md).

## Responsabilidades

| Capa | Responsabilidad | Nunca |
|---|---|---|
| `models/` | Campos, relaciones, constraints; ORM | Casos de uso, HTTP |
| `serializers/` | Formato de entrada y representación de salida | Queries, decisiones de dominio |
| `schemas/` | Describir endpoints en OpenAPI | Validación de ejecución o acceso a BD |
| `api_views/` | Parsear, resolver, autorizar, invocar, responder | Reglas de negocio, transacciones |
| `services/` | Casos de uso, reglas y transacciones | `request`, respuestas, códigos HTTP |
| `selectors/` | Lecturas complejas, joins, agregados y precarga | Escrituras, efectos secundarios |
| `policies.py` | Acciones, campos y alcance según rol | Mutaciones |
| `permissions/` | Autorización por instancia y estado | Mutaciones |
| `tasks.py` | Validar mensaje, resolver entidades y llamar service | Reglas o escrituras directas |

La auditoría y el borrado lógico genéricos de `BaseModel` son infraestructura
extraída, no decisiones de negocio. La validación de un proceso sigue en el
service aunque también se compruebe en un permiso HTTP: las tareas no pasan
por ese permiso.

## Services y transacciones

Un archivo por caso de uso; clases como `FinalizeEntryService`. Constructor y
`execute` usan argumentos keyword-only y tipado. Los argumentos que representan
entidades llegan resueltos; nunca se recibe un `request` ni un PK para sustituir
una entidad. Los valores escalares del caso de uso sí son argumentos válidos.
Login recibe el usuario resuelto por el adaptador (o `None`) y la credencial;
refresh recibe el usuario resuelto y el token validado por un selector.

**`transaction.atomic` se abre en el service, nunca en la view ni en el modelo.**
El método público que agrupa la escritura define el límite transaccional.
No se habilita `ATOMIC_REQUESTS`. Un CRUD de una escritura usa el comportamiento
normal del ORM; si necesita varias escrituras coordinadas, deja de ser CRUD
simple y pasa a un service. No hay CRUD por lotes en esta extracción.

Las validaciones que dependen del estado se repiten dentro de la transacción.
Si hay competencia por el mismo registro, usar `select_for_update` allí. El
ejemplo bloquea la entrada y la etiqueta antes de validar y guardar.
Los efectos externos posteriores se registran con `transaction.on_commit`;
una transacción de BD no garantiza entrega exactamente una vez a un broker.

Login confirma su transacción de auditoría antes de lanzar el error de
autenticación. Así los intentos fallidos y el bloqueo no se pierden por rollback.
Las tareas validan IDs, resuelven entidades y delegan; si una entidad desapareció,
registran el caso y terminan sin error. Los demás errores no se silencian.

Los services **no son Python puro independiente de Django**: usan ORM y
excepciones DRF. Se prueban **sin HTTP y con base de datos**, sin `APIClient`
ni objetos `request`. Los tests verifican también rollback y concurrencia.

## Lecturas y representación

Crear `selectors/` al aparecer una consulta que cruza modelos, requiere agregados
o concentra una precarga relevante. Las estadísticas del ejemplo cuentan
entradas activas por etiqueta en una consulta. Una obtención simple puede
permanecer en el adaptador; el selector también puede alojar resoluciones
reutilizadas una vez que la carpeta está justificada.

Los endpoints de negocio tienen un serializer de entrada y otro de salida
específicos. El CRUD conserva serializer simple y detail. Los serializers no
ejecutan consultas: se deshabilita la validación implícita de unicidad y se
valida el formato UUID de la FK, dejando unicidad e integridad a la BD. Las
relaciones de salida se precargan antes de serializar. Un test exige cero queries
durante validación y representación. Si una comprobación de existencia debe dar
un error particular, la resuelve el adaptador o el caso de uso según su naturaleza.

`schemas/` tiene una definición comprobable en el origen: decoradores y metadatos
de drf-spectacular. Se conserva para esa función, separada de los serializers
de ejecución. El envoltorio documentado coincide con `ApiResponse`.

## Imports entre módulos

Un módulo consume los `services` o una interfaz `public.py` de otro; **no importa
sus modelos, serializers, vistas, permisos ni selectores internos**. Los imports
relativos están sujetos a la misma regla. `models/` y `managers/` tampoco pueden
llamar services de otro módulo.

Una interfaz pública de lectura puede ofrecer valores o DTOs y llamar a sus
propios selectores; no reexporta modelos ni QuerySets como contrato entre
módulos. Si una interfaz pública recibe identificadores externos, resuelve sus
entidades antes de invocar el service. Las relaciones ORM entre módulos usan
referencias lazy y requieren revisar el acoplamiento del esquema.

**Caso del usuario:** `AUTH_USER_MODEL = "users.User"` se fija antes del primer
`migrate`. Las FK usan `settings.AUTH_USER_MODEL`; la resolución autorizada de
identidad usa `django.contrib.auth.get_user_model()`. Para anotaciones externas
puede usarse `AbstractBaseUser`, sin importar el modelo concreto. Esta referencia
por el contrato de Django está permitida; no habilita importar modelos,
serializers, selectors, permisos ni otros internals de `users` desde otro módulo.
Los casos de uso ajenos siguen entrando por sus services o interfaz pública.
No se añadió una excepción a import-linter: el contrato ya prohíbe esos imports
directos. Las pruebas incluyen explícitamente el límite de `users`.

No se promete extracción automática a microservicios: además de imports, habría
que separar FK, transacciones y contratos. Aquí se hace verificable el límite
de código. `core/` no importa `applications/` ni `config/`.

Los [contratos de imports](../.importlinter) aplican a todos los módulos nuevos
mediante wildcard y un contrato personalizado de import-linter. Las pruebas
crean dos módulos artificiales y comprueban casos permitidos y prohibidos.
Este análisis es estático: no detecta accesos ORM escondidos en strings o
imports dinámicos, que no deben usarse para eludir el límite.

## Referencias y decisiones conscientes

El respaldo principal es el [HackSoft Django Styleguide](https://github.com/HackSoftware/Django-Styleguide):
se adoptan services/selectors, argumentos keyword-only, contratos de entrada y
salida y pruebas de services con BD. Se conserva la decisión local de usar
vistas base para CRUD; no se adopta toda la guía literalmente.

*Architecture Patterns with Python*, de Harry Percival y Bob Gregory, y
*Clean Architecture*, de Robert C. Martin, se citan como alternativas de las que
esta arquitectura se aparta conscientemente. No se introducen repositorios,
puertos/adaptadores ni entidades separadas del ORM.

La implementación del control estático sigue la documentación oficial de
[capas](https://import-linter.readthedocs.io/en/stable/contract_types/layers/) y
[contratos personalizados](https://import-linter.readthedocs.io/en/stable/custom_contract_types/).
