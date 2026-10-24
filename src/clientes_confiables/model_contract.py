"""Validación remota de contratos, sin consultas de datos personales."""
import csv
import json

from .project_config import ROOT, load_config


def contracts():
    return json.loads((ROOT / "config/model.json").read_text(encoding="utf-8"))


def canonical_type(value):
    return value.upper().replace(" ", "").replace("INTEGER", "INT")


def table_name(context, name):
    if name not in contracts() and name not in (
        "customers_current", "customer_contacts", "contactability_current"
    ):
        raise ValueError("UNKNOWN_OBJECT")
    return f'{context["namespace"]}.`{name}{context["suffix"]}`'


def assert_table(cursor, context, name, allow_missing=False):
    cursor.execute(
        "SELECT column_name, full_data_type, is_nullable "
        "FROM workspace.information_schema.columns "
        "WHERE table_schema = :schema AND table_name = :table ORDER BY ordinal_position",
        {"schema": "demo", "table": name + context["suffix"]},
    )
    actual = [(r[0], canonical_type(r[1]), r[2] == "YES") for r in cursor.fetchall()]
    if allow_missing and not actual:
        return
    expected = [(n, canonical_type(t), nullable) for n, t, nullable in contracts()[name]]
    if actual != expected:
        raise ValueError("MODEL_CONTRACT_MISMATCH")


def reference_rows():
    with (ROOT / load_config()["reference"]).open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 5 or len({r["country_code"] for r in rows}) != 5:
        raise ValueError("INVALID_COUNTRY_REFERENCE")
    return rows


def validate_model(cursor, context):
    for name in contracts():
        assert_table(cursor, context, name)
    cursor.execute(f"SELECT country_code, country_name, region FROM {table_name(context, 'countries_reference')}")
    actual = sorted(tuple(row) for row in cursor.fetchall())
    expected = sorted((r["country_code"], r["country_name"], r["region"]) for r in reference_rows())
    if actual != expected:
        raise ValueError("REFERENCE_MISMATCH")
    for view in ("customers_current", "customer_contacts", "contactability_current"):
        cursor.execute(f"SELECT * FROM {table_name(context, view)} LIMIT 0")
