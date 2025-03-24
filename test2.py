import pandas as pd

def final_hit_chance_new(attacker_accuracy, defender_speed, evade_factor=150, accuracy_factor=150):
    evade = defender_speed / (defender_speed + evade_factor)
    accuracy_compensate = (attacker_accuracy / (attacker_accuracy + accuracy_factor))
    hit_chance = 1.0 - (evade * (1 - accuracy_compensate))
    return round(max(0.05, min(0.99, hit_chance)) * 100, 1)

# 테스트 테이블 생성
accuracy_values = range(0, 201, 25)    # accuracy: 50 ~ 200 (25 단위)
speed_values = range(0, 201, 25)        # speed: 0 ~ 200 (25 단위)

# evade_factor=100, accuracy_factor=100 기준 테스트 테이블
data = []
for acc in accuracy_values:
    row = []
    for spd in speed_values:
        hit = final_hit_chance_new(acc, spd, 250, 50)
        row.append(hit)
    data.append(row)

df_test_table = pd.DataFrame(data, index=accuracy_values, columns=speed_values)
df_test_table.index.name = 'Accuracy'
df_test_table.columns.name = 'Defender Speed'

# 결과 출력
print(df_test_table)