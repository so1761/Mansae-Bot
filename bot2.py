import aiohttp
import asyncio
import discord
import firebase_admin
import random
import prediction_vote as p
import os
import math
from firebase_admin import credentials
from firebase_admin import db
from discord import Intents
from discord.ext import commands
from discord.ext import tasks
from discord.ui import View, Button, Select
from discord import Game
from discord import Status
from discord import Object
from datetime import datetime,timedelta
from dotenv import load_dotenv

TARGET_TEXT_CHANNEL_ID = 1289184218135396483
WARNING_CHANNEL_ID = 1314643507490590731
TOKEN = None
API_KEY = None

JIMO_NAME = '강지모'
JIMO_TAG = 'KR1'
JIMO_PUUID = None
JIMO_ID = None

MELON_NAME = 'Melon'
MELON_TAG = '0715'
MELON_PUUID = None
MELON_ID = None

SEASON_CHANGE_DATE = datetime(2024, 9, 11, 0, 0, 0)

TIER_RANK_MAP = {
    'IRON': 1,
    'BRONZE': 2,
    'SILVER': 3,
    'GOLD': 4,
    'PLATINUM': 5,
    'EMERALD' : 6,
    'DIAMOND': 7,
    'MASTER': 8,
    'GRANDMASTER': 9,
    'CHALLENGER': 10
}
TIER_RANK_MAP2 = {
    'I': 1,
    'B': 2,
    'S': 3,
    'G': 4,
    'P': 5,
    'E' : 6,
    'D': 7,
    'M': 8,
    'GM': 9,
    'C': 10
}
RANK_MAP = {
    'I': 3,
    'II': 2,
    'III': 1,
    'IV': 0
}

class NotFoundError(Exception):
    pass

#익명 이름
ANONYM_NAME_WIN = [
 '바바리원숭이','회색랑구르','알렌원숭이','코주부원숭이','황금들창코원숭이','안경원숭이','동부콜로부스','붉은잎원숭이','남부돼지꼬리원숭이'
]
ANONYM_NAME_LOSE = [
 '카카포','케아','카카리키','아프리카회색앵무','유황앵무','뉴기니아앵무', '빗창앵무','유리앵무'
]

CHANNEL_ID = '938728993329397781'
NOTICE_CHANNEL_ID = '1232585451911643187'
MISSION_CHANNEL_ID = '1339058849247793255'

used_items_for_user_jimo = {}
used_items_for_user_melon = {}

async def mission_notice(name, mission, rarity):
    channel = bot.get_channel(int(CHANNEL_ID))
    
    # 희귀도에 따라 임베드 색상과 제목 설정
    color_map = {
        "일반": discord.Color.light_gray(),
        "희귀": discord.Color.blue(),
        "에픽": discord.Color.purple(),
        "전설": discord.Color.gold(),
        "신화": discord.Color.dark_red(),
        "히든": discord.Color.from_rgb(100,198,209)
    }

    title_map = {
        "일반": "[일반] 미션 달성!",
        "희귀": "[희귀] 미션 달성!",
        "에픽": "[에픽] 미션 달성!",
        "전설": "[전설] 미션 달성!",
        "신화": "[신화] 미션 달성!",
        "히든": "[히든] 미션 달성!"
    }

    color = color_map.get(rarity, discord.Color.light_gray())  # 기본 색상은 light_gray
    title = title_map.get(rarity, "미션 달성!")

    # 임베드 메시지 구성
    userembed = discord.Embed(title=title, color=color)
    userembed.add_field(name="", value=f"{name}님이 [{mission}] 미션을 달성했습니다!", inline=False)
    
    # 메시지 보내기
    await channel.send(f"\n", embed=userembed)

class MissionView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CheckDailyMissionButton())
        self.add_item(CheckSeasonMissionButton())

class CheckDailyMissionButton(Button):
    def __init__(self):
        super().__init__(label="일일 미션", custom_id="daily_mission", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        user_name = interaction.user.name
        mission_data = get_mission_data(user_name, "일일미션")  # 유저별 미션 상태 불러오기

        embed = discord.Embed(title="📜 미션 목록", color=discord.Color.green())
        for mission in mission_data:
            status = "✅ 완료" if mission["completed"] else "❌ 미완료"
            embed.add_field(name=f"{mission['name']} ({mission['points']}p)", value=status, inline=False)

        # 완료한 미션만 선택할 수 있도록 View 생성
        completed_missions = [m for m in mission_data if m["completed"] and not m["reward_claimed"]]
        view = MissionRewardView(completed_missions,"일일미션")

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class CheckSeasonMissionButton(Button):
    def __init__(self):
        super().__init__(label="시즌 미션", custom_id="season_mission", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        user_name = interaction.user.name

        mission_data = get_mission_data(user_name, "시즌미션")  # 유저별 미션 상태 불러오기

        embed = discord.Embed(title="📜 미션 목록", color=discord.Color.green())
        for mission in mission_data:
            status = "✅ 완료" if mission["completed"] else "❌ 미완료"
            embed.add_field(name=f"{mission['name']} ({mission['points']}p)", value=status, inline=False)

        # 완료한 미션만 선택할 수 있도록 View 생성
        completed_missions = [m for m in mission_data if m["completed"] and not m["reward_claimed"]]
        view = MissionRewardView(completed_missions,"시즌미션")

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class MissionSelect(discord.ui.Select):
    def __init__(self, completed_missions, mission_type):
        self.mission_type = mission_type
        options = [
            discord.SelectOption(label=f"{mission['name']} ({mission['points']}p)", value=mission['name'])
            for mission in completed_missions
        ]
        super().__init__(
            placeholder="완료한 미션을 선택하세요!",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        selected_mission = self.values[0]  # 선택한 미션

        # self.view에서 reward_button을 가져와 미션 설정
        reward_button = next(
            (item for item in self.view.children if isinstance(item, MissionRewardButton)), 
            None
        )

        if reward_button:
            reward_button.mission_name = selected_mission  # 버튼에 미션 설정
            reward_button.mission_type = self.mission_type
            reward_button.update_label()  # 버튼 라벨 업데이트
            reward_button.disabled = False  # 버튼 활성화
        
        await interaction.response.edit_message(view=self.view)

class MissionRewardButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="🎁 보상 받기",
            style=discord.ButtonStyle.success,
            disabled=True,  # 기본적으로 비활성화
            custom_id="reward_button"
        )
        self.mission_name = None  # 선택한 미션 저장
        self.mission_type = None # 어떤 종류의 미션인지 저장
    
    async def callback(self, interaction: discord.Interaction):
        user_name = interaction.user.name
        if not self.mission_name:
            await interaction.response.send_message("먼저 미션을 선택하세요!", ephemeral=True)
            return
        
        if claim_reward(user_name, self.mission_name, self.mission_type):       
            # 버튼 비활성화
            self.disabled = True  
            await interaction.response.send_message(f"🎉 {self.mission_name} 보상을 받았습니다!", ephemeral=True)
            # `self.view`를 직접 설정하지 않고, interaction에서 가져옴
            view = self.view 
        else:
            await interaction.response.send_message("이미 보상을 받았습니다.", ephemeral=True)
    def update_label(self):
        if self.mission_name:
            self.label = f"🎁 [{self.mission_name}] 보상 받기"
        else:
            self.label = "🎁 보상 받기"

class MissionRewardAllButton(discord.ui.Button):
    def __init__(self,mission_type):
        super().__init__(
            label="🎁 보상 모두 받기",
            style=discord.ButtonStyle.primary,
            disabled=True,
            custom_id="reward_all_button"
        )
        self.mission_type = mission_type

    async def callback(self, interaction: discord.Interaction):
        user_name = interaction.user.name

        if claim_all_reward(user_name,self.mission_type):
            self.disabled = True
            await interaction.response.send_message(f"🎉 {self.mission_type} 보상을 모두 받았습니다!",ephemeral=True)
        else:
            await interaction.response.send_message("이미 보상을 받았습니다.",ephemeral=True)
    def update_status(self, completed):
        if completed:
            self.disabled = False

class MissionRewardView(discord.ui.View):
    def __init__(self, completed_missions,mission_type):
        super().__init__()
        self.selected_mission = None  # 선택한 미션
        self.reward_button = MissionRewardButton()  # 보상 버튼 추가
        self.all_reward_button = MissionRewardAllButton(mission_type) # 일괄 보상 버튼 추가
        # 미션 선택 드롭다운 추가 (완료한 미션이 있을 경우에만)
        if completed_missions:
            mission_select = MissionSelect(completed_missions,mission_type)
            self.add_item(mission_select)
            self.all_reward_button.update_status(True)
        self.add_item(self.reward_button)  # 보상 버튼 추가
        self.add_item(self.all_reward_button) # 보상 모두받기 버튼 추가

def get_mission_data(user_name, mission_type):
    """데이터베이스에서 미션 상태 불러오기"""
    cur_predict_seasonref = db.reference("승부예측/현재예측시즌")  # 현재 진행 중인 예측 시즌 가져오기
    current_predict_season = cur_predict_seasonref.get()

    ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{user_name}/미션/{mission_type}")
    mission_data = ref.get()
    
    if not mission_data:
        return []

    return [
        {"name": mission_name, "completed": mission["완료"], "reward_claimed": mission["보상수령"], "points": mission["포인트"]}
        for mission_name, mission in mission_data.items()
    ]

def claim_reward(user_name, mission_name, mission_type):
    """보상 지급 처리"""
    cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
    current_predict_season = cur_predict_seasonref.get()

    ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{user_name}/미션/{mission_type}")
    mission_data = ref.get()

    ref1 = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{user_name}/미션/{mission_type}/{mission_name}")
    mission_data1 = ref1.get()
    mission_point = mission_data1.get("포인트", 0)  # '포인트'가 없을 경우 기본값 0을 설정

    ref2 = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{user_name}")
    user_data = ref2.get()
    point = user_data.get("포인트", 0)  # '포인트'가 없을 경우 기본값 0을 설정
    ref2.update({"포인트" : point + mission_point})

    if mission_data and mission_name in mission_data and not mission_data[mission_name]["보상수령"]:
        ref.child(mission_name).update({"보상수령": True})
        return True
    
    return False

def claim_all_reward(user_name, mission_type):
    """보상 일괄 지급 처리"""
    cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
    current_predict_season = cur_predict_seasonref.get()

    ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{user_name}/미션/{mission_type}")
    user_missions = ref.get() or {}

    unrewarded_missions = []
    for mission_name, mission_data in user_missions.items():
        if not mission_data.get("보상수령",False) and mission_data.get("완료",False):
            unrewarded_missions.append(mission_name)

    for mission_name in unrewarded_missions:
        ref1 = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{user_name}/미션/{mission_type}/{mission_name}")
        mission_data1 = ref1.get()
        mission_point = mission_data1.get("포인트", 0)  # '포인트'가 없을 경우 기본값 0을 설정

        ref2 = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{user_name}")
        user_data = ref2.get()
        point = user_data.get("포인트", 0)  # '포인트'가 없을 경우 기본값 0을 설정
        ref2.update({"포인트" : point + mission_point})

        if user_missions and mission_name in user_missions and not user_missions[mission_name]["보상수령"]:
            ref.child(mission_name).update({"보상수령": True})
    
    if unrewarded_missions:
        return True
    else:
        return False

async def nowgame(puuid, retries=5, delay=5):
    url = f'https://kr.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}'
    headers = {'X-Riot-Token': API_KEY}

    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    if response.status == 200:
                        data = await response.json()
                        game_mode = data.get("gameMode")
                        game_type = data.get("gameType")
                        queue_id = data.get("gameQueueConfigId")

                        if game_mode == "CLASSIC" and game_type == "MATCHED":
                            if queue_id == 420:
                                return True, "솔로랭크"
                            elif queue_id == 440:
                                return True, "자유랭크"
                        
                        return False, None  # 랭크 게임이 아닐 경우

                    elif response.status == 404:
                        return False, None  # 현재 게임이 없으면 재시도할 필요 없음

                    elif response.status in [500, 502, 503, 504, 524]:  # 524 추가
                        print(f"[{now}] [WARNING] {response.status} Server error, retrying {attempt + 1}/{retries}...")

                    else:
                        print(f"[{now}] [ERROR] Riot API returned status {response.status} in nowgame")
                        return False, None  # 다른 오류는 재시도하지 않음

        except aiohttp.ClientConnectorError as e:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{now}] [ERROR] Connection error: {e}, retrying {attempt + 1}/{retries}...")
        except Exception as e:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{now}] [ERROR] Unexpected error in nowgame: {e}")
            return False, None

        await asyncio.sleep(delay)  # 재시도 간격 증가

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] [ERROR] nowgame All retries failed.")
    return False, None

