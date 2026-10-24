"""Conexión de stage 2; importación diferida y errores sanitizados."""
import logging
import os

from .project_config import load_config


def connect():
    from databricks import sql

    names = ("DATABRICKS_HOST", "DATABRICKS_HTTP_PATH", "DATABRICKS_TOKEN")
    if not all(os.environ.get(name) for name in names):
        raise ValueError("MISSING_DATABRICKS_SECRETS")
    logging.getLogger("databricks").setLevel(logging.CRITICAL)
    return sql.connect(
        server_hostname=os.environ[names[0]].removeprefix("https://").rstrip("/"),
        http_path=os.environ[names[1]], access_token=os.environ[names[2]],
        _socket_timeout=load_config()["socket_timeout_seconds"],
    )
