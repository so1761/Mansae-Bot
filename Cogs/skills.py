import random
from .battle_utils import calculate_accuracy, calculate_evasion_score
from .status import apply_status_for_turn
from .battle_utils import calculate_damage_reduction

def invisibility(attacker, defender, evasion, skill_level, skill_data_firebase, mode = "buff"):
    if mode == "buff":
        # 은신 상태에서 회피율 증가
        invisibility_data = skill_data_firebase['기습']['values']
        DefenseIgnore_increase_level =  invisibility_data['은신공격_레벨당_방관_증가']
        DefenseIgnore_increase = DefenseIgnore_increase_level * skill_level
        invisibility_values = invisibility_data['기본_회피_증가'] + invisibility_data['레벨당_회피_증가'] * skill_level
        attacker["DefenseIgnore"] += DefenseIgnore_increase
        attacker["Evasion"] += invisibility_values
        invisibility_turns = invisibility_data['지속시간']
        apply_status_for_turn(attacker, "은신", duration=invisibility_turns, value = invisibility_values)  # 은신 상태 지속시간만큼 지속
        apply_status_for_turn(attacker, "기습", duration=invisibility_turns + 1)  # 은신 상태 지속시간만큼 지속
        skill_damage = 0
        attacker["Skills"]["기습"]["현재 쿨타임"] = 0 # 쿨타임 초기화
        attacker['evaded'] = False
        message = f"**<:surprise:1380504593317888053>기습** 사용! {invisibility_turns}턴간 은신! (회피 + {invisibility_values})\n"
        return message, skill_damage
    elif mode == "attack":
        if not evasion:
            skill_level = attacker["Skills"]["기습"]["레벨"]
            invisibility_data = skill_data_firebase['기습']['values']
            
            base_damage = invisibility_data['기본_피해량'] + invisibility_data['레벨당_피해량'] * skill_level
            attack_multiplier = (invisibility_data['기본_공격력_계수'] + invisibility_data['레벨당_공격력_계수'] * skill_level)
            speed_multiplier = (invisibility_data['기본_스피드_계수'] + invisibility_data['레벨당_스피드_계수'] * skill_level)

            skill_damage = base_damage + attack_multiplier * attacker['Attack'] + speed_multiplier * attacker['Speed']
            message = f"\n**<:surprise:1380504593317888053>기습** 사용! {round(skill_damage)}의 피해를 입힙니다!\n"

            evaded = attacker.get('evaded', False)
            if evaded: # 피격 X
                message += f"회피 추가 효과!, 상대에게 2턴간 침묵 부여!"
                apply_status_for_turn(defender, "침묵", 2)
        else:
            skill_damage = 0
            message = f"**<:surprise:1380504593317888053>기습**이 빗나갔습니다!\n"

        return message, skill_damage

def smash(attacker, defender, evasion, skill_level, skill_data_firebase):
    if not evasion:
        smash_data = skill_data_firebase['강타']['values']
        base_damage = smash_data['기본_피해량'] + smash_data['레벨당_피해량_증가'] * skill_level
        attack_multiplier = (smash_data['기본_공격력_계수'] + smash_data['레벨당_공격력_계수_증가'] * skill_level)
        attack_value = base_damage + attacker["Attack"] * attack_multiplier
        
        accuracy = calculate_accuracy(attacker["Accuracy"])
        skill_damage = random.uniform(attack_value * accuracy, attack_value)
        critical_bool = False
        stun_message = ""
        break_message = ""

        if "보호막" in defender['Status']:
            del defender['Status']['보호막'] # 보호막 파괴
            break_message = "🛡️ 보호막 파괴!\n"

        if random.random() < attacker["CritChance"]:
            skill_damage *= attacker["CritDamage"]
            critical_bool = True
            stun_message = "💥 치명타 발생! 적에게 1턴간 **기절** 부여!\n"
            apply_status_for_turn(defender,"기절",1)

        # 메시지
        message = (
            f"**<:smash:1380504562766712893>강타** 사용! **{int(skill_damage)}**의 피해!\n{break_message}{stun_message}"
        )

    else:
        # 회피 시
        skill_damage = 0
        message = "**<:smash:1380504562766712893>강타**가 빗나갔습니다!\n반동으로 한 턴간 **기절**!"
        apply_status_for_turn(attacker,"기절",1)
        critical_bool = False

    return message, skill_damage, critical_bool

