"""Permisos explícitos; los grupos reales son un prerrequisito no secreto."""
import re

from .model_contract import contracts, table_name
from .project_config import ROOT, load_config


def configured_groups():
    groups = load_config()["groups"]
    roles = {"engineering", "governance", "marketing", "bi"}
    if set(groups) != roles or not all(
        isinstance(value, str) and re.fullmatch(r"[\w .@-]{1,128}", value)
        for value in groups.values()
    ):
        raise ValueError("ACCESS_GROUPS_NOT_CONFIGURED")
    if len(set(groups.values())) != 4:
        raise ValueError("ACCESS_GROUPS_MUST_DIFFER")
    return groups


def apply_permissions(cursor, context, groups):
    template = (ROOT / "sql/model/090_permissions.sql").read_text(encoding="utf-8")
    for role, principal in groups.items():
        objects = list(contracts()) + ["customers_current"]
        if role == "marketing":
            objects = ["customer_contacts"]
        elif role == "bi":
            objects = ["contactability_current"]
        for name in objects:
            substitutions = dict(context, principal=f"`{principal}`",
                                 object_name=table_name(context, name),
                                 object_type="TABLE" if name in contracts() else "VIEW")
            sql = template.format_map(substitutions)
            for statement in sql.split(";"):
                if statement.strip():
                    cursor.execute(statement)


def validate_permissions(cursor, context, groups):
    # Detectar grants amplios conocidos; no se revocan permisos heredados automáticamente.
    allowed_raw = {groups["engineering"], groups["governance"]}
    for name in contracts():
        cursor.execute(f"SHOW GRANTS ON TABLE {table_name(context, name)}")
        rows = cursor.fetchall()
        for row in rows:
            principal, action = row[0], str(row[1]).upper()
            if action in ("SELECT", "ALL PRIVILEGES") and principal in (
                groups["marketing"], groups["bi"], "account users", "users"
            ) and principal not in allowed_raw:
                raise ValueError("BROAD_RAW_ACCESS_DETECTED")
    # Esta inspección no reemplaza pruebas de acceso con identidades reales (V19).
