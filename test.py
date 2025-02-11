from firebase_admin import db
from firebase_admin import credentials
import firebase_admin
from datetime import datetime

cred = credentials.Certificate("mykey.json")
firebase_admin.initialize_app(cred,{
            'databaseURL' : 'https://mansaebot-default-rtdb.firebaseio.com/'
        })

curseasonref = db.reference("전적분석/현재시즌")
current_season = curseasonref.get()

current_datetime = datetime.now() # 데이터베이스에 남길 현재 시각 기록
current_date = current_datetime.strftime("%Y-%m-%d")
current_time = current_datetime.strftime("%H:%M:%S")

ref = db.reference(f'전적분석/{current_season}/점수변동/지모/솔로랭크')
points = ref.get()

point_change = 0
if points is None:
    game_win_streak = 0
    game_lose_streak = 0
    result = True
else:
        # 날짜 정렬
    sorted_dates = sorted(points.keys(), key=lambda d: datetime.strptime(d, '%Y-%m-%d'))

    # 가장 최근 날짜 가져오기
    latest_date = sorted_dates[-1]
    latest_times = sorted(points[latest_date].keys(), key=lambda t: datetime.strptime(t, '%H:%M:%S'))

    if len(latest_times) > 1:
        # 같은 날짜에 여러 게임이 있는 경우, 가장 최근 경기의 "바로 전 경기" 선택
        previous_time = latest_times[-2]
        latest_time = latest_times[-1]
    else:
        # 가장 최근 날짜에 한 판만 있었다면, 이전 날짜로 넘어감
        if len(sorted_dates) > 1:
            previous_date = sorted_dates[-2]
            previous_times = sorted(points[previous_date].keys(), key=lambda t: datetime.strptime(t, '%H:%M:%S'))
            previous_time = previous_times[-1]  # 이전 날짜에서 가장 늦은 경기
            latest_time = latest_times[-1]
        else:
            # 데이터가 한 판밖에 없는 경우 (첫 경기), 연승/연패 초기화
            game_win_streak = 0
            game_lose_streak = 0
            latest_time = latest_times[-1]
            previous_time = None

    # 최신 경기 데이터
    latest_data = points[latest_date][latest_time]
    point_change = latest_data['LP 변화량']
    result = point_change > 0  # 승리 여부 판단

    if previous_time:
        # "바로 전 경기" 데이터 가져오기
        if previous_time in points[latest_date]:  # 같은 날짜에서 찾은 경우
            previous_data = points[latest_date][previous_time]
        else:  # 이전 날짜에서 가져온 경우
            previous_data = points[previous_date][previous_time]

        # "바로 전 경기"의 연승/연패 기록 사용
        game_win_streak = previous_data["연승"]
        game_lose_streak = previous_data["연패"]
    else:
        # 첫 경기라면 연승/연패 초기화
        game_win_streak = 0
        game_lose_streak = 0

print(f"result = {result}")
print(f"game_win_streak = {game_win_streak}")
print(f"game_lose_streak = {game_lose_streak}")
