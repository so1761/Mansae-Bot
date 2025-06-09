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
max_reward = 20

ref_current_boss = db.reference(f"레이드/현재 레이드 보스")
boss_name = ref_current_boss.get()

refraid = db.reference(f"레이드/내역")
raid_all_data = refraid.get() or {}

raid_data = {key:value for key, value in raid_all_data.items() if value['보스'] == boss_name and value['모의전'] == False}
# 전체 대미지 합산
total_damage = sum(data['대미지'] for data in raid_data.values())

raid_data_sorted = sorted(raid_data.items(), key=lambda x: x[1]['대미지'], reverse=True)

# 순위별로 대미지 항목을 생성
rankings = []
for idx, (nickname, data) in enumerate(raid_data_sorted, start=1):
    damage = data['대미지']
    if data.get('막타', False):
        rankings.append(f"**{idx}위**: {nickname} - {damage} 대미지 🎯")
    else:
        rankings.append(f"**{idx}위**: {nickname} - {damage} 대미지")


refraidboss = db.reference(f"레이드/보스/{boss_name}")
raid_boss_data = refraidboss.get() or {}
cur_dur = raid_boss_data.get("내구도", 0)
total_dur = raid_boss_data.get("총 내구도",0)

# 내구도 비율 계산
if total_dur > 0:
    durability_ratio = (total_dur - cur_dur) / total_dur  # 0과 1 사이의 값
    reward_count = math.floor(max_reward * durability_ratio)  # 총 20개의 재료 중, 내구도에 비례한 개수만큼 지급
else:
    reward_count = 0  # 보스가 이미 처치된 경우

cleared = False
if cur_dur <= 0: # 보스가 처치된 경우
    cleared = True


raid_root = db.reference("레이드/보스")
raid_bosses = raid_root.get() or {}


# 오늘 요일 가져오기 (0=월, 6=일)
weekday = datetime.now().weekday()

boss_order = ["팬텀", "카이사", "스우", "브라움"]

ref_current_boss = db.reference(f"레이드/현재 레이드 보스")
current_boss = ref_current_boss.get()
if current_boss is None:
    current_boss = boss_order[0]  # 없으면 첫 보스부터 시작

# 현재 보스 클리어 여부
if cleared:
    # 현재 보스 인덱스를 찾고 다음 보스로 이동
    current_index = boss_order.index(current_boss)
    next_index = (current_index + 1) % len(boss_order)  # 순환
    next_boss = boss_order[next_index]
    
    current_boss = next_boss


# Firebase에 현재 보스 업데이트
raid_boss_root = db.reference("레이드")
raid_boss_root.update({"현재 레이드 보스": current_boss})

participants = list(raid_data.keys())
for participant, data in raid_data.items():
    ref_item = db.reference(f"무기/아이템/{participant}")
    item_data = ref_item.get() or {}
    weapon_parts = item_data.get("강화재료", 0)
    ref_item.update({"강화재료" : weapon_parts + reward_count})

    if cleared: # 보스가 처치된 경우
        if boss_name == "카이사":
            random_box = item_data.get("랜덤박스") or 0
            ref_item.update({"랜덤박스": random_box + 1})
        elif boss_name == "스우":
            polish = item_data.get("연마제") or 0
            ref_item.update({"연마제": polish + 2})
        elif boss_name == "브라움":
            Rune_of_Twisted_Fate = item_data.get("운명 왜곡의 룬") or 0
            ref_item.update({"운명 왜곡의 룬": Rune_of_Twisted_Fate + 3})
        elif boss_name == "팬텀":
            weapon_parts = item_data.get("강화재료") or 0
            ref_item.update({"강화재료": weapon_parts + reward_count + 3})
        else:
            weapon_parts = item_data.get("강화재료") or 0
            ref_item.update({"강화재료": weapon_parts + reward_count + 3})

    if data.get('막타',False):
        raid_retry = item_data.get("레이드 재도전") or 0
        ref_item.update({"레이드 재도전": raid_retry + 1})

refraid.set("")

