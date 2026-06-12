"""UST utility: PostgreSQL client wrapper with connection pooling.

Standard pattern used in UST backend services to manage Postgres connections
with a context-manager interface and structured error logging.
"""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Generator

import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)

_DEFAULT_DSN = (
    "host={host} port={port} dbname={dbname} user={user} password={password}"
)


def build_dsn(
    host: str | None = None,
    port: int | str | None = None,
    dbname: str | None = None,
    user: str | None = None,
    password: str | None = None,
) -> str:
    """Build a psycopg DSN string from kwargs or environment variables."""
    return _DEFAULT_DSN.format(
        host=host or os.environ.get("POSTGRES_HOST", "localhost"),
        port=port or os.environ.get("POSTGRES_PORT", "5432"),
        dbname=dbname or os.environ.get("POSTGRES_DB", "app"),
        user=user or os.environ.get("POSTGRES_USER", "app"),
        password=password or os.environ.get("POSTGRES_PASSWORD", ""),
    )


class DBClient:
    """Thin wrapper around psycopg providing a context-manager query interface."""

    def __init__(self, dsn: str | None = None) -> None:
        self._dsn = dsn or build_dsn()

    @contextmanager
    def connection(self) -> Generator[psycopg.Connection, None, None]:
        """Yield an open psycopg connection; commits on clean exit, rolls back on error."""
        with psycopg.connect(self._dsn, row_factory=dict_row) as conn:
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def execute(self, sql: str, params: tuple | None = None) -> list[dict[str, Any]]:
        """Execute a SQL statement and return all rows as dicts."""
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                if cur.description:
                    return cur.fetchall()
                return []

    def execute_many(self, sql: str, params_seq: list[tuple]) -> None:
        """Execute a SQL statement for each params tuple (bulk insert/update)."""
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.executemany(sql, params_seq)


def get_client(dsn: str | None = None) -> DBClient:
    """Factory — returns a DBClient for the given DSN (or env-derived default)."""
    return DBClient(dsn)
