import discord
import random
import copy
import asyncio
import math
from typing import Optional, Literal
from firebase_admin import db
from discord.app_commands import Choice
from discord import app_commands
from discord.ext import commands
from discord import Interaction, Object
from datetime import datetime
from dotenv import load_dotenv
from collections import Counter
from .battle import Battle
from .battle_utils import get_user_insignia_stat, attack_weapons, skill_weapons, percent_insignias, insignia_items
from .commands import mission_notice, give_item

API_KEY = None

ENHANCEMENT_CHANNEL = 1350434647149908070


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

# 랜덤 분배 함수
def random_redistribute(total_points, keys):
    assigned = {key: 0 for key in keys}
    for _ in range(total_points):
        selected = random.choice(keys)
        assigned[selected] += 1
    return assigned

class ResultButton(discord.ui.View):
    def __init__(self, user: discord.User, wdc: dict, wdo: dict, skill_data: dict, insignia: dict):
        super().__init__(timeout=None)
        self.user = user
        self.wdc = wdc            # 원본 무기 데이터 (강화 전)
        self.wdo = wdo            # 강화 후 무기 데이터
        self.skill_data = skill_data
        self.insignia = insignia
        self.reroll_count = 0     # 재구성 시도 횟수
        self.win_count = 0        # 시뮬레이션 승리 횟수
        self.message = None       # 나중에 메세지 저장

    async def do_reroll(self):
        total_enhancement = sum(self.wdc.get("강화내역", {}).values())

        ref_weapon_enhance = db.reference(f"무기/강화")
        enhance_types_dict = ref_weapon_enhance.get() or {}
        enhance_types = list(enhance_types_dict.keys())

        weapon_type = self.wdc.get("무기타입", "")
        if weapon_type in attack_weapons:
            enhance_types = [etype for etype in enhance_types_dict.keys() if etype != "스킬 강화"]
        elif weapon_type in skill_weapons:
            enhance_types = [etype for etype in enhance_types_dict.keys() if etype != "공격 강화"]

        # 강화 점수 재분배
        random_log = random_redistribute(total_enhancement, enhance_types)

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

        # 100회 시뮬레이션 (비동기 Battle 함수 사용)
        for _ in range(100):
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
                scd=self.skill_data,
                insignia=self.insignia
            )
            if result:
                win_count += 1

        
        win_rate = win_count / 100 * 100
        outcome = f"🏆 **승리!**[{self.win_count + 1}승!]" if win_rate >= 50 else "❌ **패배!**"

        embed = discord.Embed(title="시뮬레이션 결과", color=discord.Color.gold())
        embed.add_field(
            name=f"{self.wdc['이름']} vs {self.wdo['이름']}",
            value=(
                f"{self.wdc['이름']} {win_count}승\n"
                f"{self.wdo['이름']} {100 - win_count}승\n\n"
                f"**승률**: {win_rate:.1f}%\n"
                f"{outcome}"
            )
        )

        # 승리 시
        if win_rate >= 50:
            self.win_count += 1
            give_item(interaction.user.name,"탑코인",1)
            ref_mirror = db.reference(f"무기/거울/{interaction.user.name}")
            ref_mirror.update({"승수": self.win_count})
            if self.win_count >= 10: # 10승 달성 시 종료
                # 버튼 비활성화
                for child in self.children:
                    child.disabled = True
                if self.message:
                    await self.message.edit(view=self)

                # ====================  [미션]  ====================
                # 시즌미션 : 나는 최강(거울의 전장 10승 달성)
                ref_mission = db.reference(f"미션/미션진행상태/{interaction.user.name}/시즌미션/나는 최강")
                mission_data = ref_mission.get() or {}
                mission_bool = mission_data.get('완료',0)
                if not mission_bool:
                    ref_mission.update({"완료": True})
                    mission_notice(interaction.user.display_name,"나는 최강")
                    print(f"{interaction.user.display_name}의 [나는 최강] 미션 완료")

                # ====================  [미션]  ====================
                # 최종 결과 Embed (10승 달성 시)
                final_embed = discord.Embed(title="🏆 최종 결과 (10승 달성)", color=discord.Color.gold())
                final_embed.add_field(
                    name="최종 승수",
                    value=f"🏁 **[{self.win_count}승/10승]**\n탑코인 **{self.win_count}개** 지급!",
                    inline=False
                )
                final_embed.add_field(
                    name=f"{self.wdc['이름']} vs {self.wdo['이름']}",
                    value=(
                        f"{self.wdc['이름']} {win_count}승\n"
                        f"{self.wdo['이름']} {100 - win_count}승\n\n"
                        f"**승률**: {win_rate:.1f}%\n"
                    )
                )
                await interaction.followup.send(embed=final_embed)
                return

            # 10승이 아니면 다음 라운드 진행
            await self.do_reroll()
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
                value=f"🏁 **[{self.win_count}승/10승]**\n탑코인 **{self.win_count}개** 지급!",
                inline=False
            )
            give_item(interaction.user.name,"탑코인",self.win_count)
            final_embed.add_field(
                name=f"{self.wdc['이름']} vs {self.wdo['이름']}",
                value=(
                    f"{self.wdc['이름']} {win_count}승\n"
                    f"{self.wdo['이름']} {100 - win_count}승\n\n"
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

class InsigniaView(discord.ui.View):
    def __init__(self, user: discord.User, nickname: str, inventory: dict, equipped: list, ref_user_insignia):
        super().__init__(timeout=60)
        self.user = user
        self.nickname = nickname
        self.inventory = inventory  # {인장명: 개수}
        self.equipped = equipped    # 길이 3 리스트, 빈 슬롯은 None 또는 '-'
        self.ref_user_insignia = ref_user_insignia

        for i in range(3):
            insignia_name = self.equipped[i] if i < len(self.equipped) and self.equipped[i] else "-"
            self.add_item(InsigniaSlotButton(label=insignia_name, slot_index=i, view_ref=self))

    async def update_message(self, interaction: discord.Interaction):
        desc_lines = []
        for i in range(3):
            name = self.equipped[i] if i < len(self.equipped) and self.equipped[i] else "-"
            if name and name != "-" and name in self.inventory:
                data = self.inventory[name]
                level = data.get("레벨", "N/A")
                # 각인 주스탯 정보 불러오기
                ref_item_insignia_stat = db.reference(f"무기/각인/스탯/{name}")
                insignia_stat = ref_item_insignia_stat.get() or {}

                stat = insignia_stat.get("주스탯", "N/A")
                base_value = insignia_stat.get("초기 수치", 0)
                per_level = insignia_stat.get("증가 수치", 0)
                value = base_value + per_level * level

                if name in percent_insignias:
                    value_str = f"{float(value) * 100:.1f}%"
                else:
                    value_str = str(value)

                desc_lines.append(f"{i+1}번: {name} (Lv.{level}, {stat} +{value_str})")
            else:
                desc_lines.append(f"{i+1}번: -")

        self.clear_items()
        for i in range(3):
            insignia_name = self.equipped[i] if i < len(self.equipped) and self.equipped[i] else "-"
            self.add_item(InsigniaSlotButton(label=insignia_name, slot_index=i, view_ref=self))

        embed = discord.Embed(
            title=f"{self.user.display_name}님의 각인 장착 상태",
            description="\n".join(desc_lines),
            color=discord.Color.blue()
        )
        await interaction.message.edit(embed=embed, view=self)

class InsigniaSlotButton(discord.ui.Button):
    def __init__(self, label, slot_index, view_ref):
        is_equipped = label != "-" and label != "" and label is not None
        style = discord.ButtonStyle.success if is_equipped else discord.ButtonStyle.secondary
        super().__init__(label=label, style=style)
        self.slot_index = slot_index
        self.view_ref = view_ref

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.view_ref.user:
            await interaction.response.send_message("본인만 조작할 수 있습니다.", ephemeral=True)
            return

        current_insignia = self.view_ref.equipped[self.slot_index] if self.slot_index < len(self.view_ref.equipped) else None

        if current_insignia and current_insignia != '-':
            # 해제
            self.view_ref.equipped[self.slot_index] = ""
            self.view_ref.ref_user_insignia.set(self.view_ref.equipped)
            await interaction.response.defer()
            await self.view_ref.update_message(interaction)
        else:
            # 장착 가능한 인장 목록 보여주기
            options = [name
                for name, data in self.view_ref.inventory.items()
                if data.get("개수", 0) > 0
                and name not in self.view_ref.equipped
                and name != "" and name != "-"
                ]
            if not options:
                await interaction.response.send_message("장착 가능한 인장이 없습니다.", delete_after= 3.0,ephemeral=True)
                return

            # 선택 메뉴 띄우기
            select = InsigniaSelect(slot_index=self.slot_index, options=options, view_ref=self.view_ref, interaction = interaction)
            view = discord.ui.View()
            view.add_item(select)
            await interaction.response.send_message(f"{self.slot_index +1}번 슬롯에 장착할 인장을 선택하세요.", view=view, ephemeral=True)

class InsigniaSelect(discord.ui.Select):
    def __init__(self, slot_index, options, view_ref, interaction):
        super().__init__(placeholder="인장을 선택하세요", min_values=1, max_values=1,
                         options=[discord.SelectOption(label=opt) for opt in options])
        self.slot_index = slot_index
        self.view_ref = view_ref
        self.interaction = interaction

    async def callback(self, interaction: discord.Interaction):
        chosen = self.values[0]
        if len(self.view_ref.equipped) < 3:
            self.view_ref.equipped += [""] * (3 - len(self.view_ref.equipped))
        self.view_ref.equipped[self.slot_index] = chosen
        self.view_ref.ref_user_insignia.set(self.view_ref.equipped)

        # 업데이트 메시지 갱신
        # (슬롯 버튼을 포함한 뷰를 다시 띄우는게 좋음)
        # 여기에선 예외 처리 없이 간단하게
        await interaction.response.edit_message(
            content=f"{self.slot_index + 1}번 슬롯에 장착 완료!",
            delete_after=1.0,
            view=None  # 뷰도 제거하려면 이 줄 포함
        )
        await self.view_ref.update_message(self.interaction)

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

        if diff_val > 0:
            emoji = "🟢"
            sign = "+"
        elif diff_val < 0:
            emoji = "🔴"
            sign = "-"
        else:
            emoji = "⚪️"
            sign = "±"
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

        if diff > 0:
            emoji = "🟢"
            sign = "+"
        elif diff < 0:
            emoji = "🔴"
            sign = "-"
        else:
            emoji = "⚪️"
            sign = "±"
        sign = "+" if diff > 0 else "-"
        diff_display = f"{sign}{abs(diff)}회"

        label = enhance_name_map.get(k, k)
        lines.append(f"{label}: {ch_val}회 ⟷ {op_val}회 (**{diff_display}** {emoji})")

    if not lines:
        embed.add_field(name="변경된 강화 내역 없음", value="모든 강화 내역이 동일합니다.", inline=False)
    else:
        embed.add_field(name="강화 차이", value="\n".join(lines), inline=False)

    return embed

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
    weapon_types = ["대검","스태프-화염", "조총", "스태프-냉기", "태도", "활", "스태프-신성", "단검", "낫", "창"]
    weapon_type = weapon_types[(floor - 1) % len(weapon_types)]  # 1층부터 시작
    enhancement_level = floor

    ref_weapon_base = db.reference(f"무기/기본 스탯")
    base_weapon_stats = ref_weapon_base.get() or {}

    # 기본 스탯
    base_stats = base_weapon_stats[weapon_type]

    skill_weapons = ["스태프-화염", "스태프-냉기", "스태프-신성", "낫"]
    attack_weapons = ["대검", "창", "활", "단검", "태도", "조총"]
    hybrid_weapons = []
    
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

            ref_base_skill_level_up = db.reference(f"무기/유저/{self.nickname}/계승 내역/기본 스킬 레벨 증가")
            ref_base_skill_level_up.set(0)  # 기본 스킬 레벨 초기화
            ref_base_stat_enhance = db.reference(f"무기/유저/{self.nickname}/계승 내역/기본 스탯 증가")
            ref_base_stat_enhance.set(0)  # 기본 스탯 증가 초기화
            ref_inherit = db.reference(f"무기/유저/{self.nickname}/계승")
            ref_inherit.set(0)  # 계승 수치 초기화

            # 특수 연마제 지급
            give_item(self.nickname, "특수 연마제", enhance_removed)

            # 임베드 메시지
            embed = discord.Embed(
                title="🔮 회귀의 룬이 사용되었습니다!",
                description=(
                    f"{interaction.user.display_name}님의 계승 수치가 모두 제거되었으며,\n"
                    f"추가 강화 수치 **[+{enhance_removed}]**만큼의 **특수 연마제**가 연성되었습니다."
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

            weapon_name, stat_changes = apply_stat_change(self.nickname)
            if weapon_name and stat_changes:
                embed.add_field(
                    name=f"🛠️ {weapon_name}의 변경된 스탯",
                    value="\n".join(stat_changes),
                    inline=False
                )
        # 룬 1개 소모 처리
        self.item_data = self.item_ref.get()  # 최신 상태 반영
        self.item_data[self.rune_name] -= 1
        self.item_ref.update(self.item_data)

        await interaction.edit_original_response(embed=embed, view=None)

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
            "치명타 대미지": base_weapon_stat["치명타 대미지"] + enhanced_stats.get("치명타 대미지", 0),
            "치명타 확률": base_weapon_stat["치명타 확률"] + enhanced_stats.get("치명타 확률", 0),
            "스킬": skills,
            "강화내역": new_enhancement_log,
            "계승 내역": inherit_log 
        }

        nickname = interaction.user.name

        ref_weapon = db.reference(f"무기/유저/{nickname}")
        ref_weapon.update(new_weapon_data)

        await interaction.response.send_message(
            f"[{self.weapon_data.get('이름', '이전 무기')}]의 힘을 계승한 **[{new_weapon_name}](🌟 +{inherit + 1})** 무기가 생성되었습니다!\n"
            f"계승 타입: [{self.inherit_type}] 계승이 적용되었습니다!\n"
            f"{enhancement_message}" 
        )
            
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

# 임베드를 생성하는 함수 (명령어 목록을 페이지별로 나누기)
def create_embed(commands_list, current_page, page_size):
    embed = discord.Embed(title="명령어 목록", color=discord.Color.green())
    start_index = current_page * page_size
    end_index = min((current_page + 1) * page_size, len(commands_list))

    # 현재 페이지에 해당하는 명령어들만 추가
    for cmd in commands_list[start_index:end_index]:
        embed.add_field(name=f"</{cmd.name}:{cmd.id}>", value=cmd.description, inline=False)
    return embed

class hello(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        load_dotenv()
    
    @app_commands.command(name="명령어",description="명령어 목록을 보여줍니다.")
    async def 명령어(self, interaction: discord.Interaction):
        exclude = {"온오프", "정상화", "재부팅", "익명온오프", "패배", "테스트", "열람포인트초기화", "공지", "베팅포인트초기화", "아이템지급", "아이템전체지급", "일일미션추가", "시즌미션추가", "미션삭제", "승리", "패배", "포인트지급"}
        commands_list = await self.bot.tree.fetch_commands()  # 동기화된 모든 명령어 가져오기
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
    
    @app_commands.command(name="강화", description="보유한 무기를 강화합니다.")
    async def enhance(self, interaction: discord.Interaction):
        nickname = interaction.user.name
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
                discord.SelectOption(label="속도 강화", description="스피드 증가", value="속도 강화"),
                discord.SelectOption(label="명중 강화", description="명중 증가", value="명중 강화"),
                discord.SelectOption(label="방어 강화", description="방어력 증가", value="방어 강화"),
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
                            polish_state = False
                        if speacial_polish_state:
                            used_items.append("특수 연마제")
                            speacial_polish_state = False

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
                        # ====================  [미션]  ====================
                        # 시즌미션 : 연마(무기 20강 달성)
                        if weapon_enhanced == 20:
                            ref_mission = db.reference(f"미션/미션진행상태/{nickname}/시즌미션/연마")
                            mission_data = ref_mission.get()
                            mission_bool = mission_data.get('완료',False)
                            if not mission_bool:
                                ref_mission.update({"완료": True})
                                mission_notice(interaction.user.display_name,"연마")
                                print(f"{interaction.user.display_name}의 [연마] 미션 완료")
                        # ====================  [미션]  ====================
                                
                        # ====================  [미션]  ====================
                        # 시즌미션 : 6종의 인장 미션
                        if weapon_enhanced == 20:
                            ref_enhance = db.reference(f"무기/유저/{nickname}/강화내역")
                            ref_inherit = db.reference(f"무기/유저/{nickname}/계승 내역/추가강화")
                            
                            enhance_data = ref_enhance.get() or {}
                            inherit_data = ref_inherit.get() or {}

                            # 시즌미션 이름 매핑: {강화이름: 미션명}
                            mission_targets = {
                                "공격 강화": "맹공",
                                "스킬 강화": "현자",
                                "명중 강화": "집중",
                                "속도 강화": "신속",
                                "방어 강화": "경화",
                                "밸런스 강화": "균형"
                            }

                            for stat_name, mission_name in mission_targets.items():
                                total = enhance_data.get(stat_name, 0)
                                inherited = inherit_data.get(stat_name, 0)
                                actual = total - inherited

                                if actual == 20:
                                    ref_mission = db.reference(f"미션/미션진행상태/{nickname}/시즌미션/{mission_name}")
                                    mission_data = ref_mission.get() or {}
                                    if not mission_data.get("완료", False):
                                        ref_mission.update({"완료": True})
                                        mission_notice(interaction.user.display_name, mission_name)
                                        print(f"{interaction.user.display_name}의 [{mission_name}] 미션 완료")
                            # ====================  [미션]  ===================
                            
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
        msg = await interaction.followup.send(embed=embed)
        await Battle(channel = interaction.channel,challenger_m= interaction.user, opponent_m = 상대, raid = False, practice = False)

        battle_ref = db.reference("승부예측/대결진행여부")
        battle_ref.set(False)
        await msg.delete()

    @app_commands.command(name = "계승", description = "최고 강화에 도달한 무기의 힘을 이어받습니다.")
    async def inherit(self, interaction:discord.Interaction):
        nickname = interaction.user.name

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
                discord.SelectOption(label="활", description="스피드를 통한 연사"),
                discord.SelectOption(label="대검", description="높은 공격력과 보호막 파괴"),
                discord.SelectOption(label="단검", description="높은 회피와 암살 능력"),
                discord.SelectOption(label="조총", description="치명타를 통한 스킬 연속 사용"),
                discord.SelectOption(label="창", description="꿰뚫림 스택을 통한 누적 피해"),
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

        ref_weapon_challenger = db.reference(f"무기/유저/{nickname}")
        weapon_data_challenger = ref_weapon_challenger.get() or {}

        weapon_name_challenger = weapon_data_challenger.get("이름", "")
        if weapon_name_challenger == "":
            await interaction.followup.send("무기를 가지고 있지 않습니다! 무기를 생성해주세요!",ephemeral=True)
            return
        
        ref_current_boss = db.reference(f"레이드/현재 레이드 보스")
        current_boss_name = ref_current_boss.get()
        
        ref_weapon_opponent = db.reference(f"레이드/보스/{current_boss_name}")
        weapon_data_opponent = ref_weapon_opponent.get() or {}

        weapon_name_opponent = weapon_data_opponent.get("이름", "")
        if weapon_name_opponent == "":
            await interaction.followup.send("상대가 없습니다!",ephemeral=True)
            return

        battle_ref = db.reference("레이드/레이드진행여부")
        is_battle = battle_ref.get() or {}
        if is_battle:
            warnembed = discord.Embed(title="실패",color = discord.Color.red())
            warnembed.add_field(name="",value="다른 레이드가 진행중입니다! ❌")
            await interaction.followup.send(embed = warnembed)
            return
        
        ref_boss_list = db.reference("레이드/보스목록")
        all_boss_order = ref_boss_list.get()  # 전체 보스 순서 예: ["스우", "브라움", "카이사", "팬텀"]

        ref_boss_order = db.reference("레이드/순서")
        today_index = ref_boss_order.get()  # 예: 2

        # 오늘의 4마리 보스 추출 (시계방향 순환)
        today_bosses = []
        for i in range(4):
            index = (today_index + i) % len(all_boss_order)
            today_bosses.append(all_boss_order[index])

        # 현재 보스
        ref_current_boss = db.reference("레이드/현재 레이드 보스")
        current_boss = ref_current_boss.get()

        # 시계 반대 방향 순서로 탐색
        start_index = today_bosses.index(current_boss)
        search_order = today_bosses[start_index::-1] + today_bosses[:start_index:-1]  # 역순

        # 초기화
        found_boss = None
        remain_HP = weapon_data_challenger['내구도']
        raid_damage = 0

        for boss_name in search_order:
            ref_boss_log = db.reference(f"레이드/내역/{nickname}/{boss_name}")
            boss_log = ref_boss_log.get()
            if boss_log:
                found_boss = boss_name
                remain_HP = boss_log.get("남은내구도", weapon_data_challenger['내구도'])
                raid_damage = boss_log.get("대미지", 0)
                break  # 가장 최근 도전 보스 찾았으니 탈출

        result = False
        if weapon_data_opponent.get("내구도", 0) <= 0:
            warn_embed = discord.Embed(
                title="격파 완료",
                description="오늘의 레이드보스가 모두 토벌되었습니다!",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=warn_embed, ephemeral=True)
            return

        result = False
        ref_item = db.reference(f"무기/아이템/{nickname}")
        item_data = ref_item.get() or {}
        raid_refresh = item_data.get("레이드 재도전", 0)
        if not remain_HP: # 남은 내구도가 없다면? 재도전권이 있어야함
            if raid_refresh: # 레이드 재도전권 있다면?
                if found_boss == current_boss_name: # 재도전권은 도전한 보스와 현재 보스가 같을때만 사용 가능
                    retry_embed = discord.Embed(
                        title="레이드 재도전🔄 ",
                        description="이미 레이드를 참여하셨습니다.",
                        color=discord.Color.orange()
                    )
                    retry_embed.add_field(
                        name="도전한 보스",
                        value=f"**{found_boss} **",
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

                                refraid = db.reference(f"레이드/내역/{interaction.user.name}/{boss_name}")
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
                else:
                    # 이전 보스와 현재 보스가 다르면 사용 불가!
                    warn_embed = discord.Embed(
                        title="도전 불가",
                        description="최근 기록이 다른 레이드보스에 도전한 기록입니다!",
                        color=discord.Color.red()
                    )
                    warn_embed.add_field(name="도전한 보스", value=f"**{found_boss}**")
                    warn_embed.add_field(name="현재 보스", value=f"**{current_boss_name}**")
                    await interaction.followup.send(embed=warn_embed, ephemeral=True)
                    return
            else: # 재도전권 없다면
                warn_embed = discord.Embed(
                    title="도전 불가",
                    description="내구도를 모두 소모했습니다!",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=warn_embed, ephemeral=True)
                return     

        # 초기화
        remain_HP = weapon_data_challenger['내구도']

        for boss_name in search_order:
            ref_boss_log = db.reference(f"레이드/내역/{nickname}/{boss_name}")
            boss_log = ref_boss_log.get()
            if boss_log:
                found_boss = boss_name
                remain_HP = boss_log.get("남은내구도", weapon_data_challenger['내구도'])
                break  # 가장 최근 도전 보스 찾았으니 탈출

        battle_ref.set(True)
        # 임베드 생성
        embed = discord.Embed(
            title=f"{interaction.user.display_name}의 {weapon_data_opponent.get('이름', '')} 레이드",
            description="대결이 시작되었습니다!",
            color=discord.Color.blue()  # 원하는 색상 선택
        )
        if result:
            msg = await interaction.channel.send(embed = embed)
        else:
            msg = await interaction.followup.send(embed=embed)
        await Battle(channel = interaction.channel,challenger_m = interaction.user, boss = current_boss_name, raid = True, remain_HP = remain_HP, practice = False)
        battle_ref.set(False)
        await msg.delete()

    @app_commands.command(name="현황_레이드", description="현재 레이드 현황을 보여줍니다.")
    async def raid_status(self, interaction: discord.Interaction):
        await interaction.response.defer()

        max_reward_per_boss = 15
        ref_boss_list = db.reference("레이드/보스목록")
        all_boss_order = ref_boss_list.get()  # 예: ["스우", "브라움", "카이사", "팬텀", ...]

        ref_boss_order = db.reference("레이드/순서")
        today = ref_boss_order.get()  # 예: 2

        # 시계방향 순환하며 4마리 선택
        today_bosses = []
        for i in range(4):
            index = (today + i) % len(all_boss_order)
            today_bosses.append(all_boss_order[index])

        ref_current_boss = db.reference("레이드/현재 레이드 보스")
        current_boss = ref_current_boss.get()

        # 보스 순서 문자열 생성
        boss_display = []
        for boss in today_bosses:
            if boss == current_boss:
                boss_display.append(f"**[{boss}]**")
            else:
                boss_display.append(f"[{boss}]")
        boss_order_str = " ➝ ".join(boss_display)

        # 유저별 누적 대미지 + 남은 내구도 조회
        ref_all_logs = db.reference("레이드/내역")
        all_logs = ref_all_logs.get() or {}

        user_total_damage = {}
        user_last_hp = {}

        for username, bosses in all_logs.items():
            total_damage = 0
            for boss_name, record in bosses.items():
                total_damage += record.get("대미지", 0)
                if "남은내구도" in record:
                    user_last_hp[username] = record["남은내구도"]
            if total_damage > 0:
                user_total_damage[username] = total_damage

        sorted_users = sorted(user_total_damage.items(), key=lambda x: x[1], reverse=True)

        # 랭킹 정리
        rankings = []
        for i, (username, total_dmg) in enumerate(sorted_users, start=1):
            remain_hp = user_last_hp.get(username)
            hp_text = f" [:heart: {remain_hp}]" if remain_hp is not None else ""
            rankings.append(f"{i}위: {username} - {total_dmg} 대미지{hp_text}")

        # 현재 보스 정보
        ref_boss_data = db.reference(f"레이드/보스/{current_boss}")
        boss_data = ref_boss_data.get() or {}
        cur_dur = boss_data.get("내구도", 0)
        total_dur = boss_data.get("총 내구도", 0)

        # 현재 보스 체력 비율
        remain_durability_ratio = round(cur_dur / total_dur * 100, 2) if total_dur else 0

        # 보상 계산
        current_index = today_bosses.index(current_boss) if current_boss in today_bosses else 0
        base_reward = max_reward_per_boss * current_index
        partial_reward = 0
        if total_dur > 0:
            durability_ratio = (total_dur - cur_dur) / total_dur
            partial_reward = math.floor(max_reward_per_boss * durability_ratio)

        total_reward = base_reward + partial_reward

        # 임베드 생성
        embed = discord.Embed(title="🎯 레이드 현황", color=0x00ff00)
        embed.add_field(name="현재 레이드 보스", value=boss_order_str, inline=False)
        embed.add_field(
            name="레이드 보스의 현재 체력",
            value=f"[{cur_dur}/{total_dur}] {remain_durability_ratio}%",
            inline=False
        )
        embed.add_field(
            name="현재 대미지",
            value="\n".join(rankings) if rankings else "기록 없음",
            inline=False
        )
        embed.add_field(
            name="보상 현황",
            value=f"강화재료 **{total_reward}개** 지급 예정!",
            inline=False
        )

        await interaction.followup.send(embed=embed)

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
    @app_commands.describe(층수 = "도전할 층수를 선택하세요")
    async def infinity_tower(self, interaction: discord.Interaction, 층수 : app_commands.Range[int, 1] = None):
        await interaction.response.defer()
        nickname = interaction.user.name

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
        
        if 층수 is None:
            target_floor = current_floor
            
        else:
            if 층수 < current_floor: # 현재 층수보다 낮은 곳을 입력한다면?
                warnembed = discord.Embed(title="실패",color = discord.Color.red())
                warnembed.add_field(name="",value="다음 층수보다 낮은 층수를 입력했습니다! ❌")
                await interaction.followup.send(embed = warnembed)
                return
            target_floor = 층수

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
        battle_ref.set(True)
       

        # ====================  [미션]  ====================
        # 일일미션 : 탑 1회 도전
        ref_mission = db.reference(f"미션/미션진행상태/{nickname}/일일미션/탑 1회 도전")
        mission_data = ref_mission.get() or {}
        mission_bool = mission_data.get('완료', False)
        if not mission_bool:
            ref_mission.update({"완료": True})
            print(f"{interaction.user.display_name}의 [탑 1회 도전] 미션 완료")

        # ====================  [미션]  ====================
                    
        # 임베드 생성
        embed = discord.Embed(
            title=f"{interaction.user.display_name}의 탑 등반({target_floor}층)",
            description="전투가 시작되었습니다!",
            color=discord.Color.blue()  # 원하는 색상 선택
        )
        msg = await interaction.followup.send(embed=embed)
        await Battle(channel = interaction.channel,challenger_m = interaction.user, tower = True, tower_floor=target_floor)

        battle_ref = db.reference("승부예측/대결진행여부")
        battle_ref.set(False)
        await msg.delete()

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

            challenger_insignia = get_user_insignia_stat(상대.name, role="challenger")

            win_count = 0
            for i in range(1000):
                result = await Battle(channel = interaction.channel,challenger_m= 상대, raid = False, practice = False, simulate = True, skill_data = skill_data_firebase, wdc = weapon_data_challenger, wdo = weapon_data_opponent, scd = skill_common_data, insignia=challenger_insignia)
                if result:  # True면 승리
                    win_count += 1

            result_embed = discord.Embed(title="시뮬레이션 결과",color = discord.Color.blue())
            win_probability = round((win_count / 1000) * 100, 2)
            weapon_types = ["대검","스태프-화염", "조총", "스태프-냉기", "태도", "활", "스태프-신성", "단검", "낫", "창"]
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
        msg = await interaction.response.send_message(embed=embed)
        await Battle(channel = interaction.channel,challenger_m = 상대, tower = True, practice= True, tower_floor= 층수)

        battle_ref = db.reference("승부예측/대결진행여부")
        battle_ref.set(False)
        await msg.delete()

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

            challenger_insignia = get_user_insignia_stat(상대1.name, role="challenger")
            opponent_insignia = get_user_insignia_stat(상대2.name, role="opponent")

            # 병합하려면:
            insignia = {
                **challenger_insignia,
                **opponent_insignia
            }

            win_count = 0
            for i in range(1000):
                result = await Battle(channel = interaction.channel,challenger_m= 상대1, opponent_m = 상대2, raid = False, practice = False, simulate = True, skill_data = skill_data_firebase, wdc = weapon_data_challenger, wdo = weapon_data_opponent, scd = skill_common_data, insignia = insignia)
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
        msg = await interaction.followup.send(embed=embed)
        await Battle(channel = interaction.channel,challenger_m= 상대1, opponent_m = 상대2, raid = False, practice = False)

        battle_ref = db.reference("승부예측/대결진행여부")
        battle_ref.set(False)
        await msg.delete()

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

            challenger_insignia = get_user_insignia_stat(상대1.name, role="challenger")

            damage_total = 0
            damage_results = []
            for i in range(1000):
                result = await Battle(channel = interaction.channel,challenger_m = 상대1, boss = boss_name, raid = True, practice = True, simulate = True, skill_data = skill_data_firebase, wdc = weapon_data_challenger, wdo = weapon_data_opponent, scd = skill_common_data, insignia=challenger_insignia)
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
        msg = await interaction.followup.send(embed=embed)
        await Battle(channel = interaction.channel,challenger_m = 상대1, boss = boss_name, raid = True, practice = True)

        battle_ref = db.reference("승부예측/대결진행여부")
        battle_ref.set(False)
        await msg.delete()

    @app_commands.command(name="거울", description="자신과 같은 강화 수치를 가진 상대를 만나 전투합니다.")
    async def Mirror(self, interaction: discord.Interaction):
        await interaction.response.defer()

        user_name = interaction.user.name
        ref_weapon = db.reference(f"무기/유저/{user_name}")
        weapon_data_challenger = ref_weapon.get() or {}

        if not weapon_data_challenger.get("이름"):
            await interaction.followup.send("무기를 가지고 있지 않습니다! 무기를 생성해주세요!", ephemeral=True)
            return

        ref_mirror = db.reference(f"무기/거울/{interaction.user.name}")
        mirror_data = ref_mirror.get() or {}
        mirror_bool = mirror_data.get("참여 여부", False)

        if mirror_bool:
            win_count = mirror_data.get("승수", 0)

            final_embed = discord.Embed(
                title="📉 최종 결과",
                description=f"오늘 이미 도전을 완료하셨습니다!\n\n🏁 **{win_count}승 / 10승**\n탑코인 **{win_count}개** 지급 완료!",
                color=discord.Color.gold()
            )
            final_embed.set_footer(text="같은 날에는 한 번만 도전할 수 있습니다.")
            
            await interaction.followup.send(embed=final_embed, ephemeral=True)
            return
        else:
            ref_mirror.update({
                "참여 여부": True,
                "승수": 0  # 아직 승수 없음
            })
            # ====================  [미션]  ====================
            # 일일미션 : 거울의 전장 도전
            ref_mission = db.reference(f"미션/미션진행상태/{interaction.user.name}/일일미션/거울의 전장 도전")
            mission_data = ref_mission.get() or {}
            mission_bool = mission_data.get('완료',0)
            if not mission_bool:
                ref_mission.update({"완료": True})
                print(f"{interaction.user.display_name}의 [거울의 전장 도전] 미션 완료")

            # ====================  [미션]  ====================

        # 기존 강화 내역
        original_enhance_log = weapon_data_challenger.get("강화내역", {})
        total_enhancement = sum(original_enhance_log.values())

        # 강화 보정 적용
        ref_weapon_enhance = db.reference(f"무기/강화")
        enhance_types_dict = ref_weapon_enhance.get() or {}
        enhance_types = list(enhance_types_dict.keys())  # dict_keys -> list 변환

        weapon_type = weapon_data_challenger.get("무기타입", "")
        if weapon_type in attack_weapons:
            enhance_types = [etype for etype in enhance_types_dict.keys() if etype != "스킬 강화"]
        elif weapon_type in skill_weapons:
            enhance_types = [etype for etype in enhance_types_dict.keys() if etype != "공격 강화"]

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
            name=f"{interaction.user.display_name}의 거울의 전장",
            type=discord.ChannelType.public_thread
        )

        # 임베드 생성
        embed = discord.Embed(
            title=f"{interaction.user.display_name}의 거울의 전장",
            description="도전이 시작되었습니다!",
            color=discord.Color.blue()  # 원하는 색상 선택
        )

        challenger_insignia = get_user_insignia_stat(user_name, role="challenger")
        opponent_insignia = get_user_insignia_stat(user_name, role="opponent")

        insignia = {
            **challenger_insignia,
            **opponent_insignia
        }
        result_view = ResultButton(interaction.user, weapon_data_challenger, weapon_data_opponent, skill_data_firebase, insignia)
        msg = await thread.send(
            content="💡 강화된 무기 비교 및 시뮬레이션 결과를 확인해보세요!",
            embeds=[
                get_stat_embed(weapon_data_challenger, weapon_data_opponent),
                get_enhance_embed(weapon_data_challenger, weapon_data_opponent)
            ],
            view=result_view
        )
        result_view.message = msg  # 메시지 저장

        embed_msg = await interaction.followup.send(embed = embed, ephemeral=True)
        await asyncio.sleep(10)
        await embed_msg.delete()

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
                f"계승 수치를 모두 제거하고, 추가 강화 수치만큼 **특수 연마제**를 연성합니다."
            )

        # 버튼 뷰 구성
        view = RuneUseButton(user=interaction.user, rune_name=룬, nickname=nickname, item_ref=ref_item, item_data=item_data)
        await interaction.followup.send(embed=rune_embed, view=view)

    @app_commands.command(name="각인", description="인장을 확인하고 장착 또는 해제하거나 인장을 개봉합니다.")
    @app_commands.choices(대상=[
        Choice(name='불완전한 인장', value='불완전한 인장'),
        Choice(name='강화', value = '강화')
    ])
    @app_commands.describe(대상="사용할 기능을 선택하세요")
    async def handle_insignia(self, interaction: discord.Interaction, 대상: str = None):
        await interaction.response.defer(thinking=True)
        nickname = interaction.user.name

        # ---------------- [불완전한 인장 개봉 로직] ----------------
        if 대상 == "불완전한 인장":
            ref_items = db.reference(f"무기/아이템/{nickname}")
            item_data = ref_items.get() or {}
            count = item_data.get("불완전한 인장", 0)

            if count < 1:
                await interaction.followup.send("불완전한 인장이 없습니다.", ephemeral=True)
                return

            # 불완전한 인장 1개 차감
            ref_items.update({"불완전한 인장": count - 1})

            # 무작위 인장 지급
            new_insignia = random.choice(insignia_items)
            give_item(nickname, new_insignia, 1)
            embed = discord.Embed(
                title="✨ 인장 획득!",
                description=f"{interaction.user.mention}님이 **[{new_insignia}]** 인장을 획득했습니다!",
                color=discord.Color.gold()
            )
            await interaction.followup.send(embed=embed)
            return
        # ------------------------------------------------------

        # ---------------- [강화 로직] ----------------
        if 대상 == "강화":
            ref_insignia = db.reference(f"무기/각인/유저/{nickname}")
            insignia_inventory = ref_insignia.get() or {}

            if not insignia_inventory:
                await interaction.followup.send("보유 중인 인장이 없습니다.", ephemeral=True)
                return

            # 강화할 수 있는 인장을 SelectOption으로 구성
            options = []
            for name, data in insignia_inventory.items():
                level = data.get("레벨", 1)
                count = data.get("개수", 1) - 1

                if level < 5:
                    required = level
                    total_needed = required
                    label = f"{name} (Lv.{level})"
                    desc = f"필요: {total_needed}개 / 추가 보유: {count}개"
                    options.append(discord.SelectOption(label=label, description=desc, value=name))

            if not options:
                await interaction.followup.send("모든 인장이 이미 최대 레벨입니다.", ephemeral=True)
                return

            class InsigniaSelect(discord.ui.Select):
                def __init__(self, user, options, ref_insignia, insignia_inventory):
                    self.ref_insignia = ref_insignia
                    self.insignia_inventory = insignia_inventory
                    self.user = user

                    super().__init__(
                        placeholder="강화할 인장을 선택하세요",
                        options=options,
                        min_values=1,
                        max_values=1
                    )

                async def callback(self, interaction: discord.Interaction):
                    if self.user != interaction.user:
                        await interaction.response.send_message("본인만 조작할 수 있습니다.", ephemeral=True)
                        return
                    
                    selected_insignia = self.values[0]
                    data = self.insignia_inventory[selected_insignia]
                    level = data.get("레벨", 1)
                    count = data.get("개수", 1) - 1

                    results = []

                    if level >= 5:
                        results.append(f"❌ **[{selected_insignia}]** : 이미 최대 레벨입니다.")
                    else:
                        required = level
                        total_needed = required

                        if count >= total_needed:
                            new_level = level + 1
                            new_count = count - required + 1

                            self.ref_insignia.child(selected_insignia).update({
                                "레벨": new_level,
                                "개수": new_count
                            })

                            results.append(f"✅ **[{selected_insignia}]** : Lv.{level} → Lv.{new_level} 강화 성공! (남은 개수: {new_count - 1})")
                        else:
                            results.append(f"⚠️ **[{selected_insignia}]** : 강화에 필요한 개수 부족 ({count}/{total_needed})")

                    await interaction.response.edit_message(
                        content = "",
                        embed=discord.Embed(
                            title="🛠 인장 강화 결과",
                            description="\n".join(results),
                            color=discord.Color.gold()
                        ),
                        view=None
                    )

            class SelectView(discord.ui.View):
                def __init__(self, user, options, ref_insignia, insignia_inventory, timeout=60):
                    super().__init__(timeout=timeout)
                    self.add_item(InsigniaSelect(user, options, ref_insignia, insignia_inventory))

            await interaction.followup.send("🪶 강화할 인장을 선택하세요:", view=SelectView(interaction.user, options, ref_insignia, insignia_inventory), ephemeral=True)
            return
        # ------------------------------------------------------

        ref_item_insignia = db.reference(f"무기/각인/유저/{nickname}")
        ref_user_insignia = db.reference(f"무기/유저/{nickname}/각인")
        inventory = ref_item_insignia.get() or {}
        equipped = ref_user_insignia.get() or []

        if not inventory:
            await interaction.followup.send("보유한 인장이 없습니다.", ephemeral=True)
            return

        embed = discord.Embed(title="🔹 인장 관리", color=discord.Color.blue())

        desc_lines = []
        for i in range(3):
            name = equipped[i] if i < len(equipped) and equipped[i] else "-"
            if name and name != "-" and name in inventory:
                data = inventory[name]
                level = data.get("레벨", "N/A")
                ref_item_insignia_stat = db.reference(f"무기/각인/스탯/{name}")
                insignia_stat = ref_item_insignia_stat.get() or {}
                stat = insignia_stat.get("주스탯", "N/A")
                value = insignia_stat.get("초기 수치",0) + insignia_stat.get("증가 수치", 0) * level

                if name in percent_insignias:
                    value = f"{float(value) * 100:.0f}%"
                else:
                    value = f"{value}"

                desc_lines.append(f"{i+1}번: {name} (Lv.{level}, {stat} +{value})")
            else:
                desc_lines.append(f"{i+1}번: -")

        embed.add_field(name="📌 장착 중", value="\n".join(desc_lines), inline=False)
        embed.set_footer(text="버튼을 눌러 인장을 장착하거나 해제하세요.")

        view = InsigniaView(
            user=interaction.user,
            nickname=nickname,
            inventory=inventory,
            equipped=equipped,
            ref_user_insignia=ref_user_insignia,
        )
        msg = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        await asyncio.sleep(120)
        await msg.delete()

    @app_commands.command(name="인장", description="모든 인장의 종류와 효과를 확인합니다.")
    async def show_insignias(self, interaction: discord.Interaction):
        # 경로: /무기/각인/스탯
        ref = db.reference('/무기/각인/스탯')
        insignia_data = ref.get()

        # 각인 설명 텍스트 생성
        insignia_info = {}
        for name, data in insignia_data.items():
            stat = data.get('주스탯', '스탯 없음')
            base = data.get('초기 수치', 0)
            per_level = data.get('증가 수치', 0)
            
            is_percent = name in percent_insignias
            if is_percent:
                base *= 100
                per_level *= 100

            if base == 0:
                description = f"**{stat}** `레벨당 {per_level:.0f}{'%' if is_percent else ''}`"
            else:
                description = f"**{stat}** `{base:.0f}{'%' if is_percent else ''} + 레벨당 {per_level:.0f}{'%' if is_percent else ''}`"

            insignia_info[name] = description

        embed = discord.Embed(title="📜 인장 종류 및 능력치", color=discord.Color.dark_teal())

        for k, v in insignia_info.items():
            embed.add_field(name= "", value = f"🔹 {k}: {v}",inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    # await bot.add_cog(
    #     hello(bot),
    #     guilds=[Object(id=298064707460268032)]
    # )
    await bot.add_cog(hello(bot))