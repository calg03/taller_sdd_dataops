# Fase 1 · Validación

Estado: criterios pendientes de implementar y ejecutar. Ninguna casilla está cumplida por la sola redacción de esta spec.

Ejecutar contra el commit vigente de la rama `fase-1-diseno-calidad-shift-left`. En PR, reemplazar `<tabla>` por `workspace.demo.<tabla>__pr_<numero>`; nunca probar escrituras en tablas base. Guardar evidencia sin datos personales y con commit, ejecución y entorno.

## Stage 1 · Calidad shift-left

- [ ] **V01 · Estructura.** Tests automáticos con columnas faltantes, extra, duplicadas, cabecera incorrecta, CSV ilegible, filas con distinto número de campos y archivo vacío. Esperado: validación falla, salida distinta de cero y ninguna conexión al warehouse. UTF-8 con/sin BOM, LF/CRLF y CSV entrecomillado válido pasan. Fallar bloquea merge.
- [ ] **V02 · Reglas obligatorias.** Tests por cada código de rechazo y combinaciones de errores. Esperado: todos los motivos obligatorios, una fila contada una vez, originales preservados en el resultado interno y ausencia separada de formato. Fallar bloquea merge.
- [ ] **V03 · Normalización.** Tests con espacios exteriores y país en minúsculas. Esperado: validación sobre valores normalizados, país en mayúsculas, contenido interno de nombre preservado, versión cruda sin modificar. Fallar bloquea merge.
- [ ] **V04 · Edad y banderas.** Tests de edades 0, 17, 18, vacía, negativa, decimal, texto y fuera del rango de INT. Esperado: 0/17 válidas no adultas; 18 adulta; demás casos inválidos rechazados con el motivo apropiado. Sin rechazo por minoría de edad. Fallar bloquea merge.
- [ ] **V05 · Email no bloqueante.** Tests de formato aceptado y rechazado según requerimientos, email vacío y menor con email válido. Esperado: no se incrementan rechazos obligatorios por email; adulto válido con email defectuoso es candidato a Silver no contactable; menor nunca contactable. Fallar bloquea merge; detectar defectos tolerados solo advierte.
- [ ] **V06 · Última versión.** Fixture con mismo identificador y campos distintos. Esperado: selecciona última posición; la anterior queda desplazada y no es un rechazo por duplicidad. Con última versión inválida no se recupera la anterior. IDs sin valor no se fusionan. Fallar bloquea merge.
- [ ] **V07 · Umbral exacto.** Fixture de 10 filas con 3 rechazos: 30%, SUCCESS con advertencia. Fixture de 10 filas con 4 rechazos: 40%, FAILED y stage 2 no ejecutado. Comparar sin redondear. Rechazo de 0 filas sobre un archivo no vacío pasa; archivo vacío falla. Fallar bloquea merge.
- [ ] **V08 · CSV del taller intacto.** Ejecutar validador contra `data/source/customers.csv` y comprobar su diff vacío. Esperado: 21 filas; 20 identidades; 1 versión desplazada; 5 rechazos; 23,809523…%; motivos 2 NAME_MISSING, 1 AGE_MISSING, 1 AGE_INVALID, 1 COUNTRY_MISSING; 2 emails inválidos y 1 ausente. Stage 1 pasa con advertencia al umbral de 30%. Una diferencia bloquea merge hasta explicarla, sin corregir manualmente el origen.
- [ ] **V09 · Semántica compartida del KPI.** Test local sobre el CSV, sin publicar métricas. Esperado: 15 versiones válidas seleccionadas, incluidas 2 menores; 13 adultos válidos, 10 contactables y 16 adultos vigentes del origen. Porcentaje simulado 62,5%, sin afirmar logro del objetivo del CRM. Fallar bloquea merge.
- [ ] **V10 · Privacidad del diagnóstico.** Capturar stdout/stderr y artefactos de fixtures con datos ficticios únicos. Esperado: conteos, códigos y posiciones; ningún email, nombre, identidad personal ni valor de secret. Fallar bloquea merge.
- [ ] **V11 · Sin conexión antes de validar.** Ejecutar stage 1 sin las variables de los tres secrets y comprobar dependencias/job. Esperado: todas las pruebas locales y CSV completan sin acceso a Databricks; falla de stage 1 impide iniciar despliegue. Fallar bloquea merge.

## Stage 2 · Despliegue y validación del modelo

