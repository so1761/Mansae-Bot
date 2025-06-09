import random

STATUS_EMOJIS = {
    "빙결": "❄️",
    "출혈": "🩸",
    "화상": "🔥",
    "기절": "💫",
    "독": "🫧",
    "둔화": "🐌",
    "꿰뚫림": "<:spearShot:1380512916406796358>",
    "침묵": "🔇",
    "은신": "🌫️",
    "불굴": "<:braum_E:1380505187160035378>",
    "치유 감소": "❤️‍🩹",
    "속박": "⛓️"
}

SUBSCRIPT_MAP = {
    "0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄",
    "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉"
}

def to_subscript(number):
    return ''.join(SUBSCRIPT_MAP.get(d, d) for d in str(number))

def format_status_effects(status_dict):
    result = []
    value_status = ["꿰뚫림", "치유 감소", "둔화", "은신"]
    percent_status = ["치유 감소", "둔화"]
    for status, info in status_dict.items():
        emoji = STATUS_EMOJIS.get(status, "")
        duration = info.get("duration", 0)
        if emoji and duration > 0:
            if status in value_status:
                values = info.get("value", 0)
                if status in percent_status:
                    values = int(values * 100)
                result.append(f"{emoji}{to_subscript(values)}{duration}")
            else:
                result.append(f"{emoji}{duration}")
    return " ".join(result)

def apply_status_for_turn(character, status_name, duration=1, value=None, source_id = None):
    debuffs_resistable = {
        "hard_cc": ["기절", "침묵", "빙결"],
        "soft_cc": ["둔화", "출혈", "화상", "독", "속박"]
    }

    resilience = character.get("Resilience", 0)

    if status_name in debuffs_resistable["hard_cc"]:
        resist_chance = min(resilience * 5, 80)  # 하드 CC는 저항 확률 낮게
    elif status_name in debuffs_resistable["soft_cc"]:
        resist_chance = min(resilience * 10, 80)  # 일반 CC는 저항 확률 높게
    else:
        resist_chance = 0

    if resist_chance > 0 and random.randint(1, 100) <= resist_chance:
        character.setdefault("Log", []).append(f"💪{status_name} 상태이상을 강인함으로 막아냈습니다!")
        return  # 상태이상 적용 막음
        
    # 상태 적용 및 갱신
    if source_id is None:
        source_id = character.get("Id", None)  # character의 id를 바로 꺼내서

    if status_name not in character["Status"]:
        character["Status"][status_name] = {"duration": duration}
        if value is not None:
            character["Status"][status_name]["value"] = value
        if source_id is not None:
            character["Status"][status_name]["source"] = source_id
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
        if source_id is not None:
            character["Status"][status_name]["source"] = source_id

def update_status(character, current_turn_id):
    for status, data in list(character["Status"].items()):
        # source가 없으면 기본으로 duration 감소
        source = data.get("source", None)
        # 내 턴이 아니고, 상태 부여자가 현재 턴 주체가 아니라면 감소
        # 즉, 상대 턴일 때만 줄임
        if source is None or source != current_turn_id:
            character["Status"][status]["duration"] -= 1
            if character["Status"][status]["duration"] <= 0:
                del character["Status"][status]

def remove_status_effects(character, skill_data_firebase):

    """
    상태가 사라졌을 때 효과를 되돌리는 함수
    """
    
    # 기본값으로 초기화
    character["Evasion"] = character["BaseEvasion"]
    character["CritDamage"] = character["BaseCritDamage"]
    character["CritChance"] = character["BaseCritChance"]
    character["Attack"] = character["BaseAttack"]
    character["Accuracy"] = character["BaseAccuracy"]
    character["Speed"] = character["BaseSpeed"]
    character["DamageEnhance"] = character["BaseDamageEnhance"]
    character["DefenseIgnore"] = character["BaseDefenseIgnore"]
    character["HealBan"] = 0
    character["DamageReduction"] = character["BaseDamageReduction"]

    # 현재 적용 중인 상태 효과를 확인하고 반영
    if "은신" in character["Status"]:
        value = character["Status"]['은신']['value']
        character["Evasion"] += value # 회피 수치 증가

    if "꿰뚫림" in character["Status"]:
        character["DamageReduction"] -= 0.3 * character["Status"]["꿰뚫림"]["value"]

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

    if "피해 감소" in character["Status"]:
        reduce_amount = character['Status']['피해 감소']['value']
        if reduce_amount > 1:
            reduce_amount = 1
        character["DamageReduction"] = reduce_amount

