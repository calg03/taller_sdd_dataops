"""Evaluación local compartida; no importa clientes ni credenciales de Databricks."""
import csv
import hashlib
import io
import re
from collections import Counter
from dataclasses import dataclass

COLUMNS = ["customer_id", "name", "age", "country", "email"]


class StructureError(ValueError):
    """Error estructural con código sanitizado."""


@dataclass
class Evaluation:
    position: int
    original: dict
    normalized: dict
    reasons: list
    warnings: list
    age: int | None
    is_adult: bool
    has_valid_email: bool

    @property
    def is_contactable(self):
        return not self.reasons and self.is_adult and self.has_valid_email


def read_source(path):
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        if next(reader, None) != COLUMNS:
            raise StructureError("INVALID_HEADER")
        rows = []
        for fields in reader:
            if len(fields) != len(COLUMNS):
                raise StructureError("INVALID_FIELD_COUNT")
            rows.append(dict(zip(COLUMNS, fields)))
        if not rows:
            raise StructureError("EMPTY_SOURCE")
        return hashlib.sha256(raw).hexdigest(), rows
    except (UnicodeError, csv.Error):
        raise StructureError("UNREADABLE_CSV") from None


def valid_email(value):
    if not value or re.search(r"\s", value) or value.count("@") != 1:
        return False
    local, domain = value.split("@")
    if not re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+", local):
        return False
    if local.startswith(".") or local.endswith(".") or ".." in local:
        return False
    labels = domain.split(".")
    return len(labels) >= 2 and all(
        re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?", label)
        for label in labels
    )


def evaluate_row(original, position, countries, adult_age):
    normalized = {key: value.strip() for key, value in original.items()}
    normalized["country"] = normalized["country"].upper()
    reasons = []
    for field, code in (("customer_id", "CUSTOMER_ID_MISSING"), ("name", "NAME_MISSING")):
        if not normalized[field]:
            reasons.append(code)
    age_text = normalized["age"]
    age = None
    if not age_text:
        reasons.append("AGE_MISSING")
    elif not re.fullmatch(r"[0-9]+", age_text) or len(age_text.lstrip("0")) > 10:
        reasons.append("AGE_INVALID")
    else:
        age = int(age_text.lstrip("0") or "0")
        if age > 2147483647:
            age = None
            reasons.append("AGE_INVALID")
    country = normalized["country"]
    if not country:
        reasons.append("COUNTRY_MISSING")
    elif country not in countries:
        reasons.append("COUNTRY_UNKNOWN")
    email_ok = bool(valid_email(normalized["email"]))
    warnings = [] if email_ok else ["EMAIL_INVALID" if normalized["email"] else "EMAIL_MISSING"]
    return Evaluation(position, original, normalized, reasons, warnings,
                      age, age is not None and age >= adult_age, email_ok)


def selected_versions(evaluations):
    selected = {}
    for row in evaluations:
        identity = row.normalized["customer_id"]
        if identity:
            selected[identity] = row
    return list(selected.values())


def summarize(evaluations, snapshot_id, threshold):
    selected = selected_versions(evaluations)
    rejected = sum(bool(row.reasons) for row in evaluations)
    valid = [row for row in selected if not row.reasons]
    adults = sum(row.is_adult for row in selected)
    contactable = sum(row.is_contactable for row in selected)
    failed = 100 * rejected > threshold * len(evaluations)
    return {
        "snapshot_id": snapshot_id, "status": "FAILED" if failed else "SUCCESS",
        "input_rows": len(evaluations), "rejected_rows": rejected,
        "rejection_pct": 100 * rejected / len(evaluations),
        "threshold_pct": threshold,
        "reason_counts": dict(Counter(code for row in evaluations for code in row.reasons)),
        "warning_counts": dict(Counter(code for row in evaluations for code in row.warnings)),
        "unique_customers": len(selected),
        "superseded_rows": sum(bool(r.normalized["customer_id"]) for r in evaluations) - len(selected),
        "valid_selected": len(valid), "valid_minors": sum(not r.is_adult for r in valid),
        "valid_adults": sum(r.is_adult for r in valid),
        "adult_denominator": adults, "contactable_adults": contactable,
        "simulated_contactable_pct": 100 * contactable / adults if adults else None,
    }


def validate_source(path, reference, config):
    with reference.open(encoding="utf-8-sig", newline="") as stream:
        countries = {row["country_code"] for row in csv.DictReader(stream)}
    snapshot_id, rows = read_source(path)
    evaluations = [evaluate_row(row, number, countries, config["adult_age"])
                   for number, row in enumerate(rows, 1)]
    return summarize(evaluations, snapshot_id, config["rejection_threshold_pct"])
