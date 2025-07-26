import random
from .battle_utils import calculate_accuracy, calculate_evasion_score
from .status import apply_status_for_turn, remove_status_effects
from .battle_utils import calculate_damage_reduction
from .skill_emoji import skill_emojis

def invisibility(attacker, defender, evasion, skill_level, skill_data_firebase, mode = "buff"):
    if mode == "buff":
        # 은신 상태에서 회피율 증가
        invisibility_data = skill_data_firebase['기습']['values']
        invisibility_values = invisibility_data['기본_회피_증가'] + invisibility_data['레벨당_회피_증가'] * skill_level
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
            message = f"\n**{skill_emojis['기습']}기습** 사용! {round(skill_damage)}의 피해를 입힙니다!\n"

            evaded = attacker.get('evaded', False)
            if evaded: # 피격 X
                message += f"회피 추가 효과!, 상대에게 2턴간 침묵 부여!\n"
                apply_status_for_turn(defender, "침묵", 2)
        else:
            skill_damage = 0
            message = f"**{skill_emojis['기습']}기습**이 빗나갔습니다!\n"

        return message, skill_damage

def smash(attacker, defender, evasion, skill_level, skill_data_firebase):
    if not evasion:
        smash_data = skill_data_firebase['강타']['values']
        base_damage = smash_data['기본_피해량'] + smash_data['레벨당_피해량_증가'] * skill_level
        attack_multiplier = (smash_data['기본_공격력_계수'] + smash_data['레벨당_공격력_계수_증가'] * skill_level)
        attack_value = base_damage + attacker["Attack"] * attack_multiplier
        
        evasion_score = calculate_evasion_score(defender["Speed"])
        accuracy = calculate_accuracy(attacker["Accuracy"], evasion_score + defender['Evasion'])
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
            f"**{skill_emojis['강타']}강타** 사용! **{int(skill_damage)}**의 피해!\n{break_message}{stun_message}"
        )

    else:
        # 회피 시
        skill_damage = 0
        message = f"**{skill_emojis['강타']}강타**가 빗나갔습니다!\n반동으로 한 턴간 **기절**!\n"
        apply_status_for_turn(attacker,"기절",1, source_id = defender['Id'])
        critical_bool = False

    return message, skill_damage, critical_bool

def issen(attacker, defender, skill_level, skill_data_firebase):
    # 일섬 : 다음턴에 적에게 날카로운 참격을 가한다. 회피를 무시하고 명중률에 비례한 대미지를 입히며, 표식을 부여한다.
    # 출혈 상태일 경우, 출혈 상태 해제 후 남은 피해의 150%를 즉시 입히고, 해당 피해의 50%를 고정 피해로 변환
    damage = 0
    message = ""
    if "일섬" in defender.get("Status", {}):
        if defender["Status"]["일섬"]["duration"] >= 1:
            message += f"**{skill_emojis['일섬']}일섬 - 중첩 발동!**\n{attacker['name']}이(가) 대기 중이던 일섬을 발동합니다!\n"

            issen_data = skill_data_firebase['일섬']['values']
            skill_level = attacker['Skills']['일섬']['레벨']

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
            total_issen_damage, critical, explosion_damage, bleed_explosion = calculate_damage(attacker, defender, 1)

            # 3. 결과 메시지 생성 및 출력
            apply_status_for_turn(defender, "출혈", 2, bleed_damage)
            message += f"🩸 2턴간 출혈 부여!\n"
            
            crit_text = "💥" if critical else ""
            explosion_message = ""
            if bleed_explosion:
                if '출혈' in attacker["Status"]: 
                    del attacker["Status"]['출혈']
                    message += "출혈 추가 효과! 남은 출혈 대미지를 더하고\n총 피해의 50%를 고정피해로 입힙니다.\n",
                    explosion_message = f"(+🩸{explosion_damage} 대미지)"

            damage += total_issen_damage
    apply_status_for_turn(defender, "일섬", duration=2)
    message += f"**{skill_emojis['일섬']}일섬** 사용!\n{attacker['name']}이(가) 준비자세를 취합니다." 
    return message, damage

def headShot(attacker, defender, evasion, skill_level, skill_data_firebase):
    """액티브 - 헤드샷"""
    if not evasion:
        headShot_data = skill_data_firebase['헤드샷']['values']
        crit_bonus = headShot_data['치명타_확률_증가']
        base_damage = headShot_data['기본_피해량'] + headShot_data['레벨당_피해량_증가'] * skill_level
        attack_multiplier = (headShot_data['기본_공격력_계수'] + headShot_data['레벨당_공격력_계수_증가'] * skill_level)
        attack_value = base_damage + attacker["Attack"] * attack_multiplier
        
        # 공격력, 치명타 확률을 보정한 공격
        evasion_score = calculate_evasion_score(defender["Speed"])
        accuracy = calculate_accuracy(attacker["Accuracy"], evasion_score + defender["Evasion"])
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
            f"**{skill_emojis['헤드샷']}헤드샷** 사용! 치명타 확률 +{int(round(crit_bonus * 100))}%! {int(skill_damage)}의 피해!\n{cooldown_message}"
        )

        # 장전 상태 부여
        apply_status_for_turn(attacker, "장전", duration=1, source_id=defender['Id'])
        message += "1턴간 **장전** 상태가 됩니다."

    else:
        # 회피 시
        skill_damage = 0
        message = f"**{skill_emojis['헤드샷']}헤드샷**이 빗나갔습니다!\n"
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
        message = f"\n**{skill_emojis['창격']}창격** 사용! {round(skill_damage)} 대미지!\n"
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
        message = f"\n**{skill_emojis['창격']}창격**이 빗나갔습니다!\n"
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
        message = f"\n**{skill_emojis['전선더미 방출']}전선더미 방출** 사용!\n{base_damage} + (스킬 증폭 {int(skill_multiplier * 100)}%)의 스킬 피해를 입힙니다!\n상대의 속도가 {debuff_turns}턴간 {int(speed_decrease * 100)}% 감소합니다!\n"
    else:
        skill_damage = 0
        message = f"\n**{skill_emojis['전선더미 방출']}전선더미 방출이 빗나갔습니다!**\n"

    return message,skill_damage

