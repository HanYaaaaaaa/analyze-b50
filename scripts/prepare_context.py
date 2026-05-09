#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import json
import math
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

DIFF_NAMES = {
    0: "Basic",
    1: "Advanced",
    2: "Expert",
    3: "Master",
    4: "Re:MASTER",
}

FC_LABELS = {
    "fc": "FC",
    "fcp": "FC+",
    "ap": "AP",
    "app": "AP+",
}


def load_json(path: Path) -> Any:
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as zf:
            json_names = [name for name in zf.namelist() if name.endswith(".json")]
            target = "peer_stats.json" if "peer_stats.json" in json_names else (json_names[0] if json_names else "")
            if not target:
                raise ValueError(f"No JSON file found in {path}")
            with zf.open(target) as fh:
                return json.loads(fh.read().decode("utf-8"))
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            return json.load(fh)
    return json.loads(path.read_text(encoding="utf-8"))


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def avg(values: list[float]) -> float | None:
    nums = [v for v in values if v is not None]
    if not nums:
        return None
    return round(sum(nums) / len(nums), 4)


def median(values: list[float]) -> float | None:
    nums = sorted(v for v in values if v is not None)
    if not nums:
        return None
    return round(nums[len(nums) // 2], 4)


def rating_bucket(rating: int, size: int = 200) -> str:
    start = (rating // size) * size
    return f"{start}-{start + size - 1}"


def load_peer_stats(path_arg: str | None) -> tuple[dict | None, Path | None]:
    candidates = []
    if path_arg:
        candidates.append(Path(path_arg))
    candidates.extend([ASSETS / "peer_stats.zip", ASSETS / "peer_stats.json", ASSETS / "peer_stats.json.gz"])
    for path in candidates:
        if path.exists():
            return load_json(path), path
    return None, None


def music_index(music_data: list[dict]) -> dict[str, dict]:
    return {str(item.get("id")): item for item in music_data if isinstance(item, dict) and item.get("id") is not None}


def normalize_song(raw: dict, bucket: str, music_map: dict[str, dict], chart_summary: dict[str, dict]) -> dict:
    sid = str(raw.get("song_id") or raw.get("id") or "")
    level_index = safe_int(raw.get("level_index"), -1)
    music = music_map.get(sid) or {}
    title = str(raw.get("title") or music.get("title") or f"#{sid}")
    ds = safe_float(raw.get("ds"), 0.0)
    if not ds and isinstance(music.get("ds"), list) and 0 <= level_index < len(music["ds"]):
        ds = safe_float(music["ds"][level_index], 0.0)
    summary = chart_summary.get(sid) or {}
    return {
        "bucket": bucket,
        "music_id": sid,
        "title": title,
        "type": raw.get("type") or music.get("type"),
        "level": raw.get("level"),
        "level_index": level_index,
        "level_label": raw.get("level_label") or DIFF_NAMES.get(level_index, str(level_index)),
        "ds": ds,
        "achievement": round(safe_float(raw.get("achievements")), 4),
        "ra": safe_int(raw.get("ra"), 0),
        "rate": raw.get("rate") or "",
        "fc": raw.get("fc") or "",
        "fc_label": FC_LABELS.get(str(raw.get("fc") or "").lower(), ""),
        "fs": raw.get("fs") or "",
        "dx_score": safe_int(raw.get("dxScore"), 0),
        "config_tags": (summary.get("config_tags") or [])[:5] if isinstance(summary, dict) else [],
        "community_vibe": str(summary.get("community_vibe") or "")[:160] if isinstance(summary, dict) else "",
        "chart_identity": str(summary.get("chart_identity") or "")[:160] if isinstance(summary, dict) else "",
        "difficulty_feel": str(summary.get("difficulty_feel") or "")[:140] if isinstance(summary, dict) else "",
        "rating_gap_insight": str(summary.get("rating_gap_insight") or "")[:140] if isinstance(summary, dict) else "",
    }


def attach_peer_stats(songs: list[dict], rating: int, peer_stats: dict | None) -> dict:
    if not peer_stats:
        return {"available": False, "bucket": None, "matched": 0, "arpi": None, "b50_overlap": None}
    size = safe_int(peer_stats.get("rating_bucket_size"), 200) or 200
    bucket = rating_bucket(rating, size)
    charts = (((peer_stats.get("buckets") or {}).get(bucket) or {}).get("charts") or {})
    gaps = []
    overlaps = []
    for song in songs:
        key = f"{song.get('music_id')}:{song.get('level_index')}"
        stat = charts.get(key)
        if not isinstance(stat, dict):
            continue
        peer_avg = safe_float(stat.get("avg_achievement"), 0.0)
        if peer_avg:
            gap = round(safe_float(song.get("achievement")) - peer_avg, 4)
            song["peer_avg"] = round(peer_avg, 4)
            song["gap"] = gap
            song["peer_sample_count"] = safe_int(stat.get("sample_count"), 0)
            gaps.append(gap)
        appear = stat.get("b50_appear_rate")
        if appear is not None:
            overlap = safe_float(appear, 0.0)
            if overlap <= 1:
                overlap *= 100
            song["overlap"] = round(overlap, 4)
            overlaps.append(overlap)
    return {
        "available": True,
        "bucket": bucket,
        "matched": len(gaps),
        "arpi": round(sum(gaps) / len(gaps), 4) if gaps else None,
        "b50_overlap": {
            "value": round(sum(overlaps) / len(overlaps), 4) if overlaps else None,
            "matched": len(overlaps),
        },
    }


def top_by(songs: list[dict], key: str, n: int = 5, reverse: bool = True) -> list[dict]:
    return sorted(songs, key=lambda s: safe_float(s.get(key), -9999), reverse=reverse)[:n]


def compact_song(song: dict) -> dict:
    keys = [
        "bucket", "music_id", "title", "type", "level", "level_index", "level_label",
        "ds", "achievement", "ra", "rate", "fc_label", "dx_score", "peer_avg",
        "gap", "overlap", "peer_sample_count", "config_tags", "community_vibe",
        "chart_identity", "difficulty_feel", "rating_gap_insight",
    ]
    return {k: song.get(k) for k in keys if song.get(k) not in (None, "", [])}


def section_stats(songs: list[dict], label: str) -> dict:
    pcs = [safe_int(s.get("play_count", s.get("playCount")), 0) for s in songs]
    pcs = [p for p in pcs if p > 0]
    gaps = [safe_float(s.get("gap")) for s in songs if s.get("gap") is not None]
    peer_avgs = [safe_float(s.get("peer_avg")) for s in songs if s.get("peer_avg") is not None]
    return {
        "label": label,
        "count": len(songs),
        "ra_total": sum(safe_int(s.get("ra"), 0) for s in songs),
        "avg_ra": avg([safe_float(s.get("ra"), 0.0) for s in songs]),
        "avg_ds": avg([safe_float(s.get("ds"), 0.0) for s in songs if safe_float(s.get("ds"), 0.0) > 0]),
        "median_ds": median([safe_float(s.get("ds"), 0.0) for s in songs if safe_float(s.get("ds"), 0.0) > 0]),
        "avg_achievement": avg([safe_float(s.get("achievement"), 0.0) for s in songs if safe_float(s.get("achievement"), 0.0) > 0]),
        "avg_peer": avg(peer_avgs),
        "avg_gap": avg(gaps),
        "pc_total": sum(pcs),
        "pc_avg": round(sum(pcs) / len(pcs), 1) if pcs else 0,
        "pc_median": sorted(pcs)[len(pcs) // 2] if pcs else 0,
        "high_ds_count_14_plus": sum(1 for s in songs if safe_float(s.get("ds"), 0.0) >= 14.6),
    }


def add_play_count(song: dict, raw: dict) -> None:
    pc = raw.get("playCount", raw.get("play_count"))
    if pc is not None:
        song["play_count"] = safe_int(pc, 0)


def find_push_candidates(songs: list[dict], limit: int = 8) -> list[dict]:
    candidates = []
    for song in songs:
        ach = safe_float(song.get("achievement"), 0.0)
        if ach >= 100.5:
            continue
        target = 100.5 if ach >= 100 else 100.0
        gain_hint = max(1, int(song.get("ra", 0) * (target - ach) / max(ach, 1)))
        item = compact_song(song)
        item["target"] = "鸟加" if target == 100.5 else "鸟"
        item["reason"] = f"当前 {ach:.4f}%，离{item['target']}近，适合优先复盘。"
        item["gain_hint"] = gain_hint
        candidates.append(item)
    return sorted(candidates, key=lambda s: (safe_float(s.get("ds"), 0), safe_float(s.get("achievement"), 0)), reverse=True)[:limit]


def find_config_specialized(songs: list[dict], limit: int = 4) -> list[dict]:
    scored = []
    for song in songs:
        tags = song.get("config_tags") or []
        if not tags:
            continue
        score = safe_float(song.get("achievement"), 0.0) + safe_float(song.get("gap"), 0.0) * 2 + safe_float(song.get("ds"), 0.0) / 10
        item = compact_song(song)
        item["config_score"] = round(score, 4)
        scored.append(item)
    return sorted(scored, key=lambda s: safe_float(s.get("config_score"), 0.0), reverse=True)[:limit]


def find_least_played(songs: list[dict], limit: int = 4) -> list[dict]:
    with_pc = [s for s in songs if safe_int(s.get("play_count"), 0) > 0]
    return [compact_song(s) for s in sorted(with_pc, key=lambda s: (safe_int(s.get("play_count"), 999999), -safe_int(s.get("ra"), 0)))[:limit]]


def build_wordcloud_keywords(songs: list[dict], limit: int = 28) -> list[dict]:
    counter: Counter = Counter()
    for song in songs:
        for tag in song.get("config_tags") or []:
            counter[str(tag)] += 3
        for field in ("chart_identity", "difficulty_feel", "community_vibe"):
            text = str(song.get(field) or "")
            for word in ("键盘", "扫键", "绝赞", "星星", "交互", "体力", "尾杀", "手癖", "touch", "散点", "纵连", "变速", "水谱", "底力"):
                if word in text:
                    counter[word] += 1
    return [{"word": word, "weight": weight} for word, weight in counter.most_common(limit)]


def build_context(b50: dict, tone: str, angle: str, peer_stats: dict | None) -> dict:
    music_data = load_json(ASSETS / "music_data.json")
    chart_summary = load_json(ASSETS / "chart_summary.json")
    music_map = music_index(music_data)
    sd_raw = (b50.get("charts") or {}).get("sd", [])
    dx_raw = (b50.get("charts") or {}).get("dx", [])
    sd = [normalize_song(s, "B35", music_map, chart_summary) for s in sd_raw]
    dx = [normalize_song(s, "B15", music_map, chart_summary) for s in dx_raw]
    for normalized, raw in zip(sd, sd_raw):
        add_play_count(normalized, raw)
    for normalized, raw in zip(dx, dx_raw):
        add_play_count(normalized, raw)
    songs = sorted(sd + dx, key=lambda s: safe_int(s.get("ra"), 0), reverse=True)
    rating = safe_int(b50.get("rating"), 0)
    peer = attach_peer_stats(songs, rating, peer_stats)
    tags = Counter(tag for song in songs for tag in song.get("config_tags", []))
    levels = Counter(str(song.get("level")) for song in songs if song.get("level"))
    fc_cards = [compact_song(s) for s in songs if s.get("fc_label")]
    theory_cards = [compact_song(s) for s in songs if safe_float(s.get("achievement"), 0.0) >= 101]
    highlights = top_by([s for s in songs if s.get("gap") is not None], "gap", 6) if peer["available"] else top_by(songs, "ra", 6)
    weaknesses = top_by([s for s in songs if s.get("gap") is not None], "gap", 6, reverse=False) if peer["available"] else []
    overlap_candidates = [s for s in songs if s.get("overlap") is not None]
    overlap_extremes = []
    if overlap_candidates:
        overlap_extremes = [
            compact_song(max(overlap_candidates, key=lambda s: (safe_float(s.get("overlap"), 0.0), safe_int(s.get("ra"), 0)))),
            compact_song(min(overlap_candidates, key=lambda s: (safe_float(s.get("overlap"), 999.0), -safe_int(s.get("ra"), 0)))),
        ]
        if overlap_extremes:
            overlap_extremes[0]["overlap_label"] = "最高重合"
        if len(overlap_extremes) > 1:
            overlap_extremes[1]["overlap_label"] = "最低重合"
    ds_values = [safe_float(s.get("ds"), 0.0) for s in songs if safe_float(s.get("ds"), 0.0) > 0]
    achievements = [safe_float(s.get("achievement"), 0.0) for s in songs if safe_float(s.get("achievement"), 0.0) > 0]
    peer_avgs = [safe_float(s.get("peer_avg")) for s in songs if s.get("peer_avg") is not None]
    gaps = [safe_float(s.get("gap")) for s in songs if s.get("gap") is not None]
    impression_keywords = {str(s.get("music_id")): s.get("config_tags", []) for s in songs if s.get("music_id")}
    b35_stats = section_stats(sd, "B35")
    b15_stats = section_stats(dx, "B15")
    context = {
        "player": {
            "nickname": b50.get("nickname"),
            "username": b50.get("username"),
            "rating": rating,
            "additional_rating": b50.get("additional_rating"),
        },
        "request": {
            "tone": tone,
            "angle": angle,
        },
        "peer_stats_available": peer["available"],
        "peer_stats": peer,
        "summary": {
            "b35_count": len(sd),
            "b15_count": len(dx),
            "b35_ra": sum(safe_int(s.get("ra"), 0) for s in sd),
            "b15_ra": sum(safe_int(s.get("ra"), 0) for s in dx),
            "b35": b35_stats,
            "b15": b15_stats,
            "avg_achievement": avg(achievements),
            "avg_peer": avg(peer_avgs),
            "avg_gap": avg(gaps),
            "avg_ds": avg(ds_values),
            "median_ds": median(ds_values),
            "top_config_tags": tags.most_common(12),
            "level_distribution": levels.most_common(),
            "highest_ra": compact_song(songs[0]) if songs else {},
            "best_accuracy": compact_song(max(songs, key=lambda s: (safe_float(s.get("achievement"), 0), safe_float(s.get("ds"), 0)))) if songs else {},
            "theory_cards": theory_cards[:6],
            "fc_cards": fc_cards[:8],
            "wordcloud_keywords": build_wordcloud_keywords(songs),
        },
        "evidence": {
            "highlights": [compact_song(s) for s in highlights],
            "ordinaries": [compact_song(s) for s in weaknesses[:4]],
            "weaknesses": [compact_song(s) for s in weaknesses],
            "highest_song_rating": [compact_song(songs[0])] if songs else [],
            "overlap_extremes": overlap_extremes,
            "low_overlap_specials": [compact_song(s) for s in sorted([x for x in songs if x.get("overlap") is not None], key=lambda s: (safe_float(s.get("overlap"), 999), -safe_int(s.get("ra"), 0)))[:5]],
            "config_specialized": find_config_specialized(songs),
            "least_played": find_least_played(songs),
            "push_candidates": find_push_candidates(songs),
        },
        "impression_keywords": impression_keywords,
        "b50_songs": [compact_song(s) for s in songs],
        "writing_instructions": [
            "先回应用户指定语气和分析角度。",
            "只引用 b50_songs 或 push_candidates 中存在的曲名。",
            "peer_stats_available=false 时不要写 ARPI、gap 或重合度结论。",
            "不要报告 AP/FC 总数；只可点名具体谱面的 AP/FC。",
            "结尾给具体推分路线。",
        ],
    }
    return context


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare compact B50 analysis context.")
    parser.add_argument("--b50", required=True, help="B50 JSON from fetch_b50.py")
    parser.add_argument("--tone", default="默认 OneCat")
    parser.add_argument("--angle", default="综合锐评")
    parser.add_argument("--qq", help="Optional QQ number for avatar and output metadata")
    parser.add_argument("--peer-stats", help="Optional peer_stats.zip, peer_stats.json, or peer_stats.json.gz")
    parser.add_argument("--out", help="Output context JSON path")
    args = parser.parse_args()

    b50 = load_json(Path(args.b50))
    peer_stats, _peer_path = load_peer_stats(args.peer_stats)
    context = build_context(b50, args.tone, args.angle, peer_stats)
    if args.qq:
        context.setdefault("player", {})["qq"] = str(args.qq)
    text = json.dumps(context, ensure_ascii=False, indent=2)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
