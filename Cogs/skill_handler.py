import random
from .skills import *
# 각각의 스킬 함수는 기존 skills.py 등에서 불러오거나 여기에 정의
# 예시로 몇 개의 스킬만 간략하게 구현
# 실제로는 각각의 스킬 함수 (charging_shot, Shield, etc.)를 import 하거나 이 파일에 포함해야 함

def process_skill(
    attacker, defender, skill_name, slienced, evasion, attacked,
    skill_data_firebase, battle_distance,
    result_message, used_skill, skill_attack_names
):
    skill_cooldown_current = attacker["Skills"][skill_name]["현재 쿨타임"]
    skill_cooldown_total = attacker["Skills"][skill_name]["전체 쿨타임"]
    skill_level = attacker["Skills"][skill_name]["레벨"]

    passive_skills = ["두번째 피부", "뇌진탕 펀치", "불굴", "저주받은 바디"]

    if skill_cooldown_current == 0:
        if slienced:
            result_message += f"침묵 상태로 인하여 {skill_name}스킬 사용 불가!\n"
        else:
            if skill_name == "차징샷":
                attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown_total
                result_message += charging_shot(attacker, defender, evasion, skill_level)
                used_skill.append(skill_name)
            elif skill_name == "보호막":
                attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown_total
                result_message += Shield(attacker, skill_level, skill_data_firebase)
                used_skill.append(skill_name)
            elif skill_name == "고속충전":
                attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown_total
                result_message += supercharger(attacker, skill_level, skill_data_firebase)
                used_skill.append(skill_name)
            elif skill_name == "창격":
                attacker["Skills"][skill_name]["현재 쿨타임"] = skill_cooldown_total
                result_message += spearShot(attacker, defender, evasion, skill_level, skill_data_firebase, battle_distance)
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
        result_message += f"⏳{skill_name}의 남은 쿨타임 : {skill_cooldown_current}턴\n"
    return result_message

def process_all_skills(
    attacker, defender, slienced, evasion, attacked,
    skill_data_firebase, battle_distance
):
    result_message = ""
    used_skill = []
    skill_attack_names = []
    skill_names = list(attacker["Skills"].keys())

    # 기술 사용(자동 스킬 선택) 기믹
    if "기술 사용" in attacker.get("Status", {}):
        if slienced:
            result_message += f"침묵 상태로 인하여 스킬 사용 불가!\n"
        else:
            # 거리별 스킬 목록 정의
            if battle_distance <= 1:
                ai_skills = ['섀도볼', '독찌르기', '불꽃 펀치', '병상첨병']
            elif battle_distance <= 2:
                ai_skills = ['불꽃 펀치', '섀도볼', '병상첨병']
            elif battle_distance <= 3:
                ai_skills = ['섀도볼', '독찌르기', '병상첨병']
            else:
                ai_skills = ['독찌르기', '병상첨병']
            cc_status = ['빙결', '화상', '침묵', '기절', '속박', '독', '둔화']
            if any(status in cc_status for status in defender.get('Status', {})):
                ai_skill_to_use = '병상첨병'
            else:
                ai_skill_to_use = random.choice(ai_skills)
            used_skill.append(ai_skill_to_use)
            skill_attack_names.append(ai_skill_to_use)
        # 기술 사용 관련 처리를 했으므로, 아래 일반 스킬 처리로 바로 넘어가지 않도록 return
        return result_message, used_skill, skill_attack_names

    for skill_name in skill_names:
        result_message = process_skill(
            attacker, defender, skill_name, slienced, evasion, attacked,
            skill_data_firebase, battle_distance, result_message, used_skill, skill_attack_names
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

    # 기타 특수효과, 패시브 등도 여기에 추가 가능

    return result_message, used_skill, skill_attack_names

def process_on_hit_effects(
    attacker, defender, evasion, skill_attack_names, used_skill, result_message,
    skill_data_firebase, battle_embed, battle_distance
):
    # 불굴 (방어자)
    if "불굴" in defender["Status"]:
        if not evasion:
            skill_level = defender["Skills"]["불굴"]["레벨"]
            result_message += unyielding(defender, skill_level, skill_data_firebase, battle_distance)

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
            bleed_rate = calculate_accuracy(attacker['Accuracy'])
            if random.random() < bleed_rate:
                issen_data = skill_data_firebase['일섬']['values']
                skill_level = attacker["Skills"]["일섬"]["레벨"]
                bleed_damage = issen_data['출혈_대미지'] + issen_data['레벨당_출혈_대미지'] * skill_level
                if '출혈' in defender['Status']:
                    apply_status_for_turn(defender, "출혈", 3, bleed_damage)
                    if battle_embed:
                        battle_embed.add_field(name="출혈!", value="출혈 상태에서 공격 적중으로 3턴간 **출혈** 부여!🩸", inline=False)
                else:
                    apply_status_for_turn(defender, "출혈", 2, bleed_damage)
                    if battle_embed:
                        battle_embed.add_field(name="출혈!", value="공격 적중으로 2턴간 **출혈** 부여!🩸", inline=False)
    return result_message, used_skill