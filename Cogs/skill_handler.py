import random
from .skills import *
# 각각의 스킬 함수는 기존 skills.py 등에서 불러오거나 여기에 정의
# 예시로 몇 개의 스킬만 간략하게 구현
# 실제로는 각각의 스킬 함수 (charging_shot, Shield, etc.)를 import 하거나 이 파일에 포함해야 함

async def apply_and_process_damage(
        source_char,
        target_char,
        damage_amount,
        embed,
        is_critical,
        is_evaded,
        damage_source_name,
        is_dot_damage=False  # DoT 여부를 받는 인자
    ):
        """피해를 최종 적용하고 보호막/사령 분담을 처리하며, 직관적인 결과 메시지를 Embed에 추가합니다."""
        not_evasion_skills = ['속사','일섬', "이케시아 폭우", "토네이도"]

        if is_evaded:
            if damage_source_name in not_evasion_skills: # 필중 스킬에 회피가 터졌으면 다시 초기화
                if "기습" in target_char["Status"]:
                    target_char['evaded'] = False
            else:
                embed.add_field(name="", value=f"**회피!⚡️**", inline=False)
                return target_char['HP'] <= 0

        if damage_amount <= 0:
            return target_char['HP'] <= 0

        remaining_damage = damage_amount
        shield_message_part = ""
        summon_message_part = ""
        
        # 1. 보호막 흡수
        if remaining_damage > 0 and "보호막" in target_char['Status']:
            shield = target_char['Status']['보호막']
            damage_absorbed_by_shield = min(remaining_damage, shield['value'])
            shield['value'] -= damage_absorbed_by_shield
            remaining_damage -= damage_absorbed_by_shield
            if shield['value'] <= 0:
                del target_char['Status']['보호막']
            shield_message_part = f" 🛡️{damage_absorbed_by_shield} 흡수!"
            
        # 2. 사령 흡수 (DoT가 아닐 때만 실행)
        # [의도 반영] is_dot_damage가 False일 때만 이 블록이 실행됩니다.
        if not is_dot_damage and remaining_damage > 0 and 'Summon' in target_char and target_char.get('Summon'):
            summon = target_char['Summon']
            damage_absorbed_by_summon = min(remaining_damage, summon['HP'])
            summon['HP'] -= damage_absorbed_by_summon
            
            # [의도 반영] 사령이 피해를 흡수하면, 남은 피해량(remaining_damage)을 0으로 만듭니다.
            #            본체는 피해를 입지 않습니다.
            remaining_damage = 0 
            
            if summon['HP'] <= 0:
                del target_char['Summon']
                if "사령 소환" in target_char["Skills"]:
                    cooldown = target_char["Skills"]["사령 소환"]["전체 쿨타임"]
                    target_char["Skills"]["사령 소환"]["현재 쿨타임"] = cooldown
                summon_message_part = f" 💀사령 소멸!({damage_absorbed_by_summon} 흡수)"
            else:
                summon_message_part = f" 💀{damage_absorbed_by_summon} 흡수"

        # 3. 본체 피해 적용
        # - 일반 공격 시: remaining_damage가 0이 되어 본체 피해 없음.
        # - DoT 피해 시: 사령 흡수 로직을 건너뛰었으므로, 남은 피해가 그대로 본체에 적용됨.
        target_char["HP"] -= remaining_damage
        
        # 4. 최종 메시지 조합 및 Embed에 추가
        crit_text = "💥" if is_critical else ""
        
        if remaining_damage > 0:
            final_message = f"**{remaining_damage} 대미지!{crit_text}{shield_message_part}{summon_message_part}**"
        elif shield_message_part or summon_message_part:
            final_message = f"**총 {damage_amount} 피해!{crit_text} →{shield_message_part}{summon_message_part}**"
        else:
            final_message = f"**{damage_amount} 대미지!{crit_text}**"

        embed.add_field(name="", value=final_message, inline=False)
        return target_char['HP'] <= 0

async def process_skill(
    attacker, defender, skill_name, slienced, evasion, attacked,
    skill_data_firebase,
    result_message, used_skill, skill_attack_names,
):
    skill_cooldown_current = attacker["Skills"][skill_name]["현재 쿨타임"]
    skill_cooldown_total = attacker["Skills"][skill_name]["전체 쿨타임"]
    skill_level = attacker["Skills"][skill_name]["레벨"]

    passive_skills = ["두번째 피부", "뇌진탕 펀치", "저주받은 바디"]

    if skill_cooldown_current <= 0:
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

    return result_message