def issen(attacker, defender, skill_level, skill_data_firebase):
    # 일섬 : 다음턴에 적에게 날카로운 참격을 가한다. 회피를 무시하고 명중률에 비례한 대미지를 입히며, 표식을 부여한다.
    # 출혈 상태일 경우, 출혈 상태 해제 후 남은 피해의 150%를 즉시 입히고, 해당 피해의 50%를 고정 피해로 변환

    apply_status_for_turn(defender, "일섬", duration=2)
    message = f"**<:issen:1380504641451593878>일섬** 사용!\n엄청난 속도로 적을 벤 후, 다음 턴에 날카로운 참격을 가합니다.\n회피를 무시하고 명중에 비례하는 대미지를 입힙니다.\n" 
    return message, 0

def headShot(attacker, evasion, skill_level, skill_data_firebase):
    """액티브 - 헤드샷"""
    if not evasion:
        headShot_data = skill_data_firebase['헤드샷']['values']
        crit_bonus = headShot_data['치명타_확률_증가']
        base_damage = headShot_data['기본_피해량'] + headShot_data['레벨당_피해량_증가'] * skill_level
        attack_multiplier = (headShot_data['기본_공격력_계수'] + headShot_data['레벨당_공격력_계수_증가'] * skill_level)
        attack_value = base_damage + attacker["Attack"] * attack_multiplier
        
        # 공격력, 치명타 확률을 보정한 공격
        accuracy = calculate_accuracy(attacker["Accuracy"])
        skill_damage = random.uniform(attack_value * accuracy, attack_value)
        critical_bool = False
        cooldown_message = ""
        if random.random() < attacker["CritChance"] + crit_bonus:
            skill_damage *= attacker["CritDamage"]
            critical_bool = True
            attacker["Skills"]["헤드샷"]["현재 쿨타임"] -= 1
            cooldown_message = "치명타로 헤드샷 쿨타임 1턴 감소!\n"

        # 메시지
        message = (
            f"**<:headShot:1380504463516893235>헤드샷** 사용! 치명타 확률 +{int(round(crit_bonus * 100))}%! {int(skill_damage)}의 피해!\n{cooldown_message}"
        )

        # 장전 상태 부여
        apply_status_for_turn(attacker, "장전", duration=1)
        message += "1턴간 **장전** 상태가 됩니다."

    else:
        # 회피 시
        skill_damage = 0
        message = "**<:headShot:1380504463516893235>헤드샷**이 빗나갔습니다!\n"
        critical_bool = False

    return message, skill_damage, critical_bool

def spearShot(attacker,defender,evasion,skill_level, skill_data_firebase):
    """ 창격 - 공격력 비례 스킬 대미지를 입히고, 4턴간 "꿰뚫림" 상태 부여 (최대 2스택)
        꿰뚫림 : 받는 피해가 30% 증가
        이미 꿰뚫림 2스택인 상대에게 창격 사용 시, 1턴간 기절 상태이상을 부여하며, 창격의 대미지가 2배가 된다.
    """
    spearShot_data = skill_data_firebase['창격']['values']
    if not evasion:
        base_damage = spearShot_data['기본_피해량'] + spearShot_data['레벨당_피해량_증가'] * skill_level
        attack_multiplier = (spearShot_data['기본_공격력_계수'] + spearShot_data['레벨당_공격력_계수_증가'] * skill_level)
        skill_damage = base_damage + attacker["Attack"] * attack_multiplier
        message = f"\n**<:spearShot:1380512916406796358>창격** 사용! {round(skill_damage)} 대미지!\n"
        if "꿰뚫림" in defender["Status"]:
            pierce_stack = defender["Status"]["꿰뚫림"]["value"]
            if pierce_stack == 2: # 2스택이 이미 쌓여있었다면?
                del defender["Status"]["꿰뚫림"] # 꿰뚫림 스택 삭제
                skill_damage *= 2 # 스킬 대미지 2배
                apply_status_for_turn(defender,"기절",1) # 기절 부여
                message += f"꿰뚫림 상태를 제거하고 창격 대미지 2배, 1턴간 **기절** 부여!\n"
                
            else: # 스택이 2 미만이라면
                apply_status_for_turn(defender,"꿰뚫림",4,pierce_stack + 1)
                message += f"꿰뚫림 스택 부여(**{pierce_stack + 1}**스택)! 받는 피해 {int(30 * (pierce_stack + 1))}% 증가!\n"
        else:
            apply_status_for_turn(defender,"꿰뚫림",4,1)
            message += f"꿰뚫림 스택 부여(**1**스택)! 받는 피해 30% 증가!\n"
    else:
        message = f"\n**<:spearShot:1380512916406796358>창격**이 빗나갔습니다!\n"
        skill_damage = 0


    return message,skill_damage
    
