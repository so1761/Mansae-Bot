import random
from .skills import *
# 각각의 스킬 함수는 기존 skills.py 등에서 불러오거나 여기에 정의
# 예시로 몇 개의 스킬만 간략하게 구현
# 실제로는 각각의 스킬 함수 (charging_shot, Shield, etc.)를 import 하거나 이 파일에 포함해야 함

def process_skill(
    attacker, defender, skill_name, slienced, evasion, attacked,
    skill_data_firebase,
    result_message, used_skill, skill_attack_names,
    cooldown_message
):
    skill_cooldown_current = attacker["Skills"][skill_name]["현재 쿨타임"]
    skill_cooldown_total = attacker["Skills"][skill_name]["전체 쿨타임"]
    skill_level = attacker["Skills"][skill_name]["레벨"]

    passive_skills = ["두번째 피부", "뇌진탕 펀치", "저주받은 바디"]

    if skill_cooldown_current == 0:
        if slienced:
            result_message += f"침묵 상태로 인하여 {skill_name}스킬 사용 불가!\n"
        else:
            if skill_name == "보호막":
                attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown_total
                result_message += Shield(attacker, skill_level, skill_data_firebase)
                used_skill.append(skill_name)
            elif skill_name == "고속충전":
                attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown_total
                result_message += supercharger(attacker, skill_level, skill_data_firebase)
                used_skill.append(skill_name)
            elif skill_name == "사냥본능":
                attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown_total
                result_message += killer_instinct(attacker, defender, skill_level, skill_data_firebase)
                used_skill.append(skill_name)
            else:
                if skill_name not in passive_skills:
                    # 공격형, 쿨타임형 등 기타 스킬
                    used_skill.append(skill_name)
                    skill_attack_names.append(skill_name)
    else:
        cooldown_message.append(f"⏳{skill_name}의 남은 쿨타임 : {skill_cooldown_current}턴")
    return result_message

def process_all_skills(
    attacker, defender, slienced, evasion, attacked,
    skill_data_firebase
):
    result_message = ""
    used_skill = []
    skill_attack_names = []
    skill_names = list(attacker["Skills"].keys())
    cooldown_message = [] 

    # 기술 사용(자동 스킬 선택) 기믹
    if "기술 사용" in attacker.get("Status", {}):
        if slienced:
            result_message += f"침묵 상태로 인하여 스킬 사용 불가!\n"
        else:
            ai_skills = ['섀도볼', '독찌르기', '불꽃 펀치', '병상첨병']
            cc_status = ['빙결', '화상', '침묵', '기절', '속박', '독', '둔화']
            if any(status in cc_status for status in defender.get('Status', {})):
                ai_skill_to_use = '병상첨병'
            else:
                ai_skill_to_use = random.choice(ai_skills)
            used_skill.append(ai_skill_to_use)
            skill_attack_names.append(ai_skill_to_use)
        # 기술 사용 관련 처리를 했으므로, 아래 일반 스킬 처리로 바로 넘어가지 않도록 return
        return result_message, used_skill, skill_attack_names, cooldown_message

    for skill_name in skill_names:
        result_message = process_skill(
            attacker, defender, skill_name, slienced, evasion, attacked,
            skill_data_firebase, result_message, used_skill, skill_attack_names, cooldown_message
        )

    # 특수 상태 처리 (예: 기습)
    if "기습" in attacker["Status"]:
        skill_level = attacker["Skills"]["기습"]["레벨"]
        invisibility_data = skill_data_firebase['기습']['values']
        DefenseIgnore_increase = skill_level * invisibility_data['은신공격_레벨당_방관_증가']
        bleed_chance = invisibility_data['은신공격_레벨당_출혈_확률'] * skill_level
        bleed_damage = invisibility_data['은신공격_출혈_기본_지속피해'] + skill_level * invisibility_data['은신공격_출혈_레벨당_지속피해']
        if random.random() < bleed_chance and not evasion and attacked:
            bleed_turns = invisibility_data['은신공격_출혈_지속시간']
            # apply_status_for_turn 함수는 별도 import 필요함
            try:
                from .status import apply_status_for_turn
                apply_status_for_turn(defender, "출혈", duration=bleed_turns, value=bleed_damage)
            except ImportError:
                pass  # 임포트 불가 시 무시(예시)
            result_message +=f"\n**🩸{attacker['name']}의 기습**!\n{bleed_turns}턴간 출혈 상태 부여!\n"
        result_message +=f"\n**{attacker['name']}의 기습**!\n방어력 관통 + {DefenseIgnore_increase}!\n{round(invisibility_data['은신공격_레벨당_피해_배율'] * skill_level * 100)}% 추가 대미지!\n"
    
    return result_message, used_skill, skill_attack_names, cooldown_message