async def process_all_skills(
    attacker, defender, slienced, evasion, attacked,
    skill_data_firebase
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
            ai_skills = ['섀도볼', '독찌르기', '불꽃 펀치', '병상첨병']
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
        result_message = await process_skill(
            attacker, defender, skill_name, slienced, evasion, attacked,
            skill_data_firebase, result_message, used_skill, skill_attack_names
        )

    return result_message, used_skill, skill_attack_names

async def process_on_hit_effects(
    attacker, defender, evasion, critical_bool, skill_attack_names, used_skill, result_message,
    skill_data_firebase, battle_embed
):
    # 불굴 (방어자)
    if "불굴" in defender["Status"]:
        if not evasion:
            skill_level = defender["Skills"]["불굴"]["레벨"]
            unyielding_data = skill_data_firebase['불굴']['values']
            damage_reduction_value = min(unyielding_data['최대_피해감소율'], unyielding_data['기본_피해감소'] + unyielding_data['레벨당_피해감소'] * skill_level)  # 최대 90% 감소 제한
            damage_reduction = defender.get("DamageReduction", 0)
            defender["DamageReduction"] = damage_reduction + damage_reduction_value
            
            result_message += f"**<:braum_E:1380505187160035378>불굴**의 효과로 받는 대미지 {int(damage_reduction * 100)}% 감소!\n"

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
            result_message += cursed_body(attacker, defender, skill_level, skill_data_firebase)

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

async def use_skill(attacker, defender, skills, evasion, reloading, skill_data_firebase, acceleration_triggered, overdrive_triggered):
    """스킬을 사용하여 피해를 입히고 효과를 적용"""

    total_damage = 0  # 총 피해량 저장
    result_message = ""
    critical_bool = False

    final_skills_to_cast = list(skills)

    if "명상" in skills:
        skill_data = attacker["Skills"]["명상"]
        skill_level = skill_data["레벨"]

        # meditate 함수는 이제 3개의 값을 반환함
        skill_message, damage, chained_skills = meditate(attacker, defender, skill_level, skill_data_firebase, acceleration_triggered, overdrive_triggered)
        result_message += skill_message
        
        # [핵심] 명상으로 인해 연계된 스킬들을 최종 시전 목록에 추가
        if chained_skills:
            final_skills_to_cast.extend(chained_skills)
            # 중복 제거 (예: 원래도 쿨 0이었는데 연계 목록에도 추가된 경우)
            final_skills_to_cast = list(dict.fromkeys(final_skills_to_cast)) 

    for skill_name in final_skills_to_cast:
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
            skill_message, damage = unyielding(attacker, defender, skill_level, skill_data_firebase)
            result_message += skill_message
        elif skill_name == "헤드샷":
            skill_message, damage, critical_bool = headShot(attacker,defender, evasion,skill_level, skill_data_firebase)
            result_message += skill_message
            if evasion:
                # 스킬 쿨타임 적용
                apply_status_for_turn(attacker, "장전", duration=1, source_id=defender['Id'])
                return None, result_message, critical_bool
        elif skill_name == "명상":
            continue
        elif skill_name == "기습":
            if "기습" in attacker['Status']:
                skill_message, damage = invisibility(attacker, defender, evasion, skill_level, skill_data_firebase, mode = "attack")
            else:
                skill_message, damage = invisibility(attacker, defender, evasion, skill_level, skill_data_firebase)
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
            if attacker.get('명상', 0) >= 5:
                attacker['명상'] = attacker.get('명상', 0) - 5
                skill_message, damage = ice_blizzard(attacker,defender, evasion,skill_level, skill_data_firebase)
            else:
                skill_message, damage= ice_frost(attacker,defender, evasion,skill_level, skill_data_firebase)
            result_message += skill_message
        elif skill_name == "신성 마법":
            skill_message, damage= holy(attacker,defender, evasion,skill_level, skill_data_firebase)
            result_message += skill_message
        elif skill_name == "질풍 마법":
            if attacker.get('명상', 0) >= 5:
                attacker['명상'] = attacker.get('명상', 0) - 5
                skill_message, damage = wind_tornado(attacker,defender,skill_level, skill_data_firebase, acceleration_triggered, overdrive_triggered)
                skill_name = "토네이도"
                total_damage += damage
            else:
                skill_message, damage= wind_gale(attacker,evasion,skill_level, skill_data_firebase)
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
        elif skill_name == "사령 소환":
            skill_message, damage = summon_undead(attacker, skill_level, skill_data_firebase)
            result_message += skill_message
            # 중요: 사령이 죽기 전까지 쿨타임이 돌지 않으므로, 여기서 쿨타임을 설정하지 않습니다.
            # 대신, 이미 소환된 경우를 summon_undead 내부에서 처리합니다.
            # 쿨타임 적용 라인을 이 블록 바깥으로 유지합니다.
            if "이미" not in skill_message and "부족하여" not in skill_message:
                attacker["Skills"][skill_name]["현재 쿨타임"] = 999 # 임의의 큰 수로 설정하여 재사용 방지 (사령 사망 시 초기화)
            else: # 소환 실패 시 쿨타임 원상복구
                attacker["Skills"][skill_name]["현재 쿨타임"] = 0
        elif skill_name == "저주":
            skill_message, damage = curse(attacker, defender, evasion, skill_level, skill_data_firebase)
            result_message += skill_message

        multi_skills = ['속사', '이케시아 폭우', '토네이도'] #연사기는 미리 방어력 계산함
        if skill_name not in multi_skills:
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

