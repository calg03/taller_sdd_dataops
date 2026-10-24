# Fase 1 · Evidencia de implementación

Fecha local: 2026-10-23, America/Lima. Rama: `fase-1-diseno-calidad-shift-left`.

## Comprobado localmente

- Python 3.12.7: `python -m unittest discover -s tests -v`, **25 tests aprobados**. Incluyen reglas, estructura, bordes, selección de última versión, denominador, CLI sanitizado, despliegue y creación idempotente de grupos con conexiones simuladas.
- `python scripts/validate_source.py`: SUCCESS; 21 filas, 20 identidades, 5 rechazadas, 23,809523…%, 1 versión desplazada, 15 candidatos válidos, 2 menores válidos, 16 adultos vigentes, 10 contactables. Resultado agregado guardado en `artifacts/quality.json`, ignorado por Git.
- YAML leído con PyYAML 6.0.3: dos jobs, `despliegue-modelo` depende de `calidad-shift-left`.
- Compilación de scripts, módulos y tests: sin errores de sintaxis.
- `git diff --check`: sin errores de espacios. Fuente `data/source/customers.csv` sin modificaciones.
- Primera ejecución de `python scripts/deploy_model.py --pr-number 123`: fallo esperado `ACCESS_GROUPS_NOT_CONFIGURED` antes de conectarse. Después, el usuario autorizó crear los grupos inexistentes: se configuraron cuatro nombres y se añadió aprovisionamiento SCIM. Sin secrets locales, la nueva ejecución falla con `MISSING_DATABRICKS_SECRETS`. No se han desplegado tablas ni creado grupos remotos desde esta sesión local.

## Relación con validacion.md

| Criterios | Evidencia disponible | Estado |
| --- | --- | --- |
| V01–V10 | Pruebas locales y validador; los casos cubiertos están en `tests/` | Comprobación local disponible; confirmar también ejecución en Actions. |
| V11 | El validador y tests corren sin importar el conector ni tener variables Databricks | Local disponible; falta evidencia del job real. |
| V12–V15 | DDL, contrato y ejecutores implementados | Pendiente Databricks: metadata, referencia, tablas vacías y segunda ejecución real. |
| V16–V17 | Pruebas con conexión simulada de incompatibilidad y aislamiento | Falta comprobación real en entorno desechable / PR. |
| V18 | Vistas definidas con filtros por foto y contactabilidad | Pendiente prueba remota de vistas y permisos. |
| V19 | Creación idempotente de grupos de cuenta, aplicación de permisos e inspección de grants amplios conocidos | Pendiente ejecución remota y pruebas con identidades reales; inspección de grants no sustituye estas pruebas. |
| V20 | Registro por run/stage/intento probado con conexión simulada | Pendiente persistencia y falla de conexión reales. |
| V21–V22 | Workflow creado y estructura YAML revisada | Pendiente ejecución de Actions y verificación de protección de `main`. |
| V23 | README con inventario completo y PR preparado | Pendiente revisión final de responsables y completar configuración real. |

Las casillas de aceptación permanecen pendientes hasta obtener la evidencia completa por stage. No se declara cerrada la Fase 1 ni habilitada la Fase 2 solo por pasar pruebas locales.

## Información y acceso faltantes

1. Ejecutar aprovisionamiento de los cuatro grupos de cuenta configurados, por autorización del usuario; requiere privilegio administrativo. No hay navegador conectado y la creación remota aún no está comprobada. No se agregan miembros sin conocer sus identidades.
2. Tres secrets configurados en GitHub y una identidad técnica con permisos de despliegue. En esta sesión no hay variables Databricks disponibles; nunca enviar sus valores al chat.
3. Corrida del PR con ambos checks y revisión de reglas de `main`. La sesión local de `gh` está vencida; el conector GitHub sí tiene acceso al repositorio.

La rama fue subida a `origin` con los commits `a40dbf0` y `a6db9e8`. Al intentar crear el PR en borrador, el conector devolvió **HTTP 403: Resource not accessible by integration**. No se creó el PR ni se ejecutaron sus checks; no se consideran creados los grupos remotos. La subida Git sí fue exitosa. Para continuar, habilitar creación de PR en la integración o abrir [la comparación de la rama](https://github.com/calg03/taller_sdd_dataops/compare/main...fase-1-diseno-calidad-shift-left?expand=1) y crear el PR en borrador. No hacer merge hasta obtener las verificaciones pendientes.

## Límites de la entrega

Solo modelo, referencia y stages 1–2. No se cargan clientes ni métricas; no hay publicación semanal, alertas operativas ni limpieza automática de retención. Esos componentes siguen planificados en Fase 2. No se hace merge ni se presenta el despliegue remoto como aprobado.
