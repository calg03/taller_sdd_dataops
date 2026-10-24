"""Solo lectura: comprueba modelo, referencia y grants remotos."""
import argparse

import _bootstrap  # noqa: F401
from clientes_confiables.databricks_connection import connect
from clientes_confiables.model_contract import validate_model
from clientes_confiables.model_permissions import configured_groups, validate_permissions
from clientes_confiables.project_config import deployment_mode, sql_context


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr-number")
    args = parser.parse_args()
    try:
        context = sql_context(args.pr_number)
        mode = deployment_mode()
        with connect() as connection, connection.cursor() as cursor:
            validate_model(cursor, context)
            if mode == "managed":
                validate_permissions(cursor, context, configured_groups())
        if mode == "free_edition":
            print("WARNING: V19_PENDING_NO_CONSUMER_GRANTS")
        print("MODEL_VALIDATION_SUCCESS")
        return 0
    except Exception:
        print("MODEL_VALIDATION_FAILED: revisar prerrequisitos y contrato sin publicar datos personales.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