def Shield(attacker, skill_level, skill_data_firebase):
    # 보호막: 스킬 증폭의 100% + 레벨당 10%만큼의 보호막을 얻음
    Shield_data = skill_data_firebase['보호막']['values']
    skill_multiplier = int(round((Shield_data['기본_스킬증폭_계수'] + Shield_data['레벨당_스킬증폭_계수'] * skill_level) * 100))
    shield_amount = int(round((skill_multiplier / 100) * attacker['Spell']))
    apply_status_for_turn(attacker,"보호막",3,shield_amount)
    message = f"\n**{skill_emojis['보호막']}보호막** 사용!\n{shield_amount}만큼의 보호막을 2턴간 얻습니다!\n"

    return message

def electronic_line(attacker,defender,skill_level, skill_data_firebase):
    # 전깃줄: (40 + 레벨 당 10) + 스킬 증폭 50% + 레벨당 20% 추가 피해
    electronic_line_data = skill_data_firebase['전깃줄']['values']
    base_damage = electronic_line_data['기본_피해량'] + electronic_line_data['레벨당_피해량_증가'] * skill_level
    skill_multiplier = (electronic_line_data['기본_스킬증폭_계수'] + electronic_line_data['레벨당_스킬증폭_계수_증가'] * skill_level)
    skill_damage = base_damage + attacker["Spell"] * skill_multiplier
    apply_status_for_turn(defender,"기절",1)
    message = f"\n**{skill_emojis['전깃줄']}전깃줄** 사용!\n상대에게 {base_damage} + (스킬 증폭 {int(skill_multiplier * 100)}%)의 스킬 피해!\n1턴간 기절 부여!\n"
    
    return message,skill_damage

def Reap(attacker, evasion, skill_level, skill_data_firebase):
    # 수확: (30 + 레벨 당 10) + 스킬 증폭 60% + 레벨 당 8% 추가 피해 + 공격력 20% + 레벨 당 5% 추가 피해
    if not evasion:
        Reap_data = skill_data_firebase['수확']['values']
        base_damage = Reap_data['기본_피해량'] + Reap_data['레벨당_피해량_증가'] * skill_level
        skill_multiplier = (Reap_data['기본_스킬증폭_계수'] + Reap_data['레벨당_스킬증폭_계수_증가'] * skill_level)
        attack_multiplier = (Reap_data['기본_공격력_계수'] + Reap_data['레벨당_공격력_계수_증가'] * skill_level)
        skill_damage = base_damage + attacker["Spell"] * skill_multiplier + attacker["Attack"] * attack_multiplier
        message = f"\n**{skill_emojis['수확']}수확** 사용!\n상대에게 {base_damage} + (스킬 증폭 {int(skill_multiplier * 100)}%) + (공격력 {int(attack_multiplier * 100)}%)의 스킬 피해!\n"
    else:
        skill_damage = 0
        message = f"\n**{skill_emojis['수확']}수확**이 빗나갔습니다!\n" 
    return message, skill_damage

def unyielding(attacker, defender, skill_level, skill_data_firebase):
    """불굴: 받는 대미지를 감소시킴"""
    unyielding_data = skill_data_firebase['불굴']['values']
    damage_reduction = min(unyielding_data['최대_피해감소율'], unyielding_data['기본_피해감소'] + unyielding_data['레벨당_피해감소'] * skill_level)  # 최대 90% 감소 제한
    apply_status_for_turn(attacker, "불굴", 2, source_id= defender['Id'])
    attacker["DamageReduction"] = damage_reduction
    message = f"\n**{skill_emojis['불굴']}불굴** 발동!\n방패를 들어 2턴간 받는 대미지 {int(damage_reduction * 100)}% 감소!\n"
    damage = 0
    return message, damage

def concussion_punch(target):
    """패시브 - 뇌진탕 펀치: 공격 적중 시 뇌진탕 스택 부여, 4스택 시 기절"""
    target["뇌진탕"] = target.get("뇌진탕", 0) + 1

    message = f"**{skill_emojis['뇌진탕 펀치']}뇌진탕 펀치** 효과로 뇌진탕 스택 {target['뇌진탕']}/4 부여!\n"
    
    if target["뇌진탕"] >= 4:
        target["뇌진탕"] = 0
        apply_status_for_turn(target, "기절", duration=1)
        message += f"\n**{skill_emojis['뇌진탕 펀치']}뇌진탕 폭발!** {target['name']} 1턴간 기절!\n"
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
        speed_decrease = frostbite_data['속도감소_기본수치'] + (frostbite_data['레벨당_속도감소_증가'] * skill_level)
        apply_status_for_turn(target, "둔화", duration=debuff_turns, value = speed_decrease)
        target["뇌진탕"] = target.get("뇌진탕", 0) + 1
        message = f"\n**{skill_emojis['동상']}동상** 사용!\n{base_damage} + (스킬 증폭 {int(skill_multiplier * 100)}%)의 스킬 피해!\n뇌진탕을 부여하고, 스피드가 {debuff_turns}턴간 {int(speed_decrease * 100)}% 감소!\n뇌진탕 스택 {target['뇌진탕']}/4 부여!\n"
        
        if target["뇌진탕"] >= 4:
            target["뇌진탕"] = 0
            apply_status_for_turn(target, "기절", duration=1)
            message += f"\n**{skill_emojis['뇌진탕 펀치']}뇌진탕 폭발!** {target['name']} 1턴간 **기절!**\n"

    else:
        skill_damage = 0
        message = f"\n**{skill_emojis['동상']}동상이 빗나갔습니다!**\n"
    return message, skill_damage

