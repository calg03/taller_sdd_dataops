"""Despliegue no destructivo del modelo y referencia, sin cargar clientes."""
from .model_contract import assert_table, contracts, reference_rows, validate_model
from .model_permissions import apply_permissions, validate_permissions
from .project_config import ROOT, load_config


def execute_template(cursor, path, context):
    sql = path.read_text(encoding="utf-8").format_map(context)
    for statement in sql.split(";"):
        if statement.strip():
            cursor.execute(statement)


def deploy_model(cursor, context, run_id, groups, on_audit_ready):
    folder = ROOT / "sql/model"
    execute_template(cursor, folder / "000_schema.sql", context)
    # Verificar todo lo existente antes de crear objetos o cargar referencia.
    for name in contracts():
        assert_table(cursor, context, name, allow_missing=True)
    for path in sorted(folder.glob("0[1-7]0_*.sql")):
        execute_template(cursor, path, context)
    on_audit_ready()
    seed = (ROOT / "sql/reference/seed_countries.sql").read_text(encoding="utf-8").format_map(context)
    for row in reference_rows():
        cursor.execute(seed, {"code": row["country_code"], "name": row["country_name"],
                              "region": row["region"], "version": load_config()["reference_version"],
                              "run_id": run_id})
    execute_template(cursor, folder / "080_consumer_views.sql", context)
    apply_permissions(cursor, context, groups)
    validate_model(cursor, context)
    validate_permissions(cursor, context, groups)
