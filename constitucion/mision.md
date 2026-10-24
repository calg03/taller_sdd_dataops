# Misión de ClientesConfiables

## Para qué existe

ClientesConfiables transforma la exportación del CRM en datos confiables para preparar las campañas de los lunes y medir la contactabilidad por país. Hoy Marketing desconoce las causas de los correos que rebotan; el producto distinguirá clientes contactables, clientes no contactables y registros con errores, sin exponer emails en los reportes.

La constitución es la base de conocimiento común del proyecto. Cada feature debe consultarla y respetar sus acuerdos; los cambios de negocio se acuerdan antes de modificar la implementación.

## Audiencia y responsabilidades

| Persona / área | Necesidad y responsabilidad |
| --- | --- |
| Carmen · Marketing / CRM | Usar la salida autorizada de contactos adultos; validar la definición y el resultado del KPI. |
| Andrés · Analítica / BI | Consultar métricas por país, nombre y región, y recibir alertas antes que Marketing. |
| Raúl · Ingeniería de Datos | Validar las entregas técnicas y operar un proceso automático, trazable y repetible. |
| Patricia · Gobierno de Datos | Validar las reglas de gobierno y apoyar a Ingeniería en la revisión de rechazados. |

## Alcance

Dentro del proyecto:

- Fuente única: `data/source/customers.csv`, con `customer_id`, `name`, `age`, `country` y `email`. Cada archivo representa una foto completa del CRM.
- Modelo lógico y físico, tablas creadas desde código versionado, validación previa en PR y pipeline Bronze → Silver → Gold, con rechazados, referencia de países y monitoreo.
- Conservación de versiones anteriores. Dentro de cada archivo, la última fila de un mismo `customer_id` determina su versión vigente. El KPI cuenta una sola versión vigente por cliente.
- Mayoría de edad desde los 18 años. Los menores no se contactan; ser menor no es por sí mismo un error de calidad.
- Clientes con email vacío o inválido permanecen en Silver como no contactables si cumplen las demás reglas.
- Gold agregado por país, con nombre y región, sin emails. Referencia inicial: PE, CL, CO y AR en Sudamérica; MX en Norteamérica.
- Ejecución automática cada lunes: archivo disponible a las 07:00 y publicación válida antes de las 08:00, zona `America/Lima`.
- Acceso restringido a datos personales, retención de seis meses y trazabilidad de cada ejecución.

Fuera del proyecto:

- Envío de campañas o correos.
- Corrección automática del CRM o edición manual del CSV para ocultar errores.
- Verificación de existencia del buzón, entregabilidad real o consentimiento: estos datos no están en la fuente.
- Otras fuentes y segmentaciones comerciales adicionales.

## Cómo se mide el éxito

**Objetivo de negocio:** elevar el porcentaje de clientes adultos contactables desde una línea base declarada de **30% hasta al menos 60%, en dos meses** desde el inicio acordado del proyecto.

`% contactables = 100 × adultos contactables vigentes / total de adultos vigentes del origen`

- Adulto: cliente cuya edad se puede interpretar como entero y es mayor o igual a 18.
- Contactable: adulto que cumple las reglas obligatorias de calidad y tiene email con formato válido.
- El denominador se calcula sobre la foto completa del origen, después de seleccionar la última fila por cliente. Incluye adultos con email inválido o ausente y adultos rechazados por otras reglas; excluirlos inflaría el indicador.
- Una edad ausente o no numérica impide determinar adultez: el registro se rechaza y se informa por separado, sin incluirlo en el denominador adulto.
- Cada cliente identificable cuenta una sola vez. Registros sin identificador se rechazan y se informan aparte.
- Si no hay adultos, el porcentaje es nulo y se informa denominador cero; no se presenta como 0% ni 100%.
- Se publica el indicador global y por país, junto con numerador, denominador, fecha de la foto y ejecución. Adultos con país no válido se contabilizan en un grupo sin país válido para reconciliar el total, sin inventar un país de referencia.

La línea base de 30% es un acuerdo de negocio, no un resultado calculado del CSV del taller. Carmen valida la comparación usando la misma definición. El producto permite medir y detectar problemas; la mejora del dato requiere que los responsables corrijan el origen.

**Criterios operativos:** publicación válida antes de las 08:00 de cada lunes; ningún registro con errores obligatorios en Silver; ningún email en Gold; cada fila y resultado vinculados a su ejecución; merge bloqueado cuando falle un stage obligatorio.
