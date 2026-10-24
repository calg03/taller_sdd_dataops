"""Stage 2: validar primero, desplegar después; nunca imprimir errores con secretos."""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import _bootstrap  # noqa: F401
from clientes_confiables.customer_quality import validate_source
from clientes_confiables.databricks_connection import connect
from clientes_confiables.model_deployment import deploy_model
from clientes_confiables.model_permissions import configured_groups
from clientes_confiables.project_config import ROOT, load_config, sql_context
from clientes_confiables.stage_audit import record_stage


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pr-number")
    parser.add_argument("--report", type=Path, default=ROOT / "artifacts/quality.json")
    args = parser.parse_args()
    started = datetime.now(timezone.utc)
    output = {"status": "FAILED", "stage": "despliegue-modelo"}
    try:
        config = load_config()
        report = json.loads(args.report.read_text(encoding="utf-8"))
        current = validate_source(ROOT / config["source"], ROOT / config["reference"], config)
        if report["status"] != "SUCCESS" or current["status"] != "SUCCESS" or current["snapshot_id"] != report["snapshot_id"]:
            raise ValueError("SHIFT_LEFT_REQUIRED")
        if os.getenv("GITHUB_EVENT_NAME") == "pull_request" and not args.pr_number:
            raise ValueError("PR_ISOLATION_REQUIRED")
        context = sql_context(args.pr_number)
        context["environment"] = f"pr_{args.pr_number}" if args.pr_number else "production"
        groups = configured_groups()
        with connect() as connection, connection.cursor() as cursor:
            cursor.execute("SET TIME ZONE 'UTC'")
            audit_ready = False

            def audit_start():
                nonlocal audit_ready
                audit_ready = True
                record_stage(cursor, context, report, "calidad-shift-left", "SUCCESS", report["started_at"])
                record_stage(cursor, context, report, "despliegue-modelo", "RUNNING", started)

            try:
                deploy_model(cursor, context, report["run_id"], groups, audit_start)
                record_stage(cursor, context, report, "despliegue-modelo", "SUCCESS", started)
                output = {"status": "SUCCESS", "stage": "despliegue-modelo", "run_id": report["run_id"]}
            except Exception:
                if audit_ready:
                    try:
                        record_stage(cursor, context, report, "despliegue-modelo", "FAILED", started, "DEPLOYMENT_FAILED")
                    except Exception:
                        pass  # CI conserva siempre el fallo aunque el warehouse sea inaccesible.
                raise
    except Exception as error:
        safe_codes = {"ACCESS_GROUPS_NOT_CONFIGURED", "ACCESS_GROUPS_MUST_DIFFER", "SHIFT_LEFT_REQUIRED",
                      "PR_ISOLATION_REQUIRED", "MISSING_DATABRICKS_SECRETS", "MODEL_CONTRACT_MISMATCH",
                      "BROAD_RAW_ACCESS_DETECTED", "INVALID_PR_NUMBER", "UNAPPROVED_NAMESPACE"}
        code = str(error) if type(error) is ValueError and str(error) in safe_codes else "DEPLOYMENT_FAILED"
        output["error_code"] = code
    output["started_at"] = started.isoformat()
    output["finished_at"] = datetime.now(timezone.utc).isoformat()
    target = ROOT / "artifacts/deployment.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps(output, indent=2))
    return 0 if output["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
