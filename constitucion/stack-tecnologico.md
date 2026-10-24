# Stack tecnológico y principios de implementación

## Plataforma y portabilidad

Implementación inicial: **Databricks SQL Warehouse**, catálogo `workspace`, schema `demo`; nombres completos `workspace.demo.<tabla>`. SQL expresa las transformaciones y Python coordina lectura, validación y ejecución. GitHub mantiene el código; GitHub Actions orquesta CI/CD y la ejecución semanal.

Las reglas de negocio y sus validaciones deben poder trasladarse a otra plataforma. Se separan de la conexión, autenticación y particularidades del motor. Ninguna herramienta es obligatoria como principio de arquitectura: importa la práctica que cubre. Una migración requiere actualizar esta constitución y sus adaptadores, conservando los criterios de aceptación.

| Herramienta inicial | Práctica cubierta | Alternativa equivalente para esa práctica |
| --- | --- | --- |
| Databricks SQL Warehouse | Cómputo SQL y persistencia de tablas analíticas | Snowflake o PostgreSQL, adaptando dialecto y despliegue. |
| Git | Historial y ramas del código | Mercurial. |
| GitHub y Pull Requests | Revisión, colaboración y controles de integración | GitLab y Merge Requests. |
| GitHub Actions | Orquestación programada y CI/CD por stages | GitLab CI/CD. |
| GitHub Secrets | Inyección protegida de credenciales | Variables protegidas de GitLab CI/CD o un gestor como HashiCorp Vault. |
| SQL | Modelado y transformación declarativa | Python con un motor de procesamiento, manteniendo las mismas reglas. |
| Python | Lectura, validación y coordinación | Java con librerías de CSV y acceso al motor SQL. |
| Notificaciones y registros de GitHub Actions | Alertas y evidencias operativas | Notificaciones y registros de GitLab CI/CD. |

Estas alternativas cubren prácticas equivalentes; no se promete sustitución sin adaptar código.

## Configuración y secretos

Solo tres secrets de GitHub para conectar con Databricks:

| Secret | Uso |
| --- | --- |
| `DATABRICKS_HOST` | Host del workspace, según el formato del README. |
| `DATABRICKS_HTTP_PATH` | Ruta de conexión del SQL Warehouse. |
| `DATABRICKS_TOKEN` | Credencial de autenticación con permisos mínimos. |

No se guardan credenciales en código, CSV, documentación, artefactos ni logs. Catálogo, schema, horarios y umbrales son configuración no secreta versionada. No se necesitan credenciales adicionales para alertas: se utilizan las notificaciones de GitHub y su configuración de destinatarios.

Al terminar las dos fases, el repositorio debe ejecutar el flujo completo sin editar scripts, una vez cumplidos los prerrequisitos de cuenta, warehouse disponible, permisos, protección de ramas y configuración de los tres secrets. El catálogo `workspace` es el contexto existente; el schema `demo` y todas las tablas se crean o verifican desde código versionado, nunca manualmente.

## Arquitectura y modelo lógico

- **Foto de origen:** exportación completa del CRM, identificada por su contenido y fecha de procesamiento.
- **Cliente / versión:** `customer_id` es la identidad de negocio. La última posición de una identidad en el CSV determina la versión vigente de esa foto; no se interpreta como fecha real de modificación del CRM.
- **País:** código de dos letras, nombre y región. Un país tiene muchos clientes válidos; cada versión válida de cliente pertenece a un país de referencia.
- **Rechazo:** fila con uno o más errores obligatorios, conservada con todos sus motivos y su vínculo al origen.
- **Métrica:** agregación de la foto vigente por país, además del total global. No contiene emails ni detalles identificables de clientes.
- **Ejecución y stage:** una ejecución tiene varios stages y queda vinculada a la foto, versiones, rechazos y métricas que procesa.

Bronze conserva todas las filas crudas, incluidas las versiones anteriores dentro de un archivo. Silver conserva versiones válidas históricas y permite seleccionar la foto publicada vigente. Gold conserva métricas por foto publicada. Los rechazados se almacenan aparte. Retención: seis meses; la limpieza debe respetar las relaciones de trazabilidad y registrarse.

## Modelo físico de referencia

Tipos expresados para Databricks SQL. Todas las tablas siguientes pertenecen a `workspace.demo`; las specs detallarán DDL, migraciones y validaciones de claves. Las claves y relaciones descritas son contratos lógicos que el pipeline debe comprobar, sin depender de que el motor las imponga.

Columnas de trazabilidad comunes a tablas de datos procesados: `snapshot_id STRING` (identificador estable del contenido de origen), `run_id STRING` (ejecución que escribió el dato) y `loaded_at TIMESTAMP` (UTC). La presentación del horario de negocio usa `America/Lima`.

