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

# 현재 시즌에서 숫자 추출 후 +1
match = re.search(r'\d+', current_predict_season)
if match:
    next_season_number = int(match.group()) + 1
    next_season = re.sub(r'\d+', str(next_season_number), current_predict_season)
else:
    next_season = current_predict_season + "1"
    
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
        "title": f"🏆 {current_predict_season} 시즌 종료 🏆",
        "description": f"🎉 {winner_name}님이 1등을 차지했습니다! 축하합니다! 🎉",
        "color": 0xFFD700,
        "fields": [
            {"name": "최종 포인트", "value": f"{winner_info['포인트']}", "inline": True},
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

# 기존 시즌의 강화 재료 가져오기
current_items_ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/아이템')
current_items = current_items_ref.get() or {}
next_items_ref = db.reference(f'승부예측/예측시즌/{next_season}/아이템')

# 기존 시즌의 강화 재료를 새로운 시즌으로 추가
for item, details in current_items.items():
    if "강화재료" in details:
        if item in next_items_ref.get() or {}:
            next_items_ref.child(item).update({"강화재료": details["강화재료"]})
        else:
            next_items_ref.child(item).set({"강화재료": details["강화재료"]})

# 시즌 업데이트 (다음 시즌으로 변경)
cur_predict_seasonref.set(next_season)
print(f"시즌이 {next_season}으로 변경되었습니다.")

if response.status_code == 204:
    print("✅ 주사위 메시지 전송 성공!")
else:
    print(f"❌ 메시지 전송 실패! 상태 코드: {response.status_code}")