def mech_Arm(attacker,defender, evasion, skill_level, skill_data_firebase):
    # 전선더미 방출: (20 + 레벨 당 5) + 스킬 증폭 20% + 레벨당 10% 추가 피해
    if not evasion:
        mech_Arm_data = skill_data_firebase['전선더미 방출']['values']
        base_damage = mech_Arm_data['기본_피해량'] + mech_Arm_data['레벨당_피해량_증가'] * skill_level
        skill_multiplier = (mech_Arm_data['기본_스킬증폭_계수'] + mech_Arm_data['레벨당_스킬증폭_계수_증가'] * skill_level)
        skill_damage = base_damage + attacker["Spell"] * skill_multiplier
        speed_decrease = mech_Arm_data['레벨당_속도감소_배율'] * skill_level
        defender["Speed"] *= 1 - speed_decrease
        if defender["Speed"] < 0:
            defender["Speed"] = 0
        debuff_turns = mech_Arm_data['디버프_지속시간']
        apply_status_for_turn(defender, "둔화", duration=debuff_turns, value = speed_decrease)
        message = f"\n**<:siu_Q:1380505352025538601>전선더미 방출** 사용!\n{base_damage} + (스킬 증폭 {int(skill_multiplier * 100)}%)의 스킬 피해를 입힙니다!\n상대의 속도가 {debuff_turns}턴간 {int(speed_decrease * 100)}% 감소합니다!\n"
    else:
        skill_damage = 0
        message = f"\n**<:siu_Q:1380505352025538601>전선더미 방출이 빗나갔습니다!**\n"

    return message,skill_damage

def Shield(attacker, skill_level, skill_data_firebase):
    # 보호막: 스킬 증폭의 100% + 레벨당 10%만큼의 보호막을 얻음
    Shield_data = skill_data_firebase['보호막']['values']
    skill_multiplier = int(round((Shield_data['기본_스킬증폭_계수'] + Shield_data['레벨당_스킬증폭_계수'] * skill_level) * 100))
    shield_amount = int(round((skill_multiplier / 100) * attacker['Spell']))
    apply_status_for_turn(attacker,"보호막",3,shield_amount)
    message = f"\n**<:siu_E:1380505365791244338>보호막** 사용!\n{shield_amount}만큼의 보호막을 2턴간 얻습니다!\n"

    return message

def electronic_line(attacker,defender,skill_level, skill_data_firebase):
    # 전깃줄: (40 + 레벨 당 10) + 스킬 증폭 50% + 레벨당 20% 추가 피해
    electronic_line_data = skill_data_firebase['전깃줄']['values']
    base_damage = electronic_line_data['기본_피해량'] + electronic_line_data['레벨당_피해량_증가'] * skill_level
    skill_multiplier = (electronic_line_data['기본_스킬증폭_계수'] + electronic_line_data['레벨당_스킬증폭_계수_증가'] * skill_level)
    skill_damage = base_damage + attacker["Spell"] * skill_multiplier
    apply_status_for_turn(defender,"기절",1)
    message = f"\n**<:siu_R:1380505375412850698>전깃줄** 사용!\n상대에게 {base_damage} + (스킬 증폭 {int(skill_multiplier * 100)}%)의 스킬 피해!\n1턴간 기절 부여!"
    
    return message,skill_damage