if cleared:
    for boss, boss_data in raid_bosses.items():
        # 기존 값 가져오기 (없으면 기본값 0)
        total_dura = boss_data.get("총 내구도", 0)
        attack = boss_data.get("공격력", 0)
        skill_amp = boss_data.get("스킬 증폭", 0)
        defense = boss_data.get("방어력", 0)
        speed = boss_data.get("스피드", 0)
        accuracy = boss_data.get("명중", 0)

        if boss == boss_name:
            # 업데이트 값 계산
            updates = {
                "내구도": total_dura + 1000,
                "총 내구도": total_dura + 1000,
                "공격력": attack + 10,
                "스킬 증폭": skill_amp + 20,
                "방어력": defense + 15,
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
        raid_root.child(boss).update(updates)
else:
    for boss, boss_data in raid_bosses.items():
        # 기존 값 가져오기 (없으면 기본값 0)
        total_dura = boss_data.get("총 내구도", 0)
        attack = boss_data.get("공격력", 0)
        skill_amp = boss_data.get("스킬 증폭", 0)
        defense = boss_data.get("방어력", 0)
        speed = boss_data.get("스피드", 0)
        accuracy = boss_data.get("명중", 0)

        updates = {
            "내구도": total_dura,
            "총 내구도": total_dura,
        }

        # 보스 데이터 업데이트
        raid_root.child(boss).update(updates)

# 기본 필드 리스트
fields = [
    {
        "name": "결과",
        "value": "\n".join(rankings)  # 순위표 추가
    }
]

clear_message = ""
if cleared: # 보스가 처치된 경우
    if boss_name == "카이사":
        clear_message = "\n카이사 토벌로 **랜덤박스** 지급!"
    elif boss_name == "스우":
        clear_message = "\n스우 토벌로 **연마제 2개** 지급!"
    elif boss_name == "브라움":
        clear_message = "\n브라움 토벌로 **운명 왜곡의 룬 3개** 지급!"
    elif boss_name == "팬텀":
        clear_message = "\n팬텀 토벌로 **강화재료 3개** 지급!"
    else:
        clear_message = "\n보스 토벌로 **강화재료 3개** 지급!"

# 보상 필드 추가
fields.append({
    "name": "보상",
    "value": f"강화 재료 **{reward_count}개** 지급!{clear_message}"
})

raid_after_data = {key:value for key, value in raid_all_data.items() if value['보스'] == boss_name and value['모의전'] == True}
raid_after_data_sorted = sorted(raid_after_data.items(), key=lambda x: x[1]['대미지'], reverse=True)
# 순위별로 대미지 항목을 생성
after_rankings = []
for idx, (nickname, data) in enumerate(raid_after_data_sorted, start=1):
    damage = data['대미지']
    damage_ratio = round(damage/total_dur * 100)
    reward_number = int(round(max_reward * 0.75))
    after_rankings.append(f"{nickname} - {damage} 대미지 ({damage_ratio}%)\n(강화재료 {reward_number}개 지급!)")

    ref_item = db.reference(f"무기/아이템/{nickname}")
    item_data = ref_item.get() or {}
    weapon_parts = item_data.get("강화재료", 0)
    ref_item.update({"강화재료" : weapon_parts + reward_number})
    if boss_name == "카이사":
        random_box = item_data.get("랜덤박스") or 0
        ref_item.update({"랜덤박스": random_box + 1})
    elif boss_name == "스우":
        polish = item_data.get("연마제") or 0
        ref_item.update({"연마제": polish + 2})
    elif boss_name == "브라움":
        Rune_of_Twisted_Fate = item_data.get("운명 왜곡의 룬") or 0
        ref_item.update({"운명 왜곡의 룬": Rune_of_Twisted_Fate + 3})
    elif boss_name == "팬텀":
        weapon_parts = item_data.get("강화재료") or 0
        ref_item.update({"강화재료": weapon_parts + reward_number + 3})
    else:
        weapon_parts = item_data.get("강화재료") or 0
        ref_item.update({"강화재료": weapon_parts + reward_number + 3})
    
# 보상 필드 추가
fields.append({
    "name": "추가 도전자 보상",
    "value": "\n".join(after_rankings)
})

# 임베드 메시지 생성
raid_result = {
    "content": "",
    "embeds": [
        {
            "title": "🎯 레이드 정산",
            "description": f"레이드 보스의 체력 [{cur_dur}/{total_dur}]",
            "color": 0x00ff00,  # 초록색
            "fields": fields,
            "footer": {
                "text": "Raid Bot",
            }
        }
    ]
}

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

response = requests.post(WEBHOOK_URL, json=raid_result)

if response.status_code == 204:
    print("✅ 레이드 메시지 전송 성공!")
else:
    print(f"❌ 메시지 전송 실패! 상태 코드: {response.status_code}")
    
ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트")
users = ref.get()

if users:
    for nickname, data in users.items():
        mission_ref = db.reference(f"미션/미션진행상태")
        dice_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname}/")
        yacht_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname}/야추")
        daily_missions = mission_ref.get()

        all_users = mission_ref.get()  # 전체 사용자 데이터 불러오기

        if all_users:
            for nickname in all_users.keys():
                daily_mission_ref = mission_ref.child(f"{nickname}/일일미션")
                daily_mission_ref.delete()

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