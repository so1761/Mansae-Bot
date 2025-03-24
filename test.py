import firebase_admin
import prediction_vote as p
import os
import requests
from firebase_admin import db
from firebase_admin import credentials
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

cred = credentials.Certificate("mykey.json")
firebase_admin.initialize_app(cred,{
    'databaseURL' : 'https://mansaebot-default-rtdb.firebaseio.com/'
})

now = datetime.now()
date_str = now.strftime("[%Y-%m-%d]")  # 로그 날짜 추가

cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
current_predict_season = cur_predict_seasonref.get()

refraid = db.reference(f"승부예측/예측시즌/{current_predict_season}/레이드/내역")
raid_data = refraid.get() or {}

raid_data_sorted = sorted(raid_data.items(), key=lambda x: x[1]['대미지'], reverse=True)

# 순위별로 대미지 항목을 생성
rankings = []
for idx, (nickname, data) in enumerate(raid_data_sorted, start=1):
    damage = data['대미지']
    if data.get('막타', False):
        rankings.append(f"**{idx}위**: {nickname} - {damage} 대미지 🎯")
    else:
        rankings.append(f"**{idx}위**: {nickname} - {damage} 대미지")

refraidboss = db.reference(f"승부예측/예측시즌/{current_predict_season}/레이드/")
raid_boss_data = refraidboss.get() or {}
cur_dur = raid_boss_data.get("내구도", 0)
total_dur = raid_boss_data.get("초기 내구도",0)

refraidboss.update({"내구도" : total_dur})

# 순위표를 포함한 embed 내용
data = {
    "content": "",
    "embeds": [
        {
            "title": "🎯 레이드 정산",
            "description": f"레이드 보스의 체력 [{cur_dur}/{total_dur}]",
            "color": 0x00ff00,  # 초록색
            "fields": [
                {
                    "name": "결과",
                    "value": "\n".join(rankings)  # 순위표를 필드에 추가
                }
            ],
            "footer": {
                "text": "Raid Bot",
            }
        }
    ]
}