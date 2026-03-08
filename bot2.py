import aiohttp
import asyncio
import discord
import firebase_admin
import random
import prediction_vote as p
import os
import json
import re
from pathlib import Path
from collections import defaultdict
from firebase_admin import credentials
from firebase_admin import db
from discord import Intents
from discord.ext import commands
from discord import Game
from discord import Status
from bs4 import BeautifulSoup
from datetime import datetime,timedelta, timezone
from dotenv import load_dotenv
from playwright.async_api import async_playwright
import io

TARGET_TEXT_CHANNEL_ID = 1289184218135396483
WARNING_CHANNEL_ID = 1314643507490590731
GUILD_ID = 298064707460268032
CHANNEL_ID = '938728993329397781'
NOTICE_CHANNEL_ID = '1232585451911643187'
TOKEN = None
API_KEY = None

playwright_instance = None
browser_instance = None

POS_ORDER = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]

REGISTERED_USERS = ['지모','Melon','그럭저럭', '이미름', '박퇴경', '이나호']

PUUID = {}

TIER_RANK_MAP = {
    'IRON': 1,
    'BRONZE': 2,
    'SILVER': 3,
    'GOLD': 4,
    'PLATINUM': 5,
    'EMERALD' : 6,
    'DIAMOND': 7,
    'MASTER': 8,
    'GRANDMASTER': 9,
    'CHALLENGER': 10
}
TIER_RANK_MAP2 = {
    'I': 1,
    'B': 2,
    'S': 3,
    'G': 4,
    'P': 5,
    'E' : 6,
    'D': 7,
    'M': 8,
    'GM': 9,
    'C': 10
}
RANK_MAP = {
    'I': 3,
    'II': 2,
    'III': 1,
    'IV': 0
}

MEMBER_MAP = {
    "지모" : 270093275673657355,
    "Melon" : 266140074310107136,
    "그럭저럭" : 512990115782590464,
    "이미름" : 298064278328705026,
    "박퇴경" : 298068763335589899,
    "이나호" : 298064278328705026
}

class NotFoundError(Exception):
    pass

CHAMPION_ID_NAME_MAP = {}
SPELL_ID_TO_KEY = {}
RUNE_ID_TO_PATH = {}

async def init_browser():
    global playwright_instance, browser_instance
    playwright_instance = await async_playwright().start()
    browser_instance = await playwright_instance.chromium.launch(
        args=["--no-sandbox", "--disable-setuid-sandbox"]
    )

async def create_match_result_image(
    match_info:        dict,
    target_name:       str = "",
) -> io.BytesIO:
    """
    매치 결과 이미지를 생성해 BytesIO로 반환합니다.
    ingame의 create_ingame_image와 동일한 호출 패턴.

    Parameters
    ----------
    match_info       : Riot API /matches/{matchId} 응답 전체
    version          : DDragon 버전 (e.g. "14.24.1")
    target_name      : 하이라이트할 소환사 이름 (riotIdGameName)
    """
    info          = match_info["info"]
    game_duration = _sec_to_time(info["gameDuration"])

    CHAMPION_ID_NAME_MAP = await fetch_champion_data()
    SPELL_ID_TO_KEY = await fetch_spell_id_to_key_map()
    blue, red = build_match_entries(
        participants    = info["participants"],
        champion_id_map = CHAMPION_ID_NAME_MAP,
        spell_id_to_key = SPELL_ID_TO_KEY,
        rune_id_to_path = RUNE_ID_TO_PATH,
        target_name     = target_name,
    )

    max_dmg    = max((p["damage"] for p in blue + red), default=1)

    version = await get_latest_ddragon_version()
    
    # target 기준 승패 (없으면 블루팀 기준 폴백)
    target_player = next((p for p in blue + red if p["is_target"]), None)
    target_win    = target_player["win"] if target_player else (blue[0]["win"] if blue else False)
    result_text   = "승리!" if target_win else "패배..."
    result_cls    = "win"   if target_win else "lose"

    def team_rows(players, bar_cls):
        return "".join(
            _player_row(p, max_dmg, bar_cls, version, p["is_target"])
            for p in _sort_by_pos(players)
        )

    blue_rows  = team_rows(blue, "blue-fill")
    red_rows   = team_rows(red,  "red-fill")
    blue_icons = _champ_icons(blue, version)
    red_icons  = _champ_icons(red,  version)

    html = f"""<!DOCTYPE html>
        <html lang="ko">
            <head>
            <meta charset="UTF-8">
            <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                background: #2b2b2b;
                font-family: 'NanumGothic', 'Noto Sans KR', sans-serif;
                color: #e0e0e0;
                padding: 16px;
                width: 1200px;
                -webkit-font-smoothing: antialiased;
            }}
            .match-header {{
                display: flex; align-items: center; justify-content: space-between;
                background: #222; border-radius: 10px; padding: 14px 22px; margin-bottom: 14px;
            }}
            .queue-label     {{ font-size: 11px; color: #777; text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 5px; }}
            .result-main     {{ display: flex; align-items: baseline; gap: 10px; }}
            .result-text     {{ font-size: 28px; font-weight: 900; letter-spacing: 0.5px; }}
            .result-text.win  {{ color: #4ade80; }}
            .result-text.lose {{ color: #f87171; }}
            .result-duration {{ font-size: 13px; font-weight: 600; color: #666; }}

            .team-section {{ margin-bottom: 12px; }}
            .team-title {{ display: flex; align-items: center; gap: 9px; margin-bottom: 6px; padding: 0 2px; }}
            .team-dot {{ width: 16px; height: 16px; border-radius: 50%; flex-shrink: 0; }}
            .blue-dot {{ background: #4a9eff; box-shadow: 0 0 8px rgba(74,158,255,0.5); }}
            .red-dot  {{ background: #ff5555; box-shadow: 0 0 8px rgba(255,85,85,0.5); }}
            .team-label {{ font-size: 16px; font-weight: 700; }}
            .team-champ-icons {{ display: flex; gap: 5px; margin-left: 2px; }}
            .team-champ-icons img {{ width: 26px; height: 26px; border-radius: 50%; border: 1px solid #444; object-fit: cover; }}

            .col-headers {{
                display: grid;
                grid-template-columns: 52px 64px 1fr 96px 68px 232px 52px 1fr;
                padding: 3px 12px; margin-bottom: 3px;
            }}
            .col-headers span {{ font-size: 10px; color: #555; text-transform: uppercase; letter-spacing: 0.8px; font-weight: 500; }}
            .ch-name {{ padding-left: 10px; }} .ch-c {{ text-align: center; }}
            .ch-items {{ padding-left: 5px; }} .ch-dmg {{ padding-left: 8px; }}

            .player-card {{
                display: grid;
                grid-template-columns: 52px 64px 1fr 96px 68px 232px 52px 1fr;
                align-items: center;
                background: #333; border-radius: 8px;
                padding: 8px 12px; margin-bottom: 4px; min-height: 62px;
            }}
            .player-card:last-child {{ margin-bottom: 0; }}
            .is-target .s-name {{ color: #fbbf24 !important; }}

            .champ-wrap {{ position: relative; width: 46px; height: 46px; }}
            .champ-img  {{ width: 46px; height: 46px; border-radius: 7px; object-fit: cover; border: 2px solid #4a4a4a; }}
            .champ-level {{
                position: absolute; bottom: -3px; left: -3px;
                background: #111; border: 1px solid #555; border-radius: 3px;
                font-size: 10px; font-weight: 700; padding: 0 3px; color: #bbb; line-height: 15px;
            }}
            .sr-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 3px; padding: 0 8px; width: 64px; }}
            .sr-img      {{ width: 22px; height: 22px; border-radius: 4px; object-fit: cover; border: 1px solid #3a3a3a; background: #1e1e1e; }}
            .sr-img.rune {{ border-radius: 0; background: transparent; border: none;}}

            .name-cell {{ padding: 0 10px; min-width: 0; }}
            .s-name {{ font-size: 14px; font-weight: 700; color: #e8e8e8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
            .c-name {{ font-size: 11px; color: #777; margin-top: 2px; }}

            .kda-cell {{ text-align: center; }}
            .kda-score {{ font-size: 14px; font-weight: 700; }}
            .kda-score .d {{ color: #f87171; }}
            .kda-ratio {{ font-size: 10px; color: #666; margin-top: 2px; }}
            .kda-ratio.perfect {{ color: #fbbf24; }}

            .gold-cell {{ text-align: center; font-size: 13px; font-weight: 700; color: #e8c96a; }}

            .items-cell {{ display: flex; gap: 3px; padding: 0 5px; align-items: center; }}
            .item-box {{ width: 28px; height: 28px; border-radius: 5px; background: #1e1e1e; border: 1px solid #3a3a3a; overflow: hidden; flex-shrink: 0; }}
            .item-box img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
            .item-box.empty {{ opacity: 0.18; }}

            .cs-cell {{ text-align: center; }}
            .cs-num   {{ display: block; font-size: 14px; font-weight: 700; color: #ccc; }}
            .cs-label {{ font-size: 10px; color: #555; }}

            .damage-cell {{ padding: 0 8px; }}
            .damage-top  {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 5px; }}
            .dmg-num {{ font-size: 13px; font-weight: 600; color: #bbb; }}
            .dmg-pct {{ font-size: 10px; color: #555; }}
            .bar-bg  {{ height: 6px; background: #1a1a1a; border-radius: 3px; overflow: hidden; }}
            .bar-fill{{ height: 100%; border-radius: 3px; }}
            .blue-fill {{ background: linear-gradient(90deg, #3b82f6, #93c5fd); }}
            .red-fill  {{ background: linear-gradient(90deg, #ef4444, #fca5a5); }}
            </style>
            </head>
            <body>

            <div class="match-header">
                <div class="result-main">
                <span class="result-text {result_cls}">{result_text}</span>
                <span class="result-duration">{game_duration}</span>
                </div>
            </div>

            <div class="team-section">
                <div class="team-title">
                <div class="team-dot blue-dot"></div>
                <span class="team-label">블루팀</span>
                <div class="team-champ-icons">{blue_icons}</div>
                </div>
                <div class="col-headers">
                <span></span><span></span>
                <span class="ch-name">소환사</span>
                <span class="ch-c">KDA</span>
                <span class="ch-c">골드</span>
                <span class="ch-items">아이템</span>
                <span class="ch-c">CS</span>
                <span class="ch-dmg">피해량</span>
                </div>
                {blue_rows}
            </div>

            <div class="team-section">
                <div class="team-title">
                <div class="team-dot red-dot"></div>
                <span class="team-label">레드팀</span>
                <div class="team-champ-icons">{red_icons}</div>
                </div>
                <div class="col-headers">
                <span></span><span></span>
                <span class="ch-name">소환사</span>
                <span class="ch-c">KDA</span>
                <span class="ch-c">골드</span>
                <span class="ch-items">아이템</span>
                <span class="ch-c">CS</span>
                <span class="ch-dmg">피해량</span>
                </div>
                {red_rows}
            </div>

            </body>
        </html>
    """

    context = await browser_instance.new_context(
        viewport={"width": 1200, "height": 100},
        device_scale_factor=2,
    )
    try:
        page = await context.new_page()
        await page.set_content(html, wait_until="networkidle")
        screenshot = await page.screenshot(full_page=True)
    finally:
        await context.close()  # page.close() 대신 context.close()

    return io.BytesIO(screenshot)

