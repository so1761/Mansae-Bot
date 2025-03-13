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

ref_item = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/melon_0_0/아이템")
item_data = ref_item.get()
dice_refresh = item_data.get('주사위 초기화', 0)
print(dice_refresh)