# Fase 1 · Requerimientos

Estado: aprobada por el responsable del proyecto; implementación autorizada. Fecha: 2026-10-23, America/Lima.
Rama: `fase-1-diseno-calidad-shift-left`.
Base: [misión](../../constitucion/mision.md), [stack](../../constitucion/stack-tecnologico.md) y [roadmap](../../constitucion/roadmap.md).

## 1. Scope

Diseñar el modelo completo, preparar su despliegue repetible en Databricks y validar el CSV en cada PR antes de conectarse al warehouse. Implementación prevista en semanas 1–2; esta entrega contiene solo la spec, sin ejecutar ni crear los scripts aquí descritos.

Dentro de la implementación de esta fase:

- Modelo lógico y físico de siete tablas, referencia inicial de cinco países y vistas de acceso.
- Stage 1 de calidad shift-left y stage 2 de despliegue/validación del modelo, en ese orden.
- Creación de tablas sin carga de clientes; solo se carga la referencia de países. Se permite escribir metadatos técnicos de ejecución.
- Reglas reutilizables, pruebas sintéticas, separación de tablas por PR, trazabilidad de ambos stages y documentación en README.
- Ramas y PR, con checks obligatorios que bloqueen el merge a `main` ante fallas.

Fuera: ingesta operativa Bronze, escritura de clientes Silver/rechazados, cálculo y publicación de Gold, ejecución semanal, alertas operativas y limpieza automática de retención. Son entregables de la Fase 2. Aquí se define su contrato, para crear el modelo una sola vez y no contradecirlo después. No se envían campañas ni se corrige el CSV/CRM.

## 2. Entrada y reglas de interpretación

Fuente: `data/source/customers.csv`, foto completa en UTF-8, coma como delimitador, campos entrecomillados permitidos y cabecera exacta en este orden: `customer_id,name,age,country,email`. Aceptar BOM UTF-8, finales LF/CRLF y salto final. Cabecera ausente, extra, duplicada o fuera del contrato; CSV ilegible; número incorrecto de campos; o archivo sin filas son fallas bloqueantes antes de Databricks. No omitir silenciosamente registros vacíos intermedios o mal estructurados.

Los cinco campos se leen como texto. `source_row_number` es la posición del registro lógico de datos, desde 1, no la línea física cuando un campo entrecomillado contiene saltos. Bronze conservará el texto original; las validaciones y Silver usan valores sin espacios exteriores. País se convierte a mayúsculas; no se cambia el contenido interno de nombres ni se convierte el email a minúsculas. Campo vacío después de quitar espacios se considera ausente.

| Campo | Tipo de entrada | Contrato validado |
| --- | --- | --- |
| `customer_id` | Texto | No vacío; identidad después de quitar espacios, sensible a mayúsculas. |
| `name` | Texto | No vacío después de quitar espacios. |
| `age` | Texto | Dígitos decimales ASCII, entero entre 0 y 2147483647, compatible con `INT`. Sin decimales ni signo. No se impone un máximo de edad de negocio adicional. |
| `country` | Texto | Código normalizado en PE, CL, CO, MX o AR. |
| `email` | Texto | Opcional, con validación no bloqueante de formato. |

