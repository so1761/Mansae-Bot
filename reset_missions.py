import firebase_admin
from firebase_admin import db

cred = credentials.Certificate("mykey.json")
firebase_admin.initialize_app(cred,{
    'databaseURL' : 'https://mansaebot-default-rtdb.firebaseio.com/'
})

now = datetime.datetime.now()
date_str = now.strftime("[%Y-%m-%d]")  # 로그 날짜 추가

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
            mission_ref.update(update_data)  # 모든 미션 초기화

print(f"{date_str} 모든 사용자의 일일미션이 초기화되었습니다.")