async def get_summoner_puuid(riot_id, tagline):
    url = f'https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{riot_id}/{tagline}'
    headers = {'X-Riot-Token': API_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data['puuid']
            else:
                print('Error:', response.status)
                return None

async def get_summoner_id(puuid):
    url = f'https://kr.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}'
    headers = {'X-Riot-Token': API_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data['id']
            else:
                print('Error:', response.status)
                return None

async def get_summoner_ranks(summoner_id, type="솔랭", retries=5, delay=5):
    url = f'https://kr.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}'
    headers = {'X-Riot-Token': API_KEY}

    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    if response.status == 200:
                        data = await response.json()
                        if type == "솔랭":
                            filtered_data = [entry for entry in data if entry.get("queueType") == "RANKED_SOLO_5x5"]
                        elif type == "자랭":
                            filtered_data = [entry for entry in data if entry.get("queueType") == "RANKED_FLEX_SR"]
                        return filtered_data[0] if filtered_data else []

                    elif response.status == 404:
                        print(f"[{now}] [ERROR] 404 Not Found in get_summoner_ranks")
                        return None  # 소환사 정보가 없으면 재시도할 필요 없음

                    elif response.status in [500, 502, 503, 504, 524]:  
                        print(f"[{now}] [WARNING] {response.status} Server error, retrying {attempt + 1}/{retries}...")  
                    else:
                        print(f"[{now}] [ERROR] get_summoner_ranks Error: {response.status}")
                        return None  # 다른 오류는 재시도 없이 종료

        except aiohttp.ClientConnectorError as e:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{now}] [ERROR] Connection error: {e}, retrying {attempt + 1}/{retries}...")
        except aiohttp.ClientOSError as e:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{now}] [ERROR] Client OSError (Server disconnected): {e}, retrying {attempt + 1}/{retries}...")
        except Exception as e:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{now}] [ERROR] Unexpected error in get_summoner_ranks: {e}, retrying {attempt + 1}/{retries}...")

        await asyncio.sleep(delay)  # 재시도 간격

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("[{now}] [ERROR] get_summoner_ranks All retries failed.")
    return None

async def get_summoner_recentmatch_id(puuid, retries=5, delay=5):
    url = f'https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=1'
    headers = {'X-Riot-Token': API_KEY}

    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    if response.status == 200:
                        data = await response.json()
                        return data[0] if data else None

                    elif response.status == 404:
                        print(f"[{now}] [ERROR] 404 Not Found: No matches found for PUUID {puuid}")
                        return None  # PUUID가 잘못된 경우는 재시도할 필요 없음

                    elif response.status in [500, 502, 503, 504, 524]:
                        print(f"[{now}] [WARNING] {response.status} Server error, retrying {attempt + 1}/{retries}...")
                    else:
                        print(f"[{now}] [ERROR] Riot API returned status {response.status} in get_summoner_recentmatch_id")
                        return None

        except aiohttp.ClientConnectorError as e:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{now}] [ERROR] Connection error: {e}, retrying {attempt + 1}/{retries}...")
        except Exception as e:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{now}] [ERROR] Unexpected error in get_summoner_recentmatch_id: {e}")
            return None

        await asyncio.sleep(delay)  # 재시도 간격

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] [ERROR] get_summoner_recentmatch_id All retries failed.")
    return None

async def get_summoner_matchinfo(matchid, retries=5, delay=5):
    url = f'https://asia.api.riotgames.com/lol/match/v5/matches/{matchid}'
    headers = {'X-Riot-Token': API_KEY}

    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    if response.status == 200:
                        return await response.json()

                    elif response.status == 404:
                        print(f"[{now}] [ERROR] 404 Not Found: Match ID {matchid} not found.")
                        return None  # 매치 ID가 잘못된 경우는 재시도할 필요 없음

                    elif response.status == 400:
                        print(f"[{now}] [ERROR] 400 Bad Request: Invalid match ID {matchid}.")
                        return None  # 잘못된 요청이라면 재시도할 필요 없음

                    elif response.status in [500, 502, 503, 504, 524]:
                        print(f"[{now}] [WARNING] {response.status} Server error, retrying {attempt + 1}/{retries}...")
                    else:
                        print(f"[{now}] [ERROR] Riot API returned status {response.status} in get_summoner_matchinfo")
                        return None

        except aiohttp.ClientConnectorError as e:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{now}] [ERROR] Connection error: {e}, retrying {attempt + 1}/{retries}...")
        except Exception as e:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{now}] [ERROR] Unexpected error in get_summoner_matchinfo: {e}")
            return None

        await asyncio.sleep(delay)  # 재시도 간격

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] [ERROR] get_summoner_matchinfo All retries failed.")
    return None

async def refresh_prediction(name, anonym, complete_anonym, prediction_votes):
    if name == "지모":
        embed = discord.Embed(title="예측 현황", color=0x000000) # Black
    elif name == "Melon":
        embed = discord.Embed(title="예측 현황", color=discord.Color.brand_green())
    refrate = db.reference(f'승부예측/배율증가/{name}')
    rater = refrate.get()
    if rater['배율'] != 0:
        embed.add_field(name="", value=f"추가 배율 : {rater['배율']}", inline=False)
    if complete_anonym:
        win_predictions = "\n?명"
        lose_predictions = "\n?명"
    elif anonym:
        win_predictions = "\n".join(f"{ANONYM_NAME_WIN[index]}: ? 포인트" for index, user in enumerate(prediction_votes["win"])) or "없음"
        lose_predictions = "\n".join(f"{ANONYM_NAME_LOSE[index]}: ? 포인트" for index, user in enumerate(prediction_votes["lose"])) or "없음"
    else:
        win_predictions = "\n".join(f"{user['name'].display_name}: {user['points']}포인트" for user in prediction_votes["win"]) or "없음"
        lose_predictions = "\n".join(f"{user['name'].display_name}: {user['points']}포인트" for user in prediction_votes["lose"]) or "없음"
    
    winner_total_point = sum(winner["points"] for winner in prediction_votes["win"])
    loser_total_point = sum(loser["points"] for loser in prediction_votes["lose"])

    if complete_anonym: # 완전 익명일 경우
        embed.add_field(name="총 포인트", value=f"승리: ? 포인트 | 패배: ? 포인트", inline=False)
    else:
        embed.add_field(name="총 포인트", value=f"승리: {winner_total_point}포인트 | 패배: {loser_total_point}포인트", inline=False)
    
    embed.add_field(name="승리 예측", value=win_predictions, inline=True)
    embed.add_field(name="패배 예측", value=lose_predictions, inline=True)
        
    if name == "지모":
        await p.current_message_jimo.edit(embed=embed)
    elif name == "Melon":
        await p.current_message_melon.edit(embed=embed)

async def refresh_kda_prediction(name, anonym, kda_votes):
    refperfect = db.reference('승부예측/퍼펙트포인트')
    perfect_point = refperfect.get()[name]

    if name == "지모":
        embed = discord.Embed(title="KDA 예측 현황", color=0x000000) # Black
    elif name == "Melon":
        embed = discord.Embed(title="KDA 예측 현황", color=discord.Color.brand_green())
    today = datetime.today()
    if today.weekday() == 6:
        embed.add_field(name=f"",value=f"일요일엔 점수 2배! KDA 예측 점수 2배 지급!")
    embed.add_field(name="퍼펙트 예측성공 포인트", value=perfect_point, inline=False)
    if anonym:
        up_predictions = "".join(f"{len(kda_votes['up'])}명")
        down_predictions = "".join(f"{len(kda_votes['down'])}명")
        perfect_predictions = "".join(f"{len(kda_votes['perfect'])}명")

        embed.add_field(name="KDA 3 이상 예측", value=up_predictions, inline=False)
        embed.add_field(name="KDA 3 이하 예측", value=down_predictions, inline=False)
        embed.add_field(name="KDA 퍼펙트 예측", value=perfect_predictions, inline=False)
    else:
        up_predictions = "\n".join(f"{user['name'].display_name}" for user in kda_votes["up"]) or "없음"
        down_predictions = "\n".join(f"{user['name'].display_name}" for user in kda_votes["down"]) or "없음"
        perfect_predictions = "\n".join(f"{user['name'].display_name}" for user in kda_votes["perfect"]) or "없음"
    
        embed.add_field(name="KDA 3 이상 예측", value=up_predictions, inline=False)
        embed.add_field(name="KDA 3 이하 예측", value=down_predictions, inline=False)
        embed.add_field(name="KDA 퍼펙트 예측", value=perfect_predictions, inline=False)
    
    if name == "지모":
        await p.current_message_kda_jimo.edit(embed=embed)
    elif name == "Melon":
        await p.current_message_kda_melon.edit(embed=embed)

def tier_to_number(tier, rank, lp): # 티어를 레이팅 숫자로 변환
    tier_num = TIER_RANK_MAP.get(tier)
    rank_num = RANK_MAP.get(rank)
    if tier_num is None or rank_num is None:
        return None
    return tier_num * 400 + rank_num * 100 + lp

def get_lp_and_tier_difference(previous_rank, current_rank,rank_type,name): #이전 랭크와 현재 랭크를 받아 차이를 계산하여 메세지 반환(승급/강등)

    # 티어 변화 확인
    tier_change = False
    if current_rank["tier"] != previous_rank["tier"]:
        tier_change = True

    # 현재 LP와 이전 LP의 차이 계산
    prev_tier_num = TIER_RANK_MAP.get(previous_rank["tier"])
    current_tier_num = TIER_RANK_MAP.get(current_rank["tier"])
    prev_rank_num = RANK_MAP.get(previous_rank["rank"])
    current_rank_num = RANK_MAP.get(current_rank["rank"])
    lp_difference = (current_tier_num * 400 + current_rank_num * 100 + current_rank["leaguePoints"]) - (prev_tier_num * 400 + prev_rank_num * 100 + previous_rank["leaguePoints"])
    save_lp_difference_to_file(lp_difference,current_rank,rank_type,name)
    # 티어가 바뀌었을 경우
    if tier_change:
        prev_tier_num = TIER_RANK_MAP.get(previous_rank["tier"])
        current_tier_num = TIER_RANK_MAP.get(current_rank["tier"])
        if prev_tier_num and current_tier_num:
                    if current_tier_num > prev_tier_num:
                        if name == "지모":
                            return f"@here\n{name}가 {current_rank['tier']}(으)로 승급하였습니다!:partying_face:"
                        else:
                            return f"@here\n{name}이 {current_rank['tier']}(으)로 승급하였습니다!:partying_face:"
                    elif current_tier_num < prev_tier_num:
                        if name == "지모":
                            return f"{name}가 {current_rank['tier']}(으)로 강등되었습니다."
                        else:
                            return f"{name}이 {current_rank['tier']}(으)로 강등되었습니다."
                    else:
                        return "티어 변동이 없습니다."
    else:
        # 티어는 동일하고 LP만 변화한 경우
        if lp_difference > 0:
            return f"승리!\n{current_rank['tier']} {current_rank['rank']} {current_rank['leaguePoints']}P (+{lp_difference}P)"
        elif lp_difference < 0:
            return f"패배..\n{current_rank['tier']} {current_rank['rank']} {current_rank['leaguePoints']}P (-{-lp_difference}P)"
        else:
            return f"패배..\n{current_rank['tier']} {current_rank['rank']} {current_rank['leaguePoints']}P (-0P)"