- [ ] **V12 · Existencia y contrato completo.** Ejecutar `scripts/validate_model.py` e inspeccionar `workspace.information_schema.columns` para las siete tablas y las vistas del PR. Esperado: nombres, tipos, precisión, escala y nulabilidad de requerimientos, sin columnas adicionales que expongan emails en Gold. Fallar bloquea merge.
- [ ] **V13 · Referencia.** Consultar únicamente `country_code, country_name, region` de la referencia aislada. Esperado: exactamente cinco filas: PE/Perú/Sudamérica, CL/Chile/Sudamérica, CO/Colombia/Sudamérica, MX/México/Norteamérica y AR/Argentina/Sudamérica; cero códigos duplicados. Fallar bloquea merge.
- [ ] **V14 · Sin carga prematura.** Consultar `COUNT(*)` de Bronze, Silver, rechazados, Gold y publicación en un entorno de PR recién creado. Esperado: cero en cada tabla; la referencia tiene cinco filas y auditoría sí puede tener registros técnicos. No insertar clientes para demostrar despliegue. Fallar bloquea merge.
- [ ] **V15 · Idempotencia.** Ejecutar despliegue dos veces sobre los mismos objetos de PR. Esperado: mismas siete tablas, referencia con cinco filas y mismas fechas cuando no cambió el contenido, tablas de negocio vacías y auditoría sin duplicados de clave lógica. Cada ejecución queda diferenciada. Fallar bloquea merge.
- [ ] **V16 · Incompatibilidad visible.** En un entorno desechable separado, preparar con el harness de pruebas una tabla con tipo incompatible y ejecutar despliegue. Esperado: fallo explícito, sin DROP/TRUNCATE ni pérdida de datos; check de la prueba pasa solo si detectó ese rechazo esperado. Fallar bloquea merge.
- [ ] **V17 · Aislamiento.** Comparar nombres resueltos y metadatos antes/después del despliegue de PR. Esperado: todos los objetos usan `__pr_<numero>`, incluidas referencias internas y auditoría; tablas base sin cambios. Sufijos no autorizados se rechazan antes de ejecutar SQL. Fallar bloquea merge.
- [ ] **V18 · Vistas vigentes y contacto.** Revisar definiciones de vistas y usar tests sintéticos en entorno desechable para probar filtros. Esperado: enlace al entorno/foto publicada; vista de contactos solo con `is_contactable=true`; Gold sin email ni identificador personal; las vistas del PR limpio están vacías. Fallar bloquea merge.
- [ ] **V19 · Permisos.** Revisar permisos efectivos con identidades de prueba de Ingeniería/Gobierno, Marketing y BI. Esperado: BI solo Gold, Marketing solo contactos autorizados, datos crudos/rechazados restringidos; sin permisos amplios heredados que anulen el aislamiento. Registrar grupos reales y evidencia. Si faltan grupos o no puede verificarse acceso, criterio pendiente y merge bloqueado; no sustituirlo por revisión del archivo SQL.
- [ ] **V20 · Trazabilidad y fallos de conexión.** Consultar auditoría y revisar evidencia CI de un fallo simulado sin datos personales. Esperado: stage 1 y 2 identificados por run, intento, commit y entorno; tiempos y resultado; ante fallo anterior a la tabla, evidencia en CI y estado FAILED. Ningún error convertido en éxito. Fallar bloquea merge.

Consultas orientativas para la referencia y auditoría, ejecutadas por el validador o en revisión de solo lectura:

```sql
SELECT country_code, country_name, region
FROM workspace.demo.countries_reference__pr_<numero>
ORDER BY country_code;

SELECT country_code, COUNT(*) AS occurrences
FROM workspace.demo.countries_reference__pr_<numero>
GROUP BY country_code
HAVING COUNT(*) <> 1;

SELECT run_id, stage_name, attempt_number, status, commit_sha, environment
FROM workspace.demo.pipeline_stage_runs__pr_<numero>;
```

El marcador `<numero>` debe sustituirse por el número real de PR antes de ejecutar. Son consultas de comprobación; esta entrega no crea scripts ni ejecuta DDL.

## Integración y revisión

- [ ] **V21 · Orden, credenciales y costo.** Revisar workflow y una ejecución de Actions. Esperado: `calidad-shift-left` antes de `despliegue-modelo`, sin secrets en el primer job; tres secrets solo en contexto confiable, timeout y concurrencia por PR; sin clusters adicionales, cron ni stages de ingesta. El job omitido por falta de credenciales no habilita merge. Fallar bloquea merge.
- [ ] **V22 · Protección del merge.** Revisar reglas de `main` y ejecutar un caso fallido controlado. Esperado: sin push directo; PR del commit vigente requiere ambos checks verdes; fallido/omitido bloquea merge. Fallar bloquea merge.
- [ ] **V23 · Documentación y revisión.** Revisar README y PR. Esperado: cada script implementado tiene propósito, stage, entradas/salidas, comando, configuración, errores y reejecución; prerrequisitos y grupos reales, limpieza de objetos de PR y límite Fase 1 documentados. Raúl valida técnica, Patricia gobierno y Carmen definición del KPI. Carencias bloquean aceptación.

## Qué solo genera advertencia

Filas rechazables con porcentaje mayor que 0 y menor o igual a 30%; email ausente/inválido; versiones desplazadas; exclusión de menores del contacto. Son condiciones esperadas y medibles, no exenciones a reglas obligatorias ni autorización para cargar filas erróneas en Silver.

La línea base de 30% y la meta de 60% en dos meses son indicadores de negocio; esta fase no falla por no demostrar todavía esa evolución. El criterio para cerrar Fase 1 es que los contratos, pruebas y despliegue funcionen según esta lista. El flujo operativo completo y su monitoreo se aceptan en la Fase 2.
