import discord
import random
import asyncio
import math
from firebase_admin import db

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
        
        def headShot(attacker, evasion, skill_level):
            """액티브 - 헤드샷: 공격력 or 스킬 증폭 중 높은 스탯을 기반으로 피해, 장전 스택마다 20%씩 추가 피해 누적"""
            
            if not evasion:
                headShot_data = skill_data_firebase['헤드샷']['values']
                base_damage = headShot_data['기본_대미지'] + headShot_data['레벨당_기본_대미지'] * skill_level
                skill_multiplier = headShot_data['기본_스킬증폭_계수'] + headShot_data['레벨당_스킬증폭_계수_증가'] * skill_level
                attack_multiplier = headShot_data['기본_공격력_계수'] + headShot_data['레벨당_공격력_계수_증가'] * skill_level

                # 장전 스택 가져오기
                stack = attacker.get("HeadshotStack", 0)
                bonus_multiplier = 1 + (0.5 * stack)  # 스택당 +50% 누적 피해 증가

                # 공격력 기반 또는 스증 기반 중 높은 스탯 기준으로 결정
                if attacker["Attack"] >= attacker["Spell"]:
                    # 공격력 기반 → 랜덤 딜 적용
                    accuracy = calculate_accuracy(attacker["Accuracy"])
                    attack_value = attacker["Attack"] * attack_multiplier
                    skill_damage = random.uniform(attack_value * accuracy, attack_value) * bonus_multiplier
                    damage_type = "공격력 기반"
                    critical_bool = False
                    if random.random() < attacker["CritChance"]:
                        skill_damage *= attacker["CritDamage"]
                        critical_bool = True
                else:
                    # 스킬 증폭 기반 → 고정 딜, 치명타 없음
                    spell_value = attacker["Spell"] * skill_multiplier
                    skill_damage = spell_value * bonus_multiplier
                    damage_type = "스킬 증폭 기반"
                    critical_bool = False

                # 메시지
                message = (
                    f"**<:headShot:1370300576545640459>헤드샷** 사용! ({damage_type})\n"
                    f"장전 스택: {stack} → 추가 피해 **+{int(round((bonus_multiplier - 1) * 100))}%** 적용!\n"
                )

                # 장전 스택 +1 및 상태 부여
                attacker["HeadshotStack"] = stack + 1
                apply_status_for_turn(attacker, "장전", duration=1)
                message += "1턴간 **장전** 상태가 됩니다."

            else:
                # 회피 시
                skill_damage = 0
                message = "**<:headShot:1370300576545640459>헤드샷**이 빗나갔습니다!\n장전 스택이 초기화됩니다."
                critical_bool = False
                attacker["HeadshotStack"] = 0

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