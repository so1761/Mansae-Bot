import firebase_admin
from firebase_admin import db
from firebase_admin import credentials
from datetime import datetime

cred = credentials.Certificate("mykey.json")
firebase_admin.initialize_app(cred,{
    'databaseURL' : 'https://mansaebot-default-rtdb.firebaseio.com/'
})

mref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/toe_kyung')
mref2 = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/toe_kyung/베팅포인트')
minfo = mref.get()
mbettingPoint = mref2.get()
mpoint = minfo['포인트']
print(f"Point : {mpoint}, BettingPoint : {mbettingPoint}")
if mpoint == mbettingPoint: # 포인트의 전부를 베팅포인트로 넣음
    print("달성!")