def save_lp_difference_to_file(lp_difference,current_rank,rank_type,name): #지모의 점수 변화량과 날짜를 파이어베이수에 저장
    # 현재 날짜 가져오기
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rank_num = tier_to_number(current_rank["tier"],current_rank["rank"],current_rank["leaguePoints"])

    # 현재 날짜 및 시간 가져오기
    current_datetime = datetime.now()

    # 날짜만 추출하여 저장
    current_date = current_datetime.strftime("%Y-%m-%d")

    # 시간만 추출하여 저장
    current_time = current_datetime.strftime("%H:%M:%S")

    curseasonref = db.reference("전적분석/현재시즌")
    current_season = curseasonref.get()

    refprev = db.reference(f'전적분석/{current_season}/점수변동/{name}/{rank_type}')
    points = refprev.get()

    if points is None:
        win_streak = 0
        lose_streak = 0
    else:
        # 가장 최근의 날짜를 찾음
        latest_date = max(points.keys())

        # 해당 날짜의 시간들을 정렬하여 가장 최근의 시간을 찾음
        latest_time = max(points[latest_date].keys(), key=lambda t: datetime.strptime(t, '%H:%M:%S'))

        # 가장 최근의 데이터
        latest_data = points[latest_date][latest_time]

        win_streak = latest_data["연승"]
        lose_streak = latest_data["연패"]
    if lp_difference <= 0:
        result = 0
    else:
        result = 1

    if result:
        win_streak += 1
        lose_streak = 0
    else:
        win_streak = 0
        lose_streak += 1

    # 파이어베이스에 저장
    ref = db.reference(f'전적분석/{current_season}/점수변동/{name}/{rank_type}/{current_date}/{current_time}')
    ref.update({'LP 변화량' : lp_difference})
    ref.update({'현재 점수' : rank_num})
    ref.update({"연승": win_streak})
    ref.update({"연패": lose_streak})

def get_participant_id(match_info, puuid): # match정보와 puuid를 통해 그 판에서 플레이어의 위치를 반환
    for i, participant in enumerate(match_info['info']['participants']):
        if participant['puuid'] == puuid:
            return i
    return None

def calculate_bonus(streak):
    bonus = 0
    
    if streak >= 1:
        bonus += min(2, streak) * 0.2  # 1~2연승 보너스
    if streak >= 3:
        bonus += min(2, streak - 2) * 0.3  # 3~4연승 보너스
    if streak >= 5:
        bonus += min(5, streak - 4) * 0.4  # 5~9연승 보너스
    if streak >= 10:
        bonus += (streak - 9) * 0.5  # 10연승 이상부터 0.5배씩 추가
    
    return round(bonus,1)

def calculate_points(streak):
    points = 0
    
    if streak >= 1:
        points += min(2, streak) * 2  # 1~2연승 보너스
    if streak >= 3:
        points += min(2, streak - 2) * 5  # 3~4연승 보너스
    if streak >= 5:
        points += min(5, streak - 4) * 8  # 5~9연승 보너스
    if streak >= 10:
        points += (streak - 9) * 10  # 10연승 이상부터 10점씩 추가
    
    return points

