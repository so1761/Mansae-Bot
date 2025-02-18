import requests
import discord
import platform
import random
import matplotlib.pyplot as plt
import concurrent.futures
import asyncio
import aiohttp
import pandas as pd
import mplfinance as mpf
import prediction_vote as p
import subprocess
import os
from discord.ui import Modal, TextInput
from discord import TextStyle
from firebase_admin import db
from discord.app_commands import Choice
from discord import app_commands
from discord.ext import commands
from discord import Interaction
from discord import Object
from datetime import datetime
from matplotlib import font_manager, rc
from dotenv import load_dotenv


API_KEY = None

JIMO_NAME = '강지모'
JIMO_TAG = 'KR1'

# 경고 채널의 ID (실제 채널 ID로 변경)
WARNING_CHANNEL_ID = 1314643507490590731

SEASON_CHANGE_DATE = datetime(2024, 5, 15, 0, 0, 0)
SEASON_CHANGE_DATE2 = datetime(2024, 9, 11, 0, 0, 0)
SEASON_CHANGE_DATE3 = datetime(2025, 1, 9, 0, 0, 0)
SEASON_CHANGE_DATE15 = datetime(2026,1, 1, 0, 0, 0)


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

#익명 이름
ANONYM_NAME_WIN = [
  '개코원숭이','긴팔원숭이','일본원숭이','붉은고함원숭이','알락꼬리여우원숭이','다이아나원숭이','알렌원숭이','코주부원숭이',
]
ANONYM_NAME_LOSE = [
  '사랑앵무','왕관앵무','회색앵무','모란앵무','금강앵무','유황앵무','뉴기니아앵무','장미앵무'
]

CHANNEL_ID = '938728993329397781'

class NotFoundError(Exception):
    pass

class TooManyRequestError(Exception):
    pass

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

