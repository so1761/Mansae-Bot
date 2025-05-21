import requests
import discord
import platform
import random
import copy
import matplotlib.pyplot as plt
import concurrent.futures
import asyncio
import aiohttp
import pandas as pd
import mplfinance as mpf
import prediction_vote as p
import subprocess
import os
import math
import secrets
import matplotlib.dates as mdates
from discord.ui import Modal, TextInput
from discord import TextStyle
from firebase_admin import db
from discord.app_commands import Choice
from discord import app_commands
from discord.ext import commands
from discord import Interaction
from discord import Object
from datetime import datetime
from matplotlib import font_manager, rc
from dotenv import load_dotenv
from collections import Counter

API_KEY = None

JIMO_NAME = '강지모'
JIMO_TAG = 'KR1'

# 경고 채널의 ID (실제 채널 ID로 변경)
WARNING_CHANNEL_ID = 1314643507490590731
ENHANCEMENT_CHANNEL = 1350434647149908070

SEASON_CHANGE_DATE = datetime(2024, 5, 15, 0, 0, 0)
SEASON_CHANGE_DATE2 = datetime(2024, 9, 11, 0, 0, 0)
SEASON_CHANGE_DATE3 = datetime(2025, 1, 9, 0, 0, 0)
SEASON_CHANGE_DATE15 = datetime(2026,1, 1, 0, 0, 0)


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

#익명 이름
ANONYM_NAME_WIN = [
 '바바리원숭이','회색랑구르','알렌원숭이','코주부원숭이','황금들창코원숭이','안경원숭이','동부콜로부스','붉은잎원숭이','남부돼지꼬리원숭이'
]
ANONYM_NAME_LOSE = [
 '카카포','케아','카카리키','아프리카회색앵무','유황앵무','뉴기니아앵무', '빗창앵무','유리앵무'
]

CHANNEL_ID = '938728993329397781'

weapon_battle_thread = None

enhancement_probabilities = {
    0: 100,  # 0강 - 100% 성공
    1: 90,   # 1강 - 90% 성공
    2: 90,   # 2강 - 90% 성공
    3: 80,   # 3강 - 80% 성공
    4: 80,   # 4강 - 80% 성공
    5: 80,   # 5강 - 80% 성공
    6: 70,   # 6강 - 70% 성공
    7: 60,   # 7강 - 60% 성공
    8: 60,   # 8강 - 60% 성공
    9: 40,   # 9강 - 40% 성공
    10: 40,  # 10강 - 40% 성공
    11: 30,  # 11강 - 30% 성공
    12: 20,  # 12강 - 20% 성공
    13: 20,  # 13강 - 20% 성공
    14: 10,  # 14강 - 10% 성공
    15: 10,  # 15강 - 10% 성공
    16: 5,  # 16강 - 5% 성공
    17: 5,  # 17강 - 5% 성공
    18: 3,  # 18강 - 3% 성공
    19: 1,   # 19강 - 1% 성공
}

class NotFoundError(Exception):
    pass

class TooManyRequestError(Exception):
    pass

class ResultButton(discord.ui.View):
    weapon_main_unwanted = {
        "스태프-신성": (["스킬 강화", "명중 강화"], ["공격 강화", "치명타 확률 강화", "치명타 대미지 강화"]),
        "스태프-화염": (["스킬 강화", "명중 강화"], ["공격 강화", "치명타 확률 강화", "치명타 대미지 강화"]),
        "스태프-냉기": (["스킬 강화", "명중 강화"], ["공격 강화", "치명타 확률 강화", "치명타 대미지 강화"]),
        "태도":       (["명중 강화", "속도 강화", "치명타 대미지 강화", "치명타 확률 강화"], ["스킬 강화"]),
        "단검":       (["공격 강화", "속도 강화", "치명타 대미지 강화", "치명타 확률 강화"], ["스킬 강화"]),
        "대검":       (["공격 강화", "속도 강화", "치명타 대미지 강화"], ["스킬 강화", "치명타 확률 강화"]),
        "창":         (["공격 강화", "명중 강화", "치명타 대미지 강화", "치명타 확률 강화"], ["스킬 강화"]),
        "활":         (["속도 강화", "공격 강화", "치명타 대미지 강화", "치명타 확률 강화"], ["스킬 강화"]),
        "조총":       (["스킬 강화", "속도 강화", "치명타 대미지 강화", "치명타 확률 강화"], []),
        "낫":         (["스킬 강화", "속도 강화"], ["치명타 확률 강화", "치명타 대미지 강화"]),
    }

    def __init__(self, user: discord.User, wdc: dict, wdo: dict, skill_data: dict):
        super().__init__(timeout=None)
        self.user = user
        self.wdc = wdc            # 원본 무기 데이터 (강화 전)
        self.wdo = wdo            # 강화 후 무기 데이터
        self.skill_data = skill_data
        self.reroll_count = 0     # 재구성 시도 횟수
        self.win_count = 0        # 시뮬레이션 승리 횟수
        self.message = None       # 나중에 메세지 저장

    def scale_weights_with_main_and_unwanted(self, stats_list, win_count, max_win=10):
        """
        승수에 따라 주요 스탯은 곡선 형태로 가중치 증가, 미사용 스탯은 곡선 형태로 감소
        stats_list: 강화내역의 스탯 리스트
        win_count: 현재 승수 (0~max_win)
        """
        main_stats, unwanted_stats = self.weapon_main_unwanted.get(self.wdc.get("무기타입", ""), ([], []))
        
        linear_ratio = min(win_count / max_win, 1)
        curved_ratio = linear_ratio ** 1.5  # 곡선 적용 (1보다 크면 느리게 시작 → 빠르게 증가)
        
        weights = {}

        for stat in stats_list:
            if stat in main_stats:
                # 주요 스탯: 기본 1에서 최대 10까지 부드럽게 증가
                weights[stat] = 1 + 9 * curved_ratio
            elif stat in unwanted_stats:
                # 미사용 스탯: 1에서 0까지 곡선 형태로 감소
                weights[stat] = max(1 - curved_ratio, 0)
            else:
                # 기타 스탯: 1에서 0.5까지 곡선 형태로 감소
                weights[stat] = 1 - 0.5 * curved_ratio

        return weights

    def weighted_redistribute(self, total_points, weights):
        """
        가중치 비율에 따라 total_points를 분배
        """
        assigned = {k: 0 for k in weights.keys()}
        weight_sum = sum(weights.values())

        for _ in range(total_points):
            r = random.uniform(0, weight_sum)
            upto = 0
            for stat, w in weights.items():
                if upto + w >= r:
                    assigned[stat] += 1
                    break
                upto += w
        return assigned

    async def do_reroll(self):
        total_enhancement = sum(self.wdc.get("강화내역", {}).values())

        ref_weapon_enhance = db.reference(f"무기/강화")
        enhance_types_dict = ref_weapon_enhance.get() or {}
        enhance_types = list(enhance_types_dict.keys())  # dict_keys -> list 변환

        all_stats = enhance_types

        # 승수 기반으로 가중치 계산
        scaled_weights = self.scale_weights_with_main_and_unwanted(all_stats, self.win_count)

        # 강화 점수 재분배
        random_log = self.weighted_redistribute(total_enhancement, scaled_weights)

        self.wdo = self.wdc.copy()
        self.wdo["강화내역"] = random_log

        max_enhance_type = max(random_log, key=random_log.get)
        prefix = max_enhance_type.split()[0] + "형"
        self.wdo["이름"] = f"{self.wdc['이름']}-{prefix}"

        # 외부 함수 호출 (db는 외부에서 임포트 되어 있어야 함)
        enhancement_options = db.reference("무기/강화").get() or {}
        base_weapon_stats = db.reference("무기/기본 스탯").get() or {}
        self.wdo = apply_stat_to_weapon_data(self.wdo, enhancement_options, base_weapon_stats)

    @discord.ui.button(label="⚔️ 결과 확인", style=discord.ButtonStyle.primary)
    async def show_result(self, interaction: Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("이 버튼은 당신이 사용할 수 없습니다.", ephemeral=True)
            return
        
        await interaction.response.defer()
        win_count = 0

        # 1000회 시뮬레이션 (비동기 Battle 함수 사용)
        for _ in range(1000):
            result = await Battle(
                channel=interaction.channel,
                challenger_m=self.user,
                opponent_m="",
                raid=False,
                practice=False,
                simulate=True,
                skill_data=self.skill_data,
                wdc=self.wdc,
                wdo=self.wdo,
                scd=self.skill_data
            )
            if result:
                win_count += 1

        
        win_rate = win_count / 1000 * 100
        outcome = f"🏆 **승리!**[{self.win_count + 1}승!]" if win_rate >= 50 else "❌ **패배!**"

        embed = discord.Embed(title="시뮬레이션 결과", color=discord.Color.gold())
        embed.add_field(
            name=f"{self.wdc['이름']} vs {self.wdo['이름']}",
            value=(
                f"{self.wdc['이름']} {win_count}승\n"
                f"{self.wdo['이름']} {1000 - win_count}승\n\n"
                f"**승률**: {win_rate:.1f}%\n"
                f"{outcome}"
            )
        )

        # 자동 재구성
        if win_rate >= 50:
            await self.do_reroll()
            self.win_count += 1
            if self.message:
                await self.message.edit(
                    embeds=[get_stat_embed(self.wdc, self.wdo), get_enhance_embed(self.wdc, self.wdo)],
                    view=self
                )
        else:
            # 모든 버튼 비활성화
            for child in self.children:
                child.disabled = True
            if self.message:
                await self.message.edit(view=self)

            # 최종 결과 Embed (패배 시)
            final_embed = discord.Embed(title="📉 최종 결과", color=discord.Color.red())
            final_embed.add_field(
                name="최종 승수",
                value=f"🏁 **[{self.win_count}승/10승]**",
                inline=False
            )
            final_embed.add_field(
                name=f"{self.wdc['이름']} vs {self.wdo['이름']}",
                value=(
                    f"{self.wdc['이름']} {win_count}승\n"
                    f"{self.wdo['이름']} {1000 - win_count}승\n\n"
                    f"**승률**: {win_rate:.1f}%\n"
                    f"{outcome}"
                )
            )
            await interaction.followup.send(embed=final_embed)
            return

        await interaction.followup.send(embed=embed)

    @discord.ui.button(label="🔁 재구성 (10회 가능)", style=discord.ButtonStyle.secondary)
    async def reroll_opponent(self, interaction: Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("이 버튼은 당신이 사용할 수 없습니다.", ephemeral=True)
            return
        
        await interaction.response.defer()

        if self.reroll_count >= 10:
            await interaction.followup.send("재구성은 최대 10회까지만 가능합니다.", ephemeral=True)
            return

        await self.do_reroll()
        self.reroll_count += 1
        button.label = f"🔁 재구성 ({10 - self.reroll_count}/10 남음)"
        if self.message:
            await self.message.edit(
                embeds=[get_stat_embed(self.wdc, self.wdo), get_enhance_embed(self.wdc, self.wdo)],
                view=self
            )



def redistribute_enhancements(total_points, template):
    assigned = {key: int(total_points * template[key]) for key in template}
    remain = total_points - sum(assigned.values())
    keys = list(template.keys())
    for _ in range(remain):
        selected = random.choice(keys)
        assigned[selected] += 1
    return assigned


def apply_stat_to_weapon_data(weapon_data: dict, enhancement_options: dict, base_weapon_stats: dict) -> dict:
    updated_data = copy.deepcopy(weapon_data)
    enhance_log_data = updated_data.get("강화내역", {})
    inherit_log_data = updated_data.get("계승 내역", {})
    weapon_type = updated_data.get("무기타입", "")

    inherit_level = inherit_log_data.get("기본 스탯 증가", 0)
    inherit_multiplier = inherit_level * 0.3

    if weapon_type not in base_weapon_stats:
        return updated_data

    inherit_stats = ["공격력", "스킬 증폭", "내구도", "방어력", "스피드", "명중"]
    new_stats = {
        stat: value + round(value * inherit_multiplier) if stat in inherit_stats else value
        for stat, value in base_weapon_stats[weapon_type].items()
        if stat not in ["강화", "스킬"]
    }

    for enhance_type, enhance_count in enhance_log_data.items():
        if enhance_type in enhancement_options:
            for stat, value in enhancement_options[enhance_type]["stats"].items():
                new_stats[stat] = round(new_stats.get(stat, 0) + value * enhance_count, 3)

    basic_skill_levelup = inherit_log_data.get("기본 스킬 레벨 증가", 0)
    basic_skills = ["속사", "기습", "강타", "헤드샷", "창격", "수확", "명상", "화염 마법", "냉기 마법", "신성 마법", "일섬"]
    skills = base_weapon_stats[weapon_type].get("스킬", {})
    updated_skills = {}
    for skill_name in skills:
        updated_skills[skill_name] = copy.deepcopy(skills[skill_name])
        if skill_name in basic_skills:
            updated_skills[skill_name]["레벨"] = basic_skill_levelup + 1

    for key, val in new_stats.items():
        updated_data[key] = val
    updated_data["스킬"] = updated_skills
    return updated_data


def get_stat_embed(challenger: dict, opponent: dict) -> discord.Embed:
    embed = discord.Embed(title="📊 스탯 비교", color=discord.Color.orange())

    stat_name_map = {
        "공격력": "공격",
        "스킬 증폭": "스증",
        "방어력": "방어",
        "스피드": "속도",
        "명중": "명중",
        "치명타 확률": "치확",
        "치명타 대미지": "치댐",
        "내구도": "내구"
    }

    stat_keys = [
        "공격력", "스킬 증폭", "방어력", "스피드",
        "명중", "치명타 확률", "치명타 대미지", "내구도"
    ]

    lines = []

    for key in stat_keys:
        c_val = challenger.get(key, 0)
        o_val = opponent.get(key, 0)

        # 퍼센트 처리
        is_percent = key in ["치명타 확률", "치명타 대미지"]
        c_val_display = f"{round(c_val * 100)}%" if is_percent else str(c_val)
        o_val_display = f"{round(o_val * 100)}%" if is_percent else str(o_val)
        diff_val = round((o_val - c_val) * 100) if is_percent else o_val - c_val

        emoji = "🟢" if diff_val > 0 else "🔴"
        sign = "+" if diff_val > 0 else "-"
        diff_display = f"{sign}{abs(diff_val)}{'%' if is_percent else ''}"

        label = stat_name_map.get(key, key)
        lines.append(f"{label}: {c_val_display} ⟷ {o_val_display} (**{diff_display}** {emoji})")

    if not lines:
        embed.add_field(name="변경된 스탯 없음", value="모든 스탯이 동일합니다.", inline=False)
    else:
        embed.add_field(name="스탯 차이", value="\n".join(lines), inline=False)

    return embed


def get_enhance_embed(challenger: dict, opponent: dict) -> discord.Embed:
    embed = discord.Embed(title="📈 강화 내역 비교", color=discord.Color.orange())
    ch_log = challenger.get("강화내역", {})
    op_log = opponent.get("강화내역", {})
    all_keys = sorted(set(ch_log.keys()) | set(op_log.keys()))

    enhance_name_map = {
        "공격 강화": "공격",
        "방어 강화": "방어",
        "속도 강화": "속도",
        "치명타 확률 강화": "치확",
        "치명타 대미지 강화": "치댐",
        "밸런스 강화": "균형",
        "스킬 강화": "스증",
        "명중 강화": "명중",
        "내구도 강화": "내구"
    }

    lines = []

    for k in all_keys:
        ch_val = ch_log.get(k, 0)
        op_val = op_log.get(k, 0)
        diff = op_val - ch_val

        emoji = "🟢" if diff > 0 else "🔴"
        sign = "+" if diff > 0 else "-"
        diff_display = f"{sign}{abs(diff)}회"

        label = enhance_name_map.get(k, k)
        lines.append(f"{label}: {ch_val}회 ⟷ {op_val}회 (**{diff_display}** {emoji})")

    if not lines:
        embed.add_field(name="변경된 강화 내역 없음", value="모든 강화 내역이 동일합니다.", inline=False)
    else:
        embed.add_field(name="강화 차이", value="\n".join(lines), inline=False)

    return embed

def calculate_bonus_rate(streak):
    bonus = 0
    
    if streak >= 1:
        bonus += min(2, streak) * 0.1  # 1~2연승 보너스
    if streak >= 3:
        bonus += min(2, streak - 2) * 0.2  # 3~4연승 보너스
    if streak >= 5:
        bonus += min(5, streak - 4) * 0.3  # 5~9연승 보너스
    if streak >= 10:
        bonus += (streak - 9) * 0.4  # 10연승 이상부터 0.4배씩 추가
    
    return round(bonus,1)

def restart_script(): # 봇 재시작 명령어
    try:
        # restart_bot.py 실행
        subprocess.run(["python3", "/home/xoehfdl8182/restart_bot.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing restart_bot.py: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

def apply_stat_change(nickname: str):
    ref_weapon = db.reference(f"무기/유저/{nickname}")
    weapon_data = ref_weapon.get() or {}
    if not weapon_data:
        return None, None

    weapon_name = weapon_data.get("이름", "")
    weapon_type = weapon_data.get("무기타입", "")

    ref_enhance_log = db.reference(f"무기/유저/{nickname}/강화내역")
    enhance_log_data = ref_enhance_log.get() or {}

    ref_inherit_log = db.reference(f"무기/유저/{nickname}/계승 내역")
    inherit_log_data = ref_inherit_log.get() or {}

    # 계승 내역 적용 (기본 스탯 증가)
    inherit_level = inherit_log_data.get("기본 스탯 증가", 0)
    inherit_multiplier = inherit_level * 0.3

    # 기존 스탯
    old_stats = {
        "공격력": weapon_data.get("공격력", 10),
        "스킬 증폭": weapon_data.get("스킬 증폭", 5),
        "내구도": weapon_data.get("내구도", 500),
        "방어력": weapon_data.get("방어력", 5),
        "스피드": weapon_data.get("스피드", 5),
        "명중": weapon_data.get("명중", 0),
        "치명타 대미지": weapon_data.get("치명타 대미지", 1.5),
        "치명타 확률": weapon_data.get("치명타 확률", 0.05)
    }

    ref_weapon_base = db.reference(f"무기/기본 스탯")
    base_weapon_stats = ref_weapon_base.get() or {}

    if weapon_type not in base_weapon_stats:
        return weapon_name, []  # 무기 타입이 등록되지 않은 경우

    inherit_stats = ["공격력", "스킬 증폭", "내구도", "방어력", "스피드", "명중"]

    # 기본 스탯 + 계승 보정 적용
    new_stats = {
        stat: value + round(value * inherit_multiplier) if stat in inherit_stats else value
        for stat, value in base_weapon_stats[weapon_type].items()
        if stat not in ["강화", "스킬"]
    }

    # 강화 보정 적용
    ref_weapon_enhance = db.reference(f"무기/강화")
    enhancement_options = ref_weapon_enhance.get() or {}
    for enhance_type, enhance_count in enhance_log_data.items():
        if enhance_type in enhancement_options:
            for stat, value in enhancement_options[enhance_type]["stats"].items():
                new_stats[stat] += value * enhance_count
                new_stats[stat] = round(new_stats[stat], 3)

    basic_skill_levelup = inherit_log_data.get("기본 스킬 레벨 증가", 0)
        
    basic_skills = ["속사", "기습", "강타", "헤드샷", "창격", "수확", "명상", "화염 마법", "냉기 마법", "신성 마법", "일섬"]
    base_weapon_stat = base_weapon_stats[weapon_type]
    skills = base_weapon_stat["스킬"]
    for skill_name in basic_skills:
        if skill_name in skills:
            skills[skill_name]["레벨"] = basic_skill_levelup + 1

    new_stats["스킬"] = skills
    # 변경사항 비교
    stat_changes = []
    for stat in old_stats:
        if stat in new_stats:
            if stat in ["치명타 확률", "치명타 대미지"]:
                diff = round((new_stats[stat] - old_stats[stat]) * 100)
                if diff > 0:
                    stat_changes.append(f"🟢 **{stat}**: +{diff}%")
                elif diff < 0:
                    stat_changes.append(f"🔴 **{stat}**: {diff}%")
            else:
                diff = new_stats[stat] - old_stats[stat]
                if diff > 0:
                    stat_changes.append(f"🟢 **{stat}**: +{diff}")
                elif diff < 0:
                    stat_changes.append(f"🔴 **{stat}**: {diff}")

    # 실제 업데이트 적용
    ref_weapon.update(new_stats)
    return weapon_name, stat_changes

def generate_tower_weapon(floor: int):
    weapon_types = ["대검","스태프-화염", "조총", "스태프-냉기", "창", "활", "스태프-신성", "단검", "낫"]
    weapon_type = weapon_types[(floor - 1) % len(weapon_types)]  # 1층부터 시작
    enhancement_level = floor

    ref_weapon_base = db.reference(f"무기/기본 스탯")
    base_weapon_stats = ref_weapon_base.get() or {}

    # 기본 스탯
    base_stats = base_weapon_stats[weapon_type]

    skill_weapons = ["스태프-화염", "스태프-냉기", "스태프-신성"]
    attack_weapons = ["대검", "창", "활", "단검"]
    hybrid_weapons = ["낫", "조총"]

    # 강화 단계만큼 일괄 증가
    weapon_data = base_stats.copy()
    weapon_data["이름"] = f"{weapon_type} +{enhancement_level}"
    weapon_data["무기타입"] = weapon_type
    if weapon_type in skill_weapons:
        weapon_data["스킬 증폭"] += enhancement_level * 5
    elif weapon_type in attack_weapons:
        weapon_data["공격력"] += enhancement_level * 2
    elif weapon_type in hybrid_weapons:
        weapon_data["스킬 증폭"] += enhancement_level * 3
        weapon_data["공격력"] += enhancement_level * 1
    weapon_data["내구도"] += enhancement_level * 15
    weapon_data["방어력"] += enhancement_level * 2
    weapon_data["스피드"] += enhancement_level * 2
    weapon_data["명중"] += enhancement_level * 3
    weapon_data["강화"] = enhancement_level
    for skill_data in  weapon_data["스킬"].values():
        skill_data["레벨"] = enhancement_level // 10 + 1    

    return weapon_data

class ExcludeStatSelect(discord.ui.Select):
    def __init__(self, stat_options, callback):
        options = [discord.SelectOption(label=stat) for stat in stat_options]
        super().__init__(placeholder="제외할 스탯 2개까지 선택", min_values=0, max_values=2, options=options)
        self.callback_func = callback

    async def callback(self, interaction: discord.Interaction):
        await self.callback_func(interaction, self.values)

class ExcludeStatView(discord.ui.View):
    def __init__(self, stat_options, callback):
        super().__init__(timeout=60)
        self.add_item(ExcludeStatSelect(stat_options, callback))



class RuneUseButton(discord.ui.View):
    class ConvertToRegressionRuneButton(discord.ui.Button):
        def __init__(self):
            super().__init__(label="회귀의 룬으로 변환 (50개 소모)", style=discord.ButtonStyle.secondary)

        async def callback(self, interaction: discord.Interaction):
            view: RuneUseButton = self.view  # type: ignore
            if interaction.user.id != view.user.id:
                await interaction.response.send_message("이 버튼은 당신의 것이 아닙니다.", ephemeral=True)
                return

            if view.item_data.get("운명 왜곡의 룬", 0) < 50:
                await interaction.response.send_message("운명 왜곡의 룬이 부족합니다. (50개 필요)", ephemeral=True)
                return

            await interaction.response.defer()
            # 50개 소모
            view.item_data["운명 왜곡의 룬"] -= 50
            # 회귀의 룬 1개 지급
            view.item_data["회귀의 룬"] = view.item_data.get("회귀의 룬", 0) + 1
            view.item_ref.update(view.item_data)

            # 버튼 제거 (view.children에서 모두 삭제)
            view.clear_items()

            await interaction.edit_original_response(
                embed=discord.Embed(
                    title="🔁 룬 변환 완료",
                    description="운명 왜곡의 룬 50개를 소모하여 **회귀의 룬 1개**를 획득했습니다!",
                    color=discord.Color.blurple()
                ),
                view=view
            )

    def __init__(self, user: discord.User, rune_name: str, nickname: str, item_ref, item_data):
        super().__init__(timeout=60)
        self.user = user
        self.rune_name = rune_name
        self.nickname = nickname
        self.item_ref = item_ref
        self.item_data = item_data
        
        # 운명 왜곡의 룬이 50개 이상이면 회귀의 룬으로 변환 버튼 추가
        if self.rune_name == "운명 왜곡의 룬" and self.item_data.get("운명 왜곡의 룬", 0) >= 50:
            self.add_item(self.ConvertToRegressionRuneButton())

    @discord.ui.button(label="룬 발동", style=discord.ButtonStyle.primary)
    async def activate_rune(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("이 버튼은 당신의 것이 아닙니다.", ephemeral=True)
            return

        if self.item_data.get(self.rune_name, 0) <= 0:
            await interaction.response.send_message("해당 룬을 더 이상 보유하고 있지 않습니다.", ephemeral=True)
            return

        for child in self.children:
            child.disabled = True
        await interaction.response.defer()
        
        embed = discord.Embed(color=discord.Color.green())

        if self.rune_name == "스킬 각성의 룬":
            embed.title = "스킬 각성의 룬 발동!"
            # 여기에 실제 능력치 전환 로직 구현
            ref_inherit_log = db.reference(f"무기/유저/{self.nickname}/계승 내역")
            inherit_log = ref_inherit_log.get() or {}
            base_stat_increase = inherit_log.get("기본 스탯 증가", 0)
            base_skill_level_increase = inherit_log.get("기본 스킬 레벨 증가", 0)

            ref_inherit_log.update({"기본 스탯 증가": base_stat_increase - 2})
            ref_inherit_log.update({"기본 스킬 레벨 증가": base_skill_level_increase + 1})
            
            weapon_name, stat_changes = apply_stat_change(self.nickname)
            embed.description = f"{weapon_name}의 **기본 스탯 증가 2**가 **기본 스킬 레벨 증가 1**로 전환되었습니다!"
            if weapon_name and stat_changes:
                embed.add_field(
                    name=f"🛠️ {weapon_name}의 변경된 스탯",
                    value="\n".join(stat_changes),
                    inline=False
                )
                embed.add_field(
                    name=f"🛠️ 스킬 레벨",
                    value=f"**Lv.{base_skill_level_increase + 1} → Lv.{base_skill_level_increase + 2}**",
                    inline=False
                )

        elif self.rune_name == "운명 왜곡의 룬":
            embed.title = "운명 왜곡의 룬 발동!"
            # 여기에 계승 스탯 무작위 재배치 로직 구현
            # 기존의 추가강화 수치
            ref_inherit_log = db.reference(f"무기/유저/{self.nickname}/계승 내역")
            inherit_log = ref_inherit_log.get() or {}
            additional_enhance = inherit_log.get("추가강화", {})

            ref_additional_enhance = db.reference(f"무기/유저/{self.nickname}/계승 내역/추가강화")

            ref_enhance_list = db.reference(f"무기/강화")
            enhance_list = ref_enhance_list.get() or {}

            # 새로 재배치할 수치
            enhance_keys = list(enhance_list.keys())  # 강화 키들
            enhance_count = sum(additional_enhance.values())  # 추가강화 총합

            # 새로 재배치된 수치
            new_enhance = {key: 0 for key in enhance_keys}
            for _ in range(enhance_count):
                selected = random.choice(enhance_keys)
                new_enhance[selected] += 1

            # 기존 강화 내역에서 수치 제외
            ref_weapon_enhance = db.reference(f"무기/유저/{self.nickname}/강화내역")
            enhance_data = ref_weapon_enhance.get() or {}

            # 기존 수치에서 새로 배정된 수치만큼 빼기
            for key, old_value in additional_enhance.items():
                if key in enhance_data:
                    enhance_data[key] -= old_value  # 기존 강화 내역에서 해당 수치 빼기

            # 새로운 추가강화 수치를 적용
            for key, new_value in new_enhance.items():
                if key in enhance_data:
                    enhance_data[key] += new_value  # 새로 재배치된 수치만큼 증가
                else:
                    enhance_data[key] = new_value

            additional_keys = list(additional_enhance.keys())

            for key in additional_keys:
                if enhance_data[key] == 0:  # 수치가 0이면 해당 키 삭제
                    del enhance_data[key]

            # 새롭게 수정된 강화 내역 저장
            ref_weapon_enhance.set(enhance_data)
            ref_additional_enhance.set(new_enhance)
            # 결과 비교 및 임베드 생성
            embed = discord.Embed(
                title="🔄 계승 스탯 무작위 재배치 결과",
                description=f"{interaction.user.display_name}님의 추가 강화 수치가 무작위로 재배치되었습니다.",
                color=discord.Color.gold()
            )

            for key in enhance_keys:
                old_val = additional_enhance.get(key, 0)
                new_val = new_enhance.get(key, 0)
                emoji = "⬆️" if new_val > old_val else "⬇️" if new_val < old_val else "➡️"
                embed.add_field(
                    name=key,
                    value=f"{emoji} {old_val} → {new_val}",
                    inline=True
                )

            weapon_name, stat_changes = apply_stat_change(self.nickname)
            if weapon_name and stat_changes:
                embed.add_field(
                    name=f"🛠️ {weapon_name}의 변경된 스탯",
                    value="\n".join(stat_changes),
                    inline=False
                )

        elif self.rune_name == "운명의 룬":
            ref_enhance_list = db.reference(f"무기/강화")
            enhance_list = ref_enhance_list.get() or {}
            stat_options = list(enhance_list.keys())

            async def on_stat_selected(stat_interaction, excluded_stats):
                if stat_interaction.user.id != self.user.id:
                    await stat_interaction.response.send_message("이 선택은 당신의 것이 아닙니다.", ephemeral=True)
                    return

                # 기존 코드 안에서 excluded_stats를 활용
                ref_inherit_log = db.reference(f"무기/유저/{self.nickname}/계승 내역")
                inherit_log = ref_inherit_log.get() or {}
                additional_enhance = inherit_log.get("추가강화", {})

                ref_additional_enhance = db.reference(f"무기/유저/{self.nickname}/계승 내역/추가강화")

                enhance_keys = [k for k in stat_options if k not in excluded_stats]
                enhance_count = sum(additional_enhance.values())

                new_enhance = {key: 0 for key in enhance_keys}
                for _ in range(enhance_count):
                    selected = random.choice(enhance_keys)
                    new_enhance[selected] += 1

                ref_weapon_enhance = db.reference(f"무기/유저/{self.nickname}/강화내역")
                enhance_data = ref_weapon_enhance.get() or {}

                for key, old_value in additional_enhance.items():
                    if key in enhance_data:
                        enhance_data[key] -= old_value

                for key, new_value in new_enhance.items():
                    if key in enhance_data:
                        enhance_data[key] += new_value
                    else:
                        enhance_data[key] = new_value

                for key in list(additional_enhance.keys()):
                    if enhance_data.get(key) == 0:
                        del enhance_data[key]

                ref_weapon_enhance.set(enhance_data)
                ref_additional_enhance.set(new_enhance)

                embed = discord.Embed(
                    title="🔄 계승 스탯 무작위 재배치 결과",
                    description=f"{interaction.user.display_name}님의 추가 강화 수치가 재배치되었습니다.\n(제외: {', '.join(excluded_stats)})",
                    color=discord.Color.gold()
                )
                for key in stat_options:
                    old_val = additional_enhance.get(key, 0)
                    new_val = new_enhance.get(key, 0)
                    emoji = "⬆️" if new_val > old_val else "⬇️" if new_val < old_val else "➡️"
                    embed.add_field(name=key, value=f"{emoji} {old_val} → {new_val}", inline=True)

                weapon_name, stat_changes = apply_stat_change(self.nickname)
                if weapon_name and stat_changes:
                    embed.add_field(
                        name=f"🛠️ {weapon_name}의 변경된 스탯",
                        value="\n".join(stat_changes),
                        inline=False
                    )

        elif self.rune_name == "회귀의 룬":
            embed.title = "회귀의 룬 발동!"

            # 기존의 추가강화 수치
            ref_inherit_log = db.reference(f"무기/유저/{self.nickname}/계승 내역")
            inherit_log = ref_inherit_log.get() or {}
            additional_enhance = inherit_log.get("추가강화", {})

            ref_additional_enhance = db.reference(f"무기/유저/{self.nickname}/계승 내역/추가강화")
            ref_weapon_enhance = db.reference(f"무기/유저/{self.nickname}/강화내역")
            enhance_data = ref_weapon_enhance.get() or {}

            # 총 수치 계산 및 제거
            enhance_removed = 0
            for key, value in additional_enhance.items():
                enhance_removed += value
                if key in enhance_data:
                    enhance_data[key] -= value
                    if enhance_data[key] <= 0:
                        del enhance_data[key]

            # 강화내역 갱신 및 추가강화 초기화
            ref_weapon_enhance.set(enhance_data)
            ref_additional_enhance.set({})  # 추가 강화 초기화

            # 특수 연마제 지급
            ref_refine_stone = db.reference(f"무기/유저/{self.nickname}/특수연마제")
            current_refine = ref_refine_stone.get() or 0
            ref_refine_stone.set(current_refine + enhance_removed)

            # 임베드 메시지
            embed = discord.Embed(
                title="🔮 회귀의 룬이 사용되었습니다!",
                description=(
                    f"{interaction.user.display_name}님의 추가 강화 수치가 모두 제거되었으며,\n"
                    f"해당 수치 {enhance_removed}만큼의 **특수 연마제**가 연성되었습니다."
                ),
                color=discord.Color.purple()
            )

            if enhance_removed == 0:
                embed.set_footer(text="※ 회귀의 룬 사용 시 회수할 강화 수치가 없어 아무 일도 일어나지 않았습니다.")
            else:
                embed.add_field(
                    name="💠 연성된 특수 연마제",
                    value=f"총 {enhance_removed} 개",
                    inline=False
                )
                give_item(self.nickname,"특수 연마제",enhance_removed)

            weapon_name, stat_changes = apply_stat_change(self.nickname)
            if weapon_name and stat_changes:
                embed.add_field(
                    name=f"🛠️ {weapon_name}의 변경된 스탯",
                    value="\n".join(stat_changes),
                    inline=False
                )
        # 룬 1개 소모 처리
        self.item_data[self.rune_name] -= 1
        self.item_ref.update(self.item_data)

        await interaction.edit_original_response(embed=embed, view=None)

async def Battle(channel, challenger_m, opponent_m = None, boss = None, raid = False, practice = False, tower = False, tower_floor = 1, raid_ended = False, simulate = False, skill_data = None, wdc = None, wdo = None, scd = None):
        # 전장 크기 (-10 ~ 10), 0은 없음
        MAX_DISTANCE = 10
        MIN_DISTANCE = -10

        battle_distance = 1

        weapon_battle_thread = None
        if simulate:
            skill_data_firebase = skill_data
        else:
            ref_skill_data = db.reference("무기/스킬")
            skill_data_firebase = ref_skill_data.get() or {}

        # 방어력 기반 피해 감소율 계산 함수
        def calculate_damage_reduction(defense):
            return min(0.99, 1 - (100 / (100 + defense)))  # 방어력 공식 적용

        def calculate_accuracy(accuracy):
            return min(0.99, 1 - (50 / (50 + accuracy))) # 명중률 공식 적용

        def calculate_evasion(distance):
            return (distance - 1) * 0.1
        
        def calculate_move_chance(speed):
            return min(0.99, 1 - math.exp(-speed / 70))

        def apply_status_for_turn(character, status_name, duration=1, value=None):
            """
            상태를 적용하고 지속 시간을 관리합니다.
            출혈, 화상 상태는 duration이 누적되며,
            다른 상태는 기존보다 길 경우에만 갱신합니다.
            value는 기존보다 높을 때만 갱신합니다.
            """
            if status_name not in character["Status"]:
                character["Status"][status_name] = {"duration": duration}
                if value is not None:
                    character["Status"][status_name]["value"] = value
            else:
                # 출혈은 지속시간을 누적
                if status_name == "출혈" or status_name == "화상":
                    character["Status"][status_name]["duration"] += duration
                else:
                    # 출혈 외 상태는 기존보다 길 경우만 갱신
                    if duration >= character["Status"][status_name]["duration"]:
                        character["Status"][status_name]["duration"] = duration

                # value 갱신: 기존보다 높을 때만
                if value is not None:
                    current_value = character["Status"][status_name].get("value", None)
                    if current_value is None or value > current_value:
                        character["Status"][status_name]["value"] = value

        def update_status(character):
            """
            각 턴마다 상태의 지속 시간을 감소시켜서, 0이 되면 상태를 제거합니다.
            """
            for status, data in list(character["Status"].items()):
                # 지속 시간이 남아 있으면 1턴씩 감소
                character["Status"][status]["duration"] -= 1
                if data["duration"] <= 0:
                    del character["Status"][status]

        def remove_status_effects(character):
            """
            상태가 사라졌을 때 효과를 되돌리는 함수
            """
            
            # 기본값으로 초기화
            character["Evasion"] = 0
            character["CritDamage"] = character["BaseCritDamage"]
            character["CritChance"] = character["BaseCritChance"]
            character["Attack"] = character["BaseAttack"]
            character["Accuracy"] = character["BaseAccuracy"]
            character["Speed"] = character["BaseSpeed"]
            character["DamageEnhance"] = 0
            character["DefenseIgnore"] = 0
            character["HealBan"] = 0
            character["DamageReduction"] = 0

            # 현재 적용 중인 상태 효과를 확인하고 반영
            if "기습" in character["Status"]:
                skill_level = character["Skills"]["기습"]["레벨"]
                invisibility_data = skill_data_firebase['기습']['values']
                DefenseIgnore_increase = invisibility_data['은신공격_레벨당_방관_증가'] * skill_level
                character["DefenseIgnore"] += DefenseIgnore_increase
                skill_level = character["Skills"]["기습"]["레벨"]

                # 피해 증가
                character["DamageEnhance"] += invisibility_data['은신공격_레벨당_피해_배율'] * skill_level

            if "은신" in character["Status"]:
                character["Evasion"] = 1 # 회피율 증가

            if "고속충전_속도증가" in character["Status"]:
                skill_level = character["Skills"]["고속충전"]["레벨"]
                supercharger_data = skill_data_firebase['고속충전']['values']
                base_speedup = supercharger_data['속도증가_기본수치']
                speedup_level = supercharger_data['속도증가_레벨당']
                speedup_value = base_speedup + speedup_level * skill_level
                character["Speed"] += speedup_value

            if "둔화" in character["Status"]:
                slow_amount = character['Status']['둔화']['value']
                if slow_amount > 1:
                    slow_amount = 1
                character["Speed"] *= (1 - slow_amount)
                character["Speed"] = int(character["Speed"])

            if "차징샷" in character["Status"]:
                skill_level = character["Skills"]["차징샷"]["레벨"]
                charging_shot_data = skill_data_firebase['차징샷']['values']

                attack_increase_level = charging_shot_data['적정거리_공격력증가']
                accuracy_increase_level = charging_shot_data['적정거리_명중증가']
                attack_increase = (attack_increase_level * skill_level)
                accuracy_increase = (accuracy_increase_level * skill_level)
                character["Attack"] += attack_increase
                character["Accuracy"] += accuracy_increase

            if "피해 감소" in character["Status"]:
                reduce_amount = character['Status']['피해 감소']['value']
                if reduce_amount > 1:
                    reduce_amount = 1
                character["DamageReduction"] = reduce_amount


        async def end(attacker, defender, winner, raid, simulate = False, winner_id = None):
            if simulate:
                if raid:
                    if winner == "attacker" and defender['Id'] == 0:
                        return first_HP - attacker['HP']
                    elif winner == "defender" and attacker['Id'] == 0:
                        return first_HP - defender['HP']
                    else:
                        return first_HP  # 보스가 0이 되면 끝났다는 뜻
                else:
                    return winner_id == challenger['Id']  # 일반전투일 경우 승리 여부만 반환
            await weapon_battle_thread.send(embed = battle_embed)

            if raid: #레이드 상황
                if not practice:
                    ref_raid = db.reference(f"레이드/내역/{challenger_m.name}")
                    ref_raid.update({"레이드여부": True})
                    ref_raid.update({"보스": boss})
                    ref_raid.update({"모의전": False})

                if practice and raid_ended: # 레이드 끝난 이후 도전한 경우
                    ref_raid = db.reference(f"레이드/내역/{challenger_m.name}")
                    ref_raid.update({"레이드여부": True})
                    ref_raid.update({"보스": boss})
                    ref_raid.update({"모의전": True})

                ref_boss = db.reference(f"레이드/보스/{boss}")
                if winner == "attacker": # 일반적인 상황
                    if defender['Id'] == 0: # 패배한 사람이 플레이어일 경우
                        final_HP = attacker['HP']
                        if not practice:
                            ref_boss.update({"내구도" : final_HP})
                        total_damage = first_HP - final_HP
                        await weapon_battle_thread.send(f"**레이드 종료!** 총 대미지 : {total_damage}")
                    else: # 플레이어가 승리한 경우
                        final_HP = defender['HP']
                        if final_HP < 0:
                            final_HP == 0
                        total_damage = first_HP - final_HP
                        if not practice:
                            ref_boss.update({"내구도" : final_HP})
                            ref_raid.update({"막타": True})
                        await weapon_battle_thread.send(f"**토벌 완료!** 총 대미지 : {total_damage}")
                        
                elif winner == "defender": # 출혈 등특수한 상황
                    if attacker['Id'] == 0: # 패배한 사람이 플레이어일 경우
                        final_HP = defender['HP']
                        if not practice:
                            ref_boss.update({"내구도" : final_HP})
                        total_damage = first_HP - final_HP
                        await weapon_battle_thread.send(f"**레이드 종료!** 총 대미지 : {total_damage}")
                    else: # 플레이어가 승리한 경우
                        final_HP = attacker['HP']
                        if final_HP < 0:
                            final_HP == 0
                        total_damage = first_HP - final_HP
                        if not practice:
                            ref_boss.update({"내구도" : final_HP})
                            ref_raid.update({"막타": True})
                        await weapon_battle_thread.send(f"**토벌 완료!** 총 대미지 : {total_damage}")
                
                if not practice or (practice and raid_ended): # 레이드 끝난 이후 도전한 경우    
                    ref_raid.update({"대미지": total_damage})
            elif tower:
                ref_current_floor = db.reference(f"탑/유저/{challenger_m.name}")
                tower_data = ref_current_floor.get() or {}
                current_floor = tower_data.get("층수", 1)

                if winner == "attacker": # 일반적인 상황
                    if defender['Id'] == 0: # 패배한 사람이 플레이어일 경우
                        await weapon_battle_thread.send(f"**{attacker['name']}**에게 패배!")
                        result = False
                    else: # 플레이어가 승리한 경우
                        if practice:
                            await weapon_battle_thread.send(f"**{attacker['name']}** 승리! {tower_floor}층 클리어!")
                        else:
                            if tower_floor != 1: #tower_floor 설정했다면? -> 빠른 전투
                                current_floor = tower_floor
                            await weapon_battle_thread.send(f"**{attacker['name']}** 승리! {current_floor}층 클리어!")
                        result = True
                elif winner == "defender": # 출혈 등 특수한 상황
                    if attacker['Id'] == 0: # 패배한 사람이 플레이어일 경우
                        await weapon_battle_thread.send(f"**{defender['name']}**에게 패배!")
                        result = False
                    else: # 플레이어가 승리한 경우
                        if practice:
                            await weapon_battle_thread.send(f"**{defender['name']}** 승리! {tower_floor}층 클리어!")
                        else:
                            if tower_floor != 1: #tower_floor 설정했다면? -> 빠른 전투
                                current_floor = tower_floor
                            await weapon_battle_thread.send(f"**{defender['name']}** 승리! {current_floor}층 클리어!")
                        result = True

                if not practice: # 연습모드 아닐 경우
                    if result:
                        if tower_floor != 1: #tower_floor 설정했다면? -> 빠른 전투
                            current_floor = tower_data.get("층수", 1)
                            ref_current_floor.update({"층수" : tower_floor + 1}) # 층수 1 올리기
                            ref_tc = db.reference(f'무기/아이템/{challenger_m.name}')
                            tc_data = ref_tc.get()
                            TC = tc_data.get('탑코인', 0)
                            
                            reward = 0
                            for floor in range(current_floor, tower_floor + 1):
                                if floor % 5 == 0:
                                    reward += 5
                                else:
                                    reward += 1
                            ref_tc.update({"탑코인" : TC + reward})
                            await weapon_battle_thread.send(f"탑코인 {reward}개 지급!")
                        else:
                            ref_current_floor.update({"층수" : current_floor + 1}) # 층수 1 올리기
                            ref_tc = db.reference(f'무기/아이템/{challenger_m.name}')
                            tc_data = ref_tc.get()
                            TC = tc_data.get('탑코인', 0)
                            if current_floor % 5 == 0:
                                ref_tc.update({"탑코인" : TC + 5})
                                await weapon_battle_thread.send(f"탑코인 5개 지급!")
                            else:
                                ref_tc.update({"탑코인" : TC + 1})
                                await weapon_battle_thread.send(f"탑코인 1개 지급!")
                    else:
                        ref_current_floor.update({"등반여부": True})

            else: # 일반 배틀
                if winner == "attacker": # 일반적인 상황
                    await weapon_battle_thread.send(f"**{attacker['name']}** 승리!")
                elif winner == "defender": # 출혈 등 특수한 상황
                    await weapon_battle_thread.send(f"**{defender['name']}** 승리!")
            return None
        
        
        def adjust_position(pos, move_distance, direction):
            """
            - pos: 현재 위치
            - move_distance: 이동 거리
            - direction: 이동 방향 (+1: 후퇴, -1: 돌진)
            - 0을 건너뛰도록 처리
            """
            for _ in range(move_distance):
                new_pos = pos + direction  # 방향에 따라 이동
                if new_pos == 0:  # 0을 건너뛰기
                    new_pos += direction  
                if MIN_DISTANCE <= new_pos <= MAX_DISTANCE:  # 범위 내에서만 이동
                    pos = new_pos  
            return pos

        def charging_shot(attacker, defender,evasion,skill_level):
            if not evasion:
                charging_shot_data = skill_data_firebase['차징샷']['values']
                move_distance = charging_shot_data['넉백거리']
                knockback_direction = -1 if defender['Id'] == 1 else 1
                defender["Position"] = adjust_position(defender["Position"], move_distance, knockback_direction)
                if (attacker["Position"] < 0 and defender["Position"] > 0) or (attacker["Position"] > 0 and defender["Position"] < 0):
                    battle_distance = abs(attacker["Position"] - defender["Position"]) - 1  # 0을 건너뛰므로 -1
                else:
                    battle_distance = abs(attacker["Position"] - defender["Position"])  # 같은 방향이면 그대로 계산
                if battle_distance >= charging_shot_data['적정거리']:
                    attack_increase_level = charging_shot_data['적정거리_공격력증가']
                    attack_increase = (attack_increase_level * skill_level)
                    accuracy_increase_level = charging_shot_data['적정거리_명중증가']
                    accuracy_increase = (accuracy_increase_level * skill_level)
                    attacker["Attack"] += attack_increase
                    attacker["Accuracy"] += accuracy_increase
                    apply_status_for_turn(defender, "속박", duration=charging_shot_data['속박_지속시간'])  # 속박 상태 지속시간만큼 지속
                    apply_status_for_turn(attacker, "차징샷", duration=1)
                    return f"**차징샷** 사용!\n상대를 {move_distance}만큼 날려버리고, {charging_shot_data['속박_지속시간']}턴간 속박합니다.\n적정 거리 추가 효과!\n이번 공격에 공격력 +{attack_increase}, 명중률 +{accuracy_increase} 부여!\n현재 거리: {battle_distance}\n"
                else:
                    apply_status_for_turn(defender, "속박", duration=charging_shot_data['속박_지속시간'])  # 속박 상태 지속시간만큼 지속
                    return f"**차징샷** 사용!\n상대를 {move_distance}만큼 날려버리고, {charging_shot_data['속박_지속시간']}턴간 속박합니다.\n현재 거리: {battle_distance}\n"
            else:
                return "**차징샷**이 빗나갔습니다!"

        def invisibility(attacker,skill_level):
            # 은신 상태에서 회피율 증가
            invisibility_data = skill_data_firebase['기습']['values']
            DefenseIgnore_increase_level =  invisibility_data['은신공격_레벨당_방관_증가']
            DefenseIgnore_increase = DefenseIgnore_increase_level * skill_level
            attacker["DefenseIgnore"] += DefenseIgnore_increase
            attacker["Evasion"] = 1
            invisibility_turns = invisibility_data['지속시간']
            apply_status_for_turn(attacker, "은신", duration=invisibility_turns)  # 은신 상태 지속시간만큼 지속
            apply_status_for_turn(attacker, "기습", duration=invisibility_turns)  # 은신 상태 지속시간만큼 지속
            return f"**기습** 사용! {invisibility_turns}턴간 은신 상태에 돌입하고 추가 피해를 입힙니다!\n"

        def smash(attacker, defender, evasion, skill_level):
            # 다음 공격은 반드시 치명타로 적용, 치명타 대미지 증가
            # 3턴간 둔화 부여
            if not evasion:
                smash_data = skill_data_firebase['강타']['values']
                slow_amount = smash_data['기본_둔화량'] + smash_data['레벨당_둔화량'] * skill_level
                CritDamageIncrease_level = smash_data['레벨당_치명타피해_증가']
                CritDamageIncrease = skill_level * CritDamageIncrease_level
                attack_increase_level = smash_data['레벨당_공격력_증가']
                attack_increase = skill_level * attack_increase_level
                accuracy = calculate_accuracy(attacker["Accuracy"]) # 1 - 명중률 수치만큼 빗나갈 확률 상쇄 가능
                base_damage = random.uniform((attacker["Attack"] + attack_increase) * accuracy, (attacker["Attack"] + attack_increase))  # 최소 ~ 최대 피해
                skill_damage = base_damage * (attacker["CritDamage"] + CritDamageIncrease)
                apply_status_for_turn(defender, "둔화", duration=3,value = slow_amount)
                message = f"**<:smash:1370302994301583380>강타** 사용!\n치명타 대미지 + {round(CritDamageIncrease * 100)}%, 공격력 + {attack_increase} 부여한 공격!\n3턴간 {round(slow_amount * 100)}% 둔화 효과를 부여합니다!"
            else:
                skill_damage = 0
                message = f"\n**<:smash:1370302994301583380>강타**가 빗나갔습니다!\n"

            return message,skill_damage
        
        def issen(attacker, defender, skill_level):
            # 일섬 : 다음턴에 적에게 날카로운 참격을 가한다. 회피를 무시하고 명중률에 비례한 대미지를 입히며, 표식을 부여한다.
            # 출혈 상태일 경우, 출혈 상태 해제 후 남은 피해의 150%를 즉시 입히고, 해당 피해의 50%를 고정 피해로 변환

            apply_status_for_turn(defender, "일섬", duration=2)
            message = f"**일섬** 사용!\n엄청난 속도로 적을 벤 후, 다음 턴에 날카로운 참격을 가합니다.\n회피를 무시하고 명중에 비례하는 대미지를 입힙니다.\n" 
            return message, 0
        
        def headShot(attacker, evasion,skill_level):
            """액티브 - 헤드샷: 치명타 확률에 따라 증가하는 스킬 피해"""
            # 헤드샷: 공격력 150(+50)%, 스킬 증폭 100(+30)%
            if not evasion:
                headShot_data = skill_data_firebase['헤드샷']['values']
                base_damage = headShot_data['기본_대미지'] + headShot_data['레벨당_기본_대미지'] * skill_level
                skill_multiplier = (headShot_data['기본_스킬증폭_계수'] + headShot_data['레벨당_스킬증폭_계수_증가'] * skill_level)
                attack_multiplier = (headShot_data['기본_공격력_계수'] + headShot_data['레벨당_공격력_계수_증가'] * skill_level)

                # 각각의 피해량 계산
                attack_based_damage = attacker['Attack'] * attack_multiplier
                spell_based_damage = attacker['Spell'] * skill_multiplier

                # 더 높은 피해를 기준으로 선택
                if attack_based_damage >= spell_based_damage:
                    skill_damage = attack_based_damage
                    skill_message = f"공격력을 기반으로 한 공격!\n{base_damage} + 공격력의 {round(attack_multiplier * 100)}% 피해를 입힙니다!\n"
                else:
                    skill_damage = spell_based_damage
                    skill_message = f"스킬 증폭을 기반으로 한 공격!\n{base_damage} + 스킬 증폭의 {round(skill_multiplier * 100)}% 피해를 입힙니다!\n"
                critical_bool = False
                if random.random() < attacker["CritChance"]:
                    skill_damage *= attacker["CritDamage"]
                    critical_bool = True

                apply_status_for_turn(attacker, "장전", duration=1)
                message = f"**<:headShot:1370300576545640459>헤드샷** 사용!\n{skill_message}1턴간 **장전**상태가 됩니다.\n"
            else:
                skill_damage = 0
                message = f"\n**<:headShot:1370300576545640459>헤드샷**이 빗나갔습니다!\n" 
                critical_bool = False
            return message, skill_damage, critical_bool
        
        def spearShot(attacker,defender,evasion,skill_level):
            spearShot_data = skill_data_firebase['창격']['values']
            near_distance = spearShot_data['근접_거리']
            condition_distance = spearShot_data['적정_거리']
            slow_amount = spearShot_data['기본_둔화량'] + spearShot_data['레벨당_둔화량'] * skill_level

            nonlocal battle_distance

            if evasion:
                return f"\n**창격** 사용 불가!\n공격이 빗나갔습니다!\n"
            if battle_distance <= near_distance: # 붙었을 땐 밀치기
                move_distance = spearShot_data['근접_밀쳐내기_거리']
                knockback_direction = -1 if defender['Id'] == 1 else 1
                defender["Position"] = adjust_position(defender["Position"], move_distance, knockback_direction)
                if (attacker["Position"] < 0 and defender["Position"] > 0) or (attacker["Position"] > 0 and defender["Position"] < 0):
                    battle_distance = abs(attacker["Position"] - defender["Position"]) - 1  # 0을 건너뛰므로 -1
                else:
                    battle_distance = abs(attacker["Position"] - defender["Position"])  # 같은 방향이면 그대로 계산
                apply_status_for_turn(defender, "속박", duration=1)
                return f"**창격(근접)** 사용!\n상대를 {move_distance}만큼 날려버립니다!\n1턴간 속박 효과를 부여합니다.\n"
            elif battle_distance == condition_distance: # 적정거리면 기절
                apply_status_for_turn(defender, "기절", duration=1)
                return f"**창격(적정 거리)** 사용!\n1턴간 기절 상태이상 부여!\n"
            elif battle_distance >= condition_distance + 1: # 원거리면 둔화
                apply_status_for_turn(defender, "둔화", duration=2,value = slow_amount)
                dash_direction = -1 if attacker['Id'] == 0 else 1
                attacker["Position"] = adjust_position(attacker["Position"], 1, dash_direction)
                if (attacker["Position"] < 0 and defender["Position"] > 0) or (attacker["Position"] > 0 and defender["Position"] < 0):
                    battle_distance = abs(attacker["Position"] - defender["Position"]) - 1  # 0을 건너뛰므로 -1
                else:
                    battle_distance = abs(attacker["Position"] - defender["Position"])  # 같은 방향이면 그대로 계산
                return f"**창격(원거리)** 사용!\n적을 향해 1칸 돌진합니다\n창을 던져 2턴간 {round(slow_amount * 100)}% 둔화 효과를 부여합니다\n"
            
        def mech_Arm(attacker,defender, evasion, skill_level):
            # 전선더미 방출: (20 + 레벨 당 5) + 스킬 증폭 20% + 레벨당 10% 추가 피해
            if not evasion:
                nonlocal battle_distance

                mech_Arm_data = skill_data_firebase['전선더미 방출']['values']
                base_damage = mech_Arm_data['기본_피해량'] + mech_Arm_data['레벨당_피해량_증가'] * skill_level
                skill_multiplier = (mech_Arm_data['기본_스킬증폭_계수'] + mech_Arm_data['레벨당_스킬증폭_계수_증가'] * skill_level)
                skill_damage = base_damage + attacker["Spell"] * skill_multiplier
                move_distance = mech_Arm_data['밀쳐내기_거리']
                knockback_direction = -1 if defender['Id'] == 1 else 1
                defender["Position"] = adjust_position(defender["Position"], move_distance, knockback_direction)
                if (attacker["Position"] < 0 and defender["Position"] > 0) or (attacker["Position"] > 0 and defender["Position"] < 0):
                    battle_distance = abs(attacker["Position"] - defender["Position"]) - 1  # 0을 건너뛰므로 -1
                else:
                    battle_distance = abs(attacker["Position"] - defender["Position"])  # 같은 방향이면 그대로 계산
                speed_decrease = mech_Arm_data['레벨당_속도감소_배율'] * skill_level
                defender["Speed"] *= 1 - speed_decrease
                if defender["Speed"] < 0:
                    defender["Speed"] = 0
                debuff_turns = mech_Arm_data['디버프_지속시간']
                apply_status_for_turn(defender, "둔화", duration=debuff_turns, value = speed_decrease)
                message = f"\n**<:siuu_Q:1370287135088840785>전선더미 방출** 사용!\n{base_damage} + (스킬 증폭 {int(skill_multiplier * 100)}%)의 스킬 피해를 입힌 후 상대를 {move_distance}만큼 날려버립니다!\n상대의 속도가 {debuff_turns}턴간 {int(speed_decrease * 100)}% 감소합니다!\n현재 거리: {battle_distance}\n"
            else:
                skill_damage = 0
                message = f"\n**<:siuu_Q:1370287135088840785>전선더미 방출이 빗나갔습니다!**\n"

            return message,skill_damage
        
        def Magnetic(attacker, defender, skill_level):
            nonlocal battle_distance

            # 자력 발산: (10 + 레벨 당 2) + 스킬 증폭 10% + 레벨당 5% 추가 피해
            Magnetic_data = skill_data_firebase['자력 발산']['values']
            grap_distance = Magnetic_data['최소_조건_거리']
            if battle_distance >= grap_distance:
                move_distance = Magnetic_data['끌어오기_거리']
                if battle_distance <= 1:
                    move_distance = 1
                base_damage = Magnetic_data['기본_피해량'] + Magnetic_data['레벨당_피해량_증가'] * skill_level
                skill_multiplier = (Magnetic_data['기본_스킬증폭_계수'] + Magnetic_data['레벨당_스킬증폭_계수_증가'] * skill_level)
                skill_damage = base_damage + attacker["Spell"] * skill_multiplier
                grab_direction = 1 if defender['Id'] == 1 else -1
                defender["Position"] = adjust_position(defender["Position"], move_distance, grab_direction)
                if (attacker["Position"] < 0 and defender["Position"] > 0) or (attacker["Position"] > 0 and defender["Position"] < 0):
                    battle_distance = abs(attacker["Position"] - defender["Position"]) - 1  # 0을 건너뛰므로 -1
                else:
                    battle_distance = abs(attacker["Position"] - defender["Position"])  # 같은 방향이면 그대로 계산
                speed_decrease = Magnetic_data['레벨당_속도감소_배율'] * skill_level
                defender["Speed"] *= 1 - speed_decrease
                if defender["Speed"] < 0:
                    defender["Speed"] = 0
                debuff_turns = Magnetic_data['디버프_지속시간']
                apply_status_for_turn(defender, "둔화", duration=debuff_turns, value = speed_decrease)
                message =  f"\n**자력 발산** 사용!\n{base_damage} + (스킬 증폭 {int(skill_multiplier * 100)}%)의 스킬 피해를 입힌 후 상대를 {move_distance}만큼 끌어옵니다!\n상대의 속도가 {debuff_turns}턴간 {int(speed_decrease * 100)}% 감소합니다!\n현재 거리: {battle_distance}\n"
            else:
                skill_damage = 0
                message = f"\n거리가 너무 가까워 **자력 발산**을 사용할 수 없습니다!\n"

            return message,skill_damage
        
        def Shield(attacker, skill_level):
            # 보호막: 스킬 증폭의 100% + 레벨당 10%만큼의 보호막을 얻음
            Shield_data = skill_data_firebase['보호막']['values']
            skill_multiplier = int(round((Shield_data['기본_스킬증폭_계수'] + Shield_data['레벨당_스킬증폭_계수'] * skill_level) * 100))
            shield_amount = int(round((skill_multiplier / 100) * attacker['Spell']))
            apply_status_for_turn(attacker,"보호막",3,shield_amount)
            message = f"\n**<:siuu_E:1370283463978123264>보호막** 사용!\n{shield_amount}만큼의 보호막을 2턴간 얻습니다!\n"

            return message
        
        def electronic_line(attacker,defender,skill_level):
            # 전깃줄: (40 + 레벨 당 10) + 스킬 증폭 50% + 레벨당 20% 추가 피해
            nonlocal battle_distance

            if battle_distance >= 2:
                electronic_line_data = skill_data_firebase['전깃줄']['values']
                base_damage = electronic_line_data['기본_피해량'] + electronic_line_data['레벨당_피해량_증가'] * skill_level
                skill_multiplier = (electronic_line_data['기본_스킬증폭_계수'] + electronic_line_data['레벨당_스킬증폭_계수_증가'] * skill_level)
                skill_damage = base_damage + attacker["Spell"] * skill_multiplier
                apply_status_for_turn(defender,"기절",1)
                message = f"\n**<:siuu_R:1370289428341329971>전깃줄** 사용!\n거리가 2 이상인 상대에게 {base_damage} + (스킬 증폭 {int(skill_multiplier * 100)}%)의 스킬 피해!\n1턴간 기절 부여!"
            else:
                skill_damage = 0
                message = f"\n<:siuu_R:1370289428341329971>거리가 너무 가까워 **전깃줄** 사용 불가!\n" 
            
            return message,skill_damage
        
        def Reap(attacker, evasion, skill_level):
            # 수확: (30 + 레벨 당 10) + 스킬 증폭 60% + 레벨 당 8% 추가 피해 + 공격력 20% + 레벨 당 5% 추가 피해
            if not evasion:
                Reap_data = skill_data_firebase['수확']['values']
                base_damage = Reap_data['기본_피해량'] + Reap_data['레벨당_피해량_증가'] * skill_level
                skill_multiplier = (Reap_data['기본_스킬증폭_계수'] + Reap_data['레벨당_스킬증폭_계수_증가'] * skill_level)
                attack_multiplier = (Reap_data['기본_공격력_계수'] + Reap_data['레벨당_공격력_계수_증가'] * skill_level)
                skill_damage = base_damage + attacker["Spell"] * skill_multiplier + attacker["Attack"] * attack_multiplier
                message = f"\n**<:reap:1370301351187185674>수확** 사용!\n상대에게 {base_damage} + (스킬 증폭 {int(skill_multiplier * 100)}%) + (공격력 {int(attack_multiplier * 100)}%)의 스킬 피해!\n"
            else:
                skill_damage = 0
                message = f"\n**<:reap:1370301351187185674>수확**이 빗나갔습니다!\n" 
            return message, skill_damage

        def unyielding(defender, skill_level):
            """불굴: 거리에 비례해 받는 대미지를 감소시킴"""
            unyielding_data = skill_data_firebase['불굴']['values']
            damage_reduction = min(unyielding_data['최대_피해감소율'], battle_distance * (unyielding_data['거리당_기본_피해감소'] + unyielding_data['거리당_레벨당_피해감소'] * skill_level))  # 최대 90% 감소 제한
            defender["DamageReduction"] = damage_reduction
            return f"\n**<:braum_E:1370258314666971236>불굴** 발동!\n거리에 비례하여 받는 대미지 {int(damage_reduction * 100)}% 감소!\n"
        
        def concussion_punch(target):
            """패시브 - 뇌진탕 펀치: 공격 적중 시 뇌진탕 스택 부여, 4스택 시 기절"""
            target["뇌진탕"] = target.get("뇌진탕", 0) + 1

            message = f"**<:braum_P:1370258039092805673>뇌진탕 펀치** 효과로 뇌진탕 스택 {target['뇌진탕']}/4 부여!"
            
            if target["뇌진탕"] >= 4:
                target["뇌진탕"] = 0
                apply_status_for_turn(target, "기절", duration=1)
                message += f"\n**<:braum_P:1370258039092805673>뇌진탕 폭발!** {target['name']} 1턴간 기절!\n"
            return message

        def frostbite(attacker, target, evasion, skill_level):
            """액티브 - 동상: 스킬 피해 + 스피드 감소"""
            # 동상: (20 + 레벨 당 5) +스킬 증폭 30% + 레벨당 10% 추가 피해
            if not evasion:
                frostbite_data = skill_data_firebase['동상']['values']
                base_damage = frostbite_data['기본_피해량'] + (frostbite_data['레벨당_피해량_증가'] * skill_level)
                skill_multiplier = (frostbite_data['기본_스킬증폭_계수'] + frostbite_data['레벨당_스킬증폭_계수_증가'] * skill_level)
                skill_damage = base_damage + attacker["Spell"] * skill_multiplier
                debuff_turns = frostbite_data['디버프_지속시간']
                apply_status_for_turn(target, "동상", duration=debuff_turns)
                speed_decrease = frostbite_data['속도감소_기본수치'] + (frostbite_data['레벨당_속도감소_증가'] * skill_level)
                target["Speed"] *= (1- speed_decrease)
                target["뇌진탕"] = target.get("뇌진탕", 0) + 1

                message = f"\n**<:braum_Q:1370258276855451698>동상** 사용!\n{base_damage} + (스킬 증폭 {int(skill_multiplier * 100)}%)의 스킬 피해!\n뇌진탕을 부여하고, 스피드가 {debuff_turns}턴간 {int(speed_decrease * 100)}% 감소!\n뇌진탕 스택 {target['뇌진탕']}/4 부여!\n"
                
                if target["뇌진탕"] >= 4:
                    target["뇌진탕"] = 0
                    apply_status_for_turn(target, "기절", duration=1)
                    message += f"\n**뇌진탕 폭발!** {target['name']} 1턴간 **기절!**\n"

            else:
                skill_damage = 0
                message = f"\n**<:braum_Q:1370258276855451698>동상이 빗나갔습니다!**\n"
            return message, skill_damage

        def glacial_fissure(attacker, target, evasion,skill_level):
            # 빙하 균열: (40 + 레벨 당 30) +스킬 증폭 60% + 레벨당 30% + 거리 추가 피해 (1당 5%)
            if not evasion:
                glacial_fissure_data = skill_data_firebase['빙하 균열']['values']       
                base_damage = glacial_fissure_data['기본_피해량'] + (glacial_fissure_data['레벨당_피해량_증가'] * skill_level)
                skill_multiplier = (glacial_fissure_data['기본_스킬증폭_계수'] + glacial_fissure_data['레벨당_스킬증폭_계수_증가'] * skill_level)
                distance_bonus = min(glacial_fissure_data['거리당_레벨당_피해배율_증가'] * skill_level * battle_distance, glacial_fissure_data['최대_거리_피해배율_보너스'])
                skill_damage = base_damage + attacker["Spell"] * skill_multiplier * (1 + distance_bonus)
                apply_status_for_turn(target,"기절",1)

                message = f"\n**<:braum_R:1370258355804962826>빙하 균열** 사용!\n{base_damage} + (스킬 증폭 {int(round(skill_multiplier * 100))}%)의 스킬 피해!\n{target['name']} 1턴간 기절!\n"

            else:
                skill_damage = 0
                message = f"\n**<:braum_R:1370258355804962826>빙하 균열이 빗나갔습니다!**\n"
            return message, skill_damage
        
        def rapid_fire(attacker, defender, skill_level):
            """스피드에 비례하여 연속 공격하는 속사 스킬"""
            rapid_fire_data = skill_data_firebase['속사']['values']

            speed = attacker["Speed"]
            hit_count = max(2, speed // rapid_fire_data['타격횟수결정_스피드값'])  # 최소 2회, 스피드 20당 1회 추가
            total_damage = 0

            def calculate_damage(attacker,defender,multiplier):
                accuracy = calculate_accuracy(attacker["Accuracy"]) # 1 - 명중률 수치만큼 빗나갈 확률 상쇄 가능
                base_damage = random.uniform(attacker["Attack"] * accuracy, attacker["Attack"])  # 최소 ~ 최대 피해
                critical_bool = False
                evasion_bool = False
                distance_evasion = calculate_evasion(battle_distance) # 거리 2부터 1당 10%씩 빗나갈 확률 추가   
                if random.random() < (defender["Evasion"] + distance_evasion) * (1 - accuracy): # 회피
                    evasion_bool = True
                    return 0, False, evasion_bool

                # 피해 증폭
                base_damage *= 1 + attacker["DamageEnhance"]

                if random.random() < attacker["CritChance"]:
                    base_damage *= attacker["CritDamage"]
                    critical_bool = True

                defense = max(0, defender["Defense"] - attacker["DefenseIgnore"])
                damage_reduction = calculate_damage_reduction(defense)
                defend_damage = base_damage * (1 - damage_reduction) * (multiplier)
                final_damage = defend_damage * (1 - defender['DamageReduction']) # 대미지 감소 적용
                return max(1, round(final_damage)), critical_bool, evasion_bool
                
            message = ""
            for i in range(hit_count):
                # multiplier = rapid_fire_data['일반타격_기본_피해배율'] if i < hit_count - 1 else rapid_fire_data['마지막타격_기본_피해배율']  # 마지막 공격은 조금 더 강하게
                multiplier = rapid_fire_data['일반타격_기본_피해배율']
                damage, critical, evade = calculate_damage(attacker, defender, multiplier=multiplier + skill_level * rapid_fire_data['레벨당_피해배율'])

                crit_text = "💥" if critical else ""
                evade_text = "회피!⚡️" if evade else ""
                message += f"**{evade_text}{damage} 대미지!{crit_text}**\n"
                
                total_damage += damage
            
            message += f"<:rapid_fire:1370301811663175802>**속사**로 {hit_count}연타 공격! 총 {total_damage} 피해!"
            return message,total_damage
        
        def meditate(attacker, skill_level):
            # 명상 : 모든 스킬 쿨타임 감소 + 스킬 증폭 비례 보호막 획득, 명상 스택 획득
            meditate_data = skill_data_firebase['명상']['values']
            shield_amount = int(round(attacker['Spell'] * (meditate_data['스킬증폭당_보호막_계수'] + meditate_data['레벨당_보호막_계수_증가'] * skill_level)))
            for skill, cooldown_data in attacker["Skills"].items():
                if cooldown_data["현재 쿨타임"] > 0:
                    attacker["Skills"][skill]["현재 쿨타임"] -= 1  # 현재 쿨타임 감소
            attacker['명상'] = attacker.get("명상", 0) + 1 # 명상 스택 + 1 추가
            apply_status_for_turn(attacker,"보호막",1,shield_amount)
            message = f"**<:meditation:1370297293957496954>명상** 사용!(현재 명상 스택 : {attacker['명상']})\n 모든 스킬의 현재 쿨타임이 1턴 감소하고 1턴간 {shield_amount}의 보호막 생성!\n"

            skill_damage = 0
            return message,skill_damage
        
        def fire(attacker, defender, evasion, skill_level):
            # 기본 : Flare(플레어) 강화 : Meteor(메테오)
            # 플레어 : 기본 피해 + 스킬증폭 비례의 스킬 피해. 1턴간 '화상' 상태이상 부여
            # 메테오 : 강화 기본 피해 + 스킬증폭 비례의 스킬 피해. 1턴간 기절 부여, 3턴간 '화상' 상태이상 부여
            fire_data = skill_data_firebase['화염 마법']['values']
            meditation = attacker.get("명상",0) # 현재 명상 스택 확인
            if meditation >= 5: # 명상 스택이 5 이상일 경우 스택 5 제거 후 강화된 스킬 시전
                # 메테오
                meditation -= 5 # 명상 스택 5 제거
                attacker['명상'] = meditation
                if not evasion:
                    base_damage = fire_data['강화_기본_피해량'] + fire_data['레벨당_강화_기본_피해량_증가'] * skill_level
                    skill_multiplier = fire_data['강화_기본_스킬증폭_계수'] + fire_data['레벨당_강화_스킬증폭_계수_증가'] * skill_level
                    skill_damage = base_damage + attacker['Spell'] * skill_multiplier
                    burn_skill_multiplier = fire_data['화상_기본_스킬증폭_계수'] + fire_data['화상_레벨당_스킬증폭_계수_증가'] * skill_level
                    burn_damage = round(fire_data['화상_대미지'] * skill_level + attacker['Spell'] * burn_skill_multiplier)
                    apply_status_for_turn(defender, "기절", 1)
                    apply_status_for_turn(defender, "화상", 3, burn_damage)
                    apply_status_for_turn(defender, "치유 감소", 4, fire_data['화상_치유감소_수치'])
                    message = f"**<:meteor:1370295232889098250>메테오** 사용!\n {base_damage} + 스킬증폭 {round(skill_multiplier * 100)}%의 스킬피해!\n1턴간 기절 부여 및 3턴간 화상 부여!"
                else:
                    skill_damage = 0
                    message = f"**<:meteor:1370295232889098250>메테오**가 빗나갔습니다!\n"
            else:
                # 플레어
                if not evasion:
                    base_damage = fire_data['기본_피해량'] + fire_data['레벨당_기본_피해량_증가'] * skill_level
                    skill_multiplier = fire_data['기본_스킬증폭_계수'] + fire_data['레벨당_스킬증폭_계수_증가'] * skill_level
                    skill_damage = base_damage + attacker['Spell'] * skill_multiplier
                    burn_skill_multiplier = fire_data['화상_기본_스킬증폭_계수'] + fire_data['화상_레벨당_스킬증폭_계수_증가'] * skill_level
                    burn_damage = round(fire_data['화상_대미지'] * skill_level + attacker['Spell'] * burn_skill_multiplier)
                    apply_status_for_turn(defender, "화상", 1, burn_damage)
                    apply_status_for_turn(defender, "치유 감소", 2, fire_data['화상_치유감소_수치'])
                    message = f"**<:flare:1370295196948107314>플레어** 사용!\n {base_damage} + 스킬증폭 {round(skill_multiplier * 100)}%의 스킬피해!\n1턴간 화상 부여!"
                else:
                    skill_damage = 0
                    message = f"**<:flare:1370295196948107314>플레어**가 빗나갔습니다!\n"
            return message,skill_damage
        
        def ice(attacker,defender, evasion, skill_level):
            # 기본 : Frost(프로스트) 강화 : Blizzard(블리자드)
            # 프로스트 : 기본 피해 + 스킬증폭 비례의 스킬 피해. 1턴간 '빙결' 상태이상 부여
            # 블리자드 : 강화 기본 피해 + 스킬증폭 비례의 스킬 피해. 3턴간 '빙결' 상태이상 부여 (빙결 : 공격받기 전까지 계속 스턴 상태)
            ice_data = skill_data_firebase['냉기 마법']['values']
            meditation = attacker.get("명상",0) # 현재 명상 스택 확인
            if meditation >= 5: # 명상 스택이 5 이상일 경우 스택 5 제거 후 강화된 스킬 시전
                # 블리자드
                meditation -= 5 # 명상 스택 5 제거
                attacker['명상'] = meditation
                if not evasion:
                    base_damage = ice_data['강화_기본_피해량'] + ice_data['레벨당_강화_기본_피해량_증가'] * skill_level
                    skill_multiplier = ice_data['강화_기본_스킬증폭_계수'] + ice_data['레벨당_강화_스킬증폭_계수_증가'] * skill_level
                    skill_damage = base_damage + attacker['Spell'] * skill_multiplier
                    slow_amount = int(round((ice_data['강화_둔화율'] + ice_data['강화_레벨당_둔화율'] * skill_level) * 100))
                    apply_status_for_turn(defender, "빙결", 3)
                    apply_status_for_turn(defender, "둔화", 5, slow_amount / 100)
                    message = f"**<:blizzard:1370295342372749332>블리자드** 사용!\n {base_damage} + 스킬증폭 {round(skill_multiplier * 100)}%의 스킬피해!\n3턴간 빙결 부여!, 5턴간 {slow_amount}% 둔화 부여!"
                else:
                    skill_damage = 0
                    message = f"**<:blizzard:1370295342372749332>블리자드**가 빗나갔습니다!\n"
            else:
                # 프로스트
                if not evasion:
                    base_damage = ice_data['기본_피해량'] + ice_data['레벨당_기본_피해량_증가'] * skill_level
                    skill_multiplier = ice_data['기본_스킬증폭_계수'] + ice_data['레벨당_스킬증폭_계수_증가'] * skill_level
                    skill_damage = base_damage + attacker['Spell'] * skill_multiplier
                    apply_status_for_turn(defender, "빙결", 1)
                    message = f"**<:frost:1370295315919540304>프로스트** 사용!\n {base_damage} + 스킬증폭 {round(skill_multiplier * 100)}%의 스킬피해!\n1턴간 빙결 부여!"
                else:
                    skill_damage = 0
                    message = f"**<:frost:1370295315919540304>프로스트**가 빗나갔습니다!\n"
            return message,skill_damage

        def holy(attacker,defender, evasion, skill_level):
            # 기본 : Bless(블레스) 강화 : Judgment(저지먼트)
            # 블레스 : 기본 피해 + 스킬증폭 비례의 스킬 피해. 정해진 수치만큼 회복
            # 저지먼트 : 강화 기본 피해 + 스킬증폭 비례의 스킬 피해. 3턴간 '침묵' 상태이상 부여 (침묵 : 스킬 사용 불가능)
            holy_data = skill_data_firebase['신성 마법']['values']
            meditation = attacker.get("명상",0) # 현재 명상 스택 확인
            if meditation >= 5: # 명상 스택이 5 이상일 경우 스택 5 제거 후 강화된 스킬 시전
                # 저지먼트
                meditation -= 5 # 명상 스택 5 제거
                attacker['명상'] = meditation
                if not evasion:
                    base_damage = holy_data['강화_기본_피해량'] + holy_data['레벨당_강화_기본_피해량_증가'] * skill_level
                    skill_multiplier = holy_data['강화_기본_스킬증폭_계수'] + holy_data['레벨당_강화_스킬증폭_계수_증가'] * skill_level
                    skill_damage = base_damage + attacker['Spell'] * skill_multiplier
                    apply_status_for_turn(defender, "침묵", 3)
                    message = f"**<:judgement:1370295397813194772>저지먼트** 사용!\n {base_damage} + 스킬증폭 {round(skill_multiplier * 100)}%의 스킬피해!\n3턴간 침묵 부여!"
                else:
                    skill_damage = 0
                    message = f"**<:judgement:1370295397813194772>저지먼트**가 빗나갔습니다!\n"
            else:
                # 블레스
                if not evasion:
                    base_damage = holy_data['기본_피해량'] + holy_data['레벨당_기본_피해량_증가'] * skill_level
                    skill_multiplier = holy_data['기본_스킬증폭_계수'] + holy_data['레벨당_스킬증폭_계수_증가'] * skill_level
                    skill_damage = base_damage + attacker['Spell'] * skill_multiplier
                    heal_skill_multiplier = (holy_data['치유_기본_스킬증폭_계수'] + holy_data['치유_레벨당_스킬증폭_계수_증가'] * skill_level)
                    heal_amount = round(holy_data['레벨당_치유량'] * skill_level + attacker['Spell'] * heal_skill_multiplier)
                    # 기본 힐량과 스킬 관련 계산
                    if "치유 감소" in attacker["Status"]:
                        healban_amount = attacker['Status']['치유 감소']['value']
                        reduced_heal = round(heal_amount * healban_amount)
                    else:
                        reduced_heal = 0

                    initial_HP = attacker['HP']  # 회복 전 내구도 저장
                    attacker['HP'] += heal_amount - reduced_heal  # 힐 적용
                    attacker['HP'] = min(attacker['HP'], attacker['BaseHP'])  # 최대 내구도 이상 회복되지 않도록 제한

                    # 최종 회복된 내구도
                    final_HP = attacker['HP']

                    # 메시지 출력
                    if "치유 감소" in attacker["Status"]:
                        message = f"**<:bless:1370295371997253673>블레스** 사용!\n {base_damage} + 스킬증폭 {round(skill_multiplier * 100)}%의 스킬피해!\n{heal_amount}(-{reduced_heal})만큼 내구도 회복!\n내구도: [{initial_HP}] → [{final_HP}] ❤️ (+{final_HP - initial_HP})"
                    else:
                        message = f"**<:bless:1370295371997253673>블레스** 사용!\n {base_damage} + 스킬증폭 {round(skill_multiplier * 100)}%의 스킬피해!\n{heal_amount}만큼 내구도 회복!\n내구도: [{initial_HP}] → [{final_HP}] ❤️ (+{final_HP - initial_HP})"
                else:
                    skill_damage = 0
                    message = f"**<:bless:1370295371997253673>블레스**가 빗나갔습니다!\n"
            return message,skill_damage
        
        def second_skin(target, skill_level, value):
            """패시브 - 두번째 피부: 공격 적중 시 플라즈마 중첩 부여, 5스택 시 현재 체력 비례 10% 대미지"""
            target["플라즈마 중첩"] = target.get("플라즈마 중첩", 0) + value
            message = f"<:kaisa_P:1370259635596038175>**두번째 피부** 효과로 플라즈마 중첩 {target['플라즈마 중첩']}/5 부여!"

            second_skin_data = skill_data_firebase['두번째 피부']['values']
            skill_damage = 0
            
            if target["플라즈마 중첩"] >= 5:
                target["플라즈마 중첩"] = 0
                skill_damage = round(target['HP'] * (second_skin_data['기본_대미지'] + second_skin_data['레벨당_추가_대미지'] * skill_level))
                damage_value = round((second_skin_data['기본_대미지'] + second_skin_data['레벨당_추가_대미지'] * skill_level) * 100)
                message += f"\n<:kaisa_P:1370259635596038175>**플라즈마 폭발!** 현재 내구도의 {damage_value}% 대미지!\n"
            return message, skill_damage

        def icathian_rain(attacker, defender, skill_level):
            """스피드에 비례하여 연속 공격하는 속사 스킬"""
            icathian_rain_data = skill_data_firebase['이케시아 폭우']['values']

            speed = attacker["Speed"]
            hit_count = max(2, speed // icathian_rain_data['타격횟수결정_스피드값'])  # 최소 2회, 스피드당 1회 추가
            total_damage = 0

            def calculate_damage(attacker,defender,multiplier):
                accuracy = calculate_accuracy(attacker["Accuracy"]) # 1 - 명중률 수치만큼 빗나갈 확률 상쇄 가능
                base_damage = random.uniform(attacker["Attack"] * accuracy, attacker["Attack"])  # 최소 ~ 최대 피해
                critical_bool = False
                evasion_bool = False
                distance_evasion = calculate_evasion(battle_distance) # 거리 2부터 1당 10%씩 빗나갈 확률 추가   
                if random.random() < (defender["Evasion"] + distance_evasion)* (1 - accuracy): # 회피
                    evasion_bool = True
                    return 0, False, evasion_bool

                # 피해 증폭
                base_damage *= 1 + attacker["DamageEnhance"]

                if random.random() < attacker["CritChance"]:
                    base_damage *= attacker["CritDamage"]
                    critical_bool = True
                
                defense = max(0, defender["Defense"] - attacker["DefenseIgnore"])
                damage_reduction = calculate_damage_reduction(defense)
                defend_damage = base_damage * (1 - damage_reduction) * (multiplier + skill_level * icathian_rain_data['레벨당_피해배율'])
                final_damage = defend_damage * (1 - defender['DamageReduction']) # 대미지 감소 적용
                return max(1, round(final_damage)), critical_bool, evasion_bool
                
            message = ""
            for _ in range(hit_count):
                multiplier = icathian_rain_data['일반타격_기본_피해배율']
                damage, critical, evade = calculate_damage(attacker, defender, multiplier=multiplier)

                crit_text = "💥" if critical else ""
                evade_text = "회피!⚡️" if evade else ""
                message += f"**{evade_text}{damage} 대미지!{crit_text}**\n"
                
                total_damage += damage
            
            passive_skill_data = attacker["Skills"].get("두번째 피부", None)   
            passive_skill_level = passive_skill_data["레벨"]
            passive_message, explosion_damage = second_skin(defender, passive_skill_level, 1)
            defense = max(0, defender["Defense"] - attacker["DefenseIgnore"])
            damage_reduction = calculate_damage_reduction(defense)
            defend_damage = explosion_damage * (1 - damage_reduction)
            final_damage = defend_damage * (1 - defender['DamageReduction'])
            message += f"<:kaisa_Q:1370259693972361277>이케시아 폭우로 {hit_count}연타 공격! 총 {total_damage} 피해!\n"
            message += passive_message
            total_damage += final_damage
            return message,total_damage
        
        def voidseeker(attacker, defender, evasion, skill_level):
            # 공허추적자: 스킬 증폭 70% + 레벨당 10%의 스킬 대미지
            if not evasion:
                voidseeker_data = skill_data_firebase['공허추적자']['values']       
                skill_multiplier = (voidseeker_data['기본_스킬증폭_계수'] + voidseeker_data['레벨당_스킬증폭_계수_증가'] * skill_level)
                skill_damage = attacker["Spell"] * skill_multiplier
                apply_status_for_turn(defender,"속박",1)

                message = f"\n<:kaisa_W:1370259790772572171>**공허추적자** 사용!\n스킬 증폭 {int(round(skill_multiplier * 100))}%의 스킬 피해를 입히고 1턴간 속박!\n"
                passive_skill_data = attacker["Skills"].get("두번째 피부", None)   
                passive_skill_level = passive_skill_data["레벨"]
                passive_message, explosion_damage = second_skin(defender, passive_skill_level, 2)
                message += passive_message
                skill_damage += explosion_damage
            else:
                skill_damage = 0
                message = f"\n**<:kaisa_W:1370259790772572171>공허추적자**가 빗나갔습니다!\n"
            return message, skill_damage

        def supercharger(attacker, skill_level):
            # 고속충전: 1턴간 회피율 증가, 3턴간 스피드 증가
            supercharger_data = skill_data_firebase['고속충전']['values']
            attacker["Evasion"] = 1
            invisibility_turns = supercharger_data['은신_지속시간']
            apply_status_for_turn(attacker, "은신", duration=invisibility_turns)  # 은신 상태 지속시간만큼 지속
            speedup_turns = supercharger_data['속도증가_지속시간']
            base_speedup = supercharger_data['속도증가_기본수치']
            speedup_level = supercharger_data['속도증가_레벨당']
            speedup_value = base_speedup + speedup_level * skill_level
            attacker["Speed"] += speedup_value
            apply_status_for_turn(attacker, "고속충전_속도증가", duration=speedup_turns)
            return f"<:kaisa_E:1370259874264518798>**고속충전** 사용! {invisibility_turns}턴간 은신 상태에 돌입합니다!\n{speedup_turns}턴간 스피드가 {speedup_value} 증가합니다!\n"
        
        def killer_instinct(attacker, defender, skill_level):
            # 사냥본능: 상대의 뒤로 파고들며 2턴간 보호막을 얻음.
            killer_instinct_data = skill_data_firebase['사냥본능']['values']
            retreat_direction = 1 if attacker['Id'] == 0 else -1  

            target_position = defender['Position'] - (retreat_direction * 1)
            attacker['Position'] = target_position * -1
            defender['Position'] = defender['Position'] * -1
            battle_distance = 1

            shield_amount = killer_instinct_data['기본_보호막량'] + killer_instinct_data['레벨당_보호막량'] * skill_level
            apply_status_for_turn(attacker,"보호막",3,shield_amount)
            return f"**<:kaisa_R:1370259948172349481>사냥본능** 사용! 상대 뒤로 즉시 이동하며, 2턴간 {shield_amount}의 보호막을 얻습니다!\n"

        def cursed_body(attacker, skill_level):
            #저주받은 바디: 공격당하면 확률에 따라 공격자를 둔화
            cursed_body_data = skill_data_firebase['저주받은 바디']['values']
            if random.random() < cursed_body_data['둔화_확률'] + cursed_body_data['레벨당_둔화_확률'] * skill_level: # 확률에 따라 둔화 부여
                slow_amount = cursed_body_data['둔화량'] + cursed_body_data['레벨당_둔화량'] * skill_level
                apply_status_for_turn(attacker,"둔화",2, slow_amount)
                return f"**저주받은 바디** 발동!\n공격자에게 1턴간 {round(slow_amount * 100)}% 둔화 부여!\n"
            else:
                return ""

        def shadow_ball(attacker,defender,evasion,skill_level):
            #섀도볼 : 스킬 증폭 기반 피해를 입히고, 50% 확률로 2턴간 침묵
            
            if not evasion:
                shadow_ball_data = skill_data_firebase['섀도볼']['values']    
                skill_multiplier = (shadow_ball_data['기본_스킬증폭_계수'] + shadow_ball_data['레벨당_스킬증폭_계수_증가'] * skill_level)
                skill_damage = attacker["Spell"] * skill_multiplier

                message = f"\n**섀도볼** 사용!\n스킬 증폭 {int(round(skill_multiplier * 100))}%의 스킬 피해!\n"

                cc_probability = shadow_ball_data['침묵_확률'] + shadow_ball_data['레벨당_침묵_확률'] * skill_level
                if random.random() < cc_probability: # 확룰에 따라 침묵 부여
                    apply_status_for_turn(defender,"침묵",2)
                    message += f"침묵 상태이상 2턴간 부여!(확률 : {round(cc_probability * 100)}%)"
                
            else:
                skill_damage = 0
                message = f"\n**섀도볼**이 빗나갔습니다!\n"
            return message, skill_damage

        def Hex(attacker,defender,evasion,skill_level):
            #병상첨병 : 스킬 증폭 기반 피해를 입히고, 대상이 상태이상 상태라면 2배의 피해를 입힘.
            if not evasion:
                Hex_data = skill_data_firebase['병상첨병']['values']    
                skill_multiplier = (Hex_data['기본_스킬증폭_계수'] + Hex_data['레벨당_스킬증폭_계수_증가'] * skill_level)
                skill_damage = attacker["Spell"] * skill_multiplier
                
                message = f"\n**병상첨병** 사용!\n스킬 증폭 {int(round(skill_multiplier * 100))}%의 스킬 피해!\n"
                cc_status = ['빙결', '화상', '침묵', '기절', '속박', '독', '둔화']
                if any(status in cc_status for status in defender['Status']): # 상태이상 적용상태라면
                    skill_damage *= 2
                    message = f"\n**병상첨병** 사용!\n스킬 증폭 {int(round(skill_multiplier * 100))}%의 스킬 피해!\n**상태이상으로 인해 대미지 2배!**\n"
               
            else:
                skill_damage = 0
                message = f"\n**병상첨병**이 빗나갔습니다!\n"
            return message, skill_damage

        def poison_jab(attacker,defender,evasion,skill_level):
            #독찌르기 : 공격력 기반 피해를 입히고, 50% 확률로 독 상태 부여
            if not evasion:
                poison_jab_data = skill_data_firebase['독찌르기']['values']    
                attack_multiplier = (poison_jab_data['기본_공격력_계수'] + poison_jab_data['레벨당_공격력_계수_증가'] * skill_level)
                skill_damage = attacker["Attack"] * attack_multiplier
                
                message = f"\n**독찌르기** 사용!\n공격력 {int(round(attack_multiplier * 100))}%의 스킬 피해!\n"
                cc_probability = poison_jab_data['독_확률'] + poison_jab_data['레벨당_독_확률'] * skill_level
                if random.random() < cc_probability: # 확룰에 따라 독 부여
                    apply_status_for_turn(defender,"독",3)
                    message += f"독 상태이상 3턴간 부여!(확률 : {round(cc_probability * 100)}%)"

            else:
                skill_damage = 0
                message = f"\n**독찌르기**가 빗나갔습니다!\n"
            return message, skill_damage

        def fire_punch(attacker,defender,evasion,skill_level):
            #불꽃 펀치 : 공격력 기반 피해를 입히고, 50% 확률로 3턴간 화상 상태 부여
            if not evasion:
                poison_jab_data = skill_data_firebase['불꽃 펀치']['values']    
                attack_multiplier = (poison_jab_data['기본_공격력_계수'] + poison_jab_data['레벨당_공격력_계수_증가'] * skill_level)
                skill_damage = attacker["Attack"] * attack_multiplier
                
                message = f"\n**불꽃 펀치** 사용!\n공격력 {int(round(attack_multiplier * 100))}%의 스킬 피해!\n"
                cc_probability = poison_jab_data['화상_확률'] + poison_jab_data['레벨당_화상_확률'] * skill_level
                if random.random() < cc_probability: # 확룰에 따라 화상 부여
                    burn_damage = poison_jab_data['화상_대미지'] + poison_jab_data['레벨당_화상_대미지'] * skill_level
                    apply_status_for_turn(defender,"화상",3, burn_damage)
                    apply_status_for_turn(defender,"치유 감소", 4, 0.3)
                    message += f"화상 상태이상 3턴간 부여!(확률 : {round(cc_probability * 100)}%)"

            else:
                skill_damage = 0
                message = f"\n**불꽃 펀치**가 빗나갔습니다!\n"
            return message, skill_damage

        def timer():
            skill_damage = 1000000
            message = f"타이머 종료!\n"
            return message, skill_damage

        if simulate:
            weapon_data_challenger = wdc
            weapon_data_opponent = wdo
        else:
            ref_weapon_challenger = db.reference(f"무기/유저/{challenger_m.name}")
            weapon_data_challenger = ref_weapon_challenger.get() or {}

            if raid:
                ref_weapon_opponent = db.reference(f"레이드/보스/{boss}")
                weapon_data_opponent = ref_weapon_opponent.get() or {}
            elif tower:
                if practice:
                    current_floor = tower_floor
                else:
                    if tower_floor != 1: #tower_floor 설정했다면? -> 빠른 전투
                        current_floor = tower_floor
                    else:
                        ref_current_floor = db.reference(f"탑/유저/{challenger_m.name}")
                        tower_data = ref_current_floor.get() or {}
                        current_floor = tower_data.get("층수", 1)
                weapon_data_opponent = generate_tower_weapon(current_floor)
            else:
                ref_weapon_opponent = db.reference(f"무기/유저/{opponent_m.name}")
                weapon_data_opponent = ref_weapon_opponent.get() or {}
        

        # 공격 함수
        async def attack(attacker, defender, evasion, reloading, skills = None):

            remove_status_effects(attacker)
            update_status(attacker)  # 공격자의 상태 업데이트 (은신 등)

            skill_message = ""
            if reloading:
                return 0, False, False, False, ""
            
            if skills:
                damage, skill_message, critical_bool = use_skill(attacker, defender, skills, evasion, reloading)
                if damage is not None:
                    return damage, critical_bool, False, False, skill_message  # 스킬 피해 적용
                else:
                    return 0, critical_bool, False, evasion, skill_message

            if evasion: # 회피
                return 0, False, False, True, ""

            accuracy = calculate_accuracy(attacker["Accuracy"]) # 1 - 명중률 수치만큼 빗나갈 확률 상쇄 가능

            base_damage = random.uniform(attacker["Attack"] * accuracy, attacker["Attack"])  # 최소 ~ 최대 피해
            distance_bool = False
            critical_bool = False

            if "두번째 피부" in attacker['Status']:
                passive_skill_data = attacker["Skills"].get("두번째 피부", None)   
                passive_skill_level = passive_skill_data["레벨"]
                message, damage = second_skin(defender,passive_skill_level, 1)
                skill_message += message
                base_damage += damage

            if attacker["Weapon"] == "창" and battle_distance == 3: #창 적정거리 추가 대미지
                skill_level = attacker["Skills"]["창격"]["레벨"]
                spearShot_data = skill_data_firebase['창격']['values']
                base_damage *= 1 + (spearShot_data['중거리_기본공격_추가피해_레벨당'] * skill_level)
                distance_bool = True

            # 피해 증폭
            base_damage *= 1 + attacker["DamageEnhance"]

            if random.random() < attacker["CritChance"]:
                base_damage *= attacker["CritDamage"]
                critical_bool = True

            defense = defender["Defense"] - attacker["DefenseIgnore"]
            if defense < 0:
                defense = 0
            damage_reduction = calculate_damage_reduction(defense)
            defend_damage = base_damage * (1 - damage_reduction)
            final_damage = defend_damage * (1 - defender['DamageReduction']) # 대미지 감소 적용
            
            return max(1, round(final_damage)), critical_bool, distance_bool, False, skill_message # 최소 피해량 보장
        
        def use_skill(attacker, defender, skills, evasion, reloading):
            """스킬을 사용하여 피해를 입히고 효과를 적용"""

            total_damage = 0  # 총 피해량 저장
            result_message = ""
            critical_bool = False
            for skill_name in skills:
                skill_data = attacker["Skills"].get(skill_name, None)
                if not skill_data or skill_data["현재 쿨타임"] > 0:
                    result_message += f"{skill_name}의 남은 쿨타임 : {skill_data['현재 쿨타임']}턴\n"
                    return None, result_message, critical_bool  # 쿨타임 중
                
                skill_level = skill_data["레벨"]
                skill_cooldown = skill_data["전체 쿨타임"]

                if reloading:
                    result_message += f"재장전 중이라 {skill_name}을 사용할 수 없습니다!\n"
                    return None, result_message, critical_bool # 재장전 중
                
                skill_range = skill_data.get("사거리", 1)
                if battle_distance > skill_range:
                    result_message += f"거리가 멀어 {skill_name} 사용 불가!\n"
                    if skill_name != "강타":
                        attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown
                    return None, result_message, critical_bool  # 사거리가 안닿는 경우 쿨타임을 돌림
                
                if skill_name == "빙하 균열":
                    skill_message, damage= glacial_fissure(attacker,defender,evasion,skill_level)
                    result_message += skill_message
                    if evasion:
                        # 스킬 쿨타임 적용
                        attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown
                        return None, result_message, critical_bool
                elif skill_name == "헤드샷":
                    skill_message, damage, critical_bool = headShot(attacker,evasion,skill_level)
                    result_message += skill_message
                    if evasion:
                        # 스킬 쿨타임 적용
                        attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown
                        apply_status_for_turn(attacker, "장전", duration=1)
                        return None, result_message, critical_bool
                elif skill_name == "명상":
                    skill_message, damage= meditate(attacker,skill_level)
                    result_message += skill_message
                elif skill_name == "타이머":
                    skill_message, damage= timer()
                    result_message += skill_message
                elif skill_name == "일섬":
                    skill_message, damage= issen(attacker,defender, skill_level)
                    result_message += skill_message
                elif skill_name == "화염 마법":
                    skill_message, damage= fire(attacker,defender, evasion,skill_level)
                    result_message += skill_message
                elif skill_name == "냉기 마법":
                    skill_message, damage= ice(attacker,defender, evasion,skill_level)
                    result_message += skill_message
                elif skill_name == "신성 마법":
                    skill_message, damage= holy(attacker,defender, evasion,skill_level)
                    result_message += skill_message
                elif skill_name == "강타":
                    skill_message, damage = smash(attacker,defender,evasion,skill_level)
                    critical_bool = True
                    result_message += skill_message
                    if evasion:
                        # 스킬 쿨타임 적용
                        critical_bool = False
                        attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown
                        return None, result_message, critical_bool 
                elif skill_name == "동상":
                    skill_message, damage= frostbite(attacker,defender,evasion,skill_level)
                    result_message += skill_message
                    if evasion:
                        # 스킬 쿨타임 적용
                        attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown
                        return None, result_message, critical_bool
                elif skill_name == "속사":
                    skill_message, damage = rapid_fire(attacker,defender,skill_level)
                    result_message += skill_message
                    total_damage += damage
                elif skill_name == '이케시아 폭우':
                    skill_message, damage = icathian_rain(attacker,defender,skill_level)
                    result_message += skill_message
                    total_damage += damage
                elif skill_name == '공허추적자':
                    skill_message, damage = voidseeker(attacker,defender,evasion,skill_level)
                    result_message += skill_message
                elif skill_name == "수확":
                    skill_message, damage = Reap(attacker,evasion,skill_level)
                    result_message += skill_message
                    if evasion:
                        # 스킬 쿨타임 적용
                        attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown
                        return None, result_message, critical_bool
                elif skill_name == "자력 발산":
                    skill_message, damage= Magnetic(attacker,defender,skill_level)
                    result_message += skill_message
                    if evasion:
                        # 스킬 쿨타임 적용
                        attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown
                        return None, result_message, critical_bool
                elif skill_name == "전선더미 방출":
                    skill_message, damage= mech_Arm(attacker,defender,evasion,skill_level)
                    result_message += skill_message
                    if evasion:
                        # 스킬 쿨타임 적용
                        attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown
                        return None, result_message, critical_bool
                elif skill_name == "전깃줄":
                    skill_message, damage= electronic_line(attacker,defender,skill_level)
                    result_message += skill_message
                    if evasion:
                        # 스킬 쿨타임 적용
                        attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown
                        return None, result_message, critical_bool
                elif skill_name == "섀도볼":
                    skill_message, damage= shadow_ball(attacker, defender, evasion, skill_level)
                    result_message += skill_message
                elif skill_name == "독찌르기":
                    skill_message, damage= poison_jab(attacker, defender, evasion, skill_level)
                    result_message += skill_message
                elif skill_name == "불꽃 펀치":
                    skill_message, damage= fire_punch(attacker, defender, evasion, skill_level)
                    result_message += skill_message
                elif skill_name == "병상첨병":
                    skill_message, damage= Hex(attacker, defender, evasion, skill_level)
                    result_message += skill_message

                if skill_name != "속사" and skill_name != "이케시아 폭우":
                    # 피해 증폭
                    damage *= 1 + attacker["DamageEnhance"]
                    # 방어력 계산 적용
                    defense = max(0, defender["Defense"] - attacker["DefenseIgnore"])
                    damage_reduction = calculate_damage_reduction(defense)
                    defend_damage = damage * (1 - damage_reduction)
                    final_damage = defend_damage * (1 - defender['DamageReduction']) # 대미지 감소 적용
                    total_damage += final_damage

                    if skill_name == "수확" and not evasion:
                        Reap_data = skill_data_firebase['수확']['values']
                        heal_multiplier = min(1, (Reap_data['기본_흡혈_비율'] + Reap_data['스킬증폭당_추가흡혈_비율'] * attacker["Spell"]))
                        real_damage = final_damage

                        if "보호막" in defender['Status']:
                            shield_amount = defender["Status"]["보호막"]["value"]
                            if shield_amount >= final_damage:
                                real_damage = 0
                            else:
                                real_damage = final_damage - shield_amount

                        heal_amount = round(real_damage * heal_multiplier)
                        # 기본 힐량과 스킬 관련 계산
                        if "치유 감소" in attacker["Status"]:
                            healban_amount = attacker['Status']['치유 감소']['value']
                            reduced_heal = round(heal_amount * healban_amount)
                        else:
                            reduced_heal = 0

                        initial_HP = attacker['HP']  # 회복 전 내구도 저장
                        attacker['HP'] += heal_amount - reduced_heal  # 힐 적용
                        attacker['HP'] = min(attacker['HP'], attacker['BaseHP'])  # 최대 내구도 이상 회복되지 않도록 제한

                        # 최종 회복된 내구도
                        final_HP = attacker['HP']
                        if "치유 감소" in attacker["Status"]:
                            result_message += f"가한 대미지의 {int(heal_multiplier * 100)}% 흡혈! (+{heal_amount}(-{reduced_heal}) 회복)\n내구도: [{initial_HP}] → [{final_HP}] ❤️ (+{final_HP - initial_HP})"
                        else:
                            result_message += f"가한 대미지의 {int(heal_multiplier * 100)}% 흡혈! (+{heal_amount} 회복)\n내구도: [{initial_HP}] → [{final_HP}] ❤️ (+{final_HP - initial_HP})"
                # 스킬 쿨타임 적용
                attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown

            return max(0, round(total_damage)), result_message, critical_bool  # 최소 0 피해

        skills_data = weapon_data_challenger.get("스킬", {})
        challenger_merged_skills = {}

        for skill_name, skill_info in skills_data.items():
            # 공통 스킬 정보에서 쿨타임 가져오기
            if simulate:
                skill_common_data = scd.get(skill_name, "")
            else:
                ref_skill = db.reference(f"무기/스킬/{skill_name}")
                skill_common_data = ref_skill.get() or {}
            # cooldown 전체 가져오기
            cooldown_data = skill_common_data.get("cooldown", {})
            total_cd = cooldown_data.get("전체 쿨타임", 0)
            current_cd = cooldown_data.get("현재 쿨타임", 0)

            # 사용자 데이터에 쿨타임 추가
            merged_skill_info = skill_info.copy()
            merged_skill_info["전체 쿨타임"] = total_cd
            merged_skill_info["현재 쿨타임"] = current_cd

            challenger_merged_skills[skill_name] = merged_skill_info
        challenger = {
            "Weapon": weapon_data_challenger.get("무기타입",""),
            "name": weapon_data_challenger.get("이름", ""),
            "BaseHP": weapon_data_challenger.get("내구도", 0),
            "HP": weapon_data_challenger.get("내구도", 0),
            "Attack": weapon_data_challenger.get("공격력", 0),
            "BaseAttack": weapon_data_challenger.get("공격력", 0),
            "Spell" : weapon_data_challenger.get("스킬 증폭", 0),
            "CritChance": weapon_data_challenger.get("치명타 확률", 0),
            "BaseCritChance" : weapon_data_challenger.get("치명타 확률", 0),
            "CritDamage": weapon_data_challenger.get("치명타 대미지", 0),
            "BaseCritDamage" : weapon_data_challenger.get("치명타 대미지", 0),
            "Speed": weapon_data_challenger.get("스피드", 0),
            "BaseSpeed": weapon_data_challenger.get("스피드", 0),
            "WeaponRange": weapon_data_challenger.get("사거리",""),
            "DefenseIgnore": 0,
            "Evasion" : 0,
            "DamageEnhance" : 0, # 피해 증폭
            "DamageReduction" : 0, # 피해 감소
            "Position" : 1,
            "Id": 0, # Id를 통해 도전자와 상대 파악 도전자 = 0, 상대 = 1
            "Accuracy": weapon_data_challenger.get("명중", 0),
            "BaseAccuracy": weapon_data_challenger.get("명중", 0),
            "Defense": weapon_data_challenger.get("방어력", 0),
            "Skills": challenger_merged_skills,
            "Status" : {}
        }
        
        skills_data = weapon_data_opponent.get("스킬", {})
        opponent_merged_skills = {}

        for skill_name, skill_info in skills_data.items():
            # 공통 스킬 정보에서 쿨타임 가져오기
            if simulate:
                skill_common_data = scd.get(skill_name)
            else:
                ref_skill = db.reference(f"무기/스킬/{skill_name}")
                skill_common_data = ref_skill.get() or {}
            # cooldown 전체 가져오기
            cooldown_data = skill_common_data.get("cooldown", {})
            total_cd = cooldown_data.get("전체 쿨타임", 0)
            current_cd = cooldown_data.get("현재 쿨타임", 0)

            # 사용자 데이터에 쿨타임 추가
            merged_skill_info = skill_info.copy()
            merged_skill_info["전체 쿨타임"] = total_cd
            merged_skill_info["현재 쿨타임"] = current_cd

            opponent_merged_skills[skill_name] = merged_skill_info

        opponent = {
            "Weapon": weapon_data_opponent.get("무기타입",""),
            "name": weapon_data_opponent.get("이름", ""),
            "FullHP": weapon_data_opponent.get("총 내구도", 0),
            "BaseHP": weapon_data_opponent.get("내구도", 0),
            "HP": weapon_data_opponent.get("총 내구도", 0) if raid and practice else weapon_data_opponent.get("내구도", 0) ,
            "Attack": weapon_data_opponent.get("공격력", 0),
            "BaseAttack": weapon_data_opponent.get("공격력", 0),
            "Spell" : weapon_data_opponent.get("스킬 증폭", 0),
            "CritChance": weapon_data_opponent.get("치명타 확률", 0),
            "BaseCritChance" : weapon_data_opponent.get("치명타 확률", 0),
            "CritDamage": weapon_data_opponent.get("치명타 대미지", 0),
            "BaseCritDamage" : weapon_data_opponent.get("치명타 대미지", 0),
            "Speed": weapon_data_opponent.get("스피드", 0),
            "BaseSpeed": weapon_data_opponent.get("스피드", 0),
            "WeaponRange": weapon_data_opponent.get("사거리",""),
            "DefenseIgnore": 0,
            "Evasion" : 0,
            "DamageEnhance" : 0,
            "DamageReduction" : 0,
            "Position" : -1,
            "Id" : 1, # Id를 통해 도전자와 상대 파악 도전자 = 0, 상대 = 1
            "Accuracy": weapon_data_opponent.get("명중", 0),
            "BaseAccuracy": weapon_data_opponent.get("명중", 0),
            "Defense": weapon_data_opponent.get("방어력", 0),
            "Skills": opponent_merged_skills,
            "Status" : {}
        }

        # 비동기 전투 시뮬레이션
        attacker, defender = random.choice([(challenger, opponent), (opponent, challenger)]) if challenger["Speed"] == opponent["Speed"] else \
                     (challenger, opponent) if challenger["Speed"] > opponent["Speed"] else \
                     (opponent, challenger)
        
        if not simulate:
            if raid:
                if practice:
                    weapon_battle_thread = await channel.create_thread(
                        name=f"{challenger_m.display_name}의 {boss} 레이드 모의전",
                        type=discord.ChannelType.public_thread
                    )
                else:
                    weapon_battle_thread = await channel.create_thread(
                        name=f"{challenger_m.display_name}의 {boss} 레이드",
                        type=discord.ChannelType.public_thread
                    )
            elif tower:
                if practice:
                    weapon_battle_thread = await channel.create_thread(
                        name=f"{challenger_m.display_name}의 타워 등반 모의전",
                        type=discord.ChannelType.public_thread
                    )
                else:
                    weapon_battle_thread = await channel.create_thread(
                        name=f"{challenger_m.display_name}의 타워 등반",
                        type=discord.ChannelType.public_thread
                    )
            else:
                weapon_battle_thread = await channel.create_thread(
                    name=f"{challenger_m.display_name} vs {opponent_m.display_name} 무기 대결",
                    type=discord.ChannelType.public_thread
                )
                
        # 비동기 전투 시뮬레이션 전에 스탯을 임베드로 전송
        embed = discord.Embed(title="⚔️ 무기 대결 시작!", color=discord.Color.green())

        # 스킬 정보 추가
        skills_message_challenger = "• 스킬: "
        skills_list_challenger = []

        # challenger['Skills']에서 모든 스킬 이름과 레벨을 가져와서 형식에 맞게 저장
        for skill_name, skill_data in challenger['Skills'].items():
            skill_level = skill_data['레벨']  # 스킬 레벨을 가져옴
            skills_list_challenger.append(f"{skill_name} Lv {skill_level}")

        # 스킬 목록을 콤마로 구분하여 메시지에 추가
        skills_message_challenger += " ".join(skills_list_challenger)

        # 스킬 정보 추가
        skills_message_opponent = "• 스킬: "
        skills_list_opponent = []

        # challenger['Skills']에서 모든 스킬 이름과 레벨을 가져와서 형식에 맞게 저장
        for skill_name, skill_data in opponent['Skills'].items():
            skill_level = skill_data['레벨']  # 스킬 레벨을 가져옴
            skills_list_opponent.append(f"{skill_name} Lv {skill_level}")

        # 스킬 목록을 콤마로 구분하여 메시지에 추가
        skills_message_opponent += " ".join(skills_list_opponent)

        # 챌린저 무기 스탯 정보 추가
        embed.add_field(name=f"[{challenger['name']}](+{weapon_data_challenger.get('강화', 0)})", value=f"""
        • 무기 타입: {challenger['Weapon']}
        • 대미지: {round(challenger['Attack'] * calculate_accuracy(challenger['Accuracy']))} ~ {challenger['Attack']}
        • 내구도: {challenger['HP']}
        • 공격력: {challenger['Attack']}
        • 스킬 증폭: {challenger['Spell']}
        • 치명타 확률: {round(challenger['CritChance'] * 100, 2)}%
        • 치명타 대미지: {round(challenger['CritDamage'] * 100, 2)}%
        • 스피드: {challenger['Speed']} (이동 확률: {round(calculate_move_chance(challenger['Speed']) * 100, 2)}%)
        • 사거리: {challenger['WeaponRange']}
        • 명중: {challenger['Accuracy']} (명중률: {round(calculate_accuracy(challenger['Accuracy']) * 100, 2)}%)
        • 방어력: {challenger['Defense']} (대미지 감소율: {round(calculate_damage_reduction(challenger['Defense']) * 100, 2)}%)
        {skills_message_challenger}
        """, inline=False)

        # 상대 무기 스탯 정보 추가
        embed.add_field(name=f"[{opponent['name']}](+{weapon_data_opponent.get('강화', 0)})", value=f"""
        • 무기 타입: {opponent['Weapon']}
        • 대미지: {round(opponent['Attack'] * calculate_accuracy(opponent['Accuracy']))} ~ {opponent['Attack']}
        • 내구도: {opponent['HP']}
        • 공격력: {opponent['Attack']}
        • 스킬 증폭: {opponent['Spell']}
        • 치명타 확률: {round(opponent['CritChance'] * 100, 2)}%
        • 치명타 대미지: {round(opponent['CritDamage'] * 100, 2)}%
        • 스피드: {opponent['Speed']} (이동 확률: {round(calculate_move_chance(opponent['Speed']) * 100, 2)}%)
        • 사거리: {opponent['WeaponRange']}
        • 명중: {opponent['Accuracy']} (명중률: {round(calculate_accuracy(opponent['Accuracy']) * 100, 2)}%)
        • 방어력: {opponent['Defense']} (대미지 감소율: {round(calculate_damage_reduction(opponent['Defense']) * 100, 2)}%)
        {skills_message_opponent}
        """, inline=False)

        if not simulate:
            await weapon_battle_thread.send(embed=embed)

        embed = discord.Embed(title="⚔️ 무기 강화 내역", color=discord.Color.green())
        
        # 챌린저 무기 스탯 정보 추가
        challenger_weapon_enhancement = ""
        for enhancement, count in weapon_data_challenger.get('강화내역', {}).items():
            challenger_weapon_enhancement += f"• {enhancement}: {count}\n"

        embed.add_field(name=f"[{challenger['name']}](+{weapon_data_challenger.get('강화', 0)})", value=f"""
        {challenger_weapon_enhancement if challenger_weapon_enhancement else "강화 내역 없음"}
        """, inline=False)

        # 상대 무기 스탯 정보 추가
        opponent_weapon_enhancement = ""
        for enhancement, count in weapon_data_opponent.get('강화내역', {}).items():
            opponent_weapon_enhancement += f"• **{enhancement}** +{count}\n"

        embed.add_field(name=f"[{opponent['name']}](+{weapon_data_opponent.get('강화', 0)})", value=f"""
        {opponent_weapon_enhancement if opponent_weapon_enhancement else "강화 내역 없음"}
        """, inline=False)

        if not simulate:
            await weapon_battle_thread.send(embed=embed)
        
        turn = 0
        if raid: # 레이드 시 처음 내구도를 저장
            first_HP = opponent['HP']
            if boss == "브라움":
                apply_status_for_turn(opponent, "불굴", 2669)
                apply_status_for_turn(opponent, "뇌진탕 펀치", 2669)
            elif boss == "카이사":
                apply_status_for_turn(opponent, "두번째 피부",2669)
            elif boss == "팬텀":
                apply_status_for_turn(opponent, "저주받은 바디", 2669)
                apply_status_for_turn(opponent, "기술 사용", 2669)
            elif boss == "허수아비":
                apply_status_for_turn(opponent, "속박", 2669)
                
        while challenger["HP"] > 0 and opponent["HP"] > 0:
            turn += 1

            if turn >= 30:
                healban_amount = round((turn - 20) * 0.01,1)
                apply_status_for_turn(attacker, "치유 감소", 100, healban_amount)
                apply_status_for_turn(defender, "치유 감소", 100, healban_amount)

            attacked = False
            # 이동 확률 계산: 스피드에 따라 증가
            move_chance = calculate_move_chance(attacker["Speed"])
            attack_range = attacker["WeaponRange"]

            if "일섬" in attacker["Status"]:
                if attacker["Status"]["일섬"]["duration"] == 1:
                    issen_data = skill_data_firebase['일섬']['values']
                    accuracy_apply_rate = round((issen_data['기본_명중_반영_비율'] + issen_data['레벨당_명중_반영_비율'] * skill_level) * 100)

                    def calculate_damage(attacker,defender,multiplier):
                        accuracy = calculate_accuracy(attacker["Accuracy"])
                        accuracy_apply_rate = issen_data['기본_명중_반영_비율'] + issen_data['레벨당_명중_반영_비율'] * skill_level
                        base_damage = random.uniform(attacker["Attack"] + (attacker["Accuracy"] * accuracy_apply_rate) * accuracy, attacker["Attack"] + (attacker["Accuracy"] * accuracy_apply_rate))  # 최소 ~ 최대 피해
                        critical_bool = False

                        # 피해 증폭
                        base_damage *= 1 + attacker["DamageEnhance"]

                        explosion_damage = 0
                        bleed_explosion = False
                        if '출혈' in defender["Status"]: # 출혈 적용상태라면
                            duration = defender["Status"]['출혈']['duration']
                            value = defender["Status"]['출혈']['value']
                            explosion_damage = (duration * value)
                            explosion_damage = round(explosion_damage)
                            base_damage += explosion_damage
                            bleed_explosion = True

                        if random.random() < attacker["CritChance"]:
                            base_damage *= attacker["CritDamage"]
                            critical_bool = True

                        fixed_damage = 0 # 출혈 상태 적용 시 고정 피해 50%
                        if '출혈' in defender["Status"]: # 출혈 적용상태라면
                            duration = defender["Status"]['출혈']['duration']
                            fixed_damage = round(base_damage / 2)
                            base_damage = fixed_damage

                        defense = max(0, (defender["Defense"] - attacker["DefenseIgnore"]))
                        damage_reduction = calculate_damage_reduction(defense)
                        defend_damage = base_damage * (1 - damage_reduction) * multiplier
                        final_damage = defend_damage * (1 - defender['DamageReduction']) + fixed_damage # 대미지 감소 적용
                        return max(1, round(final_damage)), critical_bool, explosion_damage,bleed_explosion

                    bleed_damage = issen_data['출혈_대미지'] + issen_data['레벨당_출혈_대미지'] * skill_level
                    issen_damage, critical, explosion_damage, bleed_explosion = calculate_damage(defender,attacker,1)
            
                    shield_message = ""
                    remain_shield = ""
                    if attacker['Id'] == 0: # 도전자 공격
                        battle_embed = discord.Embed(title=f"{defender['name']}의 일섬!", color=discord.Color.red())
                    elif attacker['Id'] == 1: # 상대 공격
                        battle_embed = discord.Embed(title=f"{defender['name']}의 일섬!", color=discord.Color.blue())
                    if "보호막" in attacker['Status']:
                        shield_amount = attacker["Status"]["보호막"]["value"]
                        if shield_amount >= issen_damage:
                            attacker["Status"]["보호막"]["value"] -= issen_damage
                            shield_message = f" 🛡️피해 {issen_damage} 흡수!"
                            issen_damage = 0
                        else:
                            issen_damage -= shield_amount
                            shield_message = f" 🛡️피해 {shield_amount} 흡수!"
                            attacker["Status"]["보호막"]["value"] = 0
                        if "보호막" in attacker["Status"] and attacker["Status"]["보호막"]["value"] <= 0: # 보호막이 0이 되면 삭제
                            del attacker["Status"]["보호막"]

                    if "보호막" in attacker['Status']:
                        shield_amount = attacker["Status"]["보호막"]["value"]
                        remain_shield = f"(🛡️보호막 {shield_amount})"
                    
                    battle_embed.add_field(
                        name="일섬!",
                        value=f"명중의 {accuracy_apply_rate}%를 공격력과 합산한 대미지를 입힙니다!\n",
                        inline=False
                    )
                    
                    attacker["HP"] -= issen_damage
                    crit_text = "💥" if critical else ""
                    explosion_message = ""
                    if bleed_explosion:
                        if '출혈' in attacker["Status"]:
                            del attacker["Status"]['출혈']
                        battle_embed.add_field(
                            name="추가 피해!",
                            value="출혈 상태의 적에게 추가 효과!\n남은 출혈 피해를 대미지에 합산하고, 총 피해의 50%를 고정피해로 입힙니다.",
                            inline=False
                        )
                        explosion_message = f"(+🩸{explosion_damage} 대미지)"
                    battle_embed.add_field(name ="", value = f"**{issen_damage} 대미지!{crit_text}{explosion_message}{shield_message}**",inline = False)

                    if attacker['Id'] == 0: # 도전자 공격
                        battle_embed.add_field(name = "남은 내구도", value=f"**[{attacker['HP']} / {attacker['BaseHP']}]{remain_shield}**")

                    elif attacker['Id'] == 1: # 상대 공격
                        if raid:
                            battle_embed.add_field(name = "남은 내구도", value=f"**[{attacker['HP']} / {attacker['FullHP']}]{remain_shield}**")
                        else:
                            battle_embed.add_field(name = "남은 내구도", value=f"**[{attacker['HP']} / {attacker['BaseHP']}]{remain_shield}**")

                    if attacker["HP"] <= 0:
                        result = await end(attacker,defender,"defender",raid,simulate,winner_id = defender['Id'])
                        if simulate:
                            return result
                        break
                    else:
                        if not simulate:
                            await weapon_battle_thread.send(embed = battle_embed)

            if "출혈" in attacker["Status"]:
                bleed_damage = attacker["Status"]["출혈"]["value"]
                shield_message = ""
                remain_shield = ""
                if attacker['Id'] == 0: # 도전자 공격
                    battle_embed = discord.Embed(title=f"{attacker['name']}의 출혈!🩸", color=discord.Color.red())
                elif attacker['Id'] == 1: # 상대 공격
                    battle_embed = discord.Embed(title=f"{attacker['name']}의 출혈!🩸", color=discord.Color.blue())
                if "보호막" in attacker['Status']:
                    shield_amount = attacker["Status"]["보호막"]["value"]
                    if shield_amount >= bleed_damage:
                        attacker["Status"]["보호막"]["value"] -= bleed_damage
                        shield_message = f" 🛡️피해 {bleed_damage} 흡수!"
                        bleed_damage = 0
                    else:
                        bleed_damage -= shield_amount
                        shield_message = f" 🛡️피해 {shield_amount} 흡수!"
                        attacker["Status"]["보호막"]["value"] = 0
                    if "보호막" in attacker["Status"] and attacker["Status"]["보호막"]["value"] <= 0: # 보호막이 0이 되면 삭제
                        del attacker["Status"]["보호막"]

                if "보호막" in attacker['Status']:
                    shield_amount = attacker["Status"]["보호막"]["value"]
                    remain_shield = f"(🛡️보호막 {shield_amount})"
                    
                attacker["HP"] -= bleed_damage
                battle_embed.add_field(name="", value = f"출혈 상태로 인하여 {bleed_damage} 대미지를 받았습니다!{shield_message}", inline = False)
                battle_embed.add_field(name="남은 턴", value = f"출혈 상태 남은 턴 : {attacker['Status']['출혈']['duration']}", inline = False)

                if attacker['Id'] == 0: # 도전자 공격
                    battle_embed.add_field(name = "남은 내구도", value=f"**[{attacker['HP']} / {attacker['BaseHP']}]{remain_shield}**")

                elif attacker['Id'] == 1: # 상대 공격
                    if raid:
                        battle_embed.add_field(name = "남은 내구도", value=f"**[{attacker['HP']} / {attacker['FullHP']}]{remain_shield}**")
                    else:
                        battle_embed.add_field(name = "남은 내구도", value=f"**[{attacker['HP']} / {attacker['BaseHP']}]{remain_shield}**")

                if attacker["HP"] <= 0:
                    result = await end(attacker,defender,"defender",raid,simulate,winner_id = defender['Id'])
                    if simulate:
                        return result
                    break
                else:
                    if not simulate:
                        await weapon_battle_thread.send(embed = battle_embed)

            if "화상" in attacker["Status"]:
                burn_damage = attacker["Status"]["화상"]["value"]
                shield_message = ""
                remain_shield = ""
                if attacker['Id'] == 0: # 도전자 공격
                    battle_embed = discord.Embed(title=f"{attacker['name']}의 화상!🔥", color=discord.Color.red())
                elif attacker['Id'] == 1: # 상대 공격
                    battle_embed = discord.Embed(title=f"{attacker['name']}의 화상!🔥", color=discord.Color.blue())
                if "보호막" in attacker['Status']:
                    shield_amount = attacker["Status"]["보호막"]["value"]
                    if shield_amount >= burn_damage:
                        attacker["Status"]["보호막"]["value"] -= burn_damage
                        shield_message = f" 🛡️피해 {burn_damage} 흡수!"
                        burn_damage = 0
                    else:
                        burn_damage -= shield_amount
                        shield_message = f" 🛡️피해 {burn_damage} 흡수!"
                        attacker["Status"]["보호막"]["value"] = 0
                    if "보호막" in attacker["Status"] and attacker["Status"]["보호막"]["value"] <= 0: # 보호막이 0이 되면 삭제
                        del attacker["Status"]["보호막"]

                if "보호막" in attacker['Status']:
                    shield_amount = attacker["Status"]["보호막"]["value"]
                    remain_shield = f"(🛡️보호막 {shield_amount})"
                    
                attacker["HP"] -= burn_damage
                battle_embed.add_field(name="", value = f"화상 상태로 인하여 {burn_damage} 대미지를 받았습니다!{shield_message}", inline = False)
                battle_embed.add_field(name="남은 턴", value = f"화상 상태 남은 턴 : {attacker['Status']['화상']['duration']}", inline = False)

                if attacker['Id'] == 0: # 도전자 공격
                    battle_embed.add_field(name = "남은 내구도", value=f"**[{attacker['HP']} / {attacker['BaseHP']}]{remain_shield}**")

                elif attacker['Id'] == 1: # 상대 공격
                    if raid:
                        battle_embed.add_field(name = "남은 내구도", value=f"**[{attacker['HP']} / {attacker['FullHP']}]{remain_shield}**")
                    else:
                        battle_embed.add_field(name = "남은 내구도", value=f"**[{attacker['HP']} / {attacker['BaseHP']}]{remain_shield}**")

                if attacker["HP"] <= 0:
                    result = await end(attacker,defender,"defender",raid,simulate,winner_id = defender['Id'])
                    if simulate:
                        return result
                    break
                else:
                    if not simulate:
                        await weapon_battle_thread.send(embed = battle_embed)

            if "독" in attacker["Status"]:
                posion_damage = round(attacker['HP'] / 16)
                shield_message = ""
                remain_shield = ""
                if attacker['Id'] == 0: # 도전자 공격
                    battle_embed = discord.Embed(title=f"{attacker['name']}의 독!🫧", color=discord.Color.red())
                elif attacker['Id'] == 1: # 상대 공격
                    battle_embed = discord.Embed(title=f"{attacker['name']}의 독!🫧", color=discord.Color.blue())
    
                    
                attacker["HP"] -= posion_damage
                battle_embed.add_field(name="", value = f"독 상태로 인하여 {posion_damage} 대미지를 받았습니다!{shield_message}", inline = False)
                battle_embed.add_field(name="남은 턴", value = f"독 상태 남은 턴 : {attacker['Status']['독']['duration']}", inline = False)

                if attacker['Id'] == 0: # 도전자 공격
                    battle_embed.add_field(name = "남은 내구도", value=f"**[{attacker['HP']} / {attacker['BaseHP']}]{remain_shield}**")

                elif attacker['Id'] == 1: # 상대 공격
                    if raid:
                        battle_embed.add_field(name = "남은 내구도", value=f"**[{attacker['HP']} / {attacker['FullHP']}]{remain_shield}**")
                    else:
                        battle_embed.add_field(name = "남은 내구도", value=f"**[{attacker['HP']} / {attacker['BaseHP']}]{remain_shield}**")

                if attacker["HP"] <= 0:
                    result = await end(attacker,defender,"defender",raid,simulate,winner_id = defender['Id'])
                    if simulate:
                        return result
                    break
                else:
                    if not simulate:
                        await weapon_battle_thread.send(embed = battle_embed)

            if "기절" in attacker["Status"]: # 기절 상태일 경우 바로 턴을 넘김
                # 공격자와 방어자 변경
                battle_embed = discord.Embed(title=f"{attacker['name']}의 턴!⚔️", color=discord.Color.blue())
                battle_embed.add_field(name="행동 불가!", value = f"기절 상태이상으로 인해 행동할 수 없습니다!\n기절 상태 남은 턴 : {attacker['Status']['기절']['duration']}", inline = False)
                if "장전" in attacker["Status"]:  # 장전이 있는지 확인
                    attacker["Status"]["장전"]["duration"] += 1
                remove_status_effects(attacker)
                update_status(attacker)  # 공격자의 상태 업데이트 (은신 등)
                attacker, defender = defender, attacker
                if not simulate:
                    await weapon_battle_thread.send(embed = battle_embed)
                    if turn >= 30:
                        await asyncio.sleep(1)
                    else:
                        await asyncio.sleep(2)  # 턴 간 딜레이
                continue
                    
            if "빙결" in attacker["Status"]: # 빙결 상태일 경우 바로 턴을 넘김
                # 공격자와 방어자 변경
                battle_embed = discord.Embed(title=f"{attacker['name']}의 턴!⚔️", color=discord.Color.blue())
                battle_embed.add_field(name="행동 불가!", value = f"빙결 상태이상으로 인해 행동할 수 없습니다!❄️\n빙결 상태 남은 턴 : {attacker['Status']['빙결']['duration']}", inline = False)
                if "장전" in attacker["Status"]:  # 장전이 있는지 확인
                    attacker["Status"]["장전"]["duration"] += 1
                remove_status_effects(attacker)
                update_status(attacker)  # 공격자의 상태 업데이트 (은신 등)
                attacker, defender = defender, attacker
                if not simulate:
                    await weapon_battle_thread.send(embed = battle_embed)
                    if turn >= 30:
                        await asyncio.sleep(1)
                    else:
                        await asyncio.sleep(2)  # 턴 간 딜레이
                continue

            # 가속 확률 계산 (스피드 5당 1% 확률)
            speed = attacker.get("Speed", 0)
            acceleration_chance = speed // 5  # 예: 스피드 50이면 10% 확률

            skill_names = list(attacker["Skills"].keys())
            used_skill = []
            skill_attack_names = []
            result_message = ""
            cooldown_message = ""
            for skill, cooldown_data in attacker["Skills"].items():
                if acceleration_chance > 0 and random.randint(1, 100) <= acceleration_chance and attacker["Skills"][skill]["현재 쿨타임"] != 0:
                    attacker["Skills"][skill]["현재 쿨타임"] -= 1  # 추가 1 감소
                    if attacker["Skills"][skill]["현재 쿨타임"] < 0:
                        attacker["Skills"][skill]["현재 쿨타임"] = 0
                    if skill == "헤드샷":
                        if "장전" in attacker["Status"]:  # 장전이 있는지 확인
                            attacker["Status"]["장전"]["duration"] -= 1
                            if attacker["Status"]["장전"]["duration"] <= 0:
                                del attacker["Status"]["장전"]
                    result_message += f"💨 {attacker['name']}의 가속! {skill}의 쿨타임이 추가로 감소했습니다!\n"
            
            slienced = False
            if '침묵' in attacker['Status']:
                slienced = True

            if "기술 사용" in attacker['Status']:
                if slienced:
                    result_message += f"침묵 상태로 인하여 스킬 사용 불가!\n"
                else:
                    # 거리별 스킬 목록
                    if battle_distance <= 1:
                        skills = ['섀도볼', '독찌르기', '불꽃 펀치', '병상첨병']
                    elif battle_distance <= 2:
                        skills = ['불꽃 펀치', '섀도볼', '병상첨병']
                    elif battle_distance <= 3:
                        skills = ['섀도볼', '독찌르기', '병상첨병']
                    else:  # 4 이상
                        skills = ['독찌르기', '병상첨병']
                    
                    cc_status = ['빙결', '화상', '침묵', '기절', '속박', '독', '둔화']
                    if any(status in cc_status for status in defender['Status']): # 상태이상 적용상태라면
                        skill_name = '병상첨병'
                    else:
                        skill_name = random.choice(skills)
                    used_skill.append(skill_name)
                    skill_attack_names.append(skill_name)

            if "자력 발산" in skill_names:
                skill_name = "자력 발산"
                skill_cooldown_current = attacker["Skills"][skill_name]["현재 쿨타임"]
                skill_cooldown_total = attacker["Skills"][skill_name]["전체 쿨타임"]
                skill_level = attacker["Skills"][skill_name]["레벨"]

                if skill_cooldown_current == 0:
                    if skill_name in skill_names:
                        used_skill.append(skill_name)
                        skill_attack_names.append(skill_name)
                else:
                    cooldown_message += f"⌛{skill_name}의 남은 쿨타임 : {skill_cooldown_current}턴\n"
                    
            dash, retreat, attacked = False, False, False

            # 돌진 및 후퇴 방향 설정
            dash_direction = -1 if attacker['Id'] == 0 else 1  
            retreat_direction = 1 if attacker['Id'] == 0 else -1  

            if battle_distance > attack_range:  # 돌진
                if random.random() < move_chance and "속박" not in attacker["Status"]:  
                    move_distance = 2 if ("기습" in attacker['Status']) else 1
                    if battle_distance == 2:
                        move_distance = 1
                    attacker["Position"] = adjust_position(attacker["Position"], move_distance, dash_direction)
                    if (attacker["Position"] < 0 and defender["Position"] > 0) or (attacker["Position"] > 0 and defender["Position"] < 0):
                        battle_distance = abs(attacker["Position"] - defender["Position"]) - 1  # 0을 건너뛰므로 -1
                    else:
                        battle_distance = abs(attacker["Position"] - defender["Position"])  # 같은 방향이면 그대로 계산
                    dash = True

                    if battle_distance <= attack_range:
                        attacked = True

            elif battle_distance < attack_range:  # 후퇴
                if random.random() < move_chance and "속박" not in attacker["Status"]:
                    move_distance = 1
                    attacker["Position"] = adjust_position(attacker["Position"], move_distance, retreat_direction)
                    if (attacker["Position"] < 0 and defender["Position"] > 0) or (attacker["Position"] > 0 and defender["Position"] < 0):
                        battle_distance = abs(attacker["Position"] - defender["Position"]) - 1  # 0을 건너뛰므로 -1
                    else:
                        battle_distance = abs(attacker["Position"] - defender["Position"])  # 같은 방향이면 그대로 계산
                    retreat = True
                else:
                    retreat = False
                attacked = True

            else:  # 거리 유지 후 공격
                attacked = True
           

            if "기습" in skill_names:
                skill_name = "기습"
                skill_cooldown_current = attacker["Skills"][skill_name]["현재 쿨타임"]
                skill_cooldown_total = attacker["Skills"][skill_name]["전체 쿨타임"]
                skill_level = attacker["Skills"][skill_name]["레벨"]

                if skill_cooldown_current == 0:
                    if slienced: # 침묵 상태일 경우
                        result_message += f"침묵 상태로 인하여 {skill_name}스킬 사용 불가!\n"
                    else:
                        attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown_total
                        result_message += invisibility(attacker,skill_level)
                        used_skill.append(skill_name)
                else:
                    cooldown_message += f"⏳{skill_name}의 남은 쿨타임 : {skill_cooldown_current}턴\n"

            evasion = False # 회피
            

            distance_evasion = calculate_evasion(battle_distance) # 거리 2부터 1당 10%씩 빗나갈 확률 추가
            accuracy = calculate_accuracy(attacker["Accuracy"]) # 1 - 명중률 수치만큼 빗나갈 확률 상쇄 가능
            if random.random() < (defender["Evasion"] + distance_evasion) * (1 - accuracy): # 회피
                evasion = True

            reloading = False
            if "장전" in attacker['Status']: 
                result_message += f"장전 중! ({attacker['Status']['장전']['duration']}턴 남음!)\n"
                # 장전 상태일 경우 공격 불가
                reloading = True
            
            battle_embed = discord.Embed(title=f"{attacker['name']}의 공격!⚔️", color=discord.Color.blue())

            if "차징샷" in skill_names:
                skill_name = "차징샷"
                skill_cooldown_current = attacker["Skills"][skill_name]["현재 쿨타임"]
                skill_cooldown_total = attacker["Skills"][skill_name]["전체 쿨타임"]
                skill_level = attacker["Skills"][skill_name]["레벨"]

                if skill_cooldown_current == 0:
                    if slienced: # 침묵 상태일 경우
                        result_message += f"침묵 상태로 인하여 {skill_name}스킬 사용 불가!\n"
                    else:
                        attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown_total
                        if "차징샷" in skill_names:
                            result_message += charging_shot(attacker,defender,evasion,skill_level)
                            used_skill.append(skill_name)
                else:
                    cooldown_message += f"⏳{skill_name}의 남은 쿨타임 : {skill_cooldown_current}턴\n"

            if "강타" in skill_names:
                skill_name = "강타"
                skill_cooldown_current = attacker["Skills"][skill_name]["현재 쿨타임"]
                skill_cooldown_total = attacker["Skills"][skill_name]["전체 쿨타임"]
                skill_level = attacker["Skills"][skill_name]["레벨"]

                if skill_cooldown_current == 0:
                    if slienced: # 침묵 상태일 경우
                        result_message += f"침묵 상태로 인하여 {skill_name}스킬 사용 불가!\n"
                    else:
                        if skill_name in skill_names:
                            used_skill.append(skill_name)
                            skill_attack_names.append(skill_name)
                else:
                    cooldown_message += f"⏳{skill_name}의 남은 쿨타임 : {skill_cooldown_current}턴\n"

            if "타이머" in skill_names:
                skill_name = "타이머"
                skill_cooldown_current = attacker["Skills"][skill_name]["현재 쿨타임"]
                skill_cooldown_total = attacker["Skills"][skill_name]["전체 쿨타임"]
                skill_level = attacker["Skills"][skill_name]["레벨"]

                if skill_cooldown_current == 0:
                    if skill_name in skill_names:
                        used_skill.append(skill_name)
                        skill_attack_names.append(skill_name)
                else:
                    cooldown_message += f"⏳{skill_name}의 남은 쿨타임 : {skill_cooldown_current}턴\n"

            if "일섬" in skill_names:
                skill_name = "일섬"
                skill_cooldown_current = attacker["Skills"][skill_name]["현재 쿨타임"]
                skill_cooldown_total = attacker["Skills"][skill_name]["전체 쿨타임"]
                skill_level = attacker["Skills"][skill_name]["레벨"]

                if skill_cooldown_current == 0:
                    if slienced: # 침묵 상태일 경우
                        result_message += f"침묵 상태로 인하여 {skill_name}스킬 사용 불가!\n"
                    else:
                        if skill_name in skill_names:
                            used_skill.append(skill_name)
                            skill_attack_names.append(skill_name)
                else:
                    cooldown_message += f"⏳{skill_name}의 남은 쿨타임 : {skill_cooldown_current}턴\n"

            if "보호막" in skill_names:
                skill_name = "보호막"
                skill_cooldown_current = attacker["Skills"][skill_name]["현재 쿨타임"]
                skill_cooldown_total = attacker["Skills"][skill_name]["전체 쿨타임"]
                skill_level = attacker["Skills"][skill_name]["레벨"]

                if skill_cooldown_current == 0:
                    if slienced: # 침묵 상태일 경우
                        result_message += f"침묵 상태로 인하여 {skill_name}스킬 사용 불가!\n"
                    else:
                        attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown_total
                        if "보호막" in skill_names:
                            result_message += Shield(attacker,skill_level)
                            used_skill.append(skill_name)
                else:
                    cooldown_message += f"⏳{skill_name}의 남은 쿨타임 : {skill_cooldown_current}턴\n"

            if "고속충전" in skill_names:
                skill_name = "고속충전"
                skill_cooldown_current = attacker["Skills"][skill_name]["현재 쿨타임"]
                skill_cooldown_total = attacker["Skills"][skill_name]["전체 쿨타임"]
                skill_level = attacker["Skills"][skill_name]["레벨"]

                if skill_cooldown_current == 0:
                    if slienced: # 침묵 상태일 경우
                        result_message += f"침묵 상태로 인하여 {skill_name}스킬 사용 불가!\n"
                    else:
                        attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown_total
                        if "고속충전" in skill_names:
                            result_message += supercharger(attacker,skill_level)
                            used_skill.append(skill_name)
                else:
                    cooldown_message += f"⏳{skill_name}의 남은 쿨타임 : {skill_cooldown_current}턴\n"

            if "수확" in skill_names:
                skill_name = "수확"
                skill_cooldown_current = attacker["Skills"][skill_name]["현재 쿨타임"]
                skill_cooldown_total = attacker["Skills"][skill_name]["전체 쿨타임"]
                skill_level = attacker["Skills"][skill_name]["레벨"]

                if skill_cooldown_current == 0:
                    if slienced: # 침묵 상태일 경우
                        result_message += f"침묵 상태로 인하여 {skill_name}스킬 사용 불가!\n"
                    else:
                        if skill_name in skill_names:
                            used_skill.append(skill_name)
                            skill_attack_names.append(skill_name)
                else:
                    cooldown_message += f"⏳{skill_name}의 남은 쿨타임 : {skill_cooldown_current}턴\n"

            if "명상" in skill_names:
                skill_name = "명상"
                skill_cooldown_current = attacker["Skills"][skill_name]["현재 쿨타임"]
                skill_cooldown_total = attacker["Skills"][skill_name]["전체 쿨타임"]
                skill_level = attacker["Skills"][skill_name]["레벨"]

                if skill_cooldown_current == 0:
                    if slienced: # 침묵 상태일 경우
                        result_message += f"침묵 상태로 인하여 {skill_name}스킬 사용 불가!\n"
                    else:
                        if skill_name in skill_names:
                            used_skill.append(skill_name)
                            skill_attack_names.append(skill_name)
                else:
                    cooldown_message += f"⏳{skill_name}의 남은 쿨타임 : {skill_cooldown_current}턴\n"

            if "화염 마법" in skill_names:
                skill_name = "화염 마법"
                skill_cooldown_current = attacker["Skills"][skill_name]["현재 쿨타임"]
                skill_cooldown_total = attacker["Skills"][skill_name]["전체 쿨타임"]
                skill_level = attacker["Skills"][skill_name]["레벨"]

                if skill_cooldown_current == 0:
                    if slienced: # 침묵 상태일 경우
                        result_message += f"침묵 상태로 인하여 {skill_name}스킬 사용 불가!\n"
                    else:
                        if skill_name in skill_names:
                            used_skill.append(skill_name)
                            skill_attack_names.append(skill_name)
                else:
                    cooldown_message += f"⏳{skill_name}의 남은 쿨타임 : {skill_cooldown_current}턴\n"

            if "냉기 마법" in skill_names:
                skill_name = "냉기 마법"
                skill_cooldown_current = attacker["Skills"][skill_name]["현재 쿨타임"]
                skill_cooldown_total = attacker["Skills"][skill_name]["전체 쿨타임"]
                skill_level = attacker["Skills"][skill_name]["레벨"]

                if skill_cooldown_current == 0:
                    if slienced: # 침묵 상태일 경우
                        result_message += f"침묵 상태로 인하여 {skill_name}스킬 사용 불가!\n"
                    else:
                        if skill_name in skill_names:
                            used_skill.append(skill_name)
                            skill_attack_names.append(skill_name)
                else:
                    cooldown_message += f"⏳{skill_name}의 남은 쿨타임 : {skill_cooldown_current}턴\n"
            
            if "신성 마법" in skill_names:
                skill_name = "신성 마법"
                skill_cooldown_current = attacker["Skills"][skill_name]["현재 쿨타임"]
                skill_cooldown_total = attacker["Skills"][skill_name]["전체 쿨타임"]
                skill_level = attacker["Skills"][skill_name]["레벨"]

                if skill_cooldown_current == 0:
                    if slienced: # 침묵 상태일 경우
                        result_message += f"침묵 상태로 인하여 {skill_name}스킬 사용 불가!\n"
                    else:
                        if skill_name in skill_names:
                            used_skill.append(skill_name)
                            skill_attack_names.append(skill_name)
                else:
                    cooldown_message += f"⏳{skill_name}의 남은 쿨타임 : {skill_cooldown_current}턴\n"

            if "공허추적자" in skill_names:
                skill_name = "공허추적자"
                skill_cooldown_current = attacker["Skills"][skill_name]["현재 쿨타임"]
                skill_cooldown_total = attacker["Skills"][skill_name]["전체 쿨타임"]
                skill_level = attacker["Skills"][skill_name]["레벨"]

                if skill_cooldown_current == 0:
                    if slienced: # 침묵 상태일 경우
                        result_message += f"침묵 상태로 인하여 {skill_name}스킬 사용 불가!\n"
                    else:
                        if skill_name in skill_names:
                            used_skill.append(skill_name)
                            skill_attack_names.append(skill_name)
                else:
                    cooldown_message += f"⏳{skill_name}의 남은 쿨타임 : {skill_cooldown_current}턴\n"

            if "이케시아 폭우" in skill_names:
                skill_name = "이케시아 폭우"
                skill_cooldown_current = attacker["Skills"][skill_name]["현재 쿨타임"]
                skill_cooldown_total = attacker["Skills"][skill_name]["전체 쿨타임"]
                skill_level = attacker["Skills"][skill_name]["레벨"]

                if skill_cooldown_current == 0:
                    if slienced: # 침묵 상태일 경우
                        result_message += f"침묵 상태로 인하여 {skill_name}스킬 사용 불가!\n"
                    else:
                        if skill_name in skill_names:
                            used_skill.append(skill_name)
                            skill_attack_names.append(skill_name)
                else:
                    cooldown_message += f"⏳{skill_name}의 남은 쿨타임 : {skill_cooldown_current}턴\n"

            if "사냥본능" in skill_names:
                skill_name = "사냥본능"
                skill_cooldown_current = attacker["Skills"][skill_name]["현재 쿨타임"]
                skill_cooldown_total = attacker["Skills"][skill_name]["전체 쿨타임"]
                skill_level = attacker["Skills"][skill_name]["레벨"]

                if skill_cooldown_current == 0:
                    if slienced: # 침묵 상태일 경우
                        result_message += f"침묵 상태로 인하여 {skill_name}스킬 사용 불가!\n"
                    else:
                        attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown_total
                        if "사냥본능" in skill_names:
                            result_message += killer_instinct(attacker,defender,skill_level)
                            used_skill.append(skill_name)
                else:
                    cooldown_message += f"⏳{skill_name}의 남은 쿨타임 : {skill_cooldown_current}턴\n"

            if "헤드샷" in skill_names:
                skill_name = "헤드샷"
                skill_cooldown_current = attacker["Skills"][skill_name]["현재 쿨타임"]
                skill_cooldown_total = attacker["Skills"][skill_name]["전체 쿨타임"]
                skill_level = attacker["Skills"][skill_name]["레벨"]

                if skill_cooldown_current == 0:
                    if slienced: # 침묵 상태일 경우
                        result_message += f"침묵 상태로 인하여 {skill_name}스킬 사용 불가!\n"
                    else:
                        if skill_name in skill_names:
                            used_skill.append(skill_name)
                            skill_attack_names.append(skill_name)
                else:
                    cooldown_message += f"⏳{skill_name}의 남은 쿨타임 : {skill_cooldown_current}턴\n"

            if "창격" in skill_names:
                skill_name = "창격"
                skill_cooldown_current = attacker["Skills"][skill_name]["현재 쿨타임"]
                skill_cooldown_total = attacker["Skills"][skill_name]["전체 쿨타임"]
                skill_level = attacker["Skills"][skill_name]["레벨"]

                if skill_cooldown_current == 0:
                    if slienced: # 침묵 상태일 경우
                        result_message += f"침묵 상태로 인하여 {skill_name}스킬 사용 불가!\n"
                    else:
                        attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown_total
                        if "창격" in skill_names:
                            result_message += spearShot(attacker,defender,evasion,skill_level)
                            used_skill.append(skill_name)
                else:
                    cooldown_message += f"⏳{skill_name}의 남은 쿨타임 : {skill_cooldown_current}턴\n"
     
            if "동상" in skill_names:
                skill_name = "동상"
                skill_cooldown_current = attacker["Skills"][skill_name]["현재 쿨타임"]
                skill_cooldown_total = attacker["Skills"][skill_name]["전체 쿨타임"]
                skill_level = attacker["Skills"][skill_name]["레벨"]

                if skill_cooldown_current == 0:
                    if slienced: # 침묵 상태일 경우
                        result_message += f"침묵 상태로 인하여 {skill_name}스킬 사용 불가!\n"
                    else:
                        if skill_name in skill_names:
                            used_skill.append(skill_name)
                            skill_attack_names.append(skill_name)
                else:
                    cooldown_message += f"⏳{skill_name}의 남은 쿨타임 : {skill_cooldown_current}턴\n"

            if "빙하 균열" in skill_names:
                skill_name = "빙하 균열"
                skill_cooldown_current = attacker["Skills"][skill_name]["현재 쿨타임"]
                skill_cooldown_total = attacker["Skills"][skill_name]["전체 쿨타임"]
                skill_level = attacker["Skills"][skill_name]["레벨"]

                if skill_cooldown_current == 0:
                    if slienced: # 침묵 상태일 경우
                        result_message += f"침묵 상태로 인하여 {skill_name}스킬 사용 불가!\n"
                    else:
                        if skill_name in skill_names:
                            used_skill.append(skill_name)
                            skill_attack_names.append(skill_name)
                else:
                    cooldown_message += f"⏳{skill_name}의 남은 쿨타임 : {skill_cooldown_current}턴\n"

            if "속사" in skill_names:
                skill_name = "속사"
                skill_cooldown_current = attacker["Skills"][skill_name]["현재 쿨타임"]
                skill_cooldown_total = attacker["Skills"][skill_name]["전체 쿨타임"]
                skill_level = attacker["Skills"][skill_name]["레벨"]

                if skill_cooldown_current == 0:
                    if slienced: # 침묵 상태일 경우
                        result_message += f"침묵 상태로 인하여 {skill_name}스킬 사용 불가!\n"
                    else:
                        if skill_name in skill_names:
                            used_skill.append(skill_name)
                            skill_attack_names.append(skill_name)
                else:
                    cooldown_message += f"⏳{skill_name}의 남은 쿨타임 : {skill_cooldown_current}턴\n"
                            
            if "전선더미 방출" in skill_names:
                skill_name = "전선더미 방출"
                skill_cooldown_current = attacker["Skills"][skill_name]["현재 쿨타임"]
                skill_cooldown_total = attacker["Skills"][skill_name]["전체 쿨타임"]
                skill_level = attacker["Skills"][skill_name]["레벨"]

                if skill_cooldown_current == 0:
                    if slienced: # 침묵 상태일 경우
                        result_message += f"침묵 상태로 인하여 {skill_name}스킬 사용 불가!\n"
                    else:
                        if skill_name in skill_names:
                            used_skill.append(skill_name)
                            skill_attack_names.append(skill_name)
                else:
                    cooldown_message += f"⏳{skill_name}의 남은 쿨타임 : {skill_cooldown_current}턴\n"

            if "전깃줄" in skill_names:
                skill_name = "전깃줄"
                skill_cooldown_current = attacker["Skills"][skill_name]["현재 쿨타임"]
                skill_cooldown_total = attacker["Skills"][skill_name]["전체 쿨타임"]
                skill_level = attacker["Skills"][skill_name]["레벨"]

                if skill_cooldown_current == 0:
                    if slienced: # 침묵 상태일 경우
                        result_message += f"침묵 상태로 인하여 {skill_name}스킬 사용 불가!\n"
                    else:
                        if skill_name in skill_names:
                            used_skill.append(skill_name)
                            skill_attack_names.append(skill_name)
                else:
                    cooldown_message += f"⏳{skill_name}의 남은 쿨타임 : {skill_cooldown_current}턴\n"

            if "기습" in attacker["Status"]: # 은신 상태일 경우, 추가 대미지 + 일정 확률로 '출혈' 상태 부여
                skill_level = attacker["Skills"]["기습"]["레벨"]
                invisibility_data = skill_data_firebase['기습']['values']
                DefenseIgnore_increase = skill_level * invisibility_data['은신공격_레벨당_방관_증가']
                bleed_chance = invisibility_data['은신공격_레벨당_출혈_확률'] * skill_level
                bleed_damage = invisibility_data['은신공격_출혈_기본_지속피해'] + skill_level * invisibility_data['은신공격_출혈_레벨당_지속피해']
                if random.random() < bleed_chance and not evasion and attacked: # 출혈 부여
                    bleed_turns = invisibility_data['은신공격_출혈_지속시간']
                    apply_status_for_turn(defender, "출혈", duration=bleed_turns, value = bleed_damage)
                    result_message +=f"\n**🩸{attacker['name']}의 기습**!\n{bleed_turns}턴간 출혈 상태 부여!\n"   
                result_message +=f"\n**{attacker['name']}의 기습**!\n방어력 관통 + {DefenseIgnore_increase}!\n{round(invisibility_data['은신공격_레벨당_피해_배율'] * skill_level * 100)}% 추가 대미지!\n"

            if attacked: #공격 시 방어자가 '불굴' 상태라면 대미지 감소
                if "불굴" in defender["Status"]:
                    if not evasion:
                        skill_level = defender["Skills"]["불굴"]["레벨"]
                        result_message += unyielding(defender, skill_level)

                if "뇌진탕 펀치" in attacker["Status"]:
                    if not skill_attack_names:
                        if not evasion:
                            result_message += concussion_punch(defender)

                if "두번째 피부" in attacker["Status"]:
                    skill_name = "두번째 피부"
                    if not skill_attack_names:
                        if not evasion:
                            used_skill.append(skill_name)

                if "저주받은 바디" in defender["Status"]:
                    if not evasion:
                        skill_level = defender["Skills"]["저주받은 바디"]["레벨"]
                        result_message += cursed_body(attacker, skill_level)

                if "일섬" in skill_names:
                    if not evasion:
                        bleed_rate = calculate_accuracy(attacker['Accuracy'])
                        if random.random() < bleed_rate:
                            issen_data = skill_data_firebase['일섬']['values']
                            skill_level = attacker["Skills"]["일섬"]["레벨"]
                            bleed_damage = issen_data['출혈_대미지'] + issen_data['레벨당_출혈_대미지'] * skill_level
                            if '출혈' in defender['Status']:
                                apply_status_for_turn(defender, "출혈", 3, bleed_damage)
                                battle_embed.add_field(name ="출혈!", value = f"출혈 상태에서 공격 적중으로 3턴간 **출혈** 부여!🩸",inline = False)
                            else:
                                apply_status_for_turn(defender, "출혈", 2, bleed_damage)
                                battle_embed.add_field(name ="출혈!", value = f"공격 적중으로 2턴간 **출혈** 부여!🩸",inline = False)

            if skill_attack_names or attacked: # 공격시 상대의 빙결 상태 해제
                if skill_attack_names != ['명상'] and not evasion: # 명상만 썼을 경우, 회피했을 경우 제외!
                    if '빙결' in defender['Status']:
                        del defender['Status']['빙결']
                        battle_embed.add_field(name="❄️빙결 상태 해제!", value = f"공격을 받아 빙결 상태가 해제되었습니다!\n")

            # 공격 처리 (돌진 후 또는 후퇴 후)
            if skill_attack_names: # 공격 스킬 사용 시
                battle_embed.title = f"{attacker['name']}의 스킬 사용!⚔️"
                if attacker['Id'] == 0: # 도전자 공격
                    battle_embed.color = discord.Color.blue()
                elif attacker['Id'] == 1: # 상대 공격
                    battle_embed.color = discord.Color.red()
                battle_embed.add_field(name="위치", value =f"{challenger['name']} 위치: {challenger['Position']}, {opponent['name']} 위치: {opponent['Position']}", inline = False) 
                battle_embed.add_field(name="거리", value = f"현재 거리 : {battle_distance}", inline = False)
                if dash:
                    battle_embed.add_field(name="돌진!", value = f"{attacker['name']}의 돌진! 거리가 {move_distance}만큼 줄어듭니다!", inline = False)
                elif retreat:
                    battle_embed.add_field(name="후퇴!", value = f"{attacker['name']}의 후퇴! 거리가 {move_distance}만큼 늘어납니다!", inline = False)
                damage, critical, dist, evade, skill_message = await attack(attacker, defender, evasion, reloading, skill_attack_names)
                result_message += skill_message
            elif attacked: # 공격 시
                battle_embed.title = f"{attacker['name']}의 공격!⚔️"
                if attacker['Id'] == 0: # 도전자 공격
                    battle_embed.color = discord.Color.blue()
                elif attacker['Id'] == 1: # 상대 공격
                    battle_embed.color = discord.Color.red() 
                battle_embed.add_field(name="위치", value =f"{challenger['name']} 위치: {challenger['Position']}, {opponent['name']} 위치: {opponent['Position']}", inline = False) 
                battle_embed.add_field(name="거리", value = f"현재 거리 : {battle_distance}", inline = False)
                if dash:
                    battle_embed.add_field(name="돌진!", value = f"{attacker['name']}의 돌진! 거리가 {move_distance}만큼 줄어듭니다!", inline = False)
                elif retreat:
                    battle_embed.add_field(name="후퇴!", value = f"{attacker['name']}의 후퇴! 거리가 {move_distance}만큼 늘어납니다!", inline = False)
                damage, critical, dist, evade, skill_message = await attack(attacker, defender, evasion, reloading, skill_attack_names)
                result_message += skill_message
            else: # 공격 불가 시
                if dash:
                    if attacker['Id'] == 0: # 도전자 공격
                        battle_embed.color = discord.Color.blue()
                    elif attacker['Id'] == 1: # 상대 공격
                        battle_embed.color = discord.Color.red()

                    battle_embed.add_field(name="위치", value =f"{challenger['name']} 위치: {challenger['Position']}, {opponent['name']} 위치: {opponent['Position']}", inline = False) 
                    battle_embed.add_field(name="거리", value = f"현재 거리 : {battle_distance}", inline = False)
                    battle_embed.add_field(name="돌진!", value = f"{attacker['name']}의 돌진! 거리가 {move_distance}만큼 줄어듭니다!", inline = False)

                    if attacker["WeaponRange"] < battle_distance:
                        battle_embed.title = f"{attacker['name']}의 공격!⚔️"
                        battle_embed.add_field(name="공격 불가!", value = f"적이 사거리 밖에 있어 공격이 불가합니다\n", inline = False)
                    else:
                        battle_embed.title = f"{attacker['name']}의 돌진!⚔️"
                        battle_embed.add_field(name="공격 불가!", value = f"속도가 느려 공격할 수 없습니다!\n", inline = False)
                    await attack(attacker, defender, evasion, reloading)
                else:
                    battle_embed.title = f"{attacker['name']}의 공격!⚔️"
                    if attacker['Id'] == 0: # 도전자 공격
                        battle_embed.color = discord.Color.blue()
                    elif attacker['Id'] == 1: # 상대 공격
                        battle_embed.color = discord.Color.red()
                    battle_embed.add_field(name="위치", value =f"{challenger['name']} 위치: {challenger['Position']}, {opponent['name']} 위치: {opponent['Position']}", inline = False) 
                    battle_embed.add_field(name="거리", value = f"현재 거리 : {battle_distance}", inline = False)
                    battle_embed.add_field(name="공격 불가!", value = f"적이 사거리 밖에 있어 공격이 불가합니다!", inline = False)
                    await attack(attacker, defender, evasion, reloading)

            result_message += f"\n{cooldown_message}"
            # 공격 후, 각 스킬의 현재 쿨타임을 감소시키는 부분
            for skill, cooldown_data in attacker["Skills"].items():
                if cooldown_data["현재 쿨타임"] > 0 and skill not in used_skill:
                    attacker["Skills"][skill]["현재 쿨타임"] -= 1  # 현재 쿨타임 감소

            if skill_attack_names:
                crit_text = "💥" if critical else ""
                evade_text = "회피!⚡️" if evade else ""
                distance_text = "🎯" if dist else ""

                shield_message = ""
                remain_shield = ""
                battle_embed.add_field(name="스킬", value = result_message.rstrip("\n"), inline = False)
                if "보호막" in defender['Status']:
                    shield_amount = defender["Status"]["보호막"]["value"]
                    if shield_amount >= damage:
                        defender["Status"]["보호막"]["value"] -= damage
                        shield_message = f" 🛡️피해 {damage} 흡수!"
                        damage = 0
                    else:
                        damage -= shield_amount
                        shield_message = f" 🛡️피해 {shield_amount} 흡수!"
                        defender["Status"]["보호막"]["value"] = 0
                    if "보호막" in defender["Status"] and defender["Status"]["보호막"]["value"] <= 0: # 보호막이 0이 되면 삭제
                        del defender["Status"]["보호막"]

                if "보호막" in defender['Status']:
                    shield_amount = defender["Status"]["보호막"]["value"]
                    remain_shield = f"(🛡️보호막 {shield_amount})"

                battle_embed.add_field(name ="", value = f"**{evade_text}{distance_text} {damage} 대미지!{crit_text}{shield_message}**",inline = False)
                defender["HP"] -= damage
                if attacker['Id'] == 0: # 도전자 공격
                    if raid:
                        battle_embed.add_field(name = "남은 내구도", value=f"**[{defender['HP']} / {defender['FullHP']}]**")
                    else:
                        battle_embed.add_field(name = "남은 내구도", value=f"**[{defender['HP']} / {defender['BaseHP']}]**")
                elif attacker['Id'] == 1: # 상대 공격
                    battle_embed.add_field(name = "남은 내구도", value=f"**[{defender['HP']} / {weapon_data_challenger.get('내구도', '')}]{remain_shield}**")
            elif attacked:
                # 크리티컬 또는 회피 여부에 따라 메시지 추가
                crit_text = "💥" if critical else ""
                evade_text = "회피!⚡️" if evade else ""
                distance_text = "🎯" if dist else ""

                shield_message = ""
                remain_shield = ""
                battle_embed.add_field(name="스킬", value = result_message.rstrip("\n"), inline = False)
                if "보호막" in defender['Status']:
                    shield_amount = defender["Status"]["보호막"]["value"]
                    if shield_amount >= damage:
                        defender["Status"]["보호막"]["value"] -= damage
                        shield_message = f" 🛡️피해 {damage} 흡수!"
                        damage = 0
                    else:
                        damage -= shield_amount
                        shield_message = f" 🛡️피해 {shield_amount} 흡수!"
                        defender["Status"]["보호막"]["value"] = 0
                    if "보호막" in defender["Status"] and defender["Status"]["보호막"]["value"] <= 0: # 보호막이 0이 되면 삭제
                        del defender["Status"]["보호막"]

                if "보호막" in defender['Status']:
                    shield_amount = defender["Status"]["보호막"]["value"]
                    remain_shield = f"(🛡️보호막 {shield_amount})"

                battle_embed.add_field(name ="", value = f"**{evade_text}{distance_text} {damage} 대미지!{crit_text}{shield_message}**",inline = False)
                defender["HP"] -= damage
                if attacker['Id'] == 0: # 도전자 공격
                    if raid:
                        battle_embed.add_field(name = "남은 내구도", value=f"**[{defender['HP']} / {defender['FullHP']}]{remain_shield}**")
                    else:
                        battle_embed.add_field(name = "남은 내구도", value=f"**[{defender['HP']} / {weapon_data_opponent.get('내구도', '')}]{remain_shield}**")
                elif attacker['Id'] == 1: # 상대 공격
                    battle_embed.add_field(name = "남은 내구도", value=f"**[{defender['HP']} / {weapon_data_challenger.get('내구도', '')}]{remain_shield}**")
            else:
                if attacker['Id'] == 0: # 도전자 이동
                    battle_embed.add_field(name="스킬", value = result_message.rstrip("\n"), inline = False)
                elif attacker['Id'] == 1: # 상대 이동
                    battle_embed.add_field(name="스킬", value = result_message.rstrip("\n"), inline = False)

            if defender["HP"] <= 0:
                result = await end(attacker,defender,"attacker",raid,simulate,winner_id = attacker['Id'])
                if simulate:
                    return result
                break
            
            # 공격자와 방어자 변경
            attacker, defender = defender, attacker
            if not simulate:
                await weapon_battle_thread.send(embed = battle_embed)
                if turn >= 30:
                    await asyncio.sleep(1)
                else:
                    await asyncio.sleep(2)  # 턴 간 딜레이

        if not simulate:
            battle_ref = db.reference("승부예측/대결진행여부")
            battle_ref.set(False)


def seconds_to_minutes_and_seconds(seconds): # 초로 주어진 데이터를 분:초 형태로 변환
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    return f"{minutes:02d}:{remaining_seconds:02d}"

def get_tier_name(value): # 숫자를 통해 티어 이름 가져오기(딕셔너리 역으로 계산)
    for tier, rank in TIER_RANK_MAP.items():
        if rank == value:
            return tier
    return None  # If value is not found in the dictionary

def tier_to_number(tier, rank, lp): # 티어를 레이팅 숫자로 변환
    tier_num = TIER_RANK_MAP.get(tier)
    rank_num = RANK_MAP.get(rank)
    if tier_num is None or rank_num is None:
        return None
    return tier_num * 400 + rank_num * 100 + lp

def number_to_tier(lp_number): # 레이팅 숫자를 티어로 변환
    tier_num = lp_number // 400
    lp_number %= 400
    rank_num = lp_number // 100
    lp = lp_number % 100
    for tier, tier_num_val in TIER_RANK_MAP.items():
        for rank, rank_num_val in RANK_MAP.items():
            if tier_num == tier_num_val and rank_num == rank_num_val:
                return f"{tier} {rank} {lp}P"
    return None

def number_to_tier2(lp_number): # 레이팅 숫자를 티어로 변환 (DIAMOND -> D)
    tier_num = lp_number // 400
    lp_number %= 400
    rank_num = lp_number // 100
    lp = lp_number % 100
    for tier, tier_num_val in TIER_RANK_MAP2.items():
        for rank, rank_num_val in RANK_MAP.items():
            if tier_num == tier_num_val and rank_num == rank_num_val:
                return f"{tier} {rank} {lp}P"
    return None

# 아이템 지급
def give_item(nickname, item_name, amount):
    cur_predict_seasonref = db.reference("승부예측/현재예측시즌") # 현재 진행중인 예측 시즌을 가져옴
    current_predict_season = cur_predict_seasonref.get()

    weapon_items = ['강화재료','랜덤박스','레이드 재도전','탑 재도전','연마제','특수 연마제','탑코인','스킬 각성의 룬','운명 왜곡의 룬', '회귀의 룬']
    if item_name in weapon_items:
        refitem = db.reference(f'무기/아이템/{nickname}')
    else:
        # 사용자 아이템 데이터 위치
        refitem = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname}/아이템')
    item_data = refitem.get() or {}

    refitem.update({item_name: item_data.get(item_name, 0) + amount})

# 대결 베팅 모달
class BettingModal(Modal):
    def __init__(self, user: discord.User, challenger, opponent, game_point, game, message, what):
        # 모달에 사용자 이름을 추가하고 포인트 입력 필드 설정
        self.user = user
        super().__init__(title=f"{self.user.display_name}님, 베팅할 포인트를 입력해주세요!")
        self.add_item(TextInput(label="베팅할 포인트", placeholder="포인트를 입력하세요", required=True, min_length=1))
        self.challenger = challenger
        self.opponent = opponent
        self.game_point = game_point
        self.game = game
        self.message = message
        self.what = what
        
    async def on_submit(self, interaction: discord.Interaction):
        # 포인트 입력값 처리
        bet_amount = self.children[0].value
        if not bet_amount.isdigit() or int(bet_amount) <= 0:
            await interaction.response.send_message(content="유효한 포인트를 입력해주세요!", ephemeral=True)
            return
        
        await interaction.response.defer()
        bet_amount = int(bet_amount)

        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
        current_predict_season = cur_predict_seasonref.get()
        ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{interaction.user.name}')
        ref2 = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{interaction.user.name}/베팅포인트')
        bettingPoint = ref2.get()
        info = ref.get()

        if info['포인트'] - bettingPoint < bet_amount:
            await interaction.followup.send(f"포인트가 부족합니다!\n현재 포인트: {info['포인트'] - bettingPoint}(베팅 금액 {bettingPoint}P) 제외",ephemeral=True)
        else:
            # 포인트 수정
            await self.game.update_game_point(self.user, bet_amount)
            ref.update({"베팅포인트" : bettingPoint + bet_amount}) # 파이어베이스에 베팅포인트 추가
            
            # 베팅한 포인트 처리
            userembed = discord.Embed(title="베팅 완료!", color=discord.Color.green())
            userembed.add_field(name="", value=f"{self.user.display_name}님이 {bet_amount} 포인트를 베팅했습니다! 🎲")
            await interaction.followup.send(embed=userembed)

        if self.what == "주사위":
            diceview_embed = discord.Embed(title = "결과 확인", color = discord.Color.blue())
            diceview_embed.add_field(name = "", value = "주사위 결과를 확인하세요! 🎲",inline=False)
            diceview_embed.add_field(name = f"{self.challenger}", value = f"{self.game_point[self.challenger]}포인트",inline=True)
            diceview_embed.add_field(name = f"{self.opponent}", value = f"{self.game_point[self.opponent]}포인트",inline=True)
            await self.message.edit(embed = diceview_embed)
        elif self.what == "숫자야구":
            player = self.game.players[self.game.turn]
            embed = discord.Embed(title="⚾ 숫자야구 진행 중!", color=discord.Color.green())
            embed.add_field(name="턴", value=f"🎯 {player.mention}님의 턴입니다!", inline=False)
            embed.add_field(name = f"{self.challenger}", value = f"{self.game_point[self.challenger]}포인트",inline=True)
            embed.add_field(name = f"{self.opponent}", value = f"{self.game_point[self.opponent]}포인트",inline=True)
            await self.message.edit(embed=embed)

duels = {}  # 진행 중인 대결 정보를 저장

class InheritWeaponNameModal(discord.ui.Modal, title="새로운 무기 이름 입력"):
    weapon_name = discord.ui.TextInput(label="무기 이름", placeholder="새 무기의 이름을 입력하세요", max_length=10)

    def __init__(self, user_id, selected_weapon_type, weapon_data, inherit_type):
        super().__init__()
        self.user_id = user_id
        self.selected_weapon_type = selected_weapon_type
        self.weapon_data = weapon_data
        self.inherit_type = inherit_type

    async def on_submit(self, interaction: discord.Interaction):
        new_weapon_name = self.weapon_name.value

        inherit = self.weapon_data.get("계승", 0)
        inherit_log = self.weapon_data.get("계승 내역", {})

        # 🔹 기존 계승 내역 업데이트
        if self.inherit_type in inherit_log:
            inherit_log[self.inherit_type] += 1
        else:
            inherit_log[self.inherit_type] = 1

        # 🔹 강화 내역 가져오기
        nickname = interaction.user.name
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
        current_predict_season = cur_predict_seasonref.get()

        ref_enhancement_log = db.reference(f"무기/유저/{nickname}/강화내역")
        enhancement_log = ref_enhancement_log.get() or {}

        selected_options = []
        # 🔹 15강 이상이면 계승할 강화 옵션 선택
        current_upgrade_level = self.weapon_data.get("강화", 0)
        if current_upgrade_level > 15:
            num_inherit_upgrades = current_upgrade_level - 15
            weighted_options = []

            for option, count in enhancement_log.items():
                # 계승 가능 횟수만큼 옵션을 리스트에 추가 (가중치 방식)
                weighted_options.extend([option] * count)

            while len(selected_options) < num_inherit_upgrades and weighted_options:
                option = random.choice(weighted_options)

                # 해당 옵션의 계승 횟수가 제한보다 작으면 선택
                if selected_options.count(option) < enhancement_log[option]:
                    selected_options.append(option)

                    # 이미 선택한 만큼 weighted_options에서도 줄여줘야 중복 방지
                    weighted_options.remove(option)
                else:
                    # 만약 최대 횟수까지 이미 선택된 경우, 더는 뽑히지 않게
                    weighted_options = [o for o in weighted_options if o != option]

            # 🔹 계승 내역에 추가
            for option in selected_options:
                # "추가강화" 키가 계승 내역에 존재하는지 확인하고 없으면 생성
                if "추가강화" not in inherit_log:
                    inherit_log["추가강화"] = {}  # "추가강화"가 없다면 새로 생성

                # 해당 옵션이 추가강화 내역에 있는지 확인
                if option in inherit_log["추가강화"]:
                    inherit_log["추가강화"][option] += 1  # 이미 있다면 개수 증가
                else:
                    inherit_log["추가강화"][option] = 1  # 없으면 1로 시작

        ref_weapon_base = db.reference(f"무기/기본 스탯")
        base_weapon_stats = ref_weapon_base.get() or {}

        base_stat_increase = inherit_log.get("기본 스탯 증가", 0) * 0.3
        base_weapon_stat = base_weapon_stats[self.selected_weapon_type]

        # 계승 내역에 각 강화 유형을 추가
        enhanced_stats = {}

        ref_weapon_enhance = db.reference(f"무기/강화")
        enhancement_options = ref_weapon_enhance.get() or {}
        # 계승 내역에서 각 강화 옵션을 확인하고, 해당 스탯을 강화 내역에 추가
        for enhancement_type, enhancement_data in inherit_log.items():
            if enhancement_type == "추가강화":  # 추가강화 항목만 따로 처리
                # "추가강화" 내역에서 각 강화 옵션을 확인
                for option, enhancement_count in enhancement_data.items():
                    # 해당 옵션에 대한 stats를 업데이트
                    if option in enhancement_options:
                        stats = enhancement_options[option]["stats"]
                        # 강화된 수치를 적용
                        for stat, increment in stats.items():
                            if stat in enhanced_stats:
                                enhanced_stats[stat] += increment * enhancement_count  # 강화 내역 수 만큼 적용
                            else:
                                enhanced_stats[stat] = increment * enhancement_count  # 처음 추가되는 stat은 그 값으로 설정

        new_enhancement_log = dict(Counter(selected_options))

        # 메시지 템플릿에 추가된 강화 내역을 포함
        enhancement_message = "\n강화 내역:\n"
        for option, count in new_enhancement_log.items():
            enhancement_message += f"{option}: {count}회\n"

        if "추가강화" in inherit_log:
            new_enhancement_log = Counter(inherit_log["추가강화"])  # 기존 내역 추가
        
        basic_skill_levelup = inherit_log.get("기본 스킬 레벨 증가", 0)
        
        basic_skills = ["속사", "기습", "강타", "헤드샷", "창격", "수확", "명상", "화염 마법", "냉기 마법", "신성 마법", "일섬"]
        skills = base_weapon_stat["스킬"]
        for skill_name in basic_skills:
            if skill_name in skills:
                skills[skill_name]["레벨"] += basic_skill_levelup

        new_weapon_data = {
            "강화": 0,  # 기본 강화 값
            "계승": inherit + 1,
            "이름": new_weapon_name,
            "무기타입": self.selected_weapon_type,
            "공격력": base_weapon_stat["공격력"] + round(base_weapon_stat["공격력"] * base_stat_increase + enhanced_stats.get("공격력", 0)),
            "스킬 증폭": base_weapon_stat["스킬 증폭"] + round(base_weapon_stat["스킬 증폭"] * base_stat_increase + enhanced_stats.get("스킬 증폭", 0)),
            "내구도": base_weapon_stat["내구도"] + round(base_weapon_stat["내구도"] * base_stat_increase + enhanced_stats.get("내구도", 0)),
            "방어력": base_weapon_stat["방어력"] + round(base_weapon_stat["방어력"] * base_stat_increase + enhanced_stats.get("방어력", 0)),
            "스피드": base_weapon_stat["스피드"] + round(base_weapon_stat["스피드"] * base_stat_increase + enhanced_stats.get("스피드", 0)),
            "명중": base_weapon_stat["명중"] + round(base_weapon_stat["명중"] * base_stat_increase + enhanced_stats.get("명중", 0)),
            "사거리": base_weapon_stat["사거리"],  # 사거리는 변경되지 않음
            "치명타 대미지": base_weapon_stat["치명타 대미지"] + enhanced_stats.get("치명타 대미지", 0),
            "치명타 확률": base_weapon_stat["치명타 확률"] + enhanced_stats.get("치명타 확률", 0),
            "스킬": skills,
            "강화내역": new_enhancement_log,
            "계승 내역": inherit_log 
        }

        nickname = interaction.user.name
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
        current_predict_season = cur_predict_seasonref.get()

        ref_weapon = db.reference(f"무기/유저/{nickname}")
        ref_weapon.update(new_weapon_data)

        await interaction.response.send_message(
            f"[{self.weapon_data.get('이름', '이전 무기')}]의 힘을 계승한 **[{new_weapon_name}](🌟 +{inherit + 1})** 무기가 생성되었습니다!\n"
            f"계승 타입: [{self.inherit_type}] 계승이 적용되었습니다!\n"
            f"{enhancement_message}" 
        )

# 대결 신청
class DuelRequestView(discord.ui.View):
    def __init__(self, challenger, opponent, point):
        super().__init__()  # 3분 타이머
        self.challenger = challenger
        self.opponent = opponent
        self.request_accepted = False
        self.message = None
        self.point = point
        self.event = asyncio.Event()

    async def start_timer(self):
        await asyncio.sleep(60)
        if not self.request_accepted:
            for child in self.children:
                child.disabled = True
        
        battleembed = discord.Embed(title="요청 만료!", color=discord.Color.blue())
        battleembed.add_field(name="", value="대결 요청이 만료되었습니다. ⏰")
        await self.message.edit(embed=battleembed,view = self)
        battle_ref = db.reference("승부예측/대결진행여부")
        battle_ref.set(False)
        self.event.set()

    @discord.ui.button(label="수락", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.opponent:
            await interaction.response.send_message("이 버튼은 지목된 사람만 누를 수 있습니다!", ephemeral=True)
            return
        
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
        current_predict_season = cur_predict_seasonref.get()
        point_ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{interaction.user.name}')
        predict_data = point_ref.get()
        point = predict_data["포인트"]
        bettingPoint = predict_data["베팅포인트"]
        real_point = point - bettingPoint

        if real_point < self.point:
            await interaction.response.send_message("포인트가 부족합니다!", ephemeral=True)
            return

        self.request_accepted = True
        for child in self.children:
            child.disabled = True

        battleembed = discord.Embed(title="대결 수락!", color = discord.Color.blue())
        battleembed.add_field(name="", value=f"{self.opponent.mention}님이 대결을 수락했습니다!")
        await interaction.response.edit_message(embed = battleembed, view = self)
        self.event.set()

    @discord.ui.button(label="거절", style=discord.ButtonStyle.danger)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.opponent:
            await interaction.response.send_message("이 버튼은 지목된 사람만 누를 수 있습니다!", ephemeral=True)
            return

        self.request_accepted = False
        for child in self.children:
            child.disabled = True

        battleembed = discord.Embed(title="대결 거절!", color = discord.Color.blue())
        battleembed.add_field(name="", value=f"{self.opponent.mention}님이 대결을 거절했습니다!")
        await interaction.response.edit_message(embed = battleembed, view = self)
        battle_ref = db.reference("승부예측/대결진행여부")
        battle_ref.set(False)
        self.event.set()

# 주사위 대결 결과 발표
class DiceRevealView(discord.ui.View):
    def __init__(self, challenger, opponent, dice_results, game_point, channel): 
        super().__init__()
        self.challenger = challenger.name
        self.opponent = opponent.name
        self.challenger_m = challenger
        self.opponent_m = opponent
        self.dice_results = dice_results
        self.game_point = game_point
        self.revealed = {challenger.name: False, opponent.name: False}
        self.reroll = {challenger.name: False, opponent.name: False}
        self.giveup = {challenger.name: False, opponent.name: False}
        self.message = ""
        self.point_limited = False
        self.keep_alive_task = None # 메시지 갱신 태스크 저장용
        self.channel = channel

    async def timer_task(self):
        """5분 타이머 진행 + 1분 전 알림 메시지 출력 (백그라운드 태스크)"""
        try:
            await asyncio.sleep(240)  # 4분 대기
            userembed = discord.Embed(title="종료 임박!", color=discord.Color.red())
            userembed.add_field(name="", value="⏳ 베팅이 **1분 뒤 종료**됩니다!")
            await self.message.channel.send(embed=userembed)
            await asyncio.sleep(60)  # 추가 1분 대기
            await self.announce_winner()
        except asyncio.CancelledError:
            # 타이머가 취소되었을 경우 예외 무시
            print("타이머가 취소되었습니다.")
            return

    async def start_timer(self):
        """타이머 백그라운드 태스크 시작"""
        self.keep_alive_task = asyncio.create_task(self.timer_task())

    @discord.ui.button(label="주사위 확인", style=discord.ButtonStyle.gray)
    async def check_dice(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.name not in [self.challenger, self.opponent]:
            userembed = discord.Embed(title = "주사위 결과!",color = discord.Color.blue())
            userembed.add_field(name=f"{self.challenger_m.display_name}의 주사위 끝자리 수",value=f" **{self.dice_results[self.challenger] % 10}**🎲", inline = False)
            userembed.add_field(name=f"{self.opponent_m.display_name}의 주사위 끝자리 수",value=f" **{self.dice_results[self.opponent] % 10}**🎲", inline = False)
            await interaction.response.send_message(content = "", embed = userembed, ephemeral = True)
            return
        
        userembed = discord.Embed(title = "주사위 확인!",color = discord.Color.red())
        userembed.add_field(name="",value=f"당신의 주사위 숫자는 **{self.dice_results[interaction.user.name]}**입니다! 🎲")
        await interaction.response.send_message(content = "",embed = userembed, ephemeral=True)

    @discord.ui.button(label="베팅", style=discord.ButtonStyle.primary)
    async def bet(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.name not in [self.challenger, self.opponent]:
            userembed = discord.Embed(title = "베팅 불가!",color = discord.Color.red())
            userembed.add_field(name="",value="참가자만 베팅할 수 있습니다!")
            await interaction.response.send_message(content = "", embed = userembed, ephemeral = True)
            return
        
        # 모달 생성
        modal = BettingModal(user=interaction.user, challenger = self.challenger, opponent = self.opponent, game_point = self.game_point, game = self, message = self.message, what = "주사위")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="포기", style=discord.ButtonStyle.danger)
    async def give_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.name not in [self.challenger, self.opponent]:
            userembed = discord.Embed(title = "포기 불가!",color = discord.Color.red())
            userembed.add_field(name="",value="참가자만 포기할 수 있습니다!")
            await interaction.response.send_message(content = "", embed = userembed, ephemeral = True)
            return

        userembed = discord.Embed(title = "승부 포기...",color = discord.Color.red())
        userembed.add_field(name="",value=f"{interaction.user.display_name}님이 승부를 포기했습니다! 🎲")

        await interaction.response.send_message(embed = userembed)

        self.giveup[interaction.user.name] = True

        if self.keep_alive_task: 
            self.keep_alive_task.cancel()
        await self.announce_winner()

    @discord.ui.button(label="🎲 다시 굴리기", style=discord.ButtonStyle.gray)
    async def reroll_dice(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.name not in [self.challenger, self.opponent]:
            userembed = discord.Embed(title = "선택 불가!",color = discord.Color.red())
            userembed.add_field(name="",value="참가자만 선택할 수 있습니다!")
            await interaction.response.send_message(content = "", embed = userembed, ephemeral = True)
            return

        if not self.reroll[interaction.user.name]:
            self.reroll[interaction.user.name] = True

            userembed = discord.Embed(title = "주사위 다시 굴리기 요청!",color = discord.Color.red())
            userembed.add_field(name="",value=f"{interaction.user.display_name}님이 주사위 다시 굴리기를 요청했습니다!")

            await interaction.response.send_message(embed = userembed)
        else:
            self.reroll[interaction.user.name] = False

            userembed = discord.Embed(title = "주사위 다시 굴리기 요청 취소!",color = discord.Color.red())
            userembed.add_field(name="",value=f"{interaction.user.display_name}님이 주사위 다시 굴리기 요청을 취소했습니다!")

            await interaction.response.send_message(embed = userembed)

        if all(self.reroll.values()):
            cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
            current_predict_season = cur_predict_seasonref.get()

            add_point_challenger = round(self.game_point[self.challenger] * 0.25)
            add_point_opponent = round(self.game_point[self.opponent] * 0.25)

            challenger_point_ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{self.challenger}')
            challenger_predict_data = challenger_point_ref.get()
            challenger_point = challenger_predict_data["포인트"]
            challenger_bettingPoint = challenger_predict_data["베팅포인트"]
            challenger_real_point = challenger_point - (challenger_bettingPoint + add_point_challenger)
            
            if challenger_real_point < 0 and not self.point_limited:
                self.point_limited = True

            opponent_point_ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{self.opponent}')
            opponent_predict_data = opponent_point_ref.get()
            opponent_point = opponent_predict_data["포인트"]
            opponent_bettingPoint = opponent_predict_data["베팅포인트"]
            opponent_real_point = opponent_point - (opponent_bettingPoint + add_point_opponent)

            if opponent_real_point < 0 and not self.point_limited:
                self.point_limited = True

            userembed = discord.Embed(title = "주사위 다시 굴리기!",color = discord.Color.blue())
            userembed.add_field(name="",value=f"주사위를 다시 굴립니다! 🎲", inline = False)
            if self.point_limited:
                userembed.add_field(name="",value=f"포인트가 부족하여 추가 베팅이 적용되지 않습니다.", inline = False)
            else:
                userembed.add_field(name="",value=f"**베팅 포인트 25% 증가!**", inline = False)
                userembed.add_field(name="추가 베팅",value=f"{self.challenger_m.display_name}: **{add_point_challenger}포인트** | {self.opponent_m.display_name}: **{add_point_opponent}포인트**", inline = False)
                self.game_point[self.challenger] += add_point_challenger
                self.game_point[self.opponent] += add_point_opponent
                challenger_point_ref.update({"베팅포인트" : challenger_bettingPoint + add_point_challenger})
                opponent_point_ref.update({"베팅포인트" : opponent_bettingPoint + add_point_opponent})
            userembed.add_field(name="이전 결과",value=f"{self.challenger_m.display_name}: 🎲**{self.dice_results[self.challenger]}** | {self.opponent_m.display_name}: 🎲**{self.dice_results[self.opponent]}**",inline = False)

            # 주사위 굴리기
            self.dice_results = {
                self.challenger: secrets.randbelow(100) + 1,
                self.opponent: secrets.randbelow(100) + 1
            }

            self.reroll[self.challenger] = False
            self.reroll[self.opponent] = False

            diceview_embed = discord.Embed(title = "결과 확인", color = discord.Color.blue())
            diceview_embed.add_field(name = "", value = "주사위 결과를 확인하세요! 🎲",inline=False)
            diceview_embed.add_field(name = f"{self.challenger}", value = f"{self.game_point[self.challenger]}포인트",inline=True)
            diceview_embed.add_field(name = f"{self.opponent}", value = f"{self.game_point[self.opponent]}포인트",inline=True)
            await self.message.edit(embed = diceview_embed)

            await self.message.channel.send(embed = userembed)

    @discord.ui.button(label="준비 완료", style=discord.ButtonStyle.green)
    async def reveal_dice(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.name not in [self.challenger, self.opponent]:
            userembed = discord.Embed(title = "준비 완료 불가!",color = discord.Color.red())
            userembed.add_field(name="",value="참가자만 준비를 완료할 수 있습니다!")
            await interaction.response.send_message(content = "", embed = userembed, ephemeral = True)
            return

        if not self.revealed[interaction.user.name]:
            self.revealed[interaction.user.name] = True

            userembed = discord.Embed(title = "준비 완료!",color = discord.Color.red())
            userembed.add_field(name="",value=f"{interaction.user.display_name}님이 결과 발표 준비를 완료했습니다! 🎲")

            await interaction.response.send_message(embed = userembed)
        else:
            self.revealed[interaction.user.name] = False

            userembed = discord.Embed(title = "준비 취소!",color = discord.Color.red())
            userembed.add_field(name="",value=f"{interaction.user.display_name}님이 결과 발표 준비를 취소했습니다! 🎲")

            await interaction.response.send_message(embed = userembed)

        if all(self.revealed.values()):
            if self.keep_alive_task: 
                self.keep_alive_task.cancel()
            await self.announce_winner()

    
    async def update_game_point(self, user, bet_amount):
        # 게임 포인트를 외부에서 수정
        if user.name in self.game_point:
            self.game_point[user.name] += bet_amount
    
    async def announce_winner(self):
        battle_ref = db.reference("승부예측/대결진행여부")
        battle_ref.set(False)
        
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
        current_predict_season = cur_predict_seasonref.get()

        battled_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{self.challenger}/배틀여부")
        item_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{self.challenger}/아이템")
        item_data = item_ref.get() or {} 
        battled = battled_ref.get()
        battle_refresh = item_data.get("주사위대결기회 추가", 0)
        if battle_refresh and battled:
            item_ref.update({"주사위대결기회 추가": battle_refresh - 1})

        ch_dice = self.dice_results[self.challenger]
        op_dice = self.dice_results[self.opponent]

        userembed = discord.Embed(title = "주사위 공개!",color = discord.Color.red())
        userembed.add_field(name="",value=f"{self.challenger_m.display_name}의 주사위 숫자: **{self.dice_results[self.challenger]}** 🎲")
        await self.message.channel.send(embed = userembed)
        
        userembed = discord.Embed(title = "주사위 공개!",color = discord.Color.red())
        userembed.add_field(name="",value=f"{self.opponent_m.display_name}의 주사위 숫자: **{self.dice_results[self.opponent]}** 🎲")
        await self.message.channel.send(embed = userembed)

        # 게임 결과 발표 후, 버튼 비활성화
        for button in self.children:  # 모든 버튼에 대해
            button.disabled = True

        # 버튼을 비활성화 한 후, 뷰 업데이트
        await self.message.edit(view=self)

        result = True
        if ch_dice > op_dice:
            if ch_dice == 100 and op_dice == 1: # 1이 100을 이김
                dice_winner = self.opponent_m
                result = False
            else:
                dice_winner = self.challenger_m
                result = True
        elif op_dice > ch_dice:
            if op_dice == 100 and ch_dice == 1: # 1이 100을 이김
                dice_winner = self.challenger_m
                result = True
            else:
                dice_winner = self.opponent_m
                result = False
        else:
            dice_winner = None

        if self.giveup[self.challenger]: # 도전자가 포기했을 경우
            dice_winner = self.opponent_m
            result = False
        elif self.giveup[self.opponent]: # 상대가 포기했을 경우
            dice_winner = self.challenger_m
            result = True

        if dice_winner:
            userembed = discord.Embed(title="메세지", color=discord.Color.blue())
            userembed.add_field(name="게임 종료", value=f"주사위 대결이 종료되었습니다!\n {dice_winner.mention}의 승리!")

            winners = p.votes['배틀']['prediction']['win'] if result else p.votes['배틀']['prediction']['lose']
            losers = p.votes['배틀']['prediction']['lose'] if result else p.votes['배틀']['prediction']['win']
            winnerNum = len(winners)
            loserNum = len(losers)

            BonusRate = 0 if winnerNum == 0 else round((((winnerNum + loserNum) / winnerNum) - 1) * 0.2, 2) + 1 # 0.2배 배율 적용
            if BonusRate > 0:
                BonusRate += 0.1

            BonusRate = round(BonusRate,2)

            userembed.add_field(
                name="", 
                value=f"베팅 배율: {BonusRate}배" if BonusRate == 0 else 
                f"베팅 배율: {BonusRate}배!((({winnerNum + loserNum}/{winnerNum} - 1) x 0.2 + 1) + 0.1)", 
                inline=False
            )

            current_datetime = datetime.now() # 데이터베이스에 남길 현재 시각 기록
            current_date = current_datetime.strftime("%Y-%m-%d")
            current_time = current_datetime.strftime("%H:%M:%S")

            cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
            current_predict_season = cur_predict_seasonref.get()

            winner_total_point = sum(winner['points'] for winner in winners)
            loser_total_point = sum(loser['points'] for loser in losers)
            remain_loser_total_point = loser_total_point
            
            for winner in winners:
                point_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner['name'].name}")
                predict_data = point_ref.get()
                point = predict_data["포인트"]
                bettingPoint = predict_data["베팅포인트"]

                # 예측 내역 업데이트
                point_ref.update({
                    "포인트": point,
                    "총 예측 횟수": predict_data["총 예측 횟수"] + 1,
                    "적중 횟수": predict_data["적중 횟수"] + 1,
                    "적중률": f"{round((((predict_data['적중 횟수'] + 1) * 100) / (predict_data['총 예측 횟수'] + 1)), 2)}%",
                    "연승": predict_data["연승"] + 1,
                    "연패": 0,
                    "베팅포인트": bettingPoint - winner["points"]
                })


                # ====================  [미션]  ====================
                # 일일미션 : 승부예측 1회 적중
                cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                current_predict_season = cur_predict_seasonref.get()
                ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner['name'].name}/미션/일일미션/승부예측 1회 적중")
                mission_data = ref.get() or {}
                mission_bool = mission_data.get('완료', False)
                if not mission_bool:
                    ref.update({"완료": True})
                    print(f"{winner['name'].display_name}의 [승부예측 1회 적중] 미션 완료")

                # ====================  [미션]  ====================
                betted_rate = round(winner['points'] / winner_total_point, 3) if winner_total_point else 0
                get_bet = round(betted_rate * loser_total_point)
                get_bet_limit = round(BonusRate * winner['points'])
                if get_bet >= get_bet_limit:
                    get_bet = get_bet_limit

                remain_loser_total_point -= get_bet
                streak_text = f"{predict_data['연승'] + 1}연속 적중을 이루어내며 " if predict_data['연승'] + 1 > 1 else ""
                
                bonus_rate = calculate_bonus_rate(predict_data["연승"] + 1)
                add_points = 10 + round(winner['points'] * (BonusRate + bonus_rate)) + get_bet if predict_data["연승"] + 1 > 1 else 10 + round(winner["points"] * BonusRate) + get_bet
                if predict_data['연승'] + 1 > 1:
                    userembed.add_field(name="", value=f"{winner['name'].display_name}님이 {streak_text}{add_points}(베팅 보너스 + {round(winner['points'] * (BonusRate + bonus_rate))} + {get_bet})(연속적중 보너스 {bonus_rate}배!) 점수를 획득하셨습니다! (베팅 포인트: {winner['points']})", inline=False)
                else:
                    userembed.add_field(name="", value=f"{winner['name'].display_name}님이 {streak_text}{add_points}(베팅 보너스 + {round(winner['points'] * BonusRate)} + {get_bet}) 점수를 획득하셨습니다! (베팅 포인트: {winner['points']})", inline=False)   
                # 예측 내역 변동 데이터
                change_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트변동로그/{current_date}/{winner['name'].name}")
                change_ref.push({
                    "시간": current_time,
                    "포인트": point + add_points - winner['points'],
                    "포인트 변동": add_points - winner['points'],
                    "사유": "주사위 대결 승부예측"
                    })
                point_ref.update({"포인트": point + add_points - winner['points']})

            for loser in losers:
                point_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{loser['name'].name}")
                predict_data = point_ref.get()
                point = predict_data["포인트"]
                bettingPoint = predict_data["베팅포인트"]
                
                # 예측 내역 업데이트
                point_ref.update({
                    "포인트": point,
                    "총 예측 횟수": predict_data["총 예측 횟수"] + 1,
                    "적중 횟수": predict_data["적중 횟수"],
                    "적중률": f"{round((((predict_data['적중 횟수']) * 100) / (predict_data['총 예측 횟수'] + 1)), 2)}%",
                    "연승": 0,
                    "연패": predict_data["연패"] + 1,
                    "베팅포인트": bettingPoint - loser["points"],
                })
                
                # 남은 포인트를 배팅한 비율에 따라 환급받음 (30%)
                betted_rate = round(loser['points'] / loser_total_point, 3) if loser_total_point else 0
                get_bet = round(betted_rate * remain_loser_total_point * 0.3)
                userembed.add_field(
                    name="",
                    value=f"{loser['name'].display_name}님이 예측에 실패하였습니다! " if loser['points'] == 0 else 
                    f"{loser['name'].display_name}님이 예측에 실패하여 베팅포인트를 잃었습니다! (베팅 포인트:-{loser['points']}) (환급 포인트: {get_bet})",
                    inline=False
                )
                # 예측 내역 변동 데이터
                change_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트변동로그/{current_date}/{loser['name'].name}")
                if point + get_bet < loser['points']:
                    point_ref.update({"포인트": 0})
                    change_ref.push({
                        "시간": current_time,
                        "포인트": 0,
                        "포인트 변동": -point,
                        "사유": "주사위 대결 승부예측"
                    })
                else:
                    point_ref.update({"포인트": point + get_bet - loser['points']})
                    change_ref.push({
                        "시간": current_time,
                        "포인트": point + get_bet - loser['points'],
                        "포인트 변동": get_bet - loser['points'],
                        "사유": "주사위 대결 승부예측"
                    })

            await self.channel.send(embed = userembed)
            p.votes['배틀']['prediction']['win'].clear()
            p.votes['배틀']['prediction']['lose'].clear()
            
            cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
            current_predict_season = cur_predict_seasonref.get()

            battleref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{p.votes['배틀']['name']['challenger']}")
            battleref.update({"배틀여부" : True})

            userembed = discord.Embed(title="승부 베팅 결과", color=discord.Color.blue())
            if result: # challenger가 승리
                remained_point = 0 # 환급 포인트
                challenger_point = self.game_point[self.challenger]
                original_opponent_point = self.game_point[self.opponent]
                opponent_point = self.game_point[self.opponent]
                
                if self.giveup[self.opponent]: # 상대가 포기했을 경우
                    if self.dice_results[self.opponent] <= self.dice_results[self.challenger]: # 상대가 더 낮은데 포기했을 경우
                        remained_point += round(opponent_point / 2)
                        opponent_point = round(opponent_point / 2)

                
                if opponent_point > challenger_point:
                    get_point = challenger_point * 2 # 받을 포인트
                    remained_point += opponent_point - challenger_point # 환급 포인트
                else:
                    get_point = challenger_point + opponent_point

                userembed.add_field(
                name="",
                value=f"{self.opponent_m.mention}님이 승부에서 패배하여 베팅포인트를 잃었습니다! (베팅 포인트:-{original_opponent_point}) (환급 포인트: {remained_point})",
                inline=False
                )
                userembed.add_field(
                name="",
                value=f"{self.challenger_m.mention}님이 승부에서 승리하여 {get_point}포인트를 획득하셨습니다! (베팅 포인트: {challenger_point})",
                inline=False
                )

                point_ref1 = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{self.opponent}')
                point_ref2 = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{self.challenger}')
                point_data1 = point_ref1.get()
                point1 = point_data1.get("포인트",0)
                bettingpoint1 = point_data1.get("베팅포인트",0)
                point_data2 = point_ref2.get()
                point2 = point_data2.get("포인트",0)
                bettingpoint2 = point_data2.get("베팅포인트",0)
                point_ref1.update({"포인트": point1 - original_opponent_point + remained_point})
                point_ref1.update({"베팅포인트": bettingpoint1 - original_opponent_point})
                point_ref2.update({"포인트": point2 + get_point - challenger_point})
                point_ref2.update({"베팅포인트": bettingpoint2 - challenger_point})

                current_datetime = datetime.now() # 데이터베이스에 남길 현재 시각 기록
                current_date = current_datetime.strftime("%Y-%m-%d")
                current_time = current_datetime.strftime("%H:%M:%S")
                change_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트변동로그/{current_date}/{self.opponent}")
                change_ref.push({
                    "시간": current_time,
                    "포인트": point1 - original_opponent_point + remained_point,
                    "포인트 변동": remained_point - original_opponent_point,
                    "사유": "주사위 대결",
                })

                change_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트변동로그/{current_date}/{self.challenger}")
                change_ref.push({
                    "시간": current_time,
                    "포인트": point2 + get_point - challenger_point,
                    "포인트 변동": get_point - challenger_point,
                    "사유": "주사위 대결",
                })
            else:
                remained_point = 0 # 환급 포인트
                challenger_point = self.game_point[self.challenger]
                original_challenger_point = self.game_point[self.challenger]
                opponent_point = self.game_point[self.opponent]

                if self.giveup[self.challenger]: # 도전자가 포기했을 경우
                    if self.dice_results[self.challenger] <= self.dice_results[self.opponent]: # 도전자가 더 낮은데 포기했을 경우
                        remained_point += round(challenger_point / 2)
                        challenger_point = round(challenger_point / 2)

                if challenger_point > opponent_point:
                    get_point = opponent_point * 2 # 받을 포인트
                    remained_point += challenger_point - opponent_point # 환급 포인트
                else:
                    get_point = opponent_point + challenger_point # 받을 포인트

                userembed.add_field(
                name="",
                value=f"{self.challenger_m.mention}님이 승부에서 패배하여 베팅포인트를 잃었습니다! (베팅 포인트:-{original_challenger_point}) (환급 포인트: {remained_point})",
                inline=False
                )
                userembed.add_field(
                name="",
                value=f"{self.opponent_m.mention}님이 승부에서 승리하여 {get_point}포인트를 획득하셨습니다! (베팅 포인트: {opponent_point})",
                inline=False
                )
                point_ref1 = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{self.opponent}')
                point_ref2 = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{self.challenger}')
                point_data1 = point_ref1.get()
                point1 = point_data1.get("포인트",0)
                bettingpoint1 = point_data1.get("베팅포인트",0)
                point_data2 = point_ref2.get()
                bettingpoint2 = point_data2.get("베팅포인트",0)
                point2 = point_data2.get("포인트",0)
                point_ref1.update({"포인트": point1 + get_point - opponent_point})
                point_ref1.update({"베팅포인트": bettingpoint1 - opponent_point})
                point_ref2.update({"포인트": point2 - original_challenger_point + remained_point})
                point_ref2.update({"베팅포인트": bettingpoint2 - original_challenger_point})
                
                current_datetime = datetime.now() # 데이터베이스에 남길 현재 시각 기록
                current_date = current_datetime.strftime("%Y-%m-%d")
                current_time = current_datetime.strftime("%H:%M:%S")
                change_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트변동로그/{current_date}/{self.opponent}")
                change_ref.push({
                    "시간": current_time,
                    "포인트": point1 + get_point - opponent_point,
                    "포인트 변동": get_point - opponent_point,
                    "사유": "주사위 대결",
                })

                change_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트변동로그/{current_date}/{self.challenger}")
                change_ref.push({
                    "시간": current_time,
                    "포인트": point2 - original_challenger_point + remained_point,
                    "포인트 변동":  remained_point - original_challenger_point,
                    "사유": "주사위 대결",
                })


            await self.channel.send(embed = userembed)

            p.votes['배틀']['name']['challenger'] = ""
            p.votes['배틀']['name']['상대'] = ""
        else:
            userembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
            userembed.add_field(name="게임 종료", value=f"배틀이 종료되었습니다!\n무승부!🤝\n")
            await self.channel.send(embed = userembed)

            cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
            current_predict_season = cur_predict_seasonref.get()

            ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{self.challenger}')
            originr = ref.get()
            bettingPoint = originr["베팅포인트"]
            bettingPoint -= self.game_point[self.challenger]
            ref.update({"베팅포인트": bettingPoint})

            ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{self.opponent}')
            originr = ref.get()
            bettingPoint = originr["베팅포인트"]
            bettingPoint -= self.game_point[self.opponent]
            ref.update({"베팅포인트": bettingPoint})
            winners = p.votes['배틀']['prediction']['win']
            losers = p.votes['배틀']['prediction']['lose']

            for winner in winners:
                ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner['name'].name}")
                originr = ref.get()
                bettingPoint = originr["베팅포인트"]
                bettingPoint -= winner['points']
                ref.update({"베팅포인트": bettingPoint})

            for loser in losers:
                ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{loser['name'].name}")
                originr = ref.get()
                bettingPoint = originr["베팅포인트"]
                bettingPoint -= loser['points']
                ref.update({"베팅포인트": bettingPoint})

            p.votes['배틀']['prediction']['win'].clear()
            p.votes['배틀']['prediction']['lose'].clear()
            cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
            current_predict_season = cur_predict_seasonref.get()

            battleref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{p.votes['배틀']['name']['challenger']}")
            battleref.update({"배틀여부" : True})
            
            self.game_point.clear()
            p.votes['배틀']['name']['challenger'] = ""
            p.votes['배틀']['name']['상대'] = ""
            
# 아이템 구매 뷰
class ItemBuyView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.selected_item = None
        self.buy_button = ItemBuyButton()

        item_select = ItemSelect()
        self.add_item(item_select)

        self.add_item(self.buy_button)

# 아이템 구매 버튼
class ItemBuyButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label = "아이템 구매",
            style = discord.ButtonStyle.success,
            disabled = True,
            custom_id = "buy_button"
        )
        self.item_name = None
    async def callback(self, interaction: discord.Interaction):
        user_name = interaction.user.name
        if not self.item_name:
            await interaction.response.send_message("먼저 아이템을 선택하세요!", ephemeral=True)
            return

        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
        current_predict_season = cur_predict_seasonref.get()
        point_ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{interaction.user.name}')
        predict_data = point_ref.get()
        point = predict_data["포인트"]
        bettingPoint = predict_data["베팅포인트"]
        real_point = point - bettingPoint

        item_menu = {
            "배율증가1": {"cost": 50 if round(real_point * 0.05) < 50 else round(real_point * 0.05), "currency": "P"},
            "배율증가3": {"cost": 100 if round(real_point * 0.1) < 100 else round(real_point * 0.1), "currency": "P"},
            "배율증가5": {"cost": 200 if round(real_point * 0.2) < 200 else round(real_point * 0.2), "currency": "P"},
            "배율감소1": {"cost": 50 if round(real_point * 0.05) < 50 else round(real_point * 0.05), "currency": "P"},
            "배율감소3": {"cost": 100 if round(real_point * 0.1) < 100 else round(real_point * 0.1), "currency": "P"},
            "배율감소5": {"cost": 200 if round(real_point * 0.2) < 200 else round(real_point * 0.2), "currency": "P"},
            "주사위 초기화": {"cost": 20, "currency": "P"},
            "주사위대결기회 추가": {"cost": 100, "currency": "P"},
            "숫자야구대결기회 추가": {"cost": 100, "currency": "P"},
            "야추 초기화": {"cost": 100, "currency": "P"},
            "완전 익명화": {"cost": 300, "currency": "P"},
            "레이드 재도전": {"cost": 1, "currency": "TC"},
            "탑 재도전": {"cost": 1, "currency": "TC"},
            "강화재료": {"cost": 1, "currency": "TC"},
            "연마제": {"cost": 3, "currency": "TC"},
            "특수 연마제": {"cost": 100, "currency": "TC"},
            "운명 왜곡의 룬": {"cost": 2, "currency": "TC"},
            "랜덤박스": {"cost": 5, "currency": "TC"},
        }

        item_info = item_menu[self.item_name]
        currency = item_info["currency"]
        cost = item_info["cost"]
        if real_point < item_menu[self.item_name]["cost"]: # 포인트가 적을 경우

            if currency == "P":
                if real_point < cost:
                    await interaction.response.send_message(
                        f"포인트가 부족합니다!\n현재 포인트 : {real_point}P | 필요 포인트 : {cost}P", ephemeral=True
                    )
                    return
            elif currency == "TC":
                tc_ref = db.reference(f"무기/아이템/{interaction.user.name}/탑코인")
                topcoin = tc_ref.get() or 0
                if topcoin < cost:
                    await interaction.response.send_message(
                        f"탑코인이 부족합니다!\n현재 탑코인 : {topcoin}TC | 필요 탑코인 : {cost}TC", ephemeral=True
                    )
                    return
        
        class NumberInputModal(discord.ui.Modal, title="개수 입력"):
            def __init__(self, item_name: str):
                super().__init__(title=f"{item_name} 입력")  # 모달 제목 변경 가능
                self.item_name = item_name  # 아이템 이름 저장

                # 입력 필드 생성
                self.number = discord.ui.TextInput(
                    label=f"{item_name}의 수량을 입력하세요",
                    style=discord.TextStyle.short,
                    required=True
                )

                # ✅ TextInput을 명시적으로 추가
                self.add_item(self.number)

            async def on_submit(self, interaction: discord.Interaction):
                try:
                    num = int(self.number.value)  # 입력값을 정수로 변환
                    if currency == "P":
                        total_cost = cost * num
                        if real_point < total_cost: # 포인트가 적을 경우
                            await interaction.response.send_message(f"포인트가 부족합니다!\n현재 포인트 : {real_point}P | 필요 포인트 : {total_cost}P",ephemeral=True)
                            return       
                        give_item(interaction.user.name,self.item_name, num)
                        point_ref.update({"포인트" : point - total_cost})

                        current_datetime = datetime.now() # 데이터베이스에 남길 현재 시각 기록
                        current_date = current_datetime.strftime("%Y-%m-%d")
                        current_time = current_datetime.strftime("%H:%M:%S")
                        change_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트변동로그/{current_date}/{interaction.user.name}")
                        change_ref.push({
                            "시간": current_time,
                            "포인트": point - total_cost,
                            "포인트 변동": -total_cost,
                            "사유": f"{self.item_name} 구매"
                        })

                        await interaction.response.send_message(f"[{self.item_name}] 아이템을 {num}개 구매했습니다!\n현재 포인트 : {real_point - total_cost}P (-{total_cost}P)",ephemeral=True)
                    
                    elif currency == "TC":
                        total_cost = cost * num
                        tc_ref = db.reference(f"무기/아이템/{interaction.user.name}/탑코인")
                        topcoin = tc_ref.get() or 0
                        if topcoin < total_cost:
                            await interaction.response.send_message(f"탑코인이 부족합니다!\n현재 탑코인 : {topcoin}TC | 필요 탑코인 : {total_cost}TC",ephemeral=True)
                            return
                        give_item(interaction.user.name,self.item_name, num)
                        tc_ref.set(topcoin - total_cost)
                        await interaction.response.send_message(f"[{self.item_name}] 아이템을 {num}개 구매했습니다!\n현재 탑코인 : {topcoin - total_cost}TC (-{total_cost}TC)",ephemeral=True)
                    
                except ValueError:
                    await interaction.response.send_message("올바른 숫자를 입력해주세요!", ephemeral=True)

        await interaction.response.send_modal(NumberInputModal(self.item_name))
        self.disabled = True

    def update_label(self):
        if self.item_name:
            self.label = f"[{self.item_name}] 구매"
        else:
            self.label = "아이템 구매"

# 아이템 선택 셀렉트
class ItemSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label = "배율증가 0.1", value = "배율증가1", description = "배율을 0.1 증가시킵니다. 현재 포인트의 5% 혹은 50p로 구매 가능합니다."),
            discord.SelectOption(label = "배율증가 0.3", value = "배율증가3", description = "배율을 0.3 증가시킵니다. 현재 포인트의 10% 혹은 100p로 구매 가능합니다."),
            discord.SelectOption(label = "배율증가 0.5", value = "배율증가5", description = "배율을 0.5 증가시킵니다. 현재 포인트의 20% 혹은 200p로 구매 가능합니다."),
            discord.SelectOption(label = "배율감소 0.1", value = "배율감소1", description = "배율을 0.1 감소시킵니다. 현재 포인트의 5% 혹은 50p로 구매 가능합니다."),
            discord.SelectOption(label = "배율감소 0.3", value = "배율감소3", description = "배율을 0.3 감소시킵니다. 현재 포인트의 10% 혹은 100p로 구매 가능합니다."),
            discord.SelectOption(label = "배율감소 0.5", value = "배율감소5", description = "배율을 0.5 감소시킵니다. 현재 포인트의 20% 혹은 200p로 구매 가능합니다."),
            discord.SelectOption(label = "주사위 초기화", value = "주사위 초기화", description = "현재 주사위 값을 초기화하고 한번 더 던질 수 있게 합니다. 20p로 구매 가능합니다."),
            discord.SelectOption(label = "주사위대결기회 추가", value = "주사위대결기회 추가", description = "주사위 대결을 한 뒤에도 다시 한번 대결을 신청할 수 있습니다. 100p로 구매 가능합니다."),
            discord.SelectOption(label = "숫자야구대결기회 추가", value = "숫자야구대결기회 추가", description = "숫자야구 대결을 한 뒤에도 다시 한번 대결을 신청할 수 있습니다. 100p로 구매 가능합니다."),
            discord.SelectOption(label = "야추 초기화", value = "야추 초기화", description = "현재 야추 값을 초기화하고 한번 더 던질 수 있게 합니다. 100p로 구매 가능합니다."),
            discord.SelectOption(label = "완전 익명화", value = "완전 익명화", description = "다음 승부예측에 투표인원, 포인트, 메세지가 전부 나오지 않는 완전한 익명화를 적용합니다. 300p로 구매 가능합니다."),
            discord.SelectOption(label = "레이드 재도전", value = "레이드 재도전", description = "레이드에 참여했던 기록을 없애고 다시 도전합니다. 1TC로 구매 가능합니다."),
            discord.SelectOption(label = "탑 재도전", value = "탑 재도전", description = "탑에 다시 도전합니다. 1TC로 구매 가능합니다."),
            discord.SelectOption(label = "강화재료", value = "강화재료", description = "강화에 필요한 재료입니다. 1TC로 구매 가능합니다."),
            discord.SelectOption(label = "연마제", value = "연마제", description = "강화 확률을 5% 올립니다. 3TC로 구매 가능합니다."),
            discord.SelectOption(label = "특수 연마제", value = "특수 연마제", description = "강화 확률을 50% 올립니다. 100TC로 구매 가능합니다."),
            discord.SelectOption(label = "운명 왜곡의 룬", value = "운명 왜곡의 룬", description = "사용 시 추가 강화 수치를 랜덤으로 재구성합니다. 2TC로 구매 가능합니다."),
            discord.SelectOption(label = "랜덤박스", value = "랜덤박스", description = "강화재료, 연마제, 레이드 재도전권, 특수 연마제 등이 들어있는 랜덤박스입니다. 5TC로 구매 가능합니다."),
        ]
        super().__init__(
            placeholder = '구매할 아이템을 선택하세요.',
            min_values = 1,
            max_values = 1,
            options = options
        )
    
    async def callback(self, interaction: discord.Interaction):
        selected_item = self.values[0]
        
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
        current_predict_season = cur_predict_seasonref.get()
        point_ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{interaction.user.name}')
        predict_data = point_ref.get()
        point = predict_data["포인트"]
        bettingPoint = predict_data["베팅포인트"]

        real_point = point - bettingPoint
        item_menu = {
            "배율증가1": {"cost": 50 if round(real_point * 0.05) < 50 else round(real_point * 0.05), "currency": "P"},
            "배율증가3": {"cost": 100 if round(real_point * 0.1) < 100 else round(real_point * 0.1), "currency": "P"},
            "배율증가5": {"cost": 200 if round(real_point * 0.2) < 200 else round(real_point * 0.2), "currency": "P"},
            "배율감소1": {"cost": 50 if round(real_point * 0.05) < 50 else round(real_point * 0.05), "currency": "P"},
            "배율감소3": {"cost": 100 if round(real_point * 0.1) < 100 else round(real_point * 0.1), "currency": "P"},
            "배율감소5": {"cost": 200 if round(real_point * 0.2) < 200 else round(real_point * 0.2), "currency": "P"},
            "주사위 초기화": {"cost": 20, "currency": "P"},
            "주사위대결기회 추가": {"cost": 100, "currency": "P"},
            "숫자야구대결기회 추가": {"cost": 100, "currency": "P"},
            "야추 초기화": {"cost": 100, "currency": "P"},
            "완전 익명화": {"cost": 300, "currency": "P"},
            "레이드 재도전": {"cost": 1, "currency": "TC"},
            "탑 재도전": {"cost": 1, "currency": "TC"},
            "강화재료": {"cost": 1, "currency": "TC"},
            "연마제": {"cost": 3, "currency": "TC"},
            "특수 연마제": {"cost": 100, "currency": "TC"},
            "운명 왜곡의 룬": {"cost": 2, "currency": "TC"},
            "랜덤박스": {"cost": 5, "currency": "TC"},
        }

        description = {
            "배율증가1": "배율을 0.1 증가시킵니다. 현재 포인트의 5% 혹은 50p로 구매 가능합니다.",
            "배율증가3": "배율을 0.3 증가시킵니다. 현재 포인트의 10% 혹은 100p로 구매 가능합니다.",
            "배율증가5": "배율을 0.5 증가시킵니다. 현재 포인트의 20% 혹은 200p로 구매 가능합니다.",
            "배율감소1": "배율을 0.1 감소시킵니다. 현재 포인트의 5% 혹은 50p로 구매 가능합니다.",
            "배율감소3": "배율을 0.3 감소시킵니다. 현재 포인트의 10% 혹은 100p로 구매 가능합니다.",
            "배율감소5": "배율을 0.5 감소시킵니다. 현재 포인트의 20% 혹은 200p로 구매 가능합니다.",
            "주사위 초기화": "현재 주사위 값을 초기화하고 한번 더 던질 수 있게 합니다. 20p로 구매 가능합니다.",
            "주사위대결기회 추가": "주사위 대결을 한 뒤에도 다시 한번 대결을 신청할 수 있습니다. 100p로 구매 가능합니다.",
            "숫자야구대결기회 추가": "숫자야구 대결을 한 뒤에도 다시 한번 대결을 신청할 수 있습니다. 100p로 구매 가능합니다.",
            "야추 초기화": "현재 야추 값을 초기화하고 한번 더 던질 수 있게 합니다. 100p로 구매 가능합니다.",
            "완전 익명화": "다음 승부예측에 투표인원, 포인트, 메세지가 전부 나오지 않는 완전한 익명화를 적용합니다. 300p로 구매 가능합니다",
            "레이드 재도전": "레이드에 참여했던 기록을 없애고 다시 도전합니다. 1IC로 구매 가능합니다.",
            "탑 재도전": "탑에 다시 도전합니다. 1IC로 구매 가능합니다.",
            "강화재료" : "강화에 필요한 재료입니다. 1TC로 구매 가능합니다.",
            "연마제" : "다음 강화 확률을 5% 올립니다. 3TC로 구매 가능합니다.",
            "특수 연마제" : "다음 강화 확률을 50% 올립니다. 100TC로 구매 가능합니다.",
            "운명 왜곡의 룬" : "사용 시 추가 강화 수치를 랜덤으로 재구성합니다. 2TC로 구매 가능합니다.",
            "랜덤박스" : "강화재료, 연마제, 레이드 재도전권, 특수 연마제 등이 들어있는 랜덤박스입니다. 5TC로 구매 가능합니다."
        }
        
        ref_tc = db.reference(f'무기/아이템/{interaction.user.name}')
        tc_data = ref_tc.get()
        TC = tc_data.get('탑코인', 0)

        item_price = item_menu[selected_item]["cost"]
        item_currency = item_menu[selected_item]["currency"]
        shop_embed = discord.Embed(title = '구매할 아이템을 선택하세요', color = 0xfffff)
        if item_currency == "P":
            shop_embed.add_field(name = f'{interaction.user.name}의 현재 포인트', value = f'**{point - bettingPoint}P** (베팅포인트 **{bettingPoint}P** 제외)', inline = False)
        else:
            shop_embed.add_field(name = f'{interaction.user.name}의 현재 탑코인', value = f'**{TC}TC**', inline = False)
        shop_embed.add_field(name = f'아이템 가격', value = f'**{item_price}{item_currency}**', inline = False)
        shop_embed.add_field(name = f'설명', value = f'**{description[selected_item]}**', inline = False)

        buy_button = next(
            (item for item in self.view.children if isinstance(item, ItemBuyButton)),
            None
        )

        if buy_button:
            buy_button.item_name = selected_item
            buy_button.update_label()
            buy_button.disabled = False

        await interaction.response.edit_message(embed = shop_embed, view = self.view)

# 대결 예측 시스템 초기화
async def initialize_prediction(bot, challenger, 상대, channel_id, what):
    """ 승부 예측 시스템을 초기화하는 함수 """
    channel = bot.get_channel(int(channel_id))
    
    # 예측 데이터 초기화
    p.votes['배틀']['name']['challenger'] = challenger
    p.votes['배틀']['name']['상대'] = 상대
    
    p.battle_winbutton = discord.ui.Button(style=discord.ButtonStyle.success, label=f"{challenger.name} 승리")
    losebutton = discord.ui.Button(style=discord.ButtonStyle.danger, label=f"{상대.name} 승리")

    # 버튼에 콜백 할당
    p.battle_winbutton.callback = lambda interaction: bet_button_callback(interaction, 'win', bot, p, challenger, 상대)
    losebutton.callback = lambda interaction: bet_button_callback(interaction, 'lose', bot, p, challenger, 상대)

    # 초기 임베드 생성
    prediction_embed = update_prediction_embed(p, challenger, 상대)
    
    prediction_view = discord.ui.View()
    prediction_view.add_item(p.battle_winbutton)
    prediction_view.add_item(losebutton)
    
    if what == "주사위":
        # 메시지 전송
        p.battle_message = await channel.send(
            f"{challenger.mention} vs {상대.mention}의 주사위 승부가 감지되었습니다! \n승부예측을 해보세요!",
            view=prediction_view,
            embed=prediction_embed
        )
    elif what == "숫자야구":
        # 메시지 전송
        p.battle_message = await channel.send(
            f"{challenger.mention} vs {상대.mention}의 숫자야구 승부가 감지되었습니다! \n승부예측을 해보세요!",
            view=prediction_view,
            embed=prediction_embed
        )

# 대결 예측 버튼 비활성화
async def disable_buttons():
    """ 1분 후 버튼을 비활성화하는 함수 """
    await asyncio.sleep(60)  # 1분 대기
    p.battle_winbutton.disabled = True
    losebutton = discord.ui.Button(style=discord.ButtonStyle.danger, label=f"{p.votes['배틀']['name']['상대'].name} 승리", disabled=True)

    prediction_view = discord.ui.View()
    prediction_view.add_item(p.battle_winbutton)
    prediction_view.add_item(losebutton)

    await p.battle_message.edit(view=prediction_view)
    p.battle_event.set()

# 대결 예측 버튼 콜백
async def bet_button_callback(interaction, prediction_type, bot, p, challenger, 상대):
    """ 예측 버튼을 눌렀을 때 호출되는 함수 """
    nickname = interaction.user.name
    await interaction.response.defer()  # 응답 지연 (오류 방지)

    # 본인 투표 금지
    if nickname in [challenger.name, 상대.name]:
        userembed = discord.Embed(title="메세지", color=discord.Color.blue())
        userembed.add_field(name="자신에게 투표 불가!", value="자신의 승부에는 투표할 수 없습니다!")
        await interaction.followup.send(embed=userembed, ephemeral=True)
        return

    # 중복 투표 방지
    if nickname in [user['name'].name for user in p.votes['배틀']['prediction']["win"]] or \
       nickname in [user['name'].name for user in p.votes['배틀']['prediction']["lose"]]:
        userembed = discord.Embed(title="메세지", color=discord.Color.blue())
        userembed.add_field(name="", value=f"{interaction.user.display_name}님은 이미 투표하셨습니다", inline=True)
        await interaction.followup.send(embed=userembed, ephemeral=True)
        return

    # 포인트 정보 가져오기
    cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
    current_predict_season = cur_predict_seasonref.get()
    refp = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname}')
    pointr = refp.get()
    point = pointr["포인트"]
    bettingPoint = pointr["베팅포인트"]

    # 자동 배팅 계산 (1%~5%)
    random_number = random.uniform(0.01, 0.05)
    baseRate = round(random_number, 2)
    basePoint = round(point * baseRate) if point - bettingPoint >= 500 else 0
    if basePoint > 0:
        basePoint = math.ceil(basePoint / 10) * 10  # 10 단위 올림

    # 베팅 반영
    refp.update({"베팅포인트": bettingPoint + basePoint})
    p.votes['배틀']['prediction'][prediction_type].append({"name": interaction.user, 'points': basePoint})

    # UI 업데이트
    prediction_embed = update_prediction_embed(p, challenger, 상대)
    await p.battle_message.edit(embed=prediction_embed)

    # 메시지 전송
    channel = bot.get_channel(int(CHANNEL_ID))
    prediction_value = challenger if prediction_type == "win" else 상대

    userembed = discord.Embed(title="메세지", color=discord.Color.blue())
    userembed.add_field(name="", value=f"{interaction.user.display_name}님이 {prediction_value.mention}에게 투표하셨습니다.", inline=True)
    #await channel.send(embed=userembed)

    if basePoint != 0:
        bettingembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
        bettingembed.add_field(name="", value=f"{interaction.user.display_name}님이 {prediction_value.mention}에게 {basePoint}포인트를 베팅했습니다!", inline=False)
        await channel.send(embed=bettingembed)

    # 미션 처리
    ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname}/미션/일일미션/승부예측 1회")
    mission = ref.get()
    if mission and not mission.get('완료', False):
        ref.update({"완료": True})
        print(f"{nickname}의 [승부예측 1회] 미션 완료")

# 대결 예측 현황 업데이트
def update_prediction_embed(p, challenger, 상대):
    """ 예측 현황을 업데이트하는 함수 """
    prediction_embed = discord.Embed(title="예측 현황", color=0x000000)  # Black

    win_predictions = "\n".join(
        f"{winner['name'].display_name}: {winner['points']}포인트" for winner in p.votes['배틀']['prediction']["win"]
    ) or "없음"
    lose_predictions = "\n".join(
        f"{loser['name'].display_name}: {loser['points']}포인트" for loser in p.votes['배틀']['prediction']["lose"]
    ) or "없음"

    winner_total_point = sum(winner["points"] for winner in p.votes['배틀']['prediction']["win"])
    loser_total_point = sum(loser["points"] for loser in p.votes['배틀']['prediction']["lose"])
    prediction_embed.add_field(name="총 포인트", value=f"{challenger.name}: {winner_total_point}포인트 | {상대.name}: {loser_total_point}포인트", inline=False)
    prediction_embed.add_field(name=f"{challenger.display_name} 승리 예측", value=win_predictions, inline=True)
    prediction_embed.add_field(name=f"{상대.display_name} 승리 예측", value=lose_predictions, inline=True)

    return prediction_embed

# 모두에게 미션 추가
async def add_missions_to_all_users(mission_name,point,mission_type):
    cur_predict_seasonref = db.reference("승부예측/현재예측시즌") # 현재 진행중인 예측 시즌을 가져옴
    current_predict_season = cur_predict_seasonref.get()
    # '예측포인트' 경로 아래의 모든 유저들 가져오기
    ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트")
    all_users = ref.get()
    
    # 각 유저에게 미션 추가
    if all_users:
        for user_id, user_data in all_users.items():
            # 각 유저의 '미션' 경로
            user_daily_missions_ref = ref.child(user_id).child("미션").child(mission_type)

            # 미션 타입에 해당하는 기존 미션 목록을 가져와서 ID 생성
            mission_type_data = user_data.get("미션", {}).get(mission_type, {})

            new_mission = {
                "완료": False,
                "보상수령": False,
                "포인트": point
            }
            # 미션 이름을 키로 사용하여 미션 추가
            user_daily_missions_ref.child(mission_name).set(new_mission)
        return True
    else:
        return False
        
async def get_summoner_puuid(riot_id, tagline):
    url = f'https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{riot_id}/{tagline}'
    headers = {'X-Riot-Token': API_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data['puuid']
            else:
                print('Error:', response.status)
                return None

async def get_summoner_id(puuid):
    url = f'https://kr.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}'
    headers = {'X-Riot-Token': API_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data['id']
            else:
                print('Error:', response.status)
                return None

async def get_summoner_ranks(summoner_id, type="솔랭"):
    url = f'https://kr.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}'
    headers = {'X-Riot-Token': API_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                if type == "솔랭":
                    # queueType이 RANKED_SOLO_5x5인 경우만 가져오기
                    filtered_data = [entry for entry in data if entry.get("queueType") == "RANKED_SOLO_5x5"]
                elif type == "자랭":
                    # queueType이 RANKED_FLEX_SR인 경우만 가져오기
                    filtered_data = [entry for entry in data if entry.get("queueType") == "RANKED_FLEX_SR"]
                if filtered_data:
                    return filtered_data[0]  # 첫 번째 티어 정보만 반환
                else:
                    return []
            elif response.status == 404:
                raise NotFoundError("404 Error occurred")
            else:
                print('Error:', response.status)
                return None

async def get_summoner_recentmatch_id(puuid):
    url = f'https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?queue=420&type=ranked&start=0&count=1'
    headers = {'X-Riot-Token': API_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data[0] if data else None
            else:
                print('Error:', response.status)
                return None

async def get_summoner_matchinfo(matchid):
    url = f'https://asia.api.riotgames.com/lol/match/v5/matches/{matchid}'
    headers = {'X-Riot-Token': API_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                print('Error:', response.status)
                return None

def get_summoner_matchinfo_nonaysnc(matchid): #matchid로 매치 정보 구하기
    url = f'https://asia.api.riotgames.com/lol/match/v5/matches/{matchid}'
    headers = {'X-Riot-Token': API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 404:
        raise NotFoundError("404 Error occurred")
    else:
        print('Error:', response.status_code)
        return None

# 임베드를 생성하는 함수 (명령어 목록을 페이지별로 나누기)
def create_embed(commands_list, current_page, page_size):
    embed = discord.Embed(title="명령어 목록", color=discord.Color.green())
    start_index = current_page * page_size
    end_index = min((current_page + 1) * page_size, len(commands_list))

    # 현재 페이지에 해당하는 명령어들만 추가
    for cmd in commands_list[start_index:end_index]:
        embed.add_field(name=f"</{cmd.name}:{cmd.id}>", value=cmd.description, inline=False)
    return embed

# 야추 다이스 굴리기
class DiceRollView(discord.ui.View):
    def __init__(self, user, initial_rolls, reroll_count=0):
        super().__init__(timeout=60)
        self.user = user
        self.rolls = initial_rolls
        self.hold = [False] * 5  # 각 주사위가 hold 상태인지 저장
        self.reroll_count = reroll_count
        self.max_rerolls = 2
        self.keep_alive_task = None
        self.update_buttons()

    def toggle_hold(self, index):
        """주사위의 hold 상태를 토글합니다."""
        self.hold[index] = not self.hold[index]
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        for idx, roll in enumerate(self.rolls):
            label = f"🎲 {roll}{' 🔒' if self.hold[idx] else ''}"
            self.add_item(DiceButton(idx, label, self))
        if self.reroll_count < self.max_rerolls:
            self.add_item(RerollButton(self))
            self.add_item(FinalizeButton(self))
        else:
            self.add_item(FinalizeButton(self))

    async def timer_task(self):
        try:
            await asyncio.sleep(120)
            self.clear_items()

            result = ', '.join(str(roll) for roll in self.rolls)
            hand = evaluate_hand(self.rolls)  # 족보 판별
            embed = discord.Embed(
                title="🎲 주사위 굴리기!",
                description=f"{self.user}님의 주사위: **{result}**\n 족보: **{hand}**",
                color=discord.Color.blue()
            )

            await self.message.edit(embed=embed,view = self)
        except asyncio.CancelledError:
            # 타이머가 취소되었을 경우 예외 무시
            return

    async def start_timer(self):
        """타이머 백그라운드 태스크 시작"""
        self.keep_alive_task = asyncio.create_task(self.timer_task())

# 야추 다이스 버튼
class DiceButton(discord.ui.Button):
    def __init__(self, index, label, view):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.index = index
        self.custom_view = view 

    async def callback(self, interaction: discord.Interaction):
        user = interaction.user
        if user != self.custom_view.user:  
            await interaction.response.send_message("이 주사위는 당신의 것이 아닙니다!", ephemeral=True)
            return

        self.custom_view.toggle_hold(self.index)
        await interaction.response.edit_message(view=self.custom_view)

# 야추 다이스 다시 굴리기 버튼
class RerollButton(discord.ui.Button):
    def __init__(self, view):
        super().__init__(style=discord.ButtonStyle.success, label="🎲 다시 굴리기")
        self.custom_view = view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.custom_view.user:  
            await interaction.response.send_message("이 주사위는 당신의 것이 아닙니다!", ephemeral=True)
            return
        for idx in range(5):
            if not self.custom_view.hold[idx]:
                self.custom_view.rolls[idx] = random.randint(1, 6)
        self.custom_view.reroll_count += 1
        self.custom_view.update_buttons()
        result = ', '.join(str(roll) for roll in self.custom_view.rolls) 
        embed = discord.Embed(
            title="🎲 주사위 굴리기!",
            description=f"{interaction.user.name}님의 주사위: **{result}**",
            color=discord.Color.blue()
        )
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
        current_predict_season = cur_predict_seasonref.get()

        ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{interaction.user.name}/야추")
        ref.update({"실행 여부":True})
        ref.update({"결과": self.custom_view.rolls})
        ref.update({"족보": evaluate_hand(self.custom_view.rolls)})
        
        await interaction.response.edit_message(view=self.custom_view, embed = embed)

# 야추 다이스 확정 버튼
class FinalizeButton(discord.ui.Button):
    def __init__(self, view):
        super().__init__(style=discord.ButtonStyle.danger, label="✅ 확정")
        self.custom_view = view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.custom_view.user:
            await interaction.response.send_message("이 주사위는 당신의 것이 아닙니다!", ephemeral=True)
            return
        
        result = ', '.join(str(roll) for roll in self.custom_view.rolls)
        hand = evaluate_hand(self.custom_view.rolls)  # 족보 판별
        embed = discord.Embed(
            title="🎲 주사위 굴리기!",
            description=f"{interaction.user.name}님의 주사위: **{result}**\n 족보: **{hand}**",
            color=discord.Color.blue()
        )
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
        current_predict_season = cur_predict_seasonref.get()

        ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{interaction.user.name}/야추")
        ref.update({"실행 여부":True})
        ref.update({"결과": self.custom_view.rolls})
        ref.update({"족보": hand})

        if self.custom_view.keep_alive_task:
            self.custom_view.keep_alive_task.cancel()
            try:
                await self.custom_view.keep_alive_task
            except asyncio.CancelledError:
                pass

        await interaction.response.edit_message(content="", view=None, embed = embed)

# 야추 다이스 족보 판별
def evaluate_hand(rolls):
    from collections import Counter
    
    counts = Counter(rolls)
    count_values = sorted(counts.values(), reverse=True)
    rolls_sorted = sorted(rolls)

    # Yahtzee
    if count_values[0] == 5:
        return "🎉 Yacht!"

    # Large Straight (1-5 or 2-6)
    elif rolls_sorted == [1, 2, 3, 4, 5] or rolls_sorted == [2, 3, 4, 5, 6]:
        return "➡️ Large Straight!"

    # Small Straight (any 4 consecutive numbers)
    elif any(all(num in rolls_sorted for num in seq) for seq in ([1,2,3,4], [2,3,4,5], [3,4,5,6])):
        return "🡒 Small Straight!"

    # Full House
    elif count_values == [3, 2]:
        return "🏠 Full House!"

    # Four of a Kind
    elif count_values[0] == 4:
        return "🔥 Four of a Kind!"

    # Chance
    else:
        total = sum(rolls)
        return f"🎲 Chance! (합계: {total})"

# 경고 지급 모달
class WarnModal(Modal):
    reason = TextInput(label="경고 사유", placeholder="경고 사유를 입력하세요.")

    def __init__(self, message: discord.Message):
        super().__init__(title="경고 사유 입력")
        self.message = message

    async def on_submit(self, interaction: discord.Interaction):
        warned_user = self.message.author
        moderator = interaction.user
        reason = self.reason.value
        
        WARNING_EMOJI = '⚠️'  # 경고 이모지

        # 임베드 생성
        embed = discord.Embed(title="🚨 경고 기록", color=discord.Color.red())
        embed.add_field(name="경고 대상", value=warned_user.mention, inline=True)
        embed.add_field(name="경고 발령자", value=moderator.mention, inline=True)
        embed.add_field(name="경고 사유", value=reason, inline=False)
        embed.add_field(name="대상 메시지", value=self.message.content, inline=False)
        embed.set_footer(text=f"메시지 ID: {self.message.id}")

        # 버튼 생성
        button = discord.ui.Button(label="원본 메시지로 이동", url=f"https://discord.com/channels/{self.message.guild.id}/{self.message.channel.id}/{self.message.id}")
        view = discord.ui.View()
        view.add_item(button)
        
        channel = interaction.client.get_channel(self.message.channel.id)
        message = await channel.fetch_message(self.message.id)
        await message.add_reaction(WARNING_EMOJI)
        # 경고 채널에 임베드 전송
        warning_channel = interaction.client.get_channel(WARNING_CHANNEL_ID)
        if warning_channel:
            await warning_channel.send(embed=embed, view = view)
            await interaction.response.send_message(embed=embed, view = view)
        else:
            await interaction.response.send_message("경고 채널을 찾을 수 없습니다.", ephemeral=True)

# 경고 지급 명령어 모달
class WarnCommandModal(discord.ui.Modal, title="경고 기록"):
    def __init__(self, bot: commands.Bot, member: discord.Member):
        super().__init__()
        self.bot = bot
        self.member = member

        self.reason = discord.ui.TextInput(label="경고 사유", placeholder="경고 사유를 입력하세요.", max_length=100)
        self.details = discord.ui.TextInput(label="자세한 경위", style=discord.TextStyle.paragraph, placeholder="상세 설명 입력...", max_length=1000)

        self.add_item(self.reason)
        self.add_item(self.details)

    async def on_submit(self, interaction: discord.Interaction):
        warn_channel = interaction.client.get_channel(WARNING_CHANNEL_ID)
        if not warn_channel:
            await interaction.response.send_message("⚠️ 경고 채널을 찾을 수 없습니다.", ephemeral=True)
            return
        
        channel = self.bot.get_channel(int(CHANNEL_ID)) #tts 채널 

        embed = discord.Embed(title="🚨 경고 기록", color=discord.Color.red())
        embed.add_field(name="경고 대상", value=self.member.mention, inline=False)
        embed.add_field(name="경고 사유", value=self.reason.value, inline=False)
        embed.add_field(name="자세한 경위", value=self.details.value, inline=False)
        embed.set_footer(text=f"경고 발송자: {interaction.user}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)

        await warn_channel.send(embed=embed)
        await channel.send(embed=embed)
        await interaction.response.send_message(f"{self.member.mention}에게 경고를 부여했습니다.", ephemeral=True)

# 경고 지급 명령어 뷰
class WarnCommandView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

        self.select = discord.ui.Select(
            placeholder="경고할 멤버를 선택하세요.",
            min_values=1,
            max_values=1,
            options=[]
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        member_id = int(self.select.values[0])
        member = interaction.guild.get_member(member_id)
        if member:
            await interaction.response.send_modal(WarnCommandModal(self.bot, member))
        else:
            await interaction.response.send_message("⚠️ 해당 멤버를 찾을 수 없습니다.", ephemeral=True)

    async def populate_members(self, guild: discord.Guild):
        self.select.options = [
            discord.SelectOption(label=member.display_name, value=str(member.id))
            for member in guild.members if not member.bot
        ]


def plot_lp_difference_firebase(season=None,name=None,rank=None):
    if season == None:
        # 현재 날짜 및 시간 가져오기
        curseasonref = db.reference("전적분석/현재시즌")
        current_season = curseasonref.get()
        season = current_season

    if name == None:
        name = "지모"
    
    if rank == None:
        rank = "솔로랭크"
    
    print(season)
    ref = db.reference(f'전적분석/{season}/점수변동/{name}/{rank}')
    lp_difference = ref.get()
    if lp_difference == None:
        return -1

    lp_scores = []
    # 각 날짜의 데이터를 정리하여 리스트에 추가
    for date, entries in lp_difference.items():
        for entry in entries.values():
            score = entry.get('현재 점수')
            lp_scores.append(score)

    # 한글 폰트 지정
    # 운영 체제 확인
    if platform.system() == 'Windows':
        font_path = "C:/Windows/Fonts/malgun.ttf"
    elif platform.system() == 'Linux':
        font_path = "/usr/share/fonts/nanum/NanumGothic.ttf"  # 리눅스에서는 적절한 폰트 경로로 수정

    font_name = font_manager.FontProperties(fname=font_path).get_name()
    rc('font', family=font_name)
    # 그래프 그리기
    if name == '지모':
        plt.plot(lp_scores, marker='', linestyle='-',color ="dodgerblue")
    if name == 'Melon':
        plt.plot(lp_scores, marker='', linestyle='-',color ="violet")
    plt.title(f"{name} {rank} LP 변화량 추이")
    plt.xlabel('게임 플레이 판수')
    plt.ylabel('현재 LP 점수')
    xticks = []
    for i in range(0, len(lp_scores)):
        xticks.append(i)

    if len(lp_scores) >= 20:
        # 판수 5판 간격마다 xticks 설정
        xticks = list(range(0, len(lp_scores), 5))
    if len(lp_scores) >= 100:
        # 판수 10판 간격마다 xticks 설정
        xticks = list(range(0, len(lp_scores), 10))
    if len(lp_scores) >= 200:
        # 판수 20판 간격마다 xticks 설정
        xticks = list(range(0, len(lp_scores), 20))
    if len(lp_scores) >= 300:
        # 판수 20판 간격마다 xticks 설정
        xticks = list(range(0, len(lp_scores), 30))
    plt.xticks(xticks)
    plt.tight_layout()

    # 최고점과 최저점 계산
    min_lp = min(lp_scores)
    max_lp = max(lp_scores)


    '''
    # Y축 레이블 설정
    yticks = [min_lp, max_lp]
    interval = (max_lp - min_lp) // 5
    for i in range(min_lp + interval, max_lp, interval):
        yticks.append(i)
    '''

    # 티어 분기점 설정 (50점 간격)
    tier_breakpoints = list(range((min_lp // 50) * 50, max_lp + 1, 50))

    # Y 축 레이블 설정
    plt.yticks(tier_breakpoints, [number_to_tier2(lp) for lp in tier_breakpoints])


    # 티어 분기점 설정 (100점 간격)
    tier_breakpoints = list(range((min_lp // 100) * 100, max_lp + 1, 100))

    # 티어 분기점에 점선 추가
    for tier_point in tier_breakpoints:
        plt.axhline(y=tier_point, color='gray', linestyle='--')


    # Y축 레이블 수정 (티어 및 랭크로 변경)
    #plt.yticks(yticks, [number_to_tier2(lp) for lp in yticks])

    # 그래프를 이미지 파일로 저장
    plt.savefig('lp_graph.png')
    plt.close()
    return 0

async def plot_prediction_graph(season=None, user_name=None):
    # 로그 데이터가 저장된 경로
    data_ref = db.reference(f"승부예측/예측시즌/{season}/예측포인트변동로그")
    # 날짜 리스트와 포인트 리스트
    dates = []
    points = []

    # Firebase에서 날짜별 포인트 변동 로그 가져오기
    logs = data_ref.get()

    # 포인트 변동 데이터를 하나하나 처리
    for date_str, date_data in logs.items():
        user_data = date_data.get(user_name)
        if user_data:
            for log_key, log_data in user_data.items():
                # 각 포인트 변동 정보 추출
                point = log_data.get('포인트')
                time = log_data.get('시간')  # 변동 시간

                if point is not None:
                    points.append((time, point))  # 시간, 포인트, 사유 추가

    # 그래프 그리기
    if points:
        plt.figure(figsize=(10, 6))
        plt.rcParams['font.family'] = 'NanumGothic'

        # 시간 데이터를 datetime 객체로 변환 (시간 형식: '%H:%M:%S')
        times = [datetime.strptime(pt[0], '%H:%M:%S') for pt in points]
        point_values = [pt[1] for pt in points]  # 포인트 값 추출

        # 포인트 변동 그래프
        plt.plot(times, point_values, marker='o', linestyle='-', color='b', label=f"{user_name}의 포인트 변동")

        # x-axis 날짜/시간 포맷
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))  # 시간 형식
        plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=1))  # x-axis 시간 간격 설정

        # 그래프 제목, 레이블
        plt.title(f'{user_name}의 포인트 변동 그래프')
        plt.xlabel('시간')
        plt.ylabel('포인트')

        plt.xticks(rotation=45)  # 시간 라벨 회전
        plt.grid(True)
        plt.tight_layout()

    # 그림을 파일로 저장
    plt.savefig('prediction_graph.png')
    plt.close()
    return 1

async def plot_candle_graph(시즌:str, 이름:str, 랭크:str):
    ref = db.reference(f'전적분석/{시즌}/점수변동/{이름}/{랭크}')
    data = ref.get()

    if data == None:
        return None
    date_list = []

    # 최고 점수와 최저 점수 초기화
    highest_score = float('-inf')
    lowest_score = float('inf')

    # 각 날짜의 데이터를 정리하여 리스트에 추가
    for date, entries in data.items():
        total_lp_change = 0
        max_score = float('-inf')  # 최고 점수를 음의 무한대로 초기화
        min_score = float('inf')   # 최저 점수를 양의 무한대로 초기화
        start_score = None
        final_score = None
        game_count = 0  # 판수를 초기화

        for entry in entries.values():
            lp_change = entry.get('LP 변화량', 0)
            score = entry.get('현재 점수', 0)
            game_count += 1

            if start_score is None:
                start_score = score - lp_change

            total_lp_change += lp_change
            max_score = max(max_score, score)
            min_score = min(min_score, score)
            final_score = score  # 반복이 끝날 때의 점수를 최종 점수로 설정
        # 최고 점수와 최저 점수 업데이트
        highest_score = max(highest_score, max_score)
        lowest_score = min(lowest_score, min_score)

        date_list.append({
            '날짜': date,
            '시작 점수': start_score,
            '총 LP 변화량': total_lp_change,
            '최고 점수': max_score,
            '최저 점수': min_score,
            '최종 점수': final_score,
            '판수': game_count
        })

    highest_tier = number_to_tier(highest_score)
    lowest_tier = number_to_tier(lowest_score)
    basecolor = 0x000000
    embed = discord.Embed(title=f'{이름} 점수 변동', color = basecolor)
    embed.add_field(name="최고점수", value=f"{highest_tier}({highest_score})",inline=False)
    embed.add_field(name="최저점수", value=f"{lowest_tier}({lowest_score})",inline=False)


    # 데이터프레임 생성
    df = pd.DataFrame(date_list)
    df['날짜'] = pd.to_datetime(df['날짜'])
    df.set_index('날짜', inplace=True)

    # 데이터프레임 열 이름 변경 (예: '시작 점수'를 'Open', '최고 점수'를 'High' 등으로 변경)
    df.rename(columns={'시작 점수': 'Open', '최고 점수': 'High', '최저 점수': 'Low', '최종 점수': 'Close', '판수': 'Volume'}, inplace=True)

    def make_mpf_style():
        # marketcolors 설정
        mc = mpf.make_marketcolors(up='red', down='blue')
        # 스타일 설정
        return mpf.make_mpf_style(base_mpf_style = "binance",marketcolors=mc)
    # 캔들스틱 차트 그리기
    fig, axlist = mpf.plot(df, type='candle', style= make_mpf_style(), ylabel='Tier', xlabel='Dates', mav=2, volume=True, ylabel_lower='Games', returnfig=True)

    # 파일 경로 및 이름 설정
    file_path = "candle_graph.png"

    # 그림을 파일로 저장
    fig.savefig(file_path)
    plt.close(fig)
    return embed

async def refresh_prediction(name, anonym, complete_anonym, prediction_votes):
    if name == "지모":
        embed = discord.Embed(title="예측 현황", color=0x000000) # Black
    elif name == "Melon":
        embed = discord.Embed(title="예측 현황", color=discord.Color.brand_green())
    refrate = db.reference(f'승부예측/배율증가/{name}')
    rater = refrate.get()
    if rater['배율'] != 0:
        embed.add_field(name="", value=f"추가 배율 : {rater['배율']}", inline=False)
    if complete_anonym:
        win_predictions = "\n?명"
        lose_predictions = "\n?명"
    elif anonym:
        win_predictions = "\n".join(f"{ANONYM_NAME_WIN[index]}: ? 포인트" for index, user in enumerate(prediction_votes["win"])) or "없음"
        lose_predictions = "\n".join(f"{ANONYM_NAME_LOSE[index]}: ? 포인트" for index, user in enumerate(prediction_votes["lose"])) or "없음"
    else:
        win_predictions = "\n".join(f"{user['name'].display_name}: {user['points']}포인트" for user in prediction_votes["win"]) or "없음"
        lose_predictions = "\n".join(f"{user['name'].display_name}: {user['points']}포인트" for user in prediction_votes["lose"]) or "없음"
    
    winner_total_point = sum(winner["points"] for winner in prediction_votes["win"])
    loser_total_point = sum(loser["points"] for loser in prediction_votes["lose"])
    if complete_anonym:
        embed.add_field(name="총 포인트", value=f"승리: ? 포인트 | 패배: ? 포인트", inline=False)
    else:
        embed.add_field(name="총 포인트", value=f"승리: {winner_total_point}포인트 | 패배: {loser_total_point}포인트", inline=False)
    embed.add_field(name="승리 예측", value=win_predictions, inline=True)
    embed.add_field(name="패배 예측", value=lose_predictions, inline=True)
    
    if name == "지모":
        await p.current_message_jimo.edit(embed=embed)
    elif name == "Melon":
        await p.current_message_melon.edit(embed=embed)

def nowgameinfo(puuid): #puuid를 통해 현재 진행중인 게임의 참가자 정보를 반환
    url = f'https://kr.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}'
    headers = {'X-Riot-Token': API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()["participants"]

async def get_recent_matches(puuid, queue, startNum):
    url = f'https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?queue={queue}&start={startNum}&count=5'
    headers = {'X-Riot-Token': API_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                match_ids = await response.json()
                return match_ids
            elif response.status == 404:
                raise NotFoundError("404 Error occurred")
            elif response.status == 429:
                raise TooManyRequestError("429 Error occurred")
            else:
                print('Error:', response.status)
                return None

async def get_recent_solo_ranked_matches(puuid, startNum):
    return await get_recent_matches(puuid, 420, startNum)

async def get_recent_flex_ranked_matches(puuid, startNum):
    return await get_recent_matches(puuid, 440, startNum)

async def get_recent_clash_matches(puuid, startNum):
    return await get_recent_matches(puuid, 700, startNum)

def get_participant_id(match_info, puuid): # match정보와 puuid를 통해 그 판에서 플레이어의 위치를 반환
    for i, participant in enumerate(match_info['info']['participants']):
        if participant['puuid'] == puuid:
            return i
    return None

async def wins_all_match_info(match_ids, puuid):
    wins_list = []
    async with aiohttp.ClientSession() as session:
       # tasks = [get_match_info(session, match_id) for match_id in match_ids]
        tasks = []
        for match_id in match_ids:
            try:
                task = get_match_info(session, match_id)
            except NotFoundError as e:
                raise NotFoundError
            except TooManyRequestError as e:
                raise TooManyRequestError
            tasks.append(task)
        match_infos = await asyncio.gather(*tasks)
        for match_info in match_infos:
            if match_info:
                participant_id = get_participant_id(match_info, puuid)
                if participant_id is not None:
                    if match_info['info']['participants'][participant_id]['gameEndedInEarlySurrender'] == True and int(match_info['info']['gameDuration']) <= 240:
                        wins_list.append('draw')
                        continue
                    participant = match_info['info']['participants'][participant_id]
                    if participant['win']: wins_list.append('win')
                    else: wins_list.append('lose')
                else:
                    print('Participant not found')
                    wins_list.append(False)  # Participant not found
            else: wins_list.append(False)
    return wins_list

async def get_match_info(session, match_id):
    url = f'https://asia.api.riotgames.com/lol/match/v5/matches/{match_id}'
    headers = {'X-Riot-Token': API_KEY}
    async with session.get(url, headers=headers) as response:
        if response.status == 200:
            return await response.json()
        elif response.status == 404:
            raise NotFoundError("404 Error occurred")
        elif response.status == 429:
            raise TooManyRequestError("429 Error occurred")
        else:
            print(response.status)
            return

# 최근 20경기 승/패 계산
async def calculate_consecutive_matches(puuid):
    url = f'https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?queue=420&type=ranked&start=0&count=30'
    headers = {'X-Riot-Token': API_KEY}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        match_ids = response.json()

        # 매치 ID를 10개씩 3번에 걸쳐 처리
        first_10_matches = match_ids[:10]
        second_10_matches = match_ids[10:20]
        #third_10_matches = match_ids[20:30]

        wins_list = []
        async with aiohttp.ClientSession() as session:
            # 첫 번째 10개 매치에 대한 정보를 비동기적으로 가져옴
            try:
                wins_list.extend(await wins_all_match_info(first_10_matches, puuid))
            except NotFoundError as e:
                raise NotFoundError("404 Error occurred")
            except TooManyRequestError as e:
                raise TooManyRequestError

            #wins_list.extend(await wins_all_match_info(first_10_matches, puuid))
            # 두 번째 10개 매치에 대한 정보를 비동기적으로 가져옴
            #wins_list.extend(await wins_all_match_info(second_10_matches, puuid))
            try:
                wins_list.extend(await wins_all_match_info(second_10_matches, puuid))
            except NotFoundError as e:
                raise NotFoundError("404 Error occurred")
            except TooManyRequestError as e:
                raise TooManyRequestError
            # 세 번째 10개 매치에 대한 정보를 비동기적으로 가져옴
           # wins_list.extend(await wins_all_match_info(third_10_matches, puuid))

        print(wins_list)

        wins = 0
        loss = 0
        draws = 0
        for win in wins_list:
            if win == 'win':
                wins += 1
            elif win == 'draw':
                draws += 1
            elif win == 'lose':
                loss += 1
            else:
                continue

        return wins, draws, loss
    return 0

# 현재 연승을 계산하여 반환
async def calculate_consecutive_wins(puuid):
    url = f'https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?queue=420&type=ranked&start=0&count=20'
    headers = {'X-Riot-Token': API_KEY}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        match_ids = response.json()

        # 매치 ID를 10개씩 3번에 걸쳐 처리
        first_10_matches = match_ids[:7]
        second_10_matches = match_ids[7:14]
        #third_10_matches = match_ids[20:30]

        wins_list = []
        async with aiohttp.ClientSession() as session:
            # 첫 번째 10개 매치에 대한 정보를 비동기적으로 가져옴
            try:
                wins_list.extend(await wins_all_match_info(first_10_matches, puuid))
            except NotFoundError as e:
                raise NotFoundError
            except TooManyRequestError as e:
                raise TooManyRequestError
            # 두 번째 10개 매치에 대한 정보를 비동기적으로 가져옴
            try:
                wins_list.extend(await wins_all_match_info(second_10_matches, puuid))
            except NotFoundError as e:
                raise NotFoundError
            except TooManyRequestError as e:
                raise TooManyRequestError
            # 세 번째 10개 매치에 대한 정보를 비동기적으로 가져옴
           # wins_list.extend(await wins_all_match_info(third_10_matches, puuid))

        print(wins_list)

        win_streak = 0
        for win in wins_list:
            if win == 'win':
                win_streak += 1
            elif win == False:
                return -1
            else:
                break

        return win_streak
    return 0

# 현재 연패를 계산하여 반환
async def calculate_consecutive_losses(puuid):
    url = f'https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?queue=420&type=ranked&start=0&count=20'
    headers = {'X-Riot-Token': API_KEY}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        match_ids = response.json()

        # 매치 ID를 10개씩 3번에 걸쳐 처리
        first_10_matches = match_ids[:7]
        second_10_matches = match_ids[7:14]
        #third_10_matches = match_ids[20:30]

        wins_list = []
        async with aiohttp.ClientSession() as session:
            # 첫 번째 10개 매치에 대한 정보를 비동기적으로 가져옴
            try:
                wins_list.extend(await wins_all_match_info(first_10_matches, puuid))
            except NotFoundError as e:
                raise NotFoundError
            except TooManyRequestError as e:
                raise TooManyRequestError
            # 두 번째 10개 매치에 대한 정보를 비동기적으로 가져옴
            try:
                wins_list.extend(await wins_all_match_info(second_10_matches, puuid))
            except NotFoundError as e:
                raise NotFoundError
            except TooManyRequestError as e:
                raise TooManyRequestError
            # 세 번째 10개 매치에 대한 정보를 비동기적으로 가져옴
           # wins_list.extend(await wins_all_match_info(third_10_matches, puuid))

        print(wins_list)

        lose_streak = 0
        for win in wins_list:
            if win == 'lose':
                lose_streak += 1
            elif win == False:
                return -1
            else:
                break

        return lose_streak
    return 0

# 매치 정보를 가져오는 함수
def fetch_match_info(matchId, puuid):
    try:
        match_details = get_summoner_matchinfo_nonaysnc(matchId)
    except NotFoundError as e:
        raise NotFoundError

    player_stats = None
    for player in match_details['info']['participants']:
        if puuid == player['puuid']:
            player_stats = {
                'Kills': player['kills'],
                'Deaths': player['deaths'],
                'Assists': player['assists'],
                'Champion': player['championName'],
                'Position': player['individualPosition'],
                'Win': player['win']
            }
    return player_stats

# 매치 ID에 대한 정보를 병렬로 가져오는 함수
def fetch_all_match_info(matches, puuid):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # 각 매치 정보를 가져오는 함수를 병렬로 실행
        try:
            player_stats_list = executor.map(fetch_match_info, matches, [puuid] * len(matches))
        except NotFoundError as e:
            raise NotFoundError
    return list(player_stats_list)

# 확성기 모달 정의 (메세지 입력만)
class 확성기모달(Modal, title="확성기 메세지 작성"):
    def __init__(self, 익명여부: str):
        super().__init__()
        self.익명여부 = 익명여부  # 커맨드에서 받은 익명 여부를 저장
        # 메세지 입력 필드 추가
        self.message_input = TextInput(
            label="메세지",
            placeholder="보낼 메세지를 입력하세요",
            style=TextStyle.long,
            max_length=2000
        )
        self.add_item(self.message_input)

    async def on_submit(self, interaction: discord.Interaction):
        # 전송할 채널 ID
        channel = interaction.client.get_channel(1332330634546253915)
        
        # 예시: DB에서 현재 예측 시즌 및 포인트 정보를 가져오는 코드 (구현은 사용 중인 DB에 맞게 수정)
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
        current_predict_season = cur_predict_seasonref.get()
        ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{interaction.user.name}')
        originr = ref.get()
        point = originr["포인트"]
        bettingPoint = originr["베팅포인트"]
        
        # 익명 여부에 따른 필요 포인트 설정
        if self.익명여부.strip() == '익명':
            need_point = 150
        else:
            need_point = 100
        
        if point - bettingPoint < need_point:
            await interaction.response.send_message(
                f"포인트가 부족합니다! 현재 포인트: {point - bettingPoint} (베팅포인트 {bettingPoint} 제외)",
                ephemeral=True
            )
            return

        # 포인트 차감
        ref.update({"포인트": point - need_point})
        
        # 익명 여부에 따라 임베드 제목 결정
        if self.익명여부.strip() == '익명':
            embed = discord.Embed(title="익명의 메세지", color=discord.Color.light_gray())
        else:
            embed = discord.Embed(title=f"{interaction.user.display_name}의 메세지", color=discord.Color.light_gray())

        embed.add_field(name="", value=self.message_input.value, inline=False)
        
        await channel.send("@everyone\n", embed=embed)
        await interaction.response.send_message(
            f"전송 완료! 남은 포인트: {point - bettingPoint - need_point} (베팅포인트 {bettingPoint} 제외)",
            ephemeral=True
        )

        current_datetime = datetime.now() # 데이터베이스에 남길 현재 시각 기록
        current_date = current_datetime.strftime("%Y-%m-%d")
        current_time = current_datetime.strftime("%H:%M:%S")
        change_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트변동로그/{current_date}/{interaction.user.name}")
        change_ref.push({
            "시간": current_time,
            "포인트": point - need_point,
            "포인트 변동": -need_point,
            "사유": "확성기 사용"
        })

# 커스텀 모달 정의 (제목, 내용, URL 입력)
class 공지모달(Modal, title="공지 작성"):
    제목 = TextInput(
        label="제목", 
        placeholder="공지 제목을 입력하세요", 
        max_length=100,
        style=TextStyle.short  # 짧은 입력 스타일
    )
    메세지 = TextInput(
        label="내용", 
        placeholder="공지 내용을 입력하세요", 
        max_length=2000,
        style=TextStyle.long  # 긴 입력 스타일
    )
    url = TextInput(
        label="URL (선택)", 
        placeholder="옵션: URL을 입력하세요", 
        required=False,
        style=TextStyle.short
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.client.get_channel(1332330634546253915)
        if interaction.user.name == "toe_kyung":
            embed = discord.Embed(
                title=self.제목.value, 
                description=self.메세지.value, 
                color=discord.Color.light_gray()
            )
            if self.url.value:
                embed.url = self.url.value
            await channel.send("@everyone\n", embed=embed)
            await interaction.response.send_message("전송 완료!", ephemeral=True)
        else:
            await interaction.response.send_message("권한이 없습니다", ephemeral=True)

async def place_bet(bot,which,result,bet_amount):
    channel = bot.get_channel(int(CHANNEL_ID))
    userembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
    userembed.add_field(name="",value=f"누군가가 {which}의 {result}에 {bet_amount}포인트를 베팅했습니다!", inline=False)
    await channel.send(f"\n",embed = userembed)

async def mission_notice(bot, name, mission, rarity):
    channel = bot.get_channel(int(CHANNEL_ID))
    
    # 희귀도에 따라 임베드 색상과 제목 설정
    color_map = {
        "일반": discord.Color.light_gray(),
        "희귀": discord.Color.blue(),
        "에픽": discord.Color.purple(),
        "전설": discord.Color.gold(),
        "신화": discord.Color.dark_red(),
        "히든": discord.Color.from_rgb(100,198,209)
    }

    title_map = {
        "일반": "[일반] 미션 달성!",
        "희귀": "[희귀] 미션 달성!",
        "에픽": "[에픽] 미션 달성!",
        "전설": "[전설] 미션 달성!",
        "신화": "[신화] 미션 달성!",
        "히든": "[히든] 미션 달성!"
    }

    color = color_map.get(rarity, discord.Color.light_gray())  # 기본 색상은 light_gray
    title = title_map.get(rarity, "미션 달성!")

    # 임베드 메시지 구성
    userembed = discord.Embed(title=title, color=color)
    userembed.add_field(name="", value=f"{name}님이 [{mission}] 미션을 달성했습니다!", inline=False)
    
    # 메시지 보내기
    await channel.send(f"\n", embed=userembed)

class hello(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(
            name='경고 주기',
            callback=self.warn_user,
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    async def warn_user(self, interaction: discord.Interaction, message: discord.Message) -> None:
        # 경고 처리 로직
        allowed_role_name = "1등 ✨"
        #allowed_role_name = "관리자"
        # 사용자의 역할 확인
        user_roles = [role.name for role in interaction.user.roles]
        if allowed_role_name in user_roles:
            await interaction.response.send_modal(WarnModal(message))
        else:
            await interaction.response.send_message("경고는 1등만 부여할 수 있습니다.")

    @commands.Cog.listener()
    async def on_ready(self):
        load_dotenv()
        global API_KEY
        API_KEY = os.getenv("RIOT_API_KEY")

    @app_commands.command(name="전적분석",description="최근 5개의 경기를 분석합니다")
    @app_commands.describe(닉네임='소환사 닉네임',태그='소환사 태그 ex)KR1',시작전적 = '어느 판부터 분석할 지 숫자로 입력 (가장 최근전적부터 : 0)',리그 = "어떤 랭크를 분석할 지 선택하세요")
    @app_commands.choices(리그=[
    Choice(name='솔랭', value='1'),
    Choice(name='자랭', value='2'),
    Choice(name='격전', value='3')
    ])
    async def 전적분석(self,interaction: discord.Interaction, 닉네임:str, 태그:str, 시작전적:int, 리그: str):
        print(f"{interaction.user}가 요청한 전적분석 요청 수행")
        RNAME = 닉네임
        TLINE = 태그
        FROMNUM = 시작전적
        LEAGUE = 리그
        print(LEAGUE)
        RNAME = RNAME.strip()
        TLINE = TLINE.strip()
        print(f'RNAME : {RNAME}, TLINE : {TLINE}')
        try:
            puuid = await get_summoner_puuid(RNAME, TLINE)
        except NotFoundError as e:
            await interaction.response.send_message("404 에러: 해당 소환사를 찾을 수 없습니다.")
            return

        if LEAGUE == '1':
            # 솔로랭크 5개 매치 가져오기
            league_type = '솔로랭크'
            try:
                matches = await get_recent_solo_ranked_matches(puuid,FROMNUM)
            except NotFoundError as e:
                await interaction.response.send_message("전적을 찾을 수 없습니다")
                return
            except TooManyRequestError as e:
                await interaction.response.send_message("너무 많은 요청. 잠시 후 시도해주세요")
                return
        elif LEAGUE == '2':
            # 자유랭크 5개 매치 가져오기
            league_type = '자유랭크'
            try:
                matches = await get_recent_flex_ranked_matches(puuid,FROMNUM)
            except NotFoundError as e:
                await interaction.response.send_message("전적을 찾을 수 없습니다")
                return
            except TooManyRequestError as e:
                await interaction.response.send_message("너무 많은 요청. 잠시 후 시도해주세요")
                return
        elif LEAGUE == '3':
            league_type = '격전'
            # 격전 5개 매치 가져오기
            try:
                matches = await get_recent_clash_matches(puuid,FROMNUM)
            except NotFoundError as e:
                await interaction.response.send_message("전적을 찾을 수 없습니다")
                return
            except TooManyRequestError as e:
                await interaction.response.send_message("너무 많은 요청. 잠시 후 시도해주세요")
                return

        if not matches:
            await interaction.response.send_message("해당 소환사의 전적을 찾을 수 없습니다.")
            return

        select = discord.ui.Select(placeholder='전적을 선택하세요')

        try:
            player_stats_list = await asyncio.to_thread(fetch_all_match_info, matches, puuid)
        except NotFoundError as e:
            await interaction.response.send_message("404 에러: 전적 세부정보를 찾을 수 없습니다")
            return
        # player_stats_list를 이용해 이후의 로직 수행

        i = 1
        for player_stats in player_stats_list:
            # 플레이어의 K/D/A, 챔피언 이름, 승리 여부 정보를 메시지에 추가
            match_info = ""
            match_info += f"{'승리' if player_stats['Win'] else '패배'}"
            match_info += f" {player_stats['Champion']} "
            match_info += f"{player_stats['Position']}"
            match_kda = f"KDA: {player_stats['Kills']}/{player_stats['Deaths']}/{player_stats['Assists']} "

            select.add_option(label= match_info,value = i,description=match_kda)
            i += 1

        view = discord.ui.View()
        view.add_item(select)
        async def select_type(interaction2: Interaction):
            match_location = select.values[0]
            type_view = discord.ui.View()
            type_select = discord.ui.Select(placeholder='분석할 정보를 선택하세요')
            type_select.add_option(label= "핑 정보",value = 1,description="얼마나 핑을 사용했는 지 분석합니다")
            type_select.add_option(label= "시야 정보",value = 2,description="시야에 관련된 정보를 분석합니다")
            type_select.add_option(label= "정글링 정보",value = 3,description="정글링에 관련된 정보를 분석합니다")
            type_select.add_option(label= "성장 정보",value = 4, description="성장에 관련된 정보를 분석합니다")
            type_view.add_item(type_select)

            async def select_analysis(interaction3: Interaction):
                if int(type_select.values[0]) == 1:
                    match_id = matches[int(match_location)-1]
                    data = await get_summoner_matchinfo(match_id)
                    participant_id = get_participant_id(data,puuid)
                    gameData = data['info']['participants'][participant_id]

                    selected_user_nickname = interaction.user.display_name
                    for player in data['info']['participants']:
                        if puuid == player['puuid']:
                            player_stats = {
                                'Kills': player['kills'],
                                'Deaths': player['deaths'],
                                'Assists': player['assists'],
                                'Champion': player['championName'],
                                'Position': player['individualPosition'],
                                'Win': player['win']
                            }

                    seconds = data['info']['gameDuration']
                    game_duration = seconds_to_minutes_and_seconds(seconds)

                    # Embed 생성
                    basecolor = 0x00ff00 if player_stats['Win'] else 0xff0000
                    embed = discord.Embed(title=f'{selected_user_nickname}이(가) 요청한 {RNAME}의 핑 정보', color = basecolor)
                    embed.add_field(name="승/패", value="승리" if player_stats['Win'] else "패배", inline=True)
                    embed.add_field(name="챔피언", value=player_stats['Champion'], inline=True)
                    embed.add_field(name="KDA", value=f"{player_stats['Kills']}/{player_stats['Deaths']}/{player_stats['Assists']}", inline=True)
                    embed.add_field(name="게임 시간", value=game_duration, inline=True)
                    embed.add_field(name="포지션", value=player_stats['Position'])
                    embed.add_field(name="기본 핑", value=gameData['basicPings'], inline=True)
                    embed.add_field(name="갑니다 핑", value=gameData['onMyWayPings'], inline=True)
                    embed.add_field(name="지원 핑", value=gameData['assistMePings'], inline=True)
                    embed.add_field(name="미아 핑", value=gameData['enemyMissingPings'], inline=True)
                    embed.add_field(name="위험 핑", value=gameData['dangerPings'], inline=True)
                    embed.add_field(name="적 시야 핑", value=gameData['enemyVisionPings'], inline=True)
                    embed.add_field(name="후퇴 핑", value=gameData['getBackPings'], inline=True)
                    embed.add_field(name="홀드 핑", value=gameData['holdPings'], inline=True)
                    embed.add_field(name="시야 필요 핑", value=gameData['needVisionPings'], inline=True)
                    embed.add_field(name="총공격 핑", value=gameData['allInPings'], inline=True)
                    embed.add_field(name="압박 핑", value=gameData['pushPings'], inline=True)


                    #await interaction.response.send_message(f"```\n{match_data}\n```")
                    await interaction3.response.send_message(embed=embed)
                elif int(type_select.values[0]) == 2:
                    match_id = matches[int(match_location)-1]
                    data = await get_summoner_matchinfo(match_id)
                    participant_id = get_participant_id(data,puuid)
                    gameData = data['info']['participants'][participant_id]

                    selected_user_nickname = interaction.user.display_name
                    for player in data['info']['participants']:
                        if puuid == player['puuid']:
                            player_stats = {
                                'Kills': player['kills'],
                                'Deaths': player['deaths'],
                                'Assists': player['assists'],
                                'Champion': player['championName'],
                                'Position': player['individualPosition'],
                                'Win': player['win']
                            }

                    seconds = data['info']['gameDuration']
                    game_duration = seconds_to_minutes_and_seconds(seconds)

                    # Embed 생성
                    basecolor = 0x00ff00 if player_stats['Win'] else 0xff0000
                    embed = discord.Embed(title=f'{selected_user_nickname}이(가) 요청한 {RNAME}의 시야 정보', color = basecolor)
                    embed.add_field(name="승/패", value="승리" if player_stats['Win'] else "패배", inline=True)
                    embed.add_field(name="챔피언", value=player_stats['Champion'], inline=True)
                    embed.add_field(name="KDA", value=f"{player_stats['Kills']}/{player_stats['Deaths']}/{player_stats['Assists']}", inline=True)
                    embed.add_field(name="게임 시간", value=game_duration, inline=True)
                    embed.add_field(name="포지션", value=player_stats['Position'])
                    embed.add_field(name="제어 와드 설치", value=gameData['challenges']['controlWardsPlaced'], inline=True)
                    embed.add_field(name="투명 와드 설치", value=gameData['challenges']['stealthWardsPlaced'], inline=True)
                    embed.add_field(name="제거한 와드", value=gameData['challenges']['wardTakedowns'], inline=False)
                    embed.add_field(name="20분전 제거한 와드", value=gameData['challenges']['wardsGuarded'], inline=False)
                    embed.add_field(name="지킨 와드", value=gameData['challenges']['epicMonsterStolenWithoutSmite'], inline=False)
                    embed.add_field(name="시야 점수", value=gameData['visionScore'], inline=False)
                    embed.add_field(name="분당 시야 점수", value=gameData['challenges']['visionScorePerMinute'], inline=False)
                    embed.add_field(name="맞라이너 대비 시야점수", value=str(round(gameData['challenges']['visionScoreAdvantageLaneOpponent']*100,2)) + "%", inline=False)
                    embed.add_field(name="적 시야 핑", value=gameData['enemyVisionPings'], inline=False)
                    embed.add_field(name="시야 필요 핑", value=gameData['needVisionPings'], inline=False)
                    embed.add_field(name="시야 확보 핑", value=gameData['visionClearedPings'], inline=False)

                    await interaction3.response.send_message(embed=embed)
                elif int(type_select.values[0]) == 3:
                    match_id = matches[int(match_location)-1]
                    data = await get_summoner_matchinfo(match_id)
                    participant_id = get_participant_id(data,puuid)
                    gameData = data['info']['participants'][participant_id]

                    if participant_id >= 5:
                        team_id = 1
                        oppsite_team_id = 0
                    else:
                        team_id = 0
                        oppsite_team_id = 1


                    baronkills = data['info']['teams'][team_id]['objectives']['baron']['kills']
                    baronkilled = data['info']['teams'][oppsite_team_id]['objectives']['baron']['kills']
                    dragonkills = data['info']['teams'][team_id]['objectives']['dragon']['kills']
                    dragonkilled = data['info']['teams'][oppsite_team_id]['objectives']['dragon']['kills']
                    riftHeraldkills = data['info']['teams'][team_id]['objectives']['riftHerald']['kills']
                    riftHeraldkilled = data['info']['teams'][oppsite_team_id]['objectives']['riftHerald']['kills']
                    if 'horde' in data['info']['teams'][team_id]['objectives']:
                        lavakills = data['info']['teams'][team_id]['objectives']['horde']['kills']
                        lavakilled = data['info']['teams'][oppsite_team_id]['objectives']['horde']['kills']
                    else:
                        lavakills = -1
                        lavakilled = -1


                    selected_user_nickname = interaction.user.display_name
                    for player in data['info']['participants']:
                        if puuid == player['puuid']:
                            player_stats = {
                                'Kills': player['kills'],
                                'Deaths': player['deaths'],
                                'Assists': player['assists'],
                                'Champion': player['championName'],
                                'Position': player['individualPosition'],
                                'Win': player['win']
                            }
                        if player['individualPosition'] == gameData['individualPosition'] and puuid != player['puuid']:
                            oppsite_player_stats = {
                                'MoreEnemyJungle' : round(player['challenges']['moreEnemyJungleThanOpponent'],2),
                                'jungleCsBefore10Minutes' : round(player['challenges']['jungleCsBefore10Minutes'],0),
                                'epicMonsterSteals' : player['challenges']['epicMonsterSteals'],
                                'epicMonsterStolenWithoutSmite' : player['challenges']['epicMonsterStolenWithoutSmite']
                            }

                    seconds = data['info']['gameDuration']
                    game_duration = seconds_to_minutes_and_seconds(seconds)


                    # Embed 생성
                    basecolor = 0x00ff00 if player_stats['Win'] else 0xff0000
                    embed = discord.Embed(title=f'{selected_user_nickname}이(가) 요청한 {RNAME}의 정글링 정보', color = basecolor)
                    embed.add_field(name="승/패", value="승리" if player_stats['Win'] else "패배", inline=True)
                    embed.add_field(name="챔피언", value=player_stats['Champion'], inline=True)
                    embed.add_field(name="KDA", value=f"{player_stats['Kills']}/{player_stats['Deaths']}/{player_stats['Assists']}", inline=True)
                    embed.add_field(name="게임 시간", value=game_duration, inline=True)
                    embed.add_field(name="아군 정글 몹 처치", value=gameData['challenges']['alliedJungleMonsterKills'], inline=True)
                    embed.add_field(name="적 정글 몹 처치", value=gameData['challenges']['enemyJungleMonsterKills'], inline=True)
                    embed.add_field(name="바론", value=baronkills, inline=True)
                    embed.add_field(name="드래곤", value=dragonkills, inline=True)
                    embed.add_field(name="전령", value=riftHeraldkills, inline=True)
                    embed.add_field(name="적 바론", value=baronkilled, inline=True)
                    embed.add_field(name="적 드래곤", value=dragonkilled, inline=True)
                    embed.add_field(name="적 전령", value=riftHeraldkilled, inline=True)
                    if lavakills and lavakilled != -1:
                        embed.add_field(name="공허 유충", value=lavakills, inline=True)
                        embed.add_field(name="적 공허 유충", value=lavakilled, inline=True)
                    embed.add_field(name="스틸한 에픽 몬스터", value=gameData['challenges']['epicMonsterSteals'], inline=False)
                    embed.add_field(name="스틸당한 에픽 몬스터", value=oppsite_player_stats['epicMonsterSteals'], inline=False)
                    embed.add_field(name="강타 없이 스틸한 에픽 몬스터", value=gameData['challenges']['epicMonsterStolenWithoutSmite'], inline=False)
                    embed.add_field(name="강타 없이 스틸당한 에픽 몬스터", value=oppsite_player_stats['epicMonsterStolenWithoutSmite'], inline=False)
                    embed.add_field(name="첫 바위게 먹은 개수(최대 2)", value=gameData['challenges']['initialCrabCount'], inline=False)
                    embed.add_field(name="10분 이전 정글 몹으로만 cs", value=round(gameData['challenges']['jungleCsBefore10Minutes'],0), inline=False)
                    embed.add_field(name="적 정글의 10분 이전 정글 몹으로만 cs", value=oppsite_player_stats['jungleCsBefore10Minutes'], inline=False)
                    embed.add_field(name="10분 이전 먹은 라인 cs", value=round(gameData['challenges']['laneMinionsFirst10Minutes'],0), inline=False)
                    embed.add_field(name="적 정글 침범 지수", value=round(gameData['challenges']['moreEnemyJungleThanOpponent'],2), inline=True)
                    embed.add_field(name="아군 정글 침범 지수", value=oppsite_player_stats['MoreEnemyJungle'], inline=True)

                    await interaction3.response.send_message(embed=embed)
                elif int(type_select.values[0]) == 4:
                    match_id = matches[int(match_location)-1]
                    data = await get_summoner_matchinfo(match_id)
                    participant_id = get_participant_id(data,puuid)
                    gameData = data['info']['participants'][participant_id]



                    selected_user_nickname = interaction.user.display_name
                    for player in data['info']['participants']:
                        if puuid == player['puuid']:
                            player_stats = {
                                'Kills': player['kills'],
                                'Deaths': player['deaths'],
                                'Assists': player['assists'],
                                'Champion': player['championName'],
                                'Position': player['individualPosition'],
                                'Win': player['win']
                            }
                        if player['individualPosition'] == gameData['individualPosition'] and puuid != player['puuid']:
                            oppsite_player_stats = {
                                'MaxCsGap' : round(player['challenges']['maxCsAdvantageOnLaneOpponent'],1),
                                'MaxLvGap' : player['challenges']['maxLevelLeadLaneOpponent'],
                                'SoloKill' : player['challenges']['soloKills'],
                                'TurretPlate' : player['challenges']['turretPlatesTaken'],
                                '10minCs' : player['challenges']['laneMinionsFirst10Minutes']
                            }

                    seconds = data['info']['gameDuration']
                    game_duration = seconds_to_minutes_and_seconds(seconds)
                    # Embed 생성
                    basecolor = 0x00ff00 if player_stats['Win'] else 0xff0000
                    embed = discord.Embed(title=f'{selected_user_nickname}이(가) 요청한 {RNAME}의 성장 정보', color = basecolor)
                    embed.add_field(name="승/패", value="승리" if player_stats['Win'] else "패배", inline=True)
                    embed.add_field(name="챔피언", value=player_stats['Champion'], inline=True)
                    embed.add_field(name="KDA", value=f"{player_stats['Kills']}/{player_stats['Deaths']}/{player_stats['Assists']}", inline=True)
                    embed.add_field(name="게임 시간", value=game_duration, inline=True)
                    embed.add_field(name="챔피언 레벨", value=gameData['champLevel'], inline=True)
                    embed.add_field(name="포지션", value=player_stats['Position'])
                    embed.add_field(name="획득 골드", value=gameData['goldEarned'], inline=True)
                    embed.add_field(name="사용 골드", value=gameData['goldSpent'], inline=True)
                    embed.add_field(name="분당 골드", value=round(int(gameData['challenges']['goldPerMinute']),2), inline=True)
                    embed.add_field(name="10분 이전 먹은 라인 cs", value=gameData['challenges']['laneMinionsFirst10Minutes'], inline=False)
                    embed.add_field(name="상대가 10분 이전 먹은 라인 cs", value=oppsite_player_stats['10minCs'], inline=False)
                    embed.add_field(name="미니언 처치 횟수", value=gameData['totalMinionsKilled'], inline=False)
                    embed.add_field(name="최고로 낸 cs차이", value=round(gameData['challenges']['maxCsAdvantageOnLaneOpponent'],1), inline=False)
                    embed.add_field(name="최고로 난 cs차이", value=oppsite_player_stats['MaxCsGap'], inline=False)
                    embed.add_field(name="최고로 낸 레벨차이", value=gameData['challenges']['maxLevelLeadLaneOpponent'], inline=False)
                    embed.add_field(name="최고로 난 레벨차이", value=oppsite_player_stats['MaxLvGap'], inline=False)
                    embed.add_field(name="적 포탑 근처에서 킬", value=gameData['challenges']['killsNearEnemyTurret'], inline=False)
                    embed.add_field(name="아군 포탑 근처에서 킬", value=gameData['challenges']['killsUnderOwnTurret'], inline=False)
                    embed.add_field(name="팀 내 넣은 데미지 비율", value=f"{round(gameData['challenges']['teamDamagePercentage']*100,1)}%", inline=False)
                    embed.add_field(name="팀 내 받은 데미지 비율", value=f"{round(gameData['challenges']['damageTakenOnTeamPercentage']*100,1)}%", inline=False)
                    embed.add_field(name="솔로킬", value=gameData['challenges']['soloKills'], inline=False)
                    embed.add_field(name="상대 솔로킬", value=oppsite_player_stats['SoloKill'], inline=False)
                    embed.add_field(name="획득한 포탑 방패", value=gameData['challenges']['turretPlatesTaken'], inline=False)
                    embed.add_field(name="뺏긴 포탑 방패", value=oppsite_player_stats['TurretPlate'], inline=False)

                    #await interaction.response.send_message(f"```\n{match_data}\n```")
                    await interaction3.response.send_message(embed=embed)
            type_select.callback = select_analysis
            embed = discord.Embed(title=f'{RNAME}#{TLINE}의 {league_type} {int(match_location) + FROMNUM}번째 게임에서 분석할 정보', color = 0x000000)
            await interaction2.response.send_message(view=type_view, embed = embed)


        select.callback = select_type

        embed = discord.Embed(title=f'{RNAME}#{TLINE}의 전적 목록({league_type})', color = 0x000000)
        await interaction.response.send_message(view=view, embed = embed)

    @app_commands.command(name="트름범인",description="누구인가?")
    async def 트름범인(self,interaction: discord.Interaction):
        print(f"{interaction.user}가 요청한 트름범인 요쳥 수행")
        # 필터링할 봇들의 사용자 이름 리스트
        excluded_bots = ['TTS Bot', '술팽봇', '뽀삐']
        if interaction.user.voice is not None:
            voice_channel = interaction.user.voice.channel
            voice_members = voice_channel.members
            eligible_members = [member for member in voice_members if member.name not in excluded_bots]
            if eligible_members:
                chosen_member = random.choice(eligible_members)
                mention_message = f"<@{chosen_member.id}>!, 너가 범인이야!"
                await interaction.response.send_message(mention_message)
        else:
            await interaction.response.send_message("음성 채널에 연결되어 있지 않습니다!")

    @app_commands.command(name="연승",description="소환사의 연승 횟수를 보여줍니다")
    @app_commands.describe(닉네임='소환사 닉네임',태그='소환사 태그 ex)KR1')
    async def 연승(self, interaction: discord.Interaction, 닉네임:str, 태그:str):
        print(f"{interaction.user}가 요청한 연승 요청 수행")
        RNAME = 닉네임
        TLINE = 태그
        RNAME = RNAME.strip()
        TLINE = TLINE.strip()
        print(f'RNAME : {RNAME}, TLINE : {TLINE}')

        try:
            puuid = await get_summoner_puuid(RNAME, TLINE)
        except NotFoundError as e:
            await interaction.response.send_message("해당 소환사를 찾을 수 없습니다.")
            return

        try:
            win_streak = await calculate_consecutive_wins(puuid)
            print(win_streak)
        except NotFoundError as e:
            await interaction.response.send_message(f"전적 정보를 찾을 수 없습니다.")
            return
        except TooManyRequestError as e:
            await interaction.response.send_message(f"너무 많은 요청. 잠시 후 다시 시도해주세요.")
            return

        if win_streak > 0:
            await interaction.response.send_message(f"{RNAME}의 현재 연승 횟수: {win_streak}연승")
        elif win_streak == 0:
            await interaction.response.send_message(f"{RNAME}은(는) 연승 중이 아닙니다.")
        else:
            await interaction.response.send_message('잠시 후에 다시 시도해주세요')

    @app_commands.command(name="연패",description="소환사의 연패 횟수를 보여줍니다")
    @app_commands.describe(닉네임='소환사 닉네임',태그='소환사 태그 ex)KR1')
    async def 연패(self, interaction: discord.Interaction, 닉네임:str, 태그:str):
        print(f"{interaction.user}가 요청한 연패 요청 수행")
        RNAME = 닉네임
        TLINE = 태그
        RNAME = RNAME.strip()
        TLINE = TLINE.strip()
        print(f'RNAME : {RNAME}, TLINE : {TLINE}')
        puuid = await get_summoner_puuid(RNAME, TLINE)

        try:
            puuid = await get_summoner_puuid(RNAME, TLINE)
        except NotFoundError as e:
            await interaction.response.send_message("해당 소환사를 찾을 수 없습니다.")
            return

        try:
            loss_streak = await calculate_consecutive_losses(puuid)
        except NotFoundError as e:
            await interaction.response.send_message(f"404 에러: 전적 데이터를 찾을 수 없습니다.")
            return
        except TooManyRequestError as e:
            await interaction.response.send_message(f'429 에러: 너무 많은 요청. 잠시 후 시도해주세요.')
            return

        if loss_streak > 0:
            await interaction.response.send_message(f"{RNAME}의 현재 연패 횟수: {loss_streak}연패")
        elif loss_streak == 0:
            await interaction.response.send_message(f"{RNAME}은(는) 연패 중이 아닙니다.")
        else:
            await interaction.response.send_message('잠시 후에 다시 시도해주세요')

    @app_commands.command(name="최근전적",description="최근 20경기의 전적을 보여줍니다")
    @app_commands.describe(닉네임='소환사 닉네임',태그='소환사 태그 ex)KR1')
    async def 최근전적(self, interaction: discord.Interaction, 닉네임:str, 태그:str):
        print(f"{interaction.user}가 요청한 최근전적 요청 수행")
        RNAME = 닉네임
        TLINE = 태그
        RNAME = RNAME.strip()
        TLINE = TLINE.strip()
        print(f'RNAME : {RNAME}, TLINE : {TLINE}')
        try:
            puuid = await get_summoner_puuid(RNAME, TLINE)
        except NotFoundError as e:
            await interaction.response.send_message("404 에러: 해당 소환사를 찾을 수 없습니다.")
            return

        try:
            wins, draw, losses = await calculate_consecutive_matches(puuid)
        except NotFoundError as e:
            await interaction.response.send_message(f'404 에러: 전적을 찾을 수 없습니다')
            return
        except TooManyRequestError as e:
            await interaction.response.send_message(f'429 에러: 요청이 너무 많음. 잠시 후 시도해주세요')
        winrate = round((wins/(wins+losses))*100,2)


        if draw != 0:
            await interaction.response.send_message(f'{RNAME}의 최근 20경기\n'
                        f'승: {wins}, 패: {losses}, 다시하기: {draw}, 승률: {winrate}%')

        else:
            await interaction.response.send_message(f'{RNAME}의 최근 20경기\n'
                        f'승: {wins}, 패: {losses}, 승률: {winrate}%')

    @app_commands.command(name="그래프",description="이번시즌 점수 변동 그래프를 보여줍니다")
    @app_commands.describe(이름="누구의 그래프를 볼지 선택하세요", 랭크="랭크 유형을 선택하세요 (기본값: 솔로랭크)")
    @app_commands.choices(이름=[
    Choice(name='강지모', value='지모'),
    Choice(name='Melon', value='Melon')
    ])
    @app_commands.choices(랭크=[
    Choice(name='솔랭', value='솔로랭크'),
    Choice(name='자랭', value='자유랭크'),
    ])
    async def 그래프(self, interaction: discord.Interaction, 이름:str, 랭크:str = "솔로랭크"):
        print(f"{interaction.user}가 요청한 그래프 요청 수행 ({이름}, {랭크})")
        # LP 변동량 그래프 그리기
        await interaction.response.defer()  # Interaction을 유지
        returnVal = plot_lp_difference_firebase(name = 이름, rank = 랭크)
        
        if returnVal == -1:
            await interaction.response.send_message("해당 시즌 데이터가 존재하지 않습니다.")
            return
        # 그래프 이미지 파일을 Discord 메시지로 전송
        await interaction.followup.send(file=discord.File('lp_graph.png'))

    @app_commands.command(name="시즌그래프",description="시즌 점수 변동 그래프를 보여줍니다")
    @app_commands.describe(시즌 = "시즌을 선택하세요")
    @app_commands.choices(시즌=[
    Choice(name='시즌14-1', value='시즌14-1'),
    Choice(name='시즌14-2', value='시즌14-2'),
    Choice(name='시즌14-3', value='시즌14-3'),
    Choice(name='시즌15', value='시즌15')
    ])
    @app_commands.describe(이름='누구의 그래프를 볼지 선택하세요')
    @app_commands.choices(이름=[
    Choice(name='강지모', value='지모'),
    Choice(name='Melon', value='Melon'),
    Choice(name='고양이', value='고양이')
    ])
    @app_commands.choices(랭크=[
    Choice(name='솔랭', value='솔로랭크'),
    Choice(name='자랭', value='자유랭크'),
    ])
    async def 시즌그래프(self, interaction: discord.Interaction, 이름:str, 시즌:str, 랭크:str = "솔로랭크"):
        print(f"{interaction.user}가 요청한 시즌그래프 요청 수행")
        # LP 변동량 그래프 그리기
        if 이름 == "고양이":
            # ====================  [미션]  ====================
            # 시즌미션 : 이 모양은 고양이?!
            cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
            current_predict_season = cur_predict_seasonref.get()
            ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{interaction.user.name}/미션/시즌미션/이 모양은 고양이%3F%21")

            mission_data = ref.get()
            if mission_data is None:
                ref.set({
                    "보상수령": False,
                    "완료": False,
                    "희귀도": "히든",
                    "포인트": 1000  # 기본 포인트 값 설정
                })
                mission_data = ref.get()
            mission_bool = mission_data.get('완료',False)
            if not mission_bool:
                ref.update({"보상수령": False,
                            "완료": True,
                            "희귀도": "히든",
                            "포인트": 1000})
                
                print(f"{interaction.user.name}의 [이 모양은 고양이?!] 미션 완료")
                await mission_notice(interaction.client,interaction.user.name,"이 모양은 고양이?!","히든")
            
            # ====================  [미션]  ====================
            await interaction.response.send_message("야옹", file=discord.File("cat.jpg"), ephemeral=True)
            return
        await interaction.response.defer()  # Interaction을 유지
        returnVal = plot_lp_difference_firebase(season = 시즌, name = 이름, rank = 랭크)

        if returnVal == -1:
            await interaction.response.send_message("해당 시즌 데이터가 존재하지 않습니다.")
            return
        else:
            # 그래프 이미지 파일을 Discord 메시지로 전송
            await interaction.followup.send(file=discord.File('lp_graph.png'))

    @app_commands.command(name="시즌종료",description="시즌 종료까지 남은 날짜를 보여줍니다.")
    async def 시즌종료(self, interaction: discord.Interaction):
        print(f"{interaction.user}가 요청한 시즌종료 요청 수행")
        # 현재 날짜 및 시간 가져오기
        current_datetime = datetime.now()

        # 시간 차이 계산
        time_difference = SEASON_CHANGE_DATE15 - current_datetime

        # 시간 차이를 한글로 변환하여 출력
        days = time_difference.days
        hours, remainder = divmod(time_difference.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        
        output = ""
        if days:
            output += f"{days}일 "
        if hours:
            output += f"{hours}시간 "
        if minutes:
            output += f"{minutes}분 "
        if seconds:
            output += f"{seconds}초"

        if time_difference.total_seconds() < 0:
            await interaction.response.send_message("시즌 15가 종료되었습니다.")
        else:
            # 시간 차이 출력 (일, 시간, 분, 초)
            await interaction.response.send_message(f"시즌종료까지 남은 시간: {output}")

    @app_commands.command(name="점수",description="현재 소환사의 점수를 보여줍니다")
    @app_commands.describe(닉네임='소환사 닉네임',태그='소환사 태그 ex)KR1',리그='리그를 선택하세요')
    @app_commands.choices(리그=[
    Choice(name='솔랭', value='솔랭'),
    Choice(name='자랭', value='자랭'),
    ])
    async def 점수(self,interaction: discord.Interaction, 닉네임:str, 태그:str, 리그:str):
        print(f"{interaction.user}가 요청한 점수 요청 수행")
        RNAME = 닉네임
        TLINE = 태그
        RNAME = RNAME.strip()
        TLINE = TLINE.strip()
        puuid = await get_summoner_puuid(RNAME, TLINE)
        id = await get_summoner_id(puuid)
        rank = await get_summoner_ranks(id,리그)
        if rank == []:
            await interaction.response.send_message("해당 리그의 전적을 찾을 수 없습니다.")
            return
        else:
            wins = rank["wins"]
            losses = rank["losses"]
            winrate = round((wins / (wins + losses))* 100,2)
            await interaction.response.send_message(f'{RNAME}의 {리그}전적\n'
                            f'{rank["tier"]} {rank["rank"]} {rank["leaguePoints"]}LP\n'
                           f'{wins}승 {losses}패 승률 {winrate}%')

    @app_commands.command(name="캔들그래프",description="이번시즌 점수를 캔들그래프로 보여줍니다")
    @app_commands.describe(이름='누구의 그래프를 볼지 선택하세요')
    @app_commands.choices(이름=[
    Choice(name='강지모', value='지모'),
    Choice(name='Melon', value='Melon'),
    ])
    @app_commands.choices(랭크=[
    Choice(name='솔랭', value='솔로랭크'),
    Choice(name='자랭', value='자유랭크'),
    ])
    async def 캔들그래프(self, interaction: discord.Interaction,이름:str, 랭크:str = "솔로랭크"):
        # 현재 시즌 정보 가져오기
        curseasonref = db.reference("전적분석/현재시즌")
        current_season = curseasonref.get()
        season = current_season
        await interaction.response.defer()  # Interaction을 유지
        result = await plot_candle_graph(season,이름,랭크)
        if result == None:
            await interaction.response.send_message("해당 시즌 데이터가 존재하지 않습니다.")
            return
        
        # 그래프 이미지 파일을 Discord 메시지로 전송
        await interaction.followup.send(file=discord.File('candle_graph.png'),embed = result)

    @app_commands.command(name="시즌캔들그래프",description="시즌 점수를 캔들그래프로 보여줍니다")
    @app_commands.describe(시즌 = "시즌을 선택하세요",이름='누구의 그래프를 볼지 선택하세요')
    @app_commands.choices(시즌=[
    Choice(name='시즌14-1', value='시즌14-1'),
    Choice(name='시즌14-2', value='시즌14-2'),
    Choice(name='시즌14-3', value='시즌14-3'),
    Choice(name='시즌15', value='시즌15')
    ])
    @app_commands.choices(이름=[
    Choice(name='강지모', value='지모'),
    Choice(name='Melon', value='Melon'),
    ])
    async def 시즌캔들그래프(self, interaction: discord.Interaction, 이름:str,시즌:str, 랭크:str = "솔로랭크"):
        
        await interaction.response.defer()  # Interaction을 유지
        result = await plot_candle_graph(시즌,이름,랭크)
        if result == None:
            await interaction.response.send_message("해당 시즌 데이터가 존재하지 않습니다.")
            return
        
        # 그래프 이미지 파일을 Discord 메시지로 전송
        await interaction.followup.send(file=discord.File('candle_graph.png'),embed = result)

    
    @app_commands.command(name="예측시즌그래프",description="예측시즌 점수를 캔들그래프로 보여줍니다")
    @app_commands.describe(시즌 = "시즌을 선택하세요")
    @app_commands.choices(시즌=[
    Choice(name='정규시즌2', value='정규시즌2')
    ])
    async def 예측시즌그래프(self, interaction: discord.Interaction, 시즌:str):
        
        await interaction.response.defer()  # Interaction을 유지
        name = interaction.user.name
        result = await plot_prediction_graph(시즌,name)
        if result == None:
            await interaction.followup.send("해당 시즌 데이터가 존재하지 않습니다.",ephemeral=True)
            return
        
        # 그래프 이미지 파일을 Discord 메시지로 전송
        await interaction.followup.send(file=discord.File('prediction_graph.png'))
    

    @app_commands.command(name="예측순위",description="승부예측 포인트 순위를 보여줍니다. 현재 진행 중인 시즌은 포인트를 사용하여 순위를 확인할 수 있습니다.")
    @app_commands.describe(시즌 = "시즌을 선택하세요")
    @app_commands.choices(시즌=[
    Choice(name='예측시즌 1', value='예측시즌1'),
    Choice(name='예측시즌 2', value='예측시즌2'),
    Choice(name='예측시즌 3', value='예측시즌3'),
    Choice(name='정규시즌 1', value='정규시즌1'),
    Choice(name='정규시즌 2', value='정규시즌2'),
    Choice(name='정규시즌 3', value='정규시즌3'),
    Choice(name='정규시즌 4', value='정규시즌4'),
    ])
    async def 예측순위(self, interaction: discord.Interaction, 시즌:str):
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
        current_predict_season = cur_predict_seasonref.get()
        if 시즌 == current_predict_season:
            today = datetime.today()
            '''
            if today.weekday() != 6:
                embed = discord.Embed(title=f'비공개', color = discord.Color.blue())
                embed.add_field(name=f"", value=f"최신 시즌 순위표는 비공개입니다!", inline=False)
                await interaction.response.send_message(embed=embed,ephemeral=True)
            '''
            embed = discord.Embed(title=f'비공개', color = discord.Color.blue())
            embed.add_field(name=f"", value=f"최신 시즌 순위표는 비공개입니다!", inline=False)
            pointref = db.reference("승부예측/혼자보기포인트")
            need_point = pointref.get()
            see1button = discord.ui.Button(style=discord.ButtonStyle.success,label=f"순위표 혼자보기({need_point} 포인트)")
            see2button = discord.ui.Button(style=discord.ButtonStyle.primary,label="순위표 같이보기(500 포인트)")
            view = discord.ui.View()
            view.add_item(see1button)
            view.add_item(see2button)
            
            async def see1button_callback(interaction:discord.Interaction): # 순위표 버튼을 눌렀을 때의 반응!
                cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                current_predict_season = cur_predict_seasonref.get()
                refp = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{interaction.user.name}')
                originr = refp.get()
                pointref = db.reference("승부예측/혼자보기포인트")
                need_point = pointref.get()
                point = originr["포인트"]
                bettingPoint = originr["베팅포인트"]
                if point - bettingPoint < need_point:
                    await interaction.response.send_message(f"포인트가 부족합니다! 현재 포인트: {point - bettingPoint} (베팅포인트 {bettingPoint} 제외)",ephemeral=True)
                else:
                    refp.update({"포인트" : point - need_point})
                    refhon = db.reference('승부예측')
                    refhon.update({"혼자보기포인트" : need_point + 50})
                    ref = db.reference(f'승부예측/예측시즌/{시즌}/예측포인트')
                    points = ref.get()

                    current_datetime = datetime.now() # 데이터베이스에 남길 현재 시각 기록
                    current_date = current_datetime.strftime("%Y-%m-%d")
                    current_time = current_datetime.strftime("%H:%M:%S")
                    change_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트변동로그/{current_date}/{interaction.user.name}")
                    change_ref.push({
                        "시간": current_time,
                        "포인트": point - need_point,
                        "포인트 변동": -need_point,
                        "사유": "순위표 혼자보기 구매",
                    })

                    # 점수를 기준으로 내림차순으로 정렬
                    sorted_data = sorted(points.items(), key=lambda x: x[1]['포인트'], reverse=True)

                    # 상위 명을 추출하여 출력
                    top = sorted_data[:]

                    embed = discord.Embed(title=f'승부예측 순위', color = discord.Color.blue())

                    rank = 1

                    for username, info in top:
                        if info['총 예측 횟수'] > 0:
                            if info['연승'] > 0:
                                embed.add_field(name=f"{rank}. {username}", value=f"연속적중 {info['연승']}, 포인트 {info['포인트']}, 적중률 {info['적중률']}({info['적중 횟수']}/{info['총 예측 횟수']}), ", inline=False)
                            elif info['연패'] > 0:
                                embed.add_field(name=f"{rank}. {username}", value=f"연속비적중 {info['연패']}, 포인트 {info['포인트']}, 적중률 {info['적중률']}({info['적중 횟수']}/{info['총 예측 횟수']}), ", inline=False)
                            else:
                                embed.add_field(name=f"{rank}. {username}", value=f"포인트 {info['포인트']}, 적중률 {info['적중률']}({info['적중 횟수']}/{info['총 예측 횟수']}), ", inline=False)
                            rank += 1
                    
                    userembed = discord.Embed(title=f"알림", color=discord.Color.light_gray())
                    userembed.add_field(name="",value=f"{interaction.user.display_name}님이 {need_point}포인트를 소모하여 순위표를 열람했습니다! (현재 열람 포인트 : {need_point + 50}(+ 50))", inline=False)
                    channel = interaction.client.get_channel(int(CHANNEL_ID))
                    await channel.send(embed=userembed)
                    await interaction.response.send_message(embed=embed,ephemeral=True)

            async def see2button_callback(interaction:discord.Interaction): # 순위표 버튼을 눌렀을 때의 반응!
                cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                current_predict_season = cur_predict_seasonref.get()
                refp = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{interaction.user.name}')
                originr = refp.get()
                point = originr["포인트"]
                bettingPoint = originr["베팅포인트"]
                need_point = 500
                if point - bettingPoint < need_point:
                    await interaction.response.send_message(f"포인트가 부족합니다! 현재 포인트: {point - bettingPoint} (베팅포인트 {bettingPoint} 제외)",ephemeral=True)
                else:
                    await interaction.response.defer()  # 응답 지연 처리
                    refp.update({"포인트" : point - need_point})
                    ref = db.reference(f'승부예측/예측시즌/{시즌}/예측포인트')
                    points = ref.get()

                    current_datetime = datetime.now() # 데이터베이스에 남길 현재 시각 기록
                    current_date = current_datetime.strftime("%Y-%m-%d")
                    current_time = current_datetime.strftime("%H:%M:%S")
                    change_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트변동로그/{current_date}/{interaction.user.name}")
                    change_ref.push({
                        "시간": current_time,
                        "포인트": point - need_point,
                        "포인트 변동": -need_point,
                        "사유": "순위표 같이보기 구매"
                    })

                    # 점수를 기준으로 내림차순으로 정렬
                    sorted_data = sorted(points.items(), key=lambda x: x[1]['포인트'], reverse=True)

                    # 상위 명을 추출하여 출력
                    top = sorted_data[:]

                    embed = discord.Embed(title=f'승부예측 순위', color = discord.Color.blue())

                    rank = 1

                    for username, info in top:
                        if info['총 예측 횟수'] > 0:
                            if info['연승'] > 0:
                                embed.add_field(name=f"{rank}. {username}", value=f"연속적중 {info['연승']}, 포인트 {info['포인트']}, 적중률 {info['적중률']}({info['적중 횟수']}/{info['총 예측 횟수']}), ", inline=False)
                            elif info['연패'] > 0:
                                embed.add_field(name=f"{rank}. {username}", value=f"연속비적중 {info['연패']}, 포인트 {info['포인트']}, 적중률 {info['적중률']}({info['적중 횟수']}/{info['총 예측 횟수']}), ", inline=False)
                            else:
                                embed.add_field(name=f"{rank}. {username}", value=f"포인트 {info['포인트']}, 적중률 {info['적중률']}({info['적중 횟수']}/{info['총 예측 횟수']}), ", inline=False)
                            rank += 1  
                    
                    
                    notice_channel = interaction.client.get_channel(1332330634546253915)
                    channel = interaction.client.get_channel(int(CHANNEL_ID))
                    userembed = discord.Embed(title=f"알림", color=discord.Color.light_gray())
                    userembed.add_field(name="",value=f"{interaction.user.display_name}님이 {need_point}포인트를 소모하여 순위표를 전체 열람했습니다!", inline=False)
                    await notice_channel.send("@everyone\n", embed=embed)

                    await interaction.followup.send(embed = userembed)

            see1button.callback = see1button_callback
            see2button.callback = see2button_callback

            await interaction.response.send_message(view = view,embed=embed,ephemeral=True)
        else:
            ref = db.reference(f'승부예측/예측시즌/{시즌}/예측포인트')
            points = ref.get()

            # 점수를 기준으로 내림차순으로 정렬
            sorted_data = sorted(points.items(), key=lambda x: x[1]['포인트'], reverse=True)

            # 상위 명을 추출하여 출력
            top = sorted_data[:]

            embed = discord.Embed(title=f'승부예측 순위', color = discord.Color.blue())

            rank = 1

            for username, info in top:
                if info['총 예측 횟수'] > 0:
                    if info['연승'] > 0:
                        embed.add_field(name=f"{rank}. {username}", value=f"연속적중 {info['연승']}, 포인트 {info['포인트']}, 적중률 {info['적중률']}({info['적중 횟수']}/{info['총 예측 횟수']}), ", inline=False)
                    elif info['연패'] > 0:
                        embed.add_field(name=f"{rank}. {username}", value=f"연속비적중 {info['연패']}, 포인트 {info['포인트']}, 적중률 {info['적중률']}({info['적중 횟수']}/{info['총 예측 횟수']}), ", inline=False)
                    else:
                        embed.add_field(name=f"{rank}. {username}", value=f"포인트 {info['포인트']}, 적중률 {info['적중률']}({info['적중 횟수']}/{info['총 예측 횟수']}), ", inline=False)
                    rank += 1

            await interaction.response.send_message(embed=embed)

    @app_commands.command(name='포인트',description="자신의 승부예측 포인트와 적중률을 알려줍니다")
    async def 포인트(self, interaction: discord.Interaction):
        username = interaction.user.name
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
        current_predict_season = cur_predict_seasonref.get()
        ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{username}')
        point_data = ref.get()

        ref_tc = db.reference(f'무기/아이템/{username}')
        tc_data = ref_tc.get()
        TC = tc_data.get('탑코인', 0)

        embed = discord.Embed(title=f'{username}의 포인트', color = discord.Color.blue())

        if (point_data['지모승리예측'] + point_data['지모패배예측']) != 0:
            jimo_prediction_rate = round((point_data['지모적중'] / (point_data['지모승리예측'] + point_data['지모패배예측'])) * 100, 2)
        else:
            jimo_prediction_rate = 0
        if (point_data['Melon승리예측'] + point_data['Melon패배예측']) != 0:
            Melon_prediction_rate = round((point_data['Melon적중'] / (point_data['Melon승리예측'] + point_data['Melon패배예측'])) * 100, 2)
        else:
            Melon_prediction_rate = 0
        if (point_data['총 예측 횟수'] - (point_data['지모승리예측'] + point_data['지모패배예측']) - (point_data['Melon승리예측'] + point_data['Melon패배예측'])) != 0:
            battle_prediction_rate = round(((point_data['적중 횟수'] - point_data['지모적중'] - point_data['Melon적중']) / (point_data['총 예측 횟수'] - (point_data['지모승리예측'] + point_data['지모패배예측']) - (point_data['Melon승리예측'] + point_data['Melon패배예측']))) * 100, 2)
        else:
            battle_prediction_rate = 0

        embed.add_field(name='',value=f"**{point_data['포인트']}**포인트(베팅 포인트:**{point_data['베팅포인트']}**)", inline=False)
        embed.add_field(name='',value=f"**{TC}**탑코인", inline=False)
        embed.add_field(name=f"승부예측 데이터", value=f"연속적중 **{point_data['연승']}**, 포인트 **{point_data['포인트']}**, 적중률 **{point_data['적중률']}**({point_data['적중 횟수']}/{point_data['총 예측 횟수']}), ", inline=False)
        embed.add_field(name=f"", value=f"연속승리예측 **{point_data['승리예측연속']}**, 연속패배예측 **{point_data['패배예측연속']}**, 적중률(대결) **{battle_prediction_rate}%**({(point_data['적중 횟수'] - point_data['지모적중'] - point_data['Melon적중'])} / {(point_data['총 예측 횟수'] - (point_data['지모승리예측'] + point_data['지모패배예측']) - (point_data['Melon승리예측'] + point_data['Melon패배예측']))})", inline=False)
        embed.add_field(name=f"", value=f"지모승리예측 **{point_data['지모승리예측']}**, 지모패배예측 **{point_data['지모패배예측']}**, 적중률(지모) **{jimo_prediction_rate}%**({point_data['지모적중']} / {point_data['지모승리예측'] + point_data['지모패배예측']})", inline=False)
        embed.add_field(name=f"", value=f"Melon승리예측 **{point_data['Melon승리예측']}**, Melon패배예측 **{point_data['Melon패배예측']}**, 적중률(Melon) **{Melon_prediction_rate}%**({point_data['Melon적중']} / {point_data['Melon승리예측'] + point_data['Melon패배예측']})", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="온오프",description="투표기능 온오프(개발자 전용)")
    @app_commands.describe(값 = "값을 선택하세요")
    @app_commands.choices(값=[
    Choice(name='On', value="False"),
    Choice(name='Off', value="True"),
    ])
    async def 온오프(self, interaction: discord.Interaction, 값:str):
        if interaction.user.name == "toe_kyung":
            onoffref = db.reference("승부예측")
            if 값 == "True":
                onoffbool = True
            else:
                onoffbool = False
            onoffref.update({"투표온오프" : onoffbool})

            embed = discord.Embed(title=f'변경 완료', color = discord.Color.blue())
            embed.add_field(name=f"변경", value=f"투표 기능이 Off 되었습니다." if onoffbool else "투표 기능이 On 되었습니다.", inline=False)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("권한이 없습니다", ephemeral=True)

    @app_commands.command(name="이벤트온오프",description="승부예측 이벤트 온오프(개발자 전용)")
    @app_commands.choices(값=[
    Choice(name='On', value="True"),
    Choice(name='Off', value="False"),
    ])
    async def 이벤트온오프(self, interaction: discord.Interaction, 값:str):
        if interaction.user.name == "toe_kyung":
            onoffref = db.reference("승부예측")
            if 값 == "True":
                onoffbool = True
            else:
                onoffbool = False
            onoffref.update({"이벤트온오프" : onoffbool})

            embed = discord.Embed(title=f'변경 완료', color = discord.Color.blue())
            embed.add_field(name=f"변경", value=f"승부예측 이벤트가 시작되었습니다." if onoffbool else "승부예측 이벤트가 종료되었습니다.", inline=False)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("권한이 없습니다", ephemeral=True)

    @app_commands.command(name="대결진행여부초기화",description="대결진행여부를 초기화합니다")
    async def 대결진행여부초기화(self, interaction: discord.Interaction):
        onoffref = db.reference("승부예측")
        onoffref.update({"대결진행여부" : False})

        embed = discord.Embed(title=f'변경 완료', color = discord.Color.blue())
        embed.add_field(name=f"변경", value=f"대결 진행상태가 초기화되었습니다", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="익명온오프",description="익명투표기능 온오프(개발자 전용)")
    @app_commands.describe(값 = "값을 선택하세요")
    @app_commands.choices(값=[
    Choice(name='On', value="True"),
    Choice(name='Off', value="False"),
    ])
    async def 익명온오프(self, interaction: discord.Interaction, 값:str):
        if interaction.user.name == "toe_kyung":
            onoffref = db.reference("승부예측")
            if 값 == "True":
                onoffbool = True
            else:
                onoffbool = False
            onoffref.update({"익명온오프" : onoffbool})

            embed = discord.Embed(title=f'변경 완료', color = discord.Color.blue())
            embed.add_field(name=f"변경", value=f"익명투표 기능이 On 되었습니다." if onoffbool else "익명투표 기능이 Off 되었습니다.", inline=False)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("권한이 없습니다", ephemeral=True)

    @app_commands.command(name="정상화",description="점수 정상화(개발자 전용)")
    async def 정상화(self, interaction: discord.Interaction):
        if interaction.user.name == "toe_kyung":
            cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
            current_predict_season = cur_predict_seasonref.get()
            ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트변동로그')

            # timestamp 기준으로 정렬하고 마지막 데이터 하나만 가져오기
            snapshot = ref.order_by_key().get()

            latest_timestamp = None
            latest_log_data = None
            embed = discord.Embed(title=f'정상화 성공', color = discord.Color.blue())


            # 데이터가 존재하는지 확인
            if snapshot:
                for date, times in snapshot.items():
                    for time, log in times.items():
                        # 날짜와 시간을 결합하여 datetime 객체 생성
                        timestamp = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M:%S")

                        # 최신 타임스탬프 업데이트
                        if latest_timestamp is None or timestamp > latest_timestamp:
                            latest_timestamp = timestamp
                            latest_log_data = log

                if latest_log_data:
                    for name, log in latest_log_data.items():
                        ref2 = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{name}')
                        ref2.update({'포인트' : log['포인트']})
                        ref2.update({"총 예측 횟수": log["총 예측 횟수"]})
                        ref2.update({"적중 횟수" : log["적중 횟수"]})
                        ref2.update({"적중률": log["적중률"]})
                        ref2.update({"연승": log["연승"]})
                        ref2.update({"연패": log["연패"]})
                        embed.add_field(name=f"{name}", value= f"{name}의 점수 정상화", inline=False)

            else:
                print('로그 데이터가 없습니다.')

            ref3 = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트변동로그/{date}/{time}')
            ref3.delete()

            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("권한이 없습니다", ephemeral=True)

    @app_commands.command(name="군대",description="전역까지 남은 날짜를 알려줍니다")
    @app_commands.describe(이름 = "이름을 입력하세요")
    @app_commands.choices(이름=[
    Choice(name='강동윤', value='강동윤'),
    Choice(name='김동현', value='김동현'),
    ])
    async def 군대(self, interaction: discord.Interaction, 이름:str):
        outdate_DY = datetime(2026, 1, 28, 7, 0, 0)
        indate_DH = datetime(2024, 11, 4, 14, 0, 0)
        outdate_DH = datetime(2026, 5, 3, 7, 0, 0)

        current_datetime = datetime.now()

        if 이름 == '강동윤':
            # 시간 차이 계산
            time_difference = outdate_DY - current_datetime

            # 시간 차이를 한글로 변환하여 출력
            days = time_difference.days
            hours, remainder = divmod(time_difference.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            hours += days*24

            output = ""
            if hours:
                output += f"{hours}시간 "
            if minutes:
                output += f"{minutes}분 "
            if seconds:
                output += f"{seconds}초"

            await interaction.response.send_message(f"{이름} 전역까지 남은 시간: {output}")
        elif 이름 == '김동현':
            if current_datetime < indate_DH: # 입대하기 전
                # 시간 차이 계산
                time_difference = indate_DH - current_datetime
                목표 = '입대'
            else:
                # 시간 차이 계산
                time_difference = outdate_DH - current_datetime
                목표 = '전역'

            # 시간 차이를 한글로 변환하여 출력
            days = time_difference.days
            hours, remainder = divmod(time_difference.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            hours += days*24

            output = ""
            if hours:
                output += f"{hours}시간 "
            if minutes:
                output += f"{minutes}분 "
            if seconds:
                output += f"{seconds}초"

            await interaction.response.send_message(f"{이름} {목표}까지 남은 시간: {output}")

    @app_commands.command(name="베팅",description="승부예측에 걸 포인트를 설정합니다.")
    @app_commands.describe(이름 = "예측한 사람의 이름을 입력하세요", 포인트 = "베팅할 포인트를 선택하세요 (자연수만)")
    @app_commands.choices(이름=[
    Choice(name='지모', value='지모'),
    Choice(name='Melon', value='Melon'),
    ])
    async def 베팅(self, interaction: discord.Interaction, 이름:str, 포인트:int):    
        async def handle_bet(winbutton):
            cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
            current_predict_season = cur_predict_seasonref.get()

            anonymref = db.reference("승부예측/익명온오프")
            anonymbool = anonymref.get()

            complete_anonymref = db.reference(f"승부예측/완전익명{이름}온오프")
            complete_anonymbool = complete_anonymref.get()

            if 포인트 < 0:
                await interaction.response.send_message("포인트는 0보다 큰 숫자로 입력해주세요",ephemeral=True)
                return
            if winbutton.disabled == True:
                await interaction.response.send_message(f"지금은 {이름}에게 베팅할 수 없습니다!",ephemeral=True)
                return
            if 포인트 == 0:
                await interaction.response.send_message("포인트는 0보다 큰 숫자로 입력해주세요",ephemeral=True)
                return
            

            nickname = interaction.user.name
            if (nickname not in [winner['name'].name for winner in p.votes[이름]['prediction']['win']] and
            nickname not in [loser['name'].name for loser in p.votes[이름]['prediction']['lose']]):
                await interaction.response.send_message(f"승부예측 후 이용해주세요",ephemeral=True)
            else:
                for winner in p.votes[이름]['prediction']['win']:
                    if winner['name'].name == nickname:
                        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                        current_predict_season = cur_predict_seasonref.get()
                        ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner['name'].name}")
                        ref2 = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner['name'].name}/베팅포인트")
                        bettingPoint = ref2.get()
                        info = ref.get()

                        if info.get('포인트',0) - bettingPoint < 포인트:
                            await interaction.response.send_message(f"포인트가 부족합니다!\n현재 포인트: {info['포인트'] - bettingPoint}(베팅 금액 {bettingPoint}P) 제외",ephemeral=True)
                        else:
                            winner['points'] += 포인트  # 포인트 수정
                            ref.update({"베팅포인트" : bettingPoint + 포인트}) # 파이어베이스에 베팅포인트 추가
                            userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                            if complete_anonymbool:
                                await interaction.response.send_message(f"{이름}의 승리에 {포인트}포인트 베팅 완료!",ephemeral=True)
                            elif anonymbool:
                                await place_bet(self.bot,이름,"승리",포인트)
                                await interaction.response.send_message(f"{이름}의 승리에 {포인트}포인트 베팅 완료!",ephemeral=True)
                            else:
                                if winner['points'] != 포인트:
                                    userembed.add_field(name="",value=f"{interaction.user.display_name}님이 {이름}의 승리에 {포인트}포인트만큼 추가 베팅하셨습니다!", inline=True)
                                    await interaction.response.send_message(embed=userembed)
                                else:
                                    userembed.add_field(name="",value=f"{interaction.user.display_name}님이 {이름}의 승리에 {포인트}포인트만큼 베팅하셨습니다!", inline=True)
                                    await interaction.response.send_message(embed=userembed)


                            await refresh_prediction(이름,anonymbool,complete_anonymbool, p.votes[이름]['prediction'])
                            
                            return

                # 패배 예측에서 닉네임 찾기
                for loser in p.votes[이름]['prediction']['lose']:
                    if loser['name'].name == nickname:
                        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                        current_predict_season = cur_predict_seasonref.get()
                        ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{loser['name'].name}")
                        ref2 = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{loser['name'].name}/베팅포인트")
                        bettingPoint = ref2.get()
                        info = ref.get()
    
                        if info['포인트'] - bettingPoint < 포인트:
                            await interaction.response.send_message(f"포인트가 부족합니다!\n현재 포인트: {info['포인트'] - bettingPoint}(베팅 금액 {bettingPoint}P) 제외",ephemeral=True)
                        else:  
                            loser['points'] += 포인트  # 포인트 수정
                            ref.update({"베팅포인트" : bettingPoint + 포인트}) # 파이어베이스에 베팅포인트 추가
                            userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                            if complete_anonymbool:
                                await interaction.response.send_message(f"{이름}의 패배에 {포인트}포인트 베팅 완료!",ephemeral=True)
                            elif anonymbool:
                                await place_bet(self.bot,이름,"패배",포인트)
                                await interaction.response.send_message(f"{이름}의 패배에 {포인트}포인트 베팅 완료!",ephemeral=True)
                            else:
                                if loser['points'] != 포인트:
                                    userembed.add_field(name="",value=f"{interaction.user.display_name}님이 {이름}의 패배에 {포인트}포인트만큼 추가 베팅하셨습니다!", inline=True)
                                    await interaction.response.send_message(embed=userembed)
                                else:
                                    userembed.add_field(name="",value=f"{interaction.user.display_name}님이 {이름}의 패배에 {포인트}포인트만큼 베팅하셨습니다!", inline=True)
                                    await interaction.response.send_message(embed=userembed)

                            await refresh_prediction(이름,anonymbool,complete_anonymbool,p.votes[이름]['prediction'])  

                            return

        if 이름 == "지모":
            await handle_bet(p.jimo_winbutton)
        elif 이름 == "Melon":
            await handle_bet(p.melon_winbutton)

    @app_commands.command(name="대결베팅",description="대결의 승부예측에 걸 포인트를 설정합니다.")
    @app_commands.describe(포인트 = "베팅할 포인트를 선택하세요 (자연수만)")
    async def 대결베팅(self, interaction: discord.Interaction, 포인트:int):
        async def handle_bet(winbutton):
            if 포인트 <= 0:
                await interaction.response.send_message("포인트는 0보다 큰 숫자로 입력해주세요",ephemeral=True)
                return
            if winbutton.disabled == True:
                await interaction.response.send_message(f"지금은 대결에 베팅할 수 없습니다!",ephemeral=True)
                return
            

            nickname = interaction.user.name
            if (nickname not in [winner['name'].name for winner in p.votes['배틀']['prediction']['win']] and
            nickname not in [loser['name'].name for loser in p.votes['배틀']['prediction']['lose']]):
                await interaction.response.send_message(f"승부예측 후 이용해주세요",ephemeral=True)
            else:
                for winner in p.votes['배틀']['prediction']['win']:
                    if winner['name'].name == nickname:
                        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                        current_predict_season = cur_predict_seasonref.get()
                        ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner['name'].name}")
                        ref2 = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner['name'].name}/베팅포인트")
                        bettingPoint = ref2.get()
                        info = ref.get()

                        if info['포인트'] - bettingPoint < 포인트:
                            await interaction.response.send_message(f"포인트가 부족합니다!\n현재 포인트: {info['포인트'] - bettingPoint}(베팅 금액 {bettingPoint}P) 제외",ephemeral=True)
                        else:
                            winner['points'] += 포인트  # 포인트 수정
                            ref.update({"베팅포인트" : bettingPoint + 포인트}) # 파이어베이스에 베팅포인트 추가
                            userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                            if winner['points'] != 포인트:
                                userembed.add_field(name="",value=f"{interaction.user.display_name}님이 {p.votes['배틀']['name']['challenger'].mention}에게 {포인트}포인트만큼 추가 베팅하셨습니다!", inline=True)
                                await interaction.response.send_message(embed=userembed)
                            else:
                                userembed.add_field(name="",value=f"{interaction.user.display_name}님이 {p.votes['배틀']['name']['challenger'].mention}에게 {포인트}포인트만큼 베팅하셨습니다!", inline=True)
                                await interaction.response.send_message(embed=userembed)

                            # 새로고침
                            prediction_embed = update_prediction_embed(p,p.votes['배틀']['name']['challenger'],p.votes['배틀']['name']['상대'])
                            await p.battle_message.edit(embed=prediction_embed)
                            
                            return

                # 패배 예측에서 닉네임 찾기
                for loser in p.votes['배틀']['prediction']['lose']:
                    if loser['name'].name == nickname:
                        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                        current_predict_season = cur_predict_seasonref.get()
                        ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{loser['name'].name}")
                        ref2 = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{loser['name'].name}/베팅포인트")
                        bettingPoint = ref2.get()
                        info = ref.get()
    
                        if info['포인트'] - bettingPoint < 포인트:
                            await interaction.response.send_message(f"포인트가 부족합니다!\n현재 포인트: {info['포인트'] - bettingPoint}(베팅 금액 {bettingPoint}P) 제외",ephemeral=True)
                        else:                    
                            loser['points'] += 포인트  # 포인트 수정
                            ref.update({"베팅포인트" : bettingPoint + 포인트}) # 파이어베이스에 베팅포인트 추가
                            userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                            if loser['points'] != 포인트:
                                userembed.add_field(name="",value=f"{interaction.user.display_name}님이 {p.votes['배틀']['name']['상대'].mention}에게 {포인트}포인트만큼 추가 베팅하셨습니다!", inline=True)
                                await interaction.response.send_message(embed=userembed)
                            else:
                                userembed.add_field(name="",value=f"{interaction.user.display_name}님이 {p.votes['배틀']['name']['상대'].mention}에게 {포인트}포인트만큼 베팅하셨습니다!", inline=True)
                                await interaction.response.send_message(embed=userembed)

                            # 새로고침
                            prediction_embed = update_prediction_embed(p,p.votes['배틀']['name']['challenger'],p.votes['배틀']['name']['상대'])
                            await p.battle_message.edit(embed=prediction_embed)

                            return

        await handle_bet(p.battle_winbutton)

    @app_commands.command(name="승리",description="베팅 승리판정(개발자 전용)")
    @app_commands.describe(이름 = "이름을 입력하세요", 포인트 = "얻을 포인트를 입력하세요", 배율 = "베팅 배율을 입력하세요", 베팅금액 = "베팅한 금액을 입력하세요", 대상 = "누구에게 예측 했는지 입력하세요", 승패 = "어느 결과를 예측했는지 입력하세요")
    @app_commands.choices(대상=[
    Choice(name='지모', value='지모'),
    Choice(name='Melon', value='Melon'),
    ])
    @app_commands.choices(승패=[
    Choice(name='승리', value='승리'),
    Choice(name='패배', value='패배'),
    ])
    async def 승리(self, interaction: discord.Interaction, 이름:discord.Member, 포인트:int, 배율:float, 베팅금액:int, 대상:str, 승패:str):
        userembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
        if interaction.user.name == "toe_kyung":
            cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
            current_predict_season = cur_predict_seasonref.get()
            point_ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{이름.name}')
            predict_data = point_ref.get()
            point = predict_data["포인트"]
            bettingPoint = predict_data["베팅포인트"]

            # 예측 내역 업데이트
            point_ref.update({
                "포인트": point,
                "총 예측 횟수": predict_data["총 예측 횟수"] + 1,
                "적중 횟수": predict_data["적중 횟수"] + 1,
                "적중률": f"{round((((predict_data['적중 횟수'] + 1) * 100) / (predict_data['총 예측 횟수'] + 1)), 2)}%",
                "연승": predict_data["연승"] + 1,
                "연패": 0,
                "베팅포인트": bettingPoint - 베팅금액,

                # 추가 데이터
                f"{대상}적중": predict_data.get(f"{대상}적중", 0) + 1,
                f"{대상}{승패}예측": predict_data.get(f"{대상}{승패}예측", 0) + 1,
                f"{승패}예측연속": predict_data.get(f"{승패}예측연속", 0) + 1
            })

            # ====================  [미션]  ====================
            # 일일미션 : 승부예측 1회 적중
            cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
            current_predict_season = cur_predict_seasonref.get()
            ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{이름.name}/미션/일일미션/승부예측 1회 적중")
            mission_data = ref.get() or {}
            mission_bool = mission_data.get('완료', False)
            if not mission_bool:
                ref.update({"완료": True})
                print(f"{이름.display_name}의 [승부예측 1회 적중] 미션 완료")

            # ====================  [미션]  ====================

            win_streak = predict_data.get("연승",0) + 1
            bonus_rate = calculate_bonus_rate(win_streak)
            if win_streak > 1:
                add_points = 포인트 + round(베팅금액*(배율+bonus_rate))
                userembed.add_field(name="",value=f"{이름.display_name}님이 {add_points}(베팅 보너스 + {round(베팅금액*배율)})(연속적중 보너스 {bonus_rate}배!) 점수를 획득하셨습니다! (베팅 포인트:{베팅금액})", inline=False)
                point_ref.update({"포인트": point + add_points - 베팅금액})
            else:
                add_points = 포인트 + round(베팅금액*배율)
                userembed.add_field(name="",value=f"{이름.display_name}님이 {add_points}(베팅 보너스 + {round(베팅금액*배율)}) 점수를 획득하셨습니다! (베팅 포인트:{베팅금액})", inline=False)
                point_ref.update({"포인트": point + add_points - 베팅금액})


            await interaction.response.send_message(embed=userembed)
        else:
            print(f"{interaction.user.display_name}의 승리 명령어 요청")
            interaction.response.send_message("권한이 없습니다",ephemeral=True)

    @app_commands.command(name="패배",description="베팅 패배판정(개발자 전용)")
    @app_commands.describe(이름 = "이름을 입력하세요", 베팅금액 = "베팅한 금액을 입력하세요", 대상 = "누구에게 예측 했는지 입력하세요", 승패 = "어느 결과를 예측했는지 입력하세요")
    @app_commands.choices(대상=[
    Choice(name='지모', value='지모'),
    Choice(name='Melon', value='Melon'),
    ])
    @app_commands.choices(승패=[
    Choice(name='승리', value='승리'),
    Choice(name='패배', value='패배'),
    ])
    async def 패배(self, interaction: discord.Interaction, 이름:discord.Member, 베팅금액:int, 환급금액:int, 대상:str, 승패:str):
        userembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
        if interaction.user.name == "toe_kyung":
            cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
            current_predict_season = cur_predict_seasonref.get()
            point_ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{이름.name}')
            predict_data = point_ref.get()
            point = predict_data["포인트"]
            bettingPoint = predict_data["베팅포인트"]

            # 예측 내역 업데이트
            point_ref.update({
                "포인트": point,
                "총 예측 횟수": predict_data["총 예측 횟수"] + 1,
                "적중 횟수": predict_data["적중 횟수"],
                "적중률": f"{round((((predict_data['적중 횟수']) * 100) / (predict_data['총 예측 횟수'] + 1)), 2)}%",
                "연승": 0,
                "연패": predict_data["연패"] + 1,
                "베팅포인트": bettingPoint - 베팅금액,
                
                # 추가 데이터
                f"{대상}{승패}예측": predict_data.get(f"{대상}{승패}예측", 0) + 1,
                f"{승패}예측연속": predict_data.get(f"{승패}예측연속", 0) + 1
            })

            if 베팅금액 == 0:
                userembed.add_field(name="",value=f"{이름.display_name}님이 예측에 실패했습니다!", inline=False)
            else:
                userembed.add_field(name="",value=f"{이름.display_name}님이 예측에 실패하여 베팅포인트를 잃었습니다! (베팅 포인트:-{베팅금액})(환급 포인트: {환급금액})", inline=False)
                point_ref.update({"포인트": point - 베팅금액 + 환급금액})

            await interaction.response.send_message(embed=userembed)
        else:
            print(f"{interaction.user.name}의 패배 명령어 요청")
            interaction.response.send_message("권한이 없습니다",ephemeral=True)

    @app_commands.command(name="재부팅",description="봇 재부팅(개발자 전용)")
    async def 재부팅(self, interaction: discord.Interaction):
        if interaction.user.name == "toe_kyung":
            restart_script()
        else:
            interaction.response.send_message("권한이 없습니다",ephemeral=True)

    @app_commands.command(
        name="확성기",
        description="예측 포인트를 사용하여 확성기 채널에 메세지를 보냅니다(비익명 100P, 익명 150P)"
    )
    @app_commands.describe(익명여부="익명 또는 비익명을 선택하세요")
    @app_commands.choices(익명여부=[
        Choice(name='익명', value='익명'),
        Choice(name='비익명', value='비익명')
    ])
    async def 확성기(self, interaction: discord.Interaction, 익명여부: str):
        # 명령어 옵션으로 받은 익명여부를 모달 생성자에 전달하여 모달 호출
        await interaction.response.send_modal(확성기모달(익명여부))
    
    # 명령어에서 모달을 호출하는 예제
    @app_commands.command(name="공지", description="확성기 채널에 공지 메세지를 보냅니다(개발자 전용)")
    async def 공지(self,interaction: discord.Interaction):
        await interaction.response.send_modal(공지모달())
    

    @app_commands.command(name="테스트",description="테스트(개발자 전용)")
    @app_commands.describe(포인트 = "포인트를 입력하세요")
    async def 테스트(self, interaction: discord.Interaction, 포인트:int):
        if interaction.user.name == "toe_kyung":
            await place_bet(self.bot,"지모","승리",포인트)
            await interaction.response.send_message("수행완료",ephemeral=True)

    @app_commands.command(name="열람포인트초기화",description="열람포인트를 100포인트로 초기화합니다(개발자 전용)")
    async def 열람포인트초기화(self, interaction: discord.Interaction):
        if interaction.user.name == "toe_kyung":
            refhon = db.reference('승부예측')
            refhon.update({"혼자보기포인트" : 100})

    @app_commands.command(name="베팅포인트초기화",description="모두의 베팅포인트를 제거합니다(개발자 전용)")
    async def 베팅포인트초기화(self, interaction: discord.Interaction):
        if interaction.user.name == "toe_kyung":
            cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
            current_predict_season = cur_predict_seasonref.get()

            point_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트")
            
            users = point_ref.get()
            if users is None:
                await interaction.response.send_message("현재 시즌의 유저 데이터가 없습니다.")
                return

            # 각 유저의 베팅포인트 필드를 0으로 업데이트할 업데이트 딕셔너리 생성
            updates = {}
            for user_id in users.keys():
                updates[f"{user_id}/베팅포인트"] = 0

            point_ref.update(updates)
            
            await interaction.response.send_message("베팅포인트 초기화 완료!")
    
    @app_commands.command(name="베팅공개",description="현재 포인트의 10%(최소 100p)를 소모하여 현재 진행중인 승부예측의 현황을 공개합니다(3분 이후만 가능)")
    @app_commands.describe(이름 = "예측한 사람의 이름을 입력하세요")
    @app_commands.choices(이름=[
    Choice(name='지모', value='지모'),
    Choice(name='Melon', value='Melon'),
    ])
    async def 베팅공개(self, interaction: discord.Interaction, 이름: str):
        async def bet_open(winbutton):
            if winbutton.disabled == True:
                if p.votes.get(이름, {}).get('prediction', {}).get('win') or p.votes.get(이름, {}).get('prediction', {}).get('lose'):
                    cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                    current_predict_season = cur_predict_seasonref.get()
                    ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{interaction.user.name}')
                    originr = ref.get()
                    point = originr["포인트"]
                    bettingPoint = originr["베팅포인트"]
                    real_point = point - bettingPoint
                    need_point = round(real_point * 0.1) # 10% 지불
                    if need_point < 100:
                        need_point = 100
                    if real_point < 100:
                        await interaction.response.send_message(f"포인트가 부족합니다! 현재 포인트: {real_point} (베팅포인트 {bettingPoint} 제외)",ephemeral=True)
                        return
                    channel = self.bot.get_channel(int(CHANNEL_ID))
                    userembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
                    userembed.add_field(name="",value=f"{interaction.user.display_name}님이 포인트를 소모하여 {이름}의 예측 현황을 공개했습니다!", inline=False)
                    await channel.send(f"\n",embed = userembed)
                    
                    await refresh_prediction(이름,False,False,p.votes[이름]['prediction'])
                    
                    ref.update({"포인트" : point - need_point})
                    current_datetime = datetime.now() # 데이터베이스에 남길 현재 시각 기록
                    current_date = current_datetime.strftime("%Y-%m-%d")
                    current_time = current_datetime.strftime("%H:%M:%S")
                    change_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트변동로그/{current_date}/{interaction.user.name}")
                    change_ref.push({
                        "시간": current_time,
                        "포인트": point - need_point,
                        "포인트 변동": -need_point,
                        "사유": "베팅공개 구매"
                    })

                    await interaction.response.send_message(f"{need_point}포인트 지불 완료! 현재 포인트: {real_point - need_point} (베팅포인트 {bettingPoint} 제외)",ephemeral=True)
                else:
                    await interaction.response.send_message(f"{이름}에게 아무도 투표하지 않았습니다!",ephemeral=True)
            else:
                await interaction.response.send_message(f"{이름}의 투표가 끝나지 않았습니다!",ephemeral=True)

        if 이름 == "지모":
            await bet_open(p.jimo_winbutton)
        elif 이름 == "Melon":
            await bet_open(p.melon_winbutton)
        
    @app_commands.command(name="지급_아이템",description="아이템을 지급합니다(관리자 전용)")
    @app_commands.describe(이름 = "아이템을 지급할 사람을 입력하세요")
    @app_commands.describe(아이템 = "지급할 아이템을 입력하세요")
    @app_commands.choices(아이템=[
    Choice(name='배율증가 0.1', value='배율증가1'),
    Choice(name='배율증가 0.3', value='배율증가3'),
    Choice(name='배율증가 0.5', value='배율증가5'),
    Choice(name='주사위 초기화', value='주사위 초기화'),
    Choice(name='야추 초기화', value='야추 초기화'),
    Choice(name='레이드 재도전', value='레이드 재도전'),
    Choice(name='강화재료', value='강화재료'),
    Choice(name='탑코인', value='탑코인'),
    Choice(name='랜덤박스', value='랜덤박스'),
    ])
    async def 아이템지급(self, interaction: discord.Interaction, 이름: discord.Member, 아이템:str, 개수:int):
        if interaction.user.name == "toe_kyung":
            give_item(이름.name,아이템,개수)
            channel = self.bot.get_channel(int(CHANNEL_ID))
            userembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
            userembed.add_field(name="",value=f"{이름.mention}에게 [{아이템}] {개수}개가 지급되었습니다!", inline=False)
            await channel.send(f"\n",embed = userembed)
            await interaction.response.send_message(f"{이름.mention}에게 [{아이템}] {개수}개 지급 완료!",ephemeral=True)
        else:
            await interaction.response.send_message("권한이 없습니다",ephemeral=True)

    @app_commands.command(name="전체지급_아이템",description="아이템을 모두에게 지급합니다(관리자 전용)")
    @app_commands.describe(아이템 = "지급할 아이템을 입력하세요")
    @app_commands.choices(아이템=[
    Choice(name='배율증가 0.1', value='배율증가1'),
    Choice(name='배율증가 0.3', value='배율증가3'),
    Choice(name='배율증가 0.5', value='배율증가5'),
    Choice(name='주사위 초기화', value='주사위 초기화'),
    Choice(name='야추 초기화', value='야추 초기화'),
    Choice(name='레이드 재도전', value='레이드 재도전'),
    Choice(name='강화재료', value='강화재료'),
    Choice(name='탑코인', value='탑코인'),
    Choice(name='랜덤박스', value='랜덤박스'),
    ])
    async def 아이템전체지급(self, interaction: discord.Interaction,아이템:str, 개수:int):
        if interaction.user.name == "toe_kyung":
            await interaction.response.defer()
            cur_predict_seasonref = db.reference("승부예측/현재예측시즌") # 현재 진행중인 예측 시즌을 가져옴
            current_predict_season = cur_predict_seasonref.get()
            ref_users = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트')
            users = ref_users.get()
            nicknames = list(users.keys())
            for nickname in nicknames:
                give_item(nickname,아이템,개수)
            channel = self.bot.get_channel(int(CHANNEL_ID))
            userembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
            userembed.add_field(name="",value=f"모두에게 [{아이템}] {개수}개가 지급되었습니다!", inline=False)
            await channel.send(f"\n",embed = userembed)
            await interaction.followup.send(f"모두에게 [{아이템}] {개수}개 지급 완료!",ephemeral=True)
        else:
            await interaction.response.send_message("권한이 없습니다",ephemeral=True)

    @app_commands.command(name="아이템",description="자신의 아이템을 확인합니다")
    @app_commands.choices(타입=[
    Choice(name="일반 아이템", value="일반"),
    Choice(name="무기 관련 아이템", value="무기")
    ])
    async def 아이템(self, interaction: discord.Interaction, 타입:str):
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") # 현재 진행중인 예측 시즌을 가져옴
        current_predict_season = cur_predict_seasonref.get()

        nickname = interaction.user
        if 타입 == "일반":
            refitem = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname.name}/아이템')
        else:
            refitem = db.reference(f'무기/아이템/{nickname.name}')
        itemr = refitem.get()
        embed = discord.Embed(title="📦 보유 아이템 목록", color=discord.Color.purple())

        if not itemr:
            embed.description = "현재 보유 중인 아이템이 없습니다. 🫥"
        else:
            item_lines = []
            for item_name, count in itemr.items():
                if isinstance(count, bool):
                    display_value = "활성" if count else "비활성"
                else:
                    display_value = f"{count}개"
                item_lines.append(f"• **{item_name}** — {display_value}")
            
            embed.add_field(
                name="보유 중인 아이템",
                value="\n".join(item_lines),
                inline=False
            )

        await interaction.response.send_message(embed=embed,ephemeral=True)

    @app_commands.command(name="자동예측",description="승부예측을 자동으로 예측합니다")
    @app_commands.choices(이름=[
    Choice(name='지모', value='지모'),
    Choice(name='Melon', value='Melon')
    ])
    @app_commands.choices(승패=[
    Choice(name='승리', value="승리"),
    Choice(name='패배', value="패배")
    ])
    @app_commands.choices(온오프=[
    Choice(name='온', value="on"),
    Choice(name='오프', value="off")
    ])
    async def 자동예측(self, interaction: discord.Interaction, 이름:str, 승패:str, 온오프:str):
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") # 현재 진행중인 예측 시즌을 가져옴
        current_predict_season = cur_predict_seasonref.get()

        nickname = interaction.user
        
        if 승패 == "승리":
            winlosebool = True
        else:
            winlosebool = False

        if 온오프 == "on":
            onoffbool = True
        else:
            onoffbool = False

        refitem = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname.name}/아이템')
        itemr = refitem.get()

        if not onoffbool:
            if winlosebool:
                if itemr.get("자동예측" + 이름 + "패배", False):
                    await interaction.response.send_message(f"이미 {이름}의 패배에 자동예측중입니다. </자동예측변경:1337254677326073929> 명령어를 사용하거나 패배로 취소해주세요!",ephemeral=True) 
                elif itemr.get("자동예측" + 이름 + "승리", False):
                    item_name = "자동예측" + 이름 + "승리"
                    refitem = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname}/아이템')
                    item_data = refitem.get()

                    refitem.update({item_name: False})
                    await interaction.response.send_message(f"{이름}의 {승패}에 자동예측취소! \n",ephemeral=True)
                else:
                    await interaction.response.send_message(f"{이름}의 {승패}에 자동예측한 내역이 없습니다! \n",ephemeral=True)
            else:
                if itemr.get("자동예측" + 이름 + "승리", False):
                    await interaction.response.send_message(f"이미 {이름}의 승리에 자동예측중입니다. </자동예측변경:1337254677326073929> 명령어를 사용하거나 승리로 취소해주세요!",ephemeral=True) 
                elif itemr.get("자동예측" + 이름 + "패배", False):
                    item_name = "자동예측" + 이름 + "패배"
                    refitem = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname}/아이템')
                    item_data = refitem.get()

                    refitem.update({item_name: False})
                    await interaction.response.send_message(f"{이름}의 {승패}에 자동예측취소! \n",ephemeral=True)
                else:
                    await interaction.response.send_message(f"{이름}의 {승패}에 자동예측한 내역이 없습니다! \n",ephemeral=True)
        if onoffbool:
            if winlosebool:
                if itemr.get("자동예측" + 이름 + "패배", False):
                    await interaction.response.send_message(f"이미 {이름}의 패배에 자동예측중입니다. </자동예측변경:1337254677326073929> 명령어를 사용해주세요!",ephemeral=True) 
                else:
                    item_name = "자동예측" + 이름 + "승리"
                    refitem = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname}/아이템')
                    item_data = refitem.get()

                    refitem.update({item_name: True})
                    await interaction.response.send_message(f"{이름}의 {승패}에 자동예측! \n",ephemeral=True)
            else:
                if itemr.get("자동예측" + 이름 + "승리", False):
                    await interaction.response.send_message(f"이미 {이름}의 승리에 자동예측중입니다. </자동예측변경:1337254677326073929> 명령어를 사용해주세요!",ephemeral=True) 
                else:
                    item_name = "자동예측" + 이름 + "패배"
                    refitem = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname}/아이템')
                    item_data = refitem.get()

                    refitem.update({item_name: True})
                    await interaction.response.send_message(f"{이름}의 {승패}에 자동예측! \n",ephemeral=True)
    
    @app_commands.command(name="예측확인", description="현재 내가 투표한 항목을 확인합니다.")
    async def check_my_vote(self,interaction: discord.Interaction):
        nickname = interaction.user.name  # 현재 유저의 닉네임
        results = []  # 투표 내역 저장 리스트

        # 확인할 플레이어 목록
        players = ["지모", "Melon"]

        for player in players:
            if player in p.votes:
                player_votes = []

                # 승부 예측 (win/lose)
                for outcome in ["win", "lose"]:
                    if any(entry['name'].name == nickname for entry in p.votes[player]["prediction"][outcome]):
                        player_votes.append(f"- {outcome.upper()} (승부예측)")

                # KDA 예측 (up/down/perfect)
                for outcome in ["up", "down", "perfect"]:
                    if any(entry['name'].name == nickname for entry in p.votes[player]["kda"][outcome]):
                        player_votes.append(f"- {outcome.upper()} (KDA예측)")

                # 플레이어별로 투표 내역 정리
                if player_votes:
                    results.append(f"✅ **{player}에 대한 투표 내역:**\n" + "\n".join(player_votes))

        # 최종 메시지 출력
        if results:
            message = "\n\n".join(results)
        else:
            message = "❌ 현재 투표한 항목이 없습니다."

        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(name="자동예측변경",description="보유한 자동예측의 승패를 바꿉니다.")
    @app_commands.choices(이름=[
    Choice(name='지모', value='지모'),
    Choice(name='Melon', value='Melon')
    ])
    async def 자동예측변경(self, interaction: discord.Interaction, 이름:str):
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") # 현재 진행중인 예측 시즌을 가져옴
        current_predict_season = cur_predict_seasonref.get()

        nickname = interaction.user

        refitem = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname.name}/아이템')
        itemr = refitem.get()
        
    
        if itemr.get("자동예측" + 이름 + "승리", False):
            item_num = itemr.get("자동예측" + 이름 + "승리", False)
            refitem.update({
                f"자동예측{이름}패배": True,
                f"자동예측{이름}승리": False
            })
            await interaction.response.send_message(f"{이름}의 자동예측을 승리에서 패배로 변경했습니다!",ephemeral=True) 
        elif itemr.get("자동예측" + 이름 + "패배", False):
            refitem.update({
                f"자동예측{이름}승리": True,
                f"자동예측{이름}패배": False
            })
            await interaction.response.send_message(f"{이름}의 자동예측을 패배에서 승리로 변경했습니다!",ephemeral=True) 
        else:
            await interaction.response.send_message(f"{이름}에게 자동예측을 하고 있지 않습니다!",ephemeral=True)
            return      
        
    @app_commands.command(name="일일미션추가",description="일일미션을 추가합니다(관리자 전용)")
    async def 일일미션추가(self,interaction: discord.Interaction, 미션이름:str, 포인트:int):
        await interaction.response.defer()
        
        result = await add_missions_to_all_users(미션이름,포인트,"일일미션")

        if result:
            await interaction.followup.send(f"미션을 추가했습니다.",ephemeral=True)
        else:
            await interaction.followup.send("유저가 존재하지 않습니다.",ephemeral=True)

    @app_commands.command(name="시즌미션추가",description="시즌미션을 추가합니다(관리자 전용)")
    async def 시즌미션추가(self,interaction: discord.Interaction, 미션이름:str, 포인트:int):
        await interaction.response.defer()

        result = await add_missions_to_all_users(미션이름,포인트,"시즌미션")

        if result:
            await interaction.followup.send(f"미션을 추가했습니다.",ephemeral=True)
        else:
            await interaction.followup.send("유저가 존재하지 않습니다.",ephemeral=True)
    
    @app_commands.command(name="미션삭제", description="일일미션 또는 시즌미션을 삭제합니다.(관리자 전용용)")
    @app_commands.choices(미션종류=[
    Choice(name='일일미션', value='일일미션'),
    Choice(name='시즌미션', value='시즌미션')
    ])
    async def remove_mission(self, interaction: discord.Interaction, 미션이름: str, 미션종류: str):
        await interaction.response.defer()

        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")  # 현재 진행중인 예측 시즌을 가져옴
        current_predict_season = cur_predict_seasonref.get()
        
        # '예측포인트' 경로 아래의 모든 유저들 가져오기
        ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트")
        all_users = ref.get()

        if not all_users:
            await interaction.followup.send("유저가 존재하지 않습니다.", ephemeral=True)
            return

        deleted = False  # 삭제 여부를 추적

        # 각 유저에서 특정 미션 삭제
        for user_id, user_data in all_users.items():
            # 각 유저의 '미션' 경로
            user_missions_ref = ref.child(user_id).child("미션").child(미션종류)

            # 유저의 미션 목록을 가져옴
            mission_type_data = user_data.get("미션", {}).get(미션종류, {})

            # 미션 목록에서 미션 이름이 일치하는 미션을 찾아 삭제
            if 미션이름 in mission_type_data:
                user_missions_ref.child(미션이름).delete()  # 미션 이름으로 삭제
                deleted = True

        if deleted:
            await interaction.followup.send(f"미션 '{미션이름}'을 삭제했습니다.", ephemeral=True)
        else:
            await interaction.followup.send(f"미션 '{미션이름}'을 찾을 수 없습니다.", ephemeral=True)

    @app_commands.command(name="업적", description="시즌미션의 상세 정보를 확인합니다.")
    async def get_user_missions(self, interaction: discord.Interaction):
        user_id = interaction.user.name
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
        current_predict_season = cur_predict_seasonref.get()

        ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{user_id}/미션")
        user_missions = ref.get()

        if not user_missions:
            await interaction.response.send_message("현재 진행 중인 미션이 없습니다.", ephemeral=True)
            return  # 중복 응답 방지

        mission_details = {
            "깜잘알": "지모의 승부예측 50번 적중 🧠. 지모의 게임결과를 정확히 예측하며 진정한 깜잘알로 거듭나자 🎯.",
            "난 이기는 판만 걸어": "오직 승리예측만으로 5연속 적중 💪. 승리가 아니면 죽음을! ⚔️",
            "금지된 숫자": "2669 포인트를 베팅하고 적중 💀. 절대 이 숫자의 의미를 말해선 안돼 🔒.",
            "도파민 중독": "올인으로 연속 3번 베팅 (1000포인트 이상) 🎲. 걸고, 걸고, 또 건다 🔥.",
            "마이너스의 손": "📉 실패의 끝을 보여줘라. 승부예측 10연속 비적중 달성",
            "누구에게도 말할 수 없는 비밀": "혼자보기 포인트가 500 이상일 때 예측순위 혼자보기 🤫. 모두에게 보여줄 바엔 혼자만 본다. 🕵️‍♂️.",
            "쿵쿵따": "두 번 연속 실패 후, 다음 예측에서 적중 💥. 앞선 2번의 실패는 다음 성공을 위한 준비 과정이었다 💪.",
            "정점": "주사위에서 100을 뽑기 🎲. 주사위의 정점을 달성하자 🏆.",
            "이럴 줄 알았어": "10데스 이상 판에서 패배를 예측하고 적중 🥲. 난 이 판 질 줄 알았음... 😎",
            "다중 그림자분신술": "한 게임에서 100포인트 이상 5번 베팅 🌀. 분신술을 쓴 것처럼 계속 베팅하라 🔮.",
            "졌지만 이겼다": "패배를 예측하고, 퍼펙트를 건 뒤 둘 다 적중 🥇. 게임은 졌지만 난 승리했다 👑.",
            "0은 곧 무한": "/베팅 명령어로 0포인트 베팅 🔢. 설마 0포인트를 베팅하는 사람이 있겠어? 🤨",
            "크릴새우": "/베팅 명령어로 1 포인트 베팅 🦐. 이게 크릴새우지 🦑.",
            "주사위주사위주사위주사위주사위": "하루에 /주사위 명령어를 5번 실행 🎲. 경고 문구는 가볍게 무시한다 🚫.",
            "이카루스의 추락": "너무 높이 날면 떨어지는 법 🕊️. 단 한 번에 80% 이상의 포인트(1000포인트 이상)를 잃고, 이카루스처럼 추락하는 순간을 경험하라 🪂.",
            "이 모양은 고양이?!": "/시즌그래프 명령어에서 대상으로 [고양이]를 선택 🐾. 누군가의 그래프에서는 고양이가 보인다는 소문이 있다... 🐱"

        }

        embed = discord.Embed(title="📜 시즌 미션 상세 정보", color=discord.Color.gold())


        ref_unlocked = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{user_id}/업적해금")
        achievement_unlocked = ref_unlocked.get() or False  # 값이 없으면 False로 처리

        for mission_type, missions in user_missions.items():
            for mission_name, mission_data in missions.items():
                if mission_type == "시즌미션":
                    description = mission_details.get(mission_name, "설명이 없습니다.")
                    if not mission_data.get("완료", False) and not achievement_unlocked:
                        description = "??"
                    embed.add_field(name=mission_name, value=description, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="업적공개", description="달성한 업적을 다른 사람들에게 공개합니다.")
    @app_commands.choices(내용공개=[
    Choice(name='공개', value='공개'),
    Choice(name='비공개', value='시즌미션')
    ])
    async def show_user_missions(self, interaction: discord.Interaction, 내용공개:str):
        user_id = interaction.user.name
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
        current_predict_season = cur_predict_seasonref.get()

        ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{user_id}/미션")
        user_missions = ref.get()

        if not user_missions:
            await interaction.response.send_message("현재 진행 중인 미션이 없습니다.", ephemeral=True)
            return  # 중복 응답 방지

        select = discord.ui.Select(placeholder='공개할 업적을 선택하세요')

        mission_details = {
            "깜잘알": "지모의 승부예측 50번 적중 🧠. 지모의 게임결과를 정확히 예측하며 진정한 깜잘알로 거듭나자 🎯.",
            "난 이기는 판만 걸어": "오직 승리예측만으로 5연속 적중 💪. 승리가 아니면 죽음을! ⚔️",
            "금지된 숫자": "2669 포인트를 베팅하고 적중 💀. 절대 이 숫자의 의미를 말해선 안돼 🔒.",
            "도파민 중독": "올인으로 연속 3번 베팅 (1000포인트 이상) 🎲. 걸고, 걸고, 또 건다 🔥.",
            "마이너스의 손": "📉 실패의 끝을 보여줘라. 승부예측 10연속 비적중 달성",
            "누구에게도 말할 수 없는 비밀": "혼자보기 포인트가 500 이상일 때 예측순위 혼자보기 🤫. 모두에게 보여줄 바엔 혼자만 본다. 🕵️‍♂️.",
            "쿵쿵따": "두 번 연속 실패 후, 다음 예측에서 적중 💥. 앞선 2번의 실패는 다음 성공을 위한 준비 과정이었다 💪.",
            "정점": "주사위에서 100을 뽑기 🎲. 주사위의 정점을 달성하자 🏆.",
            "이럴 줄 알았어": "10데스 이상 판에서 패배를 예측하고 적중 🥲. 난 이 판 질 줄 알았음... 😎",
            "다중 그림자분신술": "한 게임에서 100포인트 이상 5번 베팅 🌀. 분신술을 쓴 것처럼 계속 베팅하라 🔮.",
            "졌지만 이겼다": "패배를 예측하고, 퍼펙트를 건 뒤 둘 다 적중 🥇. 게임은 졌지만 난 승리했다 👑.",
            "0은 곧 무한": "/베팅 명령어로 0포인트 베팅 🔢. 설마 0포인트를 베팅하는 사람이 있겠어? 🤨",
            "크릴새우": "/베팅 명령어로 1 포인트 베팅 🦐. 이게 크릴새우지 🦑.",
            "주사위주사위주사위주사위주사위": "하루에 /주사위 명령어를 5번 실행 🎲. 경고 문구는 가볍게 무시한다 🚫.",
            "이카루스의 추락": "너무 높이 날면 떨어지는 법 🕊️. 단 한 번에 80% 이상의 포인트(1000포인트 이상)를 잃고, 이카루스처럼 추락하는 순간을 경험하라 🪂.",
            "이 모양은 고양이?!": "/시즌그래프 명령어에서 대상으로 [고양이]를 선택 🐾. 누군가의 그래프에서는 고양이가 보인다는 소문이 있다... 🐱"
        }
   
        mission_options = []
        for mission_type, missions in user_missions.items():
            for mission_name, mission_data in missions.items():
                if mission_type == "시즌미션":
                    if mission_data.get("완료", False):  # 완료된 미션은 "완료"로 표시
                        # Select 옵션에 추가
                        description = mission_details.get(mission_name, "설명이 없습니다.")
                        mission_options.append((mission_name,description))

        # Select 옵션 설정
        for i, (mission_name, description) in enumerate(mission_options):
            select.add_option(label=mission_name, value=mission_name, description=description)
            
        # Select에 대한 처리하는 이벤트 핸들러를 View에 추가
        async def select_callback(interaction: discord.Interaction):
            selected_mission_name = select.values[0]  # 사용자가 선택한 미션명

            # 선택된 미션의 상세 정보를 가져와서 embed에 포함
            for mission_type, missions in user_missions.items():
                for mission_name, mission_data in missions.items():
                    if mission_name == selected_mission_name:
                        embed = discord.Embed(
                            title="업적 공개!",
                            description=f"{interaction.user.display_name}님이 업적을 공개했습니다!",
                            color=discord.Color.gold()
                        )
                        
                        if 내용공개 == "공개":
                            embed.add_field(
                                name=f"",
                                value="",
                                inline=False
                            )
                            embed.add_field(
                                name=f"{selected_mission_name}",
                                value="\u200b\n" + mission_details.get(selected_mission_name, "설명이 없습니다."),
                                inline=False
                            )
                        else:
                            embed.add_field(
                                name=f"",
                                value="",
                                inline=False
                            )
                            embed.add_field(
                                name=f"{selected_mission_name}",
                                value="\u200b\n" + "이 업적은 비공개 상태입니다.",
                                inline=False
                            )
                        
                        await interaction.response.send_message(embed=embed)
                        return

        # View 생성 후 select 콜백 함수 추가
        view = discord.ui.View()
        select.callback = select_callback
        view.add_item(select)

        # Select 위젯을 포함한 메시지 보내기
        await interaction.response.send_message("달성한 업적을 선택해주세요.", view=view,ephemeral=True)
    
    @app_commands.command(name="주사위",description="주사위를 굴립니다. 하루에 한 번만 가능합니다.(1 ~ 100)")
    async def 주사위(self, interaction: discord.Interaction):
        nickname = interaction.user.name
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
        current_predict_season = cur_predict_seasonref.get()

        ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname}/주사위")
        dice = ref.get() or False

        await interaction.response.defer()
        if not dice:  # 주사위를 아직 안 굴렸다면
            dice_num = secrets.randbelow(100) + 1
            ref.set(dice_num)  # 주사위 값 저장
            embed = discord.Embed(
                title="🎲 주사위 굴리기!",
                description=f"{interaction.user.display_name}님이 주사위를 굴렸습니다!",
                color=discord.Color.blue()
            )
            embed.add_field(name="🎲 결과", value=f"**{dice_num}**", inline=False)
            embed.set_footer(text="내일 다시 도전할 수 있습니다!")
            
        
            # ====================  [미션]  ====================
            # 일일미션 : 주사위 굴리기
            cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
            current_predict_season = cur_predict_seasonref.get()
            ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname}/미션/일일미션/주사위 굴리기")
            mission_data = ref.get() or {}
            mission_bool = mission_data.get('완료',0)
            if not mission_bool:
                ref.update({"완료": True})
                print(f"{nickname}의 [주사위 굴리기] 미션 완료")

            # ====================  [미션]  ====================
        else:
            ref_item = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname}/아이템")
            item_data = ref_item.get()
            dice_refresh = item_data.get('주사위 초기화', 0)
            if dice_refresh:
                ref_item.update({'주사위 초기화': dice_refresh - 1})
                dice_num = random.randint(1, 100)
                ref.set(dice_num)  # 주사위 값 저장
                embed = discord.Embed(
                    title="🎲 주사위 굴리기!",
                    description=f"{interaction.user.display_name}님이 아이템을 사용하여 주사위를 다시 굴렸습니다!",
                    color=discord.Color.blue()
                )
                embed.add_field(name="🎲 결과", value=f"**{dice_num}**", inline=False)
                embed.set_footer(text="내일 다시 도전할 수 있습니다!")
            else:
                embed = discord.Embed(
                    title="🎲 주사위는 하루에 한 번!",
                    description=f"{interaction.user.display_name}님은 이미 주사위를 굴렸습니다.",
                    color=discord.Color.red()
                )
                embed.set_footer(text="내일 다시 도전할 수 있습니다!")

        await interaction.followup.send(embed=embed)
    

    @app_commands.command(name="야추", description="주사위 5개를 굴립니다.")
    async def 야추(self, interaction: discord.Interaction):
        nickname = interaction.user.name
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
        current_predict_season = cur_predict_seasonref.get()

        ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname}/야추")
        yacht = ref.get() or {}
        yacht_bool = yacht.get("실행 여부", False)

        await interaction.response.defer()
        if not yacht_bool:  # 주사위를 아직 안 굴렸다면
            # ====================  [미션]  ====================
            # 일일미션 : 야추 1회
            cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
            current_predict_season = cur_predict_seasonref.get()
            ref_mission = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname}/미션/일일미션/야추 1회")
            mission_data = ref_mission.get() or {}
            mission_bool = mission_data.get('완료',0)
            if not mission_bool:
                ref_mission.update({"완료": True})
                print(f"{nickname}의 [야추 1회] 미션 완료")

            # ====================  [미션]  ====================
            ref.update({"실행 여부":True})
            initial_rolls = [random.randint(1, 6) for _ in range(5)]
            ref.update({"결과": initial_rolls})
            ref.update({"족보": evaluate_hand(initial_rolls)})
            view = DiceRollView(interaction.user, initial_rolls)
            dice_display = ', '.join(str(roll) for roll in initial_rolls)
            embed = discord.Embed(
                title="🎲 주사위 굴리기!",
                description=f"{interaction.user.name}님의 주사위: **{dice_display}**",
                color=discord.Color.blue()
            )
            await interaction.followup.send(embed=embed, view=view)
            await view.start_timer()
        else:
            ref_item = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname}/아이템")
            item_data = ref_item.get()
            yacht_refresh = item_data.get('야추 초기화', 0)
            if yacht_refresh:
                userembed = discord.Embed(title=f"알림", color=discord.Color.light_gray())
                userembed.add_field(name="",value=f"{interaction.user.display_name}님이 아이템을 사용하여 야추 기회를 추가했습니다!", inline=False)
                ref_item.update({"야추 초기화": yacht_refresh - 1})
                channel = interaction.client.get_channel(int(CHANNEL_ID))
                await channel.send(embed=userembed)

                ref.update({"실행 여부":True})
                initial_rolls = [random.randint(1, 6) for _ in range(5)]
                ref.update({"결과": initial_rolls})
                ref.update({"족보": evaluate_hand(initial_rolls)})
                view = DiceRollView(interaction.user, initial_rolls)
                dice_display = ', '.join(str(roll) for roll in initial_rolls)
                embed = discord.Embed(
                    title="🎲 주사위 굴리기!",
                    description=f"{interaction.user.display_name}님의 주사위: **{dice_display}**",
                    color=discord.Color.blue()
                )
                await interaction.followup.send(embed=embed, view=view)
                await view.start_timer()
            else:
                embed = discord.Embed(
                    title="🎲 야추는 하루에 한 번!",
                    description=f"{interaction.user.display_name}님은 이미 야추 다이스를 플레이 했습니다.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)


    @app_commands.command(name="업적해금", description="1000포인트를 지불하여, 아직 달성하지 않은 시즌미션의 상세 정보까지 전부 확인합니다. 15일 이후만 가능합니다.")
    async def show_missions(self, interaction: discord.Interaction):
        user_id = interaction.user.name
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
        current_predict_season = cur_predict_seasonref.get()

        point_ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{user_id}')
        originr = point_ref.get()
        point = originr["포인트"]
        bettingPoint = originr["베팅포인트"]
        real_point = point - bettingPoint
        need_point = 1000
        
        today = datetime.today().day  # 오늘 날짜의 일(day) 값 가져오기
        if today >= 15:
            if real_point < need_point:
                await interaction.response.send_message(f"포인트가 부족합니다! 현재 포인트: {real_point} (베팅포인트 {bettingPoint} 제외) \n"
                                                        f"필요 포인트 : {need_point}",ephemeral=True)
                return

            ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{user_id}")
            ref_data = ref.get()
            if ref_data.get("업적해금", False):
                embed = discord.Embed(
                title="업적 해금 불가!",
                description=f"{interaction.user.display_name}님은 이미 업적을 해금했습니다!",
                color=discord.Color.blue()
            )
            ref.update({"업적해금": True})

            embed = discord.Embed(
                title="업적 해금!",
                description=f"{interaction.user.display_name}님이 1000포인트를 지불하여 업적 정보를 열람했습니다!",
                color=discord.Color.blue()
            )

            point_ref.update({"포인트" : point - need_point})
            current_datetime = datetime.now() # 데이터베이스에 남길 현재 시각 기록
            current_date = current_datetime.strftime("%Y-%m-%d")
            current_time = current_datetime.strftime("%H:%M:%S")
            change_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트변동로그/{current_date}/{interaction.user.name}")
            change_ref.push({
                "시간": current_time,
                "포인트": point - need_point,
                "포인트 변동": -need_point,
                "사유": "업적해금 구매"
            })
            
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(
                title="해금 실패!",
                description=f"업적 해금은 15일 이후부터 가능합니다!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral = True)

    @app_commands.command(name="주사위대결",description="포인트를 걸고 주사위대결을 진행합니다. 하루에 한번만 가능합니다.")
    @app_commands.describe(상대 = "대결할 상대를 고르세요", 포인트 = "기본 베팅으로 걸 포인트를 입력하세요. (100포인트 이상)")
    async def duel(self, interaction:discord.Interaction, 상대: discord.Member, 포인트: int = 100):
        challenger = interaction.user.name
        challenger_m = interaction.user
        if 상대.name == challenger:
            warnembed = discord.Embed(title="실패",color = discord.Color.red())
            warnembed.add_field(name="",value="자기 자신에게 도전할 수 없습니다! ❌")
            await interaction.response.send_message(embed = warnembed)
            return

        battle_ref = db.reference("승부예측/대결진행여부")
        is_battle = battle_ref.get()

        if is_battle:
            warnembed = discord.Embed(title="실패",color = discord.Color.red())
            warnembed.add_field(name="",value="다른 대결이 진행중입니다! ❌")
            await interaction.response.send_message(embed = warnembed)
            return

        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
        current_predict_season = cur_predict_seasonref.get()

        battleref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{challenger}")
        battle_data = battleref.get()
        battled = battle_data.get("배틀여부",False)

        ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{challenger}')
        originr = ref.get()
        point = originr["포인트"]
        bettingPoint = originr["베팅포인트"]
        real_point = point - bettingPoint
        
        if 포인트 < 100:
            warnembed = discord.Embed(title="실패",color = discord.Color.red())
            warnembed.add_field(name="",value=f"100포인트 미만으로 베팅할 순 없습니다! ❌")
            await interaction.response.send_message("",embed = warnembed,ephemeral=True)
            return
        
        if 포인트 > real_point:
            warnembed = discord.Embed(title="실패",color = discord.Color.red())
            warnembed.add_field(name="",value=f"{challenger_m.display_name}님의 포인트가 {포인트}포인트 미만입니다! ❌")
            await interaction.response.send_message("",embed = warnembed,ephemeral=True)
            return

        if battled:
            item_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{challenger}/아이템")
            item_data = item_ref.get() or {} 
            battle_refresh = item_data.get("주사위대결기회 추가", 0)
            if battle_refresh:
                userembed = discord.Embed(title=f"알림", color=discord.Color.light_gray())
                userembed.add_field(name="",value=f"{challenger_m.display_name}님이 아이템을 사용하여 주사위 대결을 추가로 신청했습니다!", inline=False)
                channel = interaction.client.get_channel(int(CHANNEL_ID))
                await channel.send(embed=userembed)
                battle_ref.set(True)
            else:
                warnembed = discord.Embed(title="실패",color = discord.Color.red())
                warnembed.add_field(name="",value="하루에 한번만 대결 신청할 수 있습니다! ❌")
                await interaction.response.send_message("",embed = warnembed)
                return

        if real_point < 100:
            warnembed = discord.Embed(title="실패",color = discord.Color.red())
            warnembed.add_field(name="",value=f"{challenger_m.display_name}님의 포인트가 100포인트 미만입니다! ❌")
            await interaction.response.send_message("",embed = warnembed)
            battle_ref.set(False)
            return
        
        ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{상대.name}')
        originr = ref.get()
        point = originr["포인트"]
        bettingPoint = originr["베팅포인트"]
        real_point = point - bettingPoint

        if real_point < 100:
            warnembed = discord.Embed(title="실패",color = discord.Color.red())
            warnembed.add_field(name="",value=f"{상대.display_name}님의 포인트가 100포인트 미만입니다! ❌")
            await interaction.response.send_message("",embed = warnembed)
            battle_ref.set(False)
            return
        
        # 대결 요청
        view = DuelRequestView(challenger, 상대, 포인트)
        battleembed = discord.Embed(title="대결 요청!", color = discord.Color.blue())
        battleembed.add_field(name="", value=f"{상대.mention}, {challenger_m.mention}의 주사위 대결 요청! 수락하시겠습니까? 🎲\n[걸린 포인트 : {포인트}포인트]")
        # 메시지 전송
        await interaction.response.send_message(content=상대.mention, view=view, embed=battleembed)
        battle_ref.set(True)

        # 전송된 메시지 객체 가져오기
        view.message = await interaction.original_response()

        done, pending = await asyncio.wait(
            [
                asyncio.create_task(view.start_timer()),
                asyncio.create_task(view.event.wait())
            ],
            return_when=asyncio.FIRST_COMPLETED  # 첫 번째로 끝나는 코루틴을 기다림
        )

        # 아직 끝나지 않은 태스크 취소
        for task in pending:
            task.cancel()
        
        if not view.request_accepted:
            return

        await initialize_prediction(self.bot, challenger_m, 상대, CHANNEL_ID, "주사위")

        await asyncio.gather(
            disable_buttons(),
            p.battle_event.wait()  # 이 작업은 event가 set될 때까지 대기
        )

        # 주사위 굴리기
        dice_results = {
            challenger: secrets.randbelow(100) + 1,
            상대.name: secrets.randbelow(100) + 1
        }

        game_point = {
            challenger : 포인트, 
            상대.name : 포인트
        }

        # ====================  [미션]  ====================
        # 일일미션 : 숫자야구 또는 주사위 대결 1회
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
        current_predict_season = cur_predict_seasonref.get()
        ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{interaction.user.name}/미션/일일미션/숫자야구 또는 주사위 대결 1회")
        mission_data = ref.get() or {}
        mission_bool = mission_data.get('완료',False)
        if not mission_bool:
            ref.update({"완료": True})
            print(f"{interaction.user.display_name}의 [숫자야구 또는 주사위 대결 1회] 미션 완료")

        # ====================  [미션]  ====================
            
        # ====================  [미션]  ====================
        # 일일미션 : 숫자야구 또는 주사위 대결 1회
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
        current_predict_season = cur_predict_seasonref.get()
        ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{상대.name}/미션/일일미션/숫자야구 또는 주사위 대결 1회")
        mission_data = ref.get() or {}
        mission_bool = mission_data.get('완료',False)
        if not mission_bool:
            ref.update({"완료": True})
            print(f"{상대.display_name}의 [숫자야구 또는 주사위 대결 1회] 미션 완료")

        # ====================  [미션]  ====================

        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
        current_predict_season = cur_predict_seasonref.get()

        ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{challenger}')
        ref2 = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{challenger}/베팅포인트')
        bettingPoint = ref2.get()
        ref.update({"베팅포인트" : bettingPoint + 포인트})

        ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{상대.name}')
        ref2 = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{상대.name}/베팅포인트')
        bettingPoint = ref2.get()
        ref.update({"베팅포인트" : bettingPoint + 포인트})

        diceview_embed = discord.Embed(title = "결과 확인", color = discord.Color.blue())
        diceview_embed.add_field(name = "", value = "주사위 결과를 확인하세요! 🎲", inline=False)
        diceview_embed.add_field(name = f"{challenger}", value = f"{game_point[challenger]}포인트", inline=True)
        diceview_embed.add_field(name = f"{상대}", value = f"{game_point[상대.name]}포인트", inline=True)

        thread = await interaction.channel.create_thread(
            name=f"{challenger_m.display_name} vs {상대.display_name} 주사위 대결",
            type=discord.ChannelType.public_thread
        )
        tts_channel = self.bot.get_channel(int(CHANNEL_ID)) #tts 채널  
        dice_view = DiceRevealView(challenger_m, 상대, dice_results, game_point,tts_channel)
        dice_view.message = await thread.send(content = "", view = dice_view, embed = diceview_embed)
        await dice_view.start_timer()

    @app_commands.command(name="경고", description="서버 멤버에게 경고를 부여합니다.")
    async def warn(self, interaction: discord.Interaction):
        # 경고 처리 로직
        allowed_role_name = "1등 ✨"
        #allowed_role_name = "관리자"
        # 사용자의 역할 확인
        user_roles = [role.name for role in interaction.user.roles]
        if allowed_role_name in user_roles:
            view = WarnCommandView(self.bot)
            await view.populate_members(interaction.guild)
            await interaction.response.send_message("경고할 멤버를 선택하세요.", view=view, ephemeral=True)
        else:
            await interaction.response.send_message("경고는 1등만 부여할 수 있습니다.")
    
    @app_commands.command(name="상점", description="다양한 아이템을 구매합니다.")
    async def item_shop(self, interaction: discord.Interaction):
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
        current_predict_season = cur_predict_seasonref.get()
        point_ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{interaction.user.name}')
        predict_data = point_ref.get()
        point = predict_data["포인트"]
        bettingPoint = predict_data["베팅포인트"]

        ref_tc = db.reference(f'무기/아이템/{interaction.user.name}')
        tc_data = ref_tc.get()
        TC = tc_data.get('탑코인', 0)

        shop_embed = discord.Embed(title = '구매할 아이템을 선택하세요', color = 0xfffff)
        shop_embed.add_field(name = f'{interaction.user.name}의 현재 포인트', value = f'**{point - bettingPoint}P** (베팅포인트 **{bettingPoint}P** 제외)', inline = False)
        shop_embed.add_field(name = f'{interaction.user.name}의 현재 탑코인', value = f'**{TC}TC**', inline = False)
        view = ItemBuyView()
        await interaction.response.send_message(embed = shop_embed, view = view, ephemeral = True)

    @app_commands.command(name="숫자야구",description="포인트를 걸고 숫자야구 게임을 진행합니다. 하루에 한번만 가능합니다.")
    @app_commands.describe(상대 = "대결할 상대를 고르세요", 포인트 = "기본 베팅으로 걸 포인트를 입력하세요. (100포인트 이상)")
    async def 숫자야구(self, interaction: discord.Interaction, 상대:discord.Member, 포인트: int = 100):
        challenger = interaction.user.name
        challenger_m = interaction.user
        if 상대.name == challenger:
            warnembed = discord.Embed(title="실패",color = discord.Color.red())
            warnembed.add_field(name="",value="자기 자신에게 도전할 수 없습니다! ❌")
            await interaction.response.send_message(embed = warnembed)
            return

        battle_ref = db.reference("승부예측/대결진행여부")
        is_battle = battle_ref.get()

        if is_battle:
            warnembed = discord.Embed(title="실패",color = discord.Color.red())
            warnembed.add_field(name="",value="다른 대결이 진행중입니다! ❌")
            await interaction.response.send_message(embed = warnembed)
            return
        
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
        current_predict_season = cur_predict_seasonref.get()

        battleref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{challenger}")
        battle_data = battleref.get()
        battled = battle_data.get("숫자야구배틀여부",False)

        if battled:
            item_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{challenger}/아이템")
            item_data = item_ref.get() or {} 
            battle_refresh = item_data.get("숫자야구대결기회 추가", 0)
            if battle_refresh:
                userembed = discord.Embed(title=f"알림", color=discord.Color.light_gray())
                userembed.add_field(name="",value=f"{challenger_m.display_name}님이 아이템을 사용하여 숫자야구 대결을 추가로 신청했습니다!", inline=False)
                channel = interaction.client.get_channel(int(CHANNEL_ID))
                await channel.send(embed=userembed)
                battle_ref.set(True)
            else:
                warnembed = discord.Embed(title="실패",color = discord.Color.red())
                warnembed.add_field(name="",value="하루에 한번만 대결 신청할 수 있습니다! ❌")
                await interaction.response.send_message("",embed = warnembed)
                return
        
        ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{challenger}')
        originr = ref.get()
        point = originr["포인트"]
        bettingPoint = originr["베팅포인트"]
        real_point = point - bettingPoint

        if 포인트 < 100:
            warnembed = discord.Embed(title="실패",color = discord.Color.red())
            warnembed.add_field(name="",value=f"100포인트 미만으로 베팅할 순 없습니다! ❌")
            await interaction.response.send_message("",embed = warnembed,ephemeral=True)
            return
        
        if 포인트 > real_point:
            warnembed = discord.Embed(title="실패",color = discord.Color.red())
            warnembed.add_field(name="",value=f"{challenger}님의 포인트가 {포인트}포인트 미만입니다! ❌")
            await interaction.response.send_message("",embed = warnembed,ephemeral=True)
            return
        
        ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{상대.name}')
        originr = ref.get()
        point = originr["포인트"]
        bettingPoint = originr["베팅포인트"]
        real_point = point - bettingPoint

        if real_point < 100:
            warnembed = discord.Embed(title="실패",color = discord.Color.red())
            warnembed.add_field(name="",value=f"{상대.name}님의 포인트가 100포인트 미만입니다! ❌")
            await interaction.response.send_message("",embed = warnembed)
            return

        # 대결 요청
        view = DuelRequestView(challenger, 상대, 포인트)
        battleembed = discord.Embed(title="대결 요청!", color = discord.Color.blue())
        battleembed.add_field(name="", value=f"{상대.mention}, {challenger_m.mention}의 숫자야구 대결 요청! 수락하시겠습니까?\n[걸린 포인트 : {포인트}포인트]")
        # 메시지 전송
        await interaction.response.send_message(content=상대.mention, view=view, embed=battleembed)
        battle_ref.set(True)

        # 전송된 메시지 객체 가져오기
        view.message = await interaction.original_response()

        done, pending = await asyncio.wait(
            [
                asyncio.create_task(view.start_timer()),
                asyncio.create_task(view.event.wait())
            ],
            return_when=asyncio.FIRST_COMPLETED  # 첫 번째로 끝나는 코루틴을 기다림
        )

        # 아직 끝나지 않은 태스크 취소
        for task in pending:
            task.cancel()
        
        if not view.request_accepted:
            return

        await initialize_prediction(self.bot, challenger_m, 상대, CHANNEL_ID, "숫자야구")

        await asyncio.gather(
            disable_buttons(),
            p.battle_event.wait()  # 이 작업은 event가 set될 때까지 대기
        )
        game_point = {
            challenger : 포인트, 
            상대.name : 포인트
        }

        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
        current_predict_season = cur_predict_seasonref.get()

        ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{challenger}')
        ref2 = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{challenger}/베팅포인트')
        bettingPoint = ref2.get()
        ref.update({"베팅포인트" : bettingPoint + 포인트})

        ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{상대.name}')
        ref2 = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{상대.name}/베팅포인트')
        bettingPoint = ref2.get()
        ref.update({"베팅포인트" : bettingPoint + 포인트})

        # ====================  [미션]  ====================
        # 일일미션 : 숫자야구 또는 주사위 대결 1회
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
        current_predict_season = cur_predict_seasonref.get()
        ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{interaction.user.name}/미션/일일미션/숫자야구 또는 주사위 대결 1회")
        mission_data = ref.get() or {}
        mission_bool = mission_data.get('완료',False)
        if not mission_bool:
            ref.update({"완료": True})
            print(f"{interaction.user.display_name}의 [숫자야구 또는 주사위 대결 1회] 미션 완료")

        # ====================  [미션]  ====================
            
        # ====================  [미션]  ====================
        # 일일미션 : 숫자야구 또는 주사위 대결 1회
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
        current_predict_season = cur_predict_seasonref.get()
        ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{상대.name}/미션/일일미션/숫자야구 또는 주사위 대결 1회")
        mission_data = ref.get() or {}
        mission_bool = mission_data.get('완료',False)
        if not mission_bool:
            ref.update({"완료": True})
            print(f"{상대.display_name}의 [숫자야구 또는 주사위 대결 1회] 미션 완료")

        # ====================  [미션]  ====================
            
        class GuessModal(discord.ui.Modal, title="숫자 맞추기"):
            def __init__(self, game, player):
                super().__init__()
                self.game = game
                self.player = player
                self.answer = discord.ui.TextInput(
                    label="세 자리 숫자를 입력하세요 (예: 123)",
                    style=discord.TextStyle.short,
                    max_length=3
                )
                self.add_item(self.answer)

            async def on_submit(self, interaction: discord.Interaction):
                await interaction.response.defer()
                guess = self.answer.value.strip()
                if not guess.isdigit() or len(set(guess)) != 3 or len(guess) != 3:
                    await interaction.followup.send("🚫 **서로 다른 3개의 숫자로 입력해주세요!**", ephemeral=True)
                    return

                guess = list(map(int, guess))
                result, end = await self.game.check_guess(self.player, guess)

                await interaction.followup.send(embed=result)
                if not end:
                    await self.game.next_turn()  # 턴 넘기기
                if end:
                    item_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{challenger}/아이템")
                    item_data = item_ref.get() or {} 
                    battle_refresh = item_data.get("숫자야구대결기회 추가", 0)
                    if battle_refresh and battled:
                        item_ref.update({"숫자야구대결기회 추가": battle_refresh - 1})

        class BaseballGameView(discord.ui.View):
            def __init__(self, challenger, opponent, game_point):
                super().__init__(timeout = None)
                self.players = [challenger, opponent]
                self.numbers = {challenger.name: self.generate_numbers(), opponent.name: self.generate_numbers()}
                self.turn = 1  # 상대(1) → 도전자(0)
                self.message = None
                self.turn_timer = None
                self.game_point = game_point
                self.initial_game_point = game_point
                self.challenger = challenger.name
                self.opponent = opponent.name
                self.challenger_m = challenger
                self.opponent_m = opponent
                self.channel = None
                self.point_limited = False
                self.success = {challenger.name: False, opponent.name: False}

            def generate_numbers(self):
                return random.sample(range(10), 3)

            async def start_game(self, channel):
                """게임 시작 메시지를 보내고, 상대부터 시작"""
                embed = discord.Embed(title="⚾ 숫자야구 대결 시작!", color=discord.Color.blue())
                embed.add_field(name="턴", value=f"🎯 {self.players[self.turn].mention}님의 턴입니다!", inline=False)
                embed.add_field(name = f"{self.challenger}", value = f"{self.game_point[self.challenger]}포인트",inline=True)
                embed.add_field(name = f"{self.opponent}", value = f"{self.game_point[self.opponent]}포인트",inline=True)
                self.message = await channel.send(embed=embed, view=self)
                self.channel = channel
                await self.start_turn_timer()

            async def start_turn_timer(self):
                """2분 타이머 실행, 시간이 지나면 턴 자동 변경"""
                if self.turn_timer:
                    self.turn_timer.cancel()
                self.turn_timer = asyncio.create_task(self.turn_timeout())

            async def turn_timeout(self):
                try:
                    await asyncio.sleep(120)  # 2분 대기
                    if self.turn_timer.done():  # 취소되었는지 확인
                        return

                    if self.turn == 0:
                        if self.success[self.opponent]: # 상대가 정답을 맞춘 상태에서 턴이 변경될 경우
                            baseball_winner = self.opponent_m
                            result = False
                            await self.announce_winner(baseball_winner,result)
                        else:
                            embed = discord.Embed(title=f"턴 변경!", color=discord.Color.light_gray())
                            embed.add_field(name = "", value = "2분 동안 입력이 없어 턴이 변경되었습니다.", inline = False)
                            await self.channel.send(embed=embed)
                            await self.next_turn(timeout=True)         
                except asyncio.CancelledError:
                    pass

            async def next_turn(self, timeout=False):
                """턴을 변경하고 메시지를 업데이트"""
                self.turn = (self.turn + 1) % 2
                player = self.players[self.turn]
                
                embed = discord.Embed(title="⚾ 숫자야구 진행 중!", color=discord.Color.green())
                embed.add_field(name="턴", value=f"🎯 {player.mention}님의 턴입니다!", inline=False)
                if timeout:
                    embed.add_field(name="⏳ 턴 자동 변경!", value="2분 동안 입력이 없어 턴이 변경되었습니다.", inline=False)
                embed.add_field(name = f"{self.challenger}", value = f"{self.game_point[self.challenger]}포인트",inline=True)
                embed.add_field(name = f"{self.opponent}", value = f"{self.game_point[self.opponent]}포인트",inline=True)

                self.clear_items()
                await self.add_new_buttons()

                await self.message.edit(embed=embed, view=self)
                await self.start_turn_timer()

            async def check_guess(self, player, guess):
                """입력된 숫자를 비교하고 결과를 반환"""
                opponent = self.players[(self.players.index(player) + 1) % 2]  # 상대 플레이어
                answer = self.numbers[opponent.name]
                end = False

                strikes = sum(1 for i in range(3) if guess[i] == answer[i])
                balls = sum(1 for i in range(3) if guess[i] in answer) - strikes
                
                player = self.players[self.turn]
                if player.name == self.challenger:
                    embed = discord.Embed(title=f"{player}의 숫자 맞추기 결과", color=discord.Color.red())
                else:
                    embed = discord.Embed(title=f"{player}의 숫자 맞추기 결과", color=discord.Color.blue())
                embed.add_field(name="입력값", value="".join(map(str, guess)), inline=False)
                
                if strikes == 3:
                    embed.color = discord.Color.gold()
                    embed.add_field(name="🏆 정답!", value=f"{player.mention}님이 **정답을 맞췄습니다!** 🎉")

                    if player.name == self.challenger: # 게임 종료
                        end = True
                        if self.success[self.opponent]: # 상대가 정답을 맞춘 상태라면 무승부!
                            baseball_winner = None
                            result = None
                        else: # 못맞췄다면 도전자 승리!
                            baseball_winner = self.challenger_m
                            result = True

                        await self.announce_winner(baseball_winner,result)

                    else: # 상대편이 맞추는 지 기다림
                        end = False
                        self.success[self.opponent] = True # 플레이어 정답!
                    
                else:
                    result = f"{strikes} STRIKE, {balls} BALL" if strikes or balls else "⚾ OUT!"
                    embed.add_field(name="결과", value=result, inline=False)
                    if player.name == self.challenger:
                        if self.success[self.opponent]: #상대가 정답을 맞췄다면 상대 승리!
                            end = True
                            baseball_winner = self.opponent_m
                            result = False

                            await self.announce_winner(baseball_winner,result)
                        else:
                            end = False

                return embed, end

            async def announce_winner(self, baseball_winner, result):
                cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                current_predict_season = cur_predict_seasonref.get()

                battleref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{self.challenger}/숫자야구배틀여부")
                battleref.set(True)

                self.turn_timer.cancel() # 턴 타이머 종료
                end_embed = discord.Embed(title="⚾ 숫자야구 종료!", color=discord.Color.green())
                end_embed.add_field(name = f"{self.challenger}", value = f"{self.game_point[self.challenger]}포인트",inline=True)
                end_embed.add_field(name = f"{self.opponent}", value = f"{self.game_point[self.opponent]}포인트",inline=True)

                for button in self.children:  # 모든 버튼에 대해
                    button.disabled = True

                await self.message.edit(embed=end_embed, view=self)
                
                battle_ref = db.reference("승부예측/대결진행여부")
                battle_ref.set(False)

                if baseball_winner:
                    userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                    userembed.add_field(name="게임 종료", value=f"숫자야구 대결이 종료되었습니다!\n {baseball_winner.mention}의 승리!")

                    winners = p.votes['배틀']['prediction']['win'] if result else p.votes['배틀']['prediction']['lose']
                    losers = p.votes['배틀']['prediction']['lose'] if result else p.votes['배틀']['prediction']['win']
                    winnerNum = len(winners)
                    loserNum = len(losers)

                    BonusRate = 0 if winnerNum == 0 else round((((winnerNum + loserNum) / winnerNum) - 1) * 0.1, 2) + 1 # 0.1배 배율 적용
                    if BonusRate > 0:
                        BonusRate += 0.1

                    BonusRate = round(BonusRate,2)

                    userembed.add_field(
                        name="", 
                        value=f"베팅 배율: {BonusRate}배" if BonusRate == 0 else 
                        f"베팅 배율: {BonusRate}배!((({winnerNum + loserNum}/{winnerNum} - 1) x 0.1 + 1) + 0.1)", 
                        inline=False
                    )

                    current_datetime = datetime.now() # 데이터베이스에 남길 현재 시각 기록
                    current_date = current_datetime.strftime("%Y-%m-%d")
                    current_time = current_datetime.strftime("%H:%M:%S")

                    cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                    current_predict_season = cur_predict_seasonref.get()

                    for winner in winners:
                        point_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner['name'].name}")
                        predict_data = point_ref.get()
                        point = predict_data["포인트"]
                        bettingPoint = predict_data["베팅포인트"]

                        # 예측 내역 업데이트
                        point_ref.update({
                            "포인트": point,
                            "총 예측 횟수": predict_data["총 예측 횟수"] + 1,
                            "적중 횟수": predict_data["적중 횟수"] + 1,
                            "적중률": f"{round((((predict_data['적중 횟수'] + 1) * 100) / (predict_data['총 예측 횟수'] + 1)), 2)}%",
                            "연승": predict_data["연승"] + 1,
                            "연패": 0,
                            "베팅포인트": bettingPoint - winner["points"]
                        })


                        # ====================  [미션]  ====================
                        # 일일미션 : 승부예측 1회 적중
                        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                        current_predict_season = cur_predict_seasonref.get()
                        ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner['name'].name}/미션/일일미션/승부예측 1회 적중")
                        mission_data = ref.get() or {}
                        mission_bool = mission_data.get('완료', False)
                        if not mission_bool:
                            ref.update({"완료": True})
                            print(f"{winner['name'].display_name}의 [승부예측 1회 적중] 미션 완료")

                        # ====================  [미션]  ====================

                        winner_total_point = sum(winner['points'] for winner in winners)
                        loser_total_point = sum(loser['points'] for loser in losers)
                        remain_loser_total_point = loser_total_point

                        betted_rate = round(winner['points'] / winner_total_point, 3) if winner_total_point else 0
                        get_bet = round(betted_rate * loser_total_point)
                        get_bet_limit = round(BonusRate * winner['points'])
                        if get_bet >= get_bet_limit:
                            get_bet = get_bet_limit

                        remain_loser_total_point -= get_bet
                        streak_text = f"{predict_data['연승'] + 1}연속 적중을 이루어내며 " if predict_data['연승'] + 1 > 1 else ""

                        bonus_rate = calculate_bonus_rate(predict_data["연승"] + 1)
                        add_points = 10 + round(winner['points'] * (BonusRate + bonus_rate)) + get_bet if predict_data["연승"] + 1 > 1 else 10 + round(winner["points"] * BonusRate) + get_bet
                        if predict_data['연승'] + 1 > 1:
                            userembed.add_field(name="", value=f"{winner['name'].display_name}님이 {streak_text}{add_points}(베팅 보너스 + {round(winner['points'] * (BonusRate + bonus_rate))} + {get_bet})(연속적중 보너스 {bonus_rate}배!) 점수를 획득하셨습니다! (베팅 포인트: {winner['points']})", inline=False)
                        else:
                            userembed.add_field(name="", value=f"{winner['name'].display_name}님이 {streak_text}{add_points}(베팅 보너스 + {round(winner['points'] * BonusRate)} + {get_bet}) 점수를 획득하셨습니다! (베팅 포인트: {winner['points']})", inline=False)   
                        # 예측 내역 변동 데이터
                        change_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트변동로그/{current_date}/{winner['name'].name}")
                        change_ref.push({
                            "시간": current_time,
                            "포인트": point + add_points - winner['points'],
                            "포인트 변동": add_points - winner['points'],
                            "사유": "숫자야구 승부예측"
                        })
                        point_ref.update({"포인트": point + add_points - winner['points']})

                    for loser in losers:
                        point_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{loser['name'].name}")
                        predict_data = point_ref.get()
                        point = predict_data["포인트"]
                        bettingPoint = predict_data["베팅포인트"]
                        
                        loser_total_point = sum(loser['points'] for loser in losers)
                        remain_loser_total_point = loser_total_point
                        # 예측 내역 업데이트
                        point_ref.update({
                            "포인트": point,
                            "총 예측 횟수": predict_data["총 예측 횟수"] + 1,
                            "적중 횟수": predict_data["적중 횟수"],
                            "적중률": f"{round((((predict_data['적중 횟수']) * 100) / (predict_data['총 예측 횟수'] + 1)), 2)}%",
                            "연승": 0,
                            "연패": predict_data["연패"] + 1,
                            "베팅포인트": bettingPoint - loser["points"],
                        })
                        
                        # 남은 포인트를 배팅한 비율에 따라 환급받음 (30%)
                        betted_rate = round(loser['points'] / loser_total_point, 3) if loser_total_point else 0
                        get_bet = round(betted_rate * remain_loser_total_point * 0.3)
                        userembed.add_field(
                            name="",
                            value=f"{loser['name'].display_name}님이 예측에 실패하였습니다! " if loser['points'] == 0 else 
                            f"{loser['name'].display_name}님이 예측에 실패하여 베팅포인트를 잃었습니다! (베팅 포인트:-{loser['points']}) (환급 포인트: {get_bet})",
                            inline=False
                        )
                        # 예측 내역 변동 데이터
                        change_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트변동로그/{current_date}/{loser['name'].name}")
                        if point + get_bet < loser['points']:
                            point_ref.update({"포인트": 0})
                            change_ref.push({
                                "시간": current_time,
                                "포인트": 0,
                                "포인트 변동": -point,
                                "사유": "숫자야구 승부예측"
                            })
                            
                        else:
                            point_ref.update({"포인트": point + get_bet - loser['points']})
                            change_ref.push({
                                "시간": current_time,
                                "포인트": point + get_bet - loser['points'],
                                "포인트 변동": get_bet - loser['points'],
                                "사유": "숫자야구 승부예측"
                            })

                    
                    channel = interaction.client.get_channel(int(CHANNEL_ID)) #tts 채널
                    await channel.send(embed = userembed)
                    p.votes['배틀']['prediction']['win'].clear()
                    p.votes['배틀']['prediction']['lose'].clear()
                    
                    cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
                    current_predict_season = cur_predict_seasonref.get()

                    battleref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{p.votes['배틀']['name']['challenger']}")
                    battleref.update({"배틀여부" : True})

                    userembed = discord.Embed(title="승부 베팅 결과", color=discord.Color.blue())
                    if result: # challenger가 승리
                        remained_point = 0 # 환급 포인트
                        challenger_point = self.game_point[self.challenger]
                        original_opponent_point = self.game_point[self.opponent]
                        opponent_point = self.game_point[self.opponent]
                        
                        if opponent_point > challenger_point:
                            get_point = challenger_point * 2 # 받을 포인트
                            remained_point += opponent_point - challenger_point # 환급 포인트
                        else:
                            get_point = challenger_point + opponent_point

                        userembed.add_field(
                        name="",
                        value=f"{self.opponent_m.mention}님이 승부에서 패배하여 베팅포인트를 잃었습니다! (베팅 포인트:-{original_opponent_point}) (환급 포인트: {remained_point})",
                        inline=False
                        )
                        userembed.add_field(
                        name="",
                        value=f"{self.challenger_m.mention}님이 승부에서 승리하여 {get_point}포인트를 획득하셨습니다! (베팅 포인트: {challenger_point})",
                        inline=False
                        )
                        
                        point_ref1 = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{self.opponent}')
                        point_ref2 = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{self.challenger}')
                        point_data1 = point_ref1.get()
                        point1 = point_data1.get("포인트",0)
                        bettingpoint1 = point_data1.get("베팅포인트",0)
                        point_data2 = point_ref2.get()
                        point2 = point_data2.get("포인트",0)
                        bettingpoint2 = point_data2.get("베팅포인트",0)
                        point_ref1.update({"포인트": point1 - original_opponent_point + remained_point})
                        point_ref1.update({"베팅포인트": bettingpoint1 - original_opponent_point})
                        point_ref2.update({"포인트": point2 + get_point - challenger_point})
                        point_ref2.update({"베팅포인트": bettingpoint2 - challenger_point})

                        current_datetime = datetime.now() # 데이터베이스에 남길 현재 시각 기록
                        current_date = current_datetime.strftime("%Y-%m-%d")
                        current_time = current_datetime.strftime("%H:%M:%S")
                        change_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트변동로그/{current_date}/{self.opponent}")
                        change_ref.push({
                            "시간": current_time,
                            "포인트": point1 - original_opponent_point + remained_point,
                            "포인트 변동": remained_point - original_opponent_point,
                            "사유": "숫자야구 대결",
                        })

                        change_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트변동로그/{current_date}/{self.challenger}")
                        change_ref.push({
                            "시간": current_time,
                            "포인트": point2 + get_point - challenger_point,
                            "포인트 변동": get_point - challenger_point,
                            "사유": "숫자야구 대결",
                        })

                    else:
                        remained_point = 0 # 환급 포인트
                        challenger_point = self.game_point[self.challenger]
                        original_challenger_point = self.game_point[self.challenger]
                        opponent_point = self.game_point[self.opponent]

                        if challenger_point > opponent_point:
                            get_point = opponent_point * 2 # 받을 포인트
                            remained_point += challenger_point - opponent_point # 환급 포인트
                        else:
                            get_point = opponent_point + challenger_point # 받을 포인트

                        userembed.add_field(
                        name="",
                        value=f"{self.challenger_m.mention}님이 승부에서 패배하여 베팅포인트를 잃었습니다! (베팅 포인트:-{original_challenger_point}) (환급 포인트: {remained_point})",
                        inline=False
                        )
                        userembed.add_field(
                        name="",
                        value=f"{self.opponent_m.mention}님이 승부에서 승리하여 {get_point}포인트를 획득하셨습니다! (베팅 포인트: {opponent_point})",
                        inline=False
                        )
                        point_ref1 = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{self.opponent}')
                        point_ref2 = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{self.challenger}')
                        point_data1 = point_ref1.get()
                        point1 = point_data1.get("포인트",0)
                        bettingpoint1 = point_data1.get("베팅포인트",0)
                        point_data2 = point_ref2.get()
                        bettingpoint2 = point_data2.get("베팅포인트",0)
                        point2 = point_data2.get("포인트",0)
                        point_ref1.update({"포인트": point1 + get_point - opponent_point})
                        point_ref1.update({"베팅포인트": bettingpoint1 - opponent_point})
                        point_ref2.update({"포인트": point2 - original_challenger_point + remained_point})
                        point_ref2.update({"베팅포인트": bettingpoint2 - original_challenger_point})
                        
                        current_datetime = datetime.now() # 데이터베이스에 남길 현재 시각 기록
                        current_date = current_datetime.strftime("%Y-%m-%d")
                        current_time = current_datetime.strftime("%H:%M:%S")
                        change_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트변동로그/{current_date}/{self.opponent}")
                        change_ref.push({
                            "시간": current_time,
                            "포인트": point1 + get_point - opponent_point,
                            "포인트 변동": get_point - opponent_point,
                            "사유": "숫자야구 대결",
                        })

                        change_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트변동로그/{current_date}/{self.challenger}")
                        change_ref.push({
                            "시간": current_time,
                            "포인트": point2 - original_challenger_point + remained_point,
                            "포인트 변동":  remained_point - original_challenger_point,
                            "사유": "숫자야구 대결",
                        })
                    channel = interaction.client.get_channel(int(CHANNEL_ID)) #tts 채널
                    await channel.send(embed = userembed)

                    p.votes['배틀']['name']['challenger'] = ""
                    p.votes['배틀']['name']['상대'] = ""
                    self.stop()
                else:
                    userembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
                    userembed.add_field(name="게임 종료", value=f"배틀이 종료되었습니다!\n무승부!🤝\n")
                    channel = interaction.client.get_channel(int(CHANNEL_ID)) #tts 채널
                    await channel.send(embed=userembed)

                    cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
                    current_predict_season = cur_predict_seasonref.get()

                    ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{self.challenger}')
                    originr = ref.get()
                    bettingPoint = originr["베팅포인트"]
                    bettingPoint -= self.game_point[self.challenger]
                    ref.update({"베팅포인트": bettingPoint})

                    ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{self.opponent}')
                    originr = ref.get()
                    bettingPoint = originr["베팅포인트"]
                    bettingPoint -= self.game_point[self.opponent]
                    ref.update({"베팅포인트": bettingPoint})

                    winners = p.votes['배틀']['prediction']['win']
                    losers = p.votes['배틀']['prediction']['lose']
                    for winner in winners:
                        ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner['name'].name}")
                        originr = ref.get()
                        bettingPoint = originr["베팅포인트"]
                        bettingPoint -= winner['points']
                        ref.update({"베팅포인트": bettingPoint})

                    for loser in losers:
                        ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{loser['name'].name}")
                        originr = ref.get()
                        bettingPoint = originr["베팅포인트"]
                        bettingPoint -= loser['points']
                        ref.update({"베팅포인트": bettingPoint})

                    p.votes['배틀']['prediction']['win'].clear()
                    p.votes['배틀']['prediction']['lose'].clear()
                    cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
                    current_predict_season = cur_predict_seasonref.get()

                    battleref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{p.votes['배틀']['name']['challenger']}")
                    battleref.update({"배틀여부" : True})
                    
                    self.game_point.clear()
                    p.votes['배틀']['name']['challenger'] = ""
                    p.votes['배틀']['name']['상대'] = ""
                    self.stop()  # 게임 종료

            async def update_game_point(self, user, bet_amount):
                # 게임 포인트를 외부에서 수정
                if user.name in self.game_point:
                    self.game_point[user.name] += bet_amount

            async def add_new_buttons(self):
                """새로운 버튼을 추가하는 메서드"""
                self.add_item(self.check_numbers)
                self.add_item(self.guess_numbers)
                self.add_item(self.bet)

            @discord.ui.button(label="내 숫자 확인", style=discord.ButtonStyle.gray)
            async def check_numbers(self, interaction: discord.Interaction, button: discord.ui.Button):
                """자신의 숫자를 확인하는 버튼"""
                if interaction.user.name not in self.numbers:
                    await interaction.response.send_message("🚫 당신은 이 게임의 참가자가 아닙니다!", ephemeral=True)
                    return
                
                num_str = " ".join(map(str, self.numbers[interaction.user.name]))
                embed = discord.Embed(title="🔢 내 숫자", description=f"🎲 당신의 숫자는 `{num_str}` 입니다!", color=discord.Color.blue())
                await interaction.response.send_message(embed=embed, ephemeral=True)

            @discord.ui.button(label="숫자 맞추기", style=discord.ButtonStyle.success)
            async def guess_numbers(self, interaction: discord.Interaction, button: discord.ui.Button):
                """모달을 열어 숫자 입력 받기"""
                if interaction.user != self.players[self.turn]:
                    await interaction.response.send_message("🚫 **지금은 상대의 턴입니다!**", ephemeral=True)
                    return
                
                if not self.point_limited: # 포인트 제한이 없다면
                    basePoint = round(self.initial_game_point.get(interaction.user.name, 0) * 0.1) # 베팅 포인트
                    
                    cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                    current_predict_season = cur_predict_seasonref.get()
                    point_ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{interaction.user.name}')
                    predict_data = point_ref.get()
                    point = predict_data["포인트"]
                    bettingPoint = predict_data["베팅포인트"]
                    real_point = point - (bettingPoint + basePoint)

                    if real_point < 0:
                        self.point_limited = True
                        userembed = discord.Embed(title = "베팅 불가!",color = discord.Color.red())
                        userembed.add_field(name="",value="{interaction.user.mention}님의 포인트가 부족하여 더 이상 서로 베팅하지 않습니다!")
                        await self.channel.send(embed = userembed)
                    else:
                        point_ref.update({"베팅포인트": bettingPoint + basePoint})
                        self.game_point[interaction.user.name] += basePoint
                await interaction.response.send_modal(GuessModal(self, interaction.user))

            @discord.ui.button(label="베팅", style=discord.ButtonStyle.primary)
            async def bet(self, interaction: discord.Interaction, button: discord.ui.Button):
                if interaction.user.name not in [self.challenger, self.opponent]:
                    userembed = discord.Embed(title = "베팅 불가!",color = discord.Color.red())
                    userembed.add_field(name="",value="참가자만 베팅할 수 있습니다!")
                    await interaction.response.send_message(content = "", embed = userembed, ephemeral = True)
                    return

                # 모달 생성
                modal = BettingModal(user=interaction.user, challenger = self.challenger, opponent = self.opponent, game_point = self.game_point, game = self, message = self.message, what = "숫자야구")
                await interaction.response.send_modal(modal)

        thread = await interaction.channel.create_thread(
            name=f"{challenger_m.display_name} vs {상대.display_name} 숫자야구 대결",
            type=discord.ChannelType.public_thread
        )
        await BaseballGameView(challenger_m, 상대, game_point).start_game(thread)
    
    @app_commands.command(name="명령어",description="명령어 목록을 보여줍니다.")
    async def 명령어(self, interaction: discord.Interaction):
        exclude = {"온오프", "정상화", "재부팅", "익명온오프", "패배", "테스트", "열람포인트초기화", "공지", "베팅포인트초기화", "아이템지급", "아이템전체지급", "일일미션추가", "시즌미션추가", "미션삭제", "승리", "패배", "포인트지급"}
        commands_list = await self.bot.tree.fetch_commands(guild=discord.Object(id=298064707460268032))  # 동기화된 모든 명령어 가져오기
        commands_list = [cmd for cmd in commands_list if cmd.name not in exclude]
        commands_list.sort(key=lambda x: x.name)

        # 페이지 구분 (한 페이지에 10개씩 표시한다고 가정)
        page_size = 10
        total_pages = (len(commands_list) // page_size) + (1 if len(commands_list) % page_size != 0 else 0)
        
        # 첫 번째 페이지의 명령어 목록을 임베드로 생성
        current_page = 0
        embed = create_embed(commands_list, current_page, page_size)
        
        # 버튼을 만들어 페이지를 넘길 수 있게 처리
        prev_button = discord.ui.Button(label="이전 페이지", style=discord.ButtonStyle.primary, disabled=True)
        next_button = discord.ui.Button(label="다음 페이지", style=discord.ButtonStyle.primary)

        # 버튼 클릭 이벤트 정의
        async def prev_button_callback(interaction: discord.Interaction):
            nonlocal current_page
            if current_page > 0:
                current_page -= 1
                embed = create_embed(commands_list, current_page, page_size)
                next_button.disabled = False
                if current_page == 0:
                    prev_button.disabled = True
                view.clear_items()
                view.add_item(prev_button)
                view.add_item(next_button)
                await interaction.response.edit_message(embed=embed, view=view)

        async def next_button_callback(interaction: discord.Interaction):
            nonlocal current_page
            if current_page < total_pages - 1:
                current_page += 1
                embed = create_embed(commands_list, current_page, page_size)
                prev_button.disabled = False
                if current_page == total_pages - 1:
                    next_button.disabled = True
                view.clear_items()
                view.add_item(prev_button)
                view.add_item(next_button)
                await interaction.response.edit_message(embed=embed, view=view)

        prev_button.callback = prev_button_callback
        next_button.callback = next_button_callback
        
        # View에 버튼을 추가
        view = discord.ui.View()
        view.add_item(prev_button)
        view.add_item(next_button)

        # 처음 명령어 목록을 보여주는 메시지 전송
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="포인트지급", description="포인트를 지급합니다. (관리자 전용)")
    async def give_point(self, interaction: discord.Interaction, user: discord.Member, point: int):
        if interaction.user.name == "toe_kyung":
            cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
            current_predict_season = cur_predict_seasonref.get()
            point_ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{user.name}')
            predict_data = point_ref.get()
            original_point = predict_data["포인트"]

            point_ref.update({"포인트": original_point + point})
            await interaction.response.send_message(f"{user.mention}에게 {point}포인트가 지급되었습니다!",)
        else:
            await interaction.response.send_message("권한이 없습니다",ephemeral=True)

    @app_commands.command(name="완전익명화", description="다음 승부예측에 투표인원, 포인트, 메세지가 전부 나오지 않는 완전한 익명화를 적용합니다. 완전 익명화 아이템을 구매한 후 사용 가능합니다.")
    @app_commands.choices(이름=[
        Choice(name='지모', value='지모'),
        Choice(name='Melon', value='Melon'),
    ])
    async def complete_anonymous(self, interaction: discord.Interaction, 이름: str):
        nickname = interaction.user

        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
        current_predict_season = cur_predict_seasonref.get()

        refitem = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname.name}/아이템')
        itemr = refitem.get()

        item_num = itemr.get("완전 익명화", 0)

        if item_num > 0:
            complete_anonymref = db.reference(f"승부예측/완전익명{이름}온오프")
            complete_anonymref.set(True) # 완전 익명 설정
            refitem.update({"완전 익명화": item_num - 1})
            userembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
            userembed.add_field(name="", value=f"{nickname.display_name}님이 아이템을 사용하여 {이름}의 다음 투표를 익명화하였습니다!", inline=False)
            await interaction.channel.send(embed=userembed)
            checkembed = discord.Embed(title="성공",color = discord.Color.blue())
            checkembed.add_field(name="",value=f"{이름}의 투표가 완전 익명화 되었습니다! 남은 아이템: {item_num - 1}개")
            await interaction.response.send_message(embed = checkembed, ephemeral=True)
        else:
            warnembed = discord.Embed(title="실패",color = discord.Color.red())
            warnembed.add_field(name="",value="아이템이 없습니다! ❌")
            await interaction.response.send_message(embed = warnembed,ephemeral=True)

    @app_commands.command(name="야추1등",description="현재 야추 족보가 가장 높은 플레이어를 보여줍니다.")
    async def best_yacht(self, interaction: discord.Interaction):
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
        current_predict_season = cur_predict_seasonref.get()

        refname = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트")
        name_data = refname.get()

        await interaction.response.defer()
        
        # 족보 우선순위 딕셔너리 (낮은 숫자가 높은 우선순위)
        hand_rankings = {
            "🎉 Yacht!": 0,
            "➡️ Large Straight!": 1,
            "🏠 Full House!": 2,
            "🔥 Four of a Kind!": 3,
            "🡒 Small Straight!": 4,
            "🎲 Chance!": 5
        }

        hand_bet_rate = {
            0: 50,
            1: 5,
            2: 3,
            3: 2,
            4: 1.5,
            5: 1
        }

        best_player = []  # 가장 높은 족보를 가진 플레이어
        best_hand_rank = float('inf')  # 초기값을 무한대로 설정
        best_total = -1  # 주사위 합계를 비교할 변수

        for nickname, point_data in name_data.items():
            refdice = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname}/야추")
            yacht = refdice.get() or {}

            yacht_hand = yacht.get("족보", "🎲 Chance!")  # 기본값은 Chance!
            rolls = yacht.get("결과", [])  # 플레이어의 주사위 값
            total = sum(rolls) if rolls else 0  # 주사위 총합 계산

            hand_rank = hand_rankings.get(yacht_hand.split(" (")[0], 5)  # 족보 랭킹 가져오기 (Chance는 따로 처리)

            # 1. 더 높은 족보를 찾으면 갱신
            if hand_rank < best_hand_rank:
                best_player = [nickname]
                best_hand_rank = hand_rank
                best_total = total
            # 2. 같은 족보라면 주사위 총합으로 비교
            elif hand_rank == best_hand_rank:
                if total > best_total:
                    best_player = [nickname]
                    best_total = total
                if total == best_total:
                    best_player.append(nickname)

        if len(best_player) == 1:
            point_message = f"{', '.join([f'**{winner}**' for winner in best_player])}에게 **{best_total * hand_bet_rate[best_hand_rank]}**포인트 지급 예정! 🎉"
        else:
            point_message = f"**{best_player[0]}**님에게 **{best_total * hand_bet_rate[best_hand_rank]}**포인트 지급 예정! 🎉"
        
        refdice = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{best_player[0]}/야추")
        yacht = refdice.get() or {}

        yacht_hand = yacht.get("족보", "🎲 Chance!")  # 기본값은 Chance!
        embed = discord.Embed(title="🎯 주사위 정산", color = 0x00ff00)
        embed.add_field(name="족보", value=f"**최고 족보: {yacht_hand}**(총합 : {best_total})", inline=False)
        embed.add_field(name="예상 결과", value=f"배율 : **{hand_bet_rate[best_hand_rank]}배**!\n{point_message}", inline=False)
        await interaction.followup.send(embed = embed)


    @app_commands.command(name="주사위1등",description="현재 주사위 숫자가 가장 높은 플레이어를 보여줍니다.")
    async def best_dice(self, interaction: discord.Interaction):
        await interaction.response.defer()
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
        current_predict_season = cur_predict_seasonref.get()

        refname = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트")
        name_data = refname.get()

        dice_nums = []
        for nickname, point_data in name_data.items():
            refdice = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname}/주사위")
            dice_nums.append((refdice.get(),nickname))

        max_dice_num = max(dice_nums, key=lambda x: x[0])[0]

        winners = [name for num, name in dice_nums if num == max_dice_num]

        if len(winners) == 1:
            point_message = f"{', '.join([f'**{winner}**' for winner in winners])}에게 **{max_dice_num}**포인트 지급 예정! 🎉"
        else:
            point_message = f"**{winners[0]}**님에게 **{max_dice_num}**포인트 지급 예정! 🎉"

        embed = discord.Embed(title="🎯 주사위 정산", color = 0x00ff00)
        embed.add_field(name="최고 숫자", value=f"오늘 굴린 주사위 중 가장 높은 숫자는 **{max_dice_num}**입니다!", inline=False)
        embed.add_field(name="예상 결과", value=point_message, inline=False)
        await interaction.followup.send(embed = embed)

    
    
    @app_commands.command(name="강화", description="보유한 무기를 강화합니다.")
    async def enhance(self, interaction: discord.Interaction):
        nickname = interaction.user.name
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
        current_predict_season = cur_predict_seasonref.get()

        ref_weapon = db.reference(f"무기/유저/{nickname}")
        weapon_data = ref_weapon.get() or {}
        ref_item = db.reference(f"무기/아이템/{nickname}")
        item_data = ref_item.get() or {}
        weapon_name = weapon_data.get("이름", "")

        if weapon_name == "":
            await interaction.response.send_message("무기가 없습니다! 먼저 무기를 생성하세요.", ephemeral=True)
            return

        weapon_enhanced = weapon_data.get("강화", 0)
        weapon_parts = item_data.get("강화재료", 0)

        weapon_embed = discord.Embed(title="무기 강화", color=0xff00ff)
        weapon_embed.add_field(name="무기 이름", value=f"{weapon_name} **(+{weapon_enhanced})**", inline=False)
        weapon_embed.add_field(name="내구도", value=f"{weapon_data.get('내구도', 0)}", inline=False)
        weapon_embed.add_field(name="공격력", value=f"{weapon_data.get('공격력', 0)}", inline=True)
        weapon_embed.add_field(name="스킬 증폭", value=f"{weapon_data.get('스킬 증폭', 0)}", inline=True)
        weapon_embed.add_field(name="방어력", value=f"{weapon_data.get('방어력', 0)}", inline=True)
        weapon_embed.add_field(name="스피드", value=f"{weapon_data.get('스피드', 0)}", inline=True)
        weapon_embed.add_field(name="명중", value=f"{weapon_data.get('명중', 0)}", inline=True)
        weapon_embed.add_field(name="치명타 확률", value=f"{weapon_data.get('치명타 확률', 0) * 100:.1f}%", inline=True)
        weapon_embed.add_field(name="치명타 대미지", value=f"{weapon_data.get('치명타 대미지', 0) * 100:.1f}%", inline=True)
        weapon_embed.add_field(name="보유 재료", value=f"**{weapon_parts}개**", inline=False)

        # 선택창 생성
        select = discord.ui.Select(
            placeholder="강화 타입을 선택하세요.",
            options=[
                discord.SelectOption(label="공격 강화", description="공격력 증가", value="공격 강화"),
                discord.SelectOption(label="치명타 확률 강화", description="치명타 확률 증가", value="치명타 확률 강화"),
                discord.SelectOption(label="치명타 대미지 강화", description="치명타 대미지 증가", value="치명타 대미지 강화"),
                discord.SelectOption(label="속도 강화", description="스피드 증가", value="속도 강화"),
                discord.SelectOption(label="명중 강화", description="명중 증가", value="명중 강화"),
                discord.SelectOption(label="방어 강화", description="방어력 증가", value="방어 강화"),
                discord.SelectOption(label="내구도 강화", description="내구도 증가", value="내구도 강화"),
                discord.SelectOption(label="스킬 강화", description="스킬 증폭 증가", value="스킬 강화"),
                discord.SelectOption(label="밸런스 강화", description="모든 스탯 증가", value="밸런스 강화")
            ]
        )

        async def select_callback(interaction: discord.Interaction):
            selected_enhance_type = select.values[0]

            ref_weapon = db.reference(f"무기/유저/{nickname}")
            weapon_data = ref_weapon.get() or {}
            ref_item = db.reference(f"무기/아이템/{nickname}")
            item_data = ref_item.get() or {}
            weapon_name = weapon_data.get("이름", "")
            weapon_enhanced = weapon_data.get("강화", 0)
            weapon_parts = item_data.get("강화재료", 0)
            
            polish_available = item_data.get("연마제", 0)
            speacial_polish_available = item_data.get("특수 연마제", 0)
            # 초기 연마 상태 (False: 미사용, True: 사용)
            polish_state = False
            speacial_polish_state = False
            # 강화 버튼
            enhance_button = discord.ui.Button(label="강화", style=discord.ButtonStyle.green)

            # 연마제 토글 버튼 (초기에는 미사용 상태)
            polish_button = discord.ui.Button(label="🛠️연마: 미사용", style=discord.ButtonStyle.secondary)

            async def polish_callback(interaction: discord.Interaction):
                nonlocal polish_state
                # 연마제가 없으면 토글 불가
                if polish_available <= 0:
                    await interaction.response.send_message("연마제가 없습니다!", ephemeral=True)
                    return
                # 토글 상태 변경
                polish_state = not polish_state
                polish_button.label = "🛠️연마: 사용" if polish_state else "🛠️연마: 미사용"
                polish_button.style = discord.ButtonStyle.success if polish_state else discord.ButtonStyle.secondary
                # 변경된 버튼 상태를 반영한 뷰로 메시지 업데이트
                ref_weapon = db.reference(f"무기/유저/{nickname}")
                weapon_data = ref_weapon.get() or {}
                ref_item = db.reference(f"무기/아이템/{nickname}")
                item_data = ref_item.get() or {}
                weapon_name = weapon_data.get("이름", "")
                weapon_enhanced = weapon_data.get("강화", 0)
                weapon_parts = item_data.get("강화재료", 0)
                enhancement_rate = enhancement_probabilities[weapon_enhanced]
                if polish_state:
                    enhancement_rate += 5
                if speacial_polish_state:
                    enhancement_rate += 50

                enhance_embed = discord.Embed(title="무기 강화", color=0xff00ff)
                enhance_embed.add_field(name="무기 이름", value=f"{weapon_name} **(+{weapon_enhanced})**", inline=False)
                enhance_embed.add_field(name="강화 설명", value=enhance_description[selected_enhance_type], inline=False)
                enhance_embed.add_field(name="성공 확률", value = f"**{enhancement_rate}%(+{weapon_enhanced} → +{weapon_enhanced + 1})**", inline=False)
                enhance_embed.add_field(name="보유 재료", value=f"**{weapon_parts}개**", inline=False)
                await interaction.response.edit_message(embed=enhance_embed, view=weapon_view)

            speacial_polish_button = discord.ui.Button(label="💎특수 연마: 미사용", style=discord.ButtonStyle.secondary)

            async def speacial_polish_callback(interaction: discord.Interaction):
                nonlocal speacial_polish_state
                # 연마제가 없으면 토글 불가
                if speacial_polish_available <= 0:
                    await interaction.response.send_message("특수 연마제가 없습니다!", ephemeral=True)
                    return
                # 토글 상태 변경
                speacial_polish_state = not speacial_polish_state
                speacial_polish_button.label = "💎특수 연마: 사용" if speacial_polish_state else "💎특수 연마: 미사용"
                speacial_polish_button.style = discord.ButtonStyle.success if speacial_polish_state else discord.ButtonStyle.secondary
                # 변경된 버튼 상태를 반영한 뷰로 메시지 업데이트
                ref_weapon = db.reference(f"무기/유저/{nickname}")
                weapon_data = ref_weapon.get() or {}
                ref_item = db.reference(f"무기/아이템/{nickname}")
                item_data = ref_item.get() or {}
                weapon_name = weapon_data.get("이름", "")
                weapon_enhanced = weapon_data.get("강화", 0)
                weapon_parts = item_data.get("강화재료", 0)
                enhancement_rate = enhancement_probabilities[weapon_enhanced]
                if polish_state:
                    enhancement_rate += 5
                if speacial_polish_state:
                    enhancement_rate += 50

                enhance_embed = discord.Embed(title="무기 강화", color=0xff00ff)
                enhance_embed.add_field(name="무기 이름", value=f"{weapon_name} **(+{weapon_enhanced})**", inline=False)
                enhance_embed.add_field(name="강화 설명", value=enhance_description[selected_enhance_type], inline=False)
                enhance_embed.add_field(name="성공 확률", value = f"**{enhancement_rate}%(+{weapon_enhanced} → +{weapon_enhanced + 1})**", inline=False)
                enhance_embed.add_field(name="보유 재료", value=f"**{weapon_parts}개**", inline=False)
                await interaction.response.edit_message(embed=enhance_embed, view=weapon_view)

            polish_button.callback = polish_callback
            speacial_polish_button.callback = speacial_polish_callback

            async def enhance_callback(interaction: discord.Interaction):
                nonlocal polish_state
                nonlocal speacial_polish_state
                nickname = interaction.user.name

                ref_weapon = db.reference(f"무기/유저/{nickname}")
                weapon_data = ref_weapon.get() or {}
                ref_item = db.reference(f"무기/아이템/{nickname}")
                item_data = ref_item.get() or {}
                weapon_enhanced = weapon_data.get("강화", 0)
                weapon_parts = item_data.get("강화재료", 0)
                
                if weapon_parts <= 0:
                    await interaction.response.send_message("재료가 없습니다! 일일퀘스트를 통해 재료를 모아보세요!",ephemeral=True)
                    return

                if weapon_enhanced == 20:
                    await interaction.response.send_message("이미 최고 강화입니다!",ephemeral=True)
                    return
                
                await interaction.response.defer()
                ref_item.update({"강화재료": weapon_parts - 1})

                enhancement_rate = enhancement_probabilities[weapon_enhanced]
                if polish_state:
                    enhancement_rate += 5
                    polish_state = False
                    polish_button.label = "🛠️연마: 미사용"
                    polish_button.style = discord.ButtonStyle.secondary
                    # 연마제 차감
                    item_ref = db.reference(f"무기/아이템/{nickname}")
                    current_items = item_ref.get() or {}
                    polish_count = current_items.get("연마제", 0)
                    if polish_count > 0:
                        item_ref.update({"연마제": polish_count - 1})
                if speacial_polish_state:
                    enhancement_rate += 50
                    speacial_polish_state = False
                    speacial_polish_button.label = "💎특수 연마: 미사용"
                    speacial_polish_button.style = discord.ButtonStyle.secondary
                    # 특수 연마제 차감
                    item_ref = db.reference(f"무기/아이템/{nickname}")
                    current_items = item_ref.get() or {}
                    special_polish_count = current_items.get("특수 연마제", 0)
                    if special_polish_count > 0:
                        item_ref.update({"특수 연마제": special_polish_count - 1})


                ref_weapon = db.reference(f"무기/유저/{nickname}")
                weapon_data = ref_weapon.get() or {}
                ref_item = db.reference(f"무기/아이템/{nickname}")
                item_data = ref_item.get() or {}
                weapon_name = weapon_data.get("이름", "")
                weapon_enhanced = weapon_data.get("강화", 0)
                weapon_parts = item_data.get("강화재료", 0)
                enhancement_rate = enhancement_probabilities[weapon_enhanced]
                if polish_state:
                    enhancement_rate += 5
                if speacial_polish_state:
                    enhancement_rate += 50
                    
                enhance_embed = discord.Embed(title="무기 강화", color=0xff00ff)
                enhance_embed.add_field(name="무기 이름", value=f"{weapon_name} **(+{weapon_enhanced})**", inline=False)
                enhance_embed.add_field(name="강화 설명", value=enhance_description[selected_enhance_type], inline=False)
                enhance_embed.add_field(name="성공 확률", value = f"**{enhancement_rate}%(+{weapon_enhanced} → +{weapon_enhanced + 1})**", inline=False)
                enhance_embed.add_field(name="보유 재료", value=f"**{weapon_parts}개**", inline=False)
                await interaction.edit_original_response(embed=enhance_embed, view=weapon_view)

                channel = self.bot.get_channel(int(ENHANCEMENT_CHANNEL))

                userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                userembed.add_field(name="", value=f"{interaction.user.display_name}님이 **[{weapon_name}]**의 강화를 시작했습니다!⚔️", inline=False)
                userembed.add_field(name="", value=f"**[{weapon_name}](+{weapon_enhanced}) → [{weapon_name}](+{weapon_enhanced + 1})**", inline=False)
                userembed.add_field(
                    name="현재 강화 확률",
                    value=f"{enhancement_rate}%",
                    inline=False
                )
                userembed.add_field(name="", value=f"5초 후 결과가 발표됩니다!", inline=False)
                enhance_message = await channel.send(embed=userembed)

                roll = random.randint(1, 100)

                if roll <= enhancement_rate:  # 성공
                    weapon_enhanced += 1
                    ref_weapon.update({"강화": weapon_enhanced})
                
                    # 강화 옵션 설정

                    # 강화 함수
                    async def enhance_weapon(enhancement_type):
                        
                        ref_weapon = db.reference(f"무기/유저/{nickname}")
                        weapon_data = ref_weapon.get() or {}

                        ref_weapon_log = db.reference(f"무기/유저/{nickname}/강화내역")
                        weapon_log_data = ref_weapon_log.get() or {}

                        original_enhancement = weapon_log_data.get(enhancement_type,0)
                        ref_weapon_log.update({enhancement_type : original_enhancement + 1}) # 선택한 강화 + 1

                        # 무기의 기존 스탯 가져오기
                        weapon_stats = {key: value for key, value in weapon_data.items() if key not in ["강화","이름", "강화확률", "강화내역"]}

                        # 강화 옵션 가져오기
                        ref_weapon_enhance = db.reference(f"무기/강화")
                        enhancement_options = ref_weapon_enhance.get() or {}
                        options = enhancement_options.get(enhancement_type, enhancement_options["밸런스 강화"])
                        stats = options["stats"]  # 실제 강화 수치가 있는 부분
                        main_stat = options["main_stat"]

                        # 스탯 적용
                        for stat, base_increase in stats.items():
                            # 선택한 스탯은 특화 배율 적용
                            increase = round(base_increase, 3)  # 기본 배율 적용
                            final_stat = round(weapon_stats.get(stat, 0) + increase, 3)
                            
                            if final_stat >= 1 and stat in ["치명타 확률"]:
                                weapon_stats[stat] = 1
                            else:
                                weapon_stats[stat] = final_stat
                        
                        # 결과 반영
                        ref_weapon.update(weapon_stats)

                        # 강화 성공
                        embed_color = 0x00FF00  # 녹색
                        status_text = "✅ **강화 성공!**"

                        used_items = []
                        if polish_state:
                            used_items.append("연마제")
                        if speacial_polish_state:
                            used_items.append("특수 연마제")

                        embed_data = {
                            "embeds": [
                                {
                                    "title": status_text,
                                    "color": embed_color,
                                    "fields": [
                                        {"name": "무기 이름", "value": f"`{weapon_name}`", "inline": True},
                                        {"name": "강화 종류", "value": selected_enhance_type, "inline": True},
                                        {"name": "현재 강화 수치", "value": f"{weapon_enhanced - 1}강 ➜ {weapon_enhanced}강", "inline": True},
                                        {"name": "사용한 아이템", "value": ', '.join(used_items) if used_items else "없음", "inline": False},
                                        {"name": "성공 확률", "value": f"{enhancement_rate}%", "inline": True},
                                    ],
                                    "footer": {"text": "무기 강화 시스템"},
                                }
                            ]
                        }
                        await enhance_message.edit(embed=discord.Embed.from_dict(embed_data["embeds"][0]))
                        
                    await enhance_weapon(selected_enhance_type)

                else:  # 실패
                    await asyncio.sleep(5)
                    # 강화 실패
                    embed_color = 0xFF0000  # 빨간색
                    status_text = "❌ **강화 실패**"

                    used_items = []
                    if polish_state:
                        used_items.append("연마제")
                    if speacial_polish_state:
                        used_items.append("특수 연마제")

                    embed_data = {
                        "embeds": [
                            {
                                "title": status_text,
                                "color": embed_color,
                                "fields": [
                                    {"name": "무기 이름", "value": f"`{weapon_name}`", "inline": True},
                                    {"name": "강화 종류", "value": selected_enhance_type, "inline": True},
                                    {"name": "현재 강화 수치", "value": f"{weapon_enhanced}강 ➜ {weapon_enhanced + 1}강", "inline": True},
                                    {"name": "사용한 아이템", "value": ', '.join(used_items) if used_items else "없음", "inline": False},
                                    {"name": "성공 확률", "value": f"{enhancement_rate}%", "inline": True},
                                ],
                                "footer": {"text": "무기 강화 시스템"},
                            }
                        ]
                    }
                    await enhance_message.edit(embed=discord.Embed.from_dict(embed_data["embeds"][0]))
                                    
            
            enhance_button.callback = enhance_callback
            weapon_view = discord.ui.View()
            weapon_view.add_item(select)
            weapon_view.add_item(enhance_button)
            weapon_view.add_item(polish_button)
            weapon_view.add_item(speacial_polish_button)

            def chunked_stat_lines(stat_lines, chunk_size=3):
                return [
                    ", ".join(stat_lines[i:i+chunk_size])
                    for i in range(0, len(stat_lines), chunk_size)
                ]
            
            def generate_enhance_descriptions(enhancement_options):
                fixed_descriptions = {
                    "공격 강화": "공격력을 강화합니다!",
                    "치명타 확률 강화": "치명타 확률을 강화합니다!",
                    "치명타 대미지 강화": "치명타 대미지를 강화합니다!",
                    "속도 강화": "스피드를 강화합니다!",
                    "명중 강화": "명중을 강화합니다!",
                    "방어 강화": "방어력을 강화합니다!",
                    "내구도 강화": "내구도를 강화합니다!",
                    "스킬 강화": "스킬 대미지를 강화합니다!",
                    "밸런스 강화": "모든 스탯을 강화합니다!",
                }
                

                enhance_description = {}

                
                for name, stats in enhancement_options.items():
                    
                    # 고정 문구 유지
                    fixed_line = fixed_descriptions.get(name, f"{name} 효과!")

                    # 스탯 설명 부분 자동 생성
                    stat_lines = []
                    for stat_name, value in stats['stats'].items():
                        if stat_name in ["치명타 확률", "치명타 대미지"]:
                            stat_lines.append(f"{stat_name} + {round(value * 100)}%")
                        else:
                            stat_lines.append(f"{stat_name} + {value}")

                    # 3개마다 줄바꿈
                    chunked_lines = chunked_stat_lines(stat_lines, 3)
                    full_description = fixed_line + "\n" + "\n".join(chunked_lines)

                    enhance_description[name] = full_description

                return enhance_description
            
            ref_weapon_enhance = db.reference(f"무기/강화")
            enhancement_options = ref_weapon_enhance.get() or {}
            enhance_description = generate_enhance_descriptions(enhancement_options)

            global enhancement_probabilities
            enhancement_rate = enhancement_probabilities[weapon_enhanced]
            if polish_state:
                enhancement_rate += 5
            if speacial_polish_state:
                enhancement_rate += 50
            enhance_embed = discord.Embed(title="무기 강화", color=0xff00ff)
            enhance_embed.add_field(name="무기 이름", value=f"{weapon_name} **(+{weapon_enhanced})**", inline=False)
            enhance_embed.add_field(name="강화 설명", value=enhance_description[selected_enhance_type], inline=False)
            enhance_embed.add_field(name="성공 확률", value = f"**{enhancement_rate}%(+{weapon_enhanced} → +{weapon_enhanced + 1})**", inline=False)
            enhance_embed.add_field(name="보유 재료", value=f"**{weapon_parts}개**", inline=False)
            await interaction.response.edit_message(embed=enhance_embed, view=weapon_view)

        select.callback = select_callback

        global enhancement_probabilities
        enhancement_rate = enhancement_probabilities[weapon_enhanced]
        weapon_embed.add_field(name="현재 강화 확률", value=f"**{enhancement_rate}%**", inline=False)
        await interaction.response.send_message(embed=weapon_embed, view=discord.ui.View().add_item(select), ephemeral=True)

    @app_commands.command(name="무기생성",description="무기를 생성합니다")
    @app_commands.choices(무기타입=[
    Choice(name='활', value='활'),
    Choice(name='대검', value='대검'),
    Choice(name='단검', value='단검'),
    Choice(name='조총', value='조총'),
    Choice(name='창', value='창'),
    Choice(name='낫', value='낫'),
    Choice(name='스태프-화염', value='스태프-화염'),
    Choice(name='스태프-냉기', value='스태프-냉기'),
    Choice(name='스태프-신성', value='스태프-신성'),
    Choice(name='태도', value='태도'),
    ])
    @app_commands.describe(이름 = "무기의 이름을 입력하세요", 무기타입 = "무기의 타입을 선택하세요")
    async def create_weapon(self,interaction: discord.Interaction, 이름: str, 무기타입: str):
        nickname = interaction.user.name
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
        current_predict_season = cur_predict_seasonref.get()

        ref_weapon = db.reference(f"무기/강화/{nickname}")
        weapon_data = ref_weapon.get() or {}

        weapon_name = weapon_data.get("이름", "")
        if weapon_name == "":
            ref_weapon_base = db.reference(f"무기/기본 스탯")
            base_weapon_stats = ref_weapon_base.get() or {}
            ref_weapon = db.reference(f"무기/강화/{nickname}")
            ref_weapon.update(base_weapon_stats[무기타입])
            ref_weapon.update({
                "이름" : 이름,
                "무기타입" : 무기타입,
                "강화내역" : ""
            })
            weapon_data = ref_weapon.get() or {}

            weapon_name = weapon_data.get("이름", "")
            weapon_enhanced = weapon_data.get("강화",0)
            weapon_embed = discord.Embed(title="무기 생성 완료!", color=0xff00ff)
            weapon_embed.add_field(name="무기 이름", value=f"{weapon_name} **(+{weapon_enhanced})**", inline=False)
            weapon_embed.add_field(name="무기 타입", value=f"{무기타입}", inline=False)
            weapon_embed.add_field(name="내구도", value=f"{weapon_data.get('내구도', 0)}", inline=False)
            weapon_embed.add_field(name="공격력", value=f"{weapon_data.get('공격력', 0)}", inline=True)
            weapon_embed.add_field(name="스킬 증폭", value=f"{weapon_data.get('스킬 증폭', 0)}", inline=True)
            weapon_embed.add_field(name="방어력", value=f"{weapon_data.get('방어력', 0)}", inline=True)
            weapon_embed.add_field(name="스피드", value=f"{weapon_data.get('스피드', 0)}", inline=True)
            weapon_embed.add_field(name="명중", value=f"{weapon_data.get('명중', 0)}", inline=True)
            weapon_embed.add_field(name="사거리", value=f"{weapon_data.get('사거리', 0)}", inline=True)
            weapon_embed.add_field(name="치명타 확률", value=f"{weapon_data.get('치명타 확률', 0) * 100:.1f}%", inline=True)
            weapon_embed.add_field(name="치명타 대미지", value=f"{weapon_data.get('치명타 대미지', 0) * 100:.1f}%", inline=True)
            
        else:
            weapon_enhanced = weapon_data.get("강화",0)
            weapon_embed = discord.Embed(title="무기 생성 불가!", color=0xff0000)
            weapon_embed.add_field(name="", value=f"이미 [**{weapon_name}**(+{weapon_enhanced})] 무기를 보유중입니다!", inline=False)

        await interaction.response.send_message(embed=weapon_embed)
    
# 컨텍스트 메뉴 명령어 등록 (메시지 대상)
    @app_commands.command(name="무기배틀",description="각자의 무기로 대결합니다")
    @app_commands.describe(상대 = "상대를 고르세요")
    async def weapon_battle(self, interaction: discord.Interaction, 상대 : discord.Member):
        await interaction.response.defer()

        nickname = interaction.user.name

        ref_weapon_challenger = db.reference(f"무기/유저/{nickname}")
        weapon_data_challenger = ref_weapon_challenger.get() or {}

        weapon_name_challenger = weapon_data_challenger.get("이름", "")
        if weapon_name_challenger == "":
            await interaction.followup.send("무기를 가지고 있지 않습니다! 무기를 생성해주세요!",ephemeral=True)
            return
        
        ref_weapon_opponent = db.reference(f"무기/유저/{상대.name}")
        weapon_data_opponent = ref_weapon_opponent.get() or {}

        weapon_name_opponent = weapon_data_opponent.get("이름", "")
        if weapon_name_opponent == "":
            await interaction.followup.send("상대가 무기를 가지고 있지 않습니다!",ephemeral=True)
            return

        # battle_ref = db.reference("승부예측/대결진행여부")
        # is_battle = battle_ref.get() or {}
        # if is_battle:
        #         warnembed = discord.Embed(title="실패",color = discord.Color.red())
        #         warnembed.add_field(name="",value="다른 대결이 진행중입니다! ❌")
        #         await interaction.followup.send(embed = warnembed)
        #         return
        # battle_ref.set(True)

        # 임베드 생성
        embed = discord.Embed(
            title=f"{interaction.user.display_name} vs {상대.display_name} 무기 대결",
            description="대결이 시작되었습니다!",
            color=discord.Color.blue()  # 원하는 색상 선택
        )
        await interaction.followup.send(embed=embed)
        await Battle(channel = interaction.channel,challenger_m= interaction.user, opponent_m = 상대, raid = False, practice = False)

        battle_ref = db.reference("승부예측/대결진행여부")
        battle_ref.set(False)

    @app_commands.command(name = "계승", description = "최고 강화에 도달한 무기의 힘을 이어받습니다.")
    async def inherit(self, interaction:discord.Interaction):
        nickname = interaction.user.name
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
        current_predict_season = cur_predict_seasonref.get()

        ref_weapon = db.reference(f"무기/유저/{nickname}")
        weapon_data = ref_weapon.get() or {}

        weapon_enhanced = weapon_data.get("강화")
        if weapon_enhanced < 15: # 강화가 15단계 이상이 아닐 경우
            warn_embed = discord.Embed(title="계승 불가!", color=0xff0000)
            warn_embed.add_field(name="", value=f"아직 무기가 15단계에 도달하지 않았습니다.", inline=False)
            await interaction.response.send_message(embed = warn_embed,ephemeral=True)
            return
        
        inherit_embed = discord.Embed(
        title=f"🎯 {weapon_enhanced}강 달성! 계승 가능!",
        description=(
            "계승 시:\n"
            "- 새로운 무기 종류를 선택합니다.\n"
            "- 강화 단계가 초기화됩니다.\n"
            "- +15 이후 강화한 횟수만큼 기존 강화 내역을 계승합니다.\n"
            "- 계승 보상 1종을 획득합니다.\n\n"
            "👉 아래 **계승 진행** 버튼을 눌러 계승을 완료하세요."
        ),
        color=0x00ff99
        )

        select = discord.ui.Select(
            placeholder="무기 타입을 선택하세요.",
            options = [
                discord.SelectOption(label="활", description="긴 사거리와 정확성을 가진 무기"),
                discord.SelectOption(label="대검", description="높은 공격력과 강력함"),
                discord.SelectOption(label="단검", description="높은 기동성과 회피율"),
                discord.SelectOption(label="조총", description="긴 사거리에서 강한 한 방"),
                discord.SelectOption(label="창", description="준수한 사거리와 거리 조절 능력"),
                discord.SelectOption(label="낫", description="흡혈을 통한 유지력"),
                discord.SelectOption(label="스태프-화염", description="강력한 화력과 지속적 화상 피해"),
                discord.SelectOption(label="스태프-냉기", description="얼음과 관련된 군중제어기 보유"),
                discord.SelectOption(label="스태프-신성", description="치유 능력과 침묵 부여"),
                discord.SelectOption(label="태도", description="명중에 따른 공격 능력 증가, 출혈을 통한 피해"),
            ]
        )

        async def select_callback(interaction: discord.Interaction):
            selected_weapon_type = select.values[0]

            # 강화 버튼을 추가하고 콜백 설정
            inherit_button = discord.ui.Button(label="계승 진행", style=discord.ButtonStyle.green)

            async def inherit_callback(interaction: discord.Interaction):
                chance = random.random()  # 0 ~ 1 사이 랜덤 값

                if chance < 0.7:
                    inherit_type = "기본 스탯 증가"
                else:
                    inherit_type = "기본 스킬 레벨 증가"

                modal = InheritWeaponNameModal(user_id=interaction.user.id, selected_weapon_type=selected_weapon_type, weapon_data=weapon_data, inherit_type = inherit_type)
                await interaction.response.send_modal(modal)
                
            inherit_button.callback = inherit_callback
            inherit_view = discord.ui.View()
            inherit_view.add_item(select)
            inherit_view.add_item(inherit_button)
            
    
            await interaction.response.edit_message(view=inherit_view)

        select.callback = select_callback
        await interaction.response.send_message(embed=inherit_embed, view=discord.ui.View().add_item(select), ephemeral=True)

    @app_commands.command(name="레이드",description="레이드 보스와의 전투를 실행합니다.")
    async def raid(self, interaction: discord.Interaction):
        await interaction.response.defer()

        nickname = interaction.user.name
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
        current_predict_season = cur_predict_seasonref.get()

        ref_weapon_challenger = db.reference(f"무기/유저/{nickname}")
        weapon_data_challenger = ref_weapon_challenger.get() or {}

        weapon_name_challenger = weapon_data_challenger.get("이름", "")
        if weapon_name_challenger == "":
            await interaction.followup.send("무기를 가지고 있지 않습니다! 무기를 생성해주세요!",ephemeral=True)
            return
        
        ref_current_boss = db.reference(f"레이드/현재 레이드 보스")
        boss_name = ref_current_boss.get()
        
        ref_weapon_opponent = db.reference(f"레이드/보스/{boss_name}")
        weapon_data_opponent = ref_weapon_opponent.get() or {}

        weapon_name_opponent = weapon_data_opponent.get("이름", "")
        if weapon_name_opponent == "":
            await interaction.followup.send("상대가 없습니다!",ephemeral=True)
            return
        
        
        battle_ref = db.reference("승부예측/대결진행여부")
        is_battle = battle_ref.get() or {}
        if is_battle:
            warnembed = discord.Embed(title="실패",color = discord.Color.red())
            warnembed.add_field(name="",value="다른 대결이 진행중입니다! ❌")
            await interaction.followup.send(embed = warnembed)
            return

        ref_raid = db.reference(f"레이드/내역/{nickname}")
        raid_data = ref_raid.get() or {}
        raid_damage = raid_data.get("대미지", 0)
        raid_boss_name = raid_data.get("보스","")
        raid_bool = raid_data.get("레이드여부", False)
        
        result = False
        if weapon_data_opponent.get("내구도", 0) <= 0:
            if not raid_bool: # 레이드 참여 안했을 경우
                retry_embed = discord.Embed(
                    title="레이드 추가 도전",
                    description="오늘의 레이드보스는 이미 처치되었습니다!",
                    color=discord.Color.orange()
                )
                retry_embed.add_field(
                    name="",
                    value="**레이드를 추가 도전하시겠습니까?**",
                    inline=False
                )
                retry_embed.set_footer(text="모의전 진행 후 넣은 대미지 비율만큼의 보상을 받습니다!")
                
                class AfterRaidView(discord.ui.View):
                    def __init__(self, user_id):
                        super().__init__(timeout=60)  # 60초 후 자동 종료
                        self.user_id = user_id
                        self.future = asyncio.Future()  # 버튼 결과 저장 (True/False)

                    def disable_all_buttons(self):
                        """모든 버튼을 비활성화 상태로 변경"""
                        for child in self.children:
                            if isinstance(child, discord.ui.Button):
                                child.disabled = True

                    @discord.ui.button(label="도전하기", style=discord.ButtonStyle.green)
                    async def after_raid(self, interaction: discord.Interaction, button: discord.ui.Button):
                        # 버튼 비활성화 처리
                        if interaction.user.id != self.user_id:
                            await interaction.response.send_message("이 버튼은 당신의 것이 아닙니다.", ephemeral=True)
                            return
                        await interaction.response.defer()
                        self.disable_all_buttons()
                        self.future.set_result(True)
                        await interaction.edit_original_response(view = self)
                        
                view = AfterRaidView(interaction.user.id)
                await interaction.followup.send(embed=retry_embed, view=view, ephemeral=True)

                # ✅ 버튼 클릭 결과 대기 (True = 진행, False = 중단)
                result = await view.future

                if not result:
                    return  # 안했으면 return

                # 임베드 생성
                embed = discord.Embed(
                    title=f"{interaction.user.display_name}의 {weapon_data_opponent.get('이름', '')} 레이드 (추가 도전)",
                    description="대결이 시작되었습니다!",
                    color=discord.Color.blue()  # 원하는 색상 선택
                )
                if result:
                    await interaction.channel.send(embed = embed)
                else:
                    await interaction.followup.send(embed=embed)
                await Battle(channel = interaction.channel,challenger_m = interaction.user, boss = boss_name, raid = True, practice = True, raid_ended= True)

                return
            else: # 레이드 참여했을 경우
                warn_embed = discord.Embed(
                    title="격파 완료",
                    description="오늘의 레이드보스는 이미 처치되었습니다!",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=warn_embed, ephemeral=True)
                return

        result = False
        ref_item = db.reference(f"무기/아이템/{nickname}")
        item_data = ref_item.get() or {}
        raid_refresh = item_data.get("레이드 재도전", 0)
        if raid_bool:
            if raid_refresh: # 레이드 재도전권 있다면?
                retry_embed = discord.Embed(
                    title="레이드 재도전🔄 ",
                    description="이미 레이드를 참여하셨습니다.",
                    color=discord.Color.orange()
                )
                retry_embed.add_field(
                    name="도전한 보스",
                    value=f"**{raid_boss_name} **",
                    inline=False
                )
                retry_embed.add_field(
                    name="넣은 대미지",
                    value=f"**{raid_damage}💥 **",
                    inline=False
                )
                retry_embed.add_field(
                    name="",
                    value="**재도전권을 사용하시겠습니까?**",
                    inline=False
                )
                retry_embed.set_footer(text="재도전시 기존 기록이 삭제됩니다!")
                
                class RaidRetryView(discord.ui.View):
                    def __init__(self, user_id):
                        super().__init__(timeout=60)  # 60초 후 자동 종료
                        self.user_id = user_id
                        self.future = asyncio.Future()  # 버튼 결과 저장 (True/False)

                    def disable_all_buttons(self):
                        """모든 버튼을 비활성화 상태로 변경"""
                        for child in self.children:
                            if isinstance(child, discord.ui.Button):
                                child.disabled = True

                    @discord.ui.button(label="사용하기", style=discord.ButtonStyle.green)
                    async def use_retry(self, interaction: discord.Interaction, button: discord.ui.Button):
                        if interaction.user.id != self.user_id:
                            await interaction.response.send_message("이 버튼은 당신의 것이 아닙니다.", ephemeral=True)
                            return

                        await interaction.response.defer()
                        # 레이드 재도전권 사용 로직
                        ref_item = db.reference(f"무기/아이템/{interaction.user.name}")
                        item_data = ref_item.get() or {}
                        raid_refresh = item_data.get("레이드 재도전", 0)

                        # 버튼 비활성화 처리
                        self.disable_all_buttons()
                        
                        if raid_refresh > 0:
                            ref_item.update({"레이드 재도전": raid_refresh - 1})  # 사용 후 갱신

                            refraid = db.reference(f"레이드/내역/{interaction.user.name}")
                            refraid.delete() 

                            ref_boss = db.reference(f"레이드/보스/{boss_name}")
                            boss_data = ref_boss.get() or {}
                            Boss_HP = boss_data.get("내구도", 0)
                            ref_boss.update({"내구도" : Boss_HP + raid_damage})

                            self.future.set_result(True)  # ✅ True 반환 (재도전 성공)
                            await interaction.edit_original_response(view = self)
                        else:
                            await interaction.edit_original_response(content="레이드 재도전권이 없습니다!", view=None)
                            self.future.set_result(False)  # ✅ False 반환 (재도전 불가)
                
                view = RaidRetryView(interaction.user.id)
                await interaction.followup.send(embed=retry_embed, view=view, ephemeral=True)

                # ✅ 버튼 클릭 결과 대기 (True = 진행, False = 중단)
                result = await view.future

                if not result:
                    return  # 재도전 불가면 함수 종료
            else: # 재도전권 없다면
                warn_embed = discord.Embed(
                    title="도전 완료",
                    description="오늘의 레이드보스에 이미 도전했습니다!",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=warn_embed, ephemeral=True)
                return
        battle_ref.set(True)

        # 임베드 생성
        embed = discord.Embed(
            title=f"{interaction.user.display_name}의 {weapon_data_opponent.get('이름', '')} 레이드",
            description="대결이 시작되었습니다!",
            color=discord.Color.blue()  # 원하는 색상 선택
        )
        if result:
            await interaction.channel.send(embed = embed)
        else:
            await interaction.followup.send(embed=embed)
        await Battle(channel = interaction.channel,challenger_m = interaction.user, boss = boss_name, raid = True, practice = False)

        battle_ref = db.reference("승부예측/대결진행여부")
        battle_ref.set(False)

    @app_commands.command(name="레이드현황",description="현재 레이드 현황을 보여줍니다.")
    async def raid_status(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        max_reward = 20

        ref_current_boss = db.reference(f"레이드/현재 레이드 보스")
        boss_name = ref_current_boss.get()

        refraid = db.reference(f"레이드/내역")
        raid_all_data = refraid.get() or {}

        raid_data = {key:value for key, value in raid_all_data.items() if value['보스'] == boss_name and not value['모의전']}
        # 전체 대미지 합산
        total_damage = sum(data['대미지'] for data in raid_data.values())

        raid_data_sorted = sorted(raid_data.items(), key=lambda x: x[1]['대미지'], reverse=True)

        # 순위별로 대미지 항목을 생성
        rankings = []
        for idx, (nickname, data) in enumerate(raid_data_sorted, start=1):
            damage = data['대미지']
            if data.get('막타', False):
                rankings.append(f"**{idx}위**: {nickname} - {damage} 대미지 🎯")
            else:
                rankings.append(f"**{idx}위**: {nickname} - {damage} 대미지")

        refraidboss = db.reference(f"레이드/보스/{boss_name}")
        raid_boss_data = refraidboss.get() or {}
        cur_dur = raid_boss_data.get("내구도", 0)
        total_dur = raid_boss_data.get("총 내구도",0)
        
        # 내구도 비율 계산
        if total_dur > 0:
            durability_ratio = (total_dur - cur_dur) / total_dur  # 0과 1 사이의 값
            reward_count = math.floor(max_reward * durability_ratio)  # 총 20개의 재료 중, 내구도에 비례한 개수만큼 지급
        else:
            reward_count = 0  # 보스가 이미 처치된 경우


        remain_durability_ratio = round(cur_dur / total_dur * 100, 2)

        raid_after_data = {key:value for key, value in raid_all_data.items() if value['보스'] == boss_name and value['모의전']} # 격파 이후
        raid_after_data_sorted = sorted(raid_after_data.items(), key=lambda x: x[1]['대미지'], reverse=True)

        # 순위별로 대미지 항목을 생성
        after_rankings = []
        for idx, (nickname, data) in enumerate(raid_after_data_sorted, start=1):
            damage = data['대미지']
            damage_ratio = round(damage/total_dur * 100)
            reward_number = int(round(max_reward * 0.75))
            after_rankings.append(f"{nickname} - {damage} 대미지 ({damage_ratio}%)\n(강화재료 {reward_number}개 지급 예정!)")


        # 디스코드 임베드 생성
        embed = discord.Embed(title="🎯 레이드 현황", color=0x00ff00)
        embed.add_field(name="현재 레이드 보스", value=f"[{boss_name}]", inline=False)
        embed.add_field(name="레이드 보스의 현재 체력", value=f"[{cur_dur}/{total_dur}] {remain_durability_ratio}%", inline=False)
        embed.add_field(name="현재 대미지", value="\n".join(rankings), inline=False)
        embed.add_field(name="보상 현황", value=f"강화재료 **{reward_count}개** 지급 예정!", inline=False)
        if cur_dur <= 0: # 보스가 처치된 경우
            if boss_name == "카이사":
                embed.add_field(name = "", value = f"카이사 토벌로 랜덤박스 1개 지급 예정!")
            elif boss_name == "스우":
                embed.add_field(name = "", value = f"스우 토벌로 연마제 2개 지급 예정!")
            elif boss_name == "브라움":
                embed.add_field(name = "", value = f"브라움 토벌로 운명 왜곡의 룬 3개 지급 예정!")
            elif boss_name == "팬텀":
                embed.add_field(name = "", value = f"팬텀 토벌로 강화재료 3개 지급 예정!")
            else:
                embed.add_field(name = "", value = f"보스 토벌로 강화재료 3개 지급 예정!")
        if cur_dur <= 0:
            embed.add_field(name="레이드 종료 이후 도전 인원", value="\n".join(after_rankings), inline=False)
        await interaction.followup.send(embed = embed)

    @app_commands.command(name="수치조정", description="무기에 밸런스 패치로 인해 변경된 스탯을 적용합니다")
    async def stat_change(self, interaction: discord.Interaction):
        await interaction.response.defer()

        ref_users = db.reference(f"무기/유저").get()
        if not ref_users:
            await interaction.response.send_message("업데이트할 유저 데이터가 없습니다.", ephemeral=True)
            return

        embed = discord.Embed(title=f"⚔️ 스탯 조정 완료!", color=discord.Color.green())

        for nickname in ref_users.keys():
            weapon_name, stat_changes = apply_stat_change(nickname)
            if weapon_name and stat_changes:
                embed.add_field(
                    name=f"🛠️ {weapon_name}의 변경된 스탯",
                    value="\n".join(stat_changes),
                    inline=False
                )

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="탑",description="탑을 등반하여 탑 코인을 획득합니다.")
    async def infinity_tower(self, interaction: discord.Interaction, 빠른도전: bool = False):
        await interaction.response.defer()
        nickname = interaction.user.name
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
        current_predict_season = cur_predict_seasonref.get()

        ref_weapon_challenger = db.reference(f"무기/유저/{nickname}")
        weapon_data_challenger = ref_weapon_challenger.get() or {}

        weapon_name_challenger = weapon_data_challenger.get("이름", "")
        if weapon_name_challenger == "":
            await interaction.followup.send("무기를 가지고 있지 않습니다! 무기를 생성해주세요!",ephemeral=True)
            return
        
        ref_current_floor = db.reference(f"탑/유저/{nickname}")
        tower_data = ref_current_floor.get() or {}
        if not tower_data:
            ref_current_floor.set({"층수": 1})
            current_floor = 1
        else:
            current_floor = tower_data.get("층수", 1)
        
        if 빠른도전:
            target_floor = (current_floor // 10 + 1) * 10
        else:
            target_floor = current_floor

        weapon_data_opponent = generate_tower_weapon(target_floor)

        weapon_name_opponent = weapon_data_opponent.get("이름", "")
        if weapon_name_opponent == "":
            await interaction.followup.send("상대가 없습니다!",ephemeral=True)
            return
        
        ref_item = db.reference(f"무기/아이템/{nickname}")
        item_data = ref_item.get() or {}
        tower_refesh = item_data.get("탑 재도전", 0)

        battle_ref = db.reference("승부예측/대결진행여부")
        is_battle = battle_ref.get() or {}
        if is_battle:
            warnembed = discord.Embed(title="실패",color = discord.Color.red())
            warnembed.add_field(name="",value="다른 대결이 진행중입니다! ❌")
            await interaction.followup.send(embed = warnembed)
            return
        battle_ref.set(True)
        tower_bool = tower_data.get("등반여부", False)
        if tower_bool:
            if tower_refesh:
                userembed = discord.Embed(title=f"알림", color=discord.Color.light_gray())
                userembed.add_field(name="",value=f"{interaction.user.display_name}님이 아이템을 사용하여 탑에 재도전했습니다!", inline=False)
                ref_item.update({"탑 재도전": tower_refesh - 1})
                ref_current_floor = db.reference(f"탑/유저/{nickname}")
                ref_current_floor.update({"등반여부": False}) # 등반여부 초기화
                channel = interaction.client.get_channel(int(CHANNEL_ID))
                await channel.send(embed=userembed)
            else:
                warnembed = discord.Embed(title="실패",color = discord.Color.red())
                warnembed.add_field(name="",value="오늘의 도전 기회를 다 사용했습니다! ❌")
                await interaction.followup.send(embed = warnembed)
                return
        
       

        # ====================  [미션]  ====================
        # 일일미션 : 탑 1회 도전
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
        current_predict_season = cur_predict_seasonref.get()
        ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname}/미션/일일미션/탑 1회 도전")
        mission_data = ref.get() or {}
        mission_bool = mission_data.get('완료', False)
        if not mission_bool:
            ref.update({"완료": True})
            print(f"{interaction.user.display_name}의 [탑 1회 도전] 미션 완료")

        # ====================  [미션]  ====================
                    
        # 임베드 생성
        embed = discord.Embed(
            title=f"{interaction.user.display_name}의 탑 등반({target_floor}층)",
            description="전투가 시작되었습니다!",
            color=discord.Color.blue()  # 원하는 색상 선택
        )
        await interaction.followup.send(embed=embed)
        await Battle(channel = interaction.channel,challenger_m = interaction.user, tower = True, tower_floor=target_floor)

        battle_ref = db.reference("승부예측/대결진행여부")
        battle_ref.set(False)



    @app_commands.command(name="탑모의전",description="탑의 상대와 모의전투를 진행합니다.")
    @app_commands.describe(층수 = "도전할 층수를 선택하세요.")
    async def infinity_tower_practice(self, interaction: discord.Interaction,층수 : app_commands.Range[int, 1], 상대 : discord.Member = None, 시뮬레이션 : bool = False):
        if 상대 is None:
            상대 = interaction.user  # 자기 자신을 대상으로 설정
        
        ref_weapon_challenger = db.reference(f"무기/유저/{상대.name}")
        weapon_data_challenger = ref_weapon_challenger.get() or {}

        weapon_name_challenger = weapon_data_challenger.get("이름", "")
        if weapon_name_challenger == "":
            await interaction.response.send_message("무기를 가지고 있지 않습니다! 무기를 생성해주세요!",ephemeral=True)
            return
        
        current_floor = 층수
        
        weapon_data_opponent = generate_tower_weapon(current_floor)

        weapon_name_opponent = weapon_data_opponent.get("이름", "")
        if weapon_name_opponent == "":
            await interaction.response.send_message("상대가 없습니다!",ephemeral=True)
            return

        if 시뮬레이션:
            await interaction.response.defer()
            ref_skill_data = db.reference("무기/스킬")
            skill_data_firebase = ref_skill_data.get() or {}

            ref_weapon_challenger = db.reference(f"무기/유저/{상대.name}")
            weapon_data_challenger = ref_weapon_challenger.get() or {}

            ref_skill = db.reference(f"무기/스킬")
            skill_common_data = ref_skill.get() or {}

            win_count = 0
            for i in range(1000):
                result = await Battle(channel = interaction.channel,challenger_m= 상대, raid = False, practice = False, simulate = True, skill_data = skill_data_firebase, wdc = weapon_data_challenger, wdo = weapon_data_opponent, scd = skill_common_data)
                if result:  # True면 승리
                    win_count += 1

            result_embed = discord.Embed(title="시뮬레이션 결과",color = discord.Color.blue())
            win_probability = round((win_count / 1000) * 100, 2)
            weapon_types = ["대검","스태프-화염", "조총", "스태프-냉기", "창", "활", "스태프-신성", "단검", "낫"]
            weapon_type = weapon_types[(층수 - 1) % len(weapon_types)]  # 1층부터 시작
            result_embed.add_field(name=f"{weapon_data_challenger.get('이름','')}의 {층수}층({weapon_type}) 기대 승률",value=f"{win_probability}%")
            await interaction.followup.send(embed = result_embed)
            return
        
        # battle_ref = db.reference("승부예측/대결진행여부")
        # is_battle = battle_ref.get() or {}
        # if is_battle:
        #     warnembed = discord.Embed(title="실패",color = discord.Color.red())
        #     warnembed.add_field(name="",value="다른 대결이 진행중입니다! ❌")
        #     await interaction.response.send_message(embed = warnembed)
        #     return
        
        # battle_ref.set(True)
                    
        # 임베드 생성
        embed = discord.Embed(
            title=f"{상대.display_name}의 탑 등반({current_floor}층)(모의전)",
            description="전투가 시작되었습니다!",
            color=discord.Color.blue()  # 원하는 색상 선택
        )
        await interaction.response.send_message(embed=embed)
        await Battle(channel = interaction.channel,challenger_m = 상대, tower = True, practice= True, tower_floor= 층수)

        battle_ref = db.reference("승부예측/대결진행여부")
        battle_ref.set(False)

    @app_commands.command(name="랜덤박스", description="랜덤 박스를 열어 아이템을 얻습니다!")
    @app_commands.describe(개수="개봉할 랜덤박스 개수 (기본값: 1)")
    async def 랜덤박스(self, interaction: discord.Interaction, 개수: int = 1):
        nickname = interaction.user.name
        reward_pool = [
            ("강화재료", 3, 15),         # 15% 확률로 강화재료 3개
            ("강화재료", 5, 15),         # 15% 확률로 강화재료 5개
            ("강화재료", 10, 5),         # 5% 확률로 강화재료 10개
            ("레이드 재도전", 1, 15),    # 15% 확률로 레이드 재도전권 1개
            ("탑 재도전", 1, 15),        # 15% 확률로 탑 재도전권 1개
            ("연마제", 1, 15),           # 15% 확률로 연마제 1개
            ("연마제", 3, 5),            # 5% 확률로 연마제 3개
            ("특수 연마제", 1, 1),       # 1% 확률로 특수 연마제 1개
            ("스킬 각성의 룬", 1, 2),     # 2% 확률로 스킬 각성의 룬 1개
            ("운명 왜곡의 룬", 3, 10),   # 10% 확률로 운명 왜곡의 룬 3개
            ("꽝", 0, 2),                # 2% 확률로 꽝 (아이템 없음)
        ]
        
        ref = db.reference(f"무기/아이템/{nickname}")
        current_data = ref.get() or {}
        random_box = current_data.get("랜덤박스", 0)

        if random_box < 개수:
            embed = discord.Embed(
                title="사용 불가!",
                description=f"❌ 랜덤박스가 {개수}개 필요합니다. 현재 보유: {random_box}개",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # 결과 누적용
        result_summary = {}
        꽝_횟수 = 0
        last_reward = None

        for _ in range(개수):
            roll = random.randint(1, 100)
            current = 0
            for name, amount, chance in reward_pool:
                current += chance
                if roll <= current:
                    if name == "꽝":
                        꽝_횟수 += 1
                    else:
                        result_summary[name] = result_summary.get(name, 0) + amount
                        last_reward = (name, amount)
                    break

        # DB 업데이트
        ref.update({"랜덤박스": random_box - 개수})
        for name, total_amount in result_summary.items():
            previous = current_data.get(name, 0)
            ref.update({name: previous + total_amount})

        # ✅ 결과 출력
        if 개수 == 1:
            if last_reward:
                name, amount = last_reward
                embed = discord.Embed(title=f"🎁 랜덤박스 개봉 결과", color=discord.Color.gold())
                embed.add_field(name=f"", value=f"🎉 **{interaction.user.mention}님이 랜덤박스를 열어 `{name} {amount}개`를 획득하셨습니다!**", inline=False)
                await interaction.response.send_message(embed = embed)
            else:
                embed.add_field(name=f"", value=f"😭 아쉽게도 아무것도 얻지 못했습니다!", inline=False)
                await interaction.response.send_message(embed = embed)
        else:
            embed = discord.Embed(title=f"🎁 랜덤박스 {개수}개 개봉 결과", color=discord.Color.gold())

            if result_summary:
                for name, amount in result_summary.items():
                    embed.add_field(name=f"🧧 {name}", value=f"{amount}개", inline=False)

            if 꽝_횟수 > 0:
                embed.add_field(name="😢 꽝", value=f"{꽝_횟수}번", inline=False)

            await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="탑순위", description="탑 층수 순위를 보여줍니다.")
    async def tower_ranking(self,interaction: discord.Interaction):
        await interaction.response.defer()

        ref_all_users = db.reference("탑/유저").get()
        if not ref_all_users:
            await interaction.followup.send("탑 도전 기록이 없습니다.", ephemeral=True)
            return

        # 유저 이름과 층수 데이터 모음
        user_floors = []
        for name, data in ref_all_users.items():
            floor = data.get("층수", 0)
            user_floors.append((name, floor))

        # 내림차순 정렬 (높은 층 우선)
        user_floors.sort(key=lambda x: x[1], reverse=True)

        # Embed 생성
        embed = discord.Embed(
            title="🏆 탑 도전 순위",
            description="이번 주 탑 순위!",
            color=discord.Color.gold()
        )

        for i, (name, floor) in enumerate(user_floors[:10], start=1):
            top = ""
            if i == 1:
                rank_emoji = "🥇"
                top = "👑"
            elif i == 2:
                rank_emoji = "🥈"
            elif i == 3:
                rank_emoji = "🥉"
            else:
                rank_emoji = ""
            if floor >= 2:
                embed.add_field(name=f"", value=f"{rank_emoji} {i}위 - {name} : **{floor - 1}층 {top}** ", inline=False)

        await interaction.followup.send(embed=embed)


    @app_commands.command(name="배틀테스트",description="두 명을 싸움 붙힙니다.")
    @app_commands.describe(상대1 = "상대를 고르세요", 상대2 = "상대를 고르세요")
    async def battleTest(self,interaction: discord.Interaction, 상대1 : discord.Member, 상대2 : discord.Member, 시뮬레이션 : bool = False):
        await interaction.response.defer()

        ref_weapon_challenger = db.reference(f"무기/유저/{상대1.name}")
        weapon_data_challenger = ref_weapon_challenger.get() or {}

        weapon_name_challenger = weapon_data_challenger.get("이름", "")
        if weapon_name_challenger == "":
            await interaction.followup.send("무기를 가지고 있지 않습니다! 무기를 생성해주세요!",ephemeral=True)
            return
        
        ref_weapon_opponent = db.reference(f"무기/유저/{상대2.name}")
        weapon_data_opponent = ref_weapon_opponent.get() or {}

        weapon_name_opponent = weapon_data_opponent.get("이름", "")
        if weapon_name_opponent == "":
            await interaction.followup.send("상대가 무기를 가지고 있지 않습니다!",ephemeral=True)
            return
        
        if 시뮬레이션:
            ref_skill_data = db.reference("무기/스킬")
            skill_data_firebase = ref_skill_data.get() or {}

            ref_weapon_challenger = db.reference(f"무기/유저/{상대1.name}")
            weapon_data_challenger = ref_weapon_challenger.get() or {}

            ref_weapon_opponent = db.reference(f"무기/유저/{상대2.name}")
            weapon_data_opponent = ref_weapon_opponent.get() or {}

            ref_skill = db.reference(f"무기/스킬")
            skill_common_data = ref_skill.get() or {}

            win_count = 0
            for i in range(1000):
                result = await Battle(channel = interaction.channel,challenger_m= 상대1, opponent_m = 상대2, raid = False, practice = False, simulate = True, skill_data = skill_data_firebase, wdc = weapon_data_challenger, wdo = weapon_data_opponent, scd = skill_common_data)
                if result:  # True면 승리
                    win_count += 1

            result_embed = discord.Embed(title="시뮬레이션 결과",color = discord.Color.blue())
            result_embed.add_field(name=f"{weapon_data_challenger.get('이름','')} vs {weapon_data_opponent.get('이름','')}",value=f"{weapon_data_challenger.get('이름','')} {win_count}승, {weapon_data_opponent.get('이름','')} {1000 - win_count}승")
            await interaction.followup.send(embed = result_embed)
            return

        # battle_ref = db.reference("승부예측/대결진행여부")
        # is_battle = battle_ref.get() or {}
        # if is_battle:
        #     warnembed = discord.Embed(title="실패",color = discord.Color.red())
        #     warnembed.add_field(name="",value="다른 대결이 진행중입니다! ❌")
        #     await interaction.followup.send(embed = warnembed)
        #     return
        # battle_ref.set(True)

        # 임베드 생성
        embed = discord.Embed(
            title=f"{상대1.display_name} vs {상대2.display_name} 무기 대결",
            description="대결이 시작되었습니다!",
            color=discord.Color.blue()  # 원하는 색상 선택
        )
        await interaction.followup.send(embed=embed)
        await Battle(channel = interaction.channel,challenger_m= 상대1, opponent_m = 상대2, raid = False, practice = False)

        battle_ref = db.reference("승부예측/대결진행여부")
        battle_ref.set(False)

    @app_commands.command(name="테스트레이드",description="유저를 골라 레이드 보스를 상대로 모의전투를 시킵니다")
    @app_commands.choices(보스=[
    Choice(name='스우', value='스우'),
    Choice(name='브라움', value='브라움'),
    Choice(name='카이사', value='카이사'),
    Choice(name='팬텀', value = '팬텀'),
    Choice(name='허수아비', value = '허수아비'),
    ])
    @app_commands.describe(보스 = "전투할 보스를 선택하세요")
    async def raid_practice_test(self, interaction: discord.Interaction, 보스: str, 상대1 : discord.Member = None, 시뮬레이션 : bool = False):
        await interaction.response.defer()

        if 상대1 == None:
            상대1 = interaction.user
        ref_weapon_challenger = db.reference(f"무기/유저/{상대1.name}")
        weapon_data_challenger = ref_weapon_challenger.get() or {}

        weapon_name_challenger = weapon_data_challenger.get("이름", "")
        if weapon_name_challenger == "":
            await interaction.followup.send("무기를 가지고 있지 않습니다! 무기를 생성해주세요!",ephemeral=True)
            return
        
        boss_name = 보스
        
        ref_weapon_opponent = db.reference(f"레이드/보스/{boss_name}")
        weapon_data_opponent = ref_weapon_opponent.get() or {}

        weapon_name_opponent = weapon_data_opponent.get("이름", "")
        if weapon_name_opponent == "":
            await interaction.followup.send("상대가 없습니다!",ephemeral=True)
            return
        
        if 시뮬레이션:
            ref_skill_data = db.reference("무기/스킬")
            skill_data_firebase = ref_skill_data.get() or {}

            ref_weapon_challenger = db.reference(f"무기/유저/{상대1.name}")
            weapon_data_challenger = ref_weapon_challenger.get() or {}

            ref_weapon_opponent = db.reference(f"레이드/보스/{boss_name}")
            weapon_data_opponent = ref_weapon_opponent.get() or {}

            ref_skill = db.reference(f"무기/스킬")
            skill_common_data = ref_skill.get() or {}

            damage_total = 0
            damage_results = []
            for i in range(1000):
                result = await Battle(channel = interaction.channel,challenger_m = 상대1, boss = boss_name, raid = True, practice = True, simulate = True, skill_data = skill_data_firebase, wdc = weapon_data_challenger, wdo = weapon_data_opponent, scd = skill_common_data)
                if result:
                    damage_total += result  # 숫자 반환됨
                    damage_results.append(result)

            average_damage = round(sum(damage_results) / len(damage_results))
            max_damage = max(damage_results)
            min_damage = min(damage_results)

            result_embed = discord.Embed(title="시뮬레이션 결과", color=discord.Color.blue())
            result_embed.add_field(
                name="",
                value=(
                    f"**{weapon_data_challenger.get('이름', '')}**의 {boss_name} 상대 평균 대미지 : **{average_damage}**\n"
                    f"최대 대미지 : **{max_damage}**\n"
                    f"최소 대미지 : **{min_damage}**"
                )
            )
            await interaction.followup.send(embed = result_embed)
            return
        
        # battle_ref = db.reference("승부예측/대결진행여부")
        # is_battle = battle_ref.get() or {}
        # if is_battle:
        #     warnembed = discord.Embed(title="실패",color = discord.Color.red())
        #     warnembed.add_field(name="",value="다른 대결이 진행중입니다! ❌")
        #     await interaction.followup.send(embed = warnembed)
        #     return
        
        # battle_ref.set(True)

        # 임베드 생성
        embed = discord.Embed(
            title=f"{상대1.display_name}의 {weapon_data_opponent.get('이름', '')} 레이드 모의전",
            description="모의전이 시작되었습니다!",
            color=discord.Color.blue()  # 원하는 색상 선택
        )
        await interaction.followup.send(embed=embed)
        await Battle(channel = interaction.channel,challenger_m = 상대1, boss = boss_name, raid = True, practice = True)

        battle_ref = db.reference("승부예측/대결진행여부")
        battle_ref.set(False)


    @app_commands.command(name="거울", description="테스트")
    async def Mirror(self, interaction: discord.Interaction):
        await interaction.response.defer()

        user_name = interaction.user.name
        ref_weapon = db.reference(f"무기/유저/{user_name}")
        weapon_data_challenger = ref_weapon.get() or {}

        if not weapon_data_challenger.get("이름"):
            await interaction.followup.send("무기를 가지고 있지 않습니다! 무기를 생성해주세요!", ephemeral=True)
            return

        # 강화 보정 적용
        ref_weapon_enhance = db.reference(f"무기/강화")
        enhance_types_dict = ref_weapon_enhance.get() or {}
        enhance_types = list(enhance_types_dict.keys())  # dict_keys -> list 변환

        # 기존 강화 내역
        original_enhance_log = weapon_data_challenger.get("강화내역", {})
        total_enhancement = sum(original_enhance_log.values())

        # 랜덤 분배 함수
        def random_redistribute(total_points, keys):
            assigned = {key: 0 for key in keys}
            for _ in range(total_points):
                selected = random.choice(keys)
                assigned[selected] += 1
            return assigned

        # 랜덤 분배 실행
        new_enhance_log = random_redistribute(total_enhancement, enhance_types)

        weapon_data_opponent = weapon_data_challenger.copy()
        weapon_data_opponent["강화내역"] = new_enhance_log

        # 가장 많이 강화된 항목 찾기
        max_enhance_type = max(new_enhance_log, key=new_enhance_log.get)

        # 이름 앞 글자 추출 (예: "스킬 강화" -> "스킬형")
        prefix = max_enhance_type.split()[0] + "형"

        # 이름 변경
        original_name = weapon_data_challenger["이름"]
        weapon_data_opponent["이름"] = f"{original_name}-{prefix}"

        # 스탯 반영
        enhancement_options = db.reference(f"무기/강화").get() or {}
        base_weapon_stats = db.reference(f"무기/기본 스탯").get() or {}
        weapon_data_opponent = apply_stat_to_weapon_data(
            weapon_data_opponent,
            enhancement_options,
            base_weapon_stats
        )

        skill_data_firebase = db.reference("무기/스킬").get() or {}

        # 쓰레드 생성
        thread = await interaction.channel.create_thread(
            name=f"{interaction.user.display_name}의 미러 시뮬레이션",
            type=discord.ChannelType.public_thread
        )

        # 임베드 생성
        embed = discord.Embed(
            title=f"{interaction.user.display_name}의 미러 시뮬레이션",
            description="시뮬레이션이 시작되었습니다!",
            color=discord.Color.blue()  # 원하는 색상 선택
        )

        result_view = ResultButton(interaction.user, weapon_data_challenger, weapon_data_opponent, skill_data_firebase)
        msg = await thread.send(
            content="💡 강화된 무기 비교 및 시뮬레이션 결과를 확인해보세요!",
            embeds=[
                get_stat_embed(weapon_data_challenger, weapon_data_opponent),
                get_enhance_embed(weapon_data_challenger, weapon_data_opponent)
            ],
            view=result_view
        )
        result_view.message = msg  # 메시지 저장

        await interaction.followup.send(embed = embed, ephemeral=True)


    # 명령어 정의
    @app_commands.command(name="룬사용", description="룬을 사용합니다.")
    @app_commands.choices(룬=[
        Choice(name='스킬 각성의 룬', value='스킬 각성의 룬'),
        Choice(name='운명 왜곡의 룬', value='운명 왜곡의 룬'),
        Choice(name='회귀의 룬', value='회귀의 룬'),
    ])
    @app_commands.describe(룬 = "사용할 룬을 선택하세요")
    async def rune(self, interaction: discord.Interaction, 룬: str):
        await interaction.response.defer()

        nickname = interaction.user.name
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
        current_predict_season = cur_predict_seasonref.get()

        ref_item = db.reference(f"무기/아이템/{nickname}")
        item_data = ref_item.get() or {}
        rune_count = item_data.get(룬, 0)

        if rune_count <= 0:
            await interaction.followup.send("보유한 해당 룬이 없습니다.", ephemeral=True)
            return

        
        # 임베드 생성
        rune_embed = discord.Embed(title=f"{룬} 사용 준비", color=discord.Color.orange())
        if 룬 == "스킬 각성의 룬":
            ref_inherit_log = db.reference(f"무기/유저/{nickname}/계승 내역")
            inherit_log = ref_inherit_log.get() or {}
            base_stat_increase = inherit_log.get("기본 스탯 증가", 0)
            if base_stat_increase <= 1: # 기본 스탯 증가가 1이라면 사용 불가
                warning_embed = discord.Embed(title=f"{룬} 사용 실패!", color=discord.Color.red())
                warning_embed.description = (
                    f"{interaction.user.display_name}님의 **기본 스탯 증가**가 2 미만이기 때문에 발동이 **실패**하였습니다!\n"
                )
                await interaction.followup.send(embed=warning_embed)
                return
            rune_embed.description = (
                f"🔮 {interaction.user.display_name}님의 손에 **스킬 각성의 룬**이 반응합니다...\n\n"
                f"사용 시, 고유한 힘이 **기본 스탯 증가 2**만큼을 태워\n"
                f"**기본 스킬 레벨 증가 1**로 재구성합니다."
            )
        elif 룬 == "운명 왜곡의 룬":
            ref_inherit_log = db.reference(f"무기/유저/{nickname}/계승 내역")
            inherit_log = ref_inherit_log.get() or {}
            additional_enhance = inherit_log.get("추가강화", {})
            enhance_count = sum(additional_enhance.values())
            if enhance_count <= 0: # 추가강화 수치가 0이라면 사용 불가 
                warning_embed = discord.Embed(title=f"{룬} 사용 실패!", color=discord.Color.red())
                warning_embed.description = (
                    f"{interaction.user.display_name}님의 **추가 강화**수치가 부족하여 발동이 **실패**하였습니다!\n"
                )
                await interaction.followup.send(embed=warning_embed)
                return
            
            # 여기서 보유한 룬 수량 확인
            owned_rune_count = item_data.get("운명 왜곡의 룬", 0)

            if owned_rune_count >= 50:
                rune_embed.description = (
                    f"🔮 {interaction.user.display_name}님의 손에 **운명 왜곡의 룬**이 반응합니다...\n\n"
                    f"사용 시, 알 수 없는 힘이 발현되어\n"
                    f"**추가 강화 수치가 랜덤하게 재구성**됩니다.\n\n"
                    f"운명 왜곡의 룬이 50개 이상일 경우,\n이를 융합하여 **회귀의 룬**으로 변환이 가능합니다."
                )
            else:
                rune_embed.description = (
                    f"🔮 {interaction.user.display_name}님의 손에 **운명 왜곡의 룬**이 반응합니다...\n\n"
                    f"사용 시, 알 수 없는 힘이 발현되어\n"
                    f"**추가 강화 수치가 랜덤하게 재구성**됩니다."
                )
        elif 룬 == "회귀의 룬":
            ref_inherit_log = db.reference(f"무기/유저/{nickname}/계승 내역")
            inherit_log = ref_inherit_log.get() or {}
            additional_enhance = inherit_log.get("추가강화", {})
            enhance_count = sum(additional_enhance.values())
            if enhance_count <= 0: # 추가강화 수치가 0이라면 사용 불가 
                warning_embed = discord.Embed(title=f"{룬} 사용 실패!", color=discord.Color.red())
                warning_embed.description = (
                    f"{interaction.user.display_name}님의 **추가 강화**수치가 부족하여 발동이 **실패**하였습니다!\n"
                )
                await interaction.followup.send(embed=warning_embed)
                return
            rune_embed.description = (
                f"🔮 {interaction.user.display_name}님의 손에 **회귀의 룬**이 반응합니다...\n\n"
                f"사용 시, 시간을 거슬러, 강화의 흔적을 지워냅니다.\n"
                f"사라진 힘은 **특수 연마제**의 형태로 응축됩니다. \n"
                f"추가 강화 수치를 모두 제거하고, 그 수치만큼 **특수 연마제**를 연성합니다."
            )

        # 버튼 뷰 구성
        view = RuneUseButton(user=interaction.user, rune_name=룬, nickname=nickname, item_ref=ref_item, item_data=item_data)
        await interaction.followup.send(embed=rune_embed, view=view)
                    

    @app_commands.command(name="이모지", description="이모지 테스트")
    async def emoji(self, interaction: discord.Interaction, 이모지 : str):
        await interaction.response.send_message(이모지)
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        hello(bot),
        guilds=[Object(id=298064707460268032)]
    )