async def check_points(puuid, summoner_id, name, channel_id, notice_channel_id, votes, event):
    await bot.wait_until_ready()
    channel = bot.get_channel(int(channel_id)) # 일반 채널
    notice_channel = bot.get_channel(int(notice_channel_id)) # 공지 채널
    
    prediction_votes = votes["prediction"]
    kda_votes = votes["kda"]
    try:
        last_rank_solo = await get_summoner_ranks(summoner_id, "솔랭")
        last_rank_flex = await get_summoner_ranks(summoner_id, "자랭")
        if not last_rank_solo:
            last_total_match_solo = 0
        else:
            last_win_solo = last_rank_solo['wins']
            last_loss_solo = last_rank_solo['losses']
            last_total_match_solo = last_win_solo + last_loss_solo
        
        if not last_rank_flex:
            last_total_match_flex = 0
        else:
            last_win_flex = last_rank_flex['wins']
            last_loss_flex = last_rank_flex['losses']
            last_total_match_flex = last_win_flex + last_loss_flex

    except NotFoundError:
        last_total_match_solo = 0
        last_total_match_flex = 0

    cur_predict_seasonref = db.reference("승부예측/현재예측시즌") # 현재 진행중인 예측 시즌을 가져옴
    current_predict_season = cur_predict_seasonref.get()

    while not bot.is_closed():
        try:
            current_rank_solo = await get_summoner_ranks(summoner_id, "솔랭")
            current_rank_flex = await get_summoner_ranks(summoner_id, "자랭")
        except Exception as e:
            print(f"Error in check_points: {e}")
            current_rank_solo = None
            current_rank_flex = None


        if not current_rank_solo:
            current_total_match_solo = 0
        else:
            current_win_solo = current_rank_solo['wins']
            current_loss_solo = current_rank_solo['losses']
            current_total_match_solo = current_win_solo + current_loss_solo
        
        if not current_rank_flex:
            current_total_match_flex = 0
        else:
            current_win_flex = current_rank_flex['wins']
            current_loss_flex = current_rank_flex['losses']
            current_total_match_flex = current_win_flex + current_loss_flex


        if current_total_match_solo != last_total_match_solo or current_total_match_flex != last_total_match_flex:
            if current_total_match_solo != last_total_match_solo:
                print(f"{name}의 {current_total_match_solo}번째 솔로랭크 게임 완료")
                string_solo = get_lp_and_tier_difference(last_rank_solo, current_rank_solo,"솔로랭크",name)
                await notice_channel.send(f"\n{name}의 솔로랭크 점수 변동이 감지되었습니다!\n{string_solo}")
                await channel.send(f"\n{name}의 솔로랭크 점수 변동이 감지되었습니다!\n{string_solo}")
                last_rank_solo = current_rank_solo
                last_total_match_solo = current_total_match_solo
                rank_type = "솔로랭크"
            
            if current_total_match_flex != last_total_match_flex:
                print(f"{name}의 {current_total_match_solo}번째 자유랭크 게임 완료")
                string_flex = get_lp_and_tier_difference(last_rank_flex, current_rank_flex,"자유랭크",name)
                await notice_channel.send(f"\n{name}의 자유랭크 점수 변동이 감지되었습니다!\n{string_flex}")
                await channel.send(f"\n{name}의 자유랭크 점수 변동이 감지되었습니다!\n{string_flex}")
                last_rank_flex = current_rank_flex
                last_total_match_flex = current_total_match_flex
                rank_type = "자유랭크"

            onoffref = db.reference("승부예측/투표온오프") # 투표가 off 되어있을 경우 결과 출력 X
            onoffbool = onoffref.get()
            if not onoffbool:
                await refresh_prediction(name,False,prediction_votes) # 베팅내역 공개
                await refresh_kda_prediction(name,False,kda_votes) # KDA 예측내역 공개

                complete_anonymref = db.reference("승부예측/완전익명온오프")
                complete_anonymref.set(False) # 완전 익명 해제
                
                curseasonref = db.reference("전적분석/현재시즌")
                current_season = curseasonref.get()

                current_datetime = datetime.now() # 데이터베이스에 남길 현재 시각 기록
                current_date = current_datetime.strftime("%Y-%m-%d")
                current_time = current_datetime.strftime("%H:%M:%S")

                ref = db.reference(f'전적분석/{current_season}/점수변동/{name}/{rank_type}')
                points = ref.get()

                point_change = 0
                if points is None:
                    game_win_streak = 0
                    game_lose_streak = 0
                    result = True
                else:
                     # 날짜 정렬
                    sorted_dates = sorted(points.keys(), key=lambda d: datetime.strptime(d, '%Y-%m-%d'))

                    # 가장 최근 날짜 가져오기
                    latest_date = sorted_dates[-1]
                    latest_times = sorted(points[latest_date].keys(), key=lambda t: datetime.strptime(t, '%H:%M:%S'))

                    if len(latest_times) > 1:
                        # 같은 날짜에 여러 게임이 있는 경우, 가장 최근 경기의 "바로 전 경기" 선택
                        previous_time = latest_times[-2]
                        latest_time = latest_times[-1]
                    else:
                        # 가장 최근 날짜에 한 판만 있었다면, 이전 날짜로 넘어감
                        if len(sorted_dates) > 1:
                            previous_date = sorted_dates[-2]
                            previous_times = sorted(points[previous_date].keys(), key=lambda t: datetime.strptime(t, '%H:%M:%S'))
                            previous_time = previous_times[-1]  # 이전 날짜에서 가장 늦은 경기
                            latest_time = latest_times[-1]
                        else:
                            # 데이터가 한 판밖에 없는 경우 (첫 경기), 연승/연패 초기화
                            game_win_streak = 0
                            game_lose_streak = 0
                            latest_time = latest_times[-1]
                            previous_time = None

                    # 최신 경기 데이터
                    latest_data = points[latest_date][latest_time]
                    point_change = latest_data['LP 변화량']
                    result = point_change > 0  # 승리 여부 판단

                    if previous_time:
                        # "바로 전 경기" 데이터 가져오기
                        if previous_time in points[latest_date]:  # 같은 날짜에서 찾은 경우
                            previous_data = points[latest_date][previous_time]
                        else:  # 이전 날짜에서 가져온 경우
                            previous_data = points[previous_date][previous_time]

                        # "바로 전 경기"의 연승/연패 기록 사용
                        game_win_streak = previous_data["연승"]
                        game_lose_streak = previous_data["연패"]
                    else:
                        # 첫 경기라면 연승/연패 초기화
                        game_win_streak = 0
                        game_lose_streak = 0

                if result:
                    userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                else:
                    userembed = discord.Embed(title="메세지", color=discord.Color.red())
                
    
                userembed.add_field(name="게임 종료", value=f"{name}의 {rank_type} 게임이 종료되었습니다!\n{'승리!' if result else '패배..'}\n점수변동: {point_change}")

                winners = prediction_votes['win'] if result else prediction_votes['lose']
                losers = prediction_votes['lose'] if result else prediction_votes['win']
                winnerNum = len(winners)
                loserNum = len(losers)

                streak_bonus_rate = calculate_bonus(game_lose_streak if result else game_win_streak)

                refrate = db.reference(f'승부예측/배율증가/{name}')
                rater = refrate.get()
                
                BonusRate = 0 if winnerNum == 0 else round((((winnerNum + loserNum) / winnerNum) - 1) * 0.5, 2) + 1 # 0.5배 배율 적용
                if BonusRate > 0:
                    BonusRate += rater.get('배율',0)
                    BonusRate += round(streak_bonus_rate + 0.1,2)

                winner_total_point = sum(winner['points'] for winner in winners)
                loser_total_point = sum(loser['points'] for loser in losers)
                remain_loser_total_point = loser_total_point
                
                bonus_parts = []

                if streak_bonus_rate:
                    bonus_parts.append(f"+ 역배 배율 {streak_bonus_rate}")
                if rater.get("배율",0):
                    bonus_parts.append(f"+ 아이템 추가 배율 {rater['배율']}")

                bonus_string = "".join(bonus_parts)  # 둘 다 있으면 "역배 배율 X + 아이템 추가 배율 Y" 형태
                bonus_string += " + 0.1"

                
                BonusRate = round(BonusRate, 2)
                if BonusRate <= 1.1:
                    BonusRate = 1.1

                userembed.add_field(
                    name="", 
                    value=f"베팅 배율: {BonusRate}배" if BonusRate == 0 else 
                    f"베팅 배율: {BonusRate}배!((({winnerNum + loserNum}/{winnerNum} - 1) x 0.5 + 1) {bonus_string})", 
                    inline=False
                )

                for winner in winners:
                    point_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner['name'].name}")
                    predict_data = point_ref.get()
                    point = predict_data.get("포인트",0)
                    bettingPoint = predict_data.get("베팅포인트",0)

                    prediction_value = "승리" if result else "패배"
                    prediction_opposite_value = "패배" if result else "승리"
                    # 예측 내역 변동 데이터
                    change_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트변동로그/{current_date}/{current_time}/{winner['name'].name}")
                    change_ref.update({
                        "포인트": point,
                        "총 예측 횟수": predict_data.get("총 예측 횟수",0) + 1,
                        "적중 횟수": predict_data.get("적중 횟수",0) + 1,
                        "적중률": f"{round((((predict_data.get('적중 횟수',0) + 1) * 100) / (predict_data.get('총 예측 횟수') + 1)), 2)}%",
                        "연승": predict_data.get("연승") + 1,
                        "연패": 0,
                        "베팅포인트": bettingPoint - winner["points"],
                        
                        # 추가 데이터
                        f"{name}적중": predict_data.get(f"{name}적중", 0) + 1,
                        f"{name}{prediction_value}예측": predict_data.get(f"{name}{prediction_value}예측", 0) + 1,
                        f"{prediction_value}예측연속": predict_data.get(f"{prediction_value}예측연속", 0) + 1,
                        f"{prediction_opposite_value}예측연속": 0
                    })
                    # 예측 내역 업데이트
                    point_ref.update({
                        "포인트": point,
                        "총 예측 횟수": predict_data.get("총 예측 횟수",0) + 1,
                        "적중 횟수": predict_data.get("적중 횟수",0) + 1,
                        "적중률": f"{round((((predict_data.get('적중 횟수',0) + 1) * 100) / (predict_data.get('총 예측 횟수',0) + 1)), 2)}%",
                        "연승": predict_data.get("연승",0) + 1,
                        "연패": 0,
                        "베팅포인트": bettingPoint - winner["points"],
                        
                        # 추가 데이터
                        f"{name}적중": predict_data.get(f"{name}적중", 0) + 1,
                        f"{name}{prediction_value}예측": predict_data.get(f"{name}{prediction_value}예측", 0) + 1,
                        f"{prediction_value}예측연속": predict_data.get(f"{prediction_value}예측연속", 0) + 1,
                        f"{prediction_opposite_value}예측연속": 0
                    })
                    
                    if winner['points'] == 2669:
                        # ====================  [미션]  ====================
                        # 시즌미션 : 금지된 숫자
                        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                        current_predict_season = cur_predict_seasonref.get()
                        ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner['name'].name}/미션/시즌미션/금지된 숫자")

                        mission_data = ref.get()
                        mission_bool = mission_data.get('완료',False)
                        if not mission_bool:
                            ref.update({"완료": True})
                            print(f"{winner['name'].display_name}의 [금지된 숫자] 미션 완료")
                            await mission_notice(winner['name'].display_name,"금지된 숫자","에픽")

                        # ====================  [미션]  ====================

                    # ====================  [미션]  ====================
                    # 시즌미션 : 깜잘알
                    if name == "지모" and predict_data["지모적중"] + 1 == 50:
                        ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner['name'].name}/미션/시즌미션/깜잘알")
                        mission_data = ref.get()
                        mission_bool = mission_data.get('완료',False)
                        if not mission_bool:
                            ref.update({"완료": True})
                            print(f"{winner['name'].display_name}의 [깜잘알] 미션 완료")
                            await mission_notice(winner['name'].display_name,"깜잘알","전설")
                    # ====================  [미션]  ====================

                    # ====================  [미션]  ====================
                    # 시즌미션 : 난 이기는 판만 걸어
                    point_ref_mission = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner['name'].name}")
                    predict_data_mission = point_ref_mission.get()

                    if predict_data_mission.get("승리예측연속", 0) >= 5 and predict_data_mission.get("연승", 0) >= 5:
                        ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner['name'].name}/미션/시즌미션/난 이기는 판만 걸어")
                        mission_data = ref.get()
                        mission_bool = mission_data.get('완료',False)
                        if not mission_bool:
                            ref.update({"완료": True})
                            print(f"{winner['name'].display_name}의 [난 이기는 판만 걸어] 미션 완료")
                            await mission_notice(winner['name'].display_name,"난 이기는 판만 걸어","전설")
                    # ====================  [미션]  ====================

                    # ====================  [미션]  ====================
                    # 시즌미션 : 쿵쿵따
                    if predict_data.get("연패", 0) == 2: # 2연패 였다면
                        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                        current_predict_season = cur_predict_seasonref.get()
                        ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner['name'].name}/미션/시즌미션/쿵쿵따")
                        mission_data = ref.get()
                        mission_bool = mission_data.get('완료',False)
                        if not mission_bool:
                            ref.update({"완료": True})
                            print(f"{winner['name'].display_name}의 [쿵쿵따] 미션 완료")
                            await mission_notice(winner['name'].display_name,"쿵쿵따","일반")

                    # ====================  [미션]  ====================

                    # ====================  [미션]  ====================
                    # 일일미션 : 승부예측 1회 적중
                    cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                    current_predict_season = cur_predict_seasonref.get()
                    ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner['name'].name}/미션/일일미션/승부예측 1회 적중")
                    mission_data = ref.get()
                    mission_bool = mission_data.get('완료',False)
                    if not mission_bool:
                        ref.update({"완료": True})
                        print(f"{winner['name'].display_name}의 [승부예측 1회 적중] 미션 완료")

                    # ====================  [미션]  ====================

                    betted_rate = round(winner['points'] / winner_total_point, 3) if winner_total_point else 0
                    get_bet = round(betted_rate * loser_total_point)
                    get_bet_limit = round(BonusRate * winner['points'])
                    if get_bet >= get_bet_limit:
                        get_bet = get_bet_limit

                    remain_loser_total_point -= get_bet
                    
                    win_streak = predict_data.get('연승', 0) + 1
                    streak_text = f"{win_streak}연속 적중을 이루어내며 " if win_streak > 1 else ""
                    if result:
                        add_points = point_change + (calculate_points(win_streak)) + round(winner['points'] * BonusRate) + get_bet if win_streak > 1 else point_change + round(winner["points"] * BonusRate) + get_bet
                    else:
                        add_points = -point_change + (calculate_points(win_streak)) + round(winner['points'] * BonusRate) + get_bet if win_streak > 1 else -point_change + round(winner["points"] * BonusRate) + get_bet
                    if win_streak > 1:
                        userembed.add_field(name="", value=f"{winner['name'].display_name}님이 {streak_text}{add_points}(베팅 보너스 + {round(winner['points'] * BonusRate)} + {get_bet})(연속적중 보너스 + {calculate_points(win_streak)}) 점수를 획득하셨습니다! (베팅 포인트: {winner['points']})", inline=False)
                    else:
                        userembed.add_field(name="", value=f"{winner['name'].display_name}님이 {streak_text}{add_points}(베팅 보너스 + {round(winner['points'] * BonusRate)} + {get_bet}) 점수를 획득하셨습니다! (베팅 포인트: {winner['points']})", inline=False)   
                    change_ref.update({"포인트": point + add_points - winner['points']})
                    point_ref.update({"포인트": point + add_points - winner['points']})
                for loser in losers:
                    point_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{loser['name'].name}")
                    predict_data = point_ref.get()
                    point = predict_data.get("포인트",0)
                    bettingPoint = predict_data.get("베팅포인트",0)
                    
                    prediction_value = "패배" if result else "승리"
                    prediction_opposite_value = "승리" if result else "패배"
                    # 예측 내역 변동 데이터
                    change_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트변동로그/{current_date}/{current_time}/{loser['name'].name}")
                    change_ref.update({
                        "포인트": point,
                        "총 예측 횟수": predict_data.get("총 예측 횟수",0) + 1,
                        "적중 횟수": predict_data.get("적중 횟수",0),
                        "적중률": f"{round((((predict_data.get('적중 횟수')) * 100) / (predict_data.get('총 예측 횟수',0) + 1)), 2)}%",
                        "연승": 0,
                        "연패": predict_data.get("연패",0) + 1,
                        "베팅포인트": bettingPoint - loser["points"],

                        # 추가 데이터
                        f"{name}{prediction_value}예측": predict_data.get(f"{name}{prediction_value}예측", 0) + 1,
                        f"{prediction_value}예측연속": predict_data.get(f"{prediction_value}예측연속", 0) + 1,
                        f"{prediction_opposite_value}예측연속": 0
                    })
                    # 예측 내역 업데이트
                    point_ref.update({
                        "포인트": point,
                        "총 예측 횟수": predict_data.get("총 예측 횟수",0) + 1,
                        "적중 횟수": predict_data.get("적중 횟수",0),
                        "적중률": f"{round((((predict_data.get('적중 횟수')) * 100) / (predict_data.get('총 예측 횟수',0) + 1)), 2)}%",
                        "연승": 0,
                        "연패": predict_data.get("연패",0) + 1,
                        "베팅포인트": bettingPoint - loser["points"],

                        # 추가 데이터
                        f"{name}{prediction_value}예측": predict_data.get(f"{name}{prediction_value}예측", 0) + 1,
                        f"{prediction_value}예측연속": predict_data.get(f"{prediction_value}예측연속", 0) + 1,
                        f"{prediction_opposite_value}예측연속": 0
                    })

                    # ====================  [미션]  ====================
                    # 시즌미션 : 마이너스의 손
                    if predict_data.get("연패",0) + 1 == 10:
                        ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{loser['name'].name}/미션/시즌미션/마이너스의 손")
                        mission_data = ref.get()
                        mission_bool = mission_data.get('완료',False)
                        if not mission_bool:
                            ref.update({"완료": True})
                            print(f"{loser['name'].display_name}의 [마이너스의 손] 미션 완료")
                            await mission_notice(loser['name'].display_name,"마이너스의 손","신화")
                    # ====================  [미션]  ====================
                    
                    # 남은 포인트를 배팅한 비율에 따라 환급받음 (50%)
                    betted_rate = round(loser['points'] / loser_total_point, 3) if loser_total_point else 0
                    get_bet = round(betted_rate * remain_loser_total_point * 0.5)
                    userembed.add_field(
                        name="",
                        value=f"{loser['name'].display_name}님이 예측에 실패하였습니다! " if loser['points'] == 0 else 
                        f"{loser['name'].display_name}님이 예측에 실패하여 베팅포인트를 잃었습니다! (베팅 포인트:-{loser['points']}) (환급 포인트: {get_bet})",
                        inline=False
                    )

                    if point + get_bet < loser['points']:
                        point_ref.update({"포인트": 0})
                        change_ref.update({"포인트": 0})
                    else:
                        point_ref.update({"포인트": point + get_bet - loser['points']})
                        change_ref.update({"포인트": point + get_bet - loser['points']})

                    after_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{loser['name'].name}")
                    after_predict_data = after_ref.get()
                    after_point = after_predict_data.get("포인트", 0)
                    if round(point * 0.2, 2) >= after_point and round(point * 0.8, 2) >= 1000: # 80% 이상 잃었을 경우 & 1000포인트 이상 잃었을 경우
                    # ====================  [미션]  ====================
                    # 시즌미션 : 이카루스의 추락
                        ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{loser['name'].name}/미션/시즌미션/이카루스의 추락")
                        mission_data = ref.get()
                        mission_bool = mission_data.get('완료',False)
                        if not mission_bool:
                            ref.update({"완료": True})
                            print(f"{loser['name'].display_name}의 [이카루스의 추락] 미션 완료")
                            await mission_notice(loser['name'].display_name,"이카루스의 추락","에픽")
                    # ====================  [미션]  ====================

                await channel.send(embed=userembed)
                if name == "지모":
                    used_items_for_user_jimo.clear()
                elif name == "Melon":
                    used_items_for_user_melon.clear()
                refrate.update({'배율' : 0}) # 배율 0으로 초기화

                # ====================  [미션]  ====================
                # 시즌미션 : 다중 그림자분신술
                cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                current_predict_season = cur_predict_seasonref.get()
                for better in prediction_votes['win'] + prediction_votes['lose']:
                    shadow_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{better['name'].name}/미션/시즌미션/다중 그림자분신술")
                    shadow_ref.update({f"{name}베팅" : 0})

                # ====================  [미션]  ====================

                # KDA 예측
                match_id = await get_summoner_recentmatch_id(puuid)
                match_info = await get_summoner_matchinfo(match_id)

                for player in match_info['info']['participants']:
                    if puuid == player['puuid']:
                        kda = 999 if player['deaths'] == 0 else round((player['kills'] + player['assists']) / player['deaths'], 1)

                        if kda == 999:
                            kdaembed = discord.Embed(title=f"{name} KDA 예측 결과", color=discord.Color.gold())
                        elif kda == 3:
                            kdaembed = discord.Embed(title=f"{name} KDA 예측 결과", color=discord.Color.purple())
                        elif kda > 3:
                            kdaembed = discord.Embed(title=f"{name} KDA 예측 결과", color=discord.Color.blue())
                        elif kda < 3:
                            kdaembed = discord.Embed(title=f"{name} KDA 예측 결과", color=discord.Color.red())

                        kdaembed.add_field(name=f"{name}의 KDA", value=f"{player['championName']} {player['kills']}/{player['deaths']}/{player['assists']}({'PERFECT' if kda == 999 else kda})", inline=False)
                        
                        
                        
                        # ====================  [미션]  ====================
                        # 시즌미션 : 졌지만 이겼다

                        if not result and kda == 999: # 패배 & 퍼펙트
                            cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                            current_predict_season = cur_predict_seasonref.get()
                            common_members = set(prediction_votes.get('lose', {}).keys()) & set(kda_votes.get('perfect', {}).keys())
                            for member in common_members:
                                ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{member['name'].name}/미션/시즌미션/졌지만 이겼다")
                                mission_data = ref.get() or {}  # None 방지
                                mission_bool = mission_data.get("완료", False)
                                if not mission_bool:
                                    ref.update({"완료": True})
                                    print(f"{member['name'].display_name}의 [졌지만 이겼다] 미션 완료")
                                    await mission_notice(member['name'].display_name,"졌지만 이겼다","전설")

                        # ====================  [미션]  ====================

                        # ====================  [미션]  ====================
                        # 시즌미션 : 이럴 줄 알았어

                        if not result and player['deaths'] >= 10: # 패배 & 10데스 이상
                            cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                            current_predict_season = cur_predict_seasonref.get()
                            for member in prediction_votes['lose']:
                                ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{member['name'].name}/미션/시즌미션/이럴 줄 알았어")
                                mission_data = ref.get() or {}  # None 방지
                                mission_bool = mission_data.get("완료", False)
                                if not mission_bool:
                                    ref.update({"완료": True})
                                    print(f"{member['name'].display_name}의 [이럴 줄 알았어] 미션 완료")
                                    await mission_notice(member['name'].display_name,"이럴 줄 알았어","일반")

                        # ====================  [미션]  ====================

                        refperfect = db.reference('승부예측/퍼펙트포인트')
                        perfect_point = refperfect.get()[name]

                        if kda > 3:
                            perfect_winners = kda_votes['perfect'] if kda == 999 else []
                            winners = kda_votes['up']
                            losers = kda_votes['down'] + (kda_votes['perfect'] if kda != 999 else [])
                            for perfect_winner in perfect_winners:
                                perfecter_num = len(perfect_winners)
                                point_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{perfect_winner['name'].name}")
                                predict_data = point_ref.get()
                                today = datetime.today()
                                if today.weekday() == 6:
                                    point_ref.update({"포인트": predict_data["포인트"] + round((perfect_point * 2) / perfecter_num)})
                                    kdaembed.add_field(name="", value=f"{perfect_winner['name'].display_name}님이 KDA 퍼펙트 예측에 성공하여 {round(((perfect_point * 2) / perfecter_num))}점(({perfect_point} / {perfecter_num}) x 2)을 획득하셨습니다!", inline=False)
                                else:
                                    point_ref.update({"포인트": predict_data["포인트"] + round(perfect_point / perfecter_num)})
                                    kdaembed.add_field(name="", value=f"{perfect_winner['name'].display_name}님이 KDA 퍼펙트 예측에 성공하여 {round(((perfect_point) / perfecter_num))}점({perfect_point} / {perfecter_num})점을 획득하셨습니다!", inline=False)

                            for winner in winners:
                                point_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner['name'].name}")
                                predict_data = point_ref.get()
                                today = datetime.today()
                                if today.weekday() == 6:
                                    point_ref.update({"포인트": predict_data["포인트"] + 40})
                                    kdaembed.add_field(name="", value=f"{winner['name'].display_name}님이 KDA 예측에 성공하여 40점(x2)을 획득하셨습니다!", inline=False)
                                else:
                                    point_ref.update({"포인트": predict_data["포인트"] + 20})
                                    kdaembed.add_field(name="", value=f"{winner['name'].display_name}님이 KDA 예측에 성공하여 20점을 획득하셨습니다!", inline=False)
                            for loser in losers:
                                kdaembed.add_field(name="", value=f"{loser['name'].display_name}님이 KDA 예측에 실패했습니다!", inline=False)
                        elif kda == 3:
                            winners = kda_votes['up'] + kda_votes['down']
                            losers = kda_votes['perfect']

                            for winner in winners:
                                point_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner['name'].name}")
                                predict_data = point_ref.get()
                                today = datetime.today()
                                if today.weekday() == 6:
                                    point_ref.update({"포인트": predict_data["포인트"] + 40})
                                    kdaembed.add_field(name="", value=f"{winner['name'].display_name}님이 KDA 예측에 성공하여 40점(x2)을 획득하셨습니다!", inline=False)
                                else:
                                    point_ref.update({"포인트": predict_data["포인트"] + 20})
                                    kdaembed.add_field(name="", value=f"{winner['name'].display_name}님이 KDA 예측에 성공하여 20점을 획득하셨습니다!", inline=False)
                            for loser in losers:
                                kdaembed.add_field(name="", value=f"{loser['name'].display_name}님이 KDA 예측에 실패했습니다!", inline=False)
                        else:
                            winners = kda_votes['down']
                            losers = kda_votes['up'] + kda_votes['perfect']
                            for winner in winners:
                                point_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner['name'].name}")
                                predict_data = point_ref.get()
                                today = datetime.today()
                                if today.weekday() == 6:
                                    point_ref.update({"포인트": predict_data["포인트"] + 40})
                                    kdaembed.add_field(name="", value=f"{winner['name'].display_name}님이 KDA 예측에 성공하여 40점(x2)을 획득하셨습니다!", inline=False)
                                else:
                                    point_ref.update({"포인트": predict_data["포인트"] + 20})
                                    kdaembed.add_field(name="", value=f"{winner['name'].display_name}님이 KDA 예측에 성공하여 20점을 획득하셨습니다!", inline=False)
                            for loser in losers:
                                kdaembed.add_field(name="", value=f"{loser['name'].display_name}님이 KDA 예측에 실패했습니다!", inline=False)

                        await channel.send(embed=kdaembed)
                        
                        penta_kills = player.get("pentakills", 0)
                        if penta_kills:
                            pentaembed = discord.Embed(title=f"펜타킬 달성!", color=discord.Color.gold())
                            pentaembed.add_field(name="펜타킬 달성 횟수", value=f"{penta_kills}회", inline = False)
                            for player in kda_votes['down'] + kda_votes['up'] + kda_votes['perfect']:
                                point_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{player['name'].name}")
                                predict_data = point_ref.get() 
                                pentaembed.add_field(name="", value=f"{player['name'].display_name}님이 {name}의 펜타킬 달성으로 {penta_kills * 1000}포인트를 얻었습니다!", inline = False)
                                point_ref.update({"포인트": predict_data["포인트"] + penta_kills * 1000})
                            await channel.send(embed=pentaembed)

                        refperfect.update({name: perfect_point + 5 if kda != 999 else 500})
                        kda_votes['up'].clear()
                        kda_votes['down'].clear()
                        kda_votes['perfect'].clear()
                        prediction_votes['win'].clear()
                        prediction_votes['lose'].clear()

                        event.set()

        await asyncio.sleep(20)

