#!/usr/bin/env python3
"""Shared DB helpers for suggestion chips."""
from __future__ import annotations

import os
from pathlib import Path

import psycopg2

DEPLOY_DIR = Path(__file__).resolve().parent


def db_config() -> dict:
    return {
        "host": os.getenv("DB_HOST", "database"),
        "port": int(os.getenv("DB_PORT", "5432")),
        "database": os.getenv("DB_NAME", "aiclaudia"),
        "user": os.getenv("DB_USER", "aiclaudia"),
        "password": os.getenv("DB_PASSWORD"),
    }


def connect():
    return psycopg2.connect(**db_config())


def ensure_schema() -> None:
    sql = (DEPLOY_DIR / "migrate_suggestion_chips.sql").read_text(encoding="utf-8")
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    finally:
        conn.close()


def count_active_chips() -> int:
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM suggestion_chips WHERE is_active = TRUE")
            return int(cur.fetchone()[0])
    finally:
        conn.close()


def deactivate_old_chips(months: int = 3) -> int:
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE suggestion_chips
                SET is_active = FALSE, deactivated_at = NOW()
                WHERE is_active = TRUE
                  AND created_at < NOW() - (%s || ' months')::INTERVAL
                """,
                (str(months),),
            )
            n = cur.rowcount
        conn.commit()
        return n
    finally:
        conn.close()
