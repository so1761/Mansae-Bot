import discord
import random
import asyncio
import requests
import os
from datetime import datetime
from dotenv import load_dotenv
from firebase_admin import db
from .status import apply_status_for_turn, update_status, remove_status_effects
from .battle_utils import *
from .skill_handler import process_all_skills, process_on_hit_effects, use_skill
from .skills import *

async def apply_and_process_damage(
        source_char,       # 피해를 준 캐릭터
        target_char,       # 피해를 받는 캐릭터
        damage_amount,     # 총 피해량
        embed,             # 메시지를 추가할 Embed 객체
        is_critical,       # [추가] 치명타 여부 (True/False)
        is_evaded,         # [추가] 회피 여부 (True/False)
        damage_source_name # 피해 출처 이름 (로그용)
    ):
        """피해를 최종 적용하고 보호막/사령 분담을 처리하며, 직관적인 결과 메시지를 Embed에 추가합니다."""
        
        # 회피 시 즉시 종료
        if is_evaded:
            embed.add_field(name="", value=f"**회피!⚡️**", inline=False)
            return target_char['HP'] <= 0

        # 피해량이 0이면 메시지 없이 종료 (예: 버프 스킬만 사용)
        if damage_amount <= 0:
            return target_char['HP'] <= 0

        remaining_damage = damage_amount
        shield_message_part = ""
        summon_message_part = ""
        
        # 1. 보호막 흡수
        if remaining_damage > 0 and "보호막" in target_char['Status']:
            shield = target_char['Status']['보호막']
            damage_absorbed = min(remaining_damage, shield['value'])
            shield['value'] -= damage_absorbed
            remaining_damage -= damage_absorbed
            if shield['value'] <= 0:
                del target_char['Status']['보호막']
            shield_message_part = f" 🛡️{damage_absorbed} 흡수!"
            
        # 2. 사령 흡수
        if remaining_damage > 0 and 'Summon' in target_char and target_char.get('Summon'):
            summon = target_char['Summon']
            damage_absorbed = min(remaining_damage, summon['HP'])
            summon['HP'] -= damage_absorbed
            
            # 사령 파괴 여부 확인
            if summon['HP'] <= 0:
                remaining_damage = 0 # 피해 완전 흡수
                del target_char['Summon']
                if "사령 소환" in target_char["Skills"]:
                    cooldown = target_char["Skills"]["사령 소환"]["전체 쿨타임"]
                    target_char["Skills"]["사령 소환"]["현재 쿨타임"] = cooldown
                summon_message_part = f" 💀사령 소멸!({damage_absorbed} 흡수)"
            else:
                remaining_damage = 0 # 피해 완전 흡수
                summon_message_part = f" 💀{damage_absorbed} 흡수"

        # 3. 본체 피해 적용
        target_char["HP"] -= remaining_damage
        
        # 4. 최종 메시지 조합 및 Embed에 추가
        crit_text = "💥" if is_critical else ""
        
        # 본체에 피해가 들어갔거나, 아무것도 피해를 흡수하지 못했을 때만 피해량 표시
        if remaining_damage > 0:
            final_message = f"**{remaining_damage} 대미지!{crit_text}{shield_message_part}{summon_message_part}**"
        # 보호막이나 사령이 모든 피해를 흡수했을 때
        elif shield_message_part or summon_message_part:
            final_message = f"**총 {damage_amount} 피해!{crit_text} →{shield_message_part}{summon_message_part}**"
        else: # 예상치 못한 경우 기본 메시지
            final_message = f"**{damage_amount} 대미지!{crit_text}**"

        embed.add_field(name="", value=final_message, inline=False)
        return target_char['HP'] <= 0