def Reap(attacker, evasion, skill_level, skill_data_firebase):
    # 수확: (30 + 레벨 당 10) + 스킬 증폭 60% + 레벨 당 8% 추가 피해 + 공격력 20% + 레벨 당 5% 추가 피해
    if not evasion:
        Reap_data = skill_data_firebase['수확']['values']
        base_damage = Reap_data['기본_피해량'] + Reap_data['레벨당_피해량_증가'] * skill_level
        skill_multiplier = (Reap_data['기본_스킬증폭_계수'] + Reap_data['레벨당_스킬증폭_계수_증가'] * skill_level)
        attack_multiplier = (Reap_data['기본_공격력_계수'] + Reap_data['레벨당_공격력_계수_증가'] * skill_level)
        skill_damage = base_damage + attacker["Spell"] * skill_multiplier + attacker["Attack"] * attack_multiplier
        message = f"\n**<:reap:1380504495720759399>수확** 사용!\n상대에게 {base_damage} + (스킬 증폭 {int(skill_multiplier * 100)}%) + (공격력 {int(attack_multiplier * 100)}%)의 스킬 피해!\n"
    else:
        skill_damage = 0
        message = f"\n**<:reap:1380504495720759399>수확**이 빗나갔습니다!\n" 
    return message, skill_damage

def unyielding(defender, skill_level, skill_data_firebase):
    """불굴: 받는 대미지를 감소시킴"""
    unyielding_data = skill_data_firebase['불굴']['values']
    damage_reduction = min(unyielding_data['최대_피해감소율'], unyielding_data['기본_피해감소'] + unyielding_data['레벨당_피해감소'] * skill_level)  # 최대 90% 감소 제한
    apply_status_for_turn(defender, "불굴", 2)
    defender["DamageReduction"] = damage_reduction
    message = f"\n**<:braum_E:1380505187160035378>불굴** 발동!\n방패를 들어 2턴간 받는 대미지 {int(damage_reduction * 100)}% 감소!\n"
    damage = 0
    return message, damage

def concussion_punch(target):
    """패시브 - 뇌진탕 펀치: 공격 적중 시 뇌진탕 스택 부여, 4스택 시 기절"""
    target["뇌진탕"] = target.get("뇌진탕", 0) + 1

    message = f"**<:braum_P:1380505175973695538>뇌진탕 펀치** 효과로 뇌진탕 스택 {target['뇌진탕']}/4 부여!"
    
    if target["뇌진탕"] >= 4:
        target["뇌진탕"] = 0
        apply_status_for_turn(target, "기절", duration=1)
        message += f"\n**<:braum_P:1380505175973695538>뇌진탕 폭발!** {target['name']} 1턴간 기절!\n"
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

        message = f"\n**<:braum_Q:1380505142033645590>동상** 사용!\n{base_damage} + (스킬 증폭 {int(skill_multiplier * 100)}%)의 스킬 피해!\n뇌진탕을 부여하고, 스피드가 {debuff_turns}턴간 {int(speed_decrease * 100)}% 감소!\n뇌진탕 스택 {target['뇌진탕']}/4 부여!\n"
        
        if target["뇌진탕"] >= 4:
            target["뇌진탕"] = 0
            apply_status_for_turn(target, "기절", duration=1)
            message += f"\n**뇌진탕 폭발!** {target['name']} 1턴간 **기절!**\n"

    else:
        skill_damage = 0
        message = f"\n**<:braum_Q:1380505142033645590>동상이 빗나갔습니다!**\n"
    return message, skill_damage

