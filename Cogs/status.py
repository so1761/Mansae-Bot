def apply_status_for_turn(character, status_name, duration=1, value=None):
    # 상태 적용 및 갱신
    if status_name not in character["Status"]:
        character["Status"][status_name] = {"duration": duration}
        if value is not None:
            character["Status"][status_name]["value"] = value
    else:
        if status_name in ["출혈", "화상"]:
            character["Status"][status_name]["duration"] += duration
        else:
            if duration >= character["Status"][status_name]["duration"]:
                character["Status"][status_name]["duration"] = duration
        if value is not None:
            current_value = character["Status"][status_name].get("value", None)
            if current_value is None or value > current_value:
                character["Status"][status_name]["value"] = value

def update_status(character):
    for status, data in list(character["Status"].items()):
        character["Status"][status]["duration"] -= 1
        if data["duration"] <= 0:
            del character["Status"][status]

def remove_status_effects(character, skill_data_firebase):

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

