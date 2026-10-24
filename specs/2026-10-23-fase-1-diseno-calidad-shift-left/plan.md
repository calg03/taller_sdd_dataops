# Fase 1 · Plan de implementación

Estado: aprobado; consultar `evidencia.md` para distinguir implementación local y verificaciones remotas pendientes. Rama: `fase-1-diseno-calidad-shift-left`.

Cada grupo se implementará y revisará en este orden después de aprobar la spec. No se implementa en esta fase la ingesta ni la publicación de clientes.

## 1. Fijar contratos y configuración

1. Crear `config/project.json`: catálogo `workspace`, schema `demo`, umbral 30, edad adulta 18, ubicación del origen y de la referencia. Sin secretos. El umbral se consume desde un solo lugar.
2. Crear `data/reference/countries.csv`: los cinco países y regiones aprobados, con una versión explícita del catálogo de referencia.
3. Crear `requirements.txt`: dependencias mínimas y versiones fijadas de Python para pruebas y conexión SQL; documentar versión de Python en README.
4. Modificar `README.md`: registrar aprobación de la spec, prerrequisitos, nombres reales de grupos de acceso y configuración no secreta. No solicitar ni guardar valores de secrets.

## 2. Implementar calidad local reutilizable

1. Crear `src/clientes_confiables/__init__.py` y `src/clientes_confiables/customer_quality.py`: lectura del contrato, normalización, evaluación de cada regla, banderas, última fila por identidad y clasificación. Sin conexión a Databricks.
2. Crear `scripts/validate_source.py`: ejecutar validación estructural y por filas, calcular el umbral sin redondeo, producir salida sanitizada y código de salida bloqueante cuando corresponda.
3. Definir en `src/clientes_confiables/customer_quality.py` los motivos estables, tipos de resultado y métricas compartidas con el futuro stage 4. No crear una segunda implementación SQL de reglas en esta fase.

## 3. Probar límites y resultados esperados

1. Crear `tests/test_customer_quality.py`: nulos, espacios, países, emails, mayoría de edad, edad inválida, motivos múltiples y selección de última fila, incluida última versión inválida.
2. Crear `tests/fixtures/`: CSV sintéticos válidos, estructuralmente inválidos y con exactamente 30% y más de 30% de rechazos. No reutilizar datos personales del origen en nuevos archivos.
3. Crear `tests/test_validate_source.py`: comprobar salidas, ausencia de datos personales en diagnóstico, umbral y resultado de 21 filas/5 rechazos del CSV sin modificarlo.
4. Comprobar en evaluación local los 20 clientes únicos, 15 candidatos válidos, 16 adultos vigentes y 10 contactables. Estos resultados son pruebas del contrato; no cargan Silver ni Gold.

## 4. Definir el modelo versionado

1. Crear `sql/model/000_schema.sql`: creación/verificación de `workspace.demo`.
2. Crear `sql/model/010_customers_bronze.sql`, `020_countries_reference.sql`, `030_customers_silver.sql` y `040_customers_rejected.sql`: DDL según requerimientos, con parametrización controlada del sufijo de PR.
3. Crear `sql/model/050_customer_contactability_gold.sql`, `060_pipeline_stage_runs.sql` y `070_published_snapshots.sql`: completar las siete tablas, sin insertar clientes ni métricas.
4. Crear `sql/reference/seed_countries.sql`: carga idempotente de la referencia única versionada, sin duplicados ni cambios de fecha innecesarios.
5. Crear `sql/model/080_consumer_views.sql`: vistas vigentes de Silver, contactos adultos contactables y Gold, vinculadas al puntero de publicación del entorno.
6. Crear `sql/model/090_permissions.sql`: permisos por rol y nombres de grupos configurados. Comprobar existencia y permisos antes de aplicar; no dar acceso general como sustituto de una configuración faltante.

## 5. Implementar despliegue y comprobación del modelo

1. Crear `src/clientes_confiables/databricks_connection.py`: conexión con los tres secrets, timeouts, cierre de conexión y errores sin credenciales.
2. Crear `scripts/deploy_model.py`: resolver nombres del entorno, verificar contratos existentes, aplicar DDL en orden y cargar países. No realizar DROP/TRUNCATE ni reemplazar tablas incompatibles.
3. Crear `scripts/validate_model.py`: verificar columnas, tipos, nulabilidad, referencia, vistas, aislamiento y permisos. Falla si algo incumple el contrato.
4. Crear `src/clientes_confiables/stage_audit.py`: consolidar evidencia local de stage 1 y registrar inicio/fin de stage 2 en la tabla de auditoría, con alternativas de evidencia en CI ante falta de conexión.
5. Crear `tests/test_deploy_model.py`: verificar resolución segura de sufijos, orden y manejo de errores con conexión simulada. La evidencia de despliegue real se obtiene en el PR, no se sustituye por estos tests.

## 6. Conectar los dos stages en GitHub Actions

1. Crear `.github/workflows/fase-1.yml`: check `calidad-shift-left` sin secrets ni conexión; después `despliegue-modelo`, dependiente del éxito del primero, con los tres secrets solo en el job autorizado.
2. En ese workflow, usar `__pr_<numero>` para tablas/vistas de PR, concurrencia por PR, timeout y permisos mínimos de GitHub. No ejecutar contribuciones no confiables con secrets mediante `pull_request_target`.
3. En ese workflow, permitir despliegue del modelo base al integrar en `main`, pasando primero shift-left. No agregar todavía cron ni jobs de ingesta/Gold.
4. Conservar resumen agregado de ambos stages aun si fallan; los errores siguen bloqueando los checks. Documentar gestión y limpieza de tablas de PR.

## 7. Verificar y preparar la revisión

1. Ejecutar [validacion.md](validacion.md) y registrar evidencia real por criterio: commit, ejecución de Actions y objetos remotos usados. No marcar cumplido un criterio solo por existir código.
2. Modificar `README.md`: inventario de cada script con finalidad, stage, entradas/salidas, comandos, configuración, errores, repetición segura, permisos y lectura de diagnóstico. Separar lo implementado de lo reservado a Fase 2.
3. Verificar en GitHub la protección de `main` y establecer `calidad-shift-left` y `despliegue-modelo` como checks requeridos una vez existan. Documentar cualquier prerrequisito faltante sin declarar el flujo completo listo.
4. Preparar PR hacia `main` con modelo, reglas, evidencia y limitaciones. Raúl revisa técnica; Patricia, gobierno; Carmen, semántica del KPI. No hacer merge como parte de la implementación: debe ocurrir únicamente tras validación y checks en verde.

## Condición para pasar a Fase 2

Fase 1 integrada y validada; siete tablas y vistas creadas desde código, países cargados, validación temprana operativa y documentación completa. La Fase 2 ampliará el workflow con los cuatro stages restantes, mantendrá las mismas reglas y probará la carga de clientes y la publicación sin duplicados.
