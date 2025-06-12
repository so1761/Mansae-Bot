import firebase_admin
from firebase_admin import db
from firebase_admin import credentials
from datetime import datetime
import requests
import os
import math
from dotenv import load_dotenv

WEBHOOK_URL = 'https://discord.com/api/webhooks/1382538433188331640/kB1tUaiuW0hjJHYD1I6Td4qJuyHSheGCBKwu-gw83zoZn5KunARVdlTEW96mxRo5ChbJ'

cred = credentials.Certificate("mykey.json")
firebase_admin.initialize_app(cred,{
    'databaseURL' : 'https://mansaebot-default-rtdb.firebaseio.com/'
})

load_dotenv()

# 보스 레이드 결과 처리
max_reward_per_boss = 15
ref_boss_list = db.reference("테스트레이드/보스목록")
all_boss_order = ref_boss_list.get()  # 예: ["스우", "브라움", "카이사", "팬텀", ...]

ref_boss_order = db.reference("테스트레이드/순서")
today = ref_boss_order.get()  # 예: 2

# 시계방향 순환하며 4마리 선택
today_bosses = []
for i in range(4):
    index = (today + i) % len(all_boss_order)
    today_bosses.append(all_boss_order[index])

ref_current_boss = db.reference("테스트레이드/현재 레이드 보스")
current_boss = ref_current_boss.get()

# 보스 순서 문자열 생성
boss_display = []
for boss in today_bosses:
    if boss == current_boss:
        boss_display.append(f"**[{boss}]**")
    else:
        boss_display.append(f"[{boss}]")
boss_order_str = " ➝ ".join(boss_display)

# 유저별 누적 대미지 + 남은 내구도 조회
ref_all_logs = db.reference("테스트레이드/내역")
all_logs = ref_all_logs.get() or {}

user_total_damage = {}
user_last_hp = {}

for username, bosses in all_logs.items():
    total_damage = 0
    for boss_name, record in bosses.items():
        total_damage += record.get("대미지", 0)
        if "남은내구도" in record:
            user_last_hp[username] = record["남은내구도"]
    if total_damage > 0:
        user_total_damage[username] = total_damage

sorted_users = sorted(user_total_damage.items(), key=lambda x: x[1], reverse=True)

# 랭킹 정리
rankings = []
for i, (username, total_dmg) in enumerate(sorted_users, start=1):
    remain_hp = user_last_hp.get(username)
    hp_text = f" [:heart: {remain_hp}]" if remain_hp is not None else ""
    rankings.append(f"{i}위: {username} - {total_dmg} 대미지{hp_text}")

# 현재 보스 정보
ref_boss_data = db.reference(f"테스트레이드/보스/{current_boss}")
boss_data = ref_boss_data.get() or {}
cur_dur = boss_data.get("내구도", 0)
total_dur = boss_data.get("총 내구도", 0)

# 현재 보스 체력 비율
remain_durability_ratio = round(cur_dur / total_dur * 100, 2) if total_dur else 0

# 보상 계산
current_index = today_bosses.index(current_boss) if current_boss in today_bosses else 0
base_reward = max_reward_per_boss * current_index
partial_reward = 0
if total_dur > 0:
    durability_ratio = (total_dur - cur_dur) / total_dur
    partial_reward = math.floor(max_reward_per_boss * durability_ratio)

total_reward = base_reward + partial_reward

# 현재 보스 정보
ref_boss = db.reference(f"테스트레이드/보스/")
raid_bosses = ref_boss.get() or {}

for boss, boss_data in raid_bosses.items():
    # 기존 값 가져오기 (없으면 기본값 0)
    total_dura = boss_data.get("총 내구도", 0)
    current_dura = boss_data.get("내구도", 0)
    attack = boss_data.get("공격력", 0)
    skill_amp = boss_data.get("스킬 증폭", 0)
    defense = boss_data.get("방어력", 0)
    speed = boss_data.get("스피드", 0)
    accuracy = boss_data.get("명중", 0)

    if current_dura <= 0: # 토벌당한 보스는 스탯이 오름
        # 업데이트 값 계산
        updates = {
            "내구도": total_dura + 500,
            "총 내구도": total_dura + 500,
            "공격력": attack + 10,
            "스킬 증폭": skill_amp + 20,
            "방어력": defense + 20,
            "스피드": speed + 10,
            "명중": accuracy + 20,
        }
    else:
        # 나머지 보스는 유지
        updates = {
            "내구도": total_dura,
            "총 내구도": total_dura,
        }

    # 보스 데이터 업데이트
    ref_boss.child(boss).update(updates)

ref_all_logs.delete() # 내역 삭제

# 보스 순서 변경
today = (today + 1) % len(all_boss_order) # 순서의 값을 + 1
ref_boss_order.set(today)
ref_current_boss.set(all_boss_order[today]) # 현재 레이드 보스 변경


participants = list(all_logs.keys())
for participant, data in all_logs.items():
    ref_item = db.reference(f"무기/아이템/{participant}")
    item_data = ref_item.get() or {}
    weapon_parts = item_data.get("강화재료", 0)
    ref_item.update({"강화재료" : weapon_parts + total_reward})

# 필드 정리
fields = [
    {
        "name": "레이드 보스",
        "value": boss_order_str,
        "inline": False
    },
    {
        "name": "보스 내구도",
        "value": f"[{cur_dur}/{total_dur}] ({remain_durability_ratio}%)",
        "inline": False
    },
    {
        "name": "대미지 랭킹",
        "value": "\n".join(rankings) if rankings else "기록 없음",
        "inline": False
    },
    {
        "name": "보상",
        "value": f"강화재료 **{total_reward}개** 지급!",
        "inline": False
    }
]


# 웹훅 메시지용 JSON
raid_result = {
    "content": "",  # 여기엔 멘션 등 텍스트 메시지를 쓸 수 있음. 예: "@everyone 레이드 종료!"
    "embeds": [
        {
            "title": "🎯 레이드 정산",
            "description": "",
            "color": 0x00ff00,
            "fields": fields,
            "footer": {
                "text": "Raid Bot"
            }
        }
    ]
}

response = requests.post(WEBHOOK_URL, json=raid_result)