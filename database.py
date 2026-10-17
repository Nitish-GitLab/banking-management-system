"""MySQL access. Read-only: the app only ever runs SELECT statements."""
from __future__ import annotations

import os
import re

import mysql.connector
import pandas as pd

import config as cfg


class ConfigError(Exception):
    """Missing or invalid configuration (for example a missing .env value)."""


class DatabaseError(Exception):
    """The database could not be reached or queried."""


_IDENTIFIER = re.compile(r"^[A-Za-z0-9_]+$")


def _settings() -> dict:
    missing = [name for name in ("DB_USER", "DB_PASSWORD", "DB_NAME") if os.getenv(name) is None]
    if missing:
        hint = "" if cfg.DOTENV_AVAILABLE else " (python-dotenv is not installed, so .env was not read)"
        raise ConfigError(
            "Missing environment variable(s): " + ", ".join(missing) + hint + ". "
            "Copy .env.example to .env and fill in your MySQL details."
        )
    try:
        port = int(os.getenv("DB_PORT", "3306"))
    except ValueError as exc:
        raise ConfigError("DB_PORT must be a whole number.") from exc
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": port,
        "user": os.environ["DB_USER"],
        "password": os.environ["DB_PASSWORD"],
        "database": os.environ["DB_NAME"],
        "connection_timeout": 10,
    }


def load_table(table: str | None = None) -> pd.DataFrame:
    """Read an entire table into a DataFrame (SELECT only, connection always closed)."""
    table = table or cfg.TABLE_NAME
    if not _IDENTIFIER.match(table):  # the table name is interpolated, so validate it strictly
        raise ConfigError(f"Invalid table name {table!r}: use letters, digits and underscores only.")

    settings = _settings()
    connection = None
    try:
        connection = mysql.connector.connect(**settings)
        cursor = connection.cursor()
        try:
            cursor.execute(f"SELECT * FROM `{table}`")
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
        finally:
            cursor.close()
    except mysql.connector.Error as exc:
        raise DatabaseError(
            f"Could not read `{table}` from MySQL database `{settings['database']}` on "
            f"{settings['host']}:{settings['port']}. MySQL said: {exc}"
        ) from exc
    finally:
        if connection is not None and connection.is_connected():
            connection.close()

    # coerce_float turns MySQL DECIMAL values into floats
    return pd.DataFrame.from_records(rows, columns=columns, coerce_float=True)
