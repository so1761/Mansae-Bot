import random

# 캐릭터 스탯 정의
A = {
    "name": "지모",
    "HP": 500,
    "Attack": 100,
    "CritChance": 0.10,
    "CritDamage": 1.5,
    "Speed": 10,
    "Accuracy": 0.1,
    "Defense": 12,
}

B = {
    "name": "퇴경",
    "HP": 500,
    "Attack": 110,
    "CritChance": 0.10,
    "CritDamage": 1.5,
    "Speed": 10,
    "Accuracy": 0.1,
    "Defense": 10,
}

# 방어력 기반 피해 감소율 계산 함수
def calculate_damage_reduction(defense):
    return min(0.99, 1 - (100 / (100 + defense)))  # 방어력 공식 적용

def attack(attacker, defender):
    base_damage = random.uniform(attacker["Attack"] * attacker["Accuracy"], attacker["Attack"])  # 최소~최대 피해
    if random.random() < attacker["CritChance"]:
        print("크리티컬!")
        base_damage *= attacker["CritDamage"]
    
    # 방어력에 따른 완벽 방어 확률 적용
    perfect_block_chance = (defender["Defense"] // 100) * 0.01 + max(0, (defender["Defense"] - attacker["Defense"]) // 50 * 0.01)
    if random.random() < perfect_block_chance:
        print("완벽 방어!")
        return 0  # 완벽 방어 발생 시 피해 0
    
    damage_reduction = calculate_damage_reduction(defender["Defense"])
    final_damage = base_damage * (1 - damage_reduction)  # 방어력 적용 후 최종 피해량
    
    # 스피드에 따른 추가 공격 확률 적용
    extra_attack_chance = (attacker["Speed"] // 10) * 0.01 + max(0, (attacker["Speed"] - defender["Speed"]) // 5 * 0.01)
    if random.random() < extra_attack_chance:
        print("추가 공격!")
        final_damage += base_damage  # 추가 공격 발생 시 한 번 더 공격
    
    return max(1, round(final_damage))  # 최소 피해량 보장

# 전투 시뮬레이션
def battle_simulation(A, B):
    # 스피드를 비교하여 선공자 결정
    if A["Speed"] > B["Speed"]:
        attacker, defender = A, B
    elif B["Speed"] > A["Speed"]:
        attacker, defender = B, A
    else:
        # 스피드가 같을 경우 랜덤하게 선공자 결정
        from random import choice
        attacker, defender = choice([(A, B), (B, A)])

    turn = 0
    while A["HP"] > 0 and B["HP"] > 0:
        turn += 1
        # 공격 차례
        damage = attack(attacker, defender)
        
        defender["HP"] -= damage
        print(f"{attacker['name']}의 공격! {damage} 대미지! [남은 체력 : {defender['HP']}]")

        # 공격자가 변경되며, 공격자와 수비자 교체
        attacker, defender = defender, attacker

        if A["HP"] <= 0:
            return "B 승리"
        if B["HP"] <= 0:
            return "A 승리"
    
print(battle_simulation(A,B))
# # 여러 번 시뮬레이션 실행
# battle_results = {"A 승리": 0, "B 승리": 0}
# num_simulations = 10000

# for _ in range(num_simulations):
#     A_copy = A.copy()
#     B_copy = B.copy()
#     result = battle_simulation(A_copy, B_copy)
#     battle_results[result] += 1



# print(battle_results)