"""Solo lectura: comprueba modelo, referencia y grants remotos."""
import argparse

import _bootstrap  # noqa: F401
from clientes_confiables.databricks_connection import connect
from clientes_confiables.model_contract import validate_model
from clientes_confiables.model_permissions import configured_groups, validate_permissions
from clientes_confiables.project_config import sql_context


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr-number")
    args = parser.parse_args()
    try:
        context = sql_context(args.pr_number)
        groups = configured_groups()
        with connect() as connection, connection.cursor() as cursor:
            validate_model(cursor, context)
            validate_permissions(cursor, context, groups)
        print("MODEL_VALIDATION_SUCCESS")
        return 0
    except Exception:
        print("MODEL_VALIDATION_FAILED: revisar prerrequisitos y contrato sin publicar datos personales.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
