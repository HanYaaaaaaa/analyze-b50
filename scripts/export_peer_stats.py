#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "assets" / "peer_stats.zip"


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def achievement_percent(value: Any) -> float:
    v = safe_float(value, 0.0)
    if v > 101:
        return round(v / 10000.0, 4)
    return round(v, 4)


def rating_bucket(rating: int, size: int) -> str:
    start = (rating // size) * size
    return f"{start}-{start + size - 1}"


def iter_b50_records(db_path: Path):
    con = sqlite3.connect(db_path)
    try:
        rows = con.execute(
            """
            SELECT rating, raw_payload_json
            FROM user_snapshot
            WHERE snapshot_type = 'b50'
              AND raw_payload_json IS NOT NULL
              AND rating > 0
            """
        )
        for rating, raw in rows:
            try:
                payload = json.loads(raw)
            except Exception:
                continue
            user_rating = safe_int(payload.get("rating"), safe_int(rating, 0))
            user_rating_block = payload.get("userRating") or {}
            old_list = user_rating_block.get("ratingList") or []
            new_list = user_rating_block.get("newRatingList") or []
            b50 = list(old_list[:35]) + list(new_list[:15])
            if len(b50) < 20:
                continue
            yield user_rating, b50
    finally:
        con.close()


def build_peer_stats(db_path: Path, bucket_size: int = 200, min_sample: int = 3) -> dict:
    buckets: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    bucket_user_count: dict[str, int] = defaultdict(int)
    total_users = 0
    for rating, b50 in iter_b50_records(db_path):
        bucket = rating_bucket(rating, bucket_size)
        bucket_user_count[bucket] += 1
        total_users += 1
        seen_keys: set[str] = set()
        for item in b50:
            music_id = str(item.get("musicId") or item.get("music_id") or item.get("song_id") or "")
            level = safe_int(item.get("level", item.get("level_index")), -1)
            if not music_id or level < 0:
                continue
            key = f"{music_id}:{level}"
            if key in seen_keys:
                continue
            seen_keys.add(key)
            buckets[bucket][key].append(achievement_percent(item.get("achievement", item.get("achievements"))))

    out_buckets: dict[str, dict] = {}
    for bucket, charts in buckets.items():
        user_count = max(1, bucket_user_count[bucket])
        out_charts = {}
        for key, values in charts.items():
            if len(values) < min_sample:
                continue
            values_sorted = sorted(values)
            out_charts[key] = {
                "sample_count": len(values),
                "avg_achievement": round(sum(values) / len(values), 4),
                "p50_achievement": round(statistics.median(values_sorted), 4),
                "b50_appear_rate": round(len(values) / user_count, 6),
            }
        if out_charts:
            out_buckets[bucket] = {
                "player_count": user_count,
                "charts": out_charts,
            }

    return {
        "version": datetime.now().strftime("%Y-%m-%d"),
        "rating_bucket_size": bucket_size,
        "source": "anonymous local aggregate",
        "total_players": total_users,
        "min_sample": min_sample,
        "buckets": dict(sorted(out_buckets.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Export anonymous peer stats zip from local B50 snapshots.")
    parser.add_argument("--db", required=True, help="Path to logout.sqlite3 or another sqlite DB with user_snapshot")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output peer_stats.zip path")
    parser.add_argument("--bucket-size", type=int, default=200)
    parser.add_argument("--min-sample", type=int, default=3)
    args = parser.parse_args()

    stats = build_peer_stats(Path(args.db), args.bucket_size, args.min_sample)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(stats, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        zf.writestr("peer_stats.json", data)
    print(f"Wrote {out} ({len(data)} bytes json, {stats['total_players']} players)")


if __name__ == "__main__":
    main()
