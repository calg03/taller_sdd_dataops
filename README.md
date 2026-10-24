# Taller SDD para Datos: del prompt a la spec y de la spec al pipeline

## Estado de ClientesConfiables · Fase 1

La constitución y la spec de `specs/2026-10-23-fase-1-diseno-calidad-shift-left/` están aprobadas. En la rama `fase-1-diseno-calidad-shift-left` se implementaron la validación local y el despliegue del modelo. El flujo de clientes Bronze → Silver/rechazados → Gold y la programación semanal se implementarán en la Fase 2.

**Pendiente para validar en Databricks:** completar los cuatro nombres reales de grupos en `config/project.json`, configurar los tres secrets y verificar permisos/conectividad. Los nombres están vacíos deliberadamente: el despliegue falla con `ACCESS_GROUPS_NOT_CONFIGURED` hasta completar la configuración. No se consideran verificados los accesos ni las tablas remotas por existir el código. Ver [evidencia de la Fase 1](specs/2026-10-23-fase-1-diseno-calidad-shift-left/evidencia.md).

### Ejecución local de Fase 1

Usar **Python 3.12**. Desde la raíz, sin credenciales y sin instalar el conector:

```bash
python -m unittest discover -s tests -v
python scripts/validate_source.py
```

El CSV original no se modifica. Resultado esperado: 21 filas, 5 rechazos, **23,81%**, dentro del umbral aprobado de **30%**. Emails inválidos/vacíos producen advertencias, no rechazo obligatorio. Esta fase calcula resultados de evaluación en memoria, sin cargar clientes en Databricks. El KPI simulado de la muestra no demuestra el logro del KPI del CRM.

Para desplegar después de configurar grupos y credenciales en el entorno autorizado:

```bash
python -m pip install -r requirements.txt
python scripts/validate_source.py
python scripts/deploy_model.py --pr-number 123
python scripts/validate_model.py --pr-number 123
```

`123` es un ejemplo: reemplazar por el PR real. En GitHub Actions las credenciales se inyectan exclusivamente desde GitHub Secrets; no escribirlas en archivos, argumentos, README ni logs. La ejecución local del despliegue solo es apropiada con una inyección de secretos ya autorizada; el camino habitual es Actions. Los comandos sin `--pr-number` apuntan al modelo base y se reservan al despliegue desde `main` después del merge.

### Scripts y stages

| Script o módulo | Stage | Qué hace, entradas y salidas |
| --- | --- | --- |
| `scripts/validate_source.py` | 1 · calidad shift-left | Lee origen, referencia y configuración; valida estructura/tipos/reglas; escribe `artifacts/quality.json` agregado. `--source` permite probar otro CSV y `--report` otro destino. Exit 1 ante fallo estructural o más de 30% rechazado. |
| `scripts/deploy_model.py` | 2 · despliegue | Revalida origen y reporte de stage 1, exige grupos configurados, crea/verifica el modelo, carga países, aplica permisos y valida. `--pr-number` aísla objetos. Escribe `artifacts/deployment.json`; falla ante secretos/grupos ausentes, incompatibilidad o error remoto. |
| `scripts/validate_model.py` | 2 · comprobación | Solo lectura: comprueba columnas, tipos, nulabilidad, países, vistas y grants amplios conocidos. Mismo `--pr-number`. Exit 1 ante incumplimiento. No sustituye pruebas con identidades reales. |
| `scripts/_bootstrap.py` | Soporte | Resuelve importaciones desde `src/`; no se ejecuta por separado. |
| `src/clientes_confiables/customer_quality.py` | 1; reutilizable en futuro stage 4 | Reglas y selección de última versión compartidas, sin conexión a Databricks. |
| `src/clientes_confiables/project_config.py` | 1 y 2 | Lee configuración no secreta y restringe catálogo, schema y sufijo de PR. |
| `src/clientes_confiables/databricks_connection.py` | 2 | Conector oficial, secrets inyectados y timeout de socket de 60 segundos. |
| `src/clientes_confiables/model_contract.py` | 2 | Contrato físico en `config/model.json`; verifica metadata y referencia única. |
| `src/clientes_confiables/model_deployment.py` | 2 | Aplica DDL en orden, sin DROP/TRUNCATE ni carga de clientes. |
| `src/clientes_confiables/model_permissions.py` | 2 | Aplica permisos por grupos; falla ante configuración ausente o acceso amplio conocido. |
| `src/clientes_confiables/stage_audit.py` | Transversal en 1–2 | Consolida stage 1 en Databricks cuando existe conexión y registra intentos de stage 2. |
| `sql/model/000_schema.sql` | 2 | Crea/verifica `workspace.demo`. |
| `sql/model/010_customers_bronze.sql` | 2 | Crea tabla cruda sin poblarla. |
| `sql/model/020_countries_reference.sql` | 2 | Crea tabla de países. |
| `sql/model/030_customers_silver.sql` | 2 | Crea tabla limpia con banderas, sin poblarla. |
| `sql/model/040_customers_rejected.sql` | 2 | Crea cuarentena con todos los motivos, sin poblarla. |
| `sql/model/050_customer_contactability_gold.sql` | 2 | Crea métricas agregadas sin emails, sin poblarla. |
| `sql/model/060_pipeline_stage_runs.sql` | 2 | Crea auditoría técnica por run/stage/intento. |
| `sql/model/070_published_snapshots.sql` | 2 | Crea control de publicación, inicialmente vacío. |
| `sql/model/080_consumer_views.sql` | 2 | Vistas vigentes y contactos adultos autorizados, vacías hasta publicar en Fase 2. |
| `sql/model/090_permissions.sql` | 2 | Plantilla de permisos aplicada solo a grupos configurados. |
| `sql/reference/seed_countries.sql` | 2 | MERGE parametrizado de los cinco países; conserva fecha y run si el contenido no cambia. |
| `tests/test_*.py` | 1 · pruebas | Contratos, límites, privacidad, CLI, sufijos y despliegue simulado. No acredita ejecución remota. |

