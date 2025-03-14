import itertools

# 기본 스탯
base_stats = {
    "HP": 500,
    "Attack": 100,
    "Defense": 10,
    "CritChance": 0.05,
    "CritDamage": 1.5,
    "Speed": 50,
    "Accuracy": 0.1
}

# 기본 강화 증가량 (항상 적용됨)
base_increase = {
    "HP": 50,
    "Attack": 5,
    "Defense": 5
}

# 특화 강화 추가 효과
special_increase = {
    "Attack": 5,
    "Defense": 5,
    "HP": 50,
    "Accuracy": 0.03,
    "Speed": 10,
    "CritChance": 0.02,
    "CritDamage": 0.2
}

# 대미지 기댓값 공식
def expected_damage(stats):
    attack = stats["Attack"]
    accuracy = stats["Accuracy"]
    crit_chance = stats["CritChance"]
    crit_damage = stats["CritDamage"]
    speed = stats["Speed"]
    
    base_damage = (attack * accuracy + attack) / 2
    crit_bonus = base_damage * crit_chance * crit_damage

    # 추가 공격 확률 적용 (Speed 3당 1% 추가 공격 확률)
    extra_attack_prob = min(1.0, (speed // 3) * 0.01)
    
    return (base_damage + crit_bonus) * (1 + extra_attack_prob)

# 가능한 강화 조합 계산
num_upgrades = 20
special_types = list(special_increase.keys())
best_config = None
best_damage = 0

# 모든 가능한 강화 배분 탐색 (중복 조합 포함)
for distribution in itertools.combinations_with_replacement(special_types, num_upgrades):
    # 현재 조합에 따른 스탯 적용
    stats = base_stats.copy()

    for _ in range(num_upgrades):  # 기본 강화 적용
        stats["HP"] += base_increase["HP"]
        stats["Attack"] += base_increase["Attack"]
        stats["Defense"] += base_increase["Defense"]

    for upgrade in distribution:  # 특화 강화 적용
        stats[upgrade] += special_increase[upgrade]

    # 대미지 기댓값 계산
    damage = expected_damage(stats)

    # 최고 기댓값 업데이트
    if damage > best_damage:
        best_damage = damage
        best_config = distribution

print(best_config)
print(best_damage)