# Roadmap de ClientesConfiables

Solo dos fases, en orden. Los plazos son relativos al inicio acordado del proyecto; no se fija una fecha calendario sin ese acuerdo. La meta de negocio es pasar de 30% a un mínimo de 60% de adultos contactables en dos meses.

## Fase 1 · Diseño y calidad shift-left

**Objetivo:** definir y desplegar el modelo de datos y detectar defectos del archivo en el Pull Request antes de tocar Databricks.

**Plazo:** semanas 1–2.

**Depende de:** ninguna fase previa; requiere esta constitución aprobada y los prerrequisitos de GitHub y Databricks disponibles.

**Entrega:**

- Spec de fase con requerimientos, plan y validación alineados con la constitución.
- Modelo lógico y físico: Bronze, Silver, Gold, rechazados, países, trazabilidad y control de publicación; claves, relaciones, tipos y banderas documentados.
- Creación y actualización del modelo y referencia de países desde código versionado en `workspace.demo`, sin creación manual de tablas.
- Validación del CSV en PR: estructura, tipos, reglas obligatorias, email no bloqueante, selección de última fila por cliente y umbral máximo de rechazo de 30%.
- Reglas compartidas entre validación temprana y el procesamiento posterior, para evitar resultados contradictorios.
- Rama propia, PR, `main` protegida y checks obligatorios de los stages disponibles: shift-left primero y despliegue/validación del modelo después. Evidencias de ambos; errores bloquean el merge.
- Tablas separadas para validar PR y documentación de los scripts y stages implementados en el README.

**Aceptación:** Raúl valida la entrega técnica, Patricia las reglas de gobierno y Carmen la definición del KPI. El PR solo se integra con todos los checks de esta fase en verde. Esta fase crea el modelo; todavía no declara operativo el ciclo completo.

## Fase 2 · Pipeline de punta a punta

**Objetivo:** automatizar desde la foto completa del CRM hasta las métricas publicadas, con cuarentena, trazabilidad y alertas.

**Plazo:** implementación en semanas 3–4; seguimiento del KPI en semanas 5–8 dentro de esta misma fase, sin crear una tercera fase.

**Depende de:** Fase 1 validada e integrada en `main` con sus checks en verde.

**Entrega:**

- Spec de fase con requerimientos, plan y validación del ciclo completo.
- Los seis stages en orden: calidad shift-left → despliegue del modelo → ingesta Bronze → calidad/Silver/rechazados → Gold → monitoreo.
- Foto completa con historial, última fila por cliente, repetición sin duplicados y publicación controlada de la última foto válida.
- Rechazos con todos sus motivos; email inválido o ausente conservado como no contactable; menores excluidos de contactos y KPI adulto.
- Fallo cuando los rechazos superen 30%, sin publicar una nueva Silver/Gold; preservación de Bronze y rechazados cuando se haya alcanzado la ingesta. Diagnóstico en CI para fallas anteriores a Databricks.
- Gold global y por país con nombre y región, numerador y denominador reconciliables, sin emails. Adultos rechazados no desaparecen del denominador.
- Ejecución del lunes desde disponibilidad de origen a las 07:00 y publicación antes de las 08:00, hora de Lima; aviso a Andrés por GitHub ante fallas o retrasos, antes del consumo de Marketing.
- Evidencias por stage incluso ante fallos, retención de seis meses, controles de acceso y revisión de rechazados por Ingeniería con Gobierno.
- README completo de todos los scripts y stages. Ejecución de punta a punta con los tres secrets acordados, sin edición manual de scripts ni creación manual de tablas, cumplidos los prerrequisitos documentados.
- Rama y PR propios; merge a `main` únicamente con los seis stages obligatorios en verde. Las validaciones de PR se ejecutan en tablas separadas de la publicación operativa.
- Seguimiento semanal del porcentaje de adultos contactables y de los problemas que requieren corrección en origen durante las semanas 5–8.

**Aceptación:** Raúl valida funcionamiento y repetición segura; Patricia valida privacidad, accesos y rechazados; Carmen valida el KPI y su avance hacia al menos 60% en dos meses. Andrés verifica la disponibilidad y utilidad del reporte por país. La entrega técnica y la meta de negocio se verifican por separado: un pipeline correcto no sustituye la corrección de datos en el CRM.

## Límite del trabajo actual

Esta entrega contiene únicamente la constitución. Las specs, el código SQL/Python, los workflows, la configuración de servicios y las ejecuciones se realizarán al implementar cada fase. La constitución no afirma que esos componentes ya existan ni que los permisos o la protección de ramas ya estén configurados.
