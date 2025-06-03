import math
from firebase_admin import db

# 전장 크기 (-10 ~ 10), 0은 없음
MAX_DISTANCE = 10
MIN_DISTANCE = -10

def calculate_damage_reduction(defense):
    return min(0.99, 1 - (100 / (100 + defense)))

def calculate_accuracy(accuracy):
    return min(0.99, 1 - (50 / (50 + accuracy)))

def calculate_evasion(speed: int) -> float:
    """
    스피드를 받아서 회피율을 계산 (speed 1당 0.005씩 증가)

    Args:
        speed (int): 캐릭터의 스피드 스탯

    Returns:
        float: 0~1 범위의 회피율 (ex: 0.5는 50% 회피)
    """
    evasion = speed * 0.002
    
    return evasion


def calculate_move_chance(speed, move_chain=0):
    penalty_ratio = 0.7 ** move_chain
    effective_speed = speed * penalty_ratio
    move_chance = min(0.99, 1 - math.exp(-effective_speed / 70))
    return move_chance

def generate_tower_weapon(floor: int):
    weapon_types = ["대검","스태프-화염", "조총", "스태프-냉기", "태도", "활", "스태프-신성", "단검", "낫"]
    weapon_type = weapon_types[(floor - 1) % len(weapon_types)]  # 1층부터 시작
    enhancement_level = floor

    ref_weapon_base = db.reference(f"무기/기본 스탯")
    base_weapon_stats = ref_weapon_base.get() or {}

    # 기본 스탯
    base_stats = base_weapon_stats[weapon_type]

    skill_weapons = ["스태프-화염", "스태프-냉기", "스태프-신성"]
    attack_weapons = ["대검", "창", "활", "단검"]
    hybrid_weapons = ["낫", "조총"]

    # 강화 단계만큼 일괄 증가
    weapon_data = base_stats.copy()
    weapon_data["이름"] = f"{weapon_type} +{enhancement_level}"
    weapon_data["무기타입"] = weapon_type
    if weapon_type in skill_weapons:
        weapon_data["스킬 증폭"] += enhancement_level * 5
    elif weapon_type in attack_weapons:
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