Los SQL son plantillas invocadas por los scripts; no requieren ejecución manual. No incluyen secretos. Instalar `requirements-dev.txt` solo para revisiones adicionales del YAML; las pruebas locales de negocio usan la biblioteca estándar.

### GitHub Actions, permisos y operación

`.github/workflows/fase-1.yml` ejecuta dos checks: **`calidad-shift-left` → `despliegue-modelo`**. El primer job no recibe secrets ni se conecta a Databricks. El segundo usa únicamente `DATABRICKS_HOST`, `DATABRICKS_HTTP_PATH` y `DATABRICKS_TOKEN` y falla en contextos no confiables; no se usa `pull_request_target`. Hay timeout y concurrencia por PR.

Configurar en `config/project.json` los nombres reales de cuatro grupos distintos (`engineering`, `governance`, `marketing`, `bi`). La identidad técnica debe poder usar el warehouse, crear schema/tablas/vistas y administrar sus permisos; los grupos deben existir. Los nombres de grupo son configuración, no secrets adicionales. Ingeniería/Gobierno acceden a tablas restringidas, Marketing solo a `customer_contacts`, BI solo a `contactability_current`. Verificar permisos heredados de catálogo/schema y probar con identidades reales antes de aceptar V19; los administradores pueden tener privilegios superiores por diseño.

En PR se usa `workspace.demo.<objeto>__pr_<numero>` para tablas y vistas. Una segunda ejecución no duplica países; una incompatibilidad de contrato falla sin sustituir la tabla. El despliegue en `main` crea el modelo base, sin sufijo, después de validar origen. No hay clientes publicados todavía y las vistas permanecen vacías.

`pipeline_stage_runs__pr_<numero>` permite revisar stage, estado, conteos, ejecución y commit. Si falla antes de poder escribir auditoría, la evidencia queda en Actions; los reportes agregados se conservan como artifacts por siete días y localmente en `artifacts/` (ignorado por Git). Un fallo de monitoreo/persistencia nunca convierte el check en verde. Los errores remotos se sanitizan; revisar conexión, configuración y metadata en el entorno autorizado sin publicar filas originales.

Tras el primer run, exigir ambos checks en las reglas de `main`, prohibir push directo y comprobar el bloqueo con un caso fallido. **No hacer merge con checks fallidos, omitidos ni con criterios remotos pendientes.** Los criterios y evidencias reales están en la spec.

