import firebase_admin
import prediction_vote as p
import os
import requests
from firebase_admin import db
from firebase_admin import credentials
from datetime import datetime
from dotenv import load_dotenv
from collections import defaultdict
import json

load_dotenv()
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

cred = credentials.Certificate("mykey.json")
firebase_admin.initialize_app(cred,{
    'databaseURL' : 'https://mansaebot-default-rtdb.firebaseio.com/'
})

def fetch_prediction_logs():
    ref = db.reference('승부예측/예측시즌/정규시즌2/예측포인트변동로그')
    data = ref.get()
    return data

def analyze_data(data):
    total_changes = defaultdict(int)
    user_changes = defaultdict(lambda: defaultdict(int))
    
    for date, users in data.items():
        for user, logs in users.items():
            for log_id, log in logs.items():
                reason = log.get('사유', '알 수 없음')
                points = log.get('포인트 변동', 0)
                
                # 전체 사유별 변동 합산
                total_changes[reason] += points
                
                # 유저별 사유별 변동 합산
                user_changes[user][reason] += points
                
    return total_changes, user_changes

def main():
    data = fetch_prediction_logs()
    if not data:
        print("No data found.")
        return
    
    total_changes, user_changes = analyze_data(data)
    
    print("전체 사유별 포인트 변동:")
    print(json.dumps(total_changes, indent=4, ensure_ascii=False))
    
    print("유저별 포인트 변동:")
    print(json.dumps(user_changes, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    main()