def glacial_fissure(attacker, target, evasion,skill_level, skill_data_firebase):
    # 빙하 균열: (40 + 레벨 당 30) +스킬 증폭 60% + 레벨당 30%
    if not evasion:
        glacial_fissure_data = skill_data_firebase['빙하 균열']['values']       
        base_damage = glacial_fissure_data['기본_피해량'] + (glacial_fissure_data['레벨당_피해량_증가'] * skill_level)
        skill_multiplier = (glacial_fissure_data['기본_스킬증폭_계수'] + glacial_fissure_data['레벨당_스킬증폭_계수_증가'] * skill_level)
        skill_damage = base_damage + attacker["Spell"] * skill_multiplier
        apply_status_for_turn(target,"기절",1)

        message = f"\n**{skill_emojis['빙하 균열']}빙하 균열** 사용!\n{base_damage} + (스킬 증폭 {int(round(skill_multiplier * 100))}%)의 스킬 피해!\n{target['name']} 1턴간 기절!\n"

    else:
        skill_damage = 0
        message = f"\n**{skill_emojis['빙하 균열']}빙하 균열이 빗나갔습니다!**\n"
    return message, skill_damage

def rapid_fire(attacker, defender, skill_level, skill_data_firebase):
    """스피드에 비례하여 연속 공격하는 속사 스킬"""
    rapid_fire_data = skill_data_firebase['속사']['values']

    speed = attacker["Speed"]
    hit_count = 2 + speed // rapid_fire_data['타격횟수결정_스피드값'] # 최소 2회, 스피드 100당 1회 추가
    total_damage = 0

    def calculate_damage(attacker,defender, damage, multiplier):
        evasion_score = calculate_evasion_score(defender["Speed"])
        accuracy = calculate_accuracy(attacker["Accuracy"], evasion_score + defender["Evasion"]) # 1 - 명중률 수치만큼 빗나갈 확률 상쇄 가능
        base_damage = random.uniform(damage * accuracy, damage)  # 최소 ~ 최대 피해
        critical_bool = False
        evasion_bool = False

        accuracy = max(accuracy, 0.1)  # 최소 명중률 10%
        if "속박" not in defender["Status"]:
            if random.random() > accuracy: # 회피
            #if random.random() > accuracy:
                evasion_bool = True
                if "기습" in defender["Status"]:
                    defender['evaded'] = True
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
    
    message += f"{skill_emojis['속사']}**속사**로 {hit_count}연타 공격! 총 {total_damage} 피해!\n"
    return message,total_damage

def meditate(attacker, defender, skill_level, skill_data_firebase, acceleration_triggered=False, overdrive_triggered=False):
    stacks_to_add = 1
    acceleration_message = ""
    chained_skills = []

    # [핵심 수정 7] 전달받은 값에 따라 추가 스택 결정
    if overdrive_triggered:
        stacks_to_add += 2
        acceleration_message = "초가속으로"
    elif acceleration_triggered:
        stacks_to_add += 1
        acceleration_message = "가속으로"

    attacker["명상"] = attacker.get("명상", 0) + stacks_to_add
    
    meditate_data = skill_data_firebase['명상']['values']
    shield_amount = int(round(attacker['Spell'] * (meditate_data['스킬증폭당_보호막_계수'] + meditate_data['레벨당_보호막_계수_증가'] * skill_level)))

    # 쿨타임 감소 로직 및 연계 스킬 확인
    for skill_name, cooldown_data in attacker["Skills"].items():
        if cooldown_data["현재 쿨타임"] > 0 and skill_name != "명상":
            original_cooldown = cooldown_data["현재 쿨타임"]
            new_cooldown = max(0, original_cooldown - stacks_to_add)
            attacker["Skills"][skill_name]["현재 쿨타임"] = new_cooldown
            
            # [핵심] 쿨타임이 0이 되었다면, 연계 목록에 추가
            if original_cooldown > 0 and new_cooldown == 0:
                chained_skills.append(skill_name)
            
    shield_cap = int(shield_amount / 5) # 최대 보호막량의 1/5로 제한
    final_shield_amount = min(shield_amount, shield_cap * attacker['명상']) # 명상 스택을 곱함
    apply_status_for_turn(attacker,"보호막",1,final_shield_amount, source_id= defender['Id'])
    apply_status_for_turn(attacker,"속박",1,source_id=defender['Id']) # 속박
    
    if acceleration_message:
        message = f"**{skill_emojis['명상']}명상** 사용! {acceleration_message} 스택을 **{stacks_to_add}** 획득합니다! (현재: {attacker.get('명상', 0)})\n"
    else:
        message = f"**{skill_emojis['명상']}명상** 사용! 스택을 **{stacks_to_add}** 획득합니다! (현재: {attacker.get('명상', 0)})\n"

    message += f"다른 모든 스킬의 쿨타임을 **{stacks_to_add}**만큼 감소시킵니다.\n"    
    message += f"**{final_shield_amount}**의 보호막을 얻고, 1턴간 **속박** 상태가 됩니다.\n"
    
    return message, 0, chained_skills

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
            apply_status_for_turn(defender, "치유 감소", 3, fire_data['화상_치유감소_수치'])
            message = f"**{skill_emojis['메테오']}메테오** 사용!\n {base_damage} + 스킬증폭 {round(skill_multiplier * 100)}%의 스킬피해!\n1턴간 기절 부여 및 3턴간 화상 부여!\n"
        else:
            skill_damage = 0
            message = f"**{skill_emojis['메테오']}메테오**가 빗나갔습니다!\n"
    else:
        # 플레어
        if not evasion:
            base_damage = fire_data['기본_피해량'] + fire_data['레벨당_기본_피해량_증가'] * skill_level
            skill_multiplier = fire_data['기본_스킬증폭_계수'] + fire_data['레벨당_스킬증폭_계수_증가'] * skill_level
            skill_damage = base_damage + attacker['Spell'] * skill_multiplier
            burn_skill_multiplier = fire_data['화상_기본_스킬증폭_계수'] + fire_data['화상_레벨당_스킬증폭_계수_증가'] * skill_level
            burn_damage = round(fire_data['화상_대미지'] * skill_level + attacker['Spell'] * burn_skill_multiplier)
            apply_status_for_turn(defender, "화상", 1, burn_damage)
            apply_status_for_turn(defender, "치유 감소", 1, fire_data['화상_치유감소_수치'])
            message = f"**{skill_emojis['플레어']}플레어** 사용!\n {base_damage} + 스킬증폭 {round(skill_multiplier * 100)}%의 스킬피해!\n1턴간 화상 부여!\n"
        else:
            skill_damage = 0
            message = f"**{skill_emojis['플레어']}플레어**가 빗나갔습니다!\n"
    return message,skill_damage

