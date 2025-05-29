import discord
import random
import asyncio
import math
from firebase_admin import db
from .status import apply_status_for_turn, update_status, remove_status_effects
from .battle_utils import (
    calculate_damage_reduction, calculate_accuracy, calculate_evasion,
    calculate_move_chance, adjust_position
)
from .skills import (
    charging_shot, invisibility, smash, second_skin, spearShot, glacial_fissure, headShot,
    mech_Arm, meditate, Magnetic, issen, timer, fire, ice, holy, frostbite, rapid_fire,
    icathian_rain, voidseeker, Reap, electronic_line, shadow_ball, poison_jab, fire_punch,
    Hex, Shield, supercharger, killer_instinct, unyielding, concussion_punch, cursed_body
)


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

# 방어력 기반 피해 감소율 계산 함수
def calculate_damage_reduction(defense):
    return min(0.99, 1 - (100 / (100 + defense)))  # 방어력 공식 적용

def calculate_accuracy(accuracy):
    return min(0.99, 1 - (50 / (50 + accuracy))) # 명중률 공식 적용

def calculate_evasion(distance):
    return (distance - 1) * 0.1

def calculate_move_chance(speed, move_chain = 0):
    """
    move_chain: 연속 이동 횟수 (0부터 시작)
    """
    penalty_ratio = 0.7 ** move_chain  # 이동할수록 점점 감소 (예: 1회 70%, 2회 49%, ...)
    effective_speed = speed * penalty_ratio
    move_chance = min(0.99, 1 - math.exp(-effective_speed / 70))
    return move_chance

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

    

