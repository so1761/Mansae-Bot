import firebase_admin
from firebase_admin import db
from firebase_admin import credentials
from datetime import datetime

cred = credentials.Certificate("mykey.json")
firebase_admin.initialize_app(cred,{
    'databaseURL' : 'https://mansaebot-default-rtdb.firebaseio.com/'
})

now = datetime.now()
date_str = now.strftime("[%Y-%m-%d]")  # 로그 날짜 추가

cur_predict_seasonref = db.reference("승부예측/현재예측시즌") # 현재 진행중인 예측 시즌을 가져옴
current_predict_season = cur_predict_seasonref.get()

ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트")
users = ref.get()

if users:
    for nickname, data in users.items():
        mission_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname}/미션/일일미션")
        dice_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname}/")
        daily_missions = mission_ref.get()

        dice_ref.update({"주사위" : False})
        if daily_missions:
            update_data = {mission_name + "/완료": False for mission_name in daily_missions}
            update_data2 = {mission_name + "/보상수령": False for mission_name in daily_missions}
            mission_ref.update(update_data)  # 모든 미션 초기화
            mission_ref.update(update_data2)

print(f"{date_str} 모든 사용자의 일일미션이 초기화되었습니다.")

today = datetime.now()
if today.weekday() == 6:
    solowatch_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}")
    solowatch_ref.update({"혼자보기포인트" : 100})
    print(f"{date_str} 혼자보기 포인트가 100으로 초기화되었습니다.")
