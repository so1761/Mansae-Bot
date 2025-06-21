import random
from .skill_emoji import skill_emojis

STATUS_EMOJIS = {
    "빙결": "❄️",
    "출혈": "🩸",
    "화상": "🔥",
    "기절": "💫",
    "독": "🫧",
    "둔화": "🐌",
    "꿰뚫림": skill_emojis['창격'],
    "침묵": "🔇",
    "은신": "🌫️",
    "불굴": skill_emojis['불굴'],
    "치유 감소": "❤️‍🩹",
    "속박": "⛓️",
    "장전": skill_emojis['헤드샷'],
    "저주": "💀",
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
    target_char = character.get('Summon') if 'Summon' in character and character.get('Summon') else character
    
    debuffs_resistable = {
        "hard_cc": ["기절", "침묵", "빙결", "저주"],
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

    if "Status" not in target_char:
        target_char["Status"] = {}
        
    if status_name not in target_char["Status"]:
        target_char["Status"][status_name] = {"duration": duration}
        if value is not None:
            target_char["Status"][status_name]["value"] = value
        if source_id is not None:
            target_char["Status"][status_name]["source"] = source_id
    else:
        if status_name in ["출혈", "화상"]:
            target_char["Status"][status_name]["duration"] += duration
        else:
            if duration >= target_char["Status"][status_name]["duration"]:
                target_char["Status"][status_name]["duration"] = duration
        if value is not None:
            # value가 딕셔너리인 경우 (e.g., 저주 스킬)
            if isinstance(value, dict):
                # 딕셔너리는 비교하지 않고, 항상 새로운 값으로 덮어씁니다.
                target_char["Status"][status_name]["value"] = value
            else:
                # value가 숫자나 다른 타입인 경우 기존 로직 사용
                current_value = target_char["Status"][status_name].get("value", None)
                # 새로운 값이 더 강력할 때만 갱신 (None 이거나 더 클 때)
                if current_value is None or value > current_value:
                    target_char["Status"][status_name]["value"] = value
        if source_id is not None:
            target_char["Status"][status_name]["source"] = source_id

def update_status(character, current_turn_id):
    """
    캐릭터와 그 캐릭터의 소환수의 상태이상 지속시간을 모두 감소시킵니다.
    """

    # 내부 헬퍼 함수: 특정 캐릭터의 상태이상 지속시간을 감소시키는 로직
    def _update_single_char_status(char):
        if not char or "Status" not in char:
            return

        # .items()의 복사본을 만들어 순회 (원본 딕셔너리 수정 때문)
        for status, data in list(char["Status"].items()):
            source = data.get("source", None)
            
            # 상태이상 부여자의 턴이 아닐 때만 duration 감소
            if source is None or source != current_turn_id:
                char["Status"][status]["duration"] -= 1
                if char["Status"][status]["duration"] <= 0:
                    del char["Status"][status]

    # 1. 본체의 상태이상을 업데이트합니다.
    _update_single_char_status(character)

    # 2. 만약 소환수가 존재하면, 소환수의 상태이상도 업데이트합니다.
    if 'Summon' in character and character.get('Summon'):
        summon_char = character['Summon']
        _update_single_char_status(summon_char)

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
    character["Defense"] = character["BaseDefense"]
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

    # --- 공/방 관련 디버프 ---
    if "저주" in character["Status"]:
        # [수정] value가 이제 딕셔너리
        debuff_effects = character['Status']['저주']['value']
        
        # 각 키에서 값을 가져와 적용
        def_reduce_ratio = debuff_effects.get('def_reduce', 0)
        atk_reduce_ratio = debuff_effects.get('atk_reduce', 0)
        
        character['Defense'] *= (1 - def_reduce_ratio)
        character['Attack'] *= (1 - atk_reduce_ratio) # 공격력 감소 적용