def glacial_fissure(attacker, target, evasion,skill_level, skill_data_firebase):
    # 빙하 균열: (40 + 레벨 당 30) +스킬 증폭 60% + 레벨당 30%
    if not evasion:
        glacial_fissure_data = skill_data_firebase['빙하 균열']['values']       
        base_damage = glacial_fissure_data['기본_피해량'] + (glacial_fissure_data['레벨당_피해량_증가'] * skill_level)
        skill_multiplier = (glacial_fissure_data['기본_스킬증폭_계수'] + glacial_fissure_data['레벨당_스킬증폭_계수_증가'] * skill_level)
        skill_damage = base_damage + attacker["Spell"] * skill_multiplier
        apply_status_for_turn(target,"기절",1)

        message = f"\n**<:braum_R:1380505216688062464>빙하 균열** 사용!\n{base_damage} + (스킬 증폭 {int(round(skill_multiplier * 100))}%)의 스킬 피해!\n{target['name']} 1턴간 기절!\n"

    else:
        skill_damage = 0
        message = f"\n**<:braum_R:1380505216688062464>빙하 균열이 빗나갔습니다!**\n"
    return message, skill_damage

def rapid_fire(attacker, defender, skill_level, skill_data_firebase):
    """스피드에 비례하여 연속 공격하는 속사 스킬"""
    rapid_fire_data = skill_data_firebase['속사']['values']

    speed = attacker["Speed"]
    hit_count = 2 + speed // rapid_fire_data['타격횟수결정_스피드값'] # 최소 2회, 스피드 100당 1회 추가
    total_damage = 0

    def calculate_damage(attacker,defender, damage, multiplier):
        accuracy = calculate_accuracy(attacker["Accuracy"]) # 1 - 명중률 수치만큼 빗나갈 확률 상쇄 가능
        base_damage = random.uniform(damage * accuracy, damage)  # 최소 ~ 최대 피해
        critical_bool = False
        evasion_bool = False

        evasion_score = calculate_evasion_score(defender["Speed"])
        accuracy = calculate_accuracy(attacker["Accuracy"] - (evasion_score + defender['Evasion'])) # 1 - 명중률 수치만큼 빗나갈 확률 상쇄 가능
        accuracy = max(accuracy, 0.1)  # 최소 명중률 10%
        if random.random() > accuracy: # 회피
        #if random.random() > accuracy:
            evasion_bool = True
            return 0, False, evasion_bool

        # 피해 증폭
        base_damage *= 1 + attacker["DamageEnhance"]

        defense = max(0, defender["Defense"] - attacker["DefenseIgnore"])
        damage_reduction = calculate_damage_reduction(defense)
        defend_damage = base_damage * (1 - damage_reduction) * (multiplier)
        final_damage = defend_damage * (1 - defender['DamageReduction']) # 대미지 감소 적용
        return max(1, round(final_damage)), critical_bool, evasion_bool
        
    message = ""
    for i in range(hit_count):
        base_damage = rapid_fire_data['기본_대미지'] + rapid_fire_data['레벨당_대미지'] * skill_level
        attack_multiplier = rapid_fire_data['기본_공격력_계수'] + rapid_fire_data['레벨당_공격력_계수_증가'] * skill_level
        attack_damage = base_damage + attack_multiplier * attacker['Attack']
        multiplier = 1 + speed * rapid_fire_data['스피드당_계수'] # 0.004
        damage, critical, evade = calculate_damage(attacker, defender, attack_damage, multiplier=multiplier)

        crit_text = "💥" if critical else ""
        evade_text = "회피!⚡️" if evade else ""
        message += f"**{evade_text}{damage} 대미지!{crit_text}**\n"
        
        total_damage += damage
    
    message += f"<:rapid_fire:1380504532043300904>**속사**로 {hit_count}연타 공격! 총 {total_damage} 피해!"
    return message,total_damage