| Tabla | Grano / clave lógica | Columnas de negocio y derivadas |
| --- | --- | --- |
| `customers_bronze` | Una fila del CSV por foto; `(snapshot_id, source_row_number)` | `source_row_number BIGINT`, `source_file STRING`, `customer_id STRING`, `name STRING`, `age STRING`, `country STRING`, `email STRING`, más trazabilidad común. Todos los campos del origen se preservan crudos. |
| `countries_reference` | Un código; `country_code` | `country_code STRING`, `country_name STRING`, `region STRING`, `reference_version STRING`, `run_id STRING`, `loaded_at TIMESTAMP`. Contenido inicial versionado: PE/Perú, CL/Chile, CO/Colombia, AR/Argentina en Sudamérica; MX/México en Norteamérica. |
| `customers_silver` | Una versión válida seleccionada por cliente y foto; `(snapshot_id, customer_id)` | `customer_id STRING`, `name STRING`, `age INT`, `country_code STRING`, `email STRING` nullable, `is_adult BOOLEAN`, `has_valid_email BOOLEAN`, `is_contactable BOOLEAN`, `source_row_number BIGINT`, más trazabilidad común. |
| `customers_rejected` | Una fila rechazada de origen; `(snapshot_id, source_row_number)` | Campos crudos `customer_id`, `name`, `age`, `country`, `email` como `STRING`; `source_row_number BIGINT`, `source_file STRING`, `rejection_reasons ARRAY<STRING>`, más trazabilidad común. |
| `customer_contactability_gold` | Una agregación por foto y ámbito; `(snapshot_id, aggregation_level, country_group)` | `aggregation_level STRING` (país o global), `country_group STRING` (código o grupo técnico), `country_code STRING` nullable, `country_name STRING`, `region STRING` nullable, `adult_customers BIGINT`, `contactable_adults BIGINT`, `non_contactable_adults BIGINT`, `contactable_pct DECIMAL(7,4)` nullable, `published_at TIMESTAMP`, más trazabilidad común. |
| `pipeline_stage_runs` | Un intento de un stage; `(run_id, stage_name, attempt_number)` | `run_id STRING`, `snapshot_id STRING` nullable, `stage_name STRING`, `attempt_number INT`, `status STRING`, `started_at TIMESTAMP`, `finished_at TIMESTAMP`, `input_rows BIGINT`, `output_rows BIGINT`, `rejected_rows BIGINT`, `rejection_pct DECIMAL(7,4)`, `error_code STRING`, `error_summary STRING`, `commit_sha STRING`, `environment STRING`. |
| `published_snapshots` | Publicación válida por entorno | `environment STRING`, `snapshot_id STRING`, `run_id STRING`, `published_at TIMESTAMP`, `source_file STRING`. Permite identificar la última foto completa válida sin recurrir a la mayor fecha de carga parcial. |

La vista vigente de Silver se obtiene a partir de `published_snapshots`, sin contar versiones históricas en el KPI. Las vistas y permisos de consumo también se definen desde código. No se crea todavía ningún DDL ni script como parte de esta constitución.

## Reglas de calidad y semántica del KPI

1. Estructura esperada: exactamente las cinco columnas de origen, sin cabeceras duplicadas; CSV legible y filas con estructura consistente. Los campos crudos se leen como texto y se validan sus tipos explícitamente.
2. Identificador no vacío; nombre no vacío después de quitar espacios para validar; edad interpretable como entero no negativo; país obligatorio y presente en la referencia. No se fija un límite superior de edad adicional: el foco de negocio es distinguir adultez desde 18 años.
3. Email vacío o con formato inválido **no es motivo de rechazo**. El cliente válido se conserva en Silver con `has_valid_email = false` e `is_contactable = false`. La spec define y prueba el criterio exacto de formato; no equivale a verificar un buzón real.
4. `is_adult = age >= 18`; `is_contactable = is_adult AND has_valid_email` en Silver, donde ya se cumplieron las reglas obligatorias. Los menores válidos permanecen en Silver, pero no se incluyen en la salida de contactos ni en el KPI adulto.
5. Última fila por `customer_id` como versión seleccionada. Las filas anteriores permanecen en Bronze y no incrementan el número de clientes del KPI. Una fila con errores obligatorios se guarda en rechazados con todos los motivos, aunque sea una versión anterior. No se recupera una versión anterior para ocultar que la última es inválida.
6. El porcentaje de rechazos se calcula como `100 × filas rechazadas / filas de datos del CSV`, excluyendo la cabecera y contando cada fila rechazada una sola vez aunque tenga varios motivos. Las versiones anteriores válidas no son errores ni rechazos. Con **más de 30%** el stage falla; exactamente 30% se acepta. Un archivo sin filas no se publica como una foto válida. El umbral fue actualizado de 15% a 30% por aprobación del responsable del proyecto al preparar la spec de la Fase 1.
7. El denominador adulto de Gold sigue la definición de `mision.md`: última versión del origen por cliente identificable, incluidos adultos rechazados. Por ello Gold combina agregados de evaluación de Bronze con adultos contactables de Silver; no se limita a contar filas de Silver. Los rechazados no se copian como registros limpios. Los adultos sin país válido se agregan en un grupo explícito separado de los países de referencia.

## Pipeline por stages y comportamiento ante fallas

