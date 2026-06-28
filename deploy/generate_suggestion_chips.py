#!/usr/bin/env python3
"""
Fetch headlines from news_feeds.json, ask ITCS LLM for chip questions, store in DB.
Uses 2 LLM batches (5+5) and local headline twists to always reach CHIP_COUNT.
"""
from __future__ import annotations

import json
import random
import re
import sys
import uuid
from pathlib import Path

import feedparser

DEPLOY_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DEPLOY_DIR))

from chip_db import connect, deactivate_old_chips, ensure_schema
from simple_prompt_selector import call_itcs_llm_api

FEEDS_FILE = DEPLOY_DIR / "news_feeds.json"
CHIP_COUNT = 10
LLM_BATCH_SIZE = 5
LLM_BATCHES = 2

TOPIC_LABELS = {
    "international": "o mundo",
    "politics": "a política",
    "fashion": "a moda",
    "arts": "as artes",
    "sports": "o esporte",
    "dance": "a dança",
    "theater": "o teatro",
    "music": "a música",
    "science": "a ciência",
    "society": "a sociedade",
}

SYSTEM_PROMPT_BATCH = """\
Transform news headlines into chat chip questions for aiClaudia (Brazilian satirical cloud persona).
Reply with ONLY a JSON array of exactly {count} objects. Keys per object: text, topic (no other keys).
Rules:
- text: pt-BR question, 24-70 chars, surreal humor, never copy headline literally
- topic: international|politics|fashion|arts|sports|dance|theater|music|science|society
- vary topics across the batch; each chip a different topic when possible
- sensitive tragedy: absurdist dodge, no hate, no graphic violence
- compact JSON, no markdown fences, no commentary
"""


def load_headlines() -> list[dict]:
    feeds = json.loads(FEEDS_FILE.read_text(encoding="utf-8"))
    headlines: list[dict] = []
    for feed in feeds:
        topic = feed.get("topic", "society")
        url = feed.get("url", "")
        label = feed.get("label", topic)
        if not url:
            continue
        try:
            parsed = feedparser.parse(url)
            for entry in parsed.entries[:3]:
                title = (entry.get("title") or "").strip()
                link = (entry.get("link") or "").strip()
                if title:
                    headlines.append(
                        {
                            "topic": topic,
                            "headline": title,
                            "url": link,
                            "feed": label,
                        }
                    )
                    break
        except Exception as exc:
            print(f"RSS skip {label}: {exc}", file=sys.stderr)
    return headlines


def _strip_markdown_fence(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*\n?", "", raw, count=1)
        raw = re.sub(r"\n?```\s*$", "", raw)
    return raw.strip()


def _extract_json_objects(text: str) -> list[dict]:
    items: list[dict] = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] != "{":
            i += 1
            continue
        depth = 0
        in_str = False
        esc = False
        start = i
        for j in range(i, n):
            c = text[j]
            if esc:
                esc = False
                continue
            if c == "\\" and in_str:
                esc = True
                continue
            if c == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[start : j + 1])
                        if isinstance(obj, dict):
                            items.append(obj)
                    except json.JSONDecodeError:
                        pass
                    i = j + 1
                    break
        else:
            break
    return items


def _normalize_chips(data: list) -> list[dict]:
    out: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        text = (item.get("text") or "").strip()
        if not text or len(text) > 280:
            continue
        out.append(
            {
                "text": text,
                "topic": (item.get("topic") or "society").strip()[:50],
                "source_headline": (item.get("source_headline") or "").strip() or None,
                "source_url": (item.get("source_url") or "").strip() or None,
            }
        )
    return out


def parse_llm_json(raw: str) -> list[dict]:
    raw = _strip_markdown_fence(raw)
    try:
        match = re.search(r"\[[\s\S]*\]", raw)
        if match:
            data = json.loads(match.group(0))
            if isinstance(data, list):
                return _normalize_chips(data)
    except json.JSONDecodeError:
        pass
    salvaged = _normalize_chips(_extract_json_objects(raw))
    if salvaged:
        return salvaged
    raise ValueError("LLM output is not a JSON array")


def _norm_key(text: str) -> str:
    return " ".join(text.lower().split())


def build_user_message(
    headlines: list[dict],
    count: int,
    avoid: set[str] | None = None,
) -> str:
    lines = ["Headlines for this batch:"]
    for i, h in enumerate(headlines, 1):
        lines.append(
            f"{i}. topic={h['topic']} | headline={h['headline']} | url={h['url']}"
        )
    lines.append(f"\nGenerate exactly {count} chip questions as JSON array.")
    if avoid:
        sample = list(avoid)[:8]
        lines.append("Avoid repeating or paraphrasing these existing chips:")
        for t in sample:
            lines.append(f"- {t}")
    return "\n".join(lines)


def local_chip_from_headline(h: dict, variant: int) -> dict:
    """Surreal Claudia-style chip from headline context without copying the title."""
    topic = h["topic"]
    label = TOPIC_LABELS.get(topic, "o dia")
    templates = [
        f"Se {label} mandou push hoje, abro ou finjo spam?",
        f"{label.capitalize()} parece série ou reality hoje?",
        f"Isso em {label} é tendência ou imprevisto premium?",
        f"Nuvem diz: {label} pede drama ou ironia leve?",
        f"Plot twist em {label} ou eu que não dormi?",
        f"Devo preocupar com {label} ou só com o trânsito?",
        f"Se {label} era novela, em que capítulo estamos?",
        f"{label.capitalize()} vale um cafezinho de desespero?",
        f"Isso em {label} é filme ou meme caro?",
        f"Spoiler de {label} ou só ruído de fundo?",
    ]
    text = templates[variant % len(templates)]
    if len(text) > 70:
        text = text[:67] + "..."
    return {
        "text": text,
        "topic": topic,
        "source_headline": h["headline"],
        "source_url": h["url"],
    }