def process_on_hit_effects(
    attacker, defender, evasion, critical_bool, skill_attack_names, used_skill, result_message,
    skill_data_firebase, battle_embed
):
    # 불굴 (방어자)
    if "불굴" in defender["Status"]:
        if not evasion:
            skill_level = defender["Skills"]["불굴"]["레벨"]
            unyielding_data = skill_data_firebase['불굴']['values']
            damage_reduction = min(unyielding_data['최대_피해감소율'], unyielding_data['기본_피해감소'] + unyielding_data['레벨당_피해감소'] * skill_level)  # 최대 90% 감소 제한
            defender["DamageReduction"] = damage_reduction
            
            result_message += f"**<:braum_E:1370258314666971236>불굴**의 효과로 받는 대미지 {int(damage_reduction * 100)}% 감소!\n"

    # 뇌진탕 펀치 (공격자)
    if "뇌진탕 펀치" in attacker["Status"]:
        if not skill_attack_names:
            if not evasion:
                result_message += concussion_punch(defender)

    # 두번째 피부 (공격자)
    if "두번째 피부" in attacker["Status"]:
        skill_name = "두번째 피부"
        if not skill_attack_names:
            if not evasion:
                used_skill.append(skill_name)

    # 저주받은 바디 (방어자)
    if "저주받은 바디" in defender["Status"]:
        if not evasion:
            skill_level = defender["Skills"]["저주받은 바디"]["레벨"]
            result_message += cursed_body(attacker, skill_level, skill_data_firebase)

    # 일섬 (공격자 스킬 목록)
    if "일섬" in attacker["Skills"]:
        if not evasion:
            if critical_bool:
                issen_data = skill_data_firebase['일섬']['values']
                skill_level = attacker["Skills"]["일섬"]["레벨"]
                bleed_damage = issen_data['출혈_대미지'] + issen_data['레벨당_출혈_대미지'] * skill_level
                if '출혈' in defender['Status']:
                    apply_status_for_turn(defender, "출혈", 3, bleed_damage)
                    if battle_embed:
                        battle_embed.add_field(name="출혈!", value="출혈 상태에서 치명타 공격으로 3턴간 **출혈** 부여!🩸", inline=False)
                else:
                    apply_status_for_turn(defender, "출혈", 2, bleed_damage)
                    if battle_embed:
                        battle_embed.add_field(name="출혈!", value="치명타 공격으로 2턴간 **출혈** 부여!🩸", inline=False)
    return result_message, used_skill

def use_skill(attacker, defender, skills, evasion, reloading, skill_data_firebase):
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

        # 스킬 쿨타임 적용
        attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown

        if skill_name == "빙하 균열":
            skill_message, damage= glacial_fissure(attacker,defender,evasion,skill_level, skill_data_firebase)
            result_message += skill_message
        elif skill_name == "불굴":
            skill_message, damage = unyielding(attacker, skill_level, skill_data_firebase)
            result_message += skill_message
        elif skill_name == "헤드샷":
            skill_message, damage, critical_bool = headShot(attacker,evasion,skill_level, skill_data_firebase)
            result_message += skill_message
            if evasion:
                # 스킬 쿨타임 적용
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
        elif skill_name == "창격":
            skill_message, damage = spearShot(attacker, defender, evasion, skill_level,skill_data_firebase)
            result_message += skill_message
        elif skill_name == "강타":
            skill_message, damage, critical_bool = smash(attacker,defender,evasion,skill_level, skill_data_firebase)
            result_message += skill_message
        elif skill_name == "동상":
            skill_message, damage= frostbite(attacker,defender,evasion,skill_level, skill_data_firebase)
            result_message += skill_message
        elif skill_name == "속사":
            skill_message, damage = rapid_fire(attacker,defender,skill_level, skill_data_firebase)
            result_message += skill_message
            total_damage += damage
        elif skill_name == '이케시아 폭우':
            skill_message, damage = icathian_rain(attacker,defender,skill_level, skill_data_firebase)
            result_message += skill_message
            total_damage += damage
        elif skill_name == '공허추적자':
            skill_message, damage = voidseeker(attacker,defender,evasion,skill_level, skill_data_firebase)
            result_message += skill_message
        elif skill_name == "수확":
            skill_message, damage = Reap(attacker,evasion,skill_level, skill_data_firebase)
            result_message += skill_message
        elif skill_name == "전선더미 방출":
            skill_message, damage= mech_Arm(attacker,defender,evasion,skill_level, skill_data_firebase)
            result_message += skill_message
        elif skill_name == "전깃줄":
            skill_message, damage= electronic_line(attacker,defender,skill_level, skill_data_firebase)
            result_message += skill_message
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
                heal_multiplier = Reap_data['기본_흡혈_비율']
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
                    healban_amount = min(1, attacker['Status']['치유 감소']['value'])
                    reduced_heal = round(heal_amount * healban_amount)
                else:
                    reduced_heal = 0

                initial_HP = attacker['HP']  # 회복 전 내구도 저장
                attacker['HP'] += heal_amount - reduced_heal  # 힐 적용
                attacker['HP'] = min(attacker['HP'], attacker['BaseHP'])  # 최대 내구도 이상 회복되지 않도록 제한

                # 최종 회복된 내구도
                final_HP = attacker['HP']
                if "치유 감소" in attacker["Status"]:
                    result_message += f"가한 대미지의 {int(heal_multiplier * 100)}% 흡혈! (+{heal_amount - reduced_heal}(-{reduced_heal}) 회복)\n내구도: [{initial_HP} → {final_HP}] ❤️ (+{final_HP - initial_HP})"
                else:
                    result_message += f"가한 대미지의 {int(heal_multiplier * 100)}% 흡혈! (+{heal_amount - reduced_heal} 회복)\n내구도: [{initial_HP} → {final_HP}] ❤️ (+{final_HP - initial_HP})"
        

    return max(0, round(total_damage)), result_message, critical_bool  # 최소 0 피해