| Orden | Stage | Contrato |
| --- | --- | --- |
| 1 | Calidad shift-left | En cada PR, antes de conectarse a Databricks, validar estructura, tipos y reglas del CSV. Bloquear errores estructurales y rechazos superiores a 30%; reportar defectos tolerados y emails no contactables sin exponer datos personales. Aplicar las mismas reglas que en el stage 4. |
| 2 | Despliegue del modelo | Crear o actualizar schema, tablas, referencia, vistas y permisos desde código versionado. Migraciones controladas y repetibles. |
| 3 | Ingesta Bronze | Conservar la foto cruda, posición de filas, identificador de contenido y ejecución; no modificar el CSV. |
| 4 | Calidad de datos | Evaluar filas, guardar rechazados con motivos y preparar Silver válido. Si supera 30%, fallar y no publicar Silver/Gold nuevos. Conservar Bronze, rechazados y evidencias. |
| 5 | Gold | Calcular métricas globales y por país; validar reconciliación y ausencia de datos personales. Publicar la foto completa solo después de las validaciones obligatorias. |
| 6 | Monitoreo | Consolidar resultados y avisar fallas o retrasos a Andrés antes de que Marketing use la salida. Debe ejecutarse también cuando un stage previo falle. |

Monitoreo es además transversal: **cada stage** registra inicio, fin, estado, conteos y error sanitizado. El registro inicial del stage 1 se conserva en GitHub Actions porque todavía no puede tocar Databricks; se consolida en la tabla de ejecución cuando exista conexión y modelo. Si eso no es posible, la evidencia permanece en GitHub y la ejecución falla visiblemente, sin aparentar éxito.

Errores de estructura detienen el flujo antes de Databricks; esos datos no pueden persistirse como rechazados remotos en esa ejecución. Si la calidad de filas supera el umbral en el PR, se conserva el diagnóstico sin datos personales en CI y se bloquean los stages posteriores. Cuando una falla se detecte tras la ingesta, se preservan Bronze y rechazados. Así se respeta la barrera shift-left sin prometer ingesta de una ejecución bloqueada antes de conectarse.

Las tablas de trabajo se preparan sin sustituir la foto publicada. Ante fallo se mantiene la última Silver/Gold válida, indicando su fecha y estado desactualizado; si no existe publicación previa, se informa que no hay datos publicados. El stage de monitoreo no debe convertir una ejecución fallida en un check verde.

## Ejecución semanal, idempotencia y ramas

- Programación cada lunes con origen disponible a las 07:00 de Lima y objetivo de publicación antes de las 08:00. Registrar frescura y avisar a Andrés si falta el archivo, falla un stage o no se llega al horario. Configurar suscripciones de GitHub; no implementar envío de campañas.
- Raúl / Ingeniería revisa los rechazos con Patricia / Gobierno; las correcciones se realizan en el CRM y llegan en otra exportación.
- Una foto completa reemplaza el conjunto vigente al publicarse, incluyendo desapariciones de clientes, mientras las fotos anteriores se conservan durante seis meses.
- Reprocesar el mismo contenido no duplica filas de negocio ni métricas. El identificador de foto es estable; cada intento tiene su propio `run_id` y evidencia. La spec debe resolver concurrencia y selección determinista de la publicación.
- `main` protegida: sin cambios directos; cada fase tiene rama y PR propios. El merge requiere todos los checks obligatorios disponibles en esa fase en verde.
- Fase 1 exige shift-left y despliegue/validación del modelo. Desde fase 2 se exigen los seis stages completos; un stage omitido o fallido no satisface la condición.
- Validación de PR en tablas separadas dentro de `workspace.demo`, con sufijos por PR definidos en la spec; no modifica tablas publicadas de la ejecución programada. Mismo contrato y reglas, con separación de permisos y limpieza de pruebas.

## Gobierno, acceso y entrega ejecutable

| Rol | Acceso autorizado |
| --- | --- |
| Ingeniería y Gobierno | Bronze, Silver y rechazados con emails, bajo permisos restringidos; diagnóstico y corrección del origen. |
| Marketing autorizado | Salida restringida de clientes adultos contactables y email necesario para su trabajo. Sin acceso general a crudos o rechazados. |
| BI | Gold agregado, con nombres de países y regiones; sin emails ni filas identificables de cliente. |
| Identidad técnica del pipeline | Solo permisos necesarios para despliegue y proceso dentro del ámbito aprobado. |

No colocar emails ni muestras de filas en logs, alertas o artefactos de PR. Los datos crudos y rechazados requieren el mismo cuidado que Silver. Durante los seis meses de retención se mantienen trazabilidad y controles; la política abarca también copias de prueba y artefactos. Versionar un dato personal en Git no permite retirarlo simplemente borrando la versión actual: no incorporar nuevas exportaciones personales al historial; la implementación debe documentar el tratamiento del CSV de ejemplo y la entrega de exportaciones operativas.

El README final debe documentar **cada script**: qué hace, stage, entradas/salidas, configuración, ejecución, errores y repetición segura. También debe explicar los tres secrets, prerrequisitos, permisos, programación, checks de rama, lectura del KPI, consulta de rechazados y monitoreo. No se acepta una entrega que requiera ejecutar pasos de transformación o crear tablas a mano para completar el ciclo.