async def Battle(channel, challenger_m, opponent_m = None, boss = None, raid = False, practice = False, tower = False, tower_floor = 1, raid_ended = False, simulate = False, skill_data = None, wdc = None, wdo = None, scd = None):
        battle_distance = 1

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
                    skill_message, damage= glacial_fissure(attacker,defender,evasion,skill_level, skill_data_firebase, battle_distance)
                    result_message += skill_message
                    if evasion:
                        # 스킬 쿨타임 적용
                        attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown
                        return None, result_message, critical_bool
                elif skill_name == "헤드샷":
                    skill_message, damage, critical_bool = headShot(attacker,evasion,skill_level, skill_data_firebase)
                    result_message += skill_message
                    if evasion:
                        # 스킬 쿨타임 적용
                        attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown
                        apply_status_for_turn(attacker, "장전", duration=1)
                        return None, result_message, critical_bool
                elif skill_name == "명상":
                    skill_message, damage= meditate(attacker,skill_level, skill_data_firebase)
                    result_message += skill_message
                elif skill_name == "타이머":
                    skill_message, damage= timer()
                    result_message += skill_message
                elif skill_name == "일섬":
                    skill_message, damage= issen(attacker,defender, skill_level, skill_data_firebase)
                    result_message += skill_message
                elif skill_name == "화염 마법":
                    skill_message, damage= fire(attacker,defender, evasion,skill_level, skill_data_firebase)
                    result_message += skill_message
                elif skill_name == "냉기 마법":
                    skill_message, damage= ice(attacker,defender, evasion,skill_level, skill_data_firebase)
                    result_message += skill_message
                elif skill_name == "신성 마법":
                    skill_message, damage= holy(attacker,defender, evasion,skill_level, skill_data_firebase)
                    result_message += skill_message
                elif skill_name == "강타":
                    skill_message, damage = smash(attacker,defender,evasion,skill_level, skill_data_firebase)
                    critical_bool = True
                    result_message += skill_message
                    if evasion:
                        # 스킬 쿨타임 적용
                        critical_bool = False
                        attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown
                        return None, result_message, critical_bool 
                elif skill_name == "동상":
                    skill_message, damage= frostbite(attacker,defender,evasion,skill_level, skill_data_firebase)
                    result_message += skill_message
                    if evasion:
                        # 스킬 쿨타임 적용
                        attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown
                        return None, result_message, critical_bool
                elif skill_name == "속사":
                    skill_message, damage = rapid_fire(attacker,defender,skill_level, skill_data_firebase, battle_distance)
                    result_message += skill_message
                    total_damage += damage
                elif skill_name == '이케시아 폭우':
                    skill_message, damage = icathian_rain(attacker,defender,skill_level, skill_data_firebase, battle_distance)
                    result_message += skill_message
                    total_damage += damage
                elif skill_name == '공허추적자':
                    skill_message, damage = voidseeker(attacker,defender,evasion,skill_level, skill_data_firebase)
                    result_message += skill_message
                elif skill_name == "수확":
                    skill_message, damage = Reap(attacker,evasion,skill_level, skill_data_firebase)
                    result_message += skill_message
                    if evasion:
                        # 스킬 쿨타임 적용
                        attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown
                        return None, result_message, critical_bool
                elif skill_name == "자력 발산":
                    skill_message, damage= Magnetic(attacker,defender,skill_level, skill_data_firebase, battle_distance)
                    result_message += skill_message
                    if evasion:
                        # 스킬 쿨타임 적용
                        attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown
                        return None, result_message, critical_bool
                elif skill_name == "전선더미 방출":
                    skill_message, damage= mech_Arm(attacker,defender,evasion,skill_level, skill_data_firebase, battle_distance)
                    result_message += skill_message
                    if evasion:
                        # 스킬 쿨타임 적용
                        attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown
                        return None, result_message, critical_bool
                elif skill_name == "전깃줄":
                    skill_message, damage= electronic_line(attacker,defender,skill_level, skill_data_firebase, battle_distance)
                    result_message += skill_message
                    if evasion:
                        # 스킬 쿨타임 적용
                        attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown
                        return None, result_message, critical_bool
                elif skill_name == "섀도볼":
                    skill_message, damage= shadow_ball(attacker, defender, evasion, skill_level, skill_data_firebase)
                    result_message += skill_message
                elif skill_name == "독찌르기":
                    skill_message, damage= poison_jab(attacker, defender, evasion, skill_level, skill_data_firebase)
                    result_message += skill_message
                elif skill_name == "불꽃 펀치":
                    skill_message, damage= fire_punch(attacker, defender, evasion, skill_level, skill_data_firebase)
                    result_message += skill_message
                elif skill_name == "병상첨병":
                    skill_message, damage= Hex(attacker, defender, evasion, skill_level, skill_data_firebase)
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
            "Move_chain" : 0,
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
            "Move_chain" : 0,
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
            move_chance = calculate_move_chance(attacker["Speed"], attacker["Move_chain"])
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
                    attacker['Move_chain'] += 1
                    attacker["Position"] = adjust_position(attacker["Position"], move_distance, dash_direction)
                    if (attacker["Position"] < 0 and defender["Position"] > 0) or (attacker["Position"] > 0 and defender["Position"] < 0):
                        battle_distance = abs(attacker["Position"] - defender["Position"]) - 1  # 0을 건너뛰므로 -1
                    else:
                        battle_distance = abs(attacker["Position"] - defender["Position"])  # 같은 방향이면 그대로 계산
                    dash = True

                    if battle_distance <= attack_range:
                        attacked = True
                else:
                    attacker['Move_chain'] = 0

            elif battle_distance < attack_range:  # 후퇴
                if random.random() < move_chance and "속박" not in attacker["Status"]:
                    move_distance = 1
                    attacker['Move_chain'] += 1
                    attacker["Position"] = adjust_position(attacker["Position"], move_distance, retreat_direction)
                    if (attacker["Position"] < 0 and defender["Position"] > 0) or (attacker["Position"] > 0 and defender["Position"] < 0):
                        battle_distance = abs(attacker["Position"] - defender["Position"]) - 1  # 0을 건너뛰므로 -1
                    else:
                        battle_distance = abs(attacker["Position"] - defender["Position"])  # 같은 방향이면 그대로 계산
                    retreat = True
                else:
                    attacker['Move_chain'] = 0
                    retreat = False
                attacked = True

            else:  # 거리 유지 후 공격
                attacker['Move_chain'] = 0
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
                            result_message += killer_instinct(attacker,defender,skill_level, skill_data_firebase)
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
                            result_message += spearShot(attacker,defender,evasion,skill_level, skill_data_firebase, battle_distance)
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
                        result_message += unyielding(defender, skill_level, skill_data_firebase, battle_distance)

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
                        result_message += cursed_body(attacker, skill_level, skill_data_firebase)

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
                    battle_embed.add_field(name="돌진!", value = f"{attacker['name']}의 돌진! 거리가 {move_distance}만큼 줄어듭니다!\n(이동 확률 : {round(move_chance * 100,2)}%)", inline = False)
                elif retreat:
                    battle_embed.add_field(name="후퇴!", value = f"{attacker['name']}의 후퇴! 거리가 {move_distance}만큼 늘어납니다!\n(이동 확률 : {round(move_chance * 100,2)}%)", inline = False)
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
                    battle_embed.add_field(name="돌진!", value = f"{attacker['name']}의 돌진! 거리가 {move_distance}만큼 줄어듭니다!\n(이동 확률 : {round(move_chance * 100,2)}%)", inline = False)
                elif retreat:
                    battle_embed.add_field(name="후퇴!", value = f"{attacker['name']}의 후퇴! 거리가 {move_distance}만큼 늘어납니다!\n(이동 확률 : {round(move_chance * 100,2)}%)", inline = False)
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
                    battle_embed.add_field(name="돌진!", value = f"{attacker['name']}의 돌진! 거리가 {move_distance}만큼 줄어듭니다!\n(이동 확률 : {round(move_chance * 100,2)}%)", inline = False)

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