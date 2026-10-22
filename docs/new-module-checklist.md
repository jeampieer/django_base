# Crear un módulo nuevo

- [ ] Definir el caso de uso y su límite; revisar [arquitectura](architecture.md).
- [ ] Crear paquete y `AppConfig`; instalarlo en settings.
- [ ] Añadir solo los modelos necesarios, con `BaseModel`, choices y FK lazy.
- [ ] Generar y versionar la migración junto con el cambio de modelo.
- [ ] Crear serializers con auditoría de solo lectura y sin queries implícitas.
- [ ] Elegir CRUD base o service keyword-only con `transaction.atomic`.
- [ ] Crear selector solo ante una lectura compleja; permiso de objeto solo si aplica.
- [ ] Registrar policies en `ready()` y añadir rutas plurales con UUID y OpenAPI.
- [ ] Referenciar usuarios con `settings.AUTH_USER_MODEL` en FK; resolverlos con `get_user_model()`, sin imports de internals.
- [ ] Declarar la capacidad de la policy y asignarla a roles en `USER_ROLES`; no basarse en `is_staff`.
- [ ] Añadir permisos por objeto cuando aplique y revalidarlos en el service; probar el límite de imports con `users`.
- [ ] Si requiere Celery/comando/interfaz pública, crear únicamente esa pieza.
- [ ] Incluir tests de comportamiento para todo código nuevo del módulo: flujos, reglas, errores y rollback;
  evitar imports de modelos ajenos.
- [ ] Ejecutar flake8, `lint-imports`, checks, `makemigrations --check`, OpenAPI y
  `pytest --cov --cov-report=term-missing` con PostgreSQL.
- [ ] Revisar las líneas sin cubrir del módulo y cumplir el mínimo global de `.coveragerc`;
  no añadir exclusiones ni tests artificiales para aumentar el porcentaje.
