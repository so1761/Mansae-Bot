import random

# 캐릭터 스탯 정의
A = {
    "name": "치명",
    "HP": 1500,
    "Attack": 200,
    "CritChance": 0.05,
    "CritDamage": 3.5,
    "Speed": 50,
    "Accuracy": 0.1,
    "Defense": 100,
}

B = {
    "name": "공격력",
    "HP": 1500,
    "Attack": 400,
    "CritChance": 0.05,
    "CritDamage": 1.5,
    "Speed": 50,
    "Accuracy": 0.1,
    "Defense": 100,
}

def attack(attacker, defender):
    base_damage = random.uniform(attacker["Attack"] * attacker["Accuracy"], attacker["Attack"])  # 최소~최대 피해
    critical_bool = False
    if random.random() < attacker["CritChance"]:
        critical_bool = True
        #print("크리티컬!")
        base_damage *= attacker["CritDamage"]
    
    #방어력에 따른 완벽 방어 확률 적용
    perfect_block_chance = (defender["Defense"] // 10) * 0.01
    if random.random() < perfect_block_chance:
        #print("완벽 방어!")
        return 0, False, False, True  # 완벽 방어 발생 시 피해 0
    
    damage_reduction = defender["Defense"]
    if critical_bool: # 크리티컬 시 방어력 무시
        final_damage = base_damage
    else:
        final_damage = base_damage - damage_reduction  # 방어력 적용 후 최종 피해량
    
    extra_attack_bool = False
    # 스피드에 따른 추가 공격 확률 적용
    extra_attack_chance = max(0, (attacker["Speed"] - defender["Speed"]) // 3 * 0.01)
    if random.random() < extra_attack_chance:
        extra_attack_bool = True
    
    return max(1, round(final_damage)), extra_attack_bool, critical_bool, False  # 최소 피해량 보장

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
        damage, extra, crit, defence = attack(attacker, defender)
        
        defender["HP"] -= damage
        #print(f"{attacker['name']}의 공격! {damage} 대미지! [남은 체력 : {defender['HP']}]")

        # 공격자가 변경되며, 공격자와 수비자 교체
        if not extra:
            attacker, defender = defender, attacker

        if A["HP"] <= 0:
            return "B 승리"
        if B["HP"] <= 0:
            return "A 승리"
    
# print(battle_simulation(A,B))
# 여러 번 시뮬레이션 실행
battle_results = {"A 승리": 0, "B 승리": 0}
num_simulations = 10000

for _ in range(num_simulations):
    A_copy = A.copy()
    B_copy = B.copy()
    result = battle_simulation(A_copy, B_copy)
    battle_results[result] += 1



print(battle_results)