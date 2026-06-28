#!/usr/bin/env python3
"""Load initial suggestion chips from JSON if pool is below threshold."""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

from chip_db import connect, count_active_chips, ensure_schema

DEPLOY_DIR = Path(__file__).resolve().parent
SEED_FILE = DEPLOY_DIR / "suggestion_chips_seed.json"
MIN_ACTIVE = int(__import__("os").getenv("CHIP_SEED_MIN", "30"))


def seed_if_needed(force: bool = False) -> int:
    ensure_schema()
    active = count_active_chips()
    if not force and active >= MIN_ACTIVE:
        print(f"Seed skipped: {active} active chips (min {MIN_ACTIVE}).")
        return 0

    rows = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    batch_id = str(uuid.uuid4())
    conn = connect()
    inserted = 0
    try:
        with conn.cursor() as cur:
            for row in rows:
                text = (row.get("text") or "").strip()
                topic = (row.get("topic") or "society").strip()
                if not text or len(text) > 280:
                    continue
                cur.execute(
                    """
                    INSERT INTO suggestion_chips (text, topic, batch_id, is_active)
                    SELECT %s, %s, %s, TRUE
                    WHERE NOT EXISTS (
                        SELECT 1 FROM suggestion_chips
                        WHERE text = %s AND is_active = TRUE
                    )
                    """,
                    (text, topic, batch_id, text),
                )
                inserted += cur.rowcount
        conn.commit()
    finally:
        conn.close()
    print(f"Seeded {inserted} chips (batch {batch_id}). Active total: {count_active_chips()}.")
    return inserted


if __name__ == "__main__":
    force = "--force" in sys.argv
    seed_if_needed(force=force)
