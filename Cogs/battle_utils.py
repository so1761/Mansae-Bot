import math
from firebase_admin import db

# 전장 크기 (-10 ~ 10), 0은 없음
MAX_DISTANCE = 10
MIN_DISTANCE = -10

def calculate_damage_reduction(defense):
    return min(0.99, 1 - (100 / (100 + defense)))

def calculate_accuracy(accuracy):
    return min(0.99, 1 - (30 / (30 + accuracy)))

def calculate_evasion_score(speed):
    return speed // 5

def calculate_move_chance(speed, move_chain=0):
    penalty_ratio = 0.7 ** move_chain
    effective_speed = speed * penalty_ratio
    move_chance = min(0.99, 1 - math.exp(-effective_speed / 70))
    return move_chance

def durability_bar(current, max_value, shield, bar_length=20):
    if current < 0:
        current = 0
    total = min(current + shield, max_value)
    ratio = total / max_value
    filled = int((current / max_value) * bar_length)
    shield_fill = int((min(shield, max_value - current) / max_value) * bar_length)
    empty = bar_length - filled - shield_fill

    bar = "█" * filled + "▒" * shield_fill + "░" * empty
    result = f"`{current:>4} [{bar}] {max_value:<4}`"
    
    if shield > 0:
        result += f" 🛡️{shield}"

    return result

def generate_tower_weapon(floor: int):
    weapon_types = ["대검","스태프-화염", "조총", "스태프-냉기", "태도", "활", "스태프-신성", "단검", "낫", "창"]
    weapon_type = weapon_types[(floor - 1) % len(weapon_types)]  # 1층부터 시작
    enhancement_level = floor

    ref_weapon_base = db.reference(f"무기/기본 스탯")
    base_weapon_stats = ref_weapon_base.get() or {}

    # 기본 스탯
    base_stats = base_weapon_stats[weapon_type]

    skill_weapons = ["스태프-화염", "스태프-냉기", "스태프-신성", "낫"]
    attack_weapons = ["대검", "창", "활", "단검", "조총", "태도"]
    hybrid_weapons = []
    critical_weapons = ["대검", "조총", "태도"]

    # 강화 단계만큼 일괄 증가
    weapon_data = base_stats.copy()
    weapon_data["이름"] = f"{weapon_type} +{enhancement_level}"
    weapon_data["무기타입"] = weapon_type
    if weapon_type in skill_weapons:
        weapon_data["스킬 증폭"] += enhancement_level * 5
    elif weapon_type in attack_weapons:
        if weapon_type in critical_weapons:
            weapon_data["공격력"] += round(enhancement_level * 1.5)
            weapon_data["치명타 확률"] += min((enhancement_level // 10) * 0.05, 70)
        else:
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