El email es válido si no contiene espacios, tiene una sola `@`, parte local no vacía, y dominio con al menos un punto y etiquetas no vacías. La parte local usa letras ASCII, dígitos y `.!#$%&'*+/=?^_`{|}~-`; no empieza/termina con punto ni contiene puntos consecutivos. Cada etiqueta del dominio usa letras ASCII, dígitos o guion, sin guion inicial/final. Es una validación sintáctica deliberadamente simple, sin consultas de red ni promesas de entrega. `usuario@mail.com` pasa; `usuario@mail`, `usuario@`, `usuario@@mail.com`, `usuario@.com` y texto con espacios fallan. Vacío e inválido conservan al cliente válido como no contactable.

## 3. Reglas obligatorias, duplicados y umbral

| Código estable | Condición | Resultado |
| --- | --- | --- |
| `CUSTOMER_ID_MISSING` | Identificador ausente | Rechazar fila. |
| `NAME_MISSING` | Nombre ausente o solo espacios | Rechazar fila. |
| `AGE_MISSING` | Edad ausente | Rechazar fila. |
| `AGE_INVALID` | Edad presente que incumple formato o rango físico de INT | Rechazar fila. |
| `COUNTRY_MISSING` | País ausente | Rechazar fila. |
| `COUNTRY_UNKNOWN` | Código presente fuera de referencia | Rechazar fila. |
| `EMAIL_MISSING` / `EMAIL_INVALID` | Email ausente / formato inválido | Advertir; no rechazar por este motivo. |

Evaluar todas las reglas por fila y conservar todos los motivos obligatorios; contar una sola vez la fila rechazada. No agregar simultáneamente motivo de ausencia y de formato para el mismo campo. Menor de 18 años no es un error. Una fila menor válida permanece elegible para Silver, con `is_adult=false` e `is_contactable=false`.

La última posición de cada `customer_id` normalizado identifica su versión seleccionada, incluso si esta tiene errores. Las filas anteriores válidas son versiones desplazadas, no rechazos. Las filas anteriores inválidas sí cuentan en el rechazo de filas; todo el origen quedará en Bronze en la Fase 2. No usar la versión anterior válida para sustituir la última inválida. Filas sin identidad no se agrupan en un cliente ficticio.

**Umbral aprobado: 30%.** `rechazo_pct = 100 × filas_con_error_obligatorio / total_filas_de_datos`. Se bloquea solo cuando supera 30%, sin redondear para decidir; comparar cantidades equivalentes (`100 × rechazadas > 30 × total`). Exactamente 30% pasa. Un email inválido por sí solo, un menor o un duplicado no incrementan el numerador.

Con errores estructurales no se calcula un porcentaje pretendidamente completo: fallar y no conectar a Databricks. Con filas rechazables dentro del umbral, el stage 1 pasa con advertencia y diagnóstico agregado; la persistencia de rechazados será del stage 4 en la Fase 2.

## 4. Modelo lógico

- Foto 1:N filas Bronze y versiones seleccionadas de clientes; cliente 1:N versiones entre fotos.
- País 1:N versiones Silver; códigos y nombres provienen de la referencia versionada.
- Fila Bronze 0:1 rechazo, con varios motivos en un arreglo; una versión seleccionada válida puede producir una fila Silver.
- Foto 1:N métricas por país/grupo y total global. Los adultos rechazados por otros campos siguen en el denominador de la misión.
- Ejecución 1:N intentos de stage; cada registro cargado conserva foto y ejecución.
- Entorno 0:1 foto publicada vigente. La Fase 1 no publica una foto de clientes ni métricas.

## 5. Contrato físico y scripts de creación previstos

Destino base `workspace.demo`. Tablas Delta. Las siguientes rutas SQL son artefactos **a implementar tras aprobar esta spec**, no scripts ya existentes. No ejecutar DDL incluido en documentación manualmente.

Notación: `!` significa NOT NULL; las demás columnas permiten NULL. `T` expande a `snapshot_id STRING!`, `run_id STRING!`, `loaded_at TIMESTAMP!`. Timestamps UTC. Las claves son lógicas, verificadas por pruebas; no confiar en restricciones PK/FK para deduplicar.

| Tabla y script que la creará | Columnas y tipos | Clave / relaciones |
| --- | --- | --- |
| `customers_bronze` · `sql/model/010_customers_bronze.sql` | `customer_id STRING`, `name STRING`, `age STRING`, `country STRING`, `email STRING`, `source_file STRING!`, `source_row_number BIGINT!`, T | `(snapshot_id, source_row_number)`; fila cruda sin limpieza. |
| `countries_reference` · `sql/model/020_countries_reference.sql` | `country_code STRING!`, `country_name STRING!`, `region STRING!`, `reference_version STRING!`, `run_id STRING!`, `loaded_at TIMESTAMP!` | `country_code`; exactamente cinco filas iniciales. |
| `customers_silver` · `sql/model/030_customers_silver.sql` | `customer_id STRING!`, `name STRING!`, `age INT!`, `country_code STRING!`, `email STRING`, `is_adult BOOLEAN!`, `has_valid_email BOOLEAN!`, `is_contactable BOOLEAN!`, `source_row_number BIGINT!`, T | `(snapshot_id, customer_id)`; `country_code` → referencia; fila origen → Bronze. |
| `customers_rejected` · `sql/model/040_customers_rejected.sql` | `customer_id STRING`, `name STRING`, `age STRING`, `country STRING`, `email STRING`, `source_file STRING!`, `source_row_number BIGINT!`, `rejection_reasons ARRAY<STRING>!`, T | `(snapshot_id, source_row_number)`; arreglo de motivos no vacío. |
| `customer_contactability_gold` · `sql/model/050_customer_contactability_gold.sql` | `aggregation_level STRING!`, `country_group STRING!`, `country_code STRING`, `country_name STRING!`, `region STRING`, `adult_customers BIGINT!`, `contactable_adults BIGINT!`, `non_contactable_adults BIGINT!`, `contactable_pct DECIMAL(7,4)`, `published_at TIMESTAMP!`, T | `(snapshot_id, aggregation_level, country_group)`; sin emails ni identificadores personales. |
| `pipeline_stage_runs` · `sql/model/060_pipeline_stage_runs.sql` | `run_id STRING!`, `snapshot_id STRING`, `stage_name STRING!`, `attempt_number INT!`, `status STRING!`, `started_at TIMESTAMP!`, `finished_at TIMESTAMP`, `input_rows BIGINT`, `output_rows BIGINT`, `rejected_rows BIGINT`, `rejection_pct DECIMAL(7,4)`, `error_code STRING`, `error_summary STRING`, `commit_sha STRING!`, `environment STRING!` | `(run_id, stage_name, attempt_number)`; estados RUNNING, SUCCESS, FAILED o SKIPPED. |
| `published_snapshots` · `sql/model/070_published_snapshots.sql` | `environment STRING!`, `snapshot_id STRING!`, `run_id STRING!`, `published_at TIMESTAMP!`, `source_file STRING!` | `environment`; puntero a foto válida, vacío en esta fase. |

`sql/model/000_schema.sql` creará/verificará `workspace.demo`. `sql/model/080_consumer_views.sql` definirá vistas de Silver vigente, contactos autorizados y Gold vigente, enlazadas al puntero de publicación del entorno. La vista de contactos selecciona solo `is_contactable=true`; Gold no expone email ni `customer_id`. Vacías inicialmente, las vistas no deben mostrar historia como si fuera el estado vigente.

`sql/model/090_permissions.sql` aplicará el contrato de acceso a grupos configurados por nombre no secreto: Ingeniería/Gobierno para datos restringidos, Marketing a contactos autorizados, BI a Gold. Por ampliación autorizada del alcance, al informar el usuario que no existen grupos, el stage 2 creará idempotentemente grupos de cuenta mediante el proxy SCIM del workspace: `clientesconfiables_ingenieria`, `clientesconfiables_gobierno`, `clientesconfiables_marketing` y `clientesconfiables_bi`. Verificará existencia antes y después; no creará usuarios ni agregará miembros o roles administrativos. La identidad de despliegue necesita permisos para crear grupos de cuenta y desplegar el modelo. No se usarán grupos locales de workspace para Unity Catalog. Los permisos efectivos seguirán pendientes hasta probarlos con identidades reales.

`data/reference/countries.csv` contendrá PE/Perú/Sudamérica, CL/Chile/Sudamérica, CO/Colombia/Sudamérica, MX/México/Norteamérica y AR/Argentina/Sudamérica. Se leerá tanto en validación local como en despliegue, sin dos listas independientes. `sql/reference/seed_countries.sql` hará carga repetible por código; una reejecución no añade filas ni cambia `loaded_at` si el contenido no cambió.

Bandera Silver: `is_adult = age >= 18`; `has_valid_email` sigue la regla de sección 2; `is_contactable = is_adult AND has_valid_email`. Solo entran filas sin errores obligatorios. Su cálculo y carga operativos son de la Fase 2, pero esta fase los deja especificados y probados como evaluación local.

## 6. Despliegue, idempotencia y aislamiento

- Cada PR usa sufijo `__pr_<numero>` en **todas** sus tablas y vistas, incluido referencia, auditoría y publicación, dentro de `workspace.demo`. Referencias internas al mismo sufijo; ninguna escritura a las tablas sin sufijo desde PR.
- La configuración solo permite catálogo/schema aprobados y sufijos construidos con número de PR; no interpolar SQL arbitrario del origen. Serializar despliegues del mismo PR.
- Desplegar dos veces debe conservar esquema y datos; detectar incompatibilidades sin DROP/TRUNCATE ni sustitución destructiva. En este primer modelo se crean objetos ausentes y se falla ante diferencias no soportadas.
- El SHA-256 de los bytes originales identifica la foto; UUID identifica cada ejecución. Misma entrada produce la misma foto y una nueva ejecución auditable. La reingesta efectiva se implementa en Fase 2.
- Tras merge se despliega el modelo base sin sufijo desde `main`, pasando primero validación del origen. El PR ya debe haber demostrado despliegue y validación en sus objetos aislados.
- Evidencias de stage 1 en CI antes de conectarse; al iniciar stage 2 y existir auditoría, consolidar stage 1 y registrar stage 2. Si no hay conexión, retener evidencia en CI y fallar. No fingir persistencia remota de una ejecución bloqueada antes de Databricks.

## 7. Seguridad, costo y entrega

**Adaptación aprobada tras el primer PR:** el usuario confirmó Databricks Free Edition y autorizó continuar con una sola identidad, sin SCIM ni concesiones a Marketing/BI, dejando V19 pendiente. `deployment_mode` debe ser explícitamente `free_edition` o `managed`; un valor desconocido falla. En `free_edition`, el stage 2 crea y valida las tablas/referencia/vistas y auditoría, pero no consulta/crea grupos ni ejecuta `090_permissions.sql`; emite `V19_PENDING_NO_CONSUMER_GRANTS`. No se afirma que los permisos existentes o heredados estén validados. En `managed` permanece el aprovisionamiento de grupos descrito antes. Esta excepción prevalece sobre el requisito previo de crear grupos para la ejecución de este taller; no autoriza compartir datos ni marcar V19 cumplido. No cambiar de modo automáticamente ante 401/403. [Limitaciones oficiales](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations).

Usar solo `DATABRICKS_HOST`, `DATABRICKS_HTTP_PATH` y `DATABRICKS_TOKEN` en GitHub Secrets. Stage 1 no recibe credenciales ni abre conexión. Stage 2 usa los secrets solo en PR confiables del repositorio; PR sin acceso autorizado a secrets falla/no queda elegible para merge, sin ejecutar código no confiable con credenciales.

No incluir emails, nombres, identificadores ni filas originales en logs y artefactos de CI; emitir conteos por regla y referencias de posición. Las pruebas nuevas usan datos ficticios. No modificar el CSV del taller. Retención de datos acordada: seis meses; documentar la limpieza de objetos de PR para que no se conserven sin límite. Su automatización será de la Fase 2.

Para limitar costo, validar localmente antes del warehouse, no lanzar clusters adicionales y no repetir despliegues en paralelo para el mismo PR. No se establece un presupuesto monetario no acordado. Cada acceso al warehouse debe tener timeout y fallo visible.

Checks obligatorios previstos: `calidad-shift-left` y `despliegue-modelo`; ambos deben completar correctamente en el commit vigente del PR. No tratar como aprobado un check omitido. Protección de `main` y permisos deben verificarse en GitHub durante la implementación; esta spec no los configura.

## 8. Decisiones y motivos

- Umbral cambiado de 15% a **30% por instrucción del usuario**, reflejado en la constitución; permite tolerar errores sin ocultarlos ni introducirlos en Silver.
- Email defectuoso no rechaza: conservar adultos no contactables permite construir el KPI acordado.
- Última fila manda: la fuente no tiene fecha de modificación; el orden es la regla aprobada, sin deducir antigüedad real.
- Referencia única y reglas reutilizables: evitan divergencia entre PR y procesamiento.
- Modelo completo, tablas de clientes vacías: la Fase 1 prepara el contrato y la Fase 2 ejecuta el ciclo.
- El CSV actual es una entrada aceptada con advertencia al 30%, no una prueba negativa de umbral. Los casos de exceso se construyen con datos sintéticos separados.

## 9. Evidencia esperada del CSV actual

Sin cargar clientes en Databricks, la evaluación local debe producir:

| Medida | Resultado |
| --- | --- |
| Filas de datos | 21 |
| Clientes identificables distintos | 20 |
| Filas desplazadas por última versión | 1 |
| Filas con errores obligatorios | 5 |
| Porcentaje de rechazo | 23,809523…% |
| Motivos | 2 NAME_MISSING, 1 AGE_MISSING, 1 AGE_INVALID, 1 COUNTRY_MISSING |
| Email inválido / ausente | 2 / 1 |
| Menores válidos seleccionados | 2 |
| Versiones seleccionadas válidas candidatas a Silver | 15 |
| Adultos válidos candidatos a Silver | 13 |
| Adultos contactables candidatos | 10 |
| Adultos vigentes del origen, incluidos rechazados con edad válida | 16 |
| KPI global simulado para probar semántica, sin publicar Gold | 62,5% = 10 / 16 × 100 |
| Resultado del stage 1 | SUCCESS con advertencias; stage 2 habilitado |

El 62,5% de esta muestra no sustituye la línea base de 30% ni prueba que se alcanzó la meta real del CRM.
