import discord
import random
import asyncio
import math
from firebase_admin import db
from .status import apply_status_for_turn, update_status, remove_status_effects
from .battle_utils import *
from .skill_handler import process_all_skills, process_on_hit_effects, use_skill
from .skills import *


async def Battle(channel, challenger_m, opponent_m = None, boss = None, raid = False, practice = False, tower = False, tower_floor = 1, raid_ended = False, simulate = False, skill_data = None, wdc = None, wdo = None, scd = None):
    weapon_battle_thread = None
    if simulate:
        skill_data_firebase = skill_data
    else:
        ref_skill_data = db.reference("무기/스킬")
        skill_data_firebase = ref_skill_data.get() or {}

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

        remove_status_effects(attacker, skill_data_firebase)
        update_status(attacker)  # 공격자의 상태 업데이트 (은신 등)

        skill_message = ""
        if reloading:
            return 0, False, False, False, ""
        
        if skills:
            damage, skill_message, critical_bool = use_skill(attacker, defender, skills, evasion, reloading, skill_data_firebase)
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
            message, damage = second_skin(defender,passive_skill_level, 1, skill_data_firebase)
            skill_message += message
            base_damage += damage

        if attacker["Weapon"] == "창": #창 적정거리 추가 대미지
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
        "DefenseIgnore": 0,
        "Evasion" : 0,
        "DamageEnhance" : 0, # 피해 증폭
        "DamageReduction" : 0, # 피해 감소
        "Tenacity" : 0,
        "Id": 0, # Id를 통해 도전자와 상대 파악 도전자 = 0, 상대 = 1
        "Accuracy": weapon_data_challenger.get("명중", 0),
        "BaseAccuracy": weapon_data_challenger.get("명중", 0),
        "Defense": weapon_data_challenger.get("방어력", 0),
        "Skills": challenger_merged_skills,
        "Status" : {}
    }

    if not simulate:
        # 유저 각인 정보 가져오기
        ref_user_insignia = db.reference(f"무기/유저/{challenger_m.name}/각인")  # 예: 'nickname' 변수는 해당 유저명
        user_insignia = ref_user_insignia.get() or {}

        # 0,1,2 슬롯 중 인장 찾기
        if isinstance(user_insignia, dict):
            # 딕셔너리일 경우 한 번만 슬롯 돌기
            for slot_key in ['0', '1', '2']:
                insignia_name = user_insignia.get(slot_key, "")
                if not insignia_name:
                    continue
                
                # 인장 상세 정보 가져오기
                ref_insignia_detail = db.reference(f"무기/각인/{challenger_m.name}/{insignia_name}")
                insignia_detail = ref_insignia_detail.get() or {}

                level = insignia_detail.get("레벨", 1)
                base_value = insignia_detail.get("초기 수치", 0)
                increase_per_level = insignia_detail.get("증가 수치", 0)

                total_bonus = base_value + (increase_per_level * level)

                if insignia_name == "약점 간파":
                    challenger["CritChance"] += total_bonus
                elif insignia_name == "꿰뚫는 집념":
                    challenger["DefenseIgnore"] += total_bonus
                elif insignia_name == "강철의 맹세":
                    challenger["DamageReduction"] += total_bonus
                elif insignia_name == "불굴의 심장":
                    challenger["Tenacity"] += total_bonus
                elif insignia_name == "타오르는 혼":
                    challenger["DamageEnhance"] += total_bonus
                elif insignia_name == "바람의 잔상":
                    challenger["Evaison"] += total_bonus

        elif isinstance(user_insignia, list):
            # 리스트일 경우에도 한 번만 슬롯 돌기
            for slot_key in [0, 1, 2]:
                insignia_name = user_insignia[slot_key] if slot_key < len(user_insignia) else ""
                if not insignia_name:
                    continue

                ref_insignia_detail = db.reference(f"무기/각인/{challenger_m.name}/{insignia_name}")
                insignia_detail = ref_insignia_detail.get() or {}

                level = insignia_detail.get("레벨", 1)
                base_value = insignia_detail.get("초기 수치", 0)
                increase_per_level = insignia_detail.get("증가 수치", 0)

                total_bonus = base_value + (increase_per_level * level)

                if insignia_name == "약점 간파":
                    challenger["CritChance"] += total_bonus
                elif insignia_name == "꿰뚫는 집념":
                    challenger["DefenseIgnore"] += total_bonus
                elif insignia_name == "강철의 맹세":
                    challenger["DamageReduction"] += total_bonus
                elif insignia_name == "불굴의 심장":
                    challenger["Tenacity"] += total_bonus
                elif insignia_name == "타오르는 혼":
                    challenger["DamageEnhance"] += total_bonus
                elif insignia_name == "바람의 잔상":
                    challenger["Evasion"] += total_bonus
    
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
        "DefenseIgnore": 0,
        "Evasion" : 0,
        "DamageEnhance" : 0,
        "DamageReduction" : 0,
        "Tenacity" : 0,
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
                    name=f"{challenger_m.display_name}의 탑 등반 모의전",
                    type=discord.ChannelType.public_thread
                )
            else:
                weapon_battle_thread = await channel.create_thread(
                    name=f"{challenger_m.display_name}의 탑 등반",
                    type=discord.ChannelType.public_thread
                )
        else:
            weapon_battle_thread = await channel.create_thread(
                name=f"{challenger_m.display_name} vs {opponent_m.display_name} 무기 대결",
                type=discord.ChannelType.public_thread
            )

    # 챌린저 무기 스탯 정보 추가
    challenger_embed = discord.Embed(title="🟦 도전자 스탯", color=discord.Color.blue())

    challenger_embed.add_field(
        name=f"[{challenger['name']}](+{weapon_data_challenger.get('강화', 0)}) [{challenger['Weapon']}]",
        value=(
            f"대미지        : `{round(challenger['Attack'] * calculate_accuracy(challenger['Accuracy']))} ~ {challenger['Attack']}`\n"
            f"내구도        : `{challenger['HP']}`\n"
            f"공격력        : `{challenger['Attack']}`\n"
            f"스킬 증폭     : `{challenger['Spell']}`\n"
            f"치명타 확률   : `{round(challenger['CritChance'] * 100, 2)}%`\n"
            f"치명타 대미지 : `{round(challenger['CritDamage'] * 100, 2)}%`\n"
            f"스피드        : `{challenger['Speed']}` (회피율: `{round(calculate_evasion(challenger['Speed']) * 100, 2)}%`)\n"
            f"명중          : `{challenger['Accuracy']}` (명중률: `{round(calculate_accuracy(challenger['Accuracy']) * 100, 2)}%`)\n"
            f"방어력        : `{challenger['Defense']}` (피해 감소: `{round(calculate_damage_reduction(challenger['Defense']) * 100, 2)}%`)\n"
        ),
        inline=False
    )

    # 스킬 정보 따로 아래에 추가
    skills_text_challenger = "\n".join(
        f"• {skill_name} Lv{skill_data['레벨']}" for skill_name, skill_data in challenger['Skills'].items()
    )
    challenger_embed.add_field(
        name="📘 스킬",
        value=skills_text_challenger or "없음",
        inline=False
)

    # 상대 스탯 임베드
    opponent_embed = discord.Embed(title="🟥 상대 스탯", color=discord.Color.red())

    opponent_embed.add_field(
        name=f"[{opponent['name']}](+{weapon_data_opponent.get('강화', 0)}) [{opponent['Weapon']}]",
        value=(
            f"대미지        : `{round(opponent['Attack'] * calculate_accuracy(opponent['Accuracy']))} ~ {opponent['Attack']}`\n"
            f"내구도        : `{opponent['HP']}`\n"
            f"공격력        : `{opponent['Attack']}`\n"
            f"스킬 증폭     : `{opponent['Spell']}`\n"
            f"치명타 확률   : `{round(opponent['CritChance'] * 100, 2)}%`\n"
            f"치명타 대미지 : `{round(opponent['CritDamage'] * 100, 2)}%`\n"
            f"스피드        : `{opponent['Speed']}` (회피율: `{round(calculate_evasion(opponent['Speed']) * 100, 2)}%`)\n"
            f"명중          : `{opponent['Accuracy']}` (명중률: `{round(calculate_accuracy(opponent['Accuracy']) * 100, 2)}%`)\n"
            f"방어력        : `{opponent['Defense']}` (피해 감소: `{round(calculate_damage_reduction(opponent['Defense']) * 100, 2)}%`)\n"
        ),
        inline=False
    )

    # 스킬 정보 따로 아래에 깔끔하게 추가
    skills_text_opponent = "\n".join(
        f"• {skill_name} Lv{skill_data['레벨']}" for skill_name, skill_data in opponent['Skills'].items()
    )
    opponent_embed.add_field(
        name="📘 스킬",
        value=skills_text_opponent or "없음",
        inline=False
)

    if not simulate:
        await weapon_battle_thread.send(embed=challenger_embed)
        await weapon_battle_thread.send(embed=opponent_embed)

    def create_bar(value: int, max_val: int = 50, bar_length: int = 10):
        filled_len = round((value / max_val) * bar_length)
        return "■" * filled_len

    embed = discord.Embed(title="⚔️ 무기 강화 내역", color=discord.Color.green())

    # 강화 항목 표시 이름 매핑
    enhance_name_map = {
        "공격 강화": "공격", "방어 강화": "방어", "속도 강화": "속도",
        "치명타 확률 강화": "치확", "치명타 대미지 강화": "치댐",
        "밸런스 강화": "균형", "스킬 강화": "스증", "명중 강화": "명중", "내구도 강화": "내구"
    }

    # 챌린저 무기 스탯 정보 추가
    challenger_weapon_enhancement = ""
    for enhancement, count in weapon_data_challenger.get('강화내역', {}).items():
        label = enhance_name_map.get(enhancement, enhancement).ljust(4)
        bar = create_bar(count)
        challenger_weapon_enhancement += f"+{str(count).rjust(2)} {bar.ljust(10)} {label}\n"

    embed.add_field(
        name=f"[{challenger['name']}](+{weapon_data_challenger.get('강화', 0)})",
        value=f"```ansi\n{challenger_weapon_enhancement if challenger_weapon_enhancement else '강화 내역 없음'}\n```",
        inline=False
    )

    # 상대 무기 스탯 정보 추가
    opponent_weapon_enhancement = ""
    for enhancement, count in weapon_data_opponent.get('강화내역', {}).items():
        label = enhance_name_map.get(enhancement, enhancement).ljust(4)
        bar = create_bar(count)
        opponent_weapon_enhancement += f"+{str(count).rjust(2)} {bar.ljust(10)} {label}\n"

    embed.add_field(
        name=f"[{opponent['name']}](+{weapon_data_opponent.get('강화', 0)})",
        value=f"```ansi\n{opponent_weapon_enhancement if opponent_weapon_enhancement else '강화 내역 없음'}\n```",
        inline=False
    )

    if not simulate:
        await weapon_battle_thread.send(embed=embed)
    
    turn = 0
    if raid: # 레이드 시 처음 내구도를 저장
        first_HP = opponent['HP']
        if boss == "브라움":
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

        if "일섬" in attacker["Status"]:
            if attacker["Status"]["일섬"]["duration"] == 1:
                issen_data = skill_data_firebase['일섬']['values']
                skill_level = defender['Skills']['일섬']['레벨']
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
            remove_status_effects(attacker, skill_data_firebase)
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
            remove_status_effects(attacker, skill_data_firebase)
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
        acceleration_chance = speed // 5  # 예: 스피드 50이면 10%
        overdrive_chance = max(0, (speed - 200) // 10)  # 초가속: 200 초과부터 10당 1%

        skill_names = list(attacker["Skills"].keys())
        used_skill = []
        skill_attack_names = []
        result_message = ""
        cooldown_message = ""

        for skill, cooldown_data in attacker["Skills"].items():
            if cooldown_data["현재 쿨타임"] > 0:
                if acceleration_chance > 0 and random.randint(1, 100) <= acceleration_chance:
                    # 기본 가속 성공 시
                    cooldown_reduction = 1
                    overdrive_triggered = False

                    # 초가속 판정
                    if overdrive_chance > 0 and random.randint(1, 100) <= overdrive_chance:
                        cooldown_reduction += 1
                        overdrive_triggered = True

                    # 쿨타임 감소 적용
                    attacker["Skills"][skill]["현재 쿨타임"] = max(0, cooldown_data["현재 쿨타임"] - cooldown_reduction)

                    # 메시지 처리
                    if overdrive_triggered:
                        result_message += f"⚡ {attacker['name']}의 **초가속!** {skill}의 쿨타임이 **{cooldown_reduction} 감소**했습니다!\n"
                    else:
                        result_message += f"💨 {attacker['name']}의 가속! {skill}의 쿨타임이 1 감소했습니다!\n"

                    # 헤드샷이라면 장전 지속시간도 감소
                    if skill == "헤드샷" and "장전" in attacker["Status"]:
                        attacker["Status"]["장전"]["duration"] -= cooldown_reduction
                        if attacker["Status"]["장전"]["duration"] <= 0:
                            del attacker["Status"]["장전"]
        
        slienced = False
        if '침묵' in attacker['Status']:
            slienced = True

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
                    result_message += invisibility(attacker,skill_level,skill_data_firebase)
                    used_skill.append(skill_name)
            else:
                cooldown_message += f"⏳{skill_name}의 남은 쿨타임 : {skill_cooldown_current}턴\n"

        evasion = False # 회피 

        accuracy = calculate_accuracy(attacker["Accuracy"]) # 1 - 명중률 수치만큼 빗나갈 확률 상쇄 가능
        speed_evasion = calculate_evasion(defender["Speed"])
        if random.random() < (defender["Evasion"] + speed_evasion) * (1 - accuracy): # 회피
        # if random.random() > accuracy:
            evasion = True
        else:
            attacked = True

        reloading = False
        if "장전" in attacker['Status']: 
            result_message += f"장전 중! ({attacker['Status']['장전']['duration']}턴 남음!)\n"
            # 장전 상태일 경우 공격 불가
            reloading = True
        
        battle_embed = discord.Embed(title=f"{attacker['name']}의 공격!⚔️", color=discord.Color.blue())
        
        
        skill_message, used_skill, skill_attack_names, cooldown_messages = process_all_skills(
            attacker, defender, slienced, evasion, attacked,
            skill_data_firebase
        )

        result_message += skill_message


        if attacked:
            result_message, used_skill = process_on_hit_effects(
                attacker, defender, evasion, skill_attack_names, used_skill, result_message,
                skill_data_firebase, battle_embed
            )
        
        if skill_attack_names or attacked: # 공격시 상대의 빙결 상태 해제
            if skill_attack_names != ['명상'] and not evasion: # 명상만 썼을 경우, 회피했을 경우 제외!
                if '빙결' in defender['Status']:
                    del defender['Status']['빙결']
                    battle_embed.add_field(name="❄️빙결 상태 해제!", value = f"공격을 받아 빙결 상태가 해제되었습니다!\n")

        # 공격 처리
        if skill_attack_names: # 공격 스킬 사용 시
            battle_embed.title = f"{attacker['name']}의 스킬 사용!⚔️"
            if attacker['Id'] == 0: # 도전자 공격
                battle_embed.color = discord.Color.blue()
            elif attacker['Id'] == 1: # 상대 공격
                battle_embed.color = discord.Color.red()
            damage, critical, dist, evade, skill_message = await attack(attacker, defender, evasion, reloading, skill_attack_names)
            result_message += skill_message
        else: # 일반 공격 시
            battle_embed.title = f"{attacker['name']}의 공격!⚔️"
            if attacker['Id'] == 0: # 도전자 공격
                battle_embed.color = discord.Color.blue()
            elif attacker['Id'] == 1: # 상대 공격
                battle_embed.color = discord.Color.red() 
            damage, critical, dist, evade, skill_message = await attack(attacker, defender, evasion, reloading, skill_attack_names)
            result_message += skill_message


        if cooldown_messages:
            result_message += "\n" + "\n".join(cooldown_messages)
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
        else:
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

