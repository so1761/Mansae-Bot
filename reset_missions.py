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

refname = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트")
name_data = refname.get()

dice_nums = []
for nickname, point_data in name_data.items():
    refdice = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname}/주사위")
    dice_nums.append((refdice.get(),nickname))

max_dice_num = max(dice_nums, key=lambda x: x[0])[0]

winners = [name for num, name in dice_nums if num == max_dice_num]

if len(winners) > 1:
    point_message = f"{', '.join([f'**{winner}**' for winner in winners])}에게 **{max_dice_num}**포인트 지급! 🎉"
else:
    point_message = f"**{winners[0]}**님에게 **{max_dice_num}**포인트 지급! 🎉"
dice_data = {
    "content": "",
    "embeds": [
        {
            "title": "🎯 주사위 정산",
            "description": f"어제 굴린 주사위 중 가장 높은 숫자는 **{max_dice_num}**입니다!",
            "color": 0x00ff00,  # 초록색
            "fields": [
                {
                    "name": "결과",
                    "value": point_message
                }
            ],
            "footer": {
                "text": "Dice Bot",
            }
        }
    ]
}

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
        elif total == best_total:
            best_player.append(nickname)

if len(best_player) > 1:
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

# 보스 레이드 결과 처리
max_reward_per_boss = 15
ref_boss_list = db.reference("레이드/보스목록")
all_boss_order = ref_boss_list.get()  # 예: ["스우", "브라움", "카이사", "팬텀", ...]

ref_boss_order = db.reference("레이드/순서")
today = ref_boss_order.get()  # 예: 2

# 시계방향 순환하며 4마리 선택
today_bosses = []
for i in range(4):
    index = (today + i) % len(all_boss_order)
    today_bosses.append(all_boss_order[index])

ref_current_boss = db.reference("레이드/현재 레이드 보스")
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
ref_all_logs = db.reference("레이드/내역")
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
ref_boss_data = db.reference(f"레이드/보스/{current_boss}")
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
ref_boss = db.reference(f"레이드/보스/")
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

#=========== [레이드] ============

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

# 포인트 지급
for winner in winners:
    ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner}/")
    point_data = ref.get()
    point = point_data.get("포인트")
    ref.update({"포인트" : point + max_dice_num})

    current_datetime = datetime.now() # 데이터베이스에 남길 현재 시각 기록
    current_date = current_datetime.strftime("%Y-%m-%d")
    current_time = current_datetime.strftime("%H:%M:%S")
    change_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트변동로그/{current_date}/{winner}")
    change_ref.push({
        "시간": current_time,
        "포인트": point + max_dice_num,
        "포인트 변동": max_dice_num,
        "사유": "주사위 이벤트"
    })
    
response = requests.post(WEBHOOK_URL, json=dice_data)

if response.status_code == 204:
    print("✅ 주사위 메시지 전송 성공!")
else:
    print(f"❌ 메시지 전송 실패! 상태 코드: {response.status_code}")

response = requests.post(WEBHOOK_URL, json=yacht_data)

if response.status_code == 204:
    print("✅ 야추 메시지 전송 성공!")
else:
    print(f"❌ 메시지 전송 실패! 상태 코드: {response.status_code}")

response = requests.post(WEBHOOK_URL, json=raid_result) # 레이드 메세지

if response.status_code == 204:
    print("✅ 레이드 메시지 전송 성공!")
else:
    print(f"❌ 메시지 전송 실패! 상태 코드: {response.status_code}")
    
ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트")
users = ref.get()

if users:
    for nickname, data in users.items():
        dice_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname}/")
        yacht_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname}/야추")
        
        dice_ref.update({"주사위" : 0})
        yacht_ref.update({"족보" : ""})
        yacht_ref.update({"결과" : []})
        yacht_ref.update({"실행 여부" : False})

        ref_current_floor = db.reference(f"탑/유저/{nickname}")
        tower_data = ref_current_floor.get() or {}
        if not tower_data:
            ref_current_floor.set({"층수": 1})
            current_floor = 1
        else:
            current_floor = tower_data.get("층수", 1)
        
        ref_current_floor.update({"등반여부": False})

        ref_mirror = db.reference(f"무기/거울")
        ref_mirror.set("")

        dice_ref.update({"배틀여부" : False})
        dice_ref.update({"숫자야구배틀여부" : False})

        p.votes['배틀']['name']['challenger'] = ""
        p.votes['배틀']['name']['상대'] = ""

#====== [미션 초기화] =====
mission_ref = db.reference(f"미션/미션진행상태")
daily_missions = mission_ref.get()
all_users = mission_ref.get()  # 전체 사용자 데이터 불러오기

if all_users:
    for nickname in all_users.keys():
        daily_mission_ref = mission_ref.child(f"{nickname}/일일미션")
        daily_mission_ref.delete()
        
        seasonal_mission_ref = mission_ref.child(f"{nickname}/시즌미션/선봉장")
        if seasonal_mission_ref.get() is not None:
            seasonal_mission_ref.update({"오늘달성": False})

#===== [미션 초기화] ======
print(f"{date_str} 모든 사용자의 일일미션이 초기화되었습니다.")

today = datetime.now()
if today.weekday() == 6:
    solowatch_ref = db.reference(f"승부예측/")
    solowatch_ref.update({"혼자보기포인트" : 100})
    print(f"{date_str} 혼자보기 포인트가 100으로 초기화되었습니다.")
    data = {
    "content": "",
    "embeds": [
        {
            "title": "포인트 초기화",
            "description": "혼자보기 포인트가 100으로 초기화되었습니다!",
            "color": 0x00ff00,  # 초록색
            "footer": {
                "text": "Mansae-Bot",
            }
        }
    ]
    }
    

    response = requests.post(WEBHOOK_URL, json=data)


if today.weekday() == 0:
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
    print(f"{date_str} 탑 진행상황이 초기화되었습니다.")
    data = {
    "content": "",
    "embeds": [
        {
            "title": "탑 초기화",
            "description": "탑 진행상황이 초기화되었습니다!",
            "color": 0x00ff00,  # 초록색
            "footer": {
                "text": "Mansae-Bot",
            }
        }
    ]
    }
    

    response = requests.post(WEBHOOK_URL, json=data)