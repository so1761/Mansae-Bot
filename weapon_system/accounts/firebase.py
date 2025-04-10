import firebase_admin
from firebase_admin import credentials
import os

# 현재 파일 경로를 기준으로 ../../mykey.json 파일 경로 설정
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
key_path = os.path.join(base_dir, '../../mykey.json')

# 경로가 잘 설정되었는지 확인
print(f"Firebase key path: {key_path}")

# Firebase 인증 초기화
cred = credentials.Certificate(key_path)
firebase_admin.initialize_app(cred)