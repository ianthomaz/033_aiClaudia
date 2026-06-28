#!/usr/bin/env python3
"""Pick diverse suggestion chips for the frontend."""
from __future__ import annotations

import random

from chip_db import connect

FALLBACK_CHIPS = [
    "Onde foi parar minha chave?",
    "Me dá um conselho de vida",
    "Como vai ser meu dia?",
    "Por que eu esqueço as senhas?",
]


def pick_suggestion_chips(count: int = 4) -> tuple[list[str], int, str | None]:
    """Return (texts, pool_size, latest_created_at iso)."""
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) FROM suggestion_chips WHERE is_active = TRUE
                """
            )
            pool_size = int(cur.fetchone()[0])
            if pool_size == 0:
                return FALLBACK_CHIPS[:count], 0, None

            cur.execute(
                """
                SELECT MAX(created_at) FROM suggestion_chips WHERE is_active = TRUE
                """
            )
            latest = cur.fetchone()[0]

            cur.execute(
                """
                SELECT DISTINCT topic FROM suggestion_chips WHERE is_active = TRUE
                """
            )
            topics = [r[0] for r in cur.fetchall()]
            random.shuffle(topics)

            picked_ids: list[int] = []
            texts: list[str] = []

            for topic in topics:
                if len(texts) >= count:
                    break
                cur.execute(
                    """
                    SELECT chip_id, text FROM suggestion_chips
                    WHERE is_active = TRUE AND topic = %s
                    ORDER BY RANDOM() LIMIT 1
                    """,
                    (topic,),
                )
                row = cur.fetchone()
                if row and row[0] not in picked_ids:
                    picked_ids.append(row[0])
                    texts.append(row[1])

            if len(texts) < count:
                cur.execute(
                    """
                    SELECT chip_id, text FROM suggestion_chips
                    WHERE is_active = TRUE AND chip_id != ALL(%s)
                    ORDER BY RANDOM() LIMIT %s
                    """,
                    (picked_ids or [0], count - len(texts)),
                )
                for row in cur.fetchall():
                    if row[0] not in picked_ids:
                        picked_ids.append(row[0])
                        texts.append(row[1])

            return texts[:count], pool_size, latest.isoformat() if latest else None
    finally:
        conn.close()
