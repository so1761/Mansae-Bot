import numpy as np

for speed in range(0, 200, 10):
    # e^-1 계산
    value = 1 - np.exp(-speed / 70)
    print(f"스피드 : {speed}, 이동 확률 : {int(value * 100)}%")