def ice_frost(attacker, defender, evasion, skill_level, skill_data_firebase):
    """프로스트: 기본 피해를 계산하고, 동상 스택을 +2 부여합니다."""
    frost_data = skill_data_firebase.get('냉기 마법', {}).get('values', {})
    
    if evasion:
        return f"{skill_emojis['프로스트']}프로스트가 빗나갔습니다!\n", 0

            
    # 1. 스킬을 사용하기 "전"의 동상 스택을 먼저 가져옵니다.
    frostbite_status = defender.get('Status', {}).get('동상', {})
    # value가 딕셔너리일 수 있으므로, .get('stacks', 0)으로 안전하게 접근
    current_frostbite_stacks = frostbite_status.get('value', {}).get('stacks', 0)

    # 2. 현재 스택을 기준으로 피해량 증폭률을 계산합니다.
    damage_multiplier = 1 + (current_frostbite_stacks * 0.3)

    # 3. 증폭된 최종 기본 피해량을 계산합니다.
    base_damage = frost_data['기본_피해량'] + frost_data['레벨당_기본_피해량_증가'] * skill_level
    skill_multiplier = frost_data['기본_스킬증폭_계수'] + frost_data['레벨당_스킬증폭_계수_증가'] * skill_level
    skill_damage = base_damage + attacker['Spell'] * skill_multiplier

    final_damage = skill_damage * damage_multiplier
    
    # 4. 피해량 계산이 끝난 후, 대상의 동상 스택을 +2 부여합니다.
    new_stacks = current_frostbite_stacks + 2
    apply_status_for_turn(defender, '동상', 99, value={'stacks': new_stacks})
    
    message = f"{skill_emojis['프로스트']}**프로스트** 사용!\n동상 스택을 +2 부여합니다! (현재: {new_stacks} 스택)\n"
    return message, final_damage

def ice_blizzard(attacker, defender, evasion, skill_level, skill_data_firebase):
    """블리자드: 피해를 주지 않고, 3턴간 '눈보라' 버프를 부여합니다."""
    blizzard_data = skill_data_firebase.get('냉기 마법', {}).get('values', {})
    # [수정] '블리자드'는 이제 회피의 영향을 받지 않는 버프 스킬이 됩니다.
    # if evasion:
    #     return f"{skill_emojis['블리자드']}블리자드가 빗나갔지만, 눈보라는 시작됩니다!\n", 0

    # 틱당 대미지 계산
    base_damage = blizzard_data['눈보라_기본_피해량'] + blizzard_data['눈보라_레벨당_기본_피해량_증가'] * skill_level
    skill_multiplier = blizzard_data['눈보라_기본_스킬증폭_계수'] + blizzard_data['눈보라_레벨당_스킬증폭_계수_증가'] * skill_level
    skill_damage = base_damage + attacker['Spell'] * skill_multiplier
    # '눈보라' 버프 부여
    apply_status_for_turn(attacker, '눈보라', 3, value = skill_damage)
    
    # [수정] 즉발 피해가 없음을 명확히 하는 메시지
    message = f"{skill_emojis['블리자드']}**블리자드** 시전!\n3턴 동안 **눈보라**가 전장을 뒤덮습니다!\n"
    
    # [수정] 피해량이 없으므로 0을 반환
    return message, 0

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
            message = f"**{skill_emojis['저지먼트']}저지먼트** 사용!\n {base_damage} + 스킬증폭 {round(skill_multiplier * 100)}%의 스킬피해!\n3턴간 침묵 부여!\n"
        else:
            skill_damage = 0
            message = f"**{skill_emojis['저지먼트']}저지먼트**가 빗나갔습니다!\n"
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
                message = f"**{skill_emojis['블레스']}블레스** 사용!\n {base_damage} + 스킬증폭 {round(skill_multiplier * 100)}%의 스킬피해!\n{heal_amount}(-{reduced_heal})만큼 내구도 회복!\n내구도: [{initial_HP} → {final_HP}] ❤️ (+{final_HP - initial_HP})\n"
            else:
                message = f"**{skill_emojis['블레스']}블레스** 사용!\n {base_damage} + 스킬증폭 {round(skill_multiplier * 100)}%의 스킬피해!\n{heal_amount}만큼 내구도 회복!\n내구도: [{initial_HP} → {final_HP}] ❤️ (+{final_HP - initial_HP})\n"
        else:
            skill_damage = 0
            message = f"**{skill_emojis['블레스']}블레스**가 빗나갔습니다!\n"
    return message,skill_damage

