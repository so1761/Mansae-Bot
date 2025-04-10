import firebase_admin
from firebase_admin import credentials, db

def initialize_firebase():
    # Firebase 인증 설정
    if not firebase_admin._apps:  # Firebase 앱이 이미 초기화되어 있지 않다면
        cred = credentials.Certificate("../mykey.json")
        firebase_admin.initialize_app(cred,{
            'databaseURL' : 'https://mansaebot-default-rtdb.firebaseio.com/'
        })
    else:
        print("Firebase 앱은 이미 초기화되었습니다.")