async def Battle(channel, challenger_m, opponent_m = None, boss = None, raid = False, remain_HP = None, practice = False, tower = False, tower_floor = 1, simulate = False, skill_data = None, wdc = None, wdo = None, scd = None, insignia = None):
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

        if raid:
            if not practice:
                ref_raid_exist = db.reference(f"레이드/내역/")
                existing_data = ref_raid_exist.get()

                # ====================  [미션]  ====================
                # 시즌미션 : 선봉장 (레이드에서 선공 5회 달성)
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
                      
            ref_boss = db.reference(f"레이드/보스/{boss}")

            player_is_winner = (winner == "attacker" and defender['Id'] != 0) or (winner == "defender" and attacker['Id'] != 0)

            if winner == "attacker":
                final_HP = attacker['HP'] if defender['Id'] == 0 else defender['HP']
            else:
                final_HP = defender['HP'] if attacker['Id'] == 0 else attacker['HP']
            
            final_HP = max(final_HP, 0)
            total_damage = first_HP - final_HP

            if not practice:
                # 내구도 갱신
                ref_boss.update({"내구도": final_HP})

                # 기존 기록 가져오기
                ref_raid = db.reference(f"레이드/내역/{challenger_m.name}")
                raid_data = ref_raid.get() or {}
                boss_record = raid_data.get(boss, {})
                boss_record["대미지"] = total_damage
                boss_record["남은내구도"] = attacker['HP'] if attacker['Id'] == 0 else defender['HP']
                # 막타 여부 저장
                if player_is_winner:
                    boss_record["막타"] = True

                # 갱신된 기록 저장
                ref_raid.update({boss: boss_record})

                if player_is_winner:
                    await weapon_battle_thread.send(f"**토벌 완료!** 총 대미지 : {total_damage}")
                    # 다음 보스로 진행
                    ref_current_boss = db.reference("레이드/현재 레이드 보스")
                    current_boss = ref_current_boss.get()

                    ref_all_bosses = db.reference("레이드/보스목록")
                    all_boss_order = ref_all_bosses.get()

                    ref_today = db.reference("레이드/순서")
                    today = ref_today.get() or 0

                    raid_boss_list = [(today + i) % len(all_boss_order) for i in range(4)]
                    raid_boss_names = [all_boss_order[i] for i in raid_boss_list]

                    try:
                        current_index = raid_boss_names.index(current_boss)
                    except ValueError:
                        current_index = 0

                    next_index = (current_index + 1) % len(raid_boss_names)
                    next_boss = raid_boss_names[next_index]

                    ref_next_boss = db.reference(f"레이드/보스/{next_boss}")
                    next_boss_data = ref_next_boss.get() or {}
                    next_boss_hp = next_boss_data.get("내구도", 0)

                    if next_boss_hp <= 0:
                        description = "🎉 모든 보스를 토벌했습니다! 레이드 종료!"
                        title = "토벌 완료"
                        color = 0x00ff00
                    else:
                        description = f"📢 새로운 보스 등장: {next_boss}!"
                        title = "다음 보스 등장"
                        color = 0xff0000
                        ref_current_boss.set(next_boss)

                    data = {
                        "content": "",
                        "embeds": [{
                            "title": title,
                            "description": description,
                            "color": color,
                            "footer": {
                                "text": "Raid-Bot"
                            }
                        }]
                    }

                    load_dotenv()
                    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
                    requests.post(WEBHOOK_URL, json=data)  
                else:
                    await weapon_battle_thread.send(f"**레이드 종료!** 총 대미지 : {total_damage}")
            else:
                if player_is_winner:
                    await weapon_battle_thread.send(f"**토벌 완료!** 총 대미지 : {total_damage}")
                else:
                    await weapon_battle_thread.send(f"**레이드 종료!** 총 대미지 : {total_damage}")

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
            if not practice:
                weapon_data_challenger['내구도'] = remain_HP
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
        "BaseSpell" : weapon_data_challenger.get("스킬 증폭", 0),
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
        "BaseDefense": weapon_data_challenger.get("방어력", 0),
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
        "BaseSpell": weapon_data_opponent.get("스킬 증폭", 0),
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
        "BaseDefense": weapon_data_opponent.get("방어력", 0),
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

    # 1. 고정 수치(Flat Stats) 적용
    all_flat_stats = flat_stat_keys + [f"Base{stat}" for stat in flat_stat_keys]

    for stat in all_flat_stats:
        challenger[stat] += insignia.get("challenger", {}).get("flat_stats", {}).get(stat, 0)
        if not tower and not raid:
            opponent[stat] += insignia.get("opponent", {}).get("flat_stats", {}).get(stat, 0)

    # 2. 퍼센트(%) 수치 적용
    all_percent_stats = percent_stat_keys + [f"Base{stat}" for stat in percent_stat_keys]

    for stat in all_percent_stats:
        # Challenger
        percent_bonus_c = insignia.get("challenger", {}).get("percent_stats", {}).get(stat, 0)
        if percent_bonus_c > 0:
            challenger[stat] *= (1 + percent_bonus_c)
            challenger[stat] = round(challenger[stat])
        # Opponent
        if not tower and not raid:
            percent_bonus_o = insignia.get("opponent", {}).get("percent_stats", {}).get(stat, 0)
            if percent_bonus_o > 0:
                opponent[stat] *= (1 + percent_bonus_o)
                opponent[stat] = round(opponent[stat])   
    # if not simulate:
    #     challenger_insignia = get_user_insignia_stat(challenger_m.name, role="challenger")

    #     if not tower and not raid:
    #         opponent_insignia = get_user_insignia_stat(opponent_m.name, role="opponent")
    #         insignia = {
    #             **challenger_insignia,
    #             **opponent_insignia
    #         }
    #     else:
    #         insignia = {
    #             **challenger_insignia
    #         }

    # base_stats = ["CritChance", "CritDamage", "DefenseIgnore", "DamageReduction", "Resilience", "DamageEnhance", "Evasion"]
    # all_stats = base_stats + [f"Base{stat}" for stat in base_stats]

    # for stat in all_stats:
    #     challenger[stat] += insignia.get("challenger", {}).get(stat, 0)
    #     # 타워/레이드가 아닌 경우에만 opponent 스탯 적용
    #     if not tower and not raid:
    #         opponent[stat] += insignia.get("opponent", {}).get(stat, 0)
    
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
                    name=f"{challenger_m.display_name}의 탑 등반 모의전({current_floor}층)",
                    type=discord.ChannelType.public_thread
                )
            else:
                weapon_battle_thread = await channel.create_thread(
                    name=f"{challenger_m.display_name}의 탑 등반({current_floor}층)",
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
                if name in percent_insignias:
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
                    if name in percent_insignias:
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
            
    while challenger["HP"] > 0 and opponent["HP"] > 0:
        turn += 1

        if turn >= 30:
            healban_amount = min(1, round((turn - 20) * 0.01,1))
            apply_status_for_turn(attacker, "치유 감소", 1, healban_amount, source_id = attacker['Id'])
            apply_status_for_turn(defender, "치유 감소", 1, healban_amount, source_id = defender['Id'])

        attacked = False

        if "일섬" in attacker["Status"]:
            if attacker["Status"]["일섬"]["duration"] == 1:
                issen_data = skill_data_firebase['일섬']['values']
                skill_level = defender['Skills']['일섬']['레벨']

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
                total_issen_damage, critical, explosion_damage, bleed_explosion = calculate_damage(defender, attacker, 1)

                # 2. Embed 초기화 (오류 방지)
                if attacker['Id'] == 0:
                    battle_embed = discord.Embed(title=f"{defender['name']}의 일섬!", color=discord.Color.red())
                else:
                    battle_embed = discord.Embed(title=f"{defender['name']}의 일섬!", color=discord.Color.blue())

                # 3. 결과 메시지 생성 및 출력
                apply_status_for_turn(attacker, "출혈", 2, bleed_damage)
                battle_embed.add_field(name="일섬!", value="2턴간 출혈 부여!🩸\n", inline=False)
                
                crit_text = "💥" if critical else ""
                explosion_message = ""
                if bleed_explosion:
                    if '출혈' in attacker["Status"]: del attacker["Status"]['출혈']
                    battle_embed.add_field(
                        name="출혈 추가 효과!",
                        value="남은 출혈 대미지를 더하고\n총 피해의 50%를 고정피해로 입힙니다.",
                        inline=False
                    )
                    explosion_message = f"(+🩸{explosion_damage} 대미지)"
                
                is_dead = await apply_and_process_damage(
                    defender, attacker, total_issen_damage, battle_embed, critical, evasion, "일섬"
                )

                # 5. 전투 현황 업데이트 및 종료 체크 (수정 없음)
                shield_challenger = challenger["Status"].get("보호막", {}).get("value", 0)
                shield_opponent = opponent["Status"].get("보호막", {}).get("value", 0)
                show_bar(battle_embed, raid, challenger, shield_challenger, opponent, shield_opponent)

                if is_dead:
                    attacker["HP"] = 0
                    result = await end(attacker, defender, "defender", raid, simulate, winner_id=defender['Id'])
                    if simulate: return result
                    break
                else:
                    if not simulate: await weapon_battle_thread.send(embed=battle_embed)

        async def process_turn_start_effects(
            attacker, defender, raid, simulate, weapon_battle_thread, end_func,
            challenger, opponent, turn # turn을 인자로 받아 sleep 시간 조절에 사용
        ):
            """
            턴 시작 시 본체와 소환수의 모든 상태 효과(DoT, CC)를 처리하고,
            본체의 행동 가능 여부를 반환합니다.
            """

            async def _process_effects_for_char(char, is_summon=False):
                """특정 캐릭터(char)의 DoT 및 CC 효과를 처리하는 내부 함수"""
                # 1. 지속 피해(DoT) 처리
                dot_effects = {
                    "출혈": {"emoji": "🩸", "damage_type": "value"},
                    "화상": {"emoji": "🔥", "damage_type": "value"},
                    "독": {"emoji": "🫧", "damage_type": "percent_hp"}
                }

                for effect_name, props in dot_effects.items():
                    if effect_name in char.get("Status", {}):
                        
                        char_name = "사령" if is_summon else char['name']
                        total_dot_damage = 0
                        if props["damage_type"] == "value":
                            total_dot_damage = char["Status"][effect_name].get("value", 0)
                        elif props["damage_type"] == "percent_hp":
                            # 독은 항상 본체(attacker)의 HP를 기준으로 계산
                            total_dot_damage = round(attacker['HP'] / 16) 

                        if total_dot_damage <= 0: continue

                        dot_embed = discord.Embed(
                            title=f"{char_name}의 {effect_name}!{props['emoji']}",
                            color=discord.Color.red() if attacker['Id'] == 0 else discord.Color.blue()
                        )
                        dot_embed.add_field(name="지속 효과", value=f"{effect_name} 상태로 효과가 발동합니다.", inline=False)
                        
                        # [수정] DoT 피해는 사령 자신에게 적용됨. apply_and_process_damage는 본체-사령 연계 로직이 있음
                        # 따라서 사령에게는 직접 피해를 적용하고, 본체에게는 통합 함수 사용
                        if is_summon:
                            char['HP'] -= total_dot_damage
                            dot_embed.add_field(name="", value=f"**{total_dot_damage}**의 지속 피해!", inline=False)
                            is_dead = char['HP'] <= 0
                        else:
                            is_dead = await apply_and_process_damage(
                                char, char, total_dot_damage, dot_embed,
                                is_critical=False, is_evaded=False, damage_source_name=effect_name
                            )

                        # 남은 턴 메시지
                        current_status = char.get("Status", {}).get(effect_name, {})
                        remaining_duration = current_status.get('duration', 0)
                        duration_message = f"{effect_name} 상태 남은 턴: {remaining_duration}" if remaining_duration > 0 else f"{effect_name} 효과가 소진되었습니다."
                        dot_embed.add_field(name="남은 턴", value=duration_message, inline=False)
                        

                        shield_challenger = challenger["Status"].get("보호막", {}).get("value", 0)
                        shield_opponent = opponent["Status"].get("보호막", {}).get("value", 0)
                        show_bar(dot_embed, raid, challenger, shield_challenger, opponent, shield_opponent)

                        if not simulate: await weapon_battle_thread.send(embed=dot_embed)
                
                        if is_dead:
                            if is_summon:
                                if "사령 소환" in attacker["Skills"]:
                                    cooldown = attacker["Skills"]["사령 소환"]["전체 쿨타임"]
                                    attacker["Skills"]["사령 소환"]["현재 쿨타임"] = cooldown
                                # 사령이 죽었으면 딕셔너리에서 제거
                                del attacker['Summon'] 
                                # 본체 전투는 계속되므로 루프를 계속함
                                
                            else: # 본체가 죽었으면 전투 종료
                                char["HP"] = 0
                                result = await end_func(
                                    char,            # 사망자 (attacker 자신)
                                    defender,        # 생존자 (상대방)
                                    "defender",      # 승자
                                    raid,            # raid 여부
                                    simulate,        # simulate 여부
                                    winner_id=defender['Id'] # 승자 ID
                                )
                                return "ended", result # 전투 종료 신호

                # 2. 행동 불가(CC) 처리 (수정 없음, 단 turn 인자 사용)
                cc_effects = {
                    "기절": {"emoji": "💫"},
                    "빙결": {"emoji": "❄️"}
                }
                
                for effect_name, props in cc_effects.items():
                    if effect_name in char.get("Status", {}):
                        char_name = "사령" if is_summon else char['name']
                        
                        # 메시지만 출력하는 용도
                        cc_embed = discord.Embed(
                            title=f"{char_name}의 상태!⚔️", # 대상의 이름 사용
                            color=discord.Color.orange() # 경고/상태이상을 나타내는 색
                        )
                        cc_embed.add_field(
                            name="행동 불가!",
                            value=f"{char_name}이(가) {effect_name}{props['emoji']} 상태이상으로 묶여있습니다!\n남은 턴: {char['Status'][effect_name]['duration']}",
                            inline=False
                        )
                        
                        # '장전' 상태는 본체(attacker)에만 존재하므로, is_summon이 아닐 때만 체크
                        if not is_summon and "장전" in char["Status"]:
                            char["Status"]["장전"]["duration"] += 1

                        if not simulate:
                            await weapon_battle_thread.send(embed=cc_embed)
                
                    return "can_act", None # 기본적으로 행동 가능

            # --- 메인 로직 시작 ---
    
            # 1. 사령이 있다면, 사령의 효과부터 먼저 처리
            if 'Summon' in attacker and attacker.get('Summon'):
                summon = attacker['Summon']
                status, result = await _process_effects_for_char(summon, is_summon=True)
                # 사령의 효과 처리 중 본체가 죽는 경우는 없으므로, 'ended'는 체크하지 않음
                
            # 2. 본체의 효과 처리
            status, result = await _process_effects_for_char(attacker)
            if status == "ended":
                return "ended", result

            # 3. 본체의 행동 가능 여부 최종 결정
            # 본체 또는 사령에게 행동 불가 CC가 걸려 있는지 확인
            # (규칙 변경: 사령이 CC에 걸리면 본체는 행동 가능, 본체가 걸리면 행동 불가)
            for effect_name in ["기절", "빙결"]:
                if effect_name in attacker.get("Status", {}):
                    return "cc_active", None # 본체가 행동 불가

            return "can_act", None # 모든 검사를 통과하면 행동 가능

        # [ 여기가 핵심 수정 부분 ]
        # 새로 만든 함수를 호출하여 턴 시작 효과를 통합 처리
        action_status, result = await process_turn_start_effects(
            attacker, defender, raid, simulate, weapon_battle_thread, end,
            challenger, opponent, turn
        )

        # 전투가 끝났으면 루프 종료
        if action_status == "ended":
            if simulate: return result
            break # while 루프 종료
            
        # 행동 불가(CC) 상태이면 다음 턴으로
        if action_status == "cc_active":
            remove_status_effects(attacker, skill_data_firebase) # 스탯 재계산은 필수
            update_status(attacker, current_turn_id=attacker["Id"])
            update_status(defender, current_turn_id=attacker["Id"])
            attacker, defender = defender, attacker # 턴 넘기기
            continue # while 루프의 다음 반복으로

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
            reloading = True
        
        # 1. Embed 기본틀 생성
        # 스킬 사용 여부에 따라 제목/색상은 아래에서 변경됨
        battle_embed = discord.Embed(title=f"{attacker['name']}의 공격!⚔️", color=discord.Color.blue())
        
        # 2. 스킬 사용 여부 결정 (가속 효과는 result_message에 먼저 추가됨)
        skill_message, used_skill, skill_attack_names, cooldown_messages = process_all_skills(
            attacker, defender, slienced, evasion, attacked,
            skill_data_firebase
        )
        result_message += skill_message

        # 3. 피해량 계산 (스킬/기본공격 분기 처리)
        total_damage = 0
        critical = False # 치명타 여부 추적
        
        if skill_attack_names:
            # 스킬 공격
            battle_embed.title = f"{attacker['name']}의 스킬 사용!⚔️"
            if attacker['Id'] == 1: battle_embed.color = discord.Color.red()
            
            # attack 함수는 이제 순수 피해량만 계산
            total_damage, critical, _, _, skill_message = await attack(attacker, defender, evasion, reloading, skill_attack_names)
            result_message += skill_message
        else:
            # 일반 공격
            if attacker['Id'] == 1: battle_embed.color = discord.Color.red()

            # attack 함수는 이제 순수 피해량만 계산
            total_damage, critical, _, _, skill_message = await attack(attacker, defender, evasion, reloading, None)
            result_message += skill_message
            
        # 4. 적중 시 효과 처리 (뇌진탕, 불굴 등)
        if attacked:
            hit_effects_message, used_skill_on_hit = process_on_hit_effects(
                attacker, defender, evasion, critical, skill_attack_names, [], result_message,
                skill_data_firebase, battle_embed
            )
            used_skill.extend(used_skill_on_hit)

        # 5. 모든 텍스트 메시지를 Embed에 정리하여 추가
        if cooldown_messages:
            result_message += "\n⏳:" + " ".join(cooldown_messages)
        
        battle_embed.add_field(name="진행 상황", value=result_message.strip() or "별다른 일 없었다.", inline=False)
        
        # 6. [핵심] 통합 피해 처리 함수 호출
        is_dead = await apply_and_process_damage(
            attacker, defender, total_damage, battle_embed, critical, evasion,
            skill_attack_names[0] if skill_attack_names else "기본 공격"
        )

        # 7. 사령의 추가 공격 로직 (공격자에게 사령이 있을 경우)
        summon_can_attack = True # 사령 공격 가능 여부 플래그
        
        if 'Summon' in attacker and attacker.get('Summon') and not reloading and not evasion:
            summon = attacker['Summon']
            
            # [핵심 추가] 사령의 행동 불가 상태(CC) 확인
            for effect_name in ["기절", "빙결"]:
                if effect_name in summon.get("Status", {}):
                    # Embed에 사령이 공격하지 못했음을 알리는 메시지 추가
                    battle_embed.add_field(
                        name="사령 행동 불가",
                        value=f"⚔️ 사령이 {effect_name} 상태라 공격할 수 없습니다!",
                        inline=False
                    )
                    summon_can_attack = False
                    break # CC 하나라도 걸려있으면 더 확인할 필요 없음
            
            # 사령이 공격 가능한 상태일 때만 공격 로직 실행
            if summon_can_attack:
                evasion_score = calculate_evasion_score(defender["Speed"])
                accuracy = calculate_accuracy(summon.get("Accuracy", 0), evasion_score + defender.get("Evasion", 0))

                if random.random() <= accuracy:
                    summon_base_damage = summon.get("Attack", 0)
                    # 방어력 계산
                    defense = max(0, defender.get("Defense", 0) - attacker.get("DefenseIgnore", 0))
                    damage_reduction_calc = calculate_damage_reduction(defense)
                    final_summon_damage = round(summon_base_damage * (1 - damage_reduction_calc))
                    
                    # 사령의 공격 피해도 통합 처리 함수로 전달
                    is_dead_by_summon = await apply_and_process_damage(
                        attacker, defender, final_summon_damage, battle_embed,
                        False, # 사령 공격은 치명타 X
                        False, # 회피 계산은 이미 위에서 했음
                        "사령의 공격"
                    )
                    if is_dead_by_summon: is_dead = True
                else:
                    battle_embed.add_field(name="사령 전투", value="⚔️ 사령의 공격이 빗나갔습니다!", inline=False)

        # 8. 공격 후처리
        if attacked and '빙결' in defender['Status']:
             if not skill_attack_names or (skill_attack_names and '명상' not in skill_attack_names):
                del defender['Status']['빙결']
                battle_embed.add_field(name="❄️ 빙결 상태 해제!", value="공격을 받아 빙결 상태가 해제되었습니다!", inline=False)

        for skill, data in attacker["Skills"].items():
            if data["현재 쿨타임"] > 0 and skill not in used_skill:
                data["현재 쿨타임"] -= 1

        # 9. 최종 전투 현황 업데이트 및 종료 체크
        shield_challenger = challenger["Status"].get("보호막", {}).get("value", 0)
        shield_opponent = opponent["Status"].get("보호막", {}).get("value", 0)
        show_bar(battle_embed, raid, challenger, shield_challenger, opponent, shield_opponent)

        if is_dead:
            defender["HP"] = 0
            result = await end(attacker, defender, "attacker", raid, simulate, winner_id=attacker['Id'])
            if simulate: return result
            break

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