def meditate(attacker, skill_level,skill_data_firebase):
    # 명상 : 모든 스킬 쿨타임 감소 + 스킬 증폭 비례 보호막 획득, 명상 스택 획득
    meditate_data = skill_data_firebase['명상']['values']
    shield_amount = int(round(attacker['Spell'] * (meditate_data['스킬증폭당_보호막_계수'] + meditate_data['레벨당_보호막_계수_증가'] * skill_level)))
    for skill, cooldown_data in attacker["Skills"].items():
        if cooldown_data["현재 쿨타임"] > 0 and skill != "명상":
            attacker["Skills"][skill]["현재 쿨타임"] -= 1  # 현재 쿨타임 감소
    attacker['명상'] = attacker.get("명상", 0) + 1 # 명상 스택 + 1 추가
    apply_status_for_turn(attacker,"보호막",1,shield_amount)
    message = f"**<:meditation:1380504431992373431>명상** 사용!(현재 명상 스택 : {attacker['명상']})\n 모든 스킬의 현재 쿨타임이 1턴 감소하고 1턴간 {shield_amount}의 보호막 생성!\n"

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
            message = f"**<:meteor:1380503739307393035>메테오** 사용!\n {base_damage} + 스킬증폭 {round(skill_multiplier * 100)}%의 스킬피해!\n1턴간 기절 부여 및 3턴간 화상 부여!"
        else:
            skill_damage = 0
            message = f"**<:meteor:1380503739307393035>메테오**가 빗나갔습니다!\n"
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
            message = f"**<:flare:1380503684567273552>플레어** 사용!\n {base_damage} + 스킬증폭 {round(skill_multiplier * 100)}%의 스킬피해!\n1턴간 화상 부여!"
        else:
            skill_damage = 0
            message = f"**<:flare:1380503684567273552>플레어**가 빗나갔습니다!\n"
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
            message = f"**<:blizzard:1380504269823803392>블리자드** 사용!\n {base_damage} + 스킬증폭 {round(skill_multiplier * 100)}%의 스킬피해!\n3턴간 빙결 부여!, 5턴간 {slow_amount}% 둔화 부여!"
        else:
            skill_damage = 0
            message = f"**<:blizzard:1380504269823803392>블리자드**가 빗나갔습니다!\n"
    else:
        # 프로스트
        if not evasion:
            base_damage = ice_data['기본_피해량'] + ice_data['레벨당_기본_피해량_증가'] * skill_level
            skill_multiplier = ice_data['기본_스킬증폭_계수'] + ice_data['레벨당_스킬증폭_계수_증가'] * skill_level
            skill_damage = base_damage + attacker['Spell'] * skill_multiplier
            apply_status_for_turn(defender, "빙결", 1)
            message = f"**<:frost:1380504246436233226>프로스트** 사용!\n {base_damage} + 스킬증폭 {round(skill_multiplier * 100)}%의 스킬피해!\n1턴간 빙결 부여!"
        else:
            skill_damage = 0
            message = f"**<:frost:1380504246436233226>프로스트**가 빗나갔습니다!\n"
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
            message = f"**<:judgement:1380504404263829565>저지먼트** 사용!\n {base_damage} + 스킬증폭 {round(skill_multiplier * 100)}%의 스킬피해!\n3턴간 침묵 부여!"
        else:
            skill_damage = 0
            message = f"**<:judgement:1380504404263829565>저지먼트**가 빗나갔습니다!\n"
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
                healban_amount = min(1, attacker['Status']['치유 감소']['value'])
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
                message = f"**<:bless:1380504375276867605>블레스** 사용!\n {base_damage} + 스킬증폭 {round(skill_multiplier * 100)}%의 스킬피해!\n{heal_amount}(-{reduced_heal})만큼 내구도 회복!\n내구도: [{initial_HP}] → [{final_HP}] ❤️ (+{final_HP - initial_HP})"
            else:
                message = f"**<:bless:1380504375276867605>블레스** 사용!\n {base_damage} + 스킬증폭 {round(skill_multiplier * 100)}%의 스킬피해!\n{heal_amount}만큼 내구도 회복!\n내구도: [{initial_HP}] → [{final_HP}] ❤️ (+{final_HP - initial_HP})"
        else:
            skill_damage = 0
            message = f"**<:bless:1380504375276867605>블레스**가 빗나갔습니다!\n"
    return message,skill_damage