async def open_prediction(name, puuid, votes, channel_id, notice_channel_id, event, current_game_state, winbutton):
    await bot.wait_until_ready()
    channel = bot.get_channel(int(channel_id))
    notice_channel = bot.get_channel(int(notice_channel_id))

    cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
    current_predict_season = cur_predict_seasonref.get()

    while not bot.is_closed():
        #current_game_state, current_game_type = await nowgame(puuid)
        current_game_state = True
        current_game_type = "솔로랭크"
        if current_game_state:
            onoffref = db.reference("승부예측/투표온오프")
            onoffbool = onoffref.get()

            anonymref = db.reference("승부예측/익명온오프")
            anonymbool = anonymref.get()

            complete_anonymref = db.reference("승부예측/완전익명온오프")
            complete_anonymbool = complete_anonymref.get()

            # 이전 게임의 match_id를 저장
            if name == "지모":
                if current_game_type == "솔로랭크":
                    p.jimo_current_match_id_solo = await get_summoner_recentmatch_id(puuid)
                else:
                    p.jimo_current_match_id_flex = await get_summoner_recentmatch_id(puuid)
            elif name == "Melon":
                if current_game_type == "솔로랭크":
                    p.melon_current_match_id_solo = await get_summoner_recentmatch_id(puuid)
                else:
                    p.melon_current_match_id_flex = await get_summoner_recentmatch_id(puuid)
            
            winbutton.disabled = onoffbool
            losebutton = discord.ui.Button(style=discord.ButtonStyle.danger,label="패배",disabled=onoffbool)
            betratebutton = discord.ui.Button(style=discord.ButtonStyle.primary,label="아이템 사용",disabled=onoffbool)

            
            prediction_view = discord.ui.View()
            prediction_view.add_item(winbutton)
            prediction_view.add_item(losebutton)
            prediction_view.add_item(betratebutton)

            upbutton = discord.ui.Button(style=discord.ButtonStyle.success,label="업",disabled=onoffbool)
            downbutton = discord.ui.Button(style=discord.ButtonStyle.danger,label="다운",disabled=onoffbool)
            perfectbutton = discord.ui.Button(style=discord.ButtonStyle.primary,label="퍼펙트",disabled=onoffbool)

            kda_view = discord.ui.View()
            kda_view.add_item(upbutton)
            kda_view.add_item(downbutton)
            kda_view.add_item(perfectbutton)
            
            refperfect = db.reference('승부예측/퍼펙트포인트')
            perfectr = refperfect.get()
            perfect_point = perfectr[name]
                
            async def disable_buttons():
                await asyncio.sleep(150)  # 2분 30초 대기
                alarm_embed = discord.Embed(title="알림", description="예측 종료까지 30초 남았습니다! ⏰", color=discord.Color.red())
                await channel.send(embed=alarm_embed)
                await asyncio.sleep(30) # 30초 대기
                winbutton.disabled = True
                losebutton.disabled = True
                betratebutton.disabled = True
                upbutton.disabled = True
                downbutton.disabled = True
                perfectbutton.disabled = True
                prediction_view = discord.ui.View()
                kda_view = discord.ui.View()
                prediction_view.add_item(winbutton)
                prediction_view.add_item(losebutton)
                prediction_view.add_item(betratebutton)
                kda_view.add_item(upbutton)
                kda_view.add_item(downbutton)
                kda_view.add_item(perfectbutton)
                if name == "지모":
                    await p.current_message_jimo.edit(view=prediction_view)
                    await p.current_message_kda_jimo.edit(view=kda_view)
                elif name == "Melon":
                    await p.current_message_melon.edit(view=prediction_view)
                    await p.current_message_kda_melon.edit(view=kda_view)
                

            async def auto_prediction():
                # 예측포인트의 모든 사용자 데이터 가져오기
                predict_points_ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트')
                users_data = predict_points_ref.get() or {}

                # 아이템별 사용자 목록 저장용 딕셔너리
                auto_bet_users = {
                    "자동예측지모승리": [],
                    "자동예측지모패배": [],
                    "자동예측Melon승리": [],
                    "자동예측Melon패배": []
                }

                for nickname, data in users_data.items():
                    items = data.get("아이템", {})

                    # 각 아이템이 True 라면 해당 리스트에 추가
                    for item in auto_bet_users.keys():
                        if items.get(item, 0):
                            member = bot.get_guild(298064707460268032).get_member_named(nickname)
                            auto_bet_users[item].append(member)
                
                await asyncio.sleep(120) # 2분 일단 대기
                if name == "지모":
                    for autowinner in auto_bet_users["자동예측지모승리"]:
                        delay = random.uniform(1, 5) # 1초부터 5초까지 랜덤 시간
                        await asyncio.sleep(delay)
                        await bet_button_callback(None,'win',ANONYM_NAME_WIN,autowinner)
                        print(f"{autowinner.display_name}의 자동예측지모승리")
                    for autoloser in auto_bet_users["자동예측지모패배"]:
                        delay = random.uniform(1, 5) # 1초부터 5초까지 랜덤 시간
                        await asyncio.sleep(delay)
                        await bet_button_callback(None,'lose',ANONYM_NAME_LOSE,autoloser)
                        print(f"{autoloser.display_name}의 자동예측지모패배")
                elif name == "Melon":
                    for autowinner in auto_bet_users["자동예측Melon승리"]:
                        delay = random.uniform(1, 5) # 1초부터 5초까지 랜덤 시간
                        await asyncio.sleep(delay)
                        await bet_button_callback(None,'win',ANONYM_NAME_WIN,autowinner)
                        print(f"{autowinner.display_name}의 자동예측Melon승리")
                    for autoloser in auto_bet_users["자동예측Melon패배"]:
                        delay = random.uniform(1, 5) # 1초부터 5초까지 랜덤 시간
                        await asyncio.sleep(delay)
                        await bet_button_callback(None,'lose',ANONYM_NAME_LOSE,autoloser)
                        print(f"{autoloser.display_name}의 자동예측Melon패배")


            prediction_votes = votes["prediction"]
            kda_votes = votes["kda"]
            
            async def bet_button_callback(interaction: discord.Interaction = None, prediction_type: str = "", anonym_names: list = None, nickname: discord.Member = None):
                if interaction:
                    nickname = interaction.user
                    await interaction.response.defer()  # 응답 지연 (버튼 눌렀을 때 오류 방지)
                if (nickname not in [user['name'] for user in prediction_votes["win"]]) and (nickname not in [user['name'] for user in prediction_votes["lose"]]):
                    refp = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname.name}')
                    pointr = refp.get()
                    point = pointr.get("포인트",0)
                    bettingPoint = pointr.get("베팅포인트",0)
                    random_number = random.uniform(0.01, 0.05) # 1% ~ 5% 랜덤 배팅 할 비율을 정합
                    baseRate = round(random_number, 2)
                    basePoint = round(point * baseRate) if point - bettingPoint >= 500 else 0 # 500p 이상 보유 시 자동 베팅
                    if basePoint > 0:
                        basePoint = math.ceil(basePoint / 10) * 10  # 10 단위로 무조건 올림
                    refp.update({"베팅포인트": bettingPoint + basePoint})
                    prediction_votes[prediction_type].append({"name": nickname, 'points': 0})
                    myindex = len(prediction_votes[prediction_type]) - 1 # 투표자의 위치 파악

                    await refresh_prediction(name,anonymbool, complete_anonymbool, prediction_votes) # 새로고침

                    prediction_value = "승리" if prediction_type == "win" else "패배"

                    if name == "지모":
                        #userembed = discord.Embed(title="메세지", color=0x000000)
                        noticeembed = discord.Embed(title="메세지", color=0x000000)
                    elif name == "Melon":
                        #userembed = discord.Embed(title="메세지", color=discord.Color.brand_green())
                        noticeembed = discord.Embed(title="메세지", color=discord.Color.brand_green())
                    if anonymbool:
                        #userembed.add_field(name="", value=f"{anonym_names[myindex]}님이 {prediction_value}에 투표하셨습니다.", inline=True)
                        if basePoint != 0:
                            bettingembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
                            bettingembed.add_field(name="", value=f"누군가가 {name}의 {prediction_value}에 {basePoint}포인트를 베팅했습니다!", inline=False)
                            noticeembed.add_field(name="",value=f"{name}의 {prediction_value}에 {basePoint}포인트 자동베팅 완료!", inline=False)
                            if interaction:
                                await interaction.followup.send(embed=noticeembed, ephemeral=True)
                        else:
                            noticeembed.add_field(name="",value=f"{name}의 {prediction_value}에 투표 완료!", inline=False)
                            if interaction:
                                if complete_anonymbool:
                                    await interaction.response.send_message(embed=noticeembed, ephemeral=True)
                                else:
                                    await interaction.followup.send(embed=noticeembed, ephemeral=True)
                    else:
                        #userembed.add_field(name="", value=f"{nickname.display_name}님이 {prediction_value}에 투표하셨습니다.", inline=True)
                        if basePoint != 0:
                            prediction_votes[prediction_type][myindex]['points'] += basePoint
                            await refresh_prediction(name,anonymbool,prediction_votes) # 새로고침
                            bettingembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
                            bettingembed.add_field(name="", value=f"{nickname.display_name}님이 {name}의 {prediction_value}에 {basePoint}포인트를 베팅했습니다!", inline=False)
                            if not complete_anonymbool: # 완전 익명이 아닐경우에만
                                await channel.send(f"\n", embed=bettingembed)
                            noticeembed.add_field(name="",value=f"{name}의 {prediction_value}에 {basePoint}포인트 자동베팅 완료!", inline=False)
                            if interaction:
                                if complete_anonymbool:
                                    await interaction.response.send_message(embed=noticeembed, ephemeral=True)
                                else:
                                    await interaction.followup.send(embed=noticeembed, ephemeral=True)
                    
                    #await channel.send(f"\n", embed=userembed)

                    # ====================  [미션]  ====================
                    # 미션 : 승부예측 1회

                    ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname.name}/미션/일일미션/승부예측 1회")
                    mission_data = ref.get()
                    mission_bool = mission_data.get('완료',False)
                    if not mission_bool:
                        ref.update({"완료" : True})
                        print(f"{nickname.display_name}의 [승부예측 1회] 미션 완료")

                    # ====================  [미션]  ====================

                    if basePoint != 0 and anonymbool:
                        delay = random.uniform(5, 30) # 5초부터 30초까지 랜덤 시간
                        await asyncio.sleep(delay)
                        prediction_votes[prediction_type][myindex]['points'] += basePoint
                        # 자동 베팅
                        await refresh_prediction(name,anonymbool,complete_anonymbool,prediction_votes) # 새로고침
                        if not complete_anonymbool: # 완전 익명이 아닐경우에만
                            await channel.send(f"\n", embed=bettingembed)
                else:
                    userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                    userembed.add_field(name="", value=f"{nickname.display_name}님은 이미 투표하셨습니다", inline=True)
                    if interaction:
                        await interaction.followup.send(embed=userembed, ephemeral=True)

            async def betrate_button_callback(interaction: discord.Interaction):
                nickname = interaction.user
                refitem = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname.name}/아이템')
                itemr = refitem.get()
                
                betbutton1 = discord.ui.Button(style=discord.ButtonStyle.primary,label="0.1")
                betbutton2 = discord.ui.Button(style=discord.ButtonStyle.primary,label="0.3")
                betbutton3 = discord.ui.Button(style=discord.ButtonStyle.primary,label="0.5")

                item_view = discord.ui.View()
                item_view.add_item(betbutton1)
                item_view.add_item(betbutton2)
                item_view.add_item(betbutton3)

                item_embed = discord.Embed(title="아이템 선택", color=discord.Color.purple())
                item_embed.add_field(name="", value="사용할 아이템을 선택하세요", inline=False)
                
                options = [
                    discord.SelectOption(label="배율 증가 0.1", value="increase_0.1"),
                    discord.SelectOption(label="배율 증가 0.3", value="increase_0.3"),
                    discord.SelectOption(label="배율 증가 0.5", value="increase_0.5"),
                    discord.SelectOption(label="배율 감소 0.1", value="decrease_0.1"),
                    discord.SelectOption(label="배율 감소 0.3", value="decrease_0.3"),
                    discord.SelectOption(label="배율 감소 0.5", value="decrease_0.5"),
                    discord.SelectOption(label="완전 익명화", value="complete_anonym")
                ]

                select = discord.ui.Select(placeholder="아이템을 선택하세요", options=options)


                async def select_callback(interaction: discord.Interaction):
                    selected_option = select.values[0]
                    item_map = {
                        "increase_0.1": "배율증가1",
                        "increase_0.3": "배율증가3",
                        "increase_0.5": "배율증가5",
                        "decrease_0.1": "배율감소1",
                        "decrease_0.3": "배율감소3",
                        "decrease_0.5": "배율감소5",
                        "complete_anonym": "완전 익명화",
                    }

                    description = {
                        "배율증가1": "이번 예측의 배율을 0.1 증가시킵니다.",
                        "배율증가3": "이번 예측의 배율을 0.3 증가시킵니다.",
                        "배율증가5": "이번 예측의 배율을 0.5 증가시킵니다.",
                        "배율감소1": "이번 예측의 배율을 0.1 감소시킵니다.\n배율 1.1 미만으로는 감소시킬 수 없습니다.",
                        "배율감소3": "이번 예측의 배율을 0.3 감소시킵니다.\n배율 1.1 미만으로는 감소시킬 수 없습니다.",
                        "배율감소5": "이번 예측의 배율을 0.5 감소시킵니다.\n배율 1.1 미만으로는 감소시킬 수 없습니다.",
                        "완전 익명화": "승부예측에 투표인원, 포인트, 메세지가 전부 나오지 않는 완전한 익명화를 적용합니다"
                    }

                    item_name = item_map[selected_option]
                    item_num = itemr.get(item_name, 0)

                    channel = bot.get_channel(int(CHANNEL_ID))
                    
                    if item_num > 0:
                        use_button = discord.ui.Button(style=discord.ButtonStyle.success, label="아이템 사용", disabled=False)

                        async def use_button_callback(interaction: discord.Interaction):
                            user_id = interaction.user.id
                            if used_items_for_user_jimo.get(user_id, False):
                                await interaction.response.send_message("이미 아이템을 사용했습니다.", ephemeral=True)
                                return

                            if winbutton.disabled:
                                await interaction.response.send_message("투표가 종료되어 사용할 수 없습니다!", ephemeral=True)
                            else:
                                refitem.update({item_name: item_num - 1})
                                refrate = db.reference(f'승부예측/배율증가/{name}')
                                rater = refrate.get()
                                userembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
                                if "increase" in selected_option:
                                    increase_value = float(selected_option.split("_")[1])
                                    refrate.update({'배율': round(rater['배율'] + increase_value, 1)})
                                    userembed.add_field(name="", value=f"누군가가 아이템을 사용하여 배율을 {increase_value} 올렸습니다!", inline=False)
                                elif "decrease" in selected_option:
                                    decrease_value = float(selected_option.split("_")[1])
                                    refrate.update({'배율': round(rater['배율'] - decrease_value, 1)})
                                    userembed.add_field(name="", value=f"누군가가 아이템을 사용하여 배율을 {decrease_value} 내렸습니다!", inline=False)
                                elif "complete_anonym" in selected_option:
                                    complete_anonymref = db.reference("승부예측/완전익명온오프")
                                    complete_anonymref.set(True) # 완전 익명 설정
                                    userembed.add_field(name="", value=f"누군가가 아이템을 사용하여 투표를 익명화하였습니다!", inline=False)
                                await channel.send(f"\n", embed=userembed)
                                await refresh_prediction(name, anonymbool,complete_anonymbool,prediction_votes)
                                if "increase" or "decrease" in selected_option:
                                    await interaction.response.send_message(f"{name}의 배율 {increase_value if 'increase' in selected_option else decrease_value} {'증가' if 'increase' in selected_option else '감소'} 완료! 남은 아이템: {item_num - 1}개", ephemeral=True)
                                    if name == "지모":
                                        used_items_for_user_jimo[user_id] = True
                                    elif name == "Melon":
                                        used_items_for_user_melon[user_id] = True
                                elif "complete_anonym" in selected_option:
                                    await interaction.response.send_message(f"{name}의 투표가 완전 익명화 되었습니다! 남은 아이템: {item_num - 1}개", ephemeral=True)
                                

                        use_button.callback = use_button_callback
                        item_view = discord.ui.View()
                        item_view.add_item(select)
                        item_view.add_item(use_button)

                        item_embed = discord.Embed(title=f"선택한 아이템 정보", color=discord.Color.purple())
                        item_embed.add_field(name="아이템 이름", value=f"{item_name}", inline=False)
                        item_embed.add_field(name="아이템 설명", value=f"{description[item_name]}", inline=False)
                        item_embed.add_field(name="아이템 개수", value=f"{item_num}개", inline=False)


                        await interaction.response.edit_message(embed = item_embed, view=item_view)
                    else:
                        await interaction.response.send_message("아이템이 없습니다!", ephemeral=True)

                select.callback = select_callback
                item_view = discord.ui.View()
                item_view.add_item(select)
                await interaction.response.send_message(f"\n", view=item_view, embed=item_embed, ephemeral=True)

            async def kda_button_callback(interaction: discord.Interaction, prediction_type: str):
                nickname = interaction.user
                if (nickname.name not in [user['name'].name for user in kda_votes['up']] )and (nickname.name not in [user['name'].name for user in kda_votes['down']]) and (nickname.name not in [user['name'].name for user in kda_votes['perfect']]):
                    kda_votes[prediction_type].append({"name": nickname})
                    await refresh_kda_prediction(name,anonymbool,kda_votes)

                    if name == "지모":
                        userembed = discord.Embed(title="메세지", color=0x000000)
                        noticeembed = discord.Embed(title="메세지", color=0x000000)
                    elif name == "Melon":
                        userembed = discord.Embed(title="메세지", color=discord.Color.brand_green())
                        noticeembed = discord.Embed(title="메세지", color=discord.Color.brand_green())
                    
                    if prediction_type == 'up':
                        userembed.add_field(name="", value=f"누군가가 {name}의 KDA를 3 이상으로 예측했습니다!", inline=True)
                    elif prediction_type == 'down':
                        userembed.add_field(name="", value=f"누군가가 {name}의 KDA를 3 이하로 예측했습니다!", inline=True)
                    else:
                        userembed.add_field(name="", value=f"누군가가 {name}의 KDA를 0 데스, 퍼펙트로 예측했습니다!", inline=True)
                    
                    #await channel.send(f"\n", embed=userembed)

                    if prediction_type == "up":
                        prediction_value = "KDA 3 이상"
                    elif prediction_type == "down":
                        prediction_value = "KDA 3 이하"
                    elif prediction_type == "perfect":
                        prediction_value = "KDA 퍼펙트"
                    
                    noticeembed.add_field(name="",value=f"{name}의 {prediction_value}에 투표 완료!", inline=False)
                    await interaction.response.send_message(embed=noticeembed, ephemeral=True)
                else:
                    userembed = discord.Embed(title="메세지", color=discord.Color.dark_gray())
                    userembed.add_field(name="", value=f"{nickname.display_name}님은 이미 투표하셨습니다", inline=True)
                    await interaction.response.send_message(embed=userembed, ephemeral=True)

            winbutton.callback = lambda interaction: bet_button_callback(interaction, 'win', ANONYM_NAME_WIN)
            losebutton.callback = lambda interaction: bet_button_callback(interaction, 'lose', ANONYM_NAME_LOSE)
            upbutton.callback = lambda interaction: kda_button_callback(interaction, 'up')
            downbutton.callback = lambda interaction: kda_button_callback(interaction, 'down')
            perfectbutton.callback = lambda interaction: kda_button_callback(interaction, 'perfect')
            betratebutton.callback = betrate_button_callback
            if name == "지모":
                prediction_embed = discord.Embed(title="예측 현황", color=0x000000) # Black
            elif name == "Melon":
                prediction_embed = discord.Embed(title="예측 현황", color=discord.Color.brand_green())
            if complete_anonymbool: # 완전 익명화 시
                win_predictions = "\n?명"
                lose_predictions = "\n?명"
            elif anonymbool:  # 익명 투표 시
                win_predictions = "\n".join(
                    f"{ANONYM_NAME_WIN[index]}: ? 포인트" for index, winner in enumerate(prediction_votes["win"])) or "없음"
                lose_predictions = "\n".join(
                    f"{ANONYM_NAME_LOSE[index]}: ? 포인트" for index, loser in enumerate(prediction_votes["lose"])) or "없음"
            else:
                win_predictions = "\n".join(
                    f"{winner['name'].display_name}: {winner['points']}포인트" for winner in prediction_votes["win"]) or "없음"
                lose_predictions = "\n".join(
                    f"{loser['name'].display_name}: {loser['points']}포인트" for loser in prediction_votes["lose"]) or "없음"
            
            winner_total_point = sum(winner["points"] for winner in prediction_votes["win"])
            loser_total_point = sum(loser["points"] for loser in prediction_votes["lose"])
            
            if complete_anonymbool: # 완전 익명화 시
                prediction_embed.add_field(name="총 포인트", value=f"승리: ? 포인트 | 패배: ? 포인트", inline=False)
            else:
                prediction_embed.add_field(name="총 포인트", value=f"승리: {winner_total_point}포인트 | 패배: {loser_total_point}포인트", inline=False)

            prediction_embed.add_field(name="승리 예측", value=win_predictions, inline=True)
            prediction_embed.add_field(name="패배 예측", value=lose_predictions, inline=True)

            if name == "지모":
                kda_embed = discord.Embed(title="KDA 예측 현황", color=0x000000) # Black
            elif name == "Melon":
                kda_embed = discord.Embed(title="KDA 예측 현황", color=discord.Color.brand_green())
            today = datetime.today()
            if today.weekday() == 6:
                kda_embed.add_field(name=f"",value=f"일요일엔 점수 2배! KDA 예측 점수 2배 지급!")
            kda_embed.add_field(name="퍼펙트 예측성공 포인트", value=perfect_point, inline=False)
            if anonymbool:
                up_predictions = "".join(f"{len(kda_votes['up'])}명")
                down_predictions = "".join(f"{len(kda_votes['down'])}명")
                perfect_predictions = "".join(f"{len(kda_votes['perfect'])}명")

                kda_embed.add_field(name="KDA 3 이상 예측", value=up_predictions, inline=False)
                kda_embed.add_field(name="KDA 3 이하 예측", value=down_predictions, inline=False)
                kda_embed.add_field(name="KDA 퍼펙트 예측", value=perfect_predictions, inline=False)
            else:
                up_predictions = "\n".join(f"{user['name'].display_name}" for user in kda_votes["up"]) or "없음"
                down_predictions = "\n".join(f"{user['name'].display_name}" for user in kda_votes["down"]) or "없음"
                perfect_predictions = "\n".join(f"{user['name'].display_name}" for user in kda_votes["perfect"]) or "없음"
            
                kda_embed.add_field(name="KDA 3 이상 예측", value=up_predictions, inline=False)
                kda_embed.add_field(name="KDA 3 이하 예측", value=down_predictions, inline=False)
                kda_embed.add_field(name="KDA 퍼펙트 예측", value=perfect_predictions, inline=False)

            curseasonref = db.reference("전적분석/현재시즌")
            current_season = curseasonref.get()

            refprev = db.reference(f'전적분석/{current_season}/점수변동/{name}/{current_game_type}')
            points = refprev.get()

            if points is None:
                game_win_streak = 0
                game_lose_streak = 0
            else:
                latest_date = max(points.keys())
                latest_time = max(points[latest_date].keys(), key=lambda t: datetime.strptime(t, '%H:%M:%S'))
                latest_data = points[latest_date][latest_time]
                game_win_streak = latest_data["연승"]
                game_lose_streak = latest_data["연패"]
        
            if game_win_streak >= 1:
                streak_bonusRate = calculate_bonus(game_win_streak)
                if name == "지모":
                    p.current_message_jimo = await channel.send(f"\n{name}의 {current_game_type} 게임이 감지되었습니다!\n승부예측을 해보세요!\n{game_win_streak}연승으로 패배 시 배율 {streak_bonusRate} 추가!", view=prediction_view, embed=prediction_embed)
                elif name == "Melon":
                    p.current_message_melon = await channel.send(f"\n{name}의 {current_game_type} 게임이 감지되었습니다!\n승부예측을 해보세요!\n{game_win_streak}연승으로 패배 시 배율 {streak_bonusRate} 추가!", view=prediction_view, embed=prediction_embed)
            elif game_lose_streak >= 1:
                streak_bonusRate = calculate_bonus(game_lose_streak)
                if name == "지모":
                    p.current_message_jimo = await channel.send(f"\n{name}의 {current_game_type} 게임이 감지되었습니다!\n승부예측을 해보세요!\n{game_lose_streak}연패로 승리 시 배율 {streak_bonusRate} 추가!", view=prediction_view, embed=prediction_embed)
                elif name == "Melon":
                    p.current_message_melon = await channel.send(f"\n{name}의 {current_game_type} 게임이 감지되었습니다!\n승부예측을 해보세요!\n{game_lose_streak}연패로 승리 시 배율 {streak_bonusRate} 추가!", view=prediction_view, embed=prediction_embed)
            else:
                if name == "지모":
                    p.current_message_jimo = await channel.send(f"\n{name}의 {current_game_type} 게임이 감지되었습니다!\n승부예측을 해보세요!\n", view=prediction_view, embed=prediction_embed)
                elif name == "Melon":
                    p.current_message_melon = await channel.send(f"\n{name}의 {current_game_type} 게임이 감지되었습니다!\n승부예측을 해보세요!\n", view=prediction_view, embed=prediction_embed)

            if name == "지모":
                p.current_message_kda_jimo = await channel.send("\n", view=kda_view, embed=kda_embed)
            elif name == "Melon":
                p.current_message_kda_melon = await channel.send("\n", view=kda_view, embed=kda_embed)

            #if not onoffbool:
                #await notice_channel.send(f"{name}의 {current_game_type} 게임이 감지되었습니다!\n승부예측을 해보세요!\n")

            event.clear()
            await asyncio.gather(
                disable_buttons(),
                auto_prediction(),
                event.wait()  # 이 작업은 event가 set될 때까지 대기
            )
            print(f"check_game_status for {name} 대기 종료")

        await asyncio.sleep(20)  # 20초마다 반복

