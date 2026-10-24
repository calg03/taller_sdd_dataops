"""Configuración no secreta y nombres SQL restringidos."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_config():
    return json.loads((ROOT / "config/project.json").read_text(encoding="utf-8"))


def object_suffix(pr_number=None):
    if pr_number is None:
        return ""
    if not re.fullmatch(r"[1-9][0-9]*", str(pr_number)):
        raise ValueError("INVALID_PR_NUMBER")
    return f"__pr_{pr_number}"


def sql_context(pr_number=None):
    config = load_config()
    if (config["catalog"], config["schema"]) != ("workspace", "demo"):
        raise ValueError("UNAPPROVED_NAMESPACE")
    return {"namespace": "`workspace`.`demo`", "suffix": object_suffix(pr_number)}
