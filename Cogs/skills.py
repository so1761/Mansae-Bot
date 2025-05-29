import random
from .battle_utils import calculate_accuracy, calculate_evasion
from .status import apply_status_for_turn
from .battle_utils import adjust_position, calculate_damage_reduction

def charging_shot(attacker, defender,evasion,skill_level, skill_data_firebase):
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

def invisibility(attacker,skill_level, skill_data_firebase):
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

def smash(attacker, defender, evasion, skill_level, skill_data_firebase):
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

def issen(attacker, defender, skill_level, skill_data_firebase):
    # 일섬 : 다음턴에 적에게 날카로운 참격을 가한다. 회피를 무시하고 명중률에 비례한 대미지를 입히며, 표식을 부여한다.
    # 출혈 상태일 경우, 출혈 상태 해제 후 남은 피해의 150%를 즉시 입히고, 해당 피해의 50%를 고정 피해로 변환

    apply_status_for_turn(defender, "일섬", duration=2)
    message = f"**일섬** 사용!\n엄청난 속도로 적을 벤 후, 다음 턴에 날카로운 참격을 가합니다.\n회피를 무시하고 명중에 비례하는 대미지를 입힙니다.\n" 
    return message, 0

def headShot(attacker, evasion, skill_level, skill_data_firebase):
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

def spearShot(attacker,defender,evasion,skill_level, skill_data_firebase, battle_distance):
    spearShot_data = skill_data_firebase['창격']['values']
    near_distance = spearShot_data['근접_거리']
    condition_distance = spearShot_data['적정_거리']
    slow_amount = spearShot_data['기본_둔화량'] + spearShot_data['레벨당_둔화량'] * skill_level

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
    
def mech_Arm(attacker,defender, evasion, skill_level, skill_data_firebase, battle_distance):
    # 전선더미 방출: (20 + 레벨 당 5) + 스킬 증폭 20% + 레벨당 10% 추가 피해
    if not evasion:

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

def Magnetic(attacker, defender, skill_level, skill_data_firebase, battle_distance):
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

def Shield(attacker, skill_level, skill_data_firebase):
    # 보호막: 스킬 증폭의 100% + 레벨당 10%만큼의 보호막을 얻음
    Shield_data = skill_data_firebase['보호막']['values']
    skill_multiplier = int(round((Shield_data['기본_스킬증폭_계수'] + Shield_data['레벨당_스킬증폭_계수'] * skill_level) * 100))
    shield_amount = int(round((skill_multiplier / 100) * attacker['Spell']))
    apply_status_for_turn(attacker,"보호막",3,shield_amount)
    message = f"\n**<:siuu_E:1370283463978123264>보호막** 사용!\n{shield_amount}만큼의 보호막을 2턴간 얻습니다!\n"

    return message

def electronic_line(attacker,defender,skill_level, skill_data_firebase, battle_distance):
    # 전깃줄: (40 + 레벨 당 10) + 스킬 증폭 50% + 레벨당 20% 추가 피해
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

def Reap(attacker, evasion, skill_level, skill_data_firebase):
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

def unyielding(defender, skill_level, skill_data_firebase, battle_distance):
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

def frostbite(attacker, target, evasion, skill_level, skill_data_firebase):
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

def glacial_fissure(attacker, target, evasion,skill_level, skill_data_firebase, battle_distance):
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

def rapid_fire(attacker, defender, skill_level, skill_data_firebase, battle_distance):
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

def meditate(attacker, skill_level,skill_data_firebase):
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

def fire(attacker, defender, evasion, skill_level, skill_data_firebase):
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

def ice(attacker,defender, evasion, skill_level, skill_data_firebase):
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

def holy(attacker,defender, evasion, skill_level, skill_data_firebase):
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

def second_skin(target, skill_level, value, skill_data_firebase):
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

def icathian_rain(attacker, defender, skill_level, skill_data_firebase, battle_distance):
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
    passive_message, explosion_damage = second_skin(defender, passive_skill_level, 1, skill_data_firebase)
    defense = max(0, defender["Defense"] - attacker["DefenseIgnore"])
    damage_reduction = calculate_damage_reduction(defense)
    defend_damage = explosion_damage * (1 - damage_reduction)
    final_damage = defend_damage * (1 - defender['DamageReduction'])
    message += f"<:kaisa_Q:1370259693972361277>이케시아 폭우로 {hit_count}연타 공격! 총 {total_damage} 피해!\n"
    message += passive_message
    total_damage += final_damage
    return message,total_damage

def voidseeker(attacker, defender, evasion, skill_level, skill_data_firebase):
    # 공허추적자: 스킬 증폭 70% + 레벨당 10%의 스킬 대미지
    if not evasion:
        voidseeker_data = skill_data_firebase['공허추적자']['values']       
        skill_multiplier = (voidseeker_data['기본_스킬증폭_계수'] + voidseeker_data['레벨당_스킬증폭_계수_증가'] * skill_level)
        skill_damage = attacker["Spell"] * skill_multiplier
        apply_status_for_turn(defender,"속박",1)

        message = f"\n<:kaisa_W:1370259790772572171>**공허추적자** 사용!\n스킬 증폭 {int(round(skill_multiplier * 100))}%의 스킬 피해를 입히고 1턴간 속박!\n"
        passive_skill_data = attacker["Skills"].get("두번째 피부", None)   
        passive_skill_level = passive_skill_data["레벨"]
        passive_message, explosion_damage = second_skin(defender, passive_skill_level, 2, skill_data_firebase)
        message += passive_message
        skill_damage += explosion_damage
    else:
        skill_damage = 0
        message = f"\n**<:kaisa_W:1370259790772572171>공허추적자**가 빗나갔습니다!\n"
    return message, skill_damage

def supercharger(attacker, skill_level, skill_data_firebase):
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

def killer_instinct(attacker, defender, skill_level, skill_data_firebase):
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

def cursed_body(attacker, skill_level, skill_data_firebase):
    #저주받은 바디: 공격당하면 확률에 따라 공격자를 둔화
    cursed_body_data = skill_data_firebase['저주받은 바디']['values']
    if random.random() < cursed_body_data['둔화_확률'] + cursed_body_data['레벨당_둔화_확률'] * skill_level: # 확률에 따라 둔화 부여
        slow_amount = cursed_body_data['둔화량'] + cursed_body_data['레벨당_둔화량'] * skill_level
        apply_status_for_turn(attacker,"둔화",2, slow_amount)
        return f"**저주받은 바디** 발동!\n공격자에게 1턴간 {round(slow_amount * 100)}% 둔화 부여!\n"
    else:
        return ""

def shadow_ball(attacker,defender,evasion,skill_level, skill_data_firebase):
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

def Hex(attacker,defender,evasion,skill_level, skill_data_firebase):
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

def poison_jab(attacker,defender,evasion,skill_level, skill_data_firebase):
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

def fire_punch(attacker,defender,evasion,skill_level, skill_data_firebase):
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