def build_match_entries(
    participants:      list,
    champion_id_map:   dict,   # CHAMPION_ID_NAME_MAP  {"266": {"name":..,"key":..}, ...}
    spell_id_to_key:   dict,   # SPELL_ID_TO_KEY        {"4": "SummonerFlash", ...}
    rune_id_to_path:   dict,   # RUNE_ID_TO_PATH        {"8112": "perk-images/...", ...}
    target_name:       str = "",
) -> tuple[list, list]:
    """
    Riot API match participants → (blue_team, red_team) entry 리스트 반환.
    ingame의 for p in participants 루프와 동일한 구조.
    """
    blue, red = [], []

    for p in participants:
        # 챔피언
        champ_id   = p.get("championId")
        champ_info = champion_id_map.get(str(champ_id), {})
        champ_name = champ_info.get("name", f"챔피언ID:{champ_id}")
        champ_key  = champ_info.get("key", "")

        # 스펠
        spell1_key = spell_id_to_key.get(str(p.get("summoner1Id", "")), "")
        spell2_key = spell_id_to_key.get(str(p.get("summoner2Id", "")), "")

        # 룬 (keystone: perkIds[0])
        perks    = p.get("perks", {})
        styles   = perks.get("styles", [])
        try:
            keystone_id = str(styles[0]["selections"][0]["perk"])
        except (IndexError, KeyError):
            keystone_id = None
        try: # 부 룬
            sub_style_id = str(styles[1]["style"])
        except (IndexError, KeyError):
            sub_style_id = None
        rune_path = rune_id_to_path.get(keystone_id, "") if keystone_id else ""
        sub_rune_path = rune_id_to_path.get(sub_style_id, "") if sub_style_id else ""

        # 포지션
        position = p.get("individualPosition") or p.get("teamPosition", "")

        entry = {
            "champ":      champ_name,
            "champ_key":  champ_key,
            "spell1_key": spell1_key,
            "spell2_key": spell2_key,
            "rune_path":  rune_path,
            "sub_rune_path": sub_rune_path,
            "name":       p.get("riotIdGameName") or p.get("riotId", "Unknown"),
            "level":      p.get("champLevel", 0),
            "kills":      p.get("kills", 0),
            "deaths":     p.get("deaths", 0),
            "assists":    p.get("assists", 0),
            "items":      [p.get(f"item{i}", 0) for i in range(7)],
            "gold":       p.get("goldEarned", 0),
            "damage":     p.get("totalDamageDealtToChampions", 0),
            "cs":         p.get("totalMinionsKilled", 0) + p.get("neutralMinionsKilled", 0),
            "position":   position,
            "win":        p.get("win", False),
            "teamId":     p.get("teamId", 100),
            "is_target":  (p.get("riotIdGameName") or p.get("riotId", "")) == target_name,
        }

        if p.get("teamId") == 100:
            blue.append(entry)
        else:
            red.append(entry)

    return blue, red

def _sec_to_time(s: int) -> str:
    return f"{s // 60}:{s % 60:02d}"

def _kda_ratio(k: int, d: int, a: int) -> str:
    return "Perfect" if d == 0 else f"{(k + a) / d:.2f}"

def _sort_by_pos(players: list) -> list:
    return sorted(players, key=lambda p: (
        POS_ORDER.index(p["position"].upper())
        if p["position"].upper() in POS_ORDER else 99
    ))

def _item_slots(items: list, version: str) -> str:
    slots = []
    for i in range(7):
        item_id = items[i] if i < len(items) else 0
        if item_id:
            slots.append(
                f'<div class="item-box">'
                f'<img src="https://ddragon.leagueoflegends.com/cdn/{version}/img/item/{item_id}.png"'
                f' onerror="this.parentElement.classList.add(\'empty\');this.remove()"/>'
                f'</div>'
            )
        else:
            slots.append('<div class="item-box empty"></div>')
    return "".join(slots)

def _player_row(p: dict, max_dmg: int, bar_cls: str, version: str, is_target: bool) -> str:
    base      = f"https://ddragon.leagueoflegends.com/cdn/{version}/img"
    champ_url = f"{base}/champion/{p['champ_key']}.png"
    sp1_url   = f"{base}/spell/{p['spell1_key']}.png"  if p.get('spell1_key') else ""
    sp2_url   = f"{base}/spell/{p['spell2_key']}.png"  if p.get('spell2_key') else ""
    # rune_path는 ingame과 동일하게 "perk-images/Styles/..." 형태
    rune_url  = f"https://ddragon.leagueoflegends.com/cdn/img/{p['rune_path']}" if p.get('rune_path') else ""
    sub_rune_url = f"https://ddragon.leagueoflegends.com/cdn/img/{p['sub_rune_path']}" if p.get('sub_rune_path') else ""

    ratio    = _kda_ratio(p["kills"], p["deaths"], p["assists"])
    pct      = round(p["damage"] / max_dmg * 100, 1) if max_dmg > 0 else 0
    cs       = p.get("cs", 0)
    items_h  = _item_slots(p.get("items", []), version)
    target   = " is-target" if is_target else ""

    sp1_tag  = f'<img class="sr-img"      src="{sp1_url}"  onerror="this.style.opacity=0.1"/>' if sp1_url else '<div class="sr-img"></div>'
    sp2_tag  = f'<img class="sr-img"      src="{sp2_url}"  onerror="this.style.opacity=0.1"/>' if sp2_url else '<div class="sr-img"></div>'
    rune_tag = f'<img class="sr-img rune" src="{rune_url}" onerror="this.style.opacity=0.1"/>' if rune_url else '<div class="sr-img rune"></div>'
    sub_rune_tag = f'<img class="sr-img rune" src="{sub_rune_url}" onerror="this.style.opacity=0.1"/>' if sub_rune_url else '<div class="sr-img rune"></div>'
    return f"""
    <div class="player-card{target}">
      <div class="champ-wrap">
        <img class="champ-img" src="{champ_url}" onerror="this.src='{base}/champion/Ryze.png'"/>
        <span class="champ-level">{p['level']}</span>
      </div>
      <div class="sr-grid">
        {sp1_tag}
        {rune_tag}
        {sp2_tag}
        {sub_rune_tag}
      </div>
      <div class="name-cell">
        <div class="s-name">{p['name']}</div>
        <div class="c-name">{p['champ']}</div>
      </div>
      <div class="kda-cell">
        <div class="kda-score">{p['kills']} / <span class="d">{p['deaths']}</span> / {p['assists']}</div>
        <div class="kda-ratio{' perfect' if ratio == 'Perfect' else ''}">{ratio} KDA</div>
      </div>
      <div class="gold-cell">{p['gold'] / 1000:.1f}k</div>
      <div class="items-cell">{items_h}</div>
      <div class="cs-cell">
        <span class="cs-num">{cs}</span>
        <span class="cs-label">CS</span>
      </div>
      <div class="damage-cell">
        <div class="damage-top">
          <span class="dmg-num">{p['damage']:,}</span>
          <span class="dmg-pct">{pct}%</span>
        </div>
        <div class="bar-bg"><div class="bar-fill {bar_cls}" style="width:{pct}%"></div></div>
      </div>
    </div>"""

def _champ_icons(players: list, version: str) -> str:
    base = f"https://ddragon.leagueoflegends.com/cdn/{version}/img/champion"
    return "".join(
        f'<img src="{base}/{p["champ_key"]}.png"'
        f' onerror="this.src=\'{base}/Ryze.png\'" title="{p["champ"]}"/>'
        for p in _sort_by_pos(players)
    )