def second_skin(target, skill_level, value, skill_data_firebase):
    """패시브 - 두번째 피부: 공격 적중 시 플라즈마 중첩 부여, 5스택 시 현재 체력 비례 10% 대미지"""
    target["플라즈마 중첩"] = target.get("플라즈마 중첩", 0) + value
    message = f"<:kaisa_P:1380505278109454417>**두번째 피부** 효과로 플라즈마 중첩 {target['플라즈마 중첩']}/5 부여!"

    second_skin_data = skill_data_firebase['두번째 피부']['values']
    skill_damage = 0
    
    if target["플라즈마 중첩"] >= 5:
        target["플라즈마 중첩"] = 0
        skill_damage = round(target['HP'] * (second_skin_data['기본_대미지'] + second_skin_data['레벨당_추가_대미지'] * skill_level))
        damage_value = round((second_skin_data['기본_대미지'] + second_skin_data['레벨당_추가_대미지'] * skill_level) * 100)
        message += f"\n<:kaisa_P:1380505278109454417>**플라즈마 폭발!** 현재 내구도의 {damage_value}% 대미지!\n"
    return message, skill_damage

def icathian_rain(attacker, defender, skill_level, skill_data_firebase):
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
        evasion_score = calculate_evasion_score(defender["Speed"])
        accuracy = calculate_accuracy(attacker["Accuracy"] - (evasion_score + defender['Evasion'])) # 1 - 명중률 수치만큼 빗나갈 확률 상쇄 가능
        accuracy = max(accuracy, 0.1)  # 최소 명중률 10%
        if random.random() > accuracy: # 회피
        # if random.random() > accuracy: # 회피
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
    message += f"<:kaisa_Q:1380505235503448176>이케시아 폭우로 {hit_count}연타 공격! 총 {total_damage} 피해!\n"
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

        message = f"\n<:kaisa_W:1380505250892480592>**공허추적자** 사용!\n스킬 증폭 {int(round(skill_multiplier * 100))}%의 스킬 피해를 입히고 1턴간 속박!\n"
        passive_skill_data = attacker["Skills"].get("두번째 피부", None)   
        passive_skill_level = passive_skill_data["레벨"]
        passive_message, explosion_damage = second_skin(defender, passive_skill_level, 2, skill_data_firebase)
        message += passive_message
        skill_damage += explosion_damage
    else:
        skill_damage = 0
        message = f"\n**<:kaisa_W:1380505250892480592>공허추적자**가 빗나갔습니다!\n"
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
    return f"<:kaisa_E:1380505268898631803>**고속충전** 사용! {invisibility_turns}턴간 은신 상태에 돌입합니다!\n{speedup_turns}턴간 스피드가 {speedup_value} 증가합니다!\n"

def killer_instinct(attacker, defender, skill_level, skill_data_firebase):
    # 사냥본능: 2턴간 보호막을 얻음.
    killer_instinct_data = skill_data_firebase['사냥본능']['values']

    shield_amount = killer_instinct_data['기본_보호막량'] + killer_instinct_data['레벨당_보호막량'] * skill_level
    apply_status_for_turn(attacker,"보호막",3,shield_amount)
    return f"**<:kaisa_E:1380505268898631803>사냥본능** 사용! 2턴간 {shield_amount}의 보호막을 얻습니다!\n"

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
    #불꽃 펀치 : 공격력 기반 피해를 입히고, 50% 확률로 2턴간 화상 상태 부여
    if not evasion:
        poison_jab_data = skill_data_firebase['불꽃 펀치']['values']    
        attack_multiplier = (poison_jab_data['기본_공격력_계수'] + poison_jab_data['레벨당_공격력_계수_증가'] * skill_level)
        skill_damage = attacker["Attack"] * attack_multiplier
        
        message = f"\n**불꽃 펀치** 사용!\n공격력 {int(round(attack_multiplier * 100))}%의 스킬 피해!\n"
        cc_probability = poison_jab_data['화상_확률'] + poison_jab_data['레벨당_화상_확률'] * skill_level
        if random.random() < cc_probability: # 확룰에 따라 화상 부여
            burn_damage = poison_jab_data['화상_대미지'] + poison_jab_data['레벨당_화상_대미지'] * skill_level
            apply_status_for_turn(defender,"화상",2, burn_damage)
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