def wind_gale(attacker, evasion, skill_level, skill_data_firebase):
    """
    게일: 스킬 증폭과 스피드에 비례한 피해를 입힙니다.
    질풍 스택을 1개 부여합니다.
    """
    current_stacks = attacker.get('Status', {}).get('질풍', {}).get('value',{}).get('stacks', 0)
    if not evasion:
        new_stacks = current_stacks + 1
        
        skill_level = attacker["Skills"]["질풍 마법"]["레벨"]
        wind_gale_data = skill_data_firebase['질풍 마법']['values']
        
        base_damage = wind_gale_data['기본_피해량'] + wind_gale_data['레벨당_피해량'] * skill_level
        spell_multiplier = (wind_gale_data['기본_스킬증폭_계수'] + wind_gale_data['레벨당_스킬증폭_계수'] * skill_level)
        speed_multiplier = (wind_gale_data['기본_스피드_계수'] + wind_gale_data['레벨당_스피드_계수'] * skill_level)

        skill_damage = base_damage + spell_multiplier * attacker['Spell'] + speed_multiplier * attacker['Speed']
        
        # 질풍 버프 적용 (지속시간은 매우 길게)
        apply_status_for_turn(attacker, '질풍', 99, value ={'stacks': new_stacks})
        
        message = f"{skill_emojis['게일']}**게일** 사용!\n강한 바람을 일으켜 **질풍** 스택을 +1 얻습니다!\n"
    else:
        skill_damage = 0
        message = f"**{skill_emojis['게일']}게일**이 빗나갔습니다!\n"
    return message, skill_damage

def wind_tornado(
    attacker, defender, skill_level, skill_data_firebase, 
    acceleration_triggered=False, overdrive_triggered=False
):
    """
    토네이도: 가속 여부에 따라 여러 번 타격하며, 매 타격마다 스탯을 재계산하여 강해집니다.
    """
    tornado_data = skill_data_firebase.get('질풍 마법', {}).get('values', {})
    
    # 1. 가속 여부에 따라 타격 횟수 결정
    num_hits = 1
    if overdrive_triggered:
        num_hits = 3
    elif acceleration_triggered:
        num_hits = 2
        
    total_damage = 0
    message = f"{skill_emojis.get('토네이도', '🌪️')}**토네이도** 사용! ({num_hits}회 타격)\n"
    hit_damage_messages = []

    # 2. 루프를 돌며 각 타격 처리
    for i in range(num_hits):
        # a. [타격 시작] 현재 스탯으로 먼저 재계산 (이전 타격의 영향 반영)
        remove_status_effects(attacker, skill_data_firebase)
        
        # b. 회피 판정
        is_hit_this_time = False
        if "속박" in defender.get("Status", {}):
            is_hit_this_time = True
        else:
            evasion_score = calculate_evasion_score(defender["Speed"])
            accuracy = calculate_accuracy(attacker["Accuracy"], evasion_score + defender["Evasion"])
            is_hit_this_time = (random.random() <= max(accuracy, 0.1))

        if is_hit_this_time:
            # c. 명중 시: 질풍 스택 +1 부여
            current_stacks = attacker.get('Status', {}).get('질풍', {}).get('value',{}).get('stacks', 0)
            new_stacks = current_stacks
            apply_status_for_turn(attacker, '질풍', 99, value = {'stacks': new_stacks})
            
            # d. [매우 중요] 스택 부여 후, 스탯을 즉시 재계산하여 이번 타격의 데미지에 반영
            remove_status_effects(attacker, skill_data_firebase)

            # e. 최신 스탯을 기준으로 '기본 스킬 피해량' 계산
            base_damage = tornado_data.get('강화_기본_피해량', 20) + tornado_data.get('강화_레벨당_피해량', 3) * skill_level
            spell_multiplier = tornado_data.get('강화_기본_스킬증폭_계수', 0.15) + tornado_data.get('강화_레벨당_스킬증폭_계수', 0.01) * skill_level
            speed_multiplier = tornado_data.get('강화_기본_스피드_계수', 0.08) + tornado_data.get('강화_레벨당_스피드_계수', 0.01) * skill_level
            
            skill_damage = base_damage + (spell_multiplier * attacker['Spell']) + (speed_multiplier * attacker['Speed'])
            
            # f. 방어력 계산까지 완료된 '최종 피해량' 계산 및 저장
            damage_with_enhance = skill_damage * (1 + attacker.get("DamageEnhance", 0))
            defense = max(0, defender.get("Defense", 0) - attacker.get("DefenseIgnore", 0))
            damage_reduction = calculate_damage_reduction(defense)
            final_damage_this_hit = damage_with_enhance * (1 - damage_reduction)
            final_damage_this_hit *= (1 - defender.get('DamageReduction', 0))
            final_damage_this_hit = max(1, round(final_damage_this_hit))

            total_damage += final_damage_this_hit
            hit_damage_messages.append(f"**{final_damage_this_hit} 대미지!** (질풍 {new_stacks} 스택)")
        else:
            # g. 빗나갔을 때
            hit_damage_messages.append("**회피!** ⚡️")
            if "기습" in defender["Status"]:
                defender['evaded'] = True
    
    # 3. 모든 메시지 조합
    message += "\n".join(hit_damage_messages)
    message += f"\n\n휩쓸고 지나간 토네이도가 총 **{round(total_damage)}**의 피해를 입혔습니다!"

    # 4. 최종적으로 계산된 피해량과 메시지를 반환
    return message, total_damage

def second_skin(target, skill_level, value, skill_data_firebase):
    """패시브 - 두번째 피부: 공격 적중 시 플라즈마 중첩 부여, 5스택 시 전체 체력 비례 10% 대미지"""
    target["플라즈마 중첩"] = target.get("플라즈마 중첩", 0) + value
    message = f"{skill_emojis['두번째 피부']}**두번째 피부** 효과로 플라즈마 중첩 {target['플라즈마 중첩']}/5 부여!\n"

    second_skin_data = skill_data_firebase['두번째 피부']['values']
    skill_damage = 0
    
    if target["플라즈마 중첩"] >= 5:
        target["플라즈마 중첩"] = 0
        skill_damage = round(target['BaseHP'] * (second_skin_data['기본_대미지'] + second_skin_data['레벨당_추가_대미지'] * skill_level))
        damage_value = round((second_skin_data['기본_대미지'] + second_skin_data['레벨당_추가_대미지'] * skill_level) * 100)
        message += f"\n{skill_emojis['두번째 피부']}**플라즈마 폭발!** 전체 내구도의 {damage_value}% 대미지!\n"
    return message, skill_damage