def attach_sources(chips: list[dict], headlines: list[dict]) -> None:
    headline_by_topic = {h["topic"]: h for h in headlines}
    for chip in chips:
        if chip.get("source_headline"):
            continue
        src = headline_by_topic.get(chip["topic"])
        if src:
            chip["source_headline"] = src["headline"]
            chip["source_url"] = src["url"]


def merge_unique(chips: list[dict], seen: set[str]) -> list[dict]:
    added: list[dict] = []
    for chip in chips:
        key = _norm_key(chip["text"])
        if key in seen:
            continue
        seen.add(key)
        added.append(chip)
    return added


def call_llm_batch(
    headlines: list[dict],
    count: int,
    seen: set[str],
    batch_idx: int,
) -> list[dict]:
    avoid_texts = {_norm_key(t) for t in seen}
    user_msg = build_user_message(headlines, count, avoid_texts)
    system = SYSTEM_PROMPT_BATCH.format(count=count)
    result = call_itcs_llm_api(
        system,
        user_msg,
        user_id=f"aiclaudia:chip-cron:{batch_idx}",
        model_alias="smart",
    )
    if not result.get("success"):
        print(f"LLM batch {batch_idx} failed: {result.get('error')}", file=sys.stderr)
        return []
    try:
        parsed = parse_llm_json(result["response"])
        return merge_unique(parsed, seen)
    except (json.JSONDecodeError, ValueError) as exc:
        print(
            f"LLM batch {batch_idx} JSON parse failed: {exc}\n"
            f"Raw: {result['response'][:400]}",
            file=sys.stderr,
        )
        return []


def fill_local(
    chips: list[dict],
    headlines: list[dict],
    seen: set[str],
    target: int,
) -> list[dict]:
    """Fill remaining slots with local headline-based chips (rotate topics)."""
    used_topics = {c["topic"] for c in chips}
    ordered = sorted(headlines, key=lambda h: (h["topic"] in used_topics, random.random()))
    variant = len(chips)
    for h in ordered:
        if len(chips) >= target:
            break
        local = local_chip_from_headline(h, variant)
        key = _norm_key(local["text"])
        if key in seen:
            variant += 1
            local = local_chip_from_headline(h, variant)
            key = _norm_key(local["text"])
        if key in seen:
            continue
        seen.add(key)
        chips.append(local)
        used_topics.add(h["topic"])
        variant += 1

    while len(chips) < target and headlines:
        h = headlines[variant % len(headlines)]
        local = local_chip_from_headline(h, variant + 10)
        key = _norm_key(local["text"])
        if key not in seen:
            seen.add(key)
            chips.append(local)
        variant += 1
    return chips


def insert_chips(chips: list[dict], batch_id: str) -> int:
    conn = connect()
    n = 0
    try:
        with conn.cursor() as cur:
            for chip in chips:
                cur.execute(
                    """
                    INSERT INTO suggestion_chips
                    (text, topic, source_headline, source_url, batch_id, is_active)
                    VALUES (%s, %s, %s, %s, %s, TRUE)
                    """,
                    (
                        chip["text"],
                        chip["topic"],
                        chip.get("source_headline"),
                        chip.get("source_url"),
                        batch_id,
                    ),
                )
                n += 1
        conn.commit()
    finally:
        conn.close()
    return n


def generate() -> int:
    ensure_schema()
    headlines = load_headlines()
    if not headlines:
        print("No headlines fetched; aborting generation.", file=sys.stderr)
        return 1

    random.shuffle(headlines)
    seen: set[str] = set()
    chips: list[dict] = []

    chunk_size = max(1, len(headlines) // LLM_BATCHES)
    for batch_idx in range(LLM_BATCHES):
        start = batch_idx * chunk_size
        end = start + chunk_size if batch_idx < LLM_BATCHES - 1 else len(headlines)
        batch_headlines = headlines[start:end] or headlines
        need = min(LLM_BATCH_SIZE, CHIP_COUNT - len(chips))
        if need <= 0:
            break
        added = call_llm_batch(batch_headlines, need, seen, batch_idx)
        chips.extend(added)
        print(f"LLM batch {batch_idx + 1}: +{len(added)} chips (total {len(chips)})")

    if len(chips) < CHIP_COUNT:
        before = len(chips)
        chips = fill_local(chips, headlines, seen, CHIP_COUNT)
        local_added = len(chips) - before
        if local_added:
            print(f"Local fill: +{local_added} chips (total {len(chips)})")

    if len(chips) < 4:
        print(f"Too few chips ({len(chips)}); aborting.", file=sys.stderr)
        return 1

    attach_sources(chips, headlines)
    batch_id = str(uuid.uuid4())
    inserted = insert_chips(chips[:CHIP_COUNT], batch_id)
    archived = deactivate_old_chips(3)
    print(
        f"Generated {inserted} chips (batch {batch_id}). "
        f"Deactivated {archived} older than 3 months."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(generate())