def restart_script(): # 봇 재시작 명령어
    try:
        # restart_bot.py 실행
        subprocess.run(["python3", "/home/xoehfdl8182/restart_bot.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing restart_bot.py: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


def seconds_to_minutes_and_seconds(seconds): # 초로 주어진 데이터를 분:초 형태로 변환
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    return f"{minutes:02d}:{remaining_seconds:02d}"

def get_tier_name(value): # 숫자를 통해 티어 이름 가져오기(딕셔너리 역으로 계산)
    for tier, rank in TIER_RANK_MAP.items():
        if rank == value:
            return tier
    return None  # If value is not found in the dictionary

def tier_to_number(tier, rank, lp): # 티어를 레이팅 숫자로 변환
    tier_num = TIER_RANK_MAP.get(tier)
    rank_num = RANK_MAP.get(rank)
    if tier_num is None or rank_num is None:
        return None
    return tier_num * 400 + rank_num * 100 + lp

def number_to_tier(lp_number): # 레이팅 숫자를 티어로 변환
    tier_num = lp_number // 400
    lp_number %= 400
    rank_num = lp_number // 100
    lp = lp_number % 100
    for tier, tier_num_val in TIER_RANK_MAP.items():
        for rank, rank_num_val in RANK_MAP.items():
            if tier_num == tier_num_val and rank_num == rank_num_val:
                return f"{tier} {rank} {lp}P"
    return None

def number_to_tier2(lp_number): # 레이팅 숫자를 티어로 변환 (DIAMOND -> D)
    tier_num = lp_number // 400
    lp_number %= 400
    rank_num = lp_number // 100
    lp = lp_number % 100
    for tier, tier_num_val in TIER_RANK_MAP2.items():
        for rank, rank_num_val in RANK_MAP.items():
            if tier_num == tier_num_val and rank_num == rank_num_val:
                return f"{tier} {rank} {lp}P"
    return None

def give_item(nickname, item_name, amount):
    cur_predict_seasonref = db.reference("승부예측/현재예측시즌") # 현재 진행중인 예측 시즌을 가져옴
    current_predict_season = cur_predict_seasonref.get()

    # 사용자 아이템 데이터 위치
    refitem = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname}/아이템')
    item_data = refitem.get()

    refitem.update({item_name: item_data.get(item_name, 0) + amount})

async def add_missions_to_all_users(mission_name,point,mission_type):
    cur_predict_seasonref = db.reference("승부예측/현재예측시즌") # 현재 진행중인 예측 시즌을 가져옴
    current_predict_season = cur_predict_seasonref.get()
    # '예측포인트' 경로 아래의 모든 유저들 가져오기
    ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트")
    all_users = ref.get()
    
    # 각 유저에게 미션 추가
    if all_users:
        for user_id, user_data in all_users.items():
            # 각 유저의 '미션' 경로
            user_daily_missions_ref = ref.child(user_id).child("미션").child(mission_type)

            # 미션 타입에 해당하는 기존 미션 목록을 가져와서 ID 생성
            mission_type_data = user_data.get("미션", {}).get(mission_type, {})

            # 새로운 미션 이름과 관련된 데이터
            new_mission = {
                "완료": False,
                "보상수령": False,
                "포인트": point
            }

            # 미션 이름을 키로 사용하여 미션 추가
            user_daily_missions_ref.child(mission_name).set(new_mission)
        return True
    else:
        return False
        
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

async def get_summoner_ranks(summoner_id, type="솔랭"):
    url = f'https://kr.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}'
    headers = {'X-Riot-Token': API_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                if type == "솔랭":
                    # queueType이 RANKED_SOLO_5x5인 경우만 가져오기
                    filtered_data = [entry for entry in data if entry.get("queueType") == "RANKED_SOLO_5x5"]
                elif type == "자랭":
                    # queueType이 RANKED_FLEX_SR인 경우만 가져오기
                    filtered_data = [entry for entry in data if entry.get("queueType") == "RANKED_FLEX_SR"]
                if filtered_data:
                    return filtered_data[0]  # 첫 번째 티어 정보만 반환
                else:
                    return []
            elif response.status == 404:
                raise NotFoundError("404 Error occurred")
            else:
                print('Error:', response.status)
                return None

async def get_summoner_recentmatch_id(puuid):
    url = f'https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?queue=420&type=ranked&start=0&count=1'
    headers = {'X-Riot-Token': API_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data[0] if data else None
            else:
                print('Error:', response.status)
                return None

async def get_summoner_matchinfo(matchid):
    url = f'https://asia.api.riotgames.com/lol/match/v5/matches/{matchid}'
    headers = {'X-Riot-Token': API_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                print('Error:', response.status)
                return None

def get_summoner_matchinfo_nonaysnc(matchid): #matchid로 매치 정보 구하기
    url = f'https://asia.api.riotgames.com/lol/match/v5/matches/{matchid}'
    headers = {'X-Riot-Token': API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 404:
        raise NotFoundError("404 Error occurred")
    else:
        print('Error:', response.status_code)
        return None

class WarnModal(Modal):
    reason = TextInput(label="경고 사유", placeholder="경고 사유를 입력하세요.")

    def __init__(self, message: discord.Message):
        super().__init__(title="경고 사유 입력")
        self.message = message

    async def on_submit(self, interaction: discord.Interaction):
        warned_user = self.message.author
        moderator = interaction.user
        reason = self.reason.value
        
        WARNING_EMOJI = '⚠️'  # 경고 이모지

        # 임베드 생성
        embed = discord.Embed(title="경고 기록", color=discord.Color.red())
        embed.add_field(name="경고 대상", value=warned_user.mention, inline=True)
        embed.add_field(name="경고 발령자", value=moderator.mention, inline=True)
        embed.add_field(name="경고 사유", value=reason, inline=False)
        embed.add_field(name="대상 메시지", value=self.message.content, inline=False)
        embed.set_footer(text=f"메시지 ID: {self.message.id}")

        # 버튼 생성
        button = discord.ui.Button(label="원본 메시지로 이동", url=f"https://discord.com/channels/{self.message.guild.id}/{self.message.channel.id}/{self.message.id}")
        view = discord.ui.View()
        view.add_item(button)
        
        channel = interaction.client.get_channel(self.message.channel.id)
        message = await channel.fetch_message(self.message.id)
        await message.add_reaction(WARNING_EMOJI)
        # 경고 채널에 임베드 전송
        warning_channel = interaction.client.get_channel(WARNING_CHANNEL_ID)
        if warning_channel:
            await warning_channel.send(embed=embed, view = view)
            await interaction.response.send_message(embed=embed, view = view)
        else:
            await interaction.response.send_message("경고 채널을 찾을 수 없습니다.", ephemeral=True)

def plot_lp_difference_firebase(season=None,name=None,rank=None):

    if season == None:
        # 현재 날짜 및 시간 가져오기
        curseasonref = db.reference("전적분석/현재시즌")
        current_season = curseasonref.get()
        season = current_season

    if name == None:
        name = "지모"
    
    if rank == None:
        rank = "솔로랭크"
    
    print(season)
    ref = db.reference(f'전적분석/{season}/점수변동/{name}/{rank}')
    lp_difference = ref.get()
    if lp_difference == None:
        return -1

    lp_scores = []
    # 각 날짜의 데이터를 정리하여 리스트에 추가
    for date, entries in lp_difference.items():
        for entry in entries.values():
            score = entry.get('현재 점수')
            lp_scores.append(score)

    # 한글 폰트 지정
    # 운영 체제 확인
    if platform.system() == 'Windows':
        font_path = "C:/Windows/Fonts/malgun.ttf"
    elif platform.system() == 'Linux':
        font_path = "/usr/share/fonts/nanum/NanumGothic.ttf"  # 리눅스에서는 적절한 폰트 경로로 수정

    font_name = font_manager.FontProperties(fname=font_path).get_name()
    rc('font', family=font_name)
    # 그래프 그리기
    if name == '지모':
        plt.plot(lp_scores, marker='', linestyle='-',color ="dodgerblue")
    if name == 'Melon':
        plt.plot(lp_scores, marker='', linestyle='-',color ="violet")
    plt.title(f"{name} {rank} LP 변화량 추이")
    plt.xlabel('게임 플레이 판수')
    plt.ylabel('현재 LP 점수')
    xticks = []
    for i in range(0, len(lp_scores)):
        xticks.append(i)

    if len(lp_scores) >= 20:
        # 판수 5판 간격마다 xticks 설정
        xticks = list(range(0, len(lp_scores), 5))
    if len(lp_scores) >= 100:
        # 판수 10판 간격마다 xticks 설정
        xticks = list(range(0, len(lp_scores), 10))
    if len(lp_scores) >= 200:
        # 판수 20판 간격마다 xticks 설정
        xticks = list(range(0, len(lp_scores), 20))
    if len(lp_scores) >= 300:
        # 판수 20판 간격마다 xticks 설정
        xticks = list(range(0, len(lp_scores), 30))
    plt.xticks(xticks)
    plt.tight_layout()

    # 최고점과 최저점 계산
    min_lp = min(lp_scores)
    max_lp = max(lp_scores)


    '''
    # Y축 레이블 설정
    yticks = [min_lp, max_lp]
    interval = (max_lp - min_lp) // 5
    for i in range(min_lp + interval, max_lp, interval):
        yticks.append(i)
    '''

    # 티어 분기점 설정 (50점 간격)
    tier_breakpoints = list(range((min_lp // 50) * 50, max_lp + 1, 50))

    # Y 축 레이블 설정
    plt.yticks(tier_breakpoints, [number_to_tier2(lp) for lp in tier_breakpoints])


    # 티어 분기점 설정 (100점 간격)
    tier_breakpoints = list(range((min_lp // 100) * 100, max_lp + 1, 100))

    # 티어 분기점에 점선 추가
    for tier_point in tier_breakpoints:
        plt.axhline(y=tier_point, color='gray', linestyle='--')


    # Y축 레이블 수정 (티어 및 랭크로 변경)
    #plt.yticks(yticks, [number_to_tier2(lp) for lp in yticks])

    # 그래프를 이미지 파일로 저장
    plt.savefig('lp_graph.png')
    plt.close()
    return 0

async def plot_candle_graph(시즌:str, 이름:str, 랭크:str):
    ref = db.reference(f'전적분석/{시즌}/점수변동/{이름}/{랭크}')
    data = ref.get()

    if data == None:
        return None
    date_list = []

    # 최고 점수와 최저 점수 초기화
    highest_score = float('-inf')
    lowest_score = float('inf')

    # 각 날짜의 데이터를 정리하여 리스트에 추가
    for date, entries in data.items():
        total_lp_change = 0
        max_score = float('-inf')  # 최고 점수를 음의 무한대로 초기화
        min_score = float('inf')   # 최저 점수를 양의 무한대로 초기화
        start_score = None
        final_score = None
        game_count = 0  # 판수를 초기화

        for entry in entries.values():
            lp_change = entry.get('LP 변화량', 0)
            score = entry.get('현재 점수', 0)
            game_count += 1

            if start_score is None:
                start_score = score - lp_change

            total_lp_change += lp_change
            max_score = max(max_score, score)
            min_score = min(min_score, score)
            final_score = score  # 반복이 끝날 때의 점수를 최종 점수로 설정
        # 최고 점수와 최저 점수 업데이트
        highest_score = max(highest_score, max_score)
        lowest_score = min(lowest_score, min_score)

        date_list.append({
            '날짜': date,
            '시작 점수': start_score,
            '총 LP 변화량': total_lp_change,
            '최고 점수': max_score,
            '최저 점수': min_score,
            '최종 점수': final_score,
            '판수': game_count
        })

    highest_tier = number_to_tier(highest_score)
    lowest_tier = number_to_tier(lowest_score)
    basecolor = 0x000000
    embed = discord.Embed(title=f'{이름} 점수 변동', color = basecolor)
    embed.add_field(name="최고점수", value=f"{highest_tier}({highest_score})",inline=False)
    embed.add_field(name="최저점수", value=f"{lowest_tier}({lowest_score})",inline=False)


    # 데이터프레임 생성
    df = pd.DataFrame(date_list)
    df['날짜'] = pd.to_datetime(df['날짜'])
    df.set_index('날짜', inplace=True)

    # 데이터프레임 열 이름 변경 (예: '시작 점수'를 'Open', '최고 점수'를 'High' 등으로 변경)
    df.rename(columns={'시작 점수': 'Open', '최고 점수': 'High', '최저 점수': 'Low', '최종 점수': 'Close', '판수': 'Volume'}, inplace=True)

    def make_mpf_style():
        # marketcolors 설정
        mc = mpf.make_marketcolors(up='red', down='blue')
        # 스타일 설정
        return mpf.make_mpf_style(base_mpf_style = "binance",marketcolors=mc)
    # 캔들스틱 차트 그리기
    fig, axlist = mpf.plot(df, type='candle', style= make_mpf_style(), ylabel='Tier', xlabel='Dates', mav=2, volume=True, ylabel_lower='Games', returnfig=True)

    # 파일 경로 및 이름 설정
    file_path = "candle_graph.png"

    # 그림을 파일로 저장
    fig.savefig(file_path)
    plt.close(fig)
    return embed

async def refresh_prediction(name, anonym, prediction_votes):
    if name == "지모":
        embed = discord.Embed(title="예측 현황", color=0x000000) # Black
    elif name == "Melon":
        embed = discord.Embed(title="예측 현황", color=discord.Color.brand_green())
    refrate = db.reference(f'승부예측/배율증가/{name}')
    rater = refrate.get()
    if rater['배율'] != 0:
        embed.add_field(name="", value=f"추가 배율 : {rater['배율']}", inline=False)
    if anonym:
        win_predictions = "\n".join(f"{ANONYM_NAME_WIN[index]}: ? 포인트" for index, user in enumerate(prediction_votes["win"])) or "없음"
        lose_predictions = "\n".join(f"{ANONYM_NAME_LOSE[index]}: ? 포인트" for index, user in enumerate(prediction_votes["lose"])) or "없음"
    else:
        win_predictions = "\n".join(f"{user['name']}: {user['points']}포인트" for user in prediction_votes["win"]) or "없음"
        lose_predictions = "\n".join(f"{user['name']}: {user['points']}포인트" for user in prediction_votes["lose"]) or "없음"
    
    winner_total_point = sum(winner["points"] for winner in prediction_votes["win"])
    loser_total_point = sum(loser["points"] for loser in prediction_votes["lose"])
    embed.add_field(name="총 포인트", value=f"승리: {winner_total_point}포인트 | 패배: {loser_total_point}포인트", inline=False)
    
    embed.add_field(name="승리 예측", value=win_predictions, inline=True)
    embed.add_field(name="패배 예측", value=lose_predictions, inline=True)
    
    if name == "지모":
        await p.current_message_jimo.edit(embed=embed)
    elif name == "Melon":
        await p.current_message_melon.edit(embed=embed)

def nowgameinfo(puuid): #puuid를 통해 현재 진행중인 게임의 참가자 정보를 반환
    url = f'https://kr.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}'
    headers = {'X-Riot-Token': API_KEY}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()["participants"]

async def get_recent_matches(puuid, queue, startNum):
    url = f'https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?queue={queue}&start={startNum}&count=5'
    headers = {'X-Riot-Token': API_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                match_ids = await response.json()
                return match_ids
            elif response.status == 404:
                raise NotFoundError("404 Error occurred")
            elif response.status == 429:
                raise TooManyRequestError("429 Error occurred")
            else:
                print('Error:', response.status)
                return None

async def get_recent_solo_ranked_matches(puuid, startNum):
    return await get_recent_matches(puuid, 420, startNum)

async def get_recent_flex_ranked_matches(puuid, startNum):
    return await get_recent_matches(puuid, 440, startNum)

async def get_recent_clash_matches(puuid, startNum):
    return await get_recent_matches(puuid, 700, startNum)

def get_participant_id(match_info, puuid): # match정보와 puuid를 통해 그 판에서 플레이어의 위치를 반환
    for i, participant in enumerate(match_info['info']['participants']):
        if participant['puuid'] == puuid:
            return i
    return None

'''# 승리/패배여부를 가져오는 함수

def wins_match_info(matchId, RNAME):
    try:
        match_details = get_summoner_matchinfo(matchId)
    except NotFoundError as e:
        raise NotFoundError("404 Error occurred in wins_match_info")

    for player in match_details['info']['participants']:
        if player['riotIdGameName'].lower() == RNAME.lower():
            return player['win']
    return False'''


async def wins_all_match_info(match_ids, puuid):
    wins_list = []
    async with aiohttp.ClientSession() as session:
       # tasks = [get_match_info(session, match_id) for match_id in match_ids]
        tasks = []
        for match_id in match_ids:
            try:
                task = get_match_info(session, match_id)
            except NotFoundError as e:
                raise NotFoundError
            except TooManyRequestError as e:
                raise TooManyRequestError
            tasks.append(task)
        match_infos = await asyncio.gather(*tasks)
        for match_info in match_infos:
            if match_info:
                participant_id = get_participant_id(match_info, puuid)
                if participant_id is not None:
                    if match_info['info']['participants'][participant_id]['gameEndedInEarlySurrender'] == True and int(match_info['info']['gameDuration']) <= 240:
                        wins_list.append('draw')
                        continue
                    participant = match_info['info']['participants'][participant_id]
                    if participant['win']: wins_list.append('win')
                    else: wins_list.append('lose')
                else:
                    print('Participant not found')
                    wins_list.append(False)  # Participant not found
            else: wins_list.append(False)
    return wins_list

async def get_match_info(session, match_id):
    url = f'https://asia.api.riotgames.com/lol/match/v5/matches/{match_id}'
    headers = {'X-Riot-Token': API_KEY}
    async with session.get(url, headers=headers) as response:
        if response.status == 200:
            return await response.json()
        elif response.status == 404:
            raise NotFoundError("404 Error occurred")
        elif response.status == 429:
            raise TooManyRequestError("429 Error occurred")
        else:
            print(response.status)
            return

# 최근 20경기 승/패 계산
async def calculate_consecutive_matches(puuid):
    url = f'https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?queue=420&type=ranked&start=0&count=30'
    headers = {'X-Riot-Token': API_KEY}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        match_ids = response.json()

        # 매치 ID를 10개씩 3번에 걸쳐 처리
        first_10_matches = match_ids[:10]
        second_10_matches = match_ids[10:20]
        #third_10_matches = match_ids[20:30]

        wins_list = []
        async with aiohttp.ClientSession() as session:
            # 첫 번째 10개 매치에 대한 정보를 비동기적으로 가져옴
            try:
                wins_list.extend(await wins_all_match_info(first_10_matches, puuid))
            except NotFoundError as e:
                raise NotFoundError("404 Error occurred")
            except TooManyRequestError as e:
                raise TooManyRequestError

            #wins_list.extend(await wins_all_match_info(first_10_matches, puuid))
            # 두 번째 10개 매치에 대한 정보를 비동기적으로 가져옴
            #wins_list.extend(await wins_all_match_info(second_10_matches, puuid))
            try:
                wins_list.extend(await wins_all_match_info(second_10_matches, puuid))
            except NotFoundError as e:
                raise NotFoundError("404 Error occurred")
            except TooManyRequestError as e:
                raise TooManyRequestError
            # 세 번째 10개 매치에 대한 정보를 비동기적으로 가져옴
           # wins_list.extend(await wins_all_match_info(third_10_matches, puuid))

        print(wins_list)

        wins = 0
        loss = 0
        draws = 0
        for win in wins_list:
            if win == 'win':
                wins += 1
            elif win == 'draw':
                draws += 1
            elif win == 'lose':
                loss += 1
            else:
                continue

        return wins, draws, loss
    return 0

# 현재 연승을 계산하여 반환
async def calculate_consecutive_wins(puuid):
    url = f'https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?queue=420&type=ranked&start=0&count=20'
    headers = {'X-Riot-Token': API_KEY}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        match_ids = response.json()

        # 매치 ID를 10개씩 3번에 걸쳐 처리
        first_10_matches = match_ids[:7]
        second_10_matches = match_ids[7:14]
        #third_10_matches = match_ids[20:30]

        wins_list = []
        async with aiohttp.ClientSession() as session:
            # 첫 번째 10개 매치에 대한 정보를 비동기적으로 가져옴
            try:
                wins_list.extend(await wins_all_match_info(first_10_matches, puuid))
            except NotFoundError as e:
                raise NotFoundError
            except TooManyRequestError as e:
                raise TooManyRequestError
            # 두 번째 10개 매치에 대한 정보를 비동기적으로 가져옴
            try:
                wins_list.extend(await wins_all_match_info(second_10_matches, puuid))
            except NotFoundError as e:
                raise NotFoundError
            except TooManyRequestError as e:
                raise TooManyRequestError
            # 세 번째 10개 매치에 대한 정보를 비동기적으로 가져옴
           # wins_list.extend(await wins_all_match_info(third_10_matches, puuid))

        print(wins_list)

        win_streak = 0
        for win in wins_list:
            if win == 'win':
                win_streak += 1
            elif win == False:
                return -1
            else:
                break

        return win_streak
    return 0

# 현재 연패를 계산하여 반환
async def calculate_consecutive_losses(puuid):
    url = f'https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?queue=420&type=ranked&start=0&count=20'
    headers = {'X-Riot-Token': API_KEY}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        match_ids = response.json()

        # 매치 ID를 10개씩 3번에 걸쳐 처리
        first_10_matches = match_ids[:7]
        second_10_matches = match_ids[7:14]
        #third_10_matches = match_ids[20:30]

        wins_list = []
        async with aiohttp.ClientSession() as session:
            # 첫 번째 10개 매치에 대한 정보를 비동기적으로 가져옴
            try:
                wins_list.extend(await wins_all_match_info(first_10_matches, puuid))
            except NotFoundError as e:
                raise NotFoundError
            except TooManyRequestError as e:
                raise TooManyRequestError
            # 두 번째 10개 매치에 대한 정보를 비동기적으로 가져옴
            try:
                wins_list.extend(await wins_all_match_info(second_10_matches, puuid))
            except NotFoundError as e:
                raise NotFoundError
            except TooManyRequestError as e:
                raise TooManyRequestError
            # 세 번째 10개 매치에 대한 정보를 비동기적으로 가져옴
           # wins_list.extend(await wins_all_match_info(third_10_matches, puuid))

        print(wins_list)

        lose_streak = 0
        for win in wins_list:
            if win == 'lose':
                lose_streak += 1
            elif win == False:
                return -1
            else:
                break

        return lose_streak
    return 0

# 매치 정보를 가져오는 함수
def fetch_match_info(matchId, puuid):
    try:
        match_details = get_summoner_matchinfo_nonaysnc(matchId)
    except NotFoundError as e:
        raise NotFoundError

    player_stats = None
    for player in match_details['info']['participants']:
        if puuid == player['puuid']:
            player_stats = {
                'Kills': player['kills'],
                'Deaths': player['deaths'],
                'Assists': player['assists'],
                'Champion': player['championName'],
                'Position': player['individualPosition'],
                'Win': player['win']
            }
    return player_stats

# 매치 ID에 대한 정보를 병렬로 가져오는 함수
def fetch_all_match_info(matches, puuid):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # 각 매치 정보를 가져오는 함수를 병렬로 실행
        try:
            player_stats_list = executor.map(fetch_match_info, matches, [puuid] * len(matches))
        except NotFoundError as e:
            raise NotFoundError
    return list(player_stats_list)

# 확성기 모달 정의 (메세지 입력만)
class 확성기모달(Modal, title="확성기 메세지 작성"):
    def __init__(self, 익명여부: str):
        super().__init__()
        self.익명여부 = 익명여부  # 커맨드에서 받은 익명 여부를 저장
        # 메세지 입력 필드 추가
        self.message_input = TextInput(
            label="메세지",
            placeholder="보낼 메세지를 입력하세요",
            style=TextStyle.long,
            max_length=2000
        )
        self.add_item(self.message_input)

    async def on_submit(self, interaction: discord.Interaction):
        # 전송할 채널 ID
        channel = interaction.client.get_channel(1332330634546253915)
        
        # 예시: DB에서 현재 예측 시즌 및 포인트 정보를 가져오는 코드 (구현은 사용 중인 DB에 맞게 수정)
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
        current_predict_season = cur_predict_seasonref.get()
        ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{interaction.user.name}')
        originr = ref.get()
        point = originr["포인트"]
        bettingPoint = originr["베팅포인트"]
        
        # 익명 여부에 따른 필요 포인트 설정
        if self.익명여부.strip() == '익명':
            need_point = 150
        else:
            need_point = 100
        
        if point - bettingPoint < need_point:
            await interaction.response.send_message(
                f"포인트가 부족합니다! 현재 포인트: {point - bettingPoint} (베팅포인트 {bettingPoint} 제외)",
                ephemeral=True
            )
            return

        # 포인트 차감
        ref.update({"포인트": point - need_point})
        
        # 익명 여부에 따라 임베드 제목 결정
        if self.익명여부.strip() == '익명':
            embed = discord.Embed(title="익명의 메세지", color=discord.Color.light_gray())
        else:
            embed = discord.Embed(title=f"{interaction.user.name}의 메세지", color=discord.Color.light_gray())
            # ====================  [미션]  ====================
            # 시즌미션 : 세상을 향한 외침

            cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
            current_predict_season = cur_predict_seasonref.get()
            ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{interaction.user.name}/미션/시즌미션/세상을 향한 외침")
            mission_bool = ref.get()['완료']
            if not mission_bool:
                ref.update({"완료": True})
                print(f"{interaction.user.name}의 [세상을 향한 외침] 미션 완료")
                await mission_notice(interaction.client, interaction.user.name, "세상을 향한 외침")
            # ====================  [미션]  ====================
        embed.add_field(name="", value=self.message_input.value, inline=False)
        
        await channel.send("@everyone\n", embed=embed)
        await interaction.response.send_message(
            f"전송 완료! 남은 포인트: {point - bettingPoint - need_point} (베팅포인트 {bettingPoint} 제외)",
            ephemeral=True
        )

# 커스텀 모달 정의 (제목, 내용, URL 입력)
class 공지모달(Modal, title="공지 작성"):
    제목 = TextInput(
        label="제목", 
        placeholder="공지 제목을 입력하세요", 
        max_length=100,
        style=TextStyle.short  # 짧은 입력 스타일
    )
    메세지 = TextInput(
        label="내용", 
        placeholder="공지 내용을 입력하세요", 
        max_length=2000,
        style=TextStyle.long  # 긴 입력 스타일
    )
    url = TextInput(
        label="URL (선택)", 
        placeholder="옵션: URL을 입력하세요", 
        required=False,
        style=TextStyle.short
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.client.get_channel(1332330634546253915)
        if interaction.user.name == "toe_kyung":
            embed = discord.Embed(
                title=self.제목.value, 
                description=self.메세지.value, 
                color=discord.Color.light_gray()
            )
            if self.url.value:
                embed.url = self.url.value
            await channel.send("@everyone\n", embed=embed)
            await interaction.response.send_message("전송 완료!", ephemeral=True)
        else:
            await interaction.response.send_message("권한이 없습니다", ephemeral=True)

async def place_bet(bot,which,result,bet_amount):
    channel = bot.get_channel(int(CHANNEL_ID))
    userembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
    userembed.add_field(name="",value=f"누군가가 {which}의 {result}에 {bet_amount}포인트를 베팅했습니다!", inline=False)
    await channel.send(f"\n",embed = userembed)

async def mission_notice(bot,name, mission):
    channel = bot.get_channel(int(CHANNEL_ID))
    userembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
    userembed.add_field(name="",value=f"{name}님이 [{mission}]미션을 달성했습니다!", inline=False)
    await channel.send(f"\n",embed = userembed)  

class hello(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(
            name='경고 주기',
            callback=self.warn_user,
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    async def warn_user(self, interaction: discord.Interaction, message: discord.Message) -> None:
        # 경고 처리 로직
        allowed_role_name = "1등 ✨"
        #allowed_role_name = "관리자"
        # 사용자의 역할 확인
        user_roles = [role.name for role in interaction.user.roles]
        if allowed_role_name in user_roles:
            await interaction.response.send_modal(WarnModal(message))
        else:
            await interaction.response.send_message("경고는 1등만 부여할 수 있습니다.")

    @commands.Cog.listener()
    async def on_ready(self):
        load_dotenv()
        global API_KEY
        API_KEY = os.getenv("RIOT_API_KEY")

    @app_commands.command(name="전적분석",description="최근 5개의 경기를 분석합니다")
    @app_commands.describe(닉네임='소환사 닉네임',태그='소환사 태그 ex)KR1',시작전적 = '어느 판부터 분석할 지 숫자로 입력 (가장 최근전적부터 : 0)',리그 = "어떤 랭크를 분석할 지 선택하세요")
    @app_commands.choices(리그=[
    Choice(name='솔랭', value='1'),
    Choice(name='자랭', value='2'),
    Choice(name='격전', value='3')
    ])
    async def 전적분석(self,interaction: discord.Interaction, 닉네임:str, 태그:str, 시작전적:int, 리그: str):
        print(f"{interaction.user}가 요청한 전적분석 요청 수행")
        RNAME = 닉네임
        TLINE = 태그
        FROMNUM = 시작전적
        LEAGUE = 리그
        print(LEAGUE)
        RNAME = RNAME.strip()
        TLINE = TLINE.strip()
        print(f'RNAME : {RNAME}, TLINE : {TLINE}')
        try:
            puuid = await get_summoner_puuid(RNAME, TLINE)
        except NotFoundError as e:
            await interaction.response.send_message("404 에러: 해당 소환사를 찾을 수 없습니다.")
            return

        if LEAGUE == '1':
            # 솔로랭크 5개 매치 가져오기
            league_type = '솔로랭크'
            try:
                matches = await get_recent_solo_ranked_matches(puuid,FROMNUM)
            except NotFoundError as e:
                await interaction.response.send_message("전적을 찾을 수 없습니다")
                return
            except TooManyRequestError as e:
                await interaction.response.send_message("너무 많은 요청. 잠시 후 시도해주세요")
                return
        elif LEAGUE == '2':
            # 자유랭크 5개 매치 가져오기
            league_type = '자유랭크'
            try:
                matches = await get_recent_flex_ranked_matches(puuid,FROMNUM)
            except NotFoundError as e:
                await interaction.response.send_message("전적을 찾을 수 없습니다")
                return
            except TooManyRequestError as e:
                await interaction.response.send_message("너무 많은 요청. 잠시 후 시도해주세요")
                return
        elif LEAGUE == '3':
            league_type = '격전'
            # 격전 5개 매치 가져오기
            try:
                matches = await get_recent_clash_matches(puuid,FROMNUM)
            except NotFoundError as e:
                await interaction.response.send_message("전적을 찾을 수 없습니다")
                return
            except TooManyRequestError as e:
                await interaction.response.send_message("너무 많은 요청. 잠시 후 시도해주세요")
                return

        if not matches:
            await interaction.response.send_message("해당 소환사의 전적을 찾을 수 없습니다.")
            return

        select = discord.ui.Select(placeholder='전적을 선택하세요')

        try:
            player_stats_list = await asyncio.to_thread(fetch_all_match_info, matches, puuid)
        except NotFoundError as e:
            await interaction.response.send_message("404 에러: 전적 세부정보를 찾을 수 없습니다")
            return
        # player_stats_list를 이용해 이후의 로직 수행

        i = 1
        for player_stats in player_stats_list:
            # 플레이어의 K/D/A, 챔피언 이름, 승리 여부 정보를 메시지에 추가
            match_info = ""
            match_info += f"{'승리' if player_stats['Win'] else '패배'}"
            match_info += f" {player_stats['Champion']} "
            match_info += f"{player_stats['Position']}"
            match_kda = f"KDA: {player_stats['Kills']}/{player_stats['Deaths']}/{player_stats['Assists']} "

            select.add_option(label= match_info,value = i,description=match_kda)
            i += 1

        view = discord.ui.View()
        view.add_item(select)
        async def select_type(interaction2: Interaction):
            match_location = select.values[0]
            type_view = discord.ui.View()
            type_select = discord.ui.Select(placeholder='분석할 정보를 선택하세요')
            type_select.add_option(label= "핑 정보",value = 1,description="얼마나 핑을 사용했는 지 분석합니다")
            type_select.add_option(label= "시야 정보",value = 2,description="시야에 관련된 정보를 분석합니다")
            type_select.add_option(label= "정글링 정보",value = 3,description="정글링에 관련된 정보를 분석합니다")
            type_select.add_option(label= "성장 정보",value = 4, description="성장에 관련된 정보를 분석합니다")
            type_view.add_item(type_select)

            async def select_analysis(interaction3: Interaction):
                if int(type_select.values[0]) == 1:
                    match_id = matches[int(match_location)-1]
                    data = await get_summoner_matchinfo(match_id)
                    participant_id = get_participant_id(data,puuid)
                    gameData = data['info']['participants'][participant_id]

                    selected_user_nickname = interaction.user.display_name
                    for player in data['info']['participants']:
                        if puuid == player['puuid']:
                            player_stats = {
                                'Kills': player['kills'],
                                'Deaths': player['deaths'],
                                'Assists': player['assists'],
                                'Champion': player['championName'],
                                'Position': player['individualPosition'],
                                'Win': player['win']
                            }

                    seconds = data['info']['gameDuration']
                    game_duration = seconds_to_minutes_and_seconds(seconds)

                    # Embed 생성
                    basecolor = 0x00ff00 if player_stats['Win'] else 0xff0000
                    embed = discord.Embed(title=f'{selected_user_nickname}이(가) 요청한 {RNAME}의 핑 정보', color = basecolor)
                    embed.add_field(name="승/패", value="승리" if player_stats['Win'] else "패배", inline=True)
                    embed.add_field(name="챔피언", value=player_stats['Champion'], inline=True)
                    embed.add_field(name="KDA", value=f"{player_stats['Kills']}/{player_stats['Deaths']}/{player_stats['Assists']}", inline=True)
                    embed.add_field(name="게임 시간", value=game_duration, inline=True)
                    embed.add_field(name="포지션", value=player_stats['Position'])
                    embed.add_field(name="기본 핑", value=gameData['basicPings'], inline=True)
                    embed.add_field(name="갑니다 핑", value=gameData['onMyWayPings'], inline=True)
                    embed.add_field(name="지원 핑", value=gameData['assistMePings'], inline=True)
                    embed.add_field(name="미아 핑", value=gameData['enemyMissingPings'], inline=True)
                    embed.add_field(name="위험 핑", value=gameData['dangerPings'], inline=True)
                    embed.add_field(name="적 시야 핑", value=gameData['enemyVisionPings'], inline=True)
                    embed.add_field(name="후퇴 핑", value=gameData['getBackPings'], inline=True)
                    embed.add_field(name="홀드 핑", value=gameData['holdPings'], inline=True)
                    embed.add_field(name="시야 필요 핑", value=gameData['needVisionPings'], inline=True)
                    embed.add_field(name="총공격 핑", value=gameData['allInPings'], inline=True)
                    embed.add_field(name="압박 핑", value=gameData['pushPings'], inline=True)


                    #await interaction.response.send_message(f"```\n{match_data}\n```")
                    await interaction3.response.send_message(embed=embed)
                elif int(type_select.values[0]) == 2:
                    match_id = matches[int(match_location)-1]
                    data = await get_summoner_matchinfo(match_id)
                    participant_id = get_participant_id(data,puuid)
                    gameData = data['info']['participants'][participant_id]

                    selected_user_nickname = interaction.user.display_name
                    for player in data['info']['participants']:
                        if puuid == player['puuid']:
                            player_stats = {
                                'Kills': player['kills'],
                                'Deaths': player['deaths'],
                                'Assists': player['assists'],
                                'Champion': player['championName'],
                                'Position': player['individualPosition'],
                                'Win': player['win']
                            }

                    seconds = data['info']['gameDuration']
                    game_duration = seconds_to_minutes_and_seconds(seconds)

                    # Embed 생성
                    basecolor = 0x00ff00 if player_stats['Win'] else 0xff0000
                    embed = discord.Embed(title=f'{selected_user_nickname}이(가) 요청한 {RNAME}의 시야 정보', color = basecolor)
                    embed.add_field(name="승/패", value="승리" if player_stats['Win'] else "패배", inline=True)
                    embed.add_field(name="챔피언", value=player_stats['Champion'], inline=True)
                    embed.add_field(name="KDA", value=f"{player_stats['Kills']}/{player_stats['Deaths']}/{player_stats['Assists']}", inline=True)
                    embed.add_field(name="게임 시간", value=game_duration, inline=True)
                    embed.add_field(name="포지션", value=player_stats['Position'])
                    embed.add_field(name="제어 와드 설치", value=gameData['challenges']['controlWardsPlaced'], inline=True)
                    embed.add_field(name="투명 와드 설치", value=gameData['challenges']['stealthWardsPlaced'], inline=True)
                    embed.add_field(name="제거한 와드", value=gameData['challenges']['wardTakedowns'], inline=False)
                    embed.add_field(name="20분전 제거한 와드", value=gameData['challenges']['wardsGuarded'], inline=False)
                    embed.add_field(name="지킨 와드", value=gameData['challenges']['epicMonsterStolenWithoutSmite'], inline=False)
                    embed.add_field(name="시야 점수", value=gameData['visionScore'], inline=False)
                    embed.add_field(name="분당 시야 점수", value=gameData['challenges']['visionScorePerMinute'], inline=False)
                    embed.add_field(name="맞라이너 대비 시야점수", value=str(round(gameData['challenges']['visionScoreAdvantageLaneOpponent']*100,2)) + "%", inline=False)
                    embed.add_field(name="적 시야 핑", value=gameData['enemyVisionPings'], inline=False)
                    embed.add_field(name="시야 필요 핑", value=gameData['needVisionPings'], inline=False)
                    embed.add_field(name="시야 확보 핑", value=gameData['visionClearedPings'], inline=False)

                    await interaction3.response.send_message(embed=embed)
                elif int(type_select.values[0]) == 3:
                    match_id = matches[int(match_location)-1]
                    data = await get_summoner_matchinfo(match_id)
                    participant_id = get_participant_id(data,puuid)
                    gameData = data['info']['participants'][participant_id]

                    if participant_id >= 5:
                        team_id = 1
                        oppsite_team_id = 0
                    else:
                        team_id = 0
                        oppsite_team_id = 1


                    baronkills = data['info']['teams'][team_id]['objectives']['baron']['kills']
                    baronkilled = data['info']['teams'][oppsite_team_id]['objectives']['baron']['kills']
                    dragonkills = data['info']['teams'][team_id]['objectives']['dragon']['kills']
                    dragonkilled = data['info']['teams'][oppsite_team_id]['objectives']['dragon']['kills']
                    riftHeraldkills = data['info']['teams'][team_id]['objectives']['riftHerald']['kills']
                    riftHeraldkilled = data['info']['teams'][oppsite_team_id]['objectives']['riftHerald']['kills']
                    if 'horde' in data['info']['teams'][team_id]['objectives']:
                        lavakills = data['info']['teams'][team_id]['objectives']['horde']['kills']
                        lavakilled = data['info']['teams'][oppsite_team_id]['objectives']['horde']['kills']
                    else:
                        lavakills = -1
                        lavakilled = -1


                    selected_user_nickname = interaction.user.display_name
                    for player in data['info']['participants']:
                        if puuid == player['puuid']:
                            player_stats = {
                                'Kills': player['kills'],
                                'Deaths': player['deaths'],
                                'Assists': player['assists'],
                                'Champion': player['championName'],
                                'Position': player['individualPosition'],
                                'Win': player['win']
                            }
                        if player['individualPosition'] == gameData['individualPosition'] and puuid != player['puuid']:
                            oppsite_player_stats = {
                                'MoreEnemyJungle' : round(player['challenges']['moreEnemyJungleThanOpponent'],2),
                                'jungleCsBefore10Minutes' : round(player['challenges']['jungleCsBefore10Minutes'],0),
                                'epicMonsterSteals' : player['challenges']['epicMonsterSteals'],
                                'epicMonsterStolenWithoutSmite' : player['challenges']['epicMonsterStolenWithoutSmite']
                            }

                    seconds = data['info']['gameDuration']
                    game_duration = seconds_to_minutes_and_seconds(seconds)


                    # Embed 생성
                    basecolor = 0x00ff00 if player_stats['Win'] else 0xff0000
                    embed = discord.Embed(title=f'{selected_user_nickname}이(가) 요청한 {RNAME}의 정글링 정보', color = basecolor)
                    embed.add_field(name="승/패", value="승리" if player_stats['Win'] else "패배", inline=True)
                    embed.add_field(name="챔피언", value=player_stats['Champion'], inline=True)
                    embed.add_field(name="KDA", value=f"{player_stats['Kills']}/{player_stats['Deaths']}/{player_stats['Assists']}", inline=True)
                    embed.add_field(name="게임 시간", value=game_duration, inline=True)
                    embed.add_field(name="아군 정글 몹 처치", value=gameData['challenges']['alliedJungleMonsterKills'], inline=True)
                    embed.add_field(name="적 정글 몹 처치", value=gameData['challenges']['enemyJungleMonsterKills'], inline=True)
                    embed.add_field(name="바론", value=baronkills, inline=True)
                    embed.add_field(name="드래곤", value=dragonkills, inline=True)
                    embed.add_field(name="전령", value=riftHeraldkills, inline=True)
                    embed.add_field(name="적 바론", value=baronkilled, inline=True)
                    embed.add_field(name="적 드래곤", value=dragonkilled, inline=True)
                    embed.add_field(name="적 전령", value=riftHeraldkilled, inline=True)
                    if lavakills and lavakilled != -1:
                        embed.add_field(name="공허 유충", value=lavakills, inline=True)
                        embed.add_field(name="적 공허 유충", value=lavakilled, inline=True)
                    embed.add_field(name="스틸한 에픽 몬스터", value=gameData['challenges']['epicMonsterSteals'], inline=False)
                    embed.add_field(name="스틸당한 에픽 몬스터", value=oppsite_player_stats['epicMonsterSteals'], inline=False)
                    embed.add_field(name="강타 없이 스틸한 에픽 몬스터", value=gameData['challenges']['epicMonsterStolenWithoutSmite'], inline=False)
                    embed.add_field(name="강타 없이 스틸당한 에픽 몬스터", value=oppsite_player_stats['epicMonsterStolenWithoutSmite'], inline=False)
                    embed.add_field(name="첫 바위게 먹은 개수(최대 2)", value=gameData['challenges']['initialCrabCount'], inline=False)
                    embed.add_field(name="10분 이전 정글 몹으로만 cs", value=round(gameData['challenges']['jungleCsBefore10Minutes'],0), inline=False)
                    embed.add_field(name="적 정글의 10분 이전 정글 몹으로만 cs", value=oppsite_player_stats['jungleCsBefore10Minutes'], inline=False)
                    embed.add_field(name="10분 이전 먹은 라인 cs", value=round(gameData['challenges']['laneMinionsFirst10Minutes'],0), inline=False)
                    embed.add_field(name="적 정글 침범 지수", value=round(gameData['challenges']['moreEnemyJungleThanOpponent'],2), inline=True)
                    embed.add_field(name="아군 정글 침범 지수", value=oppsite_player_stats['MoreEnemyJungle'], inline=True)

                    await interaction3.response.send_message(embed=embed)
                elif int(type_select.values[0]) == 4:
                    match_id = matches[int(match_location)-1]
                    data = await get_summoner_matchinfo(match_id)
                    participant_id = get_participant_id(data,puuid)
                    gameData = data['info']['participants'][participant_id]



                    selected_user_nickname = interaction.user.display_name
                    for player in data['info']['participants']:
                        if puuid == player['puuid']:
                            player_stats = {
                                'Kills': player['kills'],
                                'Deaths': player['deaths'],
                                'Assists': player['assists'],
                                'Champion': player['championName'],
                                'Position': player['individualPosition'],
                                'Win': player['win']
                            }
                        if player['individualPosition'] == gameData['individualPosition'] and puuid != player['puuid']:
                            oppsite_player_stats = {
                                'MaxCsGap' : round(player['challenges']['maxCsAdvantageOnLaneOpponent'],1),
                                'MaxLvGap' : player['challenges']['maxLevelLeadLaneOpponent'],
                                'SoloKill' : player['challenges']['soloKills'],
                                'TurretPlate' : player['challenges']['turretPlatesTaken'],
                                '10minCs' : player['challenges']['laneMinionsFirst10Minutes']
                            }

                    seconds = data['info']['gameDuration']
                    game_duration = seconds_to_minutes_and_seconds(seconds)
                    # Embed 생성
                    basecolor = 0x00ff00 if player_stats['Win'] else 0xff0000
                    embed = discord.Embed(title=f'{selected_user_nickname}이(가) 요청한 {RNAME}의 성장 정보', color = basecolor)
                    embed.add_field(name="승/패", value="승리" if player_stats['Win'] else "패배", inline=True)
                    embed.add_field(name="챔피언", value=player_stats['Champion'], inline=True)
                    embed.add_field(name="KDA", value=f"{player_stats['Kills']}/{player_stats['Deaths']}/{player_stats['Assists']}", inline=True)
                    embed.add_field(name="게임 시간", value=game_duration, inline=True)
                    embed.add_field(name="챔피언 레벨", value=gameData['champLevel'], inline=True)
                    embed.add_field(name="포지션", value=player_stats['Position'])
                    embed.add_field(name="획득 골드", value=gameData['goldEarned'], inline=True)
                    embed.add_field(name="사용 골드", value=gameData['goldSpent'], inline=True)
                    embed.add_field(name="분당 골드", value=round(int(gameData['challenges']['goldPerMinute']),2), inline=True)
                    embed.add_field(name="10분 이전 먹은 라인 cs", value=gameData['challenges']['laneMinionsFirst10Minutes'], inline=False)
                    embed.add_field(name="상대가 10분 이전 먹은 라인 cs", value=oppsite_player_stats['10minCs'], inline=False)
                    embed.add_field(name="미니언 처치 횟수", value=gameData['totalMinionsKilled'], inline=False)
                    embed.add_field(name="최고로 낸 cs차이", value=round(gameData['challenges']['maxCsAdvantageOnLaneOpponent'],1), inline=False)
                    embed.add_field(name="최고로 난 cs차이", value=oppsite_player_stats['MaxCsGap'], inline=False)
                    embed.add_field(name="최고로 낸 레벨차이", value=gameData['challenges']['maxLevelLeadLaneOpponent'], inline=False)
                    embed.add_field(name="최고로 난 레벨차이", value=oppsite_player_stats['MaxLvGap'], inline=False)
                    embed.add_field(name="적 포탑 근처에서 킬", value=gameData['challenges']['killsNearEnemyTurret'], inline=False)
                    embed.add_field(name="아군 포탑 근처에서 킬", value=gameData['challenges']['killsUnderOwnTurret'], inline=False)
                    embed.add_field(name="팀 내 넣은 데미지 비율", value=f"{round(gameData['challenges']['teamDamagePercentage']*100,1)}%", inline=False)
                    embed.add_field(name="팀 내 받은 데미지 비율", value=f"{round(gameData['challenges']['damageTakenOnTeamPercentage']*100,1)}%", inline=False)
                    embed.add_field(name="솔로킬", value=gameData['challenges']['soloKills'], inline=False)
                    embed.add_field(name="상대 솔로킬", value=oppsite_player_stats['SoloKill'], inline=False)
                    embed.add_field(name="획득한 포탑 방패", value=gameData['challenges']['turretPlatesTaken'], inline=False)
                    embed.add_field(name="뺏긴 포탑 방패", value=oppsite_player_stats['TurretPlate'], inline=False)

                    #await interaction.response.send_message(f"```\n{match_data}\n```")
                    await interaction3.response.send_message(embed=embed)
            type_select.callback = select_analysis
            embed = discord.Embed(title=f'{RNAME}#{TLINE}의 {league_type} {int(match_location) + FROMNUM}번째 게임에서 분석할 정보', color = 0x000000)
            await interaction2.response.send_message(view=type_view, embed = embed)


        select.callback = select_type

        embed = discord.Embed(title=f'{RNAME}#{TLINE}의 전적 목록({league_type})', color = 0x000000)
        await interaction.response.send_message(view=view, embed = embed)

    @app_commands.command(name="트름범인",description="누구인가?")
    async def 트름범인(self,interaction: discord.Interaction):
        print(f"{interaction.user}가 요청한 트름범인 요쳥 수행")
        # 필터링할 봇들의 사용자 이름 리스트
        excluded_bots = ['TTS Bot', '술팽봇', '뽀삐']
        if interaction.user.voice is not None:
            voice_channel = interaction.user.voice.channel
            voice_members = voice_channel.members
            eligible_members = [member for member in voice_members if member.name not in excluded_bots]
            if eligible_members:
                chosen_member = random.choice(eligible_members)
                mention_message = f"<@{chosen_member.id}>!, 너가 범인이야!"
                await interaction.response.send_message(mention_message)
        else:
            await interaction.response.send_message("음성 채널에 연결되어 있지 않습니다!")

    @app_commands.command(name="연승",description="연승 횟수를 보여줍니다")
    @app_commands.describe(닉네임='소환사 닉네임',태그='소환사 태그 ex)KR1')
    async def 연승(self, interaction: discord.Interaction, 닉네임:str, 태그:str):
        print(f"{interaction.user}가 요청한 연승 요청 수행")
        RNAME = 닉네임
        TLINE = 태그
        RNAME = RNAME.strip()
        TLINE = TLINE.strip()
        print(f'RNAME : {RNAME}, TLINE : {TLINE}')

        try:
            puuid = await get_summoner_puuid(RNAME, TLINE)
        except NotFoundError as e:
            await interaction.response.send_message("해당 소환사를 찾을 수 없습니다.")
            return

        try:
            win_streak = await calculate_consecutive_wins(puuid)
            print(win_streak)
        except NotFoundError as e:
            await interaction.response.send_message(f"전적 정보를 찾을 수 없습니다.")
            return
        except TooManyRequestError as e:
            await interaction.response.send_message(f"너무 많은 요청. 잠시 후 다시 시도해주세요.")
            return

        if win_streak > 0:
            await interaction.response.send_message(f"{RNAME}의 현재 연승 횟수: {win_streak}연승")
        elif win_streak == 0:
            await interaction.response.send_message(f"{RNAME}은(는) 연승 중이 아닙니다.")
        else:
            await interaction.response.send_message('잠시 후에 다시 시도해주세요')

    @app_commands.command(name="연패",description="연패 횟수를 보여줍니다")
    @app_commands.describe(닉네임='소환사 닉네임',태그='소환사 태그 ex)KR1')
    async def 연패(self, interaction: discord.Interaction, 닉네임:str, 태그:str):
        print(f"{interaction.user}가 요청한 연패 요청 수행")
        RNAME = 닉네임
        TLINE = 태그
        RNAME = RNAME.strip()
        TLINE = TLINE.strip()
        print(f'RNAME : {RNAME}, TLINE : {TLINE}')
        puuid = await get_summoner_puuid(RNAME, TLINE)

        try:
            puuid = await get_summoner_puuid(RNAME, TLINE)
        except NotFoundError as e:
            await interaction.response.send_message("해당 소환사를 찾을 수 없습니다.")
            return

        try:
            loss_streak = await calculate_consecutive_losses(puuid)
        except NotFoundError as e:
            await interaction.response.send_message(f"404 에러: 전적 데이터를 찾을 수 없습니다.")
            return
        except TooManyRequestError as e:
            await interaction.response.send_message(f'429 에러: 너무 많은 요청. 잠시 후 시도해주세요.')
            return

        if loss_streak > 0:
            await interaction.response.send_message(f"{RNAME}의 현재 연패 횟수: {loss_streak}연패")
        elif loss_streak == 0:
            await interaction.response.send_message(f"{RNAME}은(는) 연패 중이 아닙니다.")
        else:
            await interaction.response.send_message('잠시 후에 다시 시도해주세요')

    @app_commands.command(name="최근전적",description="최근 20경기의 전적을 보여줍니다")
    @app_commands.describe(닉네임='소환사 닉네임',태그='소환사 태그 ex)KR1')
    async def 최근전적(self, interaction: discord.Interaction, 닉네임:str, 태그:str):
        print(f"{interaction.user}가 요청한 최근전적 요청 수행")
        RNAME = 닉네임
        TLINE = 태그
        RNAME = RNAME.strip()
        TLINE = TLINE.strip()
        print(f'RNAME : {RNAME}, TLINE : {TLINE}')
        try:
            puuid = await get_summoner_puuid(RNAME, TLINE)
        except NotFoundError as e:
            await interaction.response.send_message("404 에러: 해당 소환사를 찾을 수 없습니다.")
            return

        try:
            wins, draw, losses = await calculate_consecutive_matches(puuid)
        except NotFoundError as e:
            await interaction.response.send_message(f'404 에러: 전적을 찾을 수 없습니다')
            return
        except TooManyRequestError as e:
            await interaction.response.send_message(f'429 에러: 요청이 너무 많음. 잠시 후 시도해주세요')
        winrate = round((wins/(wins+losses))*100,2)


        if draw != 0:
            await interaction.response.send_message(f'{RNAME}의 최근 20경기\n'
                        f'승: {wins}, 패: {losses}, 다시하기: {draw}, 승률: {winrate}%')

        else:
            await interaction.response.send_message(f'{RNAME}의 최근 20경기\n'
                        f'승: {wins}, 패: {losses}, 승률: {winrate}%')

    @app_commands.command(name="그래프",description="이번시즌 점수 변동 그래프를 보여줍니다")
    @app_commands.describe(이름="누구의 그래프를 볼지 선택하세요", 랭크="랭크 유형을 선택하세요 (기본값: 솔로랭크)")
    @app_commands.choices(이름=[
    Choice(name='강지모', value='지모'),
    Choice(name='Melon', value='Melon'),
    ])
    @app_commands.choices(랭크=[
    Choice(name='솔랭', value='솔로랭크'),
    Choice(name='자랭', value='자유랭크'),
    ])
    async def 그래프(self, interaction: discord.Interaction, 이름:str, 랭크:str = "솔로랭크"):
        print(f"{interaction.user}가 요청한 그래프 요청 수행 ({이름}, {랭크})")
        # LP 변동량 그래프 그리기
        await interaction.response.defer()  # Interaction을 유지
        returnVal = plot_lp_difference_firebase(name = 이름, rank = 랭크)
        
        if returnVal == -1:
            await interaction.response.send_message("해당 시즌 데이터가 존재하지 않습니다.")
            return
        # 그래프 이미지 파일을 Discord 메시지로 전송
        await interaction.followup.send(file=discord.File('lp_graph.png'))

    @app_commands.command(name="시즌그래프",description="시즌 점수 변동 그래프를 보여줍니다")
    @app_commands.describe(시즌 = "시즌을 선택하세요")
    @app_commands.choices(시즌=[
    Choice(name='시즌14-1', value='시즌14-1'),
    Choice(name='시즌14-2', value='시즌14-2'),
    Choice(name='시즌14-3', value='시즌14-3'),
    Choice(name='시즌15', value='시즌15')
    ])
    @app_commands.describe(이름='누구의 그래프를 볼지 선택하세요')
    @app_commands.choices(이름=[
    Choice(name='강지모', value='지모'),
    Choice(name='Melon', value='Melon'),
    ])
    @app_commands.choices(랭크=[
    Choice(name='솔랭', value='솔로랭크'),
    Choice(name='자랭', value='자유랭크'),
    ])
    async def 시즌그래프(self, interaction: discord.Interaction, 이름:str, 시즌:str, 랭크:str = "솔로랭크"):
        print(f"{interaction.user}가 요청한 시즌그래프 요청 수행")
        # LP 변동량 그래프 그리기
        await interaction.response.defer()  # Interaction을 유지
        returnVal = plot_lp_difference_firebase(season = 시즌, name = 이름, rank = 랭크)

        if returnVal == -1:
            await interaction.response.send_message("해당 시즌 데이터가 존재하지 않습니다.")
            return
        else:
            # 그래프 이미지 파일을 Discord 메시지로 전송
            await interaction.followup.send(file=discord.File('lp_graph.png'))

    @app_commands.command(name="시즌종료",description="시즌 종료까지 남은 날짜")
    async def 시즌종료(self, interaction: discord.Interaction):
        print(f"{interaction.user}가 요청한 시즌종료 요청 수행")
        # 현재 날짜 및 시간 가져오기
        current_datetime = datetime.now()

        # 시간 차이 계산
        time_difference = SEASON_CHANGE_DATE15 - current_datetime

        # 시간 차이를 한글로 변환하여 출력
        days = time_difference.days
        hours, remainder = divmod(time_difference.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        output = ""
        if days:
            output += f"{days}일 "
        if hours:
            output += f"{hours}시간 "
        if minutes:
            output += f"{minutes}분 "
        if seconds:
            output += f"{seconds}초"

        if time_difference.total_seconds() < 0:
            await interaction.response.send_message("시즌 15가 종료되었습니다.")
        else:
            # 시간 차이 출력 (일, 시간, 분, 초)
            await interaction.response.send_message(f"시즌종료까지 남은 시간: {output}")

    @app_commands.command(name="점수",description="현재 소환사의 점수를 보여줍니다")
    @app_commands.describe(닉네임='소환사 닉네임',태그='소환사 태그 ex)KR1',리그='리그를 선택하세요')
    @app_commands.choices(리그=[
    Choice(name='솔랭', value='솔랭'),
    Choice(name='자랭', value='자랭'),
    ])
    async def 점수(self,interaction: discord.Interaction, 닉네임:str, 태그:str, 리그:str):
        print(f"{interaction.user}가 요청한 점수 요청 수행")
        RNAME = 닉네임
        TLINE = 태그
        RNAME = RNAME.strip()
        TLINE = TLINE.strip()
        puuid = await get_summoner_puuid(RNAME, TLINE)
        id = await get_summoner_id(puuid)
        rank = await get_summoner_ranks(id,리그)
        if rank == []:
            await interaction.response.send_message("해당 리그의 전적을 찾을 수 없습니다.")
            return
        else:
            wins = rank["wins"]
            losses = rank["losses"]
            winrate = round((wins / (wins + losses))* 100,2)
            await interaction.response.send_message(f'{RNAME}의 {리그}전적\n'
                            f'{rank["tier"]} {rank["rank"]} {rank["leaguePoints"]}LP\n'
                           f'{wins}승 {losses}패 승률 {winrate}%')

    @app_commands.command(name="캔들그래프",description="이번시즌 점수를 캔들그래프로 보여줍니다")
    @app_commands.describe(이름='누구의 그래프를 볼지 선택하세요')
    @app_commands.choices(이름=[
    Choice(name='강지모', value='지모'),
    Choice(name='Melon', value='Melon'),
    ])
    @app_commands.choices(랭크=[
    Choice(name='솔랭', value='솔로랭크'),
    Choice(name='자랭', value='자유랭크'),
    ])
    async def 캔들그래프(self, interaction: discord.Interaction,이름:str, 랭크:str = "솔로랭크"):
        # 현재 시즌 정보 가져오기
        curseasonref = db.reference("전적분석/현재시즌")
        current_season = curseasonref.get()
        season = current_season
        await interaction.response.defer()  # Interaction을 유지
        result = await plot_candle_graph(season,이름,랭크)
        if result == None:
            await interaction.response.send_message("해당 시즌 데이터가 존재하지 않습니다.")
            return
        
        # 그래프 이미지 파일을 Discord 메시지로 전송
        await interaction.followup.send(file=discord.File('candle_graph.png'),embed = result)

    @app_commands.command(name="시즌캔들그래프",description="시즌 점수를 캔들그래프로 보여줍니다")
    @app_commands.describe(시즌 = "시즌을 선택하세요",이름='누구의 그래프를 볼지 선택하세요')
    @app_commands.choices(시즌=[
    Choice(name='시즌14-1', value='시즌14-1'),
    Choice(name='시즌14-2', value='시즌14-2'),
    Choice(name='시즌14-3', value='시즌14-3'),
    Choice(name='시즌15', value='시즌15')
    ])
    @app_commands.choices(이름=[
    Choice(name='강지모', value='지모'),
    Choice(name='Melon', value='Melon'),
    ])
    async def 시즌캔들그래프(self, interaction: discord.Interaction, 이름:str,시즌:str, 랭크:str = "솔로랭크"):
        
        await interaction.response.defer()  # Interaction을 유지
        result = await plot_candle_graph(시즌,이름,랭크)
        if result == None:
            await interaction.response.send_message("해당 시즌 데이터가 존재하지 않습니다.")
            return
        
        # 그래프 이미지 파일을 Discord 메시지로 전송
        await interaction.followup.send(file=discord.File('candle_graph.png'),embed = result)

    @app_commands.command(name="예측순위",description="승부예측 포인트 순위를 보여줍니다")
    @app_commands.describe(시즌 = "시즌을 선택하세요")
    @app_commands.choices(시즌=[
    Choice(name='예측시즌 1', value='예측시즌1'),
    Choice(name='예측시즌 2', value='예측시즌2'),
    Choice(name='예측시즌 3', value='예측시즌3'),
    Choice(name='정규시즌 1', value='정규시즌1')
    ])
    async def 예측순위(self, interaction: discord.Interaction, 시즌:str):
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
        current_predict_season = cur_predict_seasonref.get()
        if 시즌 == current_predict_season:
            today = datetime.today()
            '''
            if today.weekday() != 6:
                embed = discord.Embed(title=f'비공개', color = discord.Color.blue())
                embed.add_field(name=f"", value=f"최신 시즌 순위표는 비공개입니다!", inline=False)
                await interaction.response.send_message(embed=embed,ephemeral=True)
            '''
            embed = discord.Embed(title=f'비공개', color = discord.Color.blue())
            embed.add_field(name=f"", value=f"최신 시즌 순위표는 비공개입니다!", inline=False)
            pointref = db.reference("승부예측/혼자보기포인트")
            need_point = pointref.get()
            see1button = discord.ui.Button(style=discord.ButtonStyle.success,label=f"순위표 혼자보기({need_point} 포인트)")
            see2button = discord.ui.Button(style=discord.ButtonStyle.primary,label="순위표 같이보기(500 포인트)")
            view = discord.ui.View()
            view.add_item(see1button)
            view.add_item(see2button)
            
            async def see1button_callback(interaction:discord.Interaction): # 순위표 버튼을 눌렀을 때의 반응!
                cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                current_predict_season = cur_predict_seasonref.get()
                refp = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{interaction.user.name}')
                originr = refp.get()
                point = originr["포인트"]
                bettingPoint = originr["베팅포인트"]
                if point - bettingPoint < need_point:
                    await interaction.response.send_message(f"포인트가 부족합니다! 현재 포인트: {point - bettingPoint} (베팅포인트 {bettingPoint} 제외)",ephemeral=True)
                else:
                    refp.update({"포인트" : point - need_point})
                    refhon = db.reference('승부예측')
                    refhon.update({"혼자보기포인트" : need_point + 50})
                    ref = db.reference(f'승부예측/예측시즌/{시즌}/예측포인트')
                    points = ref.get()

                    # 점수를 기준으로 내림차순으로 정렬
                    sorted_data = sorted(points.items(), key=lambda x: x[1]['포인트'], reverse=True)

                    # 상위 명을 추출하여 출력
                    top = sorted_data[:]

                    embed = discord.Embed(title=f'승부예측 순위', color = discord.Color.blue())

                    for idx, (username, info) in enumerate(top, start=1):
                        if info['연승'] > 0:
                            embed.add_field(name=f"{idx}. {username}", value=f"연속적중 {info['연승']}, 포인트 {info['포인트']}, 적중률 {info['적중률']}({info['적중 횟수']}/{info['총 예측 횟수']}), ", inline=False)
                        elif info['연패'] > 0:
                            embed.add_field(name=f"{idx}. {username}", value=f"연속비적중 {info['연패']}, 포인트 {info['포인트']}, 적중률 {info['적중률']}({info['적중 횟수']}/{info['총 예측 횟수']}), ", inline=False)
                        else:
                            embed.add_field(name=f"{idx}. {username}", value=f"포인트 {info['포인트']}, 적중률 {info['적중률']}({info['적중 횟수']}/{info['총 예측 횟수']}), ", inline=False)

                    userembed = discord.Embed(title=f"알림", color=discord.Color.light_gray())
                    userembed.add_field(name="",value=f"{interaction.user.name}님이 {need_point}포인트를 소모하여 순위표를 열람했습니다! (현재 열람 포인트 : {need_point + 50}(+ 50))", inline=False)
                
                    await interaction.response.send_message(embed=embed,ephemeral=True)

            async def see2button_callback(interaction:discord.Interaction): # 순위표 버튼을 눌렀을 때의 반응!
                cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                current_predict_season = cur_predict_seasonref.get()
                refp = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{interaction.user.name}')
                originr = refp.get()
                point = originr["포인트"]
                bettingPoint = originr["베팅포인트"]
                need_point = 500
                if point - bettingPoint < need_point:
                    await interaction.response.send_message(f"포인트가 부족합니다! 현재 포인트: {point - bettingPoint} (베팅포인트 {bettingPoint} 제외)",ephemeral=True)
                else:
                    await interaction.response.defer()  # 응답 지연 처리
                    refp.update({"포인트" : point - need_point})
                    ref = db.reference(f'승부예측/예측시즌/{시즌}/예측포인트')
                    points = ref.get()

                    # 점수를 기준으로 내림차순으로 정렬
                    sorted_data = sorted(points.items(), key=lambda x: x[1]['포인트'], reverse=True)

                    # 상위 명을 추출하여 출력
                    top = sorted_data[:]

                    embed = discord.Embed(title=f'승부예측 순위', color = discord.Color.blue())

                    for idx, (username, info) in enumerate(top, start=1):
                        if info['연승'] > 0:
                            embed.add_field(name=f"{idx}. {username}", value=f"연속적중 {info['연승']}, 포인트 {info['포인트']}, 적중률 {info['적중률']}({info['적중 횟수']}/{info['총 예측 횟수']}), ", inline=False)
                        elif info['연패'] > 0:
                            embed.add_field(name=f"{idx}. {username}", value=f"연속비적중 {info['연패']}, 포인트 {info['포인트']}, 적중률 {info['적중률']}({info['적중 횟수']}/{info['총 예측 횟수']}), ", inline=False)
                        else:
                            embed.add_field(name=f"{idx}. {username}", value=f"포인트 {info['포인트']}, 적중률 {info['적중률']}({info['적중 횟수']}/{info['총 예측 횟수']}), ", inline=False)

                    notice_channel = interaction.client.get_channel(1332330634546253915)
                    channel = self.bot.get_channel(int(CHANNEL_ID))
                    userembed = discord.Embed(title=f"알림", color=discord.Color.light_gray())
                    userembed.add_field(name="",value=f"{interaction.user.name}님이 {need_point}포인트를 소모하여 순위표를 전체 열람했습니다!", inline=False)
                    await notice_channel.send("@everyone\n", embed=embed)
                    # ====================  [미션]  ====================
                    # 시즌미션 : 내가 보여주는 미래
                    cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                    current_predict_season = cur_predict_seasonref.get()
                    ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{interaction.user.name}/미션/시즌미션/내가 보여주는 미래")
                    mission_bool = ref.get()['완료']
                    if not mission_bool:
                        ref.update({"완료": True})
                        print(f"{interaction.user.name}의 [내가 보여주는 미래] 미션 완료")
                        await mission_notice(interaction.client,interaction.user.name, "내가 보여주는 미래")
                    # ====================  [미션]  ====================

                    await interaction.followup.send(embed = userembed)

            see1button.callback = see1button_callback
            see2button.callback = see2button_callback

            await interaction.response.send_message(view = view,embed=embed,ephemeral=True)
        else:
            ref = db.reference(f'승부예측/예측시즌/{시즌}/예측포인트')
            points = ref.get()

            # 점수를 기준으로 내림차순으로 정렬
            sorted_data = sorted(points.items(), key=lambda x: x[1]['포인트'], reverse=True)

            # 상위 명을 추출하여 출력
            top = sorted_data[:]

            embed = discord.Embed(title=f'승부예측 순위', color = discord.Color.blue())

            for idx, (username, info) in enumerate(top, start=1):
                if info['연승'] > 0:
                    embed.add_field(name=f"{idx}. {username}", value=f"연속적중 {info['연승']}, 포인트 {info['포인트']}, 적중률 {info['적중률']}({info['적중 횟수']}/{info['총 예측 횟수']}), ", inline=False)
                elif info['연패'] > 0:
                    embed.add_field(name=f"{idx}. {username}", value=f"연속비적중 {info['연패']}, 포인트 {info['포인트']}, 적중률 {info['적중률']}({info['적중 횟수']}/{info['총 예측 횟수']}), ", inline=False)
                else:
                    embed.add_field(name=f"{idx}. {username}", value=f"포인트 {info['포인트']}, 적중률 {info['적중률']}({info['적중 횟수']}/{info['총 예측 횟수']}), ", inline=False)
            await interaction.response.send_message(embed=embed)

    @app_commands.command(name='포인트',description="자신의 승부예측 포인트를 알려줍니다")
    async def 포인트(self, interaction: discord.Interaction):
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
        current_predict_season = cur_predict_seasonref.get()
        ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트')
        points = ref.get()

        # 점수를 기준으로 내림차순으로 정렬
        sorted_data = sorted(points.items(), key=lambda x: x[1]['포인트'], reverse=True)

        # 상위 명을 추출하여 출력
        top = sorted_data[:]

        embed = discord.Embed(title=f'{interaction.user.name}의 포인트', color = discord.Color.blue())

        for idx, (username, info) in enumerate(top, start=1):
            if username == interaction.user.name:
                embed.add_field(name='',value=f"{info['포인트']}포인트(베팅 포인트:{info['베팅포인트']})", inline=False)
                embed.add_field(name=f"{username}", value=f"연속적중 {info['연승']}, 포인트 {info['포인트']}, 적중률 {info['적중률']}({info['적중 횟수']}/{info['총 예측 횟수']}), ", inline=False)
                await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="온오프",description="투표기능 온오프(개발자 전용)")
    @app_commands.describe(값 = "값을 선택하세요")
    @app_commands.choices(값=[
    Choice(name='On', value="False"),
    Choice(name='Off', value="True"),
    ])
    async def 온오프(self, interaction: discord.Interaction, 값:str):
        if interaction.user.name == "toe_kyung":
            onoffref = db.reference("승부예측")
            if 값 == "True":
                onoffbool = True
            else:
                onoffbool = False
            onoffref.update({"투표온오프" : onoffbool})

            embed = discord.Embed(title=f'변경 완료', color = discord.Color.blue())
            embed.add_field(name=f"변경", value=f"투표 기능이 Off 되었습니다." if onoffbool else "투표 기능이 On 되었습니다.", inline=False)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("권한이 없습니다", ephemeral=True)

    @app_commands.command(name="익명온오프",description="익명투표기능 온오프(개발자 전용)")
    @app_commands.describe(값 = "값을 선택하세요")
    @app_commands.choices(값=[
    Choice(name='On', value="True"),
    Choice(name='Off', value="False"),
    ])
    async def 익명온오프(self, interaction: discord.Interaction, 값:str):
        if interaction.user.name == "toe_kyung":
            onoffref = db.reference("승부예측")
            if 값 == "True":
                onoffbool = True
            else:
                onoffbool = False
            onoffref.update({"익명온오프" : onoffbool})

            embed = discord.Embed(title=f'변경 완료', color = discord.Color.blue())
            embed.add_field(name=f"변경", value=f"익명투표 기능이 On 되었습니다." if onoffbool else "익명투표 기능이 Off 되었습니다.", inline=False)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("권한이 없습니다", ephemeral=True)

    @app_commands.command(name="정상화",description="점수 정상화(개발자 전용)")
    async def 정상화(self, interaction: discord.Interaction):
        if interaction.user.name == "toe_kyung":
            cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
            current_predict_season = cur_predict_seasonref.get()
            ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트변동로그')

            # timestamp 기준으로 정렬하고 마지막 데이터 하나만 가져오기
            snapshot = ref.order_by_key().get()

            latest_timestamp = None
            latest_log_data = None
            embed = discord.Embed(title=f'정상화 성공', color = discord.Color.blue())


            # 데이터가 존재하는지 확인
            if snapshot:
                for date, times in snapshot.items():
                    for time, log in times.items():
                        # 날짜와 시간을 결합하여 datetime 객체 생성
                        timestamp = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M:%S")

                        # 최신 타임스탬프 업데이트
                        if latest_timestamp is None or timestamp > latest_timestamp:
                            latest_timestamp = timestamp
                            latest_log_data = log

                if latest_log_data:
                    for name, log in latest_log_data.items():
                        ref2 = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{name}')
                        ref2.update({'포인트' : log['포인트']})
                        ref2.update({"총 예측 횟수": log["총 예측 횟수"]})
                        ref2.update({"적중 횟수" : log["적중 횟수"]})
                        ref2.update({"적중률": log["적중률"]})
                        ref2.update({"연승": log["연승"]})
                        ref2.update({"연패": log["연패"]})
                        embed.add_field(name=f"{name}", value= f"{name}의 점수 정상화", inline=False)

            else:
                print('로그 데이터가 없습니다.')

            ref3 = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트변동로그/{date}/{time}')
            ref3.delete()

            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("권한이 없습니다", ephemeral=True)

    @app_commands.command(name="군대",description="전역까지 남은 날짜를 알려줍니다")
    @app_commands.describe(이름 = "이름을 입력하세요")
    @app_commands.choices(이름=[
    Choice(name='강동윤', value='강동윤'),
    Choice(name='김동현', value='김동현'),
    ])
    async def 군대(self, interaction: discord.Interaction, 이름:str):
        outdate_DY = datetime(2026, 1, 28, 7, 0, 0)
        indate_DH = datetime(2024, 11, 4, 14, 0, 0)
        outdate_DH = datetime(2026, 5, 3, 7, 0, 0)

        current_datetime = datetime.now()

        if 이름 == '강동윤':
            # 시간 차이 계산
            time_difference = outdate_DY - current_datetime

            # 시간 차이를 한글로 변환하여 출력
            days = time_difference.days
            hours, remainder = divmod(time_difference.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            hours += days*24

            output = ""
            if hours:
                output += f"{hours}시간 "
            if minutes:
                output += f"{minutes}분 "
            if seconds:
                output += f"{seconds}초"

            await interaction.response.send_message(f"{이름} 전역까지 남은 시간: {output}")
        elif 이름 == '김동현':
            if current_datetime < indate_DH: # 입대하기 전
                # 시간 차이 계산
                time_difference = indate_DH - current_datetime
                목표 = '입대'
            else:
                # 시간 차이 계산
                time_difference = outdate_DH - current_datetime
                목표 = '전역'

            # 시간 차이를 한글로 변환하여 출력
            days = time_difference.days
            hours, remainder = divmod(time_difference.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            hours += days*24

            output = ""
            if hours:
                output += f"{hours}시간 "
            if minutes:
                output += f"{minutes}분 "
            if seconds:
                output += f"{seconds}초"

            await interaction.response.send_message(f"{이름} {목표}까지 남은 시간: {output}")

    @app_commands.command(name="베팅",description="승부예측에 걸 포인트를 설정합니다.")
    @app_commands.describe(이름 = "예측한 사람의 이름을 입력하세요", 포인트 = "베팅할 포인트를 선택하세요 (자연수만)")
    @app_commands.choices(이름=[
    Choice(name='지모', value='지모'),
    Choice(name='Melon', value='Melon'),
    ])
    async def 베팅(self, interaction: discord.Interaction, 이름:str, 포인트:int):
        anonymref = db.reference("승부예측/익명온오프")
        anonymbool = anonymref.get()
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
        current_predict_season = cur_predict_seasonref.get()

        async def handle_bet(winbutton):
            if 포인트 <= 0:
                await interaction.response.send_message("포인트는 0보다 큰 숫자로 입력해주세요",ephemeral=True)
                return
            if winbutton.disabled == True:
                await interaction.response.send_message(f"지금은 {이름}에게 베팅할 수 없습니다!",ephemeral=True)
                return

            nickname = interaction.user.name
            if (nickname not in [winner['name'] for winner in p.votes[이름]['prediction']['win']] and
            nickname not in [loser['name'] for loser in p.votes[이름]['prediction']['lose']]):
                await interaction.response.send_message(f"승부예측 후 이용해주세요",ephemeral=True)
            else:
                for winner in p.votes[이름]['prediction']['win']:
                    if winner['name'] == nickname:
                        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                        current_predict_season = cur_predict_seasonref.get()
                        ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{winner["name"]}')
                        ref2 = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{winner["name"]}/베팅포인트')
                        bettingPoint = ref2.get()
                        info = ref.get()

                        if info['포인트'] - bettingPoint < 포인트:
                            await interaction.response.send_message(f"포인트가 부족합니다!\n현재 포인트: {info['포인트'] - bettingPoint}(베팅 금액 {bettingPoint}P) 제외",ephemeral=True)
                        else:
                            winner['points'] += 포인트  # 포인트 수정
                            ref.update({"베팅포인트" : bettingPoint + 포인트}) # 파이어베이스에 베팅포인트 추가
                            userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                            if anonymbool:
                                await place_bet(self.bot,이름,"승리",포인트)
                                await interaction.response.send_message(f"{이름}의 승리에 {포인트}포인트 베팅 완료!",ephemeral=True)
                            else:
                                if winner['points'] != 포인트:
                                    userembed.add_field(name="",value=f"{nickname}님이 {이름}의 승리에 {포인트}포인트만큼 추가 베팅하셨습니다!", inline=True)
                                    await interaction.response.send_message(embed=userembed)
                                else:
                                    userembed.add_field(name="",value=f"{nickname}님이 {이름}의 승리에 {포인트}포인트만큼 베팅하셨습니다!", inline=True)
                                    await interaction.response.send_message(embed=userembed)

            
                            await refresh_prediction(이름,anonymbool,p.votes[이름]['prediction'])


                            
                            # ====================  [미션]  ====================
                            # 시즌미션 : 모든 것을 건 한방
                            
                            mref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{winner["name"]}')
                            mref2 = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{winner["name"]}/베팅포인트')
                            minfo = mref.get()
                            mbettingPoint = mref2.get()
                            mpoint = minfo['포인트']
                            if mpoint == mbettingPoint: # 포인트의 전부를 베팅포인트로 넣음
                                cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                                current_predict_season = cur_predict_seasonref.get()
                                ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname}/미션/시즌미션/모든 것을 건 한방")
                                mission_bool = ref.get()['완료']
                                if not mission_bool:
                                    ref.update({"완료": True})
                                    print(f"{nickname}의 [모든 것을 건 한방] 미션 완료")
                                    await mission_notice(interaction.client, nickname, "모든 것을 건 한방")
                            # ====================  [미션]  ====================
                            
                            return

                # 패배 예측에서 닉네임 찾기
                for loser in p.votes[이름]['prediction']['lose']:
                    if loser['name'] == nickname:
                        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                        current_predict_season = cur_predict_seasonref.get()
                        ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{loser["name"]}')
                        ref2 = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{loser["name"]}/베팅포인트')
                        bettingPoint = ref2.get()
                        info = ref.get()
    
                        if info['포인트'] - bettingPoint < 포인트:
                            await interaction.response.send_message(f"포인트가 부족합니다!\n현재 포인트: {info['포인트'] - bettingPoint}(베팅 금액 {bettingPoint}P) 제외",ephemeral=True)
                        else:
                            loser['points'] += 포인트  # 포인트 수정
                            ref.update({"베팅포인트" : bettingPoint + 포인트}) # 파이어베이스에 베팅포인트 추가
                            userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                            if anonymbool:
                                await place_bet(self.bot,이름,"패배",포인트)
                                await interaction.response.send_message(f"{이름}의 패배에 {포인트}포인트 베팅 완료!",ephemeral=True)
                            else:
                                if loser['points'] != 포인트:
                                    userembed.add_field(name="",value=f"{nickname}님이 {이름}의 패배에 {포인트}포인트만큼 추가 베팅하셨습니다!", inline=True)
                                    await interaction.response.send_message(embed=userembed)
                                else:
                                    userembed.add_field(name="",value=f"{nickname}님이 {이름}의 패배에 {포인트}포인트만큼 베팅하셨습니다!", inline=True)
                                    await interaction.response.send_message(embed=userembed)

                            await refresh_prediction(이름,anonymbool,p.votes[이름]['prediction'])

                            # ====================  [미션]  ====================
                            # 시즌미션 : 모든 것을 건 한방
                            
                            mref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{loser["name"]}')
                            mref2 = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{loser["name"]}/베팅포인트')
                            minfo = mref.get()
                            mbettingPoint = mref2.get()
                            mpoint = minfo['포인트']
                            if mpoint == mbettingPoint: # 포인트의 전부를 베팅포인트로 넣음
                                cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                                current_predict_season = cur_predict_seasonref.get()
                                ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname}/미션/시즌미션/모든 것을 건 한방")
                                mission_bool = ref.get()['완료']
                                if not mission_bool:
                                    ref.update({"완료": True})
                                    print(f"{nickname}의 [모든 것을 건 한방] 미션 완료")
                                    await mission_notice(interaction.client, nickname, "모든 것을 건 한방")
                            # ====================  [미션]  ====================

                            return

        if 이름 == "지모":
            await handle_bet(p.jimo_winbutton)
        elif 이름 == "Melon":
            await handle_bet(p.melon_winbutton)

    @app_commands.command(name="승리",description="베팅 승리판정(개발자 전용)")
    @app_commands.describe(이름 = "이름을 입력하세요", 포인트 = "얻을 포인트를 입력하세요", 배율 = "베팅 배율을 입력하세요", 베팅금액 = "베팅한 금액을 입력하세요", 대상 = "누구에게 예측 했는지 입력하세요", 승패 = "어느 결과를 예측했는지 입력하세요")
    @app_commands.choices(대상=[
    Choice(name='지모', value='지모'),
    Choice(name='Melon', value='Melon'),
    ])
    @app_commands.choices(승패=[
    Choice(name='승리', value='승리'),
    Choice(name='패배', value='패배'),
    ])
    async def 승리(self, interaction: discord.Interaction, 이름:str, 포인트:int, 배율:float, 베팅금액:int, 대상:str, 승패:str):
        userembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
        if interaction.user.name == "toe_kyung":
            cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
            current_predict_season = cur_predict_seasonref.get()
            point_ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{이름}')
            predict_data = point_ref.get()
            point = predict_data["포인트"]
            bettingPoint = predict_data["베팅포인트"]

            # 예측 내역 업데이트
            point_ref.update({
                "포인트": point,
                "총 예측 횟수": predict_data["총 예측 횟수"] + 1,
                "적중 횟수": predict_data["적중 횟수"] + 1,
                "적중률": f"{round((((predict_data['적중 횟수'] + 1) * 100) / (predict_data['총 예측 횟수'] + 1)), 2)}%",
                "연승": predict_data["연승"] + 1,
                "연패": 0,
                "베팅포인트": bettingPoint - 베팅금액,

                # 추가 데이터
                f"{대상}적중": predict_data.get(f"{대상}적중", 0) + 1,
                f"{대상}{승패}예측": predict_data.get(f"{대상}{승패}예측", 0) + 1,
                f"{승패}예측연속": predict_data.get(f"{승패}예측연속", 0) + 1
            })
            # ====================  [미션]  ====================
            # 시즌미션 : 대왕원숭이
            if predict_data.get("승리예측연속", 0) == 10:
                cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                current_predict_season = cur_predict_seasonref.get()
                ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{이름}/미션/시즌미션/대왕원숭이")
                mission_bool = ref.get()['완료']
                if not mission_bool:
                    ref.update({"완료": True})
                    print(f"{이름}의 [대왕원숭이] 미션 완료")
                    await mission_notice(interaction.client,이름,"대왕원숭이")

            # ====================  [미션]  ====================

            # ====================  [미션]  ====================
            # 시즌미션 : 대왕앵무
            if predict_data.get("패배예측연속", 0) == 10:
                cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                current_predict_season = cur_predict_seasonref.get()
                ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{이름}/미션/시즌미션/대왕앵무")
                mission_bool = ref.get()['완료']
                if not mission_bool:
                    ref.update({"완료": True})
                    print(f"{이름}의 [대왕앵무] 미션 완료")
                    await mission_notice(interaction.client,이름,"대왕앵무")

            # ====================  [미션]  ====================

            # ====================  [미션]  ====================
            # 시즌미션 : 지모의 충신
            if predict_data.get("지모승리예측", 0) == 30:
                cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                current_predict_season = cur_predict_seasonref.get()
                ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{이름}/미션/시즌미션/지모의 충신")
                mission_bool = ref.get()['완료']
                if not mission_bool:
                    ref.update({"완료": True})
                    print(f"{이름}의 [지모의 충신] 미션 완료")
                    await mission_notice(interaction.client,이름,"지모의 충신")    

            # ====================  [미션]  ====================

            # ====================  [미션]  ====================
            # 일일미션 : 승부예측 1회 적중
            cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
            current_predict_season = cur_predict_seasonref.get()
            ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{이름}/미션/일일미션/승부예측 1회 적중")
            mission_bool = ref.get()['완료']
            if not mission_bool:
                ref.update({"완료": True})
                print(f"{이름}의 [승부예측 1회 적중] 미션 완료")

            # ====================  [미션]  ====================


            # ====================  [미션]  ====================
            # 시즌미션 : 끝까지 가면 내가 다 이겨
            if predict_data["총 예측 횟수"] + 1 == 100:
                cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                current_predict_season = cur_predict_seasonref.get()
                ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{이름}/미션/시즌미션/끝까지 가면 내가 다 이겨")
                mission_bool = ref.get()['완료']
                if not mission_bool:
                    ref.update({"완료": True})
                    print(f"{이름}의 [끝까지 가면 내가 다 이겨] 미션 완료")
                    await mission_notice(interaction.client,이름,"끝까지 가면 내가 다 이겨")
            # ====================  [미션]  ====================


            win_streak = predict_data.get("연승",0) + 1
            if win_streak > 1:
                add_points = 포인트 + calculate_points(win_streak) + round(베팅금액*배율)
                userembed.add_field(name="",value=f"{이름}님이 {add_points}(베팅 보너스 + {round(베팅금액*배율)})(연속적중 보너스 + {calculate_points(win_streak)}) 점수를 획득하셨습니다! (베팅 포인트:{베팅금액})", inline=False)
                point_ref.update({"포인트": point + add_points - 베팅금액})
            else:
                add_points = 포인트 + round(베팅금액*배율)
                userembed.add_field(name="",value=f"{이름}님이 {add_points}(베팅 보너스 + {round(베팅금액*배율)}) 점수를 획득하셨습니다! (베팅 포인트:{베팅금액})", inline=False)
                point_ref.update({"포인트": point + add_points - 베팅금액})


            # ====================  [미션]  ====================
            # 시즌미션 : 신의 한 수
            if 배율 >= 3 and 베팅금액 >= 500:
                cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                current_predict_season = cur_predict_seasonref.get()
                ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{이름}/미션/시즌미션/신의 한 수")
                mission_bool = ref.get()['완료']
                if not mission_bool:
                    ref.update({"완료": True})
                    print(f"{이름}의 [신의 한 수] 미션 완료")
                    await mission_notice(interaction.client,이름,"신의 한 수")
            # ====================  [미션]  ====================

            await interaction.response.send_message(embed=userembed)
        else:
            print(f"{interaction.user.name}의 승리 명령어 요청")
            interaction.response.send_message("권한이 없습니다",ephemeral=True)

    @app_commands.command(name="패배",description="베팅 패배판정(개발자 전용)")
    @app_commands.describe(이름 = "이름을 입력하세요", 베팅금액 = "베팅한 금액을 입력하세요", 대상 = "누구에게 예측 했는지 입력하세요", 승패 = "어느 결과를 예측했는지 입력하세요")
    @app_commands.choices(대상=[
    Choice(name='지모', value='지모'),
    Choice(name='Melon', value='Melon'),
    ])
    @app_commands.choices(승패=[
    Choice(name='승리', value='승리'),
    Choice(name='패배', value='패배'),
    ])
    async def 패배(self, interaction: discord.Interaction, 이름:str, 베팅금액:int, 환급금액:int, 대상:str, 승패:str):
        userembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
        if interaction.user.name == "toe_kyung":
            cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
            current_predict_season = cur_predict_seasonref.get()
            point_ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{이름}')
            predict_data = point_ref.get()
            point = predict_data["포인트"]
            bettingPoint = predict_data["베팅포인트"]

            # 예측 내역 업데이트
            point_ref.update({
                "포인트": point,
                "총 예측 횟수": predict_data["총 예측 횟수"] + 1,
                "적중 횟수": predict_data["적중 횟수"],
                "적중률": f"{round((((predict_data['적중 횟수']) * 100) / (predict_data['총 예측 횟수'] + 1)), 2)}%",
                "연승": 0,
                "연패": predict_data["연패"] + 1,
                "베팅포인트": bettingPoint - 베팅금액,
                
                # 추가 데이터
                f"{대상}{승패}예측": predict_data.get(f"{대상}{승패}예측", 0) + 1,
                f"{승패}예측연속": predict_data.get(f"{승패}예측연속", 0) + 1
            })

            # ====================  [미션]  ====================
            # 시즌미션 : 대왕원숭이
            if predict_data.get("승리예측연속", 0) == 10:
                cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                current_predict_season = cur_predict_seasonref.get()
                ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{이름}/미션/시즌미션/대왕원숭이")
                mission_bool = ref.get()['완료']
                if not mission_bool:
                    ref.update({"완료": True})
                    print(f"{이름}의 [대왕원숭이] 미션 완료")
                    await mission_notice(interaction.client,이름,"대왕원숭이")

            # ====================  [미션]  ====================

            # ====================  [미션]  ====================
            # 시즌미션 : 대왕앵무
            if predict_data.get("패배예측연속", 0) == 10:
                cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                current_predict_season = cur_predict_seasonref.get()
                ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{이름}/미션/시즌미션/대왕앵무")
                mission_bool = ref.get()['완료']
                if not mission_bool:
                    ref.update({"완료": True})
                    print(f"{이름}의 [대왕앵무] 미션 완료")
                    await mission_notice(interaction.client,이름,"대왕앵무")

            # ====================  [미션]  ====================

            # ====================  [미션]  ====================
            # 시즌미션 : 지모의 충신
            if predict_data.get("지모승리예측", 0) == 30:
                cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                current_predict_season = cur_predict_seasonref.get()
                ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{이름}/미션/시즌미션/지모의 충신")
                mission_bool = ref.get()['완료']
                if not mission_bool:
                    ref.update({"완료": True})
                    print(f"{이름}의 [지모의 충신] 미션 완료")
                    await mission_notice(interaction.client,이름,"지모의 충신")    

            # ====================  [미션]  ====================

            # ====================  [미션]  ====================
            # 시즌미션 : 끝까지 가면 내가 다 이겨
            if predict_data["총 예측 횟수"] + 1 == 100:
                cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                current_predict_season = cur_predict_seasonref.get()
                ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{이름}/미션/시즌미션/끝까지 가면 내가 다 이겨")
                mission_bool = ref.get()['완료']
                if not mission_bool:
                    ref.update({"완료": True})
                    print(f"{이름}의 [끝까지 가면 내가 다 이겨] 미션 완료")
                    await mission_notice(interaction.client,이름,"끝까지 가면 내가 다 이겨")
            # ====================  [미션]  ====================

            # ====================  [미션]  ====================
            # 시즌미션 : 마이너스의 손
            if predict_data["연패"] + 1 == 10:
                ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{이름}/미션/시즌미션/마이너스의 손")
                mission_bool = ref.get()['완료']
                if not mission_bool:
                    ref.update({"완료": True})
                    print(f"{이름}의 [마이너스의 손] 미션 완료")
                    await mission_notice(interaction.client,이름,"마이너스의 손")
            # ====================  [미션]  ====================

            if 베팅금액 == 0:
                userembed.add_field(name="",value=f"{이름}님이 예측에 실패했습니다!", inline=False)
            else:
                userembed.add_field(name="",value=f"{이름}님이 예측에 실패하여 베팅포인트를 잃었습니다! (베팅 포인트:-{베팅금액})(환급 포인트: {환급금액})", inline=False)
                point_ref.update({"포인트": point - 베팅금액 + 환급금액})

        else:
            print(f"{interaction.user.name}의 패배 명령어 요청")
            interaction.response.send_message("권한이 없습니다",ephemeral=True)

    @app_commands.command(name="재부팅",description="봇 재부팅(개발자 전용)")
    async def 재부팅(self, interaction: discord.Interaction):
        if interaction.user.name == "toe_kyung":
            restart_script()
        else:
            interaction.response.send_message("권한이 없습니다",ephemeral=True)

    @app_commands.command(
        name="확성기",
        description="예측 포인트를 사용하여 확성기 채널에 메세지를 보냅니다(비익명 100P, 익명 150P)"
    )
    @app_commands.describe(익명여부="익명 또는 비익명을 선택하세요")
    @app_commands.choices(익명여부=[
        Choice(name='익명', value='익명'),
        Choice(name='비익명', value='비익명')
    ])
    async def 확성기(self, interaction: discord.Interaction, 익명여부: str):
        # 명령어 옵션으로 받은 익명여부를 모달 생성자에 전달하여 모달 호출
        await interaction.response.send_modal(확성기모달(익명여부))
    
    # 명령어에서 모달을 호출하는 예제
    @app_commands.command(name="공지", description="확성기 채널에 공지 메세지를 보냅니다(개발자 전용)")
    async def 공지(self,interaction: discord.Interaction):
        await interaction.response.send_modal(공지모달())
    

    @app_commands.command(name="테스트",description="테스트(개발자 전용)")
    @app_commands.describe(포인트 = "포인트를 입력하세요")
    async def 테스트(self, interaction: discord.Interaction, 포인트:int):
        if interaction.user.name == "toe_kyung":
            await place_bet(self.bot,"지모","승리",포인트)
            await interaction.response.send_message("수행완료",ephemeral=True)

    @app_commands.command(name="열람포인트초기화",description="열람포인트를 100포인트로 초기화합니다(개발자 전용)")
    async def 열람포인트초기화(self, interaction: discord.Interaction):
        if interaction.user.name == "toe_kyung":
            refhon = db.reference('승부예측')
            refhon.update({"혼자보기포인트" : 100})

    @app_commands.command(name="베팅포인트초기화",description="모두의 베팅포인트를 제거합니다(개발자 전용)")
    async def 베팅포인트초기화(self, interaction: discord.Interaction):
        if interaction.user.name == "toe_kyung":
            cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
            current_predict_season = cur_predict_seasonref.get()

            point_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트")
            
            users = point_ref.get()
            if users is None:
                await interaction.response.send_message("현재 시즌의 유저 데이터가 없습니다.")
                return

            # 각 유저의 베팅포인트 필드를 0으로 업데이트할 업데이트 딕셔너리 생성
            updates = {}
            for user_id in users.keys():
                updates[f"{user_id}/베팅포인트"] = 0

            point_ref.update(updates)
            
            await interaction.response.send_message("베팅포인트 초기화 완료!")
    
    @app_commands.command(name="베팅공개",description="현재 포인트의 10%(최소 100p)를 소모하여 현재 진행중인 승부예측의 현황을 공개합니다(3분 이후만 가능)")
    @app_commands.describe(이름 = "예측한 사람의 이름을 입력하세요")
    @app_commands.choices(이름=[
    Choice(name='지모', value='지모'),
    Choice(name='Melon', value='Melon'),
    ])
    async def 베팅공개(self, interaction: discord.Interaction, 이름: str):
        async def bet_open(winbutton):
            if winbutton.disabled == True:
                if p.votes.get(이름, {}).get('prediction', {}).get('win') or p.votes.get(이름, {}).get('prediction', {}).get('lose'):
                    cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                    current_predict_season = cur_predict_seasonref.get()
                    ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{interaction.user.name}')
                    originr = ref.get()
                    point = originr["포인트"]
                    bettingPoint = originr["베팅포인트"]
                    real_point = point - bettingPoint
                    need_point = round(real_point * 0.1) # 10% 지불
                    if need_point < 100:
                        need_point = 100
                    if real_point < 100:
                        await interaction.response.send_message(f"포인트가 부족합니다! 현재 포인트: {real_point} (베팅포인트 {bettingPoint} 제외)",ephemeral=True)
                        return
                    channel = self.bot.get_channel(int(CHANNEL_ID))
                    userembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
                    userembed.add_field(name="",value=f"{interaction.user.name}님이 포인트를 소모하여 {이름}의 예측 현황을 공개했습니다!", inline=False)
                    await channel.send(f"\n",embed = userembed)
                    
                    await refresh_prediction(이름,False,p.votes[이름]['prediction'])
                    
                    ref.update({"포인트" : point - need_point})
                    await interaction.response.send_message(f"{need_point}포인트 지불 완료! 현재 포인트: {real_point - need_point} (베팅포인트 {bettingPoint} 제외)",ephemeral=True)
                else:
                    await interaction.response.send_message(f"{이름}에게 아무도 투표하지 않았습니다!",ephemeral=True)
            else:
                await interaction.response.send_message(f"{이름}의 투표가 끝나지 않았습니다!",ephemeral=True)

        if 이름 == "지모":
            await bet_open(p.jimo_winbutton)
        elif 이름 == "Melon":
            await bet_open(p.melon_winbutton)
        
    @app_commands.command(name="아이템지급",description="아이템을 지급합니다(관리자 전용)")
    @app_commands.describe(이름 = "아이템을 지급할 사람을 입력하세요")
    @app_commands.describe(아이템 = "지급할 아이템을 입력하세요")
    @app_commands.choices(이름=[
    Choice(name='_kangjihun3', value='_kangjihun3'),
    Choice(name='leemireum', value='leemireum'),
    Choice(name='toe_kyung', value='toe_kyung'),
    Choice(name='grjr1', value='grjr1'),
    Choice(name='melon_0_0', value='melon_0_0'),
    Choice(name='kimdonghyun123123123', value='kimdonghyun123123123'),
    Choice(name='dalho', value='dalho'),
    Choice(name='manggo6340', value='manggo6340'),
    Choice(name='ssource_8', value='ssource_8'),
    Choice(name='coeganghanu', value='coeganghanu')
    ])
    @app_commands.choices(아이템=[
    Choice(name='배율증가 0.1', value='배율증가1'),
    Choice(name='배율증가 0.3', value='배율증가3'),
    Choice(name='배율증가 0.5', value='배율증가5'),
    ])
    async def 아이템지급(self, interaction: discord.Interaction, 이름: str, 아이템:str, 개수:int):
        if interaction.user.name == "toe_kyung":
            give_item(이름,아이템,개수)
            channel = self.bot.get_channel(int(CHANNEL_ID))
            userembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
            userembed.add_field(name="",value=f"{이름}에게 [{아이템}] {개수}개가 지급되었습니다!", inline=False)
            await channel.send(f"\n",embed = userembed)
            await interaction.response.send_message(f"{이름}에게 [{아이템}] {개수}개 지급 완료!",ephemeral=True)
        else:
            await interaction.response.send_message("권한이 없습니다",ephemeral=True)

    @app_commands.command(name="아이템전체지급",description="아이템을 모두에게 지급합니다(관리자 전용)")
    @app_commands.describe(아이템 = "지급할 아이템을 입력하세요")
    @app_commands.choices(아이템=[
    Choice(name='배율증가 0.1', value='배율증가1'),
    Choice(name='배율증가 0.3', value='배율증가3'),
    Choice(name='배율증가 0.5', value='배율증가5'),
    ])
    async def 아이템전체지급(self, interaction: discord.Interaction,아이템:str, 개수:int):
        if interaction.user.name == "toe_kyung":
            cur_predict_seasonref = db.reference("승부예측/현재예측시즌") # 현재 진행중인 예측 시즌을 가져옴
            current_predict_season = cur_predict_seasonref.get()
            ref_users = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트')
            users = ref_users.get()
            nicknames = list(users.keys())
            for nickname in nicknames:
                give_item(nickname,아이템,개수)
            channel = self.bot.get_channel(int(CHANNEL_ID))
            userembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
            userembed.add_field(name="",value=f"모두에게 [{아이템}] {개수}개가 지급되었습니다!", inline=False)
            await channel.send(f"\n",embed = userembed)
            await interaction.response.send_message(f"모두에게 [{아이템}] {개수}개 지급 완료!",ephemeral=True)
        else:
            await interaction.response.send_message("권한이 없습니다",ephemeral=True)

    @app_commands.command(name="아이템",description="자신의 아이템을 확인합니다")
    async def 아이템(self, interaction: discord.Interaction):
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") # 현재 진행중인 예측 시즌을 가져옴
        current_predict_season = cur_predict_seasonref.get()

        nickname = interaction.user
        refitem = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname.name}/아이템')
        itemr = refitem.get()
        embed = discord.Embed(title="📦 보유 아이템 목록", color=discord.Color.purple())

        if not itemr:
            embed.description = "현재 보유 중인 아이템이 없습니다. 🫥"
        else:
            for item_name, count in itemr.items():
                embed.add_field(name=f"🎁 {item_name}", value=f"개수: {count}", inline=False)

        await interaction.response.send_message(embed=embed,ephemeral=True)

    @app_commands.command(name="자동예측",description="판당 15 포인트를 소모하여, 승부예측이 올라왔을 때 자동으로 예측합니다")
    @app_commands.choices(이름=[
    Choice(name='지모', value='지모'),
    Choice(name='Melon', value='Melon')
    ])
    @app_commands.choices(승패=[
    Choice(name='승리', value="승리"),
    Choice(name='패배', value="패배")
    ])
    async def 자동예측(self, interaction: discord.Interaction, 이름:str, 승패:str, 판수:int):
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") # 현재 진행중인 예측 시즌을 가져옴
        current_predict_season = cur_predict_seasonref.get()

        nickname = interaction.user
        
        if 승패 == "승리":
            winlosebool = True
        else:
            winlosebool = False
        need_point = 15 # 한 판당 15p를 소모하여 자동예측
        total_need_point = need_point * 판수

        ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname.name}')
        originr = ref.get()
        point = originr["포인트"]
        bettingPoint = originr["베팅포인트"]
        real_point = point - bettingPoint

        if real_point < total_need_point:
            await interaction.response.send_message(f"포인트가 부족합니다! 현재 포인트: {real_point} (베팅포인트 {bettingPoint} 제외) \n"
                                                    f"필요 포인트 : {total_need_point}({need_point} x {판수})",ephemeral=True)
            return

        refitem = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname.name}/아이템')
        itemr = refitem.get()

        if winlosebool:
            if itemr.get("자동예측" + 이름 + "패배", 0) > 0:
                await interaction.response.send_message(f"이미 {이름}의 패배에 자동예측중입니다. </자동예측변경:1337254677326073929> 명령어를 사용해주세요!",ephemeral=True) 
            else:
                item_name = "자동예측" + 이름 + "승리"
                ref.update({"포인트" : point - total_need_point})
                give_item(nickname,item_name,판수)
                await interaction.response.send_message(f"{이름}의 {승패}에 {판수}게임동안 자동예측! \n"
                                                        f"남은 포인트 : {real_point - total_need_point} (베팅포인트 {bettingPoint} 제외) (- {total_need_point}({need_point} x {판수}))",ephemeral=True)
        else:
            if itemr.get("자동예측" + 이름 + "승리", 0) > 0:
                await interaction.response.send_message(f"이미 {이름}의 승리에 자동예측중입니다. </자동예측변경:1337254677326073929> 명령어를 사용해주세요!",ephemeral=True) 
            else:
                item_name = "자동예측" + 이름 + "패배"
                ref.update({"포인트" : point - total_need_point})
                give_item(nickname,item_name,판수)
                await interaction.response.send_message(f"{이름}의 {승패}에 {판수}게임동안 자동예측! \n"
                                                        f"남은 포인트 : {real_point - total_need_point} (베팅포인트 {bettingPoint} 제외) (- {total_need_point})",ephemeral=True)
    
    @app_commands.command(name="예측확인", description="현재 내가 투표한 항목을 확인합니다.")
    async def check_my_vote(self,interaction: discord.Interaction):
        nickname = interaction.user.name  # 현재 유저의 닉네임
        results = []  # 투표 내역 저장 리스트

        # 확인할 플레이어 목록
        players = ["지모", "Melon"]

        for player in players:
            if player in p.votes:
                player_votes = []

                # 승부 예측 (win/lose)
                for outcome in ["win", "lose"]:
                    if any(entry["name"] == nickname for entry in p.votes[player]["prediction"][outcome]):
                        player_votes.append(f"- {outcome.upper()} (승부예측)")

                # KDA 예측 (up/down/perfect)
                for outcome in ["up", "down", "perfect"]:
                    if any(entry["name"] == nickname for entry in p.votes[player]["kda"][outcome]):
                        player_votes.append(f"- {outcome.upper()} (KDA예측)")

                # 플레이어별로 투표 내역 정리
                if player_votes:
                    results.append(f"✅ **{player}에 대한 투표 내역:**\n" + "\n".join(player_votes))

        # 최종 메시지 출력
        if results:
            message = "\n\n".join(results)
        else:
            message = "❌ 현재 투표한 항목이 없습니다."

        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(name="자동예측변경",description="보유한 자동예측의 승패를 바꿉니다.")
    @app_commands.choices(이름=[
    Choice(name='지모', value='지모'),
    Choice(name='Melon', value='Melon')
    ])
    async def 자동예측변경(self, interaction: discord.Interaction, 이름:str):
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") # 현재 진행중인 예측 시즌을 가져옴
        current_predict_season = cur_predict_seasonref.get()

        nickname = interaction.user

        refitem = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname.name}/아이템')
        itemr = refitem.get()
        
    
        if itemr.get("자동예측" + 이름 + "승리", 0) > 0:
            item_num = itemr.get("자동예측" + 이름 + "승리", 0)
            refitem.update({
                f"자동예측{이름}패배": item_num,
                f"자동예측{이름}승리": 0
            })
            await interaction.response.send_message(f"{이름}의 자동예측을 승리에서 패배로 변경했습니다! 현재 보유중인 [자동예측{이름}패배] : {item_num}개",ephemeral=True) 
        elif itemr.get("자동예측" + 이름 + "패배", 0) > 0:
            item_num = itemr.get("자동예측" + 이름 + "패배", 0)
            refitem.update({
                f"자동예측{이름}승리": item_num,
                f"자동예측{이름}패배": 0
            })
            await interaction.response.send_message(f"{이름}의 자동예측을 패배에서 승리로 변경했습니다! 현재 보유중인 [자동예측{이름}승리] : {item_num}개",ephemeral=True) 
        else:
            await interaction.response.send_message(f"보유한 {이름}의 자동예측이 없습니다!",ephemeral=True)
            return
        
        
    @app_commands.command(name="일일미션추가",description="일일미션을 추가합니다")
    async def 일일미션추가(self,interaction: discord.Interaction, 미션이름:str, 포인트:int):
        await interaction.response.defer()
        
        result = await add_missions_to_all_users(미션이름,포인트,"일일미션")

        if result:
            await interaction.followup.send(f"미션을 추가했습니다.",ephemeral=True)
        else:
            await interaction.followup.send("유저가 존재하지 않습니다.",ephemeral=True)

    @app_commands.command(name="시즌미션추가",description="시즌미션을 추가합니다")
    async def 시즌미션추가(self,interaction: discord.Interaction, 미션이름:str, 포인트:int):
        await interaction.response.defer()

        result = await add_missions_to_all_users(미션이름,포인트,"시즌미션")

        if result:
            await interaction.followup.send(f"미션을 추가했습니다.",ephemeral=True)
        else:
            await interaction.followup.send("유저가 존재하지 않습니다.",ephemeral=True)
    
    @app_commands.command(name="미션삭제", description="일일미션 또는 시즌미션을 삭제합니다.")
    @app_commands.choices(미션종류=[
    Choice(name='일일미션', value='일일미션'),
    Choice(name='시즌미션', value='시즌미션')
    ])
    async def remove_mission(self, interaction: discord.Interaction, 미션이름: str, 미션종류: str):
        await interaction.response.defer()

        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")  # 현재 진행중인 예측 시즌을 가져옴
        current_predict_season = cur_predict_seasonref.get()
        
        # '예측포인트' 경로 아래의 모든 유저들 가져오기
        ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트")
        all_users = ref.get()

        if not all_users:
            await interaction.followup.send("유저가 존재하지 않습니다.", ephemeral=True)
            return

        deleted = False  # 삭제 여부를 추적

        # 각 유저에서 특정 미션 삭제
        for user_id, user_data in all_users.items():
            # 각 유저의 '미션' 경로
            user_missions_ref = ref.child(user_id).child("미션").child(미션종류)

            # 유저의 미션 목록을 가져옴
            mission_type_data = user_data.get("미션", {}).get(미션종류, {})

            # 미션 목록에서 미션 이름이 일치하는 미션을 찾아 삭제
            if 미션이름 in mission_type_data:
                user_missions_ref.child(미션이름).delete()  # 미션 이름으로 삭제
                deleted = True

        if deleted:
            await interaction.followup.send(f"미션 '{미션이름}'을 삭제했습니다.", ephemeral=True)
        else:
            await interaction.followup.send(f"미션 '{미션이름}'을 찾을 수 없습니다.", ephemeral=True)

    @app_commands.command(name="업적", description="시즌미션의 상세 정보를 확인합니다.")
    async def get_user_missions(self, interaction: discord.Interaction):
        user_id = interaction.user.name
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
        current_predict_season = cur_predict_seasonref.get()

        ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{user_id}/미션")
        user_missions = ref.get()

        if not user_missions:
            await interaction.response.send_message("현재 진행 중인 미션이 없습니다.", ephemeral=True)
            return  # 중복 응답 방지

        mission_details = {
            "모든 것을 건 한방": "🔥 승부사에게 필요한 건 단 한 번의 기회. 자신의 모든 포인트를 베팅하기.",
            "불사대마왕": "👑 죽음을 모르는 전설이 되어라. KDA 예측에서 퍼펙트를 건 뒤, 적중하기.",
            "세상을 향한 외침": "📢 세상은 용기 있는 자를 기억한다. 확성기 명령어를 통해 '비익명'으로 메시지 전달하기.",
            "천 리 길도 한 걸음부터": "🚶 가장 위대한 여정도 작은 한 걸음에서 시작된다. 시즌 미션 버튼을 눌러 미션 목록을 확인하기.",
            "내가 보여주는 미래": "🔮 예언자는 미래를 숨기지 않는다. 예측순위 명령어를 통해 '모두에게' 예측 순위표 공개하기.",
            "신의 한 수": "♟️ 이 한 수로 승부를 결정짓는다. 배율 3 이상에서 500포인트 이상 베팅하고 적중하기.",
            "마이너스의 손": "📉 실패의 끝을 보여줘라. 승부예측 10연속 비적중 달성",
            "끝까지 가면 내가 다 이겨": "🔄 포기하지 않으면 결국 승리한다. 승부예측 100회.",
            "행운의 주인공": "🎲 행운의 여신이 나에게 미소를 짓는다. 주사위에서 77 띄우기",
            "대왕원숭이": "🐵 원숭이의 왕이 되어라. 승부예측 승리에만 10번 연속 예측하기.",
            "대왕앵무": "🦜 앵무새의 왕이 되어라. 승부예측 패배에만 10번 연속 예측하기.",
            "지모의 충신": "⚫ 지모를 향한 일편단심. 지모의 승리에 30번 예측하기."
        }

        embed = discord.Embed(title="📜 시즌 미션 상세 정보", color=discord.Color.gold())


        ref_unlocked = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{user_id}/업적해금")
        achievement_unlocked = ref_unlocked.get() or False  # 값이 없으면 False로 처리

        for mission_type, missions in user_missions.items():
            for mission_name, mission_data in missions.items():
                if mission_type == "시즌미션":
                    description = mission_details.get(mission_name, "설명이 없습니다.")
                    if not mission_data.get("완료", False) and not achievement_unlocked:
                        description = "??"
                    embed.add_field(name=mission_name, value=description, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="업적공개", description="달성한 업적을 다른 사람들에게 공개합니다.")
    @app_commands.choices(내용공개=[
    Choice(name='공개', value='공개'),
    Choice(name='비공개', value='비공개')
    ])
    async def show_user_missions(self, interaction: discord.Interaction, 내용공개:str):
        user_id = interaction.user.name
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
        current_predict_season = cur_predict_seasonref.get()

        ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{user_id}/미션")
        user_missions = ref.get()

        if not user_missions:
            await interaction.response.send_message("현재 진행 중인 미션이 없습니다.", ephemeral=True)
            return  # 중복 응답 방지

        select = discord.ui.Select(placeholder='공개할 업적을 선택하세요')

        mission_details = {
            "모든 것을 건 한방": "🔥 승부사에게 필요한 건 단 한 번의 기회. 자신의 모든 포인트를 베팅하기.",
            "불사대마왕": "👑 죽음을 모르는 전설이 되어라. KDA 예측에서 퍼펙트를 건 뒤, 적중하기.",
            "세상을 향한 외침": "📢 세상은 용기 있는 자를 기억한다. 확성기 명령어를 통해 '비익명'으로 메시지 전달하기.",
            "천 리 길도 한 걸음부터": "🚶 가장 위대한 여정도 작은 한 걸음에서 시작된다. 시즌 미션 버튼을 눌러 미션 목록을 확인하기.",
            "내가 보여주는 미래": "🔮 예언자는 미래를 숨기지 않는다. 예측순위 명령어를 통해 '모두에게' 예측 순위표 공개하기.",
            "신의 한 수": "♟️ 이 한 수로 승부를 결정짓는다. 배율 3 이상에서 500포인트 이상 베팅하고 적중하기.",
            "마이너스의 손": "📉 실패의 끝을 보여줘라. 승부예측 10연속 비적중 달성",
            "끝까지 가면 내가 다 이겨": "🔄 포기하지 않으면 결국 승리한다. 승부예측 100회.",
            "행운의 주인공": "🎲 행운의 여신이 나에게 미소를 짓는다. 주사위에서 77 띄우기",
            "대왕원숭이": "🐵 원숭이의 왕이 되어라. 승부예측 승리에만 10번 연속 예측하기.",
            "대왕앵무": "🦜 앵무새의 왕이 되어라. 승부예측 패배에만 10번 연속 예측하기.",
            "지모의 충신": "⚫ 지모를 향한 일편단심. 지모의 승리에 30번 예측하기."
        }
   
        mission_options = []
        for mission_type, missions in user_missions.items():
            for mission_name, mission_data in missions.items():
                if mission_type == "시즌미션":
                    if mission_data.get("완료", False):  # 완료된 미션은 "완료"로 표시
                        # Select 옵션에 추가
                        description = mission_details.get(mission_name, "설명이 없습니다.")
                        mission_options.append((mission_name,description))

        # Select 옵션 설정
        for i, (mission_name, description) in enumerate(mission_options):
            select.add_option(label=mission_name, value=mission_name, description=description)
            
        # Select에 대한 처리하는 이벤트 핸들러를 View에 추가
        async def select_callback(interaction: discord.Interaction):
            selected_mission_name = select.values[0]  # 사용자가 선택한 미션명

            # 선택된 미션의 상세 정보를 가져와서 embed에 포함
            for mission_type, missions in user_missions.items():
                for mission_name, mission_data in missions.items():
                    if mission_name == selected_mission_name:
                        embed = discord.Embed(
                            title="업적 공개!",
                            description=f"{interaction.user.name}님이 업적을 공개했습니다!\n\n",
                            color=discord.Color.gold()
                        )
                        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/1828/1828884.png")
                        
                        if 내용공개 == "공개":
                            embed.add_field(
                                name=f"{selected_mission_name}\n\n",
                                value="\u200b\n" + mission_details.get(selected_mission_name, "설명이 없습니다."),
                                inline=False
                            )
                        else:
                            embed.add_field(
                                name=f"{selected_mission_name}",
                                value="\u200b\n" + "이 업적은 비공개 상태입니다.",
                                inline=False
                            )
                        
                        await interaction.response.send_message(embed=embed)
                        return

        # View 생성 후 select 콜백 함수 추가
        view = discord.ui.View()
        select.callback = select_callback
        view.add_item(select)

        # Select 위젯을 포함한 메시지 보내기
        await interaction.response.send_message("달성한 업적을 선택해주세요.", view=view,ephemeral=True)

    @app_commands.command(name="주사위",description="주사위를 굴립니다. 하루에 한 번만 가능합니다.(1 ~ 100)")
    async def 주사위(self, interaction: discord.Interaction):
        nickname = interaction.user.name
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
        current_predict_season = cur_predict_seasonref.get()

        ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname}/주사위")
        dice = ref.get()

        if not dice:  # 주사위를 아직 안 굴렸다면
            dice_num = random.randint(1, 100)
            ref.set(True)  # 주사위 값 저장
            embed = discord.Embed(
                title="🎲 주사위 굴리기!",
                description=f"{nickname}님이 주사위를 굴렸습니다!",
                color=discord.Color.blue()
            )
            embed.add_field(name="🎲 결과", value=f"**{dice_num}**", inline=False)
            embed.set_footer(text="내일 다시 도전할 수 있습니다!")
            # ====================  [미션]  ====================
            # 일일미션 : 주사위 굴리기
            cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
            current_predict_season = cur_predict_seasonref.get()
            ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname}/미션/일일미션/주사위 굴리기")
            mission_bool = ref.get()['완료']
            if not mission_bool:
                ref.update({"완료": True})
                print(f"{nickname}의 [주사위 굴리기] 미션 완료")

            # ====================  [미션]  ====================

            # ====================  [미션]  ====================
            # 시즌미션 : 행운의 주인공
            if dice_num == 77:
                cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
                current_predict_season = cur_predict_seasonref.get()
                ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{nickname}/미션/시즌미션/행운의 주인공")
                mission_bool = ref.get()['완료']
                if not mission_bool:
                    ref.update({"완료": True})
                    print(f"{nickname}의 [행운의 주인공] 미션 완료")
                    await mission_notice(interaction.client, nickname, "행운의 주인공")
            # ====================  [미션]  ====================
        else: 
            embed = discord.Embed(
                title="🎲 주사위는 하루에 한 번!",
                description=f"{nickname}님은 이미 주사위를 굴렸습니다.",
                color=discord.Color.red()
            )
            embed.set_footer(text="내일 다시 도전할 수 있습니다!")

        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="업적해금", description="1000포인트를 지불하여, 아직 달성하지 않은 시즌미션의 상세 정보까지 전부 확인합니다.")
    async def show_missions(self, interaction: discord.Interaction):
        user_id = interaction.user.name
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌") 
        current_predict_season = cur_predict_seasonref.get()

        point_ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{user_id}')
        originr = point_ref.get()
        point = originr["포인트"]
        bettingPoint = originr["베팅포인트"]
        real_point = point - bettingPoint

        need_point = 1000
        if real_point < need_point:
            await interaction.response.send_message(f"포인트가 부족합니다! 현재 포인트: {real_point} (베팅포인트 {bettingPoint} 제외) \n"
                                                    f"필요 포인트 : {need_point}",ephemeral=True)
            return

        ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{user_id}")
        ref.update({"업적해금": True})

        embed = discord.Embed(
            title="업적 해금!",
            description=f"{user_id}님이 1000포인트를 지불하여 모든 업적의 정보를 열람했습니다!",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="숫자야구",description="포인트를 걸고 숫자야구 게임을 진행합니다")
    @app_commands.describe(포인트 = "포인트를 입력하세요")
    @app_commands.choices(상대=[
    Choice(name='강지모', value='_kangjihun3'),
    Choice(name='이미름', value='leemireum'),
    Choice(name='박퇴경', value='toe_kyung'),
    Choice(name='그럭저럭', value='grjr1'),
    Choice(name='Melon', value='melon_0_0'),
    Choice(name='꿀꿀희', value='kimdonghyun123123123'),
    Choice(name='달호', value='dalho'),
    Choice(name='망고', value='manggo6340'),
    Choice(name='출처', value='ssource_8'),
    Choice(name='최강하누', value='coeganghanu')
    ])
    async def 숫자야구(self, interaction: discord.Interaction, 상대:str, 포인트:int):
        if interaction.user.name == "toe_kyung":
            player_A = interaction.user.name
            battleEmbed = discord.Embed(title=f"대결 신청", color=discord.Color.light_gray())
            battleEmbed.add_field(name="",value=f"{player_A}님이 {상대}님에게 숫자 야구 대결을 신청했습니다!({포인트})", inline=False)

            channel = self.bot.get_channel(int(CHANNEL_ID))
            await channel.send(f"\n",embed = battleEmbed)
            await interaction.response.send_message("수행완료",ephemeral=True)


    #베팅 테스트를 위한 코드
    # @app_commands.command(name="베팅테스트",description="베팅 테스트(개발자 전용)")
    # @app_commands.describe(이름 = "이름을 입력하세요", 값 = "값")
    # @app_commands.choices(이름=[
    # Choice(name='지모', value='지모'),
    # Choice(name='Melon', value='Melon'),
    # ])
    # async def 베팅테스트(self, interaction: discord.Interaction, 이름:str, 값:bool):
    #     print(f"{interaction.user.name}의 베팅테스트 명령어 요청")
    #     if interaction.user.name == "toe_kyung":
    #         if 이름 == "지모":
    #             p.jimo_current_game_state = 값
    #         elif 이름 == "Melon":
    #             p.melon_current_game_state = 값
    #     else:
    #         interaction.response.send_message("권한이 없습니다",ephemeral=True)
    # @app_commands.command(name="베팅테스트2",description="베팅 테스트2(개발자 전용)")
    # @app_commands.describe(이름 = "이름을 입력하세요")
    # @app_commands.choices(이름=[
    # Choice(name='지모', value='지모'),
    # Choice(name='Melon', value='Melon'),
    # ])
    # async def 베팅테스트2(self, interaction: discord.Interaction, 이름:str):
    #     print(f"{interaction.user.name}의 베팅테스트2 명령어 요청")
    #     if interaction.user.name == "toe_kyung":
    #         if 이름 == "지모":
    #             p.jimo_event.set()
    #             p.prediction_votes['win'].clear()
    #             p.prediction_votes['lose'].clear()
    #         elif 이름 == "Melon":
    #             p.melon_event.set()
    #             p.prediction_votes2['win'].clear()
    #             p.prediction_votes2['lose'].clear()

    #     else:
    #         interaction.response.send_message("권한이 없습니다",ephemeral=True)

# 컨텍스트 메뉴 명령어 등록 (메시지 대상)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        hello(bot),
        guilds=[Object(id=298064707460268032)]
    )