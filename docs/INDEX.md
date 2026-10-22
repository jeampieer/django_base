# Plantilla backend Django/DRF — Documentación

Índice de la documentación de la plantilla, agrupada por tema.
«Cuándo consultarlo» indica cuándo volver a cada guía; los agentes deben leer
íntegramente la documentación antes de planificar o modificar el proyecto.

## Arquitectura y convenciones

| Documento | Contenido | Cuándo consultarlo |
| --- | --- | --- |
| [Arquitectura](architecture.md) | Patrón modular, responsabilidades, services, transacciones, selectors y límites de imports. | Al diseñar un cambio o revisar sus dependencias. |
| [Estructura de aplicaciones](app-structure.md) | Carpetas, modelos, serializers, vistas, schemas, policies, tareas y convenciones autoritativas. | Al crear o modificar cualquier pieza de un módulo. |

---

## Usuarios, autenticación y autorización

| Documento | Contenido | Cuándo consultarlo |
| --- | --- | --- |
| [Usuarios y autenticación](auth.md) | Usuario configurable, roles, capacidades, permisos por objeto, JWT, sesiones y auditoría. | Antes de migrar por primera vez o cambiar identidad, acceso y seguridad. |

---

## Desarrollo de módulos

| Documento | Contenido | Cuándo consultarlo |
| --- | --- | --- |
| [Checklist de un módulo nuevo](new-module-checklist.md) | Pasos para registrar una app, implementar sus capas, versionar migraciones y verificarla. | Al incorporar un módulo y antes de darlo por terminado. |

---

## Framework y verificación

| Documento | Contenido | Cuándo consultarlo |
| --- | --- | --- |
| [Extracción del framework](core-extraction.md) | Componentes conservados, adaptaciones, exclusiones y hallazgos históricos del código de origen. | Al evaluar el alcance del core o sus diferencias respecto del origen. |
| [Verificación](verification.md) | Comprobaciones realizadas, resultados históricos, cobertura funcional y límites de ejecución. | Al preparar la validación de una entrega; contrastar siempre con los checks actuales de CI. |
