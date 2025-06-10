import discord
import random
import asyncio
from datetime import datetime
from firebase_admin import db
from .status import apply_status_for_turn, update_status, remove_status_effects
from .battle_utils import *
from .skill_handler import process_all_skills, process_on_hit_effects, use_skill
from .skills import *

async def Battle(channel, challenger_m, opponent_m = None, boss = None, raid = False, practice = False, tower = False, tower_floor = 1, raid_ended = False, simulate = False, skill_data = None, wdc = None, wdo = None, scd = None, insignia = None):
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
                ref_raid_exist = db.reference(f"레이드/내역/")
                existing_data = ref_raid_exist.get()

                # ====================  [미션]  ====================
                # 시즌미션 : 선봉장 (레이드에서 선공 10회 달성)
                if not existing_data: # 아직 아무도 도전하지 않았다면?
                    ref_mission = db.reference(f"미션/미션진행상태/{challenger_m.name}/시즌미션/선봉장")
                    mission_data = ref_mission.get() or {}

                    already_today = mission_data.get('오늘달성', False)
                    completed = mission_data.get('완료', False)
                    current_count = mission_data.get('달성횟수', 0)

                    if not completed and not already_today:
                        new_count = current_count + 1
                        updates = {
                            "달성횟수": new_count,
                            "오늘달성": True
                        }

                        if new_count >= 10:
                            from .commands import mission_notice
                            updates["완료"] = True
                            mission_notice(challenger_m.display_name,"선봉장")
                            print(f"{challenger_m.display_name}의 [선봉장] 미션 완료")

                        ref_mission.update(updates)
                # ====================  [미션]  ====================
                        
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
        # attacker 턴일 때 attacker 상태 갱신
        update_status(attacker, current_turn_id=attacker["Id"])
        update_status(defender, current_turn_id=attacker["Id"])

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

        evasion_score = calculate_evasion_score(defender["Speed"])
        accuracy = calculate_accuracy(attacker["Accuracy"], evasion_score + defender["Evasion"]) # 1 - 명중률 수치만큼 빗나갈 확률 상쇄 가능

        base_damage = random.uniform(attacker["Attack"] * accuracy, attacker["Attack"])  # 최소 ~ 최대 피해
        distance_bool = False
        critical_bool = False

        if "두번째 피부" in attacker['Status']:
            passive_skill_data = attacker["Skills"].get("두번째 피부", None)   
            passive_skill_level = passive_skill_data["레벨"]
            message, damage = second_skin(defender,passive_skill_level, 1, skill_data_firebase)
            skill_message += message
            base_damage += damage

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
        "BaseDefenseIgnore": 0,
        "Evasion" : 0,
        "BaseEvasion" : 0,
        "DamageEnhance" : 0, # 피해 증폭
        "BaseDamageEnhance" : 0, # 피해 감소
        "DamageReduction" : 0, # 피해 감소
        "BaseDamageReduction" : 0, # 피해 감소
        "Resilience" : 0, # 강인함
        "BaseResilience" : 0,
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
        "DefenseIgnore": 0,
        "BaseDefenseIgnore": 0,
        "Evasion" : 0,
        "BaseEvasion" : 0,
        "DamageEnhance" : 0, # 피해 증폭
        "BaseDamageEnhance" : 0, # 피해 감소
        "DamageReduction" : 0, # 피해 감소
        "BaseDamageReduction" : 0, # 피해 감소
        "Resilience" : 0, # 강인함
        "BaseResilience" : 0,
        "Id" : 1, # Id를 통해 도전자와 상대 파악 도전자 = 0, 상대 = 1
        "Accuracy": weapon_data_opponent.get("명중", 0),
        "BaseAccuracy": weapon_data_opponent.get("명중", 0),
        "Defense": weapon_data_opponent.get("방어력", 0),
        "Skills": opponent_merged_skills,
        "Status" : {}
    }

    if not simulate:
        challenger_insignia = get_user_insignia_stat(challenger_m.name, role="challenger")

        if not tower and not raid:
            opponent_insignia = get_user_insignia_stat(opponent_m.name, role="opponent")
            insignia = {
                **challenger_insignia,
                **opponent_insignia
            }
        else:
            insignia = {
                **challenger_insignia
            }

    base_stats = ["CritChance", "CritDamage", "DefenseIgnore", "DamageReduction", "Resilience", "DamageEnhance", "Evasion"]
    all_stats = base_stats + [f"Base{stat}" for stat in base_stats]

    for stat in all_stats:
        challenger[stat] += insignia.get("challenger", {}).get(stat, 0)
        # 타워/레이드가 아닌 경우에만 opponent 스탯 적용
        if not tower and not raid:
            opponent[stat] += insignia.get("opponent", {}).get(stat, 0)
    
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

    if not simulate:
        # 챌린저 무기 스탯 정보 추가
        challenger_embed = discord.Embed(title="🟦 도전자 스탯", color=discord.Color.blue())

        evasion_score = calculate_evasion_score(opponent["Speed"])
        challenger_embed.add_field(
            name=f"[{challenger['name']}](+{weapon_data_challenger.get('강화', 0)}) [{challenger['Weapon']}]",
            value=(
                f"대미지        : `{round(challenger['Attack'] * calculate_accuracy(challenger['Accuracy'], evasion_score + opponent['Evasion']))} ~ {challenger['Attack']}`\n"
                f"내구도        : `{challenger['HP']}`\n"
                f"공격력        : `{challenger['Attack']}`\n"
                f"스킬 증폭     : `{challenger['Spell']}`\n"
                f"치명타 확률   : `{round(challenger['CritChance'] * 100, 2)}%`\n"
                f"치명타 대미지 : `{round(challenger['CritDamage'] * 100, 2)}%`\n"
                f"스피드        : `{challenger['Speed']}` (회피: `{round(calculate_evasion_score(challenger['Speed']))}`)\n"
                f"명중          : `{challenger['Accuracy']}` (명중률: `{round(calculate_accuracy(challenger['Accuracy'], evasion_score + opponent['Evasion']) * 100, 2)}%`)\n"
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

        ref_user_insignia = db.reference(f"무기/유저/{challenger_m.name}/각인")  # 예: 'nickname' 변수는 해당 유저명
        user_insignia = ref_user_insignia.get() or {}

        equipped = user_insignia  # 이미 위에서 불러온 각인 목록

        
        # 인장 상세 정보 가져오기
        ref_insignia_level_detail = db.reference(f"무기/각인/유저/{challenger_m.name}")
        insignia_level_detail = ref_insignia_level_detail.get() or {}
        inventory = insignia_level_detail  # {인장명: {"레벨": x, ...}} 형태라고 가정

        desc_lines = []
        for i in range(3):
            name = equipped[i] if i < len(equipped) and equipped[i] else "-"
            if name and name != "-" and name in inventory:
                data = inventory[name]
                level = data.get("레벨", 1)
                
                # 각인 주스탯 정보 불러오기
                ref_item_insignia_stat = db.reference(f"무기/각인/스탯/{name}")
                insignia_stat = ref_item_insignia_stat.get() or {}

                stat = insignia_stat.get("주스탯", "N/A")
                base_value = insignia_stat.get("초기 수치", 0)
                per_level = insignia_stat.get("증가 수치", 0)
                value = base_value + per_level * level

                # %로 표시할 각인인지 판별
                percent_names = ['강철의 맹세', '약점 간파', '타오르는 혼']
                if name in percent_names:
                    value_str = f"{value * 100:.0f}%"
                else:
                    value_str = f"{value}"

                desc_lines.append(f"{i+1}번: {name} (Lv.{level}, {stat} +{value_str})")
            else:
                desc_lines.append(f"{i+1}번: -")

        challenger_embed.add_field(
            name="📙 각인",
            value="\n".join(desc_lines),
            inline=False
        )

        # 상대 스탯 임베드
        opponent_embed = discord.Embed(title="🟥 상대 스탯", color=discord.Color.red())

        evasion_score = calculate_evasion_score(challenger["Speed"])
        opponent_embed.add_field(
            name=f"[{opponent['name']}](+{weapon_data_opponent.get('강화', 0)}) [{opponent['Weapon']}]",
            value=(
                f"대미지        : `{round(opponent['Attack'] * calculate_accuracy(opponent['Accuracy'], evasion_score + challenger['Evasion']))} ~ {opponent['Attack']}`\n"
                f"내구도        : `{opponent['HP']}`\n"
                f"공격력        : `{opponent['Attack']}`\n"
                f"스킬 증폭     : `{opponent['Spell']}`\n"
                f"치명타 확률   : `{round(opponent['CritChance'] * 100, 2)}%`\n"
                f"치명타 대미지 : `{round(opponent['CritDamage'] * 100, 2)}%`\n"
                f"스피드        : `{opponent['Speed']}` (회피: `{round(calculate_evasion_score(opponent['Speed']))}`)\n"
                f"명중          : `{opponent['Accuracy']}` (명중률: `{round(calculate_accuracy(opponent['Accuracy'], evasion_score + challenger['Evasion']) * 100, 2)}%`)\n"
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

        if not raid and not tower:
            ref_user_insignia = db.reference(f"무기/유저/{opponent_m.name}/각인")  # 예: 'nickname' 변수는 해당 유저명
            user_insignia = ref_user_insignia.get() or {}

            equipped = user_insignia  # 이미 위에서 불러온 각인 목록

        
            # 인장 상세 정보 가져오기
            ref_insignia_level_detail = db.reference(f"무기/각인/유저/{opponent_m.name}")
            insignia_level_detail = ref_insignia_level_detail.get() or {}
            inventory = insignia_level_detail  # {인장명: {"레벨": x, ...}} 형태라고 가정

            desc_lines = []
            for i in range(3):
                name = equipped[i] if i < len(equipped) and equipped[i] else "-"
                if name and name != "-" and name in inventory:
                    data = inventory[name]
                    level = data.get("레벨", 1)
                    
                    # 각인 주스탯 정보 불러오기
                    ref_item_insignia_stat = db.reference(f"무기/각인/스탯/{name}")
                    insignia_stat = ref_item_insignia_stat.get() or {}

                    stat = insignia_stat.get("주스탯", "N/A")
                    base_value = insignia_stat.get("초기 수치", 0)
                    per_level = insignia_stat.get("증가 수치", 0)
                    value = base_value + per_level * level

                    # %로 표시할 각인인지 판별
                    percent_names = ['강철의 맹세', '약점 간파', '타오르는 혼']
                    if name in percent_names:
                        value_str = f"{value * 100:.0f}%"
                    else:
                        value_str = f"{value}"

                    desc_lines.append(f"{i+1}번: {name} (Lv.{level}, {stat} +{value_str})")
                else:
                    desc_lines.append(f"{i+1}번: -")

            opponent_embed.add_field(
                name="📙 각인",
                value="\n".join(desc_lines),
                inline=False
            )

        await weapon_battle_thread.send(embed=challenger_embed)
        await weapon_battle_thread.send(embed=opponent_embed)

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
            apply_status_for_turn(attacker, "치유 감소", 1, healban_amount, source_id = attacker['Id'])
            apply_status_for_turn(defender, "치유 감소", 1, healban_amount, source_id = defender['Id'])

        attacked = False

        if "일섬" in attacker["Status"]:
            if attacker["Status"]["일섬"]["duration"] == 1:
                issen_data = skill_data_firebase['일섬']['values']
                skill_level = defender['Skills']['일섬']['레벨']
                accuracy_apply_rate = round((issen_data['기본_명중_반영_비율'] + issen_data['레벨당_명중_반영_비율'] * skill_level) * 100)

                def calculate_damage(attacker,defender,multiplier):
                    evasion_score = calculate_evasion_score(defender["Speed"])
                    accuracy = calculate_accuracy(attacker["Accuracy"], evasion_score + defender["Evasion"])
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
                else:
                    shield_amount = 0

                

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

                if "보호막" in challenger['Status']:
                    shield_amount_challenger = challenger["Status"]["보호막"]["value"]
                else:
                    shield_amount_challenger = 0

                if "보호막" in opponent['Status']:
                    shield_amount_opponent = opponent["Status"]["보호막"]["value"]
                else:
                    shield_amount_opponent = 0
                

                show_bar(battle_embed, raid, challenger, shield_amount_challenger, opponent, shield_amount_opponent)

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
            else:
                shield_amount = 0
                
            attacker["HP"] -= bleed_damage
            battle_embed.add_field(name="", value = f"출혈 상태로 인하여 {bleed_damage} 대미지를 받았습니다!{shield_message}", inline = False)
            battle_embed.add_field(name="남은 턴", value = f"출혈 상태 남은 턴 : {attacker['Status']['출혈']['duration']}", inline = False)

            if "보호막" in challenger['Status']:
                shield_amount_challenger = challenger["Status"]["보호막"]["value"]
            else:
                shield_amount_challenger = 0

            if "보호막" in opponent['Status']:
                shield_amount_opponent = opponent["Status"]["보호막"]["value"]
            else:
                shield_amount_opponent = 0

            show_bar(battle_embed, raid, challenger, shield_amount_challenger, opponent, shield_amount_opponent)

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
            else:
                shield_amount = 0
                
            attacker["HP"] -= burn_damage
            battle_embed.add_field(name="", value = f"화상 상태로 인하여 {burn_damage} 대미지를 받았습니다!{shield_message}", inline = False)
            battle_embed.add_field(name="남은 턴", value = f"화상 상태 남은 턴 : {attacker['Status']['화상']['duration']}", inline = False)

            if "보호막" in challenger['Status']:
                shield_amount_challenger = challenger["Status"]["보호막"]["value"]
            else:
                shield_amount_challenger = 0

            if "보호막" in opponent['Status']:
                shield_amount_opponent = opponent["Status"]["보호막"]["value"]
            else:
                shield_amount_opponent = 0

            show_bar(battle_embed, raid, challenger, shield_amount_challenger, opponent, shield_amount_opponent)

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
            if attacker['Id'] == 0: # 도전자 공격
                battle_embed = discord.Embed(title=f"{attacker['name']}의 독!🫧", color=discord.Color.red())
            elif attacker['Id'] == 1: # 상대 공격
                battle_embed = discord.Embed(title=f"{attacker['name']}의 독!🫧", color=discord.Color.blue())

                
            attacker["HP"] -= posion_damage
            battle_embed.add_field(name="", value = f"독 상태로 인하여 {posion_damage} 대미지를 받았습니다!{shield_message}", inline = False)
            battle_embed.add_field(name="남은 턴", value = f"독 상태 남은 턴 : {attacker['Status']['독']['duration']}", inline = False)

            if "보호막" in challenger['Status']:
                shield_amount_challenger = challenger["Status"]["보호막"]["value"]
            else:
                shield_amount_challenger = 0

            if "보호막" in opponent['Status']:
                shield_amount_opponent = opponent["Status"]["보호막"]["value"]
            else:
                shield_amount_opponent = 0
            
            show_bar(battle_embed, raid, challenger, shield_amount_challenger, opponent, shield_amount_opponent)

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
            update_status(attacker, current_turn_id=attacker["Id"])
            update_status(defender, current_turn_id=attacker["Id"])
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
            update_status(attacker, current_turn_id=attacker["Id"])
            update_status(defender, current_turn_id=attacker["Id"])
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
        overdrive_chance = max(0, (speed - 200) // 5)  # 초가속: 200 초과부터 5당 1%
        result_message = ""

        # 가속 판정 1회
        acceleration_triggered = False
        overdrive_triggered = False
        cooldown_reduction = 0

        if "속박" not in attacker["Status"]: # 속박 상태가 아니라면
            if acceleration_chance > 0 and random.randint(1, 100) <= acceleration_chance:
                cooldown_reduction = 1
                acceleration_triggered = True

                # 초가속 판정
                if overdrive_chance > 0 and random.randint(1, 100) <= overdrive_chance:
                    cooldown_reduction += 1
                    overdrive_triggered = True

            # 가속이 발동한 경우: 모든 쿨다운 감소 처리
            if acceleration_triggered:
                for skill, cooldown_data in attacker["Skills"].items():
                    if cooldown_data["현재 쿨타임"] > 0:
                        attacker["Skills"][skill]["현재 쿨타임"] = max(0, cooldown_data["현재 쿨타임"] - cooldown_reduction)

                        # 헤드샷 장전 감소
                        if skill == "헤드샷" and "장전" in attacker["Status"]:
                            attacker["Status"]["장전"]["duration"] -= cooldown_reduction
                            if attacker["Status"]["장전"]["duration"] <= 0:
                                del attacker["Status"]["장전"]

                # 결과 메시지 출력
                if overdrive_triggered:
                    result_message = f"⚡**초가속!** 모든 스킬의 쿨타임이 **{cooldown_reduction} 감소**했습니다!\n"
                else:
                    result_message = f"💨가속! 모든 스킬의 쿨타임이 1 감소했습니다!\n"
        
        slienced = False
        if '침묵' in attacker['Status']:
            slienced = True

        evasion = False # 회피

        if "속박" in defender["Status"]: # 속박 시 회피 불가
            attacked = True 
        else:
            evasion_score = calculate_evasion_score(defender["Speed"])
            accuracy = calculate_accuracy(attacker["Accuracy"], evasion_score + defender["Evasion"]) # 1 - 명중률 수치만큼 빗나갈 확률 상쇄 가능
            accuracy = max(accuracy, 0.1)  # 최소 명중률 10%
            if random.random() > accuracy: # 회피
            # if random.random() > accuracy:
                evasion = True
            else:
                attacked = True

        if "기습" in defender["Status"]:
            if evasion: # 기습 스킬 시전 후 회피했다면?
                defender['evaded'] = True

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

        if attacked:
            result_message, used_skill = process_on_hit_effects(
                attacker, defender, evasion, critical, skill_attack_names, used_skill, result_message,
                skill_data_firebase, battle_embed
            )
        
        if skill_attack_names or attacked: # 공격시 상대의 빙결 상태 해제
            if skill_attack_names != ['명상'] and not evasion: # 명상만 썼을 경우, 회피했을 경우 제외!
                if '빙결' in defender['Status']:
                    del defender['Status']['빙결']
                    battle_embed.add_field(name="❄️빙결 상태 해제!", value = f"공격을 받아 빙결 상태가 해제되었습니다!\n")

        # 강인함 로그 처리 - attacker, defender 모두 포함
        for char in (attacker, defender):
            logs = char.get("Log", [])
            if logs:
                result_message += "\n".join(logs) + "\n"
                char["Log"].clear()  # 로그 초기화

        if cooldown_messages:
            final_cooldown_text = "⏳:" + " ".join(cooldown_messages)
            result_message += final_cooldown_text + "\n"

        # 공격 후, 각 스킬의 현재 쿨타임을 감소시키는 부분
        for skill, cooldown_data in attacker["Skills"].items():
            if cooldown_data["현재 쿨타임"] > 0 and skill not in used_skill:
                attacker["Skills"][skill]["현재 쿨타임"] -= 1  # 현재 쿨타임 감소

        if skill_attack_names:
            crit_text = "💥" if critical else ""
            evade_text = "회피!⚡️" if evade else ""
            distance_text = "🎯" if dist else ""

            shield_message = ""
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
            else:
                shield_amount = 0

            battle_embed.add_field(name ="", value = f"**{evade_text}{distance_text} {damage} 대미지!{crit_text}{shield_message}**",inline = False)
            defender["HP"] -= damage

            if "보호막" in challenger['Status']:
                shield_amount_challenger = challenger["Status"]["보호막"]["value"]
            else:
                shield_amount_challenger = 0

            if "보호막" in opponent['Status']:
                shield_amount_opponent = opponent["Status"]["보호막"]["value"]
            else:
                shield_amount_opponent = 0

            show_bar(battle_embed, raid, challenger, shield_amount_challenger, opponent, shield_amount_opponent)
        else:
            # 크리티컬 또는 회피 여부에 따라 메시지 추가
            crit_text = "💥" if critical else ""
            evade_text = "회피!⚡️" if evade else ""
            distance_text = "🎯" if dist else ""

            shield_message = ""
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
            else:
                shield_amount = 0

            battle_embed.add_field(name ="", value = f"**{evade_text}{distance_text} {damage} 대미지!{crit_text}{shield_message}**",inline = False)
            defender["HP"] -= damage

            if "보호막" in challenger['Status']:
                shield_amount_challenger = challenger["Status"]["보호막"]["value"]
            else:
                shield_amount_challenger = 0

            if "보호막" in opponent['Status']:
                shield_amount_opponent = opponent["Status"]["보호막"]["value"]
            else:
                shield_amount_opponent = 0
            
            show_bar(battle_embed, raid, challenger, shield_amount_challenger, opponent, shield_amount_opponent)

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

