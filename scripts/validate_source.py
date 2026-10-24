"""Stage 1: diagnóstico agregado, sin acceso a Databricks."""
import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import _bootstrap  # noqa: F401
from clientes_confiables.customer_quality import StructureError, validate_source
from clientes_confiables.project_config import ROOT, load_config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path)
    parser.add_argument("--report", type=Path, default=ROOT / "artifacts/quality.json")
    args = parser.parse_args()
    config = load_config()
    started = datetime.now(timezone.utc).isoformat()
    try:
        result = validate_source(args.source or ROOT / config["source"],
                                 ROOT / config["reference"], config)
    except (StructureError, OSError) as error:
        code = str(error) if isinstance(error, StructureError) else "SOURCE_IO_ERROR"
        result = {"status": "FAILED", "error_code": code}
    result.update(run_id=str(uuid.uuid4()), started_at=started,
                  finished_at=datetime.now(timezone.utc).isoformat())
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