def icathian_rain(attacker, defender, skill_level, skill_data_firebase):
    """스피드에 비례하여 연속 공격하는 속사 스킬"""
    icathian_rain_data = skill_data_firebase['이케시아 폭우']['values']

    speed = attacker["Speed"]
    hit_count = max(2, speed // icathian_rain_data['타격횟수결정_스피드값'])  # 최소 2회, 스피드당 1회 추가
    total_damage = 0

    def calculate_damage(attacker,defender,multiplier):
        evasion_score = calculate_evasion_score(defender["Speed"])
        accuracy = calculate_accuracy(attacker["Accuracy"], evasion_score + defender["Evasion"]) # 1 - 명중률 수치만큼 빗나갈 확률 상쇄 가능
        base_damage = random.uniform(attacker["Attack"] * accuracy, attacker["Attack"])  # 최소 ~ 최대 피해
        critical_bool = False
        evasion_bool = False
        evasion_score = calculate_evasion_score(defender["Speed"])
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
    message += f"{skill_emojis['이케시아 폭우']}이케시아 폭우로 {hit_count}연타 공격! 총 {total_damage} 피해!\n"
    message += passive_message
    total_damage += final_damage
    return message,total_damage

def voidseeker(attacker, defender, evasion, skill_level, skill_data_firebase):
    # 공허추적자: 스킬 증폭 70% + 레벨당 10%의 스킬 대미지
    if not evasion:
        voidseeker_data = skill_data_firebase['공허추적자']['values']       
        skill_multiplier = (voidseeker_data['기본_스킬증폭_계수'] + voidseeker_data['레벨당_스킬증폭_계수_증가'] * skill_level)
        skill_damage = attacker["Spell"] * skill_multiplier
        apply_status_for_turn(defender,"속박",1, source_id=defender['Id'])

        message = f"\n{skill_emojis['공허추적자']}**공허추적자** 사용!\n스킬 증폭 {int(round(skill_multiplier * 100))}%의 스킬 피해를 입히고 1턴간 속박!\n"
        passive_skill_data = attacker["Skills"].get("두번째 피부", None)   
        passive_skill_level = passive_skill_data["레벨"]
        passive_message, explosion_damage = second_skin(defender, passive_skill_level, 2, skill_data_firebase)
        message += passive_message
        skill_damage += explosion_damage
    else:
        skill_damage = 0
        message = f"\n**{skill_emojis['공허추적자']}공허추적자**가 빗나갔습니다!\n"
    return message, skill_damage

def supercharger(attacker, skill_level, skill_data_firebase):
    # 고속충전: 1턴간 회피 증가, 3턴간 스피드 증가
    supercharger_data = skill_data_firebase['고속충전']['values']
    attacker["Evasion"] = 1
    invisibility_turns = supercharger_data['은신_지속시간']
    invisibility_values = supercharger_data['은신_기본_회피증가'] + supercharger_data['은신_레벨당_회피증가']
    apply_status_for_turn(attacker, "은신", duration=invisibility_turns, value = invisibility_values)  # 은신 상태 지속시간만큼 지속
    speedup_turns = supercharger_data['속도증가_지속시간']
    base_speedup = supercharger_data['속도증가_기본수치']
    speedup_level = supercharger_data['속도증가_레벨당']
    speedup_value = base_speedup + speedup_level * skill_level
    attacker["Speed"] += speedup_value
    apply_status_for_turn(attacker, "고속충전_속도증가", duration=speedup_turns)
    return f"{skill_emojis['고속충전']}**고속충전** 사용! {invisibility_turns}턴간 은신 상태에 돌입합니다!\n{speedup_turns}턴간 스피드가 {speedup_value} 증가합니다!\n"

def killer_instinct(attacker, defender, skill_level, skill_data_firebase):
    # 사냥본능: 2턴간 보호막을 얻음.
    killer_instinct_data = skill_data_firebase['사냥본능']['values']

    shield_amount = killer_instinct_data['기본_보호막량'] + killer_instinct_data['레벨당_보호막량'] * skill_level
    apply_status_for_turn(attacker,"보호막",3,shield_amount)
    return f"**{skill_emojis['사냥본능']}사냥본능** 사용! 2턴간 {shield_amount}의 보호막을 얻습니다!\n"

def cursed_body(attacker, defender, skill_level, skill_data_firebase):
    #저주받은 바디: 공격당하면 확률에 따라 공격자를 둔화
    cursed_body_data = skill_data_firebase['저주받은 바디']['values']
    if random.random() < cursed_body_data['둔화_확률'] + cursed_body_data['레벨당_둔화_확률'] * skill_level: # 확률에 따라 둔화 부여
        slow_amount = cursed_body_data['둔화량'] + cursed_body_data['레벨당_둔화량'] * skill_level
        apply_status_for_turn(attacker,"둔화",1, slow_amount, source_id = defender['Id'])
        return f"{skill_emojis['저주받은 바디']}**저주받은 바디** 발동!\n공격자에게 1턴간 {round(slow_amount * 100)}% **둔화** 부여!\n"
    else:
        return ""

def shadow_ball(attacker,defender,evasion,skill_level, skill_data_firebase):
    #섀도볼 : 스킬 증폭 기반 피해를 입히고, 50% 확률로 2턴간 침묵
    if not evasion:
        shadow_ball_data = skill_data_firebase['섀도볼']['values']    
        skill_multiplier = (shadow_ball_data['기본_스킬증폭_계수'] + shadow_ball_data['레벨당_스킬증폭_계수_증가'] * skill_level)
        skill_damage = attacker["Spell"] * skill_multiplier

        message = f"\n{skill_emojis['섀도볼']}**섀도볼** 사용!\n스킬 증폭 {int(round(skill_multiplier * 100))}%의 스킬 피해!\n"

        cc_probability = shadow_ball_data['침묵_확률'] + shadow_ball_data['레벨당_침묵_확률'] * skill_level
        if random.random() < cc_probability: # 확룰에 따라 침묵 부여
            apply_status_for_turn(defender,"침묵",2)
            message += f"**침묵** 2턴간 부여!(확률 : {round(cc_probability * 100)}%)\n"
        
    else:
        skill_damage = 0
        message = f"\n{skill_emojis['섀도볼']}**섀도볼**이 빗나갔습니다!\n"
    return message, skill_damage

def Hex(attacker,defender,evasion,skill_level, skill_data_firebase):
    #병상첨병 : 스킬 증폭 기반 피해를 입히고, 대상이 상태이상 상태라면 2배의 피해를 입힘.
    if not evasion:
        Hex_data = skill_data_firebase['병상첨병']['values']    
        skill_multiplier = (Hex_data['기본_스킬증폭_계수'] + Hex_data['레벨당_스킬증폭_계수_증가'] * skill_level)
        skill_damage = attacker["Spell"] * skill_multiplier
        
        message = f"\n{skill_emojis['병상첨병']}**병상첨병** 사용!\n스킬 증폭 {int(round(skill_multiplier * 100))}%의 스킬 피해!\n"
        cc_status = ['빙결', '화상', '침묵', '기절', '독', '둔화']
        if any(status in cc_status for status in defender['Status']): # 상태이상 적용상태라면
            skill_damage *= 2
            message = f"\n{skill_emojis['병상첨병']}**병상첨병** 사용!\n스킬 증폭 {int(round(skill_multiplier * 100))}%의 스킬 피해!\n**상태이상으로 인해 대미지 2배!**\n"
    
    else:
        skill_damage = 0
        message = f"\n{skill_emojis['병상첨병']}**병상첨병**이 빗나갔습니다!\n"
    return message, skill_damage

def poison_jab(attacker,defender,evasion,skill_level, skill_data_firebase):
    #독찌르기 : 공격력 기반 피해를 입히고, 50% 확률로 독 상태 부여
    if not evasion:
        poison_jab_data = skill_data_firebase['독찌르기']['values']    
        attack_multiplier = (poison_jab_data['기본_공격력_계수'] + poison_jab_data['레벨당_공격력_계수_증가'] * skill_level)
        skill_damage = attacker["Attack"] * attack_multiplier
        
        message = f"\n{skill_emojis['독찌르기']}**독찌르기** 사용!\n공격력 {int(round(attack_multiplier * 100))}%의 스킬 피해!\n"
        cc_probability = poison_jab_data['독_확률'] + poison_jab_data['레벨당_독_확률'] * skill_level
        if random.random() < cc_probability: # 확룰에 따라 독 부여
            apply_status_for_turn(defender,"독",3)
            message += f"**독** 3턴간 부여!(확률 : {round(cc_probability * 100)}%)\n"

    else:
        skill_damage = 0
        message = f"\n{skill_emojis['독찌르기']}**독찌르기**가 빗나갔습니다!\n"
    return message, skill_damage

def fire_punch(attacker,defender,evasion,skill_level, skill_data_firebase):
    #불꽃 펀치 : 공격력 기반 피해를 입히고, 50% 확률로 2턴간 화상 상태 부여
    if not evasion:
        poison_jab_data = skill_data_firebase['불꽃 펀치']['values']    
        attack_multiplier = (poison_jab_data['기본_공격력_계수'] + poison_jab_data['레벨당_공격력_계수_증가'] * skill_level)
        skill_damage = attacker["Attack"] * attack_multiplier
        
        message = f"\n{skill_emojis['불꽃 펀치']}**불꽃 펀치** 사용!\n공격력 {int(round(attack_multiplier * 100))}%의 스킬 피해!\n"
        cc_probability = poison_jab_data['화상_확률'] + poison_jab_data['레벨당_화상_확률'] * skill_level
        if random.random() < cc_probability: # 확룰에 따라 화상 부여
            burn_damage = poison_jab_data['화상_대미지'] + poison_jab_data['레벨당_화상_대미지'] * skill_level
            apply_status_for_turn(defender,"화상",2, burn_damage)
            apply_status_for_turn(defender,"치유 감소", 2, 0.4)
            message += f"화상 상태이상 2턴간 부여!(확률 : {round(cc_probability * 100)}%)\n"

    else:
        skill_damage = 0
        message = f"\n{skill_emojis['불꽃 펀치']}**불꽃 펀치**가 빗나갔습니다!\n"
    return message, skill_damage

def timer():
    skill_damage = 1000000
    message = f"타이머 종료!\n"
    return message, skill_damage

def summon_undead(attacker, skill_level, skill_data_firebase):
    """
    액티브 - 사령 소환
    자신의 현재 내구도 15%를 소모하여 사령을 소환합니다.
    사령은 소환사의 기본 스탯 50%를 가집니다.
    """
    # firebase에 정의하거나 여기에 하드코딩
    necro_data = skill_data_firebase.get('사령 소환', {}).get('values', {})
    hp_cost_ratio = necro_data.get('내구도_소모_비율', 0.15)
    stat_inherit_ratio = necro_data.get('스탯_계승_비율', 0.5)

    hp_cost = max(20, round(attacker['HP'] * hp_cost_ratio)) # 최소 20

    if attacker['HP'] <= hp_cost:
        return "내구도가 부족하여 사령을 소환할 수 없습니다!", 0

    # 사령이 이미 존재하면 소환 불가
    if 'Summon' in attacker:
        return "이미 사령이 소환되어 있습니다!", 0

    attacker['HP'] -= hp_cost

    # 사령의 스탯은 소환사의 '기본(Base)' 스탯을 따릅니다.
    summon_stats = {
        'name': '사령',
        'BaseHP': round(attacker['BaseHP'] * stat_inherit_ratio),
        'HP': round(attacker['BaseHP'] * stat_inherit_ratio),
        'Attack': round(attacker['BaseSpell'] *  stat_inherit_ratio), # 공격력은 스킬 증폭 기반
        'Defense': round(attacker['BaseDefense'] * stat_inherit_ratio), # 기본 방어력 스탯이 필요합니다.
        'Speed': round(attacker['BaseSpeed'] * stat_inherit_ratio),
        'Accuracy': attacker['BaseAccuracy'], # 명중률은 그대로 계승
        'Status': {}  # <<<<<<<< [핵심 추가] 사령의 상태이상 딕셔너리
    }
    
    # 소환사 딕셔너리에 사령 정보 추가
    attacker['Summon'] = summon_stats

    # skill_emojis 딕셔너리가 있는 파일에 '사령 소환' 이모지 추가 권장
    emoji = skill_emojis.get('사령 소환', '💀')
    message = (
        f"**{emoji}사령 소환** 사용! 자신의 내구도 **{hp_cost}**를 소모하여 사령을 소환합니다!\n"
        f"사령 스탯: (HP: {summon_stats['HP']}, 공격력: {summon_stats['Attack']})\n"
    )
    
    return message, 0 # 소환 자체는 피해를 주지 않음


def curse(attacker, defender, evasion, skill_level, skill_data_firebase):
    """
    액티브 - 저주
    스킬 증폭 비례 피해와 함께 [저주] 상태(공/방 감소)를 부여.
    사령이 활성화되어 있으면 강화된 버전으로 발동.
    """
    curse_data = skill_data_firebase['저주']['values']
    hp_cost_ratio = curse_data.get('내구도_소모_비율', 0.05) # DB에서 값 가져오기 (없으면 0.05)

    # [추가] 내구도 코스트 계산 및 확인
    hp_cost = round(attacker['HP'] * hp_cost_ratio)

    # 최소 1의 내구도는 소모하도록 설정 (내구도 20 미만일 때 hp_cost가 0이 되는 것 방지)
    hp_cost = max(1, hp_cost) 

    if attacker['HP'] <= hp_cost:
        skill_damage = 0
        message = f"**{skill_emojis.get('저주', '💀')}저주** 시전 실패! 내구도가 부족합니다!\n"
        # 중요: 스킬 시전 실패 시 쿨타임이 돌지 않도록 처리 필요
        # use_skill 핸들러에서 쿨타임 처리를 조정해야 함
        return message, skill_damage

    # [추가] 스킬 시전 성공 시 내구도 소모
    attacker['HP'] -= hp_cost
    cost_message = f"내구도 **{hp_cost}**를 소모하여, "
    if evasion:
        skill_damage = 0
        message = cost_message +  f"**{skill_emojis.get('저주', '💀')}저주**를 시전했지만 빗나갔습니다!\n"
        return message, skill_damage

    is_enhanced = 'Summon' in attacker and attacker.get('Summon')
    
    if is_enhanced:
        # 강화된 저주 (사령 존재)
        base_damage = curse_data['강화_기본_피해량'] + curse_data['강화_레벨당_피해량_증가'] * skill_level
        skill_multiplier = curse_data['강화_기본_스킬증폭_계수'] + curse_data['강화_레벨당_스킬증폭_계수_증가'] * skill_level
        
        # [수정] 디버프 값을 딕셔너리로 저장
        debuff_effects = {
            'def_reduce': curse_data['강화_저주_방어력_감소율'],
            'atk_reduce': curse_data['강화_저주_공격력_감소율']
        }
        duration = curse_data['저주_지속시간']

        skill_damage = base_damage + attacker['Spell'] * skill_multiplier
        # [수정] apply_status_for_turn에 딕셔너리를 값으로 전달
        apply_status_for_turn(defender, "저주", duration, debuff_effects)
        
        message = (
            cost_message +
            f"**{skill_emojis.get('저주', '💀')}[사령의 낙인]** 시전!\n"
            f"사령의 힘으로, 대상의 공격력이 **{int(debuff_effects['atk_reduce'] * 100)}%**, "
            f"방어력이 **{int(debuff_effects['def_reduce'] * 100)}%** 감소합니다! ({duration}턴 지속)\n"
        )
    else:
        # 일반 저주
        base_damage = curse_data['기본_피해량'] + curse_data['레벨당_피해량_증가'] * skill_level
        skill_multiplier = curse_data['기본_스킬증폭_계수'] + curse_data['레벨당_스킬증폭_계수_증가'] * skill_level
        
        # [수정] 디버프 값을 딕셔너리로 저장
        debuff_effects = {
            'def_reduce': curse_data['저주_방어력_감소율'],
            'atk_reduce': curse_data['저주_공격력_감소율']
        }
        duration = curse_data['저주_지속시간']

        skill_damage = base_damage + attacker['Spell'] * skill_multiplier
        # [수정] apply_status_for_turn에 딕셔너리를 값으로 전달
        apply_status_for_turn(defender, "저주", duration, debuff_effects)

        message = (
            cost_message +
            f"**{skill_emojis.get('저주', '💀')}저주** 시전!\n"
            f"대상의 공격력이 **{int(debuff_effects['atk_reduce'] * 100)}%**, "
            f"방어력이 **{int(debuff_effects['def_reduce'] * 100)}%** 감소합니다! ({duration}턴 지속)\n"
        )

    return message, skill_damage