Retención acordada: seis meses para datos y trazabilidad. Los objetos de PR no deben conservarse más de ese plazo; registrar objetos y solicitar su limpieza al cerrar el PR, verificando el sufijo exacto antes de cualquier eliminación. La limpieza automática se implementará en Fase 2. No subir nuevas exportaciones personales al historial de Git; `customers.csv` es el ejemplo existente del taller y los fixtures nuevos son ficticios.

Referencias de implementación: [conector SQL oficial](https://docs.databricks.com/aws/en/dev-tools/python-sql-connector) y [paquete del conector](https://pypi.org/project/databricks-sql-connector/). Las instrucciones generales del taller continúan a continuación; los acuerdos específicos vigentes son los de `constitucion/` y esta spec.

---

Taller práctico de **Spec-Driven Development (SDD)** aplicado a datos. En vez de pedirle a un asistente de IA "hazme un pipeline", primero escribimos **qué** queremos y **cómo sabremos que está listo**. Esa especificación (spec) es la que guía la construcción.

Vamos a recorrer el **ciclo del dato** completo sobre un archivo de clientes (`customers.csv`):

```
Diseño  →  Build (Bronze → Silver → Gold)  →  Test  →  Deploy  →  Monitoring
```

> **Idea clave:** no te cases con ninguna herramienta. Aquí usamos Databricks y GitHub Actions como ejemplo, pero la spec es la misma si mañana usas otra plataforma. Lo que se queda contigo es el método.

---

## ¿Qué vas a construir?

Al terminar tendrás en este repo:

1. **La constitución** del proyecto (`constitucion/`): la misión, el stack tecnológico y el roadmap. Es la base de conocimiento del proyecto y se consulta en cada feature.
2. **Una feature spec por cada fase** del roadmap: requerimientos, plan y validación.
3. **El modelo de datos** creado en Databricks desde el código: Bronze, Silver, Gold, una tabla de rechazados y una tabla de países.
4. **El pipeline** que tu asistente de IA construye a partir de esas specs, corriendo por stages en GitHub Actions. Nada llega a `main` sin pasar todos los stages.

## El pipeline que vas a especificar

No te lo damos hecho: lo describes en la constitución y tu asistente lo construye. Esta es la forma que pide el negocio:

```
rama de la fase ──► Pull Request ──────────────────────────────────────► merge a main
                     │                                                   (solo si todo
                     ▼                                                    está en verde)
 1. Calidad shift-left   valida el CSV antes de tocar Databricks
 2. Despliegue del modelo crea las tablas desde el código
 3. Ingesta Bronze        guarda el dato crudo
 4. Calidad de datos      válidos → Silver · con error → tabla de rechazados (con motivo)
 5. Gold                  indicador por país (nombre y región), solo mayores de edad
 6. Monitoreo             cada stage deja registro de su ejecución
```

Si un stage falla, el Pull Request queda bloqueado y no se puede hacer merge.

## Las dos partes de SDD

| Parte | Pregunta que responde | Archivo |
|---|---|---|
| **Constitución** · Misión | ¿Por qué existe este dato? ¿Para quién? ¿Qué KPI mueve? | `constitucion/mision.md` |
| **Constitución** · Stack tecnológico | ¿Cómo encaja con la tecnología? Restricciones de equipo, gobierno y calidad | `constitucion/stack-tecnologico.md` |
| **Constitución** · Roadmap | ¿Qué fases están planificadas y en qué orden? | `constitucion/roadmap.md` |
| **Feature Spec** · Scope + Requirements | ¿Qué construye esta fase? ¿Qué restricciones importan? | `specs/AAAA-MM-DD-fase/requerimientos.md` |
| **Feature Spec** · Plan | ¿En qué tareas se divide? | `specs/AAAA-MM-DD-fase/plan.md` |
| **Feature Spec** · Validation | ¿Cómo sabemos que ya está listo? | `specs/AAAA-MM-DD-fase/validacion.md` |

La constitución se escribe **una vez** por proyecto y vive en `constitucion/`, como base de conocimiento. La feature spec se escribe **una vez por cada fase** del roadmap y vive en `specs/`, que solo guarda lo que necesita cada feature.

---

## Requisitos previos

- Una cuenta de **GitHub**.
- Una cuenta de **Databricks Free Edition** con un SQL Warehouse (el mismo del taller de DataOps sirve).
- **Cualquier asistente de IA** que pueda leer y escribir archivos en tu repo, por ejemplo Claude Code, GitHub Copilot, Cursor o Gemini CLI. El taller funciona igual con cualquiera.
- Git instalado en tu computadora (o usa GitHub Codespaces).

## Estructura del repo

```
.
├── README.md                 ← este archivo
├── prompts.md                ← los prompts del taller, en español
├── constitucion/             ← vacío al inicio; base de conocimiento del proyecto
├── negocio/
│   └── input-negocio.md      ← lo que pidieron los stakeholders (entrada de la constitución)
├── data/
│   └── source/
│       └── customers.csv     ← el dato de entrada
└── specs/                    ← vacío al inicio; una carpeta por cada feature
```

No hay código del pipeline al comenzar. **El código sale de la spec**, no al revés.

---

## Paso a paso

### 1. Crea tu copia del repo

Haz **fork** de este repositorio (botón *Fork* arriba a la derecha) y clónalo:

```bash
git clone https://github.com/<tu-usuario>/<nombre-del-repo>.git
cd <nombre-del-repo>
```

✅ Checkpoint: ves `README.md`, `prompts.md`, `constitucion/`, `negocio/`, `data/` y `specs/`.

### 2. Deja listo Databricks

1. En Databricks, ve a **SQL Warehouses** y pulsa **Start** en tu warehouse. Espera a que diga **Running**.
2. Abre el **SQL Editor** y ejecuta:

   ```sql
   CREATE SCHEMA IF NOT EXISTS demo;
   ```

✅ Checkpoint: el warehouse está en Running y el schema `demo` existe.

### 3. Conecta GitHub con Databricks

En tu repo de GitHub: **Settings → Secrets and variables → Actions → New repository secret**. Crea estos 3 secrets:

| Secret | Qué es | Dónde lo encuentras |
|---|---|---|
| `DATABRICKS_HOST` | El host del workspace, sin `https://` (ej. `dbc-xxxx.cloud.databricks.com`) | SQL Warehouses → tu warehouse → Connection details |
| `DATABRICKS_HTTP_PATH` | La ruta del warehouse (ej. `/sql/1.0/warehouses/xxxx`) | SQL Warehouses → tu warehouse → Connection details |
| `DATABRICKS_TOKEN` | Tu token personal | Tu perfil → User settings → Developer → Access tokens → Generate new token |

> 🔒 Nunca pegues el token en un archivo del repo ni en el chat con tu asistente. Solo va en los secrets.

✅ Checkpoint: tienes los 3 secrets creados.

### 3b. Protege la rama `main`

Así nadie (ni tu asistente) puede subir cambios directo a `main`.

1. En tu repo: **Settings → Branches → Add branch ruleset** (o *Add rule*).
2. Aplícalo a la rama `main` y activa:
   - **Require a pull request before merging**, con **Required approvals = 0**. Así el Pull Request no espera que otra persona lo apruebe: lo que lo bloquea o lo deja pasar son los stages del pipeline. (Si trabajas en pareja, puedes subirlo a 1 para que tu compañero/a revise la spec.)
   - **Require status checks to pass**. Los checks del pipeline aparecen aquí después de su primera ejecución; vuelve a este paso para marcarlos.
3. Guarda la regla.

> En cuentas gratuitas de GitHub, la protección de ramas funciona en repos **públicos**. Si tu fork es privado y no la ves, mantenlo público para el taller.

✅ Checkpoint: un `git push` directo a `main` es rechazado.

### 4. Escribe la constitución (Parte 1)

1. Lee [`negocio/input-negocio.md`](negocio/input-negocio.md): es lo que pidieron Marketing, Ingeniería de Datos, Gobierno y BI. Completa en clase la sección "Lo que completamos en clase".
2. Abre tu asistente de IA dentro de la carpeta del repo.
3. Copia el **Prompt 1 · Constitución** de [`prompts.md`](prompts.md) y pégalo. El prompt le pide al asistente leer el input del negocio.
4. El asistente **te hará preguntas antes de escribir**. Respóndelas pensando como el dueño del dato desde el punto de vista de negocio
5. Revisa los tres archivos que crea en `constitucion/`. Si algo no te convence, pídele que lo corrija. **Tú apruebas la spec, no el asistente.**

✅ Checkpoint: existen `constitucion/mision.md`, `constitucion/stack-tecnologico.md` y `constitucion/roadmap.md`, y el roadmap tiene 2 fases que, juntas, cubren todo el ciclo del dato.

Guarda tu avance:

```bash
git add constitucion/
git commit -m "docs: constitución del proyecto"
git push
```

### 5. Escribe la spec de una fase (Parte 2)

1. Copia el **Prompt 2 · Feature Spec** de [`prompts.md`](prompts.md).
2. El asistente toma la **siguiente fase** del roadmap, crea una rama y te pregunta por el detalle.
3. Revisa `requerimientos.md`, `plan.md` y `validacion.md`. Pregúntate: *si alguien más leyera solo esto, ¿construiría lo mismo que yo tengo en la cabeza?*

✅ Checkpoint: existe una carpeta `specs/AAAA-MM-DD-<fase>/` con los tres archivos.

### 6. Construye desde la spec

Pídele al asistente que implemente el `plan.md` de esa fase, **respetando** `requerimientos.md`. El asistente escribirá el código (SQL, Python, workflow de GitHub Actions).

Prompt sugerido (es el **Prompt 3** de [`prompts.md`](prompts.md); cambia la fecha y el nombre de la fase por los tuyos):

```text
Implementa el plan de specs/AAAA-MM-DD-nombre-de-la-fase/plan.md, una tarea a
la vez, respetando requerimientos.md y constitucion/stack-tecnologico.md.

- Después de cada grupo de tareas, dime qué archivos cambiaste.
- Si una tarea no se puede hacer como dice la spec, detente y pregúntame;
  no cambies la spec por tu cuenta.
- Trabaja solo en la rama de esta fase. Cuando termines, prepara el Pull
  Request hacia main, pero no hagas merge: el merge se hace cuando todos los
  stages del pipeline pasan en verde.
- Al final, recorre validacion.md y dime qué criterios puedo comprobar ahora
  y cómo.
```

Sube los cambios y abre un Pull Request:

```bash
git add .
git commit -m "feat: <fase> según spec"
git push -u origin <nombre-de-la-rama>
```

✅ Checkpoint: en el Pull Request ves los stages del pipeline. El primero en correr es el de calidad shift-left, y todos terminan en verde.

### 7. Valida contra la spec

Ejecuta lo que dice `validacion.md` (por ejemplo, las consultas en el SQL Editor de Databricks). Revisa también la tabla de rechazados: cada registro con error tiene que estar ahí, con su motivo. Si todo cumple, haz merge del Pull Request a `main`. Si no, **corrige la spec o el código**, pero no "lo dejes pasar".

✅ Checkpoint: cada criterio de `validacion.md` está marcado como cumplido.

### 8. Repite con la fase 2

Vuelve al paso 5 con la fase 2 del roadmap. Son solo dos fases: la **fase 1** (diseño, modelado y calidad shift-left) y la **fase 2** (pipeline de punta a punta: Bronze, calidad y rechazados, Gold y monitoreo). Cada una tiene su propia rama y su propio Pull Request. Al terminar la fase 2, el pipeline completo corre con solo tus 3 secrets.

---

## El dato: `customers.csv`

Columnas: `customer_id`, `name`, `age`, `country` (código de 2 letras), `email`.

El archivo trae a propósito algunos problemas de calidad (nombres vacíos, países vacíos, edades no numéricas, menores de edad, correos mal formados, duplicados). **No los corrijas a mano**: que tu spec diga qué hacer con ellos.

## Preguntas frecuentes

**¿Tengo que usar Databricks?** No. Si cambias de plataforma, actualiza `constitucion/stack-tecnologico.md` y las specs de cada feature siguen sirviendo.

**¿Qué pasa si el asistente escribe código antes de que apruebe la spec?** Detenlo y recuérdale la regla del prompt: primero preguntas, después spec, después código.

**¿Puedo editar la spec a mano?** Sí, y es buena práctica. La spec es tuya.

## Créditos

Taller del Módulo de Operaciones (DevSecOps / DataOps), UTEC Posgrado. Basado en el flujo de prompts de [Coding-Latam/taller-sdd-02](https://github.com/Coding-Latam/taller-sdd-02), adaptado a datos y al español.
