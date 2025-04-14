import firebase_admin
import prediction_vote as p
import os
import requests
from firebase_admin import db
from firebase_admin import credentials
from datetime import datetime
from dotenv import load_dotenv
import math

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

  
ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트")
users = ref.get()

if users:
    for nickname, data in users.items():
        ref_current_floor = db.reference(f"탑/유저/{nickname}")
        tower_data = ref_current_floor.get() or {}
        if tower_data:
            ref_current_floor.set({"층수": 1})
            current_floor = 1
        
        ref_current_floor.update({"등반여부": False})