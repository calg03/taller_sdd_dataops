"""Registro idempotente por ejecución, stage e intento."""
import os
from datetime import datetime, timezone

from .model_contract import table_name


def record_stage(cursor, context, report, stage, status, started, error=None):
    values = {
        "run_id": report["run_id"], "snapshot_id": report.get("snapshot_id"),
        "stage_name": stage, "attempt_number": int(os.getenv("GITHUB_RUN_ATTEMPT", "1")),
        "status": status, "started_at": started,
        "finished_at": None if status == "RUNNING" else datetime.now(timezone.utc),
        "input_rows": report.get("input_rows"), "output_rows": None,
        "rejected_rows": report.get("rejected_rows"), "rejection_pct": report.get("rejection_pct"),
        "error_code": error, "error_summary": error,
        "commit_sha": os.getenv("GITHUB_SHA", "local"), "environment": context["environment"],
    }
    if stage == "calidad-shift-left":
        values["finished_at"] = report["finished_at"]
    columns = list(values)
    source = ", ".join(f":{key} AS {key}" for key in columns)
    condition = " AND ".join(f"t.{key} = s.{key}" for key in ("run_id", "stage_name", "attempt_number"))
    cursor.execute(
        f"MERGE INTO {table_name(context, 'pipeline_stage_runs')} t "
        f"USING (SELECT {source}) s ON {condition} "
        "WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *", values,
    )