async def check_remake_status(name, puuid, event, prediction_votes,kda_votes):
    channel = bot.get_channel(int(CHANNEL_ID))
    last_game_state = False

    cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
    current_predict_season = cur_predict_seasonref.get()

    while not bot.is_closed():
        current_game_state, current_game_type = await nowgame(puuid)
        if current_game_state != last_game_state:
            if not current_game_state:
                
                # open_prediction에서 얻은 이전 게임의 current_match_id를 파악한 뒤 previous_match_id에 넣음
                if name == "지모":
                    if current_game_type == "솔로랭크":
                        previous_match_id_solo = p.jimo_current_match_id_solo
                    else:
                        previous_match_id_flex  = p.jimo_current_match_id_flex
                elif name == "Melon":
                    if current_game_type == "솔로랭크":
                        previous_match_id_solo = p.melon_current_match_id_solo
                    else:
                        previous_match_id_flex = p.melon_current_match_id_flex

                await asyncio.sleep(30)  # 게임 종료 후 30초 대기
                
                # 30초 뒤 다시 이전 게임의 match_id를 구함. match_id가 다르다면 게임이 끝난 것(다시하기)
                async def check_match_id(puuid, previous_match_id):
                    current_match_id = await get_summoner_recentmatch_id(puuid)
                    return previous_match_id != current_match_id, current_match_id

                # match_id를 확인하고 게임이 끝났는지 판단
                if current_game_type == "솔로랭크":
                    match_ended, current_match_id = await check_match_id(puuid, previous_match_id_solo)
                else:
                    match_ended, current_match_id = await check_match_id(puuid, previous_match_id_flex)

                if match_ended: # 게임이 끝났다면
                    match_info = await get_summoner_matchinfo(current_match_id)
                    participant_id = get_participant_id(match_info, puuid)

                    if match_info['info']['participants'][participant_id]['gameEndedInEarlySurrender'] and int(match_info['info']['gameDuration']) <= 240:
                        await refresh_prediction(name,False,False,prediction_votes) # 베팅내역 공개
                        await refresh_kda_prediction(name,False,kda_votes) # KDA 예측내역 공개

                        complete_anonymref = db.reference("승부예측/완전익명온오프")
                        complete_anonymref.set(False) # 완전 익명 해제

                        userembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
                        userembed.add_field(name="게임 종료", value=f"{name}의 랭크게임이 종료되었습니다!\n다시하기\n")
                        await channel.send(embed=userembed)

                        winners = prediction_votes['win']
                        losers = prediction_votes['lose']
                        for winner in winners:
                            ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner['name'].name}")
                            originr = ref.get()
                            bettingPoint = originr.get("베팅포인트",0)
                            bettingPoint -= winner['points']
                            ref.update({"베팅포인트": bettingPoint})

                        for loser in losers:
                            ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{loser['name'].name}")
                            originr = ref.get()
                            bettingPoint = originr.get("베팅포인트",0)
                            bettingPoint -= loser['points']
                            ref.update({"베팅포인트": bettingPoint})

                        
                        # ====================  [미션]  ====================
                        # 시즌미션 : 다중 그림자분신술
                        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                        current_predict_season = cur_predict_seasonref.get()
                        for better in prediction_votes['win'] + prediction_votes['lose']:
                            shadow_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{better['name'].name}/미션/시즌미션/다중 그림자분신술")
                            shadow_ref.update({f"{name}베팅" : 0})

                        # ====================  [미션]  ====================

                        prediction_votes['win'].clear()
                        prediction_votes['lose'].clear()
                        kda_votes['up'].clear()
                        kda_votes['down'].clear()
                        kda_votes['perfect'].clear()

                        
                        
                        event.set()

        last_game_state = current_game_state
        await asyncio.sleep(20)


