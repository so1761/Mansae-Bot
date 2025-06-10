import math
from firebase_admin import db
from .status import format_status_effects

def get_user_insignia_stat(user_name: str, role: str = "challenger") -> dict:
    """
    주어진 유저의 인장 정보를 기반으로 스탯 보너스를 계산하여 반환합니다.

    Args:
        user_name (str): 유저 이름
        role (str): 결과 딕셔너리에서 사용할 역할 키 (예: 'challenger', 'opponent')

    Returns:
        dict: {role: {스탯명: 값, ...}} 형태의 딕셔너리
    """
    base_stats = ["CritChance", "CritDamage", "DefenseIgnore", "DamageReduction", "Resilience", "DamageEnhance", "Evasion"]

    insignia_stats = {
        role: {
            stat: 0 for stat in base_stats + [f"Base{stat}" for stat in base_stats]
        }
    }

    # 장착된 인장 리스트 가져오기
    ref_user_insignia = db.reference(f"무기/유저/{user_name}/각인")
    user_insignia = ref_user_insignia.get() or []

    # 보유한 인장의 레벨 정보
    ref_insignia_level_detail = db.reference(f"무기/각인/유저/{user_name}")
    insignia_level_detail = ref_insignia_level_detail.get() or {}

    for slot_key in range(3):
        insignia_name = user_insignia[slot_key] if slot_key < len(user_insignia) else ""
        if not insignia_name:
            continue

        # 인장 스탯 정보
        ref_insignia_stat_detail = db.reference(f"무기/각인/스탯/{insignia_name}")
        insignia_stat_detail = ref_insignia_stat_detail.get() or {}

        level = insignia_level_detail.get(insignia_name, {}).get("레벨", 1)
        base_value = insignia_stat_detail.get("초기 수치", 0)
        increase_per_level = insignia_stat_detail.get("증가 수치", 0)

        total_bonus = base_value + (increase_per_level * level)

        # 각 인장에 따른 스탯 매핑
        stat_map = {
            "약점 간파": "CritChance",
            "파멸의 일격": "CritDamage",
            "꿰뚫는 집념": "DefenseIgnore",
            "강철의 맹세": "DamageReduction",
            "불굴의 심장": "Resilience",
            "타오르는 혼": "DamageEnhance",
            "바람의 잔상": "Evasion"
        }

        if insignia_name in stat_map:
            stat_key = stat_map[insignia_name]
            insignia_stats[role][stat_key] += total_bonus
            base_stat = f"Base{stat_key}"
            insignia_stats[role][base_stat] += total_bonus
    return insignia_stats

def create_bar(value: int, max_val: int = 50, bar_length: int = 10):
        filled_len = round((value / max_val) * bar_length)
        return "■" * filled_len

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

def show_bar(battle_embed, raid, challenger, shield_amount_challenger, opponent, shield_amount_opponent):
    def name_with_effects(player):
        effects_str = format_status_effects(player.get("Status", {}))
        return f"{player['name']} {effects_str}" if effects_str else player['name']

    def bar_for(player, is_raid, shield, is_opponent=False):
        if is_raid and is_opponent:
            max_hp = player['FullHP']
        else:
            max_hp = player['BaseHP']
        return durability_bar(player['HP'], max_hp, shield)

    battle_embed.add_field(
    name=name_with_effects(challenger),
    value=f"**{bar_for(challenger, raid, shield_amount_challenger, is_opponent=False)}**",
    inline=False
    )

    battle_embed.add_field(
        name=name_with_effects(opponent),
        value=f"**{bar_for(opponent, raid, shield_amount_opponent, is_opponent=True)}**",
        inline=False
    )

def calculate_damage_reduction(defense):
    return min(0.99, 1 - (100 / (100 + defense)))

def calculate_accuracy(accuracy, opponent_speed):
    return min(0.99, accuracy / (accuracy + opponent_speed * 1.5))

def calculate_evasion_score(speed):
    return speed // 5

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