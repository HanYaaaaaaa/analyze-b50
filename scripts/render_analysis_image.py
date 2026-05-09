#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import json
import math
import random
import re
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
UI = ASSETS / "ui"
ICONS = UI / "icons"
COVER_CACHE = ASSETS / "cache" / "covers"

CANVAS_W = 2000
CLOUD_COLORS = ["#4285F4", "#EA4335", "#FBBC04", "#34A853", "#FF6D01", "#46BDC6", "#7B1FA2"]
DIFF_SHORT = {0: "BAS", 1: "ADV", 2: "EXP", 3: "MAS", 4: "ReM"}
FC_ICON = {"FC": "UI_MSS_MBase_Icon_FC.png", "FC+": "UI_MSS_MBase_Icon_FCp.png", "AP": "UI_MSS_MBase_Icon_AP.png", "AP+": "UI_MSS_MBase_Icon_APp.png"}


def load_json(path: Path) -> Any:
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


def strip_emoji(text: str) -> str:
    return re.sub(r"[\U00010000-\U0010ffff]", "", str(text or ""))


def hex_color(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def cover_url(song_id: str) -> str:
    try:
        sid = int(song_id)
    except ValueError:
        sid = 11000
    return f"https://www.diving-fish.com/covers/{sid:05d}.png"


def rank_icon_name(achievement: float) -> str:
    if achievement >= 100.5:
        return "UI_TTR_Rank_SSSp.png"
    if achievement >= 100.0:
        return "UI_TTR_Rank_SSS.png"
    if achievement >= 99.5:
        return "UI_TTR_Rank_SSp.png"
    if achievement >= 99.0:
        return "UI_TTR_Rank_SS.png"
    if achievement >= 98.0:
        return "UI_TTR_Rank_Sp.png"
    if achievement >= 97.0:
        return "UI_TTR_Rank_S.png"
    if achievement >= 94.0:
        return "UI_TTR_Rank_AAA.png"
    if achievement >= 90.0:
        return "UI_TTR_Rank_AA.png"
    if achievement >= 80.0:
        return "UI_TTR_Rank_A.png"
    return ""


def ra_pic_name(rating: int) -> str:
    for threshold, name in [
        (1000, "01"), (2000, "02"), (4000, "03"), (7000, "04"), (10000, "05"),
        (12000, "06"), (13000, "07"), (14000, "08"), (14500, "09"), (15000, "10"),
    ]:
        if rating < threshold:
            return f"UI_CMN_DXRating_{name}.png"
    return "UI_CMN_DXRating_11.png"


class DrawAnalyzeB50:
    def __init__(self, data: dict, title: str, analysis_text: str, impression_text: str = "") -> None:
        self.data = data
        self.title = strip_emoji(title)
        self.analysis_text = strip_emoji(analysis_text)
        self.impression_text = strip_emoji(impression_text)
        self.im = Image.new("RGBA", (CANVAS_W, 5800), (255, 255, 255, 255))
        self.d = ImageDraw.Draw(self.im)
        self.fonts: dict[str, ImageFont.FreeTypeFont] = {}
        self.cover_cache: dict[str, Image.Image] = {}
        self.avatar: Image.Image | None = None

    def font(self, family: str, size: int) -> ImageFont.FreeTypeFont:
        key = f"{family}:{size}"
        if key not in self.fonts:
            filename = "SourceHanSansSC-Bold.otf" if family == "cn" else "Torus SemiBold.otf"
            self.fonts[key] = ImageFont.truetype(str(UI / "fonts" / filename), size)
        return self.fonts[key]

    def ensure_height(self, min_h: int) -> None:
        if min_h <= self.im.height:
            return
        new_h = int(math.ceil(min_h / 200.0) * 200)
        new_im = Image.new("RGBA", (CANVAS_W, new_h), (255, 255, 255, 255))
        new_im.alpha_composite(self.im, (0, 0))
        self.im = new_im
        self.d = ImageDraw.Draw(self.im)

    def rrect(self, xy: tuple[int, int, int, int], radius: int, fill, outline=None) -> None:
        x1, y1, x2, y2 = (int(v) for v in xy)
        layer = Image.new("RGBA", (max(1, x2 - x1), max(1, y2 - y1)), (0, 0, 0, 0))
        ImageDraw.Draw(layer).rounded_rectangle((0, 0, x2 - x1, y2 - y1), radius=radius, fill=fill, outline=outline)
        self.im.alpha_composite(layer, (x1, y1))
        self.d = ImageDraw.Draw(self.im)

    def paste(self, img: Image.Image, xy: tuple[int, int]) -> None:
        self.im.alpha_composite(img.convert("RGBA"), xy)
        self.d = ImageDraw.Draw(self.im)

    def icon(self, filename: str, size: tuple[int, int]) -> Image.Image | None:
        path = ICONS / filename
        if not path.exists():
            return None
        try:
            return Image.open(path).convert("RGBA").resize(size, Image.Resampling.LANCZOS)
        except Exception:
            return None

    def wrap(self, text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
        lines: list[str] = []
        for raw in str(text or "").replace("\r", "").split("\n"):
            cur = ""
            for ch in raw:
                if font.getbbox(cur + ch)[2] > max_w:
                    if cur:
                        lines.append(cur)
                    cur = ch
                else:
                    cur += ch
            if cur:
                lines.append(cur)
        return lines

    def fit_single_line(self, text: str, max_w: int, max_size: int = 28, min_size: int = 16) -> tuple[ImageFont.FreeTypeFont, str]:
        clean = " ".join(str(text or "").replace("\r", " ").replace("\n", " ").split())
        for size in range(max_size, min_size - 1, -2):
            font = self.font("cn", size)
            if font.getbbox(clean)[2] <= max_w:
                return font, clean
        font = self.font("cn", min_size)
        lo, hi = 0, len(clean)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if font.getbbox(clean[:mid] + "...")[2] <= max_w:
                lo = mid
            else:
                hi = mid - 1
        return font, clean if lo == len(clean) else clean[:lo] + "..."

    def fit_text(self, text: str, max_w: int, max_lines: int, max_size: int = 28, min_size: int = 16) -> tuple[ImageFont.FreeTypeFont, list[str], int]:
        for size in range(max_size, min_size - 1, -2):
            font = self.font("cn", size)
            lines = self.wrap(text, font, max_w)
            step = max(size + 10, int(size * 1.45))
            if len(lines) <= max_lines:
                return font, lines, step
        font = self.font("cn", min_size)
        lines = self.wrap(text, font, max_w)[:max_lines]
        if lines and len(self.wrap(text, font, max_w)) > max_lines:
            lines[-1] = lines[-1].rstrip("。.，；") + "..."
        return font, lines, max(min_size + 10, int(min_size * 1.45))

    def parse_rich(self, text: str) -> list[tuple[str, bool]]:
        parts: list[tuple[str, bool]] = []
        pos = 0
        for match in re.finditer(r"<r>(.*?)</r>", text, flags=re.S):
            if match.start() > pos:
                parts.append((text[pos:match.start()], False))
            parts.append((match.group(1), True))
            pos = match.end()
        if pos < len(text):
            parts.append((text[pos:], False))
        return parts or [(text, False)]

    def wrap_rich(self, parts: list[tuple[str, bool]], font: ImageFont.FreeTypeFont, max_w: int) -> list[list[tuple[str, bool]]]:
        lines: list[list[tuple[str, bool]]] = [[]]
        cur_w = 0
        for text, is_red in parts:
            buf = ""
            for ch in text.replace("\r", ""):
                if ch == "\n":
                    if buf:
                        lines[-1].append((buf, is_red))
                    lines.append([])
                    cur_w = 0
                    buf = ""
                    continue
                ch_w = font.getbbox(ch)[2]
                if cur_w + ch_w > max_w:
                    if buf:
                        lines[-1].append((buf, is_red))
                    lines.append([])
                    cur_w = 0
                    buf = ""
                buf += ch
                cur_w += ch_w
            if buf:
                lines[-1].append((buf, is_red))
        return [line for line in lines if line]

    def fit_rich(self, text: str, max_w: int, max_size: int = 24, min_size: int = 14) -> tuple[ImageFont.FreeTypeFont, list[list[tuple[str, bool]]], int]:
        parts = self.parse_rich(text)
        for size in range(max_size, min_size - 1, -2):
            font = self.font("cn", size)
            lines = self.wrap_rich(parts, font, max_w)
            return font, lines, max(size + 10, int(size * 1.45))
        font = self.font("cn", min_size)
        return font, self.wrap_rich(parts, font, max_w), max(min_size + 10, int(min_size * 1.45))

    def load_cover(self, song_id: Any, size: int = 120) -> Image.Image:
        sid = str(song_id or "")
        key = f"{sid}:{size}"
        if key in self.cover_cache:
            return self.cover_cache[key]
        COVER_CACHE.mkdir(parents=True, exist_ok=True)
        path = COVER_CACHE / f"{sid}.png"
        if sid and not path.exists():
            try:
                with urllib.request.urlopen(cover_url(sid), timeout=8) as resp:
                    path.write_bytes(resp.read())
            except Exception:
                pass
        try:
            img = Image.open(path if path.exists() else UI / "default_cover.png").convert("RGBA")
        except Exception:
            img = Image.open(UI / "default_cover.png").convert("RGBA")
        self.cover_cache[key] = img.resize((size, size), Image.Resampling.LANCZOS)
        return self.cover_cache[key]

    def fetch_avatar(self) -> None:
        qq = str((self.data.get("player") or {}).get("qq") or "")
        if not qq:
            return
        try:
            with urllib.request.urlopen(f"http://q.qlogo.cn/headimg_dl?dst_uin={qq}&spec=640", timeout=3) as resp:
                self.avatar = Image.open(io.BytesIO(resp.read())).resize((140, 140)).convert("RGBA")
        except Exception:
            self.avatar = None

    def draw_header(self) -> None:
        player = self.data.get("player") or {}
        peer = self.data.get("peer_stats") or {}
        summary = self.data.get("summary") or {}
        rating = safe_int(player.get("rating"), 0)
        self.rrect((40, 30, 620, 420), 16, (245, 248, 255, 255))
        if self.avatar:
            mask = Image.new("L", (140, 140), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, 140, 140), fill=255)
            circle = Image.new("RGBA", (140, 140), (0, 0, 0, 0))
            circle.paste(self.avatar, (0, 0), mask)
            self.paste(circle, (80, 50))
        nick = str(player.get("nickname") or player.get("username") or "maimai player")
        nick_font, nick_line = self.fit_single_line(nick, 330, 32, 20)
        self.d.text((240, 55), nick_line, font=nick_font, fill=(51, 51, 51))
        ra_img = self.icon(ra_pic_name(rating), (180, 36))
        if ra_img:
            self.paste(ra_img, (240, 105))
        self.d.text((312, 100), f"{rating:05d}", font=self.font("en", 36), fill=(255, 255, 255))
        arpi = peer.get("arpi")
        overlap = peer.get("b50_overlap") if isinstance(peer.get("b50_overlap"), dict) else {}
        overlap_val = overlap.get("value")
        arpi_text = "N/A" if arpi is None else f"{safe_float(arpi):+.4f}"
        overlap_text = "N/A" if overlap_val is None else f"{safe_float(overlap_val):.2f}%"
        self.d.text((80, 250), "B35 / B15", font=self.font("en", 22), fill=(120, 120, 120))
        self.d.text((220, 242), f"{summary.get('b35_ra', 0)} / {summary.get('b15_ra', 0)}", font=self.font("en", 32), fill=(51, 51, 51))
        self.d.text((80, 310), "ARPI", font=self.font("en", 22), fill=(120, 120, 120))
        self.d.text((160, 300), arpi_text, font=self.font("en", 36), fill=(46, 125, 50) if safe_float(arpi, 0) >= 0 else (198, 40, 40))
        self.d.text((80, 360), "重合", font=self.font("cn", 22), fill=(120, 120, 120))
        self.d.text((160, 350), overlap_text, font=self.font("en", 36), fill=(66, 133, 244))

        self.rrect((640, 30, 1260, 420), 16, (245, 248, 255, 255))
        self.d.text((675, 55), "平均值", font=self.font("cn", 30), fill=(26, 115, 232))
        rows = [
            ("全B50达成", summary.get("avg_achievement"), "%"),
            ("全B50同段", summary.get("avg_peer"), "%"),
            ("B35均值", (summary.get("b35") or {}).get("avg_achievement"), "%"),
            ("B15均值", (summary.get("b15") or {}).get("avg_achievement"), "%"),
            ("定数均值", summary.get("avg_ds"), ""),
        ]
        y = 110
        for label, value, suffix in rows:
            txt = "N/A" if value is None else f"{safe_float(value):.4f}{suffix}" if suffix else f"{safe_float(value):.2f}"
            self.d.text((675, y), label, font=self.font("cn", 22), fill=(110, 110, 110))
            self.d.text((850, y - 8), txt, font=self.font("en", 30), fill=(51, 51, 51))
            y += 55

        self.rrect((1280, 30, 1960, 420), 16, (255, 251, 235, 255), (245, 221, 160, 255))
        self.d.text((1310, 52), "指数说明", font=self.font("cn", 28), fill=(180, 110, 20))
        explain = (
            "ARPI：对比同 rating 段玩家在同一谱面的平均达成率，得到综合表现差异。"
            "B50重合度：统计同段玩家 B50 与本 B50 的平均重合比例。"
            "低于30%偏小众审美，超过50%偏模板路线；高分段重合度仅作娱乐参考。"
        )
        font, lines, step = self.fit_text(explain, 620, 7, 24, 18)
        for i, line in enumerate(lines):
            self.d.text((1310, 100 + i * step), line, font=font, fill=(95, 85, 65))
        slogan = "分析内容仅供娱乐参考，不要攀比和焦虑，玩得开心就好。"
        font2, lines2, step2 = self.fit_text(slogan, 620, 2, 22, 18)
        for i, line in enumerate(lines2):
            self.d.text((1310, 325 + i * step2), line, font=font2, fill=(198, 40, 40))

    def song_card(self, x: int, y: int, w: int, h: int, song: dict, label: str, label_color, bg_color, show_peer: bool = False) -> None:
        self.rrect((x, y, x + w, y + h), 14, bg_color)
        mid = song.get("music_id") or song.get("musicId") or ""
        self.paste(self.load_cover(mid, 120), (x + 15, y + 15))
        self.d.text((x + 15, y + h - 30), label, font=self.font("cn", 18), fill=label_color)
        title_font, title = self.fit_single_line(str(song.get("title") or ""), 760, 24, 18)
        self.d.text((x + 150, y + 12), title, font=title_font, fill=(51, 51, 51))
        ach = safe_float(song.get("achievement"), 0.0)
        ach_text = f"{ach:.4f}%"
        self.d.text((x + 150, y + 45), ach_text, font=self.font("en", 48), fill=(33, 33, 33))
        icon_x = x + 150 + self.font("en", 48).getbbox(ach_text)[2] + 12
        rank = self.icon(rank_icon_name(ach), (80, 40))
        if rank:
            self.paste(rank, (icon_x, y + 55))
            icon_x += 88
        fc_icon = self.icon(FC_ICON.get(str(song.get("fc_label") or ""), ""), (50, 50))
        if fc_icon:
            self.paste(fc_icon, (icon_x, y + 50))
        pc = safe_int(song.get("play_count", song.get("playCount")), 0)
        level_idx = safe_int(song.get("level_index"), -1)
        ds = safe_float(song.get("ds"), 0.0)
        info_y = y + 108
        if pc > 0:
            self.d.text((x + 150, info_y), f"PC {pc}", font=self.font("en", 22), fill=(100, 100, 100))
            meta_x = x + 270
        else:
            meta_x = x + 150
        self.d.text((meta_x, info_y), f"{DIFF_SHORT.get(level_idx, song.get('level_label', ''))} {ds:.1f}", font=self.font("en", 22), fill=(140, 140, 140))
        self.d.text((x + 420, info_y), f"RA {safe_int(song.get('ra'), 0)}", font=self.font("en", 22), fill=(232, 124, 32))
        overlap_label = str(song.get("overlap_label") or "重合")
        if song.get("overlap") is not None:
            self.d.text((x + 680, info_y), f"{overlap_label} {safe_float(song.get('overlap')):.2f}%", font=self.font("cn", 20), fill=(66, 133, 244))
        row2_y = y + 135
        if show_peer:
            if song.get("peer_avg") is not None:
                self.d.text((x + 150, row2_y), f"同级均值 {safe_float(song.get('peer_avg')):.4f}%", font=self.font("cn", 20), fill=(120, 120, 120))
            if song.get("gap") is not None:
                gap = safe_float(song.get("gap"))
                self.d.text((x + 430, row2_y), f"ARPI {gap:+.4f}", font=self.font("en", 20), fill=(46, 125, 50) if gap >= 0 else (198, 40, 40))
        else:
            reason = strip_emoji(str(song.get("reason") or song.get("chart_identity") or song.get("difficulty_feel") or ""))
            reason_font, reason_line = self.fit_single_line(reason, 760, 18, 14)
            self.d.text((x + 150, row2_y), reason_line, font=reason_font, fill=(150, 150, 150))
        tag_x = x + 150
        for tag in (song.get("config_tags") or [])[:5]:
            tag_str = str(tag).strip()
            if not tag_str:
                continue
            tag_font = self.font("cn", 17)
            tw = tag_font.getbbox(tag_str)[2] + 12
            if tag_x + tw > x + w - 10:
                break
            self.rrect((tag_x, y + 162, tag_x + tw, y + 186), 6, (220, 235, 255, 255))
            self.d.text((tag_x + 6, y + 165), tag_str, font=tag_font, fill=(30, 100, 200))
            tag_x += tw + 6

    def draw_song_sections(self) -> int:
        evidence = self.data.get("evidence") or {}
        cy = 450
        card_h = 210
        sections = [
            ("亮点谱面", "highlights", "亮点", (46, 125, 50), (232, 245, 233, 255), True, 4),
            ("普通点", "ordinaries", "普通", (198, 40, 40), (253, 237, 237, 255), True, 2),
            ("单曲RA最高", "highest_song_rating", "最高RA", (232, 124, 32), (255, 248, 235, 255), False, 1),
            ("B50重合极值", "overlap_extremes", "重合", (66, 133, 244), (235, 245, 255, 255), False, 2),
            ("推分推荐", "push_candidates", "推分", (232, 124, 32), (255, 248, 235, 255), False, 3),
            ("配置特化", "config_specialized", "擅长", (30, 100, 180), (230, 240, 255, 255), False, 2),
            ("最少游玩", "least_played", "少PC", (120, 80, 200), (240, 235, 255, 255), False, 2),
        ]
        for title, key, label, color, bg, show_peer, max_n in sections:
            songs = (evidence.get(key) or [])[:max_n]
            if not songs:
                continue
            self.d.text((40, cy), title, font=self.font("cn", 28), fill=color)
            cy += 38
            for row_start in range(0, len(songs), 2):
                for col in range(2):
                    idx = row_start + col
                    if idx >= len(songs):
                        break
                    self.song_card(40 + col * 980, cy, 940, card_h, songs[idx], label, color, bg, show_peer)
                cy += card_h + 15
        return cy

    def draw_analysis_panel(self, start_y: int) -> int:
        left_x, right_x = 40, 1020
        top_y = start_y + 45
        font, rich_lines, step = self.fit_rich(self.analysis_text, 880, 24, 14)
        roast_h = max(1280, 84 + len(rich_lines) * step + 60)
        panel_h = max(1280, 160 + roast_h)
        self.ensure_height(top_y + panel_h + 160)
        self.d.text((left_x, start_y), "OneCat锐评", font=self.font("cn", 32), fill=(26, 115, 232))
        self.d.text((right_x, start_y), "谱面印象", font=self.font("cn", 32), fill=(51, 51, 51))
        self.rrect((left_x, top_y, 980, top_y + panel_h), 16, (250, 252, 255, 255))
        self.rrect((right_x, top_y, 1960, top_y + panel_h), 16, (250, 252, 255, 255))
        if self.title:
            self.d.text((left_x + 30, top_y + 22), self.title, font=self.font("cn", 36), fill=(26, 115, 232))
        roast_y = top_y + 84
        self.rrect((left_x + 30, roast_y, left_x + 930, roast_y + roast_h), 14, (255, 249, 238, 255), (245, 210, 150, 255))
        self.d.text((left_x + 50, roast_y + 14), "综合锐评", font=self.font("cn", 28), fill=(198, 100, 20))
        y_cursor = roast_y + 62
        for line in rich_lines:
            x_cursor = left_x + 50
            for seg_text, is_red in line:
                self.d.text((x_cursor, y_cursor), seg_text, font=font, fill=(210, 45, 45) if is_red else (80, 65, 45))
                bb = font.getbbox(seg_text)
                x_cursor += bb[2] - bb[0]
            y_cursor += step
        self.draw_word_cloud(right_x, top_y, panel_h)
        return top_y + panel_h + 20

    def draw_word_cloud(self, right_x: int, top_y: int, panel_h: int) -> None:
        if self.impression_text:
            roast_font, lines, step = self.fit_text(f"OneCat锐评：{self.impression_text}", 850, 2, 24, 18)
            for i, line in enumerate(lines):
                self.d.text((right_x + 30, top_y + 24 + i * step), line, font=roast_font, fill=(198, 40, 40))
            top_pad = 25 + len(lines) * step
        else:
            top_pad = 25
        words = []
        for item in ((self.data.get("summary") or {}).get("wordcloud_keywords") or []):
            if isinstance(item, dict) and item.get("word"):
                words.append((str(item.get("word")), max(1, safe_int(item.get("weight"), 1))))
        if not words:
            counter: Counter = Counter()
            for kws in (self.data.get("impression_keywords") or {}).values():
                for kw in kws or []:
                    counter[str(kw)] += 1
            words = counter.most_common(25)
        if not words:
            self.d.text((right_x + 30, top_y + 80), "暂无印象数据", font=self.font("cn", 28), fill=(150, 150, 150))
            return
        area_x, area_y = right_x + 25, top_y + top_pad
        area_w, area_h = 890, panel_h - top_pad - 25
        cx, cy = area_x + area_w // 2, area_y + area_h // 2
        colors = [hex_color(c) for c in CLOUD_COLORS]
        placed: list[tuple[int, int, int, int]] = []
        max_c = max(1, words[0][1])
        for i, (word, count) in enumerate(words[:28]):
            fsize = 64 if i == 0 else max(20, int(20 + 38 * count / max_c))
            font = self.font("cn", fsize)
            bb = font.getbbox(word)
            tw, th = bb[2] - bb[0] + 10, bb[3] - bb[1] + 10
            if i == 0:
                tx, ty = cx - tw // 2, cy - th // 2
                self.d.text((tx, ty), word, font=font, fill=(*colors[0], 255))
                placed.append((tx - 4, ty - 4, tw + 8, th + 8))
                continue
            angle = i * 1.45
            radius = 50 + i * 18
            for _ in range(80):
                tx = max(area_x, min(int(cx + radius * math.cos(angle)) - tw // 2, area_x + area_w - tw))
                ty = max(area_y, min(int(cy + radius * math.sin(angle)) - th // 2, area_y + area_h - th))
                if all(tx + tw <= bx or tx >= bx + bw or ty + th <= by or ty >= by + bh for bx, by, bw, bh in placed):
                    color = colors[i % len(colors)]
                    self.d.text((tx, ty), word, font=font, fill=(*color, 255))
                    placed.append((tx, ty, tw, th))
                    break
                angle += 0.55
                radius += 4.5
        mids = list((self.data.get("impression_keywords") or {}).keys())[:6]
        for idx, mid in enumerate(mids):
            cv = self.load_cover(mid, 50)
            angle = idx * 1.2
            rad = 95 + idx * 52
            px = max(area_x, min(int(cx + rad * math.cos(angle)) - 25, area_x + area_w - 50))
            py = max(area_y, min(int(cy + rad * math.sin(angle)) - 25, area_y + area_h - 50))
            if all(px + 50 <= bx or px >= bx + bw or py + 50 <= by or py >= by + bh for bx, by, bw, bh in placed):
                self.paste(cv, (px, py))
                placed.append((px, py, 50, 50))

    def draw_footer(self, y: int) -> None:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        for text, family, size, color in [
            ("OneCat B50 Analysis Skill", "en", 20, (153, 153, 153)),
            (now, "en", 18, (187, 187, 187)),
        ]:
            font = self.font(family, size)
            tw = font.getbbox(text)[2]
            self.d.text(((CANVAS_W - tw) // 2, y), text, font=font, fill=color)
            y += 28

    def draw(self) -> Image.Image:
        random.seed(7)
        self.fetch_avatar()
        self.draw_header()
        songs_end = self.draw_song_sections()
        panel_end = self.draw_analysis_panel(songs_end + 10)
        self.ensure_height(panel_end + 120)
        self.draw_footer(panel_end + 10)
        final_h = panel_end + 80
        cropped = self.im.crop((0, 0, CANVAS_W, final_h))
        out_w = 1000
        out_h = int(out_w * cropped.height / cropped.width)
        return cropped.resize((out_w, out_h), Image.Resampling.LANCZOS).convert("RGB")


def render(context: dict, analysis_text: str, title: str | None = None, impression: str = "") -> Image.Image:
    drawer = DrawAnalyzeB50(context, title or "B50锐评现场", analysis_text, impression)
    return drawer.draw()


def main() -> None:
    parser = argparse.ArgumentParser(description="Render an original-plugin-style B50 analysis image from context JSON.")
    parser.add_argument("--context", required=True)
    parser.add_argument("--analysis-text", required=True, help="Final analysis text, or @path/to/text.txt")
    parser.add_argument("--title")
    parser.add_argument("--impression", default="")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    context = load_json(Path(args.context))
    analysis_text = args.analysis_text
    if analysis_text.startswith("@"):
        analysis_text = Path(analysis_text[1:]).read_text(encoding="utf-8")
    img = render(context, analysis_text, args.title, args.impression)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=92)


if __name__ == "__main__":
    main()
