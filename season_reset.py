import firebase_admin
import prediction_vote as p
import os
import requests
from firebase_admin import db
from firebase_admin import credentials
from datetime import datetime
from dotenv import load_dotenv
import re

load_dotenv()
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

cred = credentials.Certificate("mykey.json")
firebase_admin.initialize_app(cred,{
    'databaseURL' : 'https://mansaebot-default-rtdb.firebaseio.com/'
})

# 현재 시즌 가져오기
cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
current_predict_season = cur_predict_seasonref.get()

now = datetime.now()

# 연도 뒤의 2자리와 월 조합 (예: 2026년 2월 -> 26-2)
next_predict_season = f"{now.strftime('%y')}-{now.month}"

# 이제 DB에서 해당 시즌 데이터를 참조
cur_predict_seasonref = db.reference(f"승부예측/예측시즌/{current_predict_season}")
    
# 포인트 순위 가져오기
ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트')
points = ref.get()

# 포인트 순위를 기준으로 내림차순 정렬
sorted_data = sorted(points.items(), key=lambda x: x[1]['포인트'], reverse=True)

# 1등 찾기
winner = sorted_data[0] if sorted_data else None

if winner:
    winner_name, winner_info = winner
    embed = {
        "title": f"🏆 [{current_predict_season}] 시즌 종료 🏆",
        "description": f"🎉 {winner_name}님이 1등을 차지했습니다! 축하합니다! 🎉",
        "color": 0xFFD700,
        "fields": [
            {"name": "최종 포인트", "value": f"**{winner_info['포인트']}**", "inline": True},
            {"name": "적중률", "value": f"{winner_info['적중률']} ({winner_info['적중 횟수']}/{winner_info['총 예측 횟수']})", "inline": True},
        ],
        "footer": {"text": "새 시즌도 많은 참여 부탁드립니다!"},
        "timestamp": datetime.utcnow().isoformat()
    }
else:
    embed = {
        "title": "🏆 시즌 종료 🏆",
        "description": "이번 시즌에는 1등이 없습니다.",
        "color": 0x808080,
        "footer": {"text": "새 시즌도 많은 참여 부탁드립니다!"},
        "timestamp": datetime.utcnow().isoformat()
    }

# 디스코드 웹훅으로 메시지 전송
response = requests.post(WEBHOOK_URL, json={"embeds": [embed]})


# 시즌 업데이트 (다음 시즌으로 변경)
cur_predict_seasonref.set(next_predict_season)
print(f"시즌이 [{next_predict_season}]으로 변경되었습니다.")

if response.status_code == 204:
    print("✅ 시즌 종료 메시지 전송 성공!")
else:
    print(f"❌ 메시지 전송 실패! 상태 코드: {response.status_code}")