async def update_mission_message():
    mission_channel = bot.get_channel(int(MISSION_CHANNEL_ID)) # 미션 채널
    global MESSAGE_ID
    MESSAGE_ID = 1339062649287217184

    if not mission_channel:
        return

    while True:
        # 현재 시간 (KST 기준)
        now = datetime.now()
        reset_time = now.replace(hour=5, minute=0, second=0, microsecond=0)
        if now >= reset_time:
            reset_time += timedelta(days=1)

        # 남은 시간 계산 (시간, 분)
        remaining_time = reset_time - now
        hours, remainder = divmod(remaining_time.seconds, 3600)
        minutes = remainder // 60

        season_end_date = datetime(2025, 4, 1, 0, 0, 0)
        time_difference = season_end_date - now
        
        # 시간 차이를 한글로 변환하여 출력
        sdays = time_difference.days
        shours , sremainder = divmod(time_difference.seconds, 3600)

        output = ""
        if sdays:
            output += f"{sdays}일 "
        if shours:
            output += f"{shours}시간 "

        if time_difference.total_seconds() < 0:
            output = "시즌 종료"

        # 미션 임베드 생성
        embed = discord.Embed(title="🎯 예측 미션", color=discord.Color.blue())
        embed.add_field(name="⏳ 일일 미션 초기화까지 남은 시간", value=f"{hours}시간 {minutes}분", inline=False)
        embed.add_field(name="⏳ 시즌 초기화까지 남은 시간", value=f"{output}", inline=False)
        embed.set_footer(text="아래 버튼을 눌러 미션을 확인하세요.")

        if MESSAGE_ID is None:
            message = await mission_channel.send(content="",embed=embed, view=MissionView())
            MESSAGE_ID = message.id
        else:
            try:
                message = await mission_channel.fetch_message(MESSAGE_ID)
                await message.edit(content="",embed=embed, view=MissionView())
            except discord.NotFound:
                # 메시지가 삭제된 경우 새로 생성
                message = await mission_channel.send(content="",embed=embed, view=MissionView())
                MESSAGE_ID = message.id

        await asyncio.sleep(60)  # 1분마다 업데이트 (초 단위)

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=Intents.all(),
            sync_command=True,
            application_id=1232000910872547350
        )
        self.initial_extension = [
            "Cogs.commands"
        ]

    async def setup_hook(self):
        for ext in self.initial_extension:
            await self.load_extension(ext)

        await bot.tree.sync(guild=Object(id=298064707460268032))

    async def on_ready(self):
        print('Logged on as', self.user)
        await self.change_presence(status=Status.online,
                                    activity=Game("만세"))
        cred = credentials.Certificate("mykey.json")
        firebase_admin.initialize_app(cred,{
            'databaseURL' : 'https://mansaebot-default-rtdb.firebaseio.com/'
        })
        await self.tree.sync(guild=Object(id=298064707460268032))

        admin = await bot.fetch_user("298068763335589899")  # toe_kyung의 디스코드 사용자 ID 입력
        '''
        if admin:
            try:
                #DM 보내기
                await admin.send("ㅎㅇ")
                print(f"{user.name}에게 DM 전송 완료")
            except Exception as e:
                print(f"DM 전송 실패: {e}")
        else:
            print("관리자가 발견되지 않았습니다")
        '''

        bot.loop.create_task(update_mission_message())
        
        # Task for Jimo
        bot.loop.create_task(open_prediction(
            name="지모", 
            puuid=JIMO_PUUID, 
            votes=p.votes['지모'], 
            channel_id=CHANNEL_ID, 
            notice_channel_id=NOTICE_CHANNEL_ID, 
            event=p.jimo_event,
            current_game_state = p.jimo_current_game_state,
            winbutton = p.jimo_winbutton
        ))

        '''
        # Task for Melon
        bot.loop.create_task(open_prediction(
            name="Melon", 
            puuid=MELON_PUUID, 
            votes=p.votes['Melon'], 
            channel_id=CHANNEL_ID, 
            notice_channel_id=NOTICE_CHANNEL_ID, 
            event=p.melon_event, 
            current_game_state = p.melon_current_game_state,
            winbutton = p.melon_winbutton
        ))
        '''
        # Check points for Jimo
        bot.loop.create_task(check_points(
            puuid=JIMO_PUUID, 
            summoner_id=JIMO_ID, 
            name="지모", 
            channel_id=CHANNEL_ID, 
            notice_channel_id=NOTICE_CHANNEL_ID, 
            votes=p.votes['지모'], 
            event=p.jimo_event
        ))

        # Check points for Melon
        bot.loop.create_task(check_points(
            puuid=MELON_PUUID, 
            summoner_id=MELON_ID, 
            name="Melon", 
            channel_id=CHANNEL_ID, 
            notice_channel_id=NOTICE_CHANNEL_ID, 
            votes=p.votes['Melon'], 
            event=p.melon_event
        ))

        bot.loop.create_task(check_remake_status("지모", JIMO_PUUID, p.jimo_event, p.votes['지모']['prediction'],p.votes['지모']['kda']))
        bot.loop.create_task(check_remake_status("Melon", MELON_PUUID, p.melon_event, p.votes['Melon']['prediction'],p.votes['Melon']['kda']))

bot = MyBot()
@bot.event
async def on_message(message):

    if message.author == bot.user:
        return


load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
API_KEY = os.getenv("RIOT_API_KEY")
JIMO_PUUID = os.getenv("JIMO_PUUID")
JIMO_ID = os.getenv("JIMO_ID")
MELON_PUUID = os.getenv("MELON_PUUID")
MELON_ID = os.getenv("MELON_ID")

bot.run(TOKEN)