async def create_ingame_image(team1_data, team2_data, version, banned_champions):
    def most_html(most):
        slots = []
        for i in range(3):
            m = most[i] if most and i < len(most) else None
            if m:
                wr = m['winrate']
                wr_color = "#ff4444" if wr >= 60 else "#ffa500" if wr >= 55 else "#4CAF50" if wr >= 50 else "#aaaaaa"
                slots.append(f"""
                <div class="most-item">
                    <img class="most-icon" src="https://ddragon.leagueoflegends.com/cdn/{version}/img/champion/{m['champ_key']}.png">
                    <span class="most-wr" style="color:{wr_color}">{wr}%</span>
                    <span class="most-games">{m['games']}판</span>
                </div>""")
            else:
                slots.append("""
                <div class="most-item">
                    <div class="most-icon most-empty"></div>
                    <span class="most-wr"></span>
                    <span class="most-games"></span>
                </div>""")
        return "".join(slots)

    def ban_icons(team_id):
        bans = sorted(
            [b for b in banned_champions if b['teamId'] == team_id],
            key=lambda b: b['pickTurn']
        )
        result = []
        for b in bans:
            champ_info = CHAMPION_ID_NAME_MAP.get(str(b['championId']), {})
            key = champ_info.get('key', '')
            if key:
                result.append(f'<img class="ban-icon" src="https://ddragon.leagueoflegends.com/cdn/{version}/img/champion/{key}.png">')
            else:
                result.append('<div class="ban-empty"></div>')
        return "".join(result)

    def player_row(p):
        champ_url  = f"https://ddragon.leagueoflegends.com/cdn/{version}/img/champion/{p['champ_key']}.png"
        spell1_url = f"https://ddragon.leagueoflegends.com/cdn/{version}/img/spell/{p['spell1_key']}.png"
        spell2_url = f"https://ddragon.leagueoflegends.com/cdn/{version}/img/spell/{p['spell2_key']}.png"
        rune_url   = f"https://ddragon.leagueoflegends.com/cdn/img/{p['rune_path']}"

        wr = p['winrate']
        if isinstance(wr, (int, float)):
            wr_color = "#ff4444" if wr >= 60 else "#ffa500" if wr >= 55 else "#4CAF50" if wr >= 50 else "#aaaaaa"
            wr_text = f"{wr}%"
        else:
            wr_color = "#aaaaaa"
            wr_text = "N/A"

        tier = p['tier'].upper()
        if "CHALLENGER" in tier:    tier_color = "#f4c874"
        elif "GRANDMASTER" in tier: tier_color = "#ff6b6b"
        elif "MASTER" in tier:      tier_color = "#9b59b6"
        elif "DIAMOND" in tier:     tier_color = "#4fc3f7"
        elif "EMERALD" in tier:     tier_color = "#2ecc71"
        elif "PLATINUM" in tier:    tier_color = "#1abc9c"
        elif "GOLD" in tier:        tier_color = "#f1c40f"
        elif "SILVER" in tier:      tier_color = "#bdc3c7"
        elif "BRONZE" in tier:      tier_color = "#cd6133"
        elif "IRON" in tier:        tier_color = "#808080"
        else:                       tier_color = "#555555"

        games_html = f'<span class="games">{p["games"]}게임</span>' if p.get('games') else ''

        return f"""
        <div class="player">
            <img class="icon champ-icon" src="{champ_url}">
            <img class="icon spell-icon" src="{spell1_url}">
            <img class="icon spell-icon" src="{spell2_url}">
            <img class="icon rune-icon"  src="{rune_url}">
            <span class="champ">{p['champ']}</span>
            <span class="name">{p['name']}</span>
            <div class="right-block">
                <div class="tier-block">
                    <span class="tier" style="color:{tier_color}">{p['tier']}</span>
                    {games_html}
                </div>
                <span class="winrate" style="color:{wr_color}">{wr_text}</span>
                <div class="sep"></div>
                <div class="most-list">{most_html(p.get('most', []))}</div>
            </div>
        </div>"""

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: #1e1f22;
            color: white;
            font-family: 'NanumGothic', sans-serif;
            padding: 16px;
            width: 900px;
            -webkit-font-smoothing: antialiased;
        }}
        .team-header {{
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 16px;
            font-weight: bold;
            padding: 6px 4px;
            margin-bottom: 6px;
            letter-spacing: 1px;
        }}
        .blue {{ color: #5865f2; }}
        .red  {{ color: #ed4245; }}
        .ban-list {{ display: flex; align-items: center; gap: 4px; }}
        .ban-icon {{
            width: 24px; height: 24px;
            border-radius: 50%;
            object-fit: cover;
            opacity: 0.75;
            filter: grayscale(30%);
            border: 1px solid #555;
        }}
        .ban-empty {{
            width: 24px; height: 24px;
            border-radius: 50%;
            background: #2b2d31;
            border: 1px dashed #444;
        }}
        .player {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 7px 10px;
            margin: 3px 0;
            background: #2b2d31;
            border-radius: 8px;
        }}
        .icon       {{ border-radius: 4px; object-fit: cover; flex-shrink: 0; }}
        .champ-icon {{ width: 32px; height: 32px; }}
        .spell-icon {{ width: 22px; height: 22px; }}
        .rune-icon  {{ width: 22px; height: 22px; }}
        .champ {{
            font-weight: 800;
            width: 80px;
            font-size: 13px;
            color: #ffffff;
            flex-shrink: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .name {{
            color: #cccccc;
            font-size: 12px;
            font-weight: 600;
            flex: 1;
            min-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .right-block {{
            display: flex;
            align-items: center;
            gap: 8px;
            flex-shrink: 0;
        }}
        .tier-block {{
            display: flex;
            flex-direction: column;
            width: 140px;
            flex-shrink: 0;
        }}
        .tier  {{ font-size: 12px; font-weight: 700; line-height: 1.4; }}
        .games {{ font-size: 10px; color: #888; font-weight: 500; }}
        .winrate {{
            width: 42px;
            text-align: right;
            font-size: 13px;
            font-weight: 700;
            flex-shrink: 0;
        }}
        .sep {{
            width: 1px;
            height: 32px;
            background: #3a3a3a;
            flex-shrink: 0;
        }}
        .most-list  {{ display: flex; align-items: center; gap: 6px; flex-shrink: 0; }}
        .most-item  {{ display: flex; flex-direction: column; align-items: center; gap: 2px; }}
        .most-icon  {{ width: 26px; height: 26px; border-radius: 4px; object-fit: cover; }}
        .most-empty {{ background: #3a3a3a; border: 1px dashed #555; }}
        .most-wr    {{ font-size: 9px; font-weight: 700; text-align: center; line-height: 1; width: 30px; }}
        .most-games {{ font-size: 8px; color: #777; text-align: center; line-height: 1; }}
        .divider {{ border: 1px solid #3a3a3a; margin: 10px 0; }}
    </style>
    </head>
    <body>
        <div class="team-header blue">
            🔵 블루팀
            <div class="ban-list">{ban_icons(100)}</div>
        </div>
        {"".join(player_row(p) for p in team1_data)}
        <div class="divider"></div>
        <div class="team-header red">
            🔴 레드팀
            <div class="ban-list">{ban_icons(200)}</div>
        </div>
        {"".join(player_row(p) for p in team2_data)}
    </body>
    </html>
    """

    context = await browser_instance.new_context(
        viewport={"width": 900, "height": 100},
        device_scale_factor=2,
    )
    try:
        page = await context.new_page()
        await page.set_content(html, wait_until="networkidle")
        screenshot = await page.screenshot(full_page=True)
    finally:
        await context.close()

    return io.BytesIO(screenshot)

async def get_latest_ddragon_version():
    url = 'https://ddragon.leagueoflegends.com/api/versions.json'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                versions = await response.json()
                return versions[0]  # 가장 최신 버전
            else:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] 버전 정보 불러오기 실패: {response.status}")
                return None

# 챔피언 데이터 다운로드 함수 (캐시 추가)
async def fetch_champion_data(force_download=False):
    global CHAMPION_ID_NAME_MAP

    cache_path = "champion_cache.json"
    if not force_download and os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            CHAMPION_ID_NAME_MAP = json.load(f)
        return CHAMPION_ID_NAME_MAP

    # 최신 버전 가져오기
    version = await get_latest_ddragon_version()
    if not version:
        return {}

    # 챔피언 데이터 가져오기

    async with aiohttp.ClientSession() as session:
        # 한글 이름용
        ko_url = f'https://ddragon.leagueoflegends.com/cdn/{version}/data/ko_KR/champion.json'
        # 영문 키용
        en_url = f'https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json'

        async with session.get(ko_url) as ko_res, session.get(en_url) as en_res:
            if ko_res.status == 200 and en_res.status == 200:
                ko_data = await ko_res.json()
                en_data = await en_res.json()

                data_by_id = {}
                for champ_id_str, champ in en_data["data"].items():
                    champ_id = int(champ["key"])
                    en_key   = champ["id"]    # "Xayah", "LeeSin" 등
                    ko_name  = ko_data["data"].get(champ_id_str, {}).get("name", en_key)
                    tags = champ.get("tags", [])  # 챔피언 태그 추가
                    data_by_id[champ_id] = {
                        "name": ko_name,   # "자야"
                        "key":  en_key,    # "Xayah"
                        "tags": tags       # ["Marksman", "Carry"] 등
                    }

                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] {len(data_by_id)}개의 챔피언을 불러왔습니다. (버전: {version})")

                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(data_by_id, f, ensure_ascii=False, indent=2)

                CHAMPION_ID_NAME_MAP = data_by_id
                return data_by_id

# 패치 버전 주기적으로 확인하여 최신 버전이 바뀌면 데이터 갱신
async def fetch_patch_version():

    version = await get_latest_ddragon_version()

    curseasonref = db.reference("전적분석/현재시즌")
    current_season = curseasonref.get()

    season_name = "시즌" + version.split(".")[0]

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [LOG] 현재 시즌 : {season_name}")

    if current_season != season_name:
        curseasonref = db.reference("전적분석")
        curseasonref.update({'현재시즌' : season_name})
    # 최신 버전 가져오기
    await asyncio.sleep(3600)

async def fetch_rune_data(force_download=False):
    global RUNE_ID_TO_PATH

    cache_path = "rune_cache.json"
    if not force_download and os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            RUNE_ID_TO_PATH = json.load(f)
        return RUNE_ID_TO_PATH

    version = await get_latest_ddragon_version()
    url = f"https://ddragon.leagueoflegends.com/cdn/{version}/data/ko_KR/runesReforged.json"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                rune_map = {}

                for style in data:
                    # 스타일 자체 (정밀, 지배 등)
                    rune_map[str(style["id"])] = style["icon"]

                    for slot in style["slots"]:
                        for rune in slot["runes"]:
                            rune_map[str(rune["id"])] = rune["icon"]

                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(rune_map, f, ensure_ascii=False, indent=2)

                RUNE_ID_TO_PATH = rune_map
                return rune_map

async def fetch_rune_id_to_key_map(force_download=False):
    cache_path = "rune_id_to_key_cache.json"
    if not force_download and os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            rune_id_to_key = json.load(f)
        return rune_id_to_key

    # 최신 버전 가져오기
    version = await get_latest_ddragon_version()
    if not version:
        return {}

    # 룬 데이터 가져오기
    url = f'https://ddragon.leagueoflegends.com/cdn/{version}/data/ko_KR/runesReforged.json'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()

                rune_id_to_key = {
                    str(rune["id"]): rune["key"]
                    for tree in data
                    for rune in tree["slots"][0]["runes"]
                }       

                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] {len(rune_id_to_key)}개의 룬을 불러왔습니다. (버전: {version})")

                # 로컬 캐시 저장
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(rune_id_to_key, f, ensure_ascii=False, indent=2)

                return rune_id_to_key
            else:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] 룬 데이터 불러오기 실패: {response.status}")
                return {}

async def fetch_spell_id_to_key_map(force_download=False):
    cache_path = "spell_id_to_key_cache.json"
    if not force_download and os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            spell_id_to_key = json.load(f)
        return spell_id_to_key

    # 최신 버전 가져오기
    version = await get_latest_ddragon_version()
    if not version:
        return {}

    # 스펠 데이터 가져오기
    url = f'https://ddragon.leagueoflegends.com/cdn/{version}/data/ko_KR/summoner.json'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()

                spell_id_to_key = {
                    str(value["key"]): key  # 예: "11": "SummonerSmite"
                    for key, value in data["data"].items()
                }

                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] {len(spell_id_to_key)}개의 스펠을 불러왔습니다. (버전: {version})")

                # 로컬 캐시 저장
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(spell_id_to_key, f, ensure_ascii=False, indent=2)

                return spell_id_to_key
            else:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] 스펠 데이터 불러오기 실패: {response.status}")
                return {}

async def fake_get_current_game_info(puuid):
    import json
    with open("mock_active_game.json", "r", encoding="utf-8") as f:
        return json.load(f)
    
async def get_current_game_info(puuid):
    url = f'https://kr.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}'
    headers = {'X-Riot-Token': API_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            elif response.status == 404:
                return None  # 게임 안 하는 중
            else:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_current_game_info에서 오류 발생: {response.status}")
                return None

def guess_position(spell1_key, spell2_key, champ_tags):
    """스펠과 챔피언 태그를 통해 포지션 추정"""
    spells = {spell1_key, spell2_key}
    tags = set(champ_tags) if champ_tags else set()

    # 1. 강타 → 정글 (100%)
    if "SummonerSmite" in spells:
        return "JUNGLE"

    # 2. 방어막 → 바텀
    if "SummonerBarrier" in spells:
        if "Marksman" in tags:
            return "BOTTOM"
        if "Fighter" in tags or "Tank" in tags:
            return "TOP"
        return "MIDDLE"  # Mage, Assassin
    
    # 3. 텔 → 탑/미드 태그로 구분
    if "SummonerTeleport" in spells:
        if "Mage" in tags or "Assassin" in tags:
            return "MIDDLE"
        return "TOP"  # Fighter, Tank
    
    # 4. 유체화 → 탑 or 바텀
    if "SummonerHaste" in spells:
        if "Fighter" in tags or "Tank" in tags:
            return "TOP"
        if "Marksman" in tags:
            return "BOTTOM"

    # 5. 탈진 → 서폿 or 탑
    if "SummonerExhaust" in spells:
        if "Support" in tags:
            return "UTILITY"
        if "Marksman" in tags:
            return "BOTTOM"
        return "TOP"

    # 6. 정화 → 바텀 (서폿 제외)
    if "SummonerBoost" in spells:
        if "Marksman" not in tags:
            return "MIDDLE"
        return "BOTTOM"

    # 7. 점화 → 태그로 구분
    if "SummonerDot" in spells:
        if "Support" in tags:
            return "UTILITY"
        if "Fighter" in tags or "Tank" in tags:
            return "TOP"
        return "MIDDLE"  # Mage, Assassin

    return "UNKNOWN"

def assign_positions(team):
    """팀 내 포지션 중복 제거 및 최종 배치"""
    POSITION_ORDER = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
    
    # 1차 추정
    for player in team:
        player['position'] = guess_position(
            player['spell1_key'], 
            player['spell2_key'], 
            player.get('champ_tags', [])
        )
    
    # 2차 중복 제거
    used = set()
    unassigned = []
    
    # 확실한 것 먼저 확정 (정글 → 유체화 순)
    PRIORITY = ["JUNGLE", "TOP", "BOTTOM", "UTILITY", "MIDDLE"]
    
    result = {}
    for pos in PRIORITY:
        candidates = [p for p in team if p['position'] == pos and pos not in used]
        if candidates:
            result[pos] = candidates[0]
            used.add(pos)
            if len(candidates) > 1:
                unassigned.extend(candidates[1:])
    
    unassigned.extend([p for p in team if p['position'] == "UNKNOWN"])
    
    # 3차 남은 포지션 채우기
    remaining = [p for p in POSITION_ORDER if p not in used]
    for player, pos in zip(unassigned, remaining):
        player['position'] = pos
    
    # 최종 정렬
    return sorted(team, key=lambda x: POSITION_ORDER.index(x.get('position', 'UNKNOWN')) 
                  if x.get('position') in POSITION_ORDER else 99)


async def get_team_champion(username, puuid, mode, get_info_func=get_current_game_info):
    data = await get_info_func(puuid)
    if not data:
        return None

    banned_champions = data.get("bannedChampions",[])
    participants = data.get("participants", [])
    if not participants:
        return None

    team1 = []
    team2 = []

    CHAMPION_ID_NAME_MAP = await fetch_champion_data(force_download = False)
    SPELL_ID_TO_KEY = await fetch_spell_id_to_key_map()

    summoners = []
    for p in participants:
        name = p.get("riotId", "Unknown").split("#")[0] if "#" in p.get("riotId", "Unknown") else p.get("riotId", "Unknown")
        tag = p.get("riotId", "Unknown").split("#")[1] if "#" in p.get("riotId", "Unknown") else ""
        summoners.append((name, tag))

    async with aiohttp.ClientSession() as session:
        results = await get_fow_multisearch(session, summoners, mode)
    # async with aiohttp.ClientSession() as session:
    #     # 10명 요청을 한꺼번에 발사
    #     tasks = []
    #     for p in participants:
    #         riot_id = p.get("riotId", "Unknown")
    #         name = riot_id.split("#")[0] if "#" in riot_id else riot_id
    #         tag  = riot_id.split("#")[1] if "#" in riot_id else ""
    #         tasks.append(get_opgg_tier(session, name, tag, mode))

    #     results = await asyncio.gather(*tasks)

    team1_temp = []
    team2_temp = []

    for p in participants:
        summoner_name = p.get("riotId", "Unknown")
        data = results.get(summoner_name, {
            "tier": "UNRANKED",
            "winrate": None,
            "games": None,
            "most": []
        })
        # most champ_id → champ_key 역변환
        # CHAMPION_ID_NAME_MAP의 key가 str(championId) 형태라고 가정
        converted_most = []
        for m in data.get("most", []):
            champ_info = CHAMPION_ID_NAME_MAP.get(str(m["champ_id"]), {})
            champ_key = champ_info.get("key", "")
            converted_most.append({
                "champ_key": champ_key,
                "champ":     m["champ"],
                "games":     m["games"],
                "winrate":   m["winrate"],
            })
        data["most"] = converted_most

        champ_id = p.get("championId")
        champ_info = CHAMPION_ID_NAME_MAP.get(str(champ_id), {})
        champ_name = champ_info.get("name", f"챔피언ID:{champ_id}")
        champ_key  = champ_info.get("key", "")
        champ_tags = champ_info.get("tags", [])
        

        spell1_id = str(p.get("spell1Id"))
        spell2_id = str(p.get("spell2Id"))

        spell1_key = SPELL_ID_TO_KEY.get(spell1_id, "")  # 예: 'SummonerSmite'
        spell2_key = SPELL_ID_TO_KEY.get(spell2_id, "")

        perks = p.get("perks", {})
        perk_ids = perks.get("perkIds", [])
        rune_id = str(perk_ids[0]) if perk_ids else None

        #entry = f"{tier_emoji}{rune_emoji}{spell1_emoji}{spell2_emoji} **{champ_name}** - {summoner_name} **[{winrate}%]**"
        entry = {
            "champ": champ_name,
            "champ_key": champ_key,        # "Xayah", "LeeSin" 등 영문 키
            "spell1_key": spell1_key,      # "SummonerFlash" 등
            "spell2_key": spell2_key,
            "rune_path": RUNE_ID_TO_PATH.get(rune_id, ""),  # "perk-images/Styles/..."
            "name": summoner_name,
            "tier": data['tier'] or "UNRANKED",
            "winrate": data['winrate'] if data['winrate'] is not None else "N/A",
            "games": data['games'], # 올 시즌 판 수
            "most" : data['most'], # 올 시즌 모스트 3
            "champ_tags": champ_tags      # 포지션 판별용
        }
        
        if p.get("teamId") == 100:
            team1_temp.append(entry)
        elif p.get("teamId") == 200:
            team2_temp.append(entry)
    
    # 포지션 최적화
    team1 = assign_positions(team1_temp)
    team2 = assign_positions(team2_temp)

    version = await get_latest_ddragon_version()
    img_buf = await create_ingame_image(team1, team2, version, banned_champions)
    file = discord.File(img_buf, filename="ingame.png")
    return file


async def fake_nowgame(puuid):
    print("🧪 fake_nowgame 호출됨!")
    return True, "솔로랭크"

async def nowgame(puuid, retries=5, delay=5):
    url = f'https://kr.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}'
    headers = {'X-Riot-Token': API_KEY}

    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        game_id = data.get("gameId")
                        game_mode = data.get("gameMode")
                        game_type = data.get("gameType")
                        game_start_time = data.get("gameStartTime")
                        queue_id = data.get("gameQueueConfigId")

                        if game_mode == "CLASSIC" and game_type == "MATCHED":
                            if queue_id == 420:
                                return True, "솔로랭크", game_id, game_start_time
                            elif queue_id == 440:
                                return True, "자유랭크", game_id, game_start_time

                        return False, None, game_id, None  # 랭크 게임이 아닐 경우

                    elif response.status == 404:
                        return False, None, None, None  # 현재 게임이 없으면 재시도할 필요 없음

                    elif response.status in [500, 502, 503, 504, 524]:  # 524 추가
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARNING] nowgame에서 {response.status} 오류 발생, 재시도 중 {attempt + 1}/{retries}...")

                    else:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] nowgame에서 {response.status} 오류 발생")
                        return False, None, None, None  # 다른 오류는 재시도하지 않음

        except aiohttp.ClientConnectorError as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] nowgame에서 연결 오류 발생: {e}, 재시도 중 {attempt + 1}/{retries}...")
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] nowgame에서 예기치 않은 오류 발생: {e}")
            return False, None, None, None

        await asyncio.sleep(delay)  # 재시도 간격 증가

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] nowgame에서 모든 재시도 실패")
    return False, None, None, None

async def get_summoner_puuid(riot_id, tagline):
    url = f'https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{riot_id}/{tagline}'
    headers = {'X-Riot-Token': API_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data['puuid']
            else:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_puuid에서 {response.status} 오류 발생")
                return None

async def get_summoner_ranks(puuid, type="솔로랭크", retries=5, delay=5):
    url = f'https://kr.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}'
    headers = {'X-Riot-Token': API_KEY}

    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if type == "솔로랭크":
                            filtered_data = [entry for entry in data if entry.get("queueType") == "RANKED_SOLO_5x5"]
                        elif type == "자유랭크":
                            filtered_data = [entry for entry in data if entry.get("queueType") == "RANKED_FLEX_SR"]
                        return filtered_data[0] if filtered_data else []

                    elif response.status == 404:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_ranks에서 404 오류 발생")
                        return None  # 소환사 정보가 없으면 재시도할 필요 없음

                    elif response.status in [500, 502, 503, 504, 524]:  
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARNING] get_summoner_ranks에서 {response.status} 오류 발생, 재시도 중 {attempt + 1}/{retries}...")  
                    else:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_ranks에서 {response.status} 오류 발생")
                        return None  # 다른 오류는 재시도 없이 종료

        except aiohttp.ClientConnectorError as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_ranks에서 연결 오류 발생: {e}, 재시도 중 {attempt + 1}/{retries}...")
        except aiohttp.ClientOSError as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_ranks에서 클라이언트 오류 발생 (서버 연결 해제): {e}, 재시도 중 {attempt + 1}/{retries}...")
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_ranks에서 예기치 않은 오류 발생: {e}, 재시도 중 {attempt + 1}/{retries}...")

        await asyncio.sleep(delay)  # 재시도 간격

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_ranks 모든 재시도 실패")
    return None

async def get_summoner_recentmatch_id(puuid, retries=5, delay=5):
    url = f'https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=1'
    headers = {'X-Riot-Token': API_KEY}

    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data[0] if data else None

                    elif response.status == 404:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_recentmatch_id에서 404 오류 발생: PUUID {puuid}에 대한 매치가 없습니다.")
                        return None  # PUUID가 잘못된 경우는 재시도할 필요 없음

                    elif response.status in [500, 502, 503, 504, 524]:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARNING] get_summoner_recentmatch_id에서 {response.status} 오류 발생, 재시도 중 {attempt + 1}/{retries}...")
                    else:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_recentmatch_id에서 {response.status} 오류 발생")
                        return None

        except aiohttp.ClientConnectorError as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_recentmatch_id에서 연결 오류 발생: {e}, 재시도 중 {attempt + 1}/{retries}...")
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_recentmatch_id에서 예기치 않은 오류 발생: {e}, 재시도 중 {attempt + 1}/{retries}...")
            return None

        await asyncio.sleep(delay)  # 재시도 간격

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_recentmatch_id 모든 재시도 실패")
    return None

async def get_summoner_matchinfo(matchid, retries=5, delay=5):
    url = f'https://asia.api.riotgames.com/lol/match/v5/matches/{matchid}'
    headers = {'X-Riot-Token': API_KEY}

    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()

                    elif response.status == 404:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_matchinfo에서 404 오류 발생: 매치 ID {matchid}를 찾을 수 없습니다.")
                        return None  # 매치 ID가 잘못된 경우는 재시도할 필요 없음

                    elif response.status == 400:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_matchinfo에서 400 오류 발생: 잘못된 매치 ID {matchid}.")
                        return None  # 잘못된 요청이라면 재시도할 필요 없음

                    elif response.status in [500, 502, 503, 504, 524]:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARNING] get_summoner_matchinfo에서 {response.status} 오류 발생, 재시도 중 {attempt + 1}/{retries}...")
                    else:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_matchinfo에서 {response.status} 오류 발생")
                        return None

        except aiohttp.ClientConnectorError as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_matchinfo에서 연결 오류 발생: {e}, 재시도 중 {attempt + 1}/{retries}...")
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_matchinfo에서 예기치 않은 오류 발생: {e}, 재시도 중 {attempt + 1}/{retries}...")
            return None

        await asyncio.sleep(delay)  # 재시도 간격

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_matchinfo 모든 재시도 실패")
    return None

async def refresh_prediction(name, prediction_votes):
    """
    주어진 소환사의 예측 현황을 업데이트합니다.
    Args:
        name: 소환사 이름
        prediction_votes: 예측 투표 데이터 (승리 예측과 패배 예측을 포함하는 딕셔너리)
    Returns:
        None
    """
    embed = discord.Embed(title=f"{name} 예측 현황", color=0x000000) # Black
   
    win_predictions = "\n".join(f"{user['name'].display_name}" for user in prediction_votes["win"]) or "없음"
    lose_predictions = "\n".join(f"{user['name'].display_name}" for user in prediction_votes["lose"]) or "없음"
    
    embed.add_field(name="승리 예측", value=win_predictions, inline=True)
    embed.add_field(name="패배 예측", value=lose_predictions, inline=True)
        
    await p.current_messages[name].edit(embed=embed)

async def refresh_kda_prediction(name, kda_votes):
    """
    주어진 소환사의 KDA 예측 현황을 업데이트합니다.
    Args:
        name: 소환사 이름
        kda_votes: KDA 예측 투표 데이터 (KDA 3 이상, KDA 3 이하, 퍼펙트를 포함하는 딕셔너리)
    Returns:
        None
    """
    embed = discord.Embed(title=f"{name} KDA 예측 현황", color=0x000000) # Black

    up_predictions = "\n".join(f"{user['name'].display_name}" for user in kda_votes["up"]) or "없음"
    down_predictions = "\n".join(f"{user['name'].display_name}" for user in kda_votes["down"]) or "없음"
    perfect_predictions = "\n".join(f"{user['name'].display_name}" for user in kda_votes["perfect"]) or "없음"

    embed.add_field(name="KDA 3 이상", value=up_predictions, inline=False)
    embed.add_field(name="KDA 3 이하", value=down_predictions, inline=False)
    embed.add_field(name="퍼펙트", value=perfect_predictions, inline=False)
    
    await p.current_messages_kda[name].edit(embed=embed)

def tier_to_number(tier, rank, lp): # 티어를 레이팅 숫자로 변환
    """
    주어진 소환사의 티어를 숫자로 변환합니다.
    Args:
        tier: 소환사 티어
        rank: 소환사 랭크
        lp: 소환사 LP
    Returns:
        소환사의 티어를 숫자로 변환한 값 (예: Iron IV 0LP -> 0,  EMERALD II 69LP -> 2669)
    """
    tier_num = TIER_RANK_MAP.get(tier)
    rank_num = RANK_MAP.get(rank)
    if tier_num is None or rank_num is None:
        return None
    return tier_num * 400 + rank_num * 100 + lp

def get_lp_and_tier_difference(previous_rank, current_rank,rank_type,name): # 이전 랭크와 현재 랭크를 받아 차이를 계산하여 메세지 반환(승급/강등)

    # 티어 변화 확인
    tier_change = False
    if current_rank["tier"] != previous_rank["tier"]:
        tier_change = True

    # 현재 LP와 이전 LP의 차이 계산
    prev_tier_num = TIER_RANK_MAP.get(previous_rank["tier"])
    current_tier_num = TIER_RANK_MAP.get(current_rank["tier"])
    prev_rank_num = RANK_MAP.get(previous_rank["rank"])
    current_rank_num = RANK_MAP.get(current_rank["rank"])
    lp_difference = (current_tier_num * 400 + current_rank_num * 100 + current_rank["leaguePoints"]) - (prev_tier_num * 400 + prev_rank_num * 100 + previous_rank["leaguePoints"])
    save_lp_difference_to_file(lp_difference,current_rank,rank_type,name)
    # 티어가 바뀌었을 경우
    if tier_change:
        prev_tier_num = TIER_RANK_MAP.get(previous_rank["tier"])
        current_tier_num = TIER_RANK_MAP.get(current_rank["tier"])
        if prev_tier_num and current_tier_num:
                    if current_tier_num > prev_tier_num:
                        return f"@here\n{name}(이)가 {current_rank['tier']}(으)로 승급하였습니다!:partying_face:"
                    elif current_tier_num < prev_tier_num:
                        return f"{name}(이)가 {current_rank['tier']}(으)로 강등되었습니다."
                    else:
                        return "티어 변동이 없습니다."
    else:
        # 티어는 동일하고 LP만 변화한 경우
        if lp_difference > 0:
            return f"승리!\n{current_rank['tier']} {current_rank['rank']} {current_rank['leaguePoints']}P (+{lp_difference}P)"
        elif lp_difference < 0:
            return f"패배..\n{current_rank['tier']} {current_rank['rank']} {current_rank['leaguePoints']}P (-{-lp_difference}P)"
        else:
            return f"패배..\n{current_rank['tier']} {current_rank['rank']} {current_rank['leaguePoints']}P (-0P)"

def save_lp_difference_to_file(lp_difference,current_rank,rank_type,name): # 사용자의 점수 변화량과 날짜를 파이어베이스에 저장
    # 현재 날짜 가져오기
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rank_num = tier_to_number(current_rank["tier"],current_rank["rank"],current_rank["leaguePoints"])

    # 현재 날짜 및 시간 가져오기
    current_datetime = datetime.now()

    # 날짜만 추출하여 저장
    current_date = current_datetime.strftime("%Y-%m-%d")

    # 시간만 추출하여 저장
    current_time = current_datetime.strftime("%H:%M:%S")

    curseasonref = db.reference("전적분석/현재시즌")
    current_season = curseasonref.get()

    refprev = db.reference(f'전적분석/{current_season}/점수변동/{name}/{rank_type}')
    points = refprev.get()

    if points is None:
        win_streak = 0
        lose_streak = 0
    else:
        # 가장 최근의 날짜를 찾음
        latest_date = max(points.keys())

        # 해당 날짜의 시간들을 정렬하여 가장 최근의 시간을 찾음
        latest_time = max(points[latest_date].keys(), key=lambda t: datetime.strptime(t, '%H:%M:%S'))

        # 가장 최근의 데이터
        latest_data = points[latest_date][latest_time]

        win_streak = latest_data["연승"]
        lose_streak = latest_data["연패"]
    if lp_difference <= 0:
        result = 0
    else:
        result = 1

    if result:
        win_streak += 1
        lose_streak = 0
    else:
        win_streak = 0
        lose_streak += 1

    # 파이어베이스에 저장
    ref = db.reference(f'전적분석/{current_season}/점수변동/{name}/{rank_type}/{current_date}/{current_time}')
    ref.update({'LP 변화량' : lp_difference})
    ref.update({'현재 점수' : rank_num})
    ref.update({"연승": win_streak})
    ref.update({"연패": lose_streak})

def get_participant_id(match_info, puuid): # match정보와 puuid를 통해 그 판에서 플레이어의 위치를 반환
    for i, participant in enumerate(match_info['info']['participants']):
        if participant['puuid'] == puuid:
            return i
    return None

async def get_opgg_tier(session: aiohttp.ClientSession, name, tag, mode="솔로랭크"):
    """
    OP.GG에서 소환사의 티어 정보를 크롤링하여 반환합니다.
    Args:
        session: aiohttp 클라이언트 세션
        name: 소환사 이름   
        tag: 소환사 태그 (예: KR1, KR2 등)
    Returns:
        티어 이름 + 티어 번호 (예: "Platinum1") 또는 오류 메시지
    """
    mode_map = {
        "솔로랭크": "Ranked Solo/Duo",
        "자유랭크": "Ranked Flex",
    }

    if mode not in mode_map:
        return None, None

    target_label = mode_map[mode]

    url = f"https://www.op.gg/summoners/kr/{name}-{tag}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    try:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                return None, None
            html = await response.text()
    except Exception:
        return None, None

    soup = BeautifulSoup(html, 'html.parser')

    for section in soup.find_all('section'):
        if not section.find('span', string=target_label):
            continue

        # 티어 추출
        tier_tag = section.find('strong', class_=lambda c: c and 'text-xl' in c)
        if not tier_tag:
            return "UNRANKED", None

        tier_text = tier_tag.get_text(strip=True)
        match = re.match(
            r'(iron|bronze|silver|gold|platinum|emerald|diamond|master|grandmaster|challenger)\s*(\d?)',
            tier_text, re.IGNORECASE
        )
        tier = f"{match.group(1).upper()}{match.group(2)}".strip() if match else "UNRANKED"

        # 승/패 추출 → 승률 계산
        wl_tag = section.find('span', class_=lambda c: c and 'leading-[26px]' in c)
        winrate = None
        if wl_tag:
            wl_text = wl_tag.get_text(separator='', strip=True)
            wl_match = re.search(r'(\d+)W.*?(\d+)L', wl_text)
            if wl_match:
                wins = int(wl_match.group(1))
                losses = int(wl_match.group(2))
                total = wins + losses
                if total > 0:
                    winrate = round(wins / total * 100, 1)

        return tier, winrate

    return "UNRANKED", None

async def get_fow_multisearch(session: aiohttp.ClientSession, summoners: list[tuple[str, str]], mode="솔로랭크"):
    """
    Returns:
        { "name#tag": {
            "tier": str,
            "winrate": float | None,
            "games": int | None,
            "most": [
                {"champ": str, "games": int, "winrate": float},
                ...  # 최대 3개
            ]
        }}
    """
    mode_map = {
        "솔로랭크": ["솔로랭크", "Ranked Solo"],
        "자유랭크": ["자유랭크", "Ranked Flex"],
    }
    mode_labels = mode_map.get(mode, ["솔로랭크", "Ranked Solo"])

    text = ",".join(f"{name} #{tag}" for name, tag in summoners)
    url = "https://www.fow.lol/api/multisearch"
    params = {"region": "kr", "text": text}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.fow.lol/",
    }

    async with session.get(url, params=params, headers=headers) as resp:
        if resp.status != 200:
            return {}
        html = await resp.text()

    soup = BeautifulSoup(html, 'html.parser')
    results = {}

    for line in soup.select("div.multisearch_line"):
        divs = line.select("div.multisearch_line > div")
        if not divs:
            continue

        info_block = divs[0]

        # 소환사 이름 + 태그
        link = info_block.select_one("a.summoner_link")
        if not link:
            continue
        name = link.contents[0].strip()
        tag_el = link.select_one("span.tag")
        tag = tag_el.text.strip().lstrip("#") if tag_el else ""
        key = f"{name}#{tag}"

        # 티어 파싱 (예: "PLATINUM I 39 LP", "CHALLENGER 1977 LP")
        tier = "UNRANKED"
        for div in info_block.find_all("div"):
            t = div.get_text(strip=True)
            match = re.match(
                r'(CHALLENGER|GRANDMASTER|MASTER|DIAMOND|EMERALD|PLATINUM|GOLD|SILVER|BRONZE|IRON)'
                r'(?:\s+([IVX]+))?(?:\s+\d+\s+LP)?$',
                t, re.IGNORECASE
            )
            if match:
                tier_name = match.group(1).upper()
                division  = match.group(2).upper() if match.group(2) else ""
                tier = f"{tier_name} {division}".strip()
                break

        # 승/패/게임수/승률 파싱 (예: "솔로랭크: 53W 53L (50.00%)")
        winrate, games = None, None
        for div in info_block.find_all("div"):
            t = div.get_text(strip=True)
            if not any(label in t for label in mode_labels):  # ← any로 변경
                continue
            wl_match = re.search(r'(\d+)W\s*(\d+)L', t)
            if wl_match:
                w = int(wl_match.group(1))
                l = int(wl_match.group(2))
                games   = w + l
                winrate = round(w / games * 100, 1) if games > 0 else None
            break

        # 모스트 챔피언 파싱 (최대 3개)
        # multisearch_champlist 는 line 내 두번째 div 블록 안에 있음
        most = []
        champ_list = line.select_one("div.multisearch_champlist")
        if champ_list:
            for champ_div in champ_list.select("div.multisearch_champ")[:3]:
                champ_id = champ_div.get("data-toggle-id", "")
                champ_divs = champ_div.select("div")
                if len(champ_divs) < 4:
                    continue

                champ_name  = champ_divs[1].get_text(strip=True)
                champ_games = champ_divs[2].get_text(strip=True)
                wr_text     = champ_divs[3].get_text(strip=True).replace("%", "")

                try:
                    most.append({
                        "champ_id": champ_id,
                        "champ":   champ_name,
                        "games":   int(champ_games),
                        "winrate": float(wr_text),
                    })
                except ValueError:
                    continue

        results[key] = {
            "tier":    tier,
            "winrate": winrate,
            "games":   games,
            "most":    most,
        }

    return results


def calculate_bonus(streak):
    bonus = 3 * streak
    return bonus

opened_games = set()
active_games = defaultdict(lambda: {"players": [], "game_start_time": None})
tracked_users = set()
monitored_games = set()
async def monitor_games():
    """
    게임 모니터링: REGISTERED_USERS들이 게임을 시작했는지 주기적으로 확인하여 예측 오픈
    """
    await bot.wait_until_ready()
    while not bot.is_closed():
        # 전체 플레이어를 한번에 검사
        for username in REGISTERED_USERS:
            
            if username in tracked_users:
                continue  # 이미 추적 중인 플레이어는 건너뜀
            puuid = PUUID[username]

            ingame, mode, game_id, game_start_time = await nowgame(puuid)

            if ingame:
                tracked_users.add(username)  # 추적 중인 플레이어로 추가
                active_games[game_id]["players"].append((username, mode))
                active_games[game_id]["game_start_time"] = game_start_time
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [LOG] {username}이(가) 게임 중입니다! (게임 ID: {game_id}, 모드: {mode})")  

        # 게임 id 단위로 처리
        for game_id, data in active_games.items():
            players = data["players"]
            game_start_time = data["game_start_time"]

            if game_id in opened_games: # 이미 예측이 열린 게임이라면
                continue

            # 같은 게임 id를 가진 플레이어들 중에서 랜덤으로 한 명을 선택하여 예측 오픈
            selected_user, mode = random.choice(players)

            # 진행중인 게임 목록에 게임 id 추가
            opened_games.add(game_id)
            active_games[game_id]["prediction_owner"] = selected_user
            # 예측 오픈
            bot.loop.create_task(
                open_prediction(
                    name=selected_user,
                    mode=mode,
                    game_id=game_id,
                    game_start_time = game_start_time
                )
            )

        await asyncio.sleep(20)

# 플레이어 별 게임 종료 모니터링 (동시 처리)
async def monitor_single_player_ending(name, game_id, current_game_type, channel, notice_channel):
    puuid = PUUID[name]
    
    # 마지막으로 확인한 랭크 정보 가져오기
    try:
        last_rank = await get_summoner_ranks(puuid, current_game_type) 
    except NotFoundError:
        last_rank = None

    recent_match_id = None
    while not bot.is_closed():
        # 게임 종료 체크
        ingame, _, _, _ = await nowgame(puuid)
        if not ingame: # 게임 종료 의심 상태
            await asyncio.sleep(20) # 20초 후 재확인
            recent_match_id = await get_summoner_recentmatch_id(puuid)
            if recent_match_id.split("_")[1] == str(game_id): # 최근 매치가 해당 게임과 동일하다면 게임이 종료된 것으로 간주
                break
        await asyncio.sleep(20)  # API 호출 간 20초 대기
    
    if recent_match_id is None:
        return

    # 다시하기 여부 확인
    match_info = await get_summoner_matchinfo(recent_match_id)
    participant_id = get_participant_id(match_info, puuid)

    if match_info['info']['participants'][participant_id]['gameEndedInEarlySurrender']:
        userembed = discord.Embed(title=f"{name}의 게임 종료!", color=discord.Color.light_gray())
        userembed.add_field(name=f"{name}의 랭크게임이 종료되었습니다!", value="결과 : 다시하기!")
        await channel.send(embed=userembed)

        if name in p.votes:
            votes = p.votes[name]
            votes['prediction']['win'].clear()
            votes['prediction']['lose'].clear()
            votes['kda']['up'].clear()
            votes['kda']['down'].clear()
            votes['kda']['perfect'].clear()         

            active_games.pop(game_id, None) # 게임 종료된 게임 id는 active_games에서 제거 (존재하지 않을 수 있으므로 None 기본값)
            tracked_users.discard(name) # 게임 종료된 플레이어는 추적 대상에서 제거
            p.events[name].set()
        return

    try:
        current_rank = await get_summoner_ranks(puuid, current_game_type)
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] monitor_single_player_ending에서 예기치 않은 오류 발생: {e}")
        current_rank= None

    if not current_rank:
        current_total_match = 0
    else:
        current_win = current_rank['wins']
        current_loss = current_rank['losses']
        current_total_match = current_win + current_loss

        if last_rank:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [LOG] {name}의 {current_total_match}번째 {current_game_type} 게임 완료")
            string = get_lp_and_tier_difference(last_rank, current_rank, current_game_type, name)
            await notice_channel.send(f"\n{name}의 {current_game_type} 점수 변동이 감지되었습니다!\n{string}")
            await channel.send(f"\n{name}의 {current_game_type} 점수 변동이 감지되었습니다!\n{string}")

    prediction_owner = active_games.get(game_id, {}).get("prediction_owner")
    tracked_users.discard(name)
    if name in p.votes and name == prediction_owner:
        active_games.pop(game_id, None) # 게임 종료된 게임 id는 active_games에서 제거 (존재하지 않을 수 있으므로 None 기본값)
         # 게임 종료된 플레이어는 추적 대상에서 제거
        await predict_results(name,current_game_type) # 예측 결과 처리

# 게임 종료 모니터링: 게임이 종료되었는지 주기적으로 확인하여 점수 변동 감지 및 예측 결과 처리 (동시에 모든 플레이어 모니터링)
async def monitor_endings():
    await bot.wait_until_ready()
    channel = bot.get_channel(int(CHANNEL_ID)) # 일반 채널
    notice_channel = bot.get_channel(int(NOTICE_CHANNEL_ID)) # 공지 채널
    
    # 게임 진행중인 플레이어들에 대해서 게임 종료 여부 동시에 확인
    while not bot.is_closed():
        for game_id, data in active_games.items():
            players = data["players"]

            if game_id in monitored_games:
                continue

            monitored_games.add(game_id)

            for name, current_game_type in players:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [LOG] {name}의 게임 종료를 모니터링 중입니다. (게임 ID: {game_id}, 모드: {current_game_type})")
                asyncio.create_task(monitor_single_player_ending(name, game_id, current_game_type, channel, notice_channel))
        
        await asyncio.sleep(10)
# 예측 결과 처리
async def predict_results(name, current_game_type):
    # 예측 결과 처리
    onoffref = db.reference("승부예측/투표온오프") # 투표가 off 되어있을 경우 결과 출력 X
    onoffbool = onoffref.get()

    if name not in p.votes:
        prediction_opened = False
    else:
        prediction_opened = True
        

    if not onoffbool or not prediction_opened: # 투표가 off 되어있거나 예측이 열리지 않았을 경우 결과 출력 X
        
        curseasonref = db.reference("전적분석/현재시즌")
        current_season = curseasonref.get()

        ref = db.reference(f'전적분석/{current_season}/점수변동/{name}/{current_game_type}')
        points = ref.get()

        point_change = 0
        if points is None:
            game_win_streak = 0
            game_lose_streak = 0
            result = True
        else:
            # 날짜 정렬
            sorted_dates = sorted(points.keys(), key=lambda d: datetime.strptime(d, '%Y-%m-%d'))

            # 가장 최근 날짜 가져오기
            latest_date = sorted_dates[-1]
            latest_times = sorted(points[latest_date].keys(), key=lambda t: datetime.strptime(t, '%H:%M:%S'))

            if len(latest_times) > 1:
                # 같은 날짜에 여러 게임이 있는 경우, 가장 최근 경기의 "바로 전 경기" 선택
                previous_time = latest_times[-2]
                latest_time = latest_times[-1]
            else:
                # 가장 최근 날짜에 한 판만 있었다면, 이전 날짜로 넘어감
                if len(sorted_dates) > 1:
                    previous_date = sorted_dates[-2]
                    previous_times = sorted(points[previous_date].keys(), key=lambda t: datetime.strptime(t, '%H:%M:%S'))
                    previous_time = previous_times[-1]  # 이전 날짜에서 가장 늦은 경기
                    latest_time = latest_times[-1]
                else:
                    # 데이터가 한 판밖에 없는 경우 (첫 경기), 연승/연패 초기화
                    game_win_streak = 0
                    game_lose_streak = 0
                    latest_time = latest_times[-1]
                    previous_time = None

            # 최신 경기 데이터
            latest_data = points[latest_date][latest_time]
            point_change = latest_data['LP 변화량']
            result = point_change > 0  # 승리 여부 판단

            if previous_time:
                # "바로 전 경기" 데이터 가져오기
                if previous_time in points[latest_date]:  # 같은 날짜에서 찾은 경우
                    previous_data = points[latest_date][previous_time]
                else:  # 이전 날짜에서 가져온 경우
                    previous_data = points[previous_date][previous_time]

                # "바로 전 경기"의 연승/연패 기록 사용
                game_win_streak = previous_data["연승"]
                game_lose_streak = previous_data["연패"]
            else:
                # 첫 경기라면 연승/연패 초기화
                game_win_streak = 0
                game_lose_streak = 0

        if result:
            userembed = discord.Embed(title=f"{name}의 게임 종료!", color=discord.Color.blue())
        else:
            userembed = discord.Embed(title=f"{name}의 게임 종료!", color=discord.Color.red())
        

        userembed.add_field(name=f"{name}의 {current_game_type} 게임이 종료되었습니다!", value=f"결과 : **{'승리!' if result else '패배..'}**\n점수변동: {point_change}")
        await calculate_points(name, result, userembed) # 예측 포인트 정산

# 예측 포인트 정산
async def calculate_points(name, result, userembed):
    channel = bot.get_channel(int(CHANNEL_ID)) # 일반 채널
    puuid = PUUID[name]
    event = p.events[name]
    prediction_votes = p.votes[name]["prediction"]
    kda_votes = p.votes[name]["kda"]
    
    winners = prediction_votes['win'] if result else prediction_votes['lose']
    losers = prediction_votes['lose'] if result else prediction_votes['win']

    cur_predict_seasonref = db.reference("승부예측/현재예측시즌") # 현재 진행중인 예측 시즌을 가져옴
    current_predict_season = cur_predict_seasonref.get()

    for winner in winners:
        point_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner['name'].name}")
        predict_data = point_ref.get()

        if predict_data is None:
            predict_data = {}
        
        point = predict_data.get("포인트",0)

        prediction_value = "승리" if result else "패배"
        prediction_opposite_value = "패배" if result else "승리"
        # 예측 내역 업데이트
        point_ref.update({
            "포인트": point,
            "총 예측 횟수": predict_data.get("총 예측 횟수",0) + 1,
            "적중 횟수": predict_data.get("적중 횟수",0) + 1,
            "적중률": f"{round((((predict_data.get('적중 횟수',0) + 1) * 100) / (predict_data.get('총 예측 횟수',0) + 1)), 2)}%",
            "연승": predict_data.get("연승",0) + 1,
            "연패": 0,
        
            # 추가 데이터
            f"{name}적중": predict_data.get(f"{name}적중", 0) + 1,
            f"{name}{prediction_value}예측": predict_data.get(f"{name}{prediction_value}예측", 0) + 1,
            f"{prediction_value}예측연속": predict_data.get(f"{prediction_value}예측연속", 0) + 1,
            f"{prediction_opposite_value}예측연속": 0
        })

        win_streak = predict_data.get('연승', 0) + 1
        streak_bonus = calculate_bonus(win_streak)
        streak_text = f"{win_streak}연속 적중으로 " if win_streak > 1 else ""
        streak_bonus_text = f"(+{streak_bonus})" if win_streak > 1 else ""
        
        add_points = 20 + streak_bonus if win_streak > 1 else 20
        userembed.add_field(name="", value=f"**{winner['name'].display_name}**님이 {streak_text}**{add_points}**{streak_bonus_text}점을 획득하셨습니다!", inline=False)

        point_ref.update({"포인트": point + add_points})
    for loser in losers:
        point_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{loser['name'].name}")
        predict_data = point_ref.get()

        if predict_data is None:
            predict_data = {}

        point = predict_data.get("포인트",0)
        
        prediction_value = "패배" if result else "승리"
        prediction_opposite_value = "승리" if result else "패배"
        # 예측 내역 업데이트
        point_ref.update({
            "포인트": point,
            "총 예측 횟수": predict_data.get("총 예측 횟수",0) + 1,
            "적중 횟수": predict_data.get("적중 횟수",0),
            "적중률": f"{round((((predict_data.get('적중 횟수',0)) * 100) / (predict_data.get('총 예측 횟수',0) + 1)), 2)}%",
            "연승": 0,
            "연패": predict_data.get("연패",0) + 1,

            # 추가 데이터
            f"{name}{prediction_value}예측": predict_data.get(f"{name}{prediction_value}예측", 0) + 1,
            f"{prediction_value}예측연속": predict_data.get(f"{prediction_value}예측연속", 0) + 1,
            f"{prediction_opposite_value}예측연속": 0
        })

    await channel.send(embed=userembed)

    # KDA 예측
    match_id = await get_summoner_recentmatch_id(puuid)
    match_info = await get_summoner_matchinfo(match_id)

    for player in match_info['info']['participants']:
        if puuid == player['puuid']:
            kda = 999 if player['deaths'] == 0 else round((player['kills'] + player['assists']) / player['deaths'], 1)

            if kda == 999:
                kdaembed = discord.Embed(title=f"{name} KDA 예측 결과", color=discord.Color.gold())
            elif kda == 3:
                kdaembed = discord.Embed(title=f"{name} KDA 예측 결과", color=discord.Color.purple())
            elif kda > 3:
                kdaembed = discord.Embed(title=f"{name} KDA 예측 결과", color=discord.Color.blue())
            elif kda < 3:
                kdaembed = discord.Embed(title=f"{name} KDA 예측 결과", color=discord.Color.red())

            kdaembed.add_field(name=f"{name}의 KDA", value=f"{player['championName']} {player['kills']}/{player['deaths']}/{player['assists']}({'PERFECT' if kda == 999 else kda})", inline=False)
            
            if kda > 3:
                perfect_winners = kda_votes['perfect'] if kda == 999 else []
                winners = kda_votes['up']
                losers = kda_votes['down'] + (kda_votes['perfect'] if kda != 999 else [])
                for perfect_winner in perfect_winners:
                    point_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{perfect_winner['name'].name}")
                    predict_data = point_ref.get()

                    if predict_data is None:
                        predict_data = {}

                    point_ref.update({"포인트": predict_data["포인트"] + 100})
                    kdaembed.add_field(name="", value=f"{perfect_winner['name'].display_name}님이 KDA 퍼펙트 예측에 성공하여 100점을 획득하셨습니다!", inline=False)

                for winner in winners:
                    point_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner['name'].name}")
                    predict_data = point_ref.get()

                    if predict_data is None:
                        predict_data = {}

                    point_ref.update({"포인트": predict_data["포인트"] + 10})
                    kdaembed.add_field(name="", value=f"{winner['name'].display_name}님이 KDA 예측에 성공하여 10점을 획득하셨습니다!", inline=False)
            elif kda == 3:
                winners = kda_votes['up'] + kda_votes['down']
                losers = kda_votes['perfect']

                for winner in winners:
                    point_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner['name'].name}")
                    predict_data = point_ref.get()

                    if predict_data is None:
                        predict_data = {}

                    point_ref.update({"포인트": predict_data["포인트"] + 10})
                    kdaembed.add_field(name="", value=f"{winner['name'].display_name}님이 KDA 예측에 성공하여 10점을 획득하셨습니다!", inline=False)
            else:
                winners = kda_votes['down']
                losers = kda_votes['up'] + kda_votes['perfect']
                for winner in winners:
                    point_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner['name'].name}")
                    predict_data = point_ref.get()

                    if predict_data is None:
                        predict_data = {}

                    point_ref.update({"포인트": predict_data["포인트"] + 10})
                    kdaembed.add_field(name="", value=f"{winner['name'].display_name}님이 KDA 예측에 성공하여 10점을 획득하셨습니다!", inline=False)

            await channel.send(embed=kdaembed)

            
            img_buf = await create_match_result_image(
                match_info    = match_info,
                target_name   = name,
            )
            file = discord.File(img_buf, filename="match_result.png")
            await channel.send(file=file)

            kda_votes['up'].clear()
            kda_votes['down'].clear()
            kda_votes['perfect'].clear()
            prediction_votes['win'].clear()
            prediction_votes['lose'].clear()

            event.set()       

# 예측 오픈 함수: 게임이 감지되면 해당 게임에 대한 예측을 오픈하는 함수
async def open_prediction(name, mode, game_id, game_start_time):
    await bot.wait_until_ready()
    channel = bot.get_channel(int(CHANNEL_ID))
    notice_channel = bot.get_channel(int(NOTICE_CHANNEL_ID))

    cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
    current_predict_season = cur_predict_seasonref.get()

    puuid = PUUID[name]

    p.votes[name] = {
        "prediction": {
            "win": [],
            "lose": []
        },
        "kda": {
            "up": [],
            "down": [],
            "perfect": []
        }
    }

    votes = p.votes[name]

    p.events[name] = asyncio.Event()
    event = p.events[name]

    p.winbuttons[name] = discord.ui.Button(style=discord.ButtonStyle.success,label="승리")
    winbutton = p.winbuttons[name]

    p.current_match_id_flex[name] = ""
    p.current_match_id_solo[name] = ""
    
    onoffref = db.reference("승부예측/투표온오프")
    onoffbool = onoffref.get()

    # 이전 게임의 match_id를 저장
    if mode == "솔로랭크":
        p.current_match_id_solo[name] = await get_summoner_recentmatch_id(puuid)
    else:
        p.current_match_id_flex[name] = await get_summoner_recentmatch_id(puuid)
    p.current_predict_season[name] = current_predict_season

    winbutton.disabled = onoffbool
    losebutton = discord.ui.Button(style=discord.ButtonStyle.danger,label="패배",disabled=onoffbool)

    
    prediction_view = discord.ui.View()
    prediction_view.add_item(winbutton)
    prediction_view.add_item(losebutton)

    upbutton = discord.ui.Button(style=discord.ButtonStyle.success,label="업",disabled=onoffbool)
    downbutton = discord.ui.Button(style=discord.ButtonStyle.danger,label="다운",disabled=onoffbool)
    perfectbutton = discord.ui.Button(style=discord.ButtonStyle.primary,label="퍼펙트",disabled=onoffbool)

    kda_view = discord.ui.View()
    kda_view.add_item(upbutton)
    kda_view.add_item(downbutton)
    kda_view.add_item(perfectbutton)
        
    async def disable_buttons():
        if onoffbool: # 투표 꺼져있다면 안함
            return
        await asyncio.sleep(270)  # 4분 30초 대기
        alarm_embed = discord.Embed(title="알림", description=f"{name}의 예측 종료까지 30초 남았습니다! ⏰", color=discord.Color.red())
        await channel.send(embed=alarm_embed)
        await asyncio.sleep(30) # 30초 대기
        winbutton.disabled = True
        losebutton.disabled = True
        upbutton.disabled = True
        downbutton.disabled = True
        perfectbutton.disabled = True
        prediction_view = discord.ui.View()
        kda_view = discord.ui.View()
        prediction_view.add_item(winbutton)
        prediction_view.add_item(losebutton)
        kda_view.add_item(upbutton)
        kda_view.add_item(downbutton)
        kda_view.add_item(perfectbutton)

        await p.current_messages[name].edit(view=prediction_view)
        await p.current_messages_kda[name].edit(view=kda_view)

    prediction_votes = votes["prediction"]
    kda_votes = votes["kda"]
    
    async def bet_button_callback(interaction: discord.Interaction = None, prediction_type: str = "", nickname: discord.Member = None):
        if interaction:
            nickname = interaction.user
            await interaction.response.defer()  # 응답 지연 (버튼 눌렀을 때 오류 방지)

        # 사용자가 이미 투표한 유형이 있는지 확인
        current_prediction_type = None

        for p_type in ["win", "lose"]:
            if nickname.name in [user['name'].name for user in prediction_votes[p_type]]:
                current_prediction_type = p_type
                break
        
        # 사용자가 같은 유형으로 투표하려는 경우, 이미 투표했다는 메시지를 보내고 함수 종료
        if current_prediction_type == prediction_type:
            userembed = discord.Embed(title="메세지", color=discord.Color.blue())
            userembed.add_field(name="", value=f"{nickname.display_name}님은 이미 {prediction_type}에 투표하셨습니다", inline=True)
            if interaction:
                await interaction.followup.send(embed=userembed, ephemeral=True)
            return
        
        # 사용자가 다른 유형으로 투표하려는 경우, 기존 투표를 제거하고 새로운 투표 추가
        if current_prediction_type:
            prediction_votes[current_prediction_type] = [user for user in prediction_votes[current_prediction_type] if user['name'].name != nickname.name]
            await refresh_prediction(name,prediction_votes) # 새로고침

        prediction_votes[prediction_type].append({"name": nickname})
        await refresh_prediction(name,prediction_votes) # 새로고침

    async def kda_button_callback(interaction: discord.Interaction = None, prediction_type: str = "", nickname: discord.Member = None):
        if not nickname:
            nickname = interaction.user
            await interaction.response.defer()

        # 사용자가 이미 투표한 유형이 있는지 확인
        current_prediction_type = None

        for kda_type in ["up", "down", "perfect"]:
            if nickname.name in [user['name'].name for user in kda_votes[kda_type]]:
                current_prediction_type = kda_type
                break
        
        # 사용자가 같은 유형으로 투표하려는 경우, 이미 투표했다는 메시지를 보내고 함수 종료
        if current_prediction_type == prediction_type:
            userembed = discord.Embed(title="메세지", color=discord.Color.dark_gray())
            userembed.add_field(name="", value=f"{nickname.display_name}님은 이미 {prediction_type}에 투표하셨습니다", inline=True)
            await interaction.followup.send(embed=userembed, ephemeral=True)
            return
        
        # 사용자가 다른 유형으로 투표하려는 경우, 기존 투표를 제거하고 새로운 투표 추가
        if current_prediction_type:
            kda_votes[current_prediction_type] = [user for user in kda_votes[current_prediction_type] if user['name'].name != nickname.name]
            await refresh_kda_prediction(name,kda_votes)
        
        kda_votes[prediction_type].append({"name": nickname})
        await refresh_kda_prediction(name,kda_votes)

    winbutton.callback = lambda interaction: bet_button_callback(interaction, 'win')
    losebutton.callback = lambda interaction: bet_button_callback(interaction, 'lose')
    upbutton.callback = lambda interaction: kda_button_callback(interaction, 'up')
    downbutton.callback = lambda interaction: kda_button_callback(interaction, 'down')
    perfectbutton.callback = lambda interaction: kda_button_callback(interaction, 'perfect')

    prediction_embed = discord.Embed(title=f"{name} 예측 현황", color=0x000000) # Black

    win_predictions = "\n".join(
        f"{winner['name'].display_name}" for winner in prediction_votes["win"]) or "없음"
    lose_predictions = "\n".join(
        f"{loser['name'].display_name}" for loser in prediction_votes["lose"]) or "없음"

    prediction_embed.add_field(name="승리 예측", value=win_predictions, inline=True)
    prediction_embed.add_field(name="패배 예측", value=lose_predictions, inline=True)

    kda_embed = discord.Embed(title=f"{name} KDA 예측 현황", color=0x000000) # Black

    up_predictions = "\n".join(f"{user['name'].display_name}" for user in kda_votes["up"]) or "없음"
    down_predictions = "\n".join(f"{user['name'].display_name}" for user in kda_votes["down"]) or "없음"
    perfect_predictions = "\n".join(f"{user['name'].display_name}" for user in kda_votes["perfect"]) or "없음"

    kda_embed.add_field(name="KDA 3 이상", value=up_predictions, inline=False)
    kda_embed.add_field(name="KDA 3 이하", value=down_predictions, inline=False)
    kda_embed.add_field(name="퍼펙트", value=perfect_predictions, inline=False)

    curseasonref = db.reference("전적분석/현재시즌")
    current_season = curseasonref.get()

    refprev = db.reference(f'전적분석/{current_season}/점수변동/{name}/{mode}')
    points = refprev.get()

    if points is None:
        game_win_streak = 0
        game_lose_streak = 0
    else:
        latest_date = max(points.keys())
        latest_time = max(points[latest_date].keys(), key=lambda t: datetime.strptime(t, '%H:%M:%S'))
        latest_data = points[latest_date][latest_time]
        game_win_streak = latest_data["연승"]
        game_lose_streak = latest_data["연패"]
    

    onoffref = db.reference("승부예측/이벤트온오프")

    streak_message = ""
    if game_win_streak >= 1:
        streak_message = f"{game_win_streak}연승 중!"
    elif game_lose_streak >= 1:        
        streak_message = f"{game_lose_streak}연패 중!"

    unix_seconds = int(game_start_time / 1000)
    p.current_messages[name] = await channel.send(
        f"\n{name}의 {mode} 게임이 감지되었습니다!\n승부예측을 해보세요!\n{streak_message}",
        view=prediction_view,
        embed=prediction_embed
    )   
    await p.current_messages[name].edit( 
        content=f"{name}의 {mode} 게임이 <t:{unix_seconds}:R>에 감지되었습니다!\n승부예측을 해보세요!\n{streak_message}",
    ) 
    p.current_messages_kda[name] = await channel.send("\n", view=kda_view, embed=kda_embed)

    if not onoffbool:
        await notice_channel.send(f"{name}의 {mode} 게임이 감지되었습니다!\n승부예측을 해보세요!\n")
    
    guild = bot.get_guild(GUILD_ID)
    game_player = guild.get_member(MEMBER_MAP[name])
    await bet_button_callback(prediction_type='win', nickname=game_player)
    await kda_button_callback(prediction_type='up', nickname=game_player)
    
    # 듀오 게임인 경우 다른 멤버도 자동 투표
    if game_id in active_games:
        for other_player_name, _ in active_games[game_id]["players"]:
            if other_player_name != name and other_player_name in MEMBER_MAP:
                other_game_player = guild.get_member(MEMBER_MAP[other_player_name])
                if other_game_player:
                    await bet_button_callback(prediction_type='win', nickname=other_game_player)
                    await kda_button_callback(prediction_type='up', nickname=other_game_player)
    
    info_file = await get_team_champion(name, puuid, mode, get_info_func=get_current_game_info)
    await channel.send(file=info_file) # PNG 파일만 전송 (화질 유지)

    event.clear()
    await asyncio.gather(
        disable_buttons(),
        event.wait()  # 이 작업은 event가 set될 때까지 대기
    )
    opened_games.discard(game_id)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [LOG] {name}의 게임 종료! (게임 ID: {game_id}, 모드: {mode})")

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=Intents.all(),
            sync_command=True,
            application_id=1232000910872547350
        )
        self.initial_extension = [
            "Cogs.commands"
        ]

    async def setup_hook(self):
        for ext in self.initial_extension:
            await self.load_extension(ext)

        #await bot.tree.sync(guild=Object(id=298064707460268032))
        await bot.tree.sync()

    async def on_ready(self):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [LOG] {self.user}로 로그인 완료!")
        await self.change_presence(status=Status.online,
                                    activity=Game("만세중"))
        cred = credentials.Certificate("mykey.json")
        firebase_admin.initialize_app(cred,{
            'databaseURL' : 'https://mansaebot-default-rtdb.firebaseio.com/'
        })
        #await self.tree.sync(guild=Object(id=298064707460268032))
        
        await init_browser()
        await fetch_champion_data(True) # 챔피언 데이터를 받음
        await fetch_rune_data(True)
        await fetch_rune_id_to_key_map(True)
        await fetch_spell_id_to_key_map(True)

        bot.loop.create_task(monitor_games())
        bot.loop.create_task(monitor_endings())
        bot.loop.create_task(fetch_patch_version())
bot = MyBot()
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
API_KEY = os.getenv("RIOT_API_KEY")

PUUID = {
    "지모" : os.getenv("JIMO_PUUID"),
    "Melon" : os.getenv("MELON_PUUID"),
    "그럭저럭" : os.getenv("YOON_PUUID"),
    "이미름" : os.getenv("LEE_PUUID"),
    "박퇴경" : os.getenv("PARK_PUUID"),
    "이나호" : os.getenv("NAHO_PUUID"),
}

bot.run(TOKEN)