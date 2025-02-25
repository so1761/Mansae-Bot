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

data = {
    "content": "🎲 주사위 정산!",
    "embeds": [
        {
            "title": "🎯 주사위 정산",
            "description": "어제 굴린 주사위 중 가장 높은 숫자는 **6**입니다!",
            "color": 0x00ff00,  # 초록색
            "fields": [
                {
                    "name": "결과",
                    "value": "**6** 🎉"
                }
            ],
            "footer": {
                "text": "Dice Bot",
                "icon_url": "https://i.imgur.com/your-icon.png"  # 아이콘 URL
            }
        }
    ]
}


response = requests.post(WEBHOOK_URL, json=data)

if response.status_code == 204:
    print("✅ Embed 메시지 전송 성공!")
else:
    print(f"❌ 메시지 전송 실패! 상태 코드: {response.status_code}")