import firebase_admin
from firebase_admin import db
from firebase_admin import credentials
from datetime import datetime
import requests
import os
from dotenv import load_dotenv

cred = credentials.Certificate("mykey.json")
firebase_admin.initialize_app(cred,{
    'databaseURL' : 'https://mansaebot-default-rtdb.firebaseio.com/'
})

load_dotenv()
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
current_predict_season = cur_predict_seasonref.get()

refname = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트")
name_data = refname.get()

# 족보 우선순위 딕셔너리 (낮은 숫자가 높은 우선순위)
hand_rankings = {
    "🎉 Yacht!": 0,
    "➡️ Large Straight!": 1,
    "🏠 Full House!": 2,
    "🔥 Four of a Kind!": 3,
    "🡒 Small Straight!": 4,
    "🎲 Chance!": 5
}

hand_bet_rate = {
    0: 50,
    1: 5,
    2: 3,
    3: 2,
    4: 1.5,
    5: 1
}

best_player = []  # 가장 높은 족보를 가진 플레이어
best_hand_rank = float('inf')  # 초기값을 무한대로 설정
best_total = -1  # 주사위 합계를 비교할 변수

for nickname, point_data in name_data.items():
    refdice = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname}/야추")
    yacht = refdice.get() or {}

    yacht_hand = yacht.get("족보", "🎲 Chance!")  # 기본값은 Chance!
    rolls = yacht.get("결과", [])  # 플레이어의 주사위 값
    total = sum(rolls) if rolls else 0  # 주사위 총합 계산

    hand_rank = hand_rankings.get(yacht_hand.split(" (")[0], 5)  # 족보 랭킹 가져오기 (Chance는 따로 처리)

    # 1. 더 높은 족보를 찾으면 갱신
    if hand_rank < best_hand_rank:
        best_player = [nickname]
        best_hand_rank = hand_rank
        best_total = total
    # 2. 같은 족보라면 주사위 총합으로 비교
    elif hand_rank == best_hand_rank:
        if total > best_total:
            best_player = [nickname]
            best_total = total
        if total == best_total:
            best_player.append(nickname)

if len(best_player) == 1:
    point_message = f"{', '.join([f'**{winner}**' for winner in best_player])}에게 **{best_total * hand_bet_rate[best_hand_rank]}**포인트 지급! 🎉"
else:
    point_message = f"**{best_player[0]}**님에게 **{best_total * hand_bet_rate[best_hand_rank]}**포인트 지급! 🎉"

refdice = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{best_player[0]}/야추")
yacht = refdice.get() or {}
yacht_hand = yacht.get("족보", "🎲 Chance!")  # 기본값은 Chance!

yacht_data = {
    "content": "",
    "embeds": [
        {
            "title": "🎯 주사위 정산",
            "description": "",
            "color": 0x00ff00,  # 초록색
            "fields": [
                {
                    "name": "족보",
                    "value": f"**최고 족보: {yacht_hand}**(총합 : {best_total})"
                },
                {
                    "name": "결과",
                    "value": f"배율 : **{hand_bet_rate[best_hand_rank]}배**!\n{point_message}"
                }
            ],
            "footer": {
                "text": "Dice Bot",
            }
        }
    ]
}


# 포인트 지급
for winner in best_player:
    ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner}/")
    point_data = ref.get()
    point = point_data.get("포인트")
    ref.update({"포인트" : point + (best_total * hand_bet_rate[best_hand_rank])})

    current_datetime = datetime.now() # 데이터베이스에 남길 현재 시각 기록
    current_date = current_datetime.strftime("%Y-%m-%d")
    current_time = current_datetime.strftime("%H:%M:%S")
    change_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트변동로그/{current_date}/{winner}")
    change_ref.push({
        "시간": current_time,
        "포인트": point + (best_total * hand_bet_rate[best_hand_rank]),
        "포인트 변동": best_total * hand_bet_rate[best_hand_rank],
        "사유": "야추 이벤트"
    })

response = requests.post(WEBHOOK_URL, json=yacht_data)

if response.status_code == 204:
    print("✅ 야추 메시지 전송 성공!")
else:
    print(f"❌ 메시지 전송 실패! 상태 코드: {response.status_code}")