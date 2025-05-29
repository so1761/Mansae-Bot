import math

# 전장 크기 (-10 ~ 10), 0은 없음
MAX_DISTANCE = 10
MIN_DISTANCE = -10

def calculate_damage_reduction(defense):
    return min(0.99, 1 - (100 / (100 + defense)))

def calculate_accuracy(accuracy):
    return min(0.99, 1 - (50 / (50 + accuracy)))

def calculate_evasion(distance):
    return (distance - 1) * 0.1

def calculate_move_chance(speed, move_chain=0):
    penalty_ratio = 0.7 ** move_chain
    effective_speed = speed * penalty_ratio
    move_chance = min(0.99, 1 - math.exp(-effective_speed / 70))
    return move_chance

def adjust_position(pos, move_distance, direction, MIN_DISTANCE, MAX_DISTANCE):
    for _ in range(move_distance):
        new_pos = pos + direction
        if new_pos == 0:
            new_pos += direction
        if MIN_DISTANCE <= new_pos <= MAX_DISTANCE:
            pos = new_pos
    return pos