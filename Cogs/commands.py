import requests
import discord
import platform
import random
import copy
import matplotlib.pyplot as plt
import concurrent.futures
import asyncio
import aiohttp
import pandas as pd
import mplfinance as mpf
import prediction_vote as p
import subprocess
import os
import math
import secrets
import matplotlib.dates as mdates
from discord.ui import Modal, TextInput
from discord import TextStyle
from firebase_admin import db
from discord.app_commands import Choice
from discord import app_commands
from discord.ext import commands
from discord import Interaction
from datetime import datetime
from matplotlib import font_manager, rc
from dotenv import load_dotenv
from collections import Counter
API_KEY = None

JIMO_NAME = '강지모'
JIMO_TAG = 'KR1'

# 경고 채널의 ID (실제 채널 ID로 변경)
WARNING_CHANNEL_ID = 1314643507490590731
ENHANCEMENT_CHANNEL = 1350434647149908070

SEASON_CHANGE_DATE = datetime(2027, 1, 6, 0, 0, 0)


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

CHANNEL_ID = '938728993329397781'

class NotFoundError(Exception):
    pass

class TooManyRequestError(Exception):
    pass

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

duels = {}  # 진행 중인 대결 정보를 저장

# 대결 신청
class DuelRequestView(discord.ui.View):
    def __init__(self, challenger, opponent):
        super().__init__()  # 3분 타이머
        self.challenger = challenger
        self.opponent = opponent
        self.request_accepted = False
        self.message = None
        self.event = asyncio.Event()

    async def start_timer(self):
        await asyncio.sleep(60)
        if not self.request_accepted:
            for child in self.children:
                child.disabled = True
        
        battleembed = discord.Embed(title="요청 만료!", color=discord.Color.blue())
        battleembed.add_field(name="", value="대결 요청이 만료되었습니다. ⏰")
        await self.message.edit(embed=battleembed,view = self)
        battle_ref = db.reference("승부예측/대결진행여부")
        battle_ref.set(False)
        self.event.set()

    @discord.ui.button(label="수락", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.opponent:
            await interaction.response.send_message("이 버튼은 지목된 사람만 누를 수 있습니다!", ephemeral=True)
            return

        self.request_accepted = True
        for child in self.children:
            child.disabled = True

        battleembed = discord.Embed(title="대결 수락!", color = discord.Color.blue())
        battleembed.add_field(name="", value=f"{self.opponent.mention}님이 대결을 수락했습니다!")
        await interaction.response.edit_message(embed = battleembed, view = self)
        self.event.set()

    @discord.ui.button(label="거절", style=discord.ButtonStyle.danger)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.opponent:
            await interaction.response.send_message("이 버튼은 지목된 사람만 누를 수 있습니다!", ephemeral=True)
            return

        self.request_accepted = False
        for child in self.children:
            child.disabled = True

        battleembed = discord.Embed(title="대결 거절!", color = discord.Color.blue())
        battleembed.add_field(name="", value=f"{self.opponent.mention}님이 대결을 거절했습니다!")
        await interaction.response.edit_message(embed = battleembed, view = self)
        battle_ref = db.reference("승부예측/대결진행여부")
        battle_ref.set(False)
        self.event.set()
        
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

async def get_summoner_ranks(puuid, type="솔랭"):
    url = f'https://kr.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}'
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

# 임베드를 생성하는 함수 (명령어 목록을 페이지별로 나누기)
def create_embed(commands_list, current_page, page_size):
    embed = discord.Embed(title="명령어 목록", color=discord.Color.green())
    start_index = current_page * page_size
    end_index = min((current_page + 1) * page_size, len(commands_list))

    # 현재 페이지에 해당하는 명령어들만 추가
    for cmd in commands_list[start_index:end_index]:
        embed.add_field(name=f"</{cmd.name}:{cmd.id}>", value=cmd.description, inline=False)
    return embed

# 야추 다이스 굴리기
class DiceRollView(discord.ui.View):
    def __init__(self, user, initial_rolls, reroll_count=0):
        super().__init__(timeout=60)
        self.user = user
        self.rolls = initial_rolls
        self.hold = [False] * 5  # 각 주사위가 hold 상태인지 저장
        self.reroll_count = reroll_count
        self.max_rerolls = 2
        self.keep_alive_task = None
        self.update_buttons()

    def toggle_hold(self, index):
        """주사위의 hold 상태를 토글합니다."""
        self.hold[index] = not self.hold[index]
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        for idx, roll in enumerate(self.rolls):
            label = f"🎲 {roll}{' 🔒' if self.hold[idx] else ''}"
            self.add_item(DiceButton(idx, label, self))
        if self.reroll_count < self.max_rerolls:
            self.add_item(RerollButton(self))
            self.add_item(FinalizeButton(self))
        else:
            self.add_item(FinalizeButton(self))

    async def timer_task(self):
        try:
            await asyncio.sleep(120)
            self.clear_items()

            result = ', '.join(str(roll) for roll in self.rolls)
            hand = evaluate_hand(self.rolls)  # 족보 판별
            embed = discord.Embed(
                title="🎲야추 다이스!",
                description=f"{self.user.display_name}님의 주사위: **{result}**\n 족보: **{hand}**",
                color=discord.Color.blue()
            )

            await self.message.edit(embed=embed,view = self)
        except asyncio.CancelledError:
            # 타이머가 취소되었을 경우 예외 무시
            return

    async def start_timer(self):
        """타이머 백그라운드 태스크 시작"""
        self.keep_alive_task = asyncio.create_task(self.timer_task())

# 야추 다이스 버튼
class DiceButton(discord.ui.Button):
    def __init__(self, index, label, view):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.index = index
        self.custom_view = view 

    async def callback(self, interaction: discord.Interaction):
        user = interaction.user
        if user != self.custom_view.user:  
            await interaction.response.send_message("이 주사위는 당신의 것이 아닙니다!", ephemeral=True)
            return

        self.custom_view.toggle_hold(self.index)
        await interaction.response.edit_message(view=self.custom_view)

# 야추 다이스 다시 굴리기 버튼
class RerollButton(discord.ui.Button):
    def __init__(self, view):
        super().__init__(style=discord.ButtonStyle.success, label="🎲 다시 굴리기")
        self.custom_view = view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.custom_view.user:  
            await interaction.response.send_message("이 주사위는 당신의 것이 아닙니다!", ephemeral=True)
            return
        for idx in range(5):
            if not self.custom_view.hold[idx]:
                self.custom_view.rolls[idx] = random.randint(1, 6)
        self.custom_view.reroll_count += 1
        self.custom_view.update_buttons()
        result = ', '.join(str(roll) for roll in self.custom_view.rolls) 
        embed = discord.Embed(
            title="🎲야추 다이스!",
            description=f"{interaction.user.display_name}님의 주사위: **{result}**",
            color=discord.Color.blue()
        )
        
        await interaction.response.edit_message(view=self.custom_view, embed = embed)

# 야추 다이스 확정 버튼
class FinalizeButton(discord.ui.Button):
    def __init__(self, view):
        super().__init__(style=discord.ButtonStyle.danger, label="✅ 확정")
        self.custom_view = view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.custom_view.user:
            await interaction.response.send_message("이 주사위는 당신의 것이 아닙니다!", ephemeral=True)
            return
        
        result = ', '.join(str(roll) for roll in self.custom_view.rolls)
        hand = evaluate_hand(self.custom_view.rolls)  # 족보 판별
        embed = discord.Embed(
            title="야추 다이스",
            description=f"{interaction.user.display_name}님의 주사위: **{result}**\n 족보: **{hand}**",
            color=discord.Color.blue()
        )

        if self.custom_view.keep_alive_task:
            self.custom_view.keep_alive_task.cancel()
            try:
                await self.custom_view.keep_alive_task
            except asyncio.CancelledError:
                pass

        await interaction.response.edit_message(content="", view=None, embed = embed)

# 야추 다이스 족보 판별
def evaluate_hand(rolls):
    from collections import Counter
    
    counts = Counter(rolls)
    count_values = sorted(counts.values(), reverse=True)
    rolls_sorted = sorted(rolls)

    # Yahtzee
    if count_values[0] == 5:
        return "🎉 야추!"

    # Large Straight (1-5 or 2-6)
    elif rolls_sorted == [1, 2, 3, 4, 5] or rolls_sorted == [2, 3, 4, 5, 6]:
        return "➡️ 라지 스트레이트!"

    # Small Straight (any 4 consecutive numbers)
    elif any(all(num in rolls_sorted for num in seq) for seq in ([1,2,3,4], [2,3,4,5], [3,4,5,6])):
        return "🡒 스몰 스트레이트!"

    # Full House
    elif count_values == [3, 2]:
        return "🏠 풀 하우스!"

    # Four of a Kind
    elif count_values[0] == 4:
        return "🔥 포 오브 어 카인드!"

    # Chance
    else:
        total = sum(rolls)
        return f"🎲 합계: {total}!"

# 경고 지급 모달
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
        embed = discord.Embed(title="🚨 경고 기록", color=discord.Color.red())
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

# 경고 지급 명령어 모달
class WarnCommandModal(discord.ui.Modal, title="경고 기록"):
    def __init__(self, bot: commands.Bot, member: discord.Member):
        super().__init__()
        self.bot = bot
        self.member = member

        self.reason = discord.ui.TextInput(label="경고 사유", placeholder="경고 사유를 입력하세요.", max_length=100)
        self.details = discord.ui.TextInput(label="자세한 경위", style=discord.TextStyle.paragraph, placeholder="상세 설명 입력...", max_length=1000)

        self.add_item(self.reason)
        self.add_item(self.details)

    async def on_submit(self, interaction: discord.Interaction):
        warn_channel = interaction.client.get_channel(WARNING_CHANNEL_ID)
        if not warn_channel:
            await interaction.response.send_message("⚠️ 경고 채널을 찾을 수 없습니다.", ephemeral=True)
            return
        
        channel = self.bot.get_channel(int(CHANNEL_ID)) #tts 채널 

        embed = discord.Embed(title="🚨 경고 기록", color=discord.Color.red())
        embed.add_field(name="경고 대상", value=self.member.mention, inline=False)
        embed.add_field(name="경고 사유", value=self.reason.value, inline=False)
        embed.add_field(name="자세한 경위", value=self.details.value, inline=False)
        embed.set_footer(text=f"경고 발송자: {interaction.user}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)

        await warn_channel.send(embed=embed)
        await channel.send(embed=embed)
        await interaction.response.send_message(f"{self.member.mention}에게 경고를 부여했습니다.", ephemeral=True)

# 경고 지급 명령어 뷰
class WarnCommandView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

        self.select = discord.ui.Select(
            placeholder="경고할 멤버를 선택하세요.",
            min_values=1,
            max_values=1,
            options=[]
        )
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        member_id = int(self.select.values[0])
        member = interaction.guild.get_member(member_id)
        if member:
            await interaction.response.send_modal(WarnCommandModal(self.bot, member))
        else:
            await interaction.response.send_message("⚠️ 해당 멤버를 찾을 수 없습니다.", ephemeral=True)

    async def populate_members(self, guild: discord.Guild):
        self.select.options = [
            discord.SelectOption(label=member.display_name, value=str(member.id))
            for member in guild.members if not member.bot
        ]

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
        excluded_bots = ['TTS Bot', '술팽봇', '뽀삐', '알로항']
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

    @app_commands.command(name="연승",description="소환사의 연승 횟수를 보여줍니다")
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

    @app_commands.command(name="연패",description="소환사의 연패 횟수를 보여줍니다")
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
    Choice(name='Melon', value='Melon')
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
    Choice(name='시즌15', value='시즌15'),
    Choice(name='시즌16', value='시즌16'),
    ])
    @app_commands.describe(이름='누구의 그래프를 볼지 선택하세요')
    @app_commands.choices(이름=[
    Choice(name='강지모', value='지모'),
    Choice(name='Melon', value='Melon')
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

    @app_commands.command(name="시즌종료",description="시즌 종료까지 남은 날짜를 보여줍니다.")
    async def 시즌종료(self, interaction: discord.Interaction):
        print(f"{interaction.user}가 요청한 시즌종료 요청 수행")
        # 현재 날짜 및 시간 가져오기
        current_datetime = datetime.now()

        # 시간 차이 계산
        time_difference = SEASON_CHANGE_DATE - current_datetime

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
            await interaction.response.send_message("시즌 16이 종료되었습니다.")
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
        rank = await get_summoner_ranks(puuid,리그)
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
    Choice(name='시즌15', value='시즌15'),
    Choice(name='시즌16', value='시즌16'),
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

    @app_commands.command(name="예측순위",description="승부예측 포인트 순위를 보여줍니다.")
    @app_commands.describe(시즌 = "시즌을 입력하세요(26년 2월 => 26-2)")
    async def 예측순위(self, interaction: discord.Interaction, 시즌:str):
        ref = db.reference(f'승부예측/예측시즌/{시즌}/예측포인트')
        points = ref.get()

        if points is None:
            await interaction.response.send_message("해당되는 시즌이 존재하지 않습니다.", ephemeral=True)
            return
        
        # 점수를 기준으로 내림차순으로 정렬
        sorted_data = sorted(points.items(), key=lambda x: x[1]['포인트'], reverse=True)

        # 상위 명을 추출하여 출력
        top = sorted_data[:]

        embed = discord.Embed(title=f'승부예측 순위', color = discord.Color.blue())

        rank = 1

        for username, info in top:
            if info['총 예측 횟수'] > 0:
                if info['연승'] > 0:
                    embed.add_field(name=f"{rank}. {username}", value=f"연속적중 {info['연승']}, 포인트 {info['포인트']}, 적중률 {info['적중률']}({info['적중 횟수']}/{info['총 예측 횟수']}), ", inline=False)
                elif info['연패'] > 0:
                    embed.add_field(name=f"{rank}. {username}", value=f"연속비적중 {info['연패']}, 포인트 {info['포인트']}, 적중률 {info['적중률']}({info['적중 횟수']}/{info['총 예측 횟수']}), ", inline=False)
                else:
                    embed.add_field(name=f"{rank}. {username}", value=f"포인트 {info['포인트']}, 적중률 {info['적중률']}({info['적중 횟수']}/{info['총 예측 횟수']}), ", inline=False)
                rank += 1

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name='포인트',description="자신의 승부예측 포인트와 적중률을 알려줍니다")
    async def 포인트(self, interaction: discord.Interaction):
        username = interaction.user.name
        cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
        current_predict_season = cur_predict_seasonref.get()
        ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{username}')
        point_data = ref.get()

        embed = discord.Embed(title=f'{username}의 포인트', color = discord.Color.blue())

        if (point_data['지모승리예측'] + point_data['지모패배예측']) != 0:
            jimo_prediction_rate = round((point_data['지모적중'] / (point_data['지모승리예측'] + point_data['지모패배예측'])) * 100, 2)
        else:
            jimo_prediction_rate = 0
        if (point_data['Melon승리예측'] + point_data['Melon패배예측']) != 0:
            Melon_prediction_rate = round((point_data['Melon적중'] / (point_data['Melon승리예측'] + point_data['Melon패배예측'])) * 100, 2)
        else:
            Melon_prediction_rate = 0
        if (point_data['총 예측 횟수'] - (point_data['지모승리예측'] + point_data['지모패배예측']) - (point_data['Melon승리예측'] + point_data['Melon패배예측'])) != 0:
            battle_prediction_rate = round(((point_data['적중 횟수'] - point_data['지모적중'] - point_data['Melon적중']) / (point_data['총 예측 횟수'] - (point_data['지모승리예측'] + point_data['지모패배예측']) - (point_data['Melon승리예측'] + point_data['Melon패배예측']))) * 100, 2)
        else:
            battle_prediction_rate = 0

        embed.add_field(name='',value=f"**{point_data['포인트']}**포인트**)", inline=False)
        embed.add_field(name=f"승부예측 데이터", value=f"연속적중 **{point_data['연승']}**, 연속비적중 **{point_data['연패']}**, 포인트 **{point_data['포인트']}**, 적중률 **{point_data['적중률']}**({point_data['적중 횟수']}/{point_data['총 예측 횟수']}), ", inline=False)
        embed.add_field(name=f"", value=f"연속승리예측 **{point_data['승리예측연속']}**, 연속패배예측 **{point_data['패배예측연속']}**, 적중률(대결) **{battle_prediction_rate}%**({(point_data['적중 횟수'] - point_data['지모적중'] - point_data['Melon적중'])} / {(point_data['총 예측 횟수'] - (point_data['지모승리예측'] + point_data['지모패배예측']) - (point_data['Melon승리예측'] + point_data['Melon패배예측']))})", inline=False)
        embed.add_field(name=f"", value=f"지모승리예측 **{point_data['지모승리예측']}**, 지모패배예측 **{point_data['지모패배예측']}**, 적중률(지모) **{jimo_prediction_rate}%**({point_data['지모적중']} / {point_data['지모승리예측'] + point_data['지모패배예측']})", inline=False)
        embed.add_field(name=f"", value=f"Melon승리예측 **{point_data['Melon승리예측']}**, Melon패배예측 **{point_data['Melon패배예측']}**, 적중률(Melon) **{Melon_prediction_rate}%**({point_data['Melon적중']} / {point_data['Melon승리예측'] + point_data['Melon패배예측']})", inline=False)
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

    @app_commands.command(name="대결진행여부초기화",description="대결진행여부를 초기화합니다")
    async def 대결진행여부초기화(self, interaction: discord.Interaction):
        onoffref = db.reference("승부예측")
        onoffref.update({"대결진행여부" : False})
        embed = discord.Embed(title=f'변경 완료', color = discord.Color.blue())
        embed.add_field(name=f"변경", value=f"대결 진행상태가 초기화되었습니다", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="군대",description="전역까지 남은 날짜를 알려줍니다")
    async def 군대(self, interaction: discord.Interaction):
        outdate_DH = datetime(2026, 5, 3, 7, 0, 0)

        current_datetime = datetime.now()

        # 시간 차이 계산
        time_difference = outdate_DH - current_datetime

        
        # 시간 차이를 한글로 변환하여 출력
        days = time_difference.days
        hours, remainder = divmod(time_difference.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        hours += days*24

        output = "김동현 전역까지 남은 시간: "
        
        if hours:
            output += f"{hours}시간 "
        if minutes:
            output += f"{minutes}분 "
        if seconds:
            output += f"{seconds}초"
        
        if hours < 0:
            output = "김동현은 **[민간인]** 상태입니다!"

        await interaction.response.send_message(f"{output}")

    @app_commands.command(name="재부팅",description="봇 재부팅(개발자 전용)")
    async def 재부팅(self, interaction: discord.Interaction):
        if interaction.user.name == "toe_kyung":
            restart_script()
        else:
            interaction.response.send_message("권한이 없습니다",ephemeral=True)

    @app_commands.command(name="테스트",description="테스트(개발자 전용)")
    @app_commands.describe(포인트 = "포인트를 입력하세요")
    async def 테스트(self, interaction: discord.Interaction, 포인트:int):
        if interaction.user.name == "toe_kyung":
            await interaction.response.send_message("수행완료",ephemeral=True)
    
    @app_commands.command(name="주사위",description="20면체 주사위를 굴립니다. (1 ~ 20)")
    async def 주사위(self, interaction: discord.Interaction):
        nickname = interaction.user.display_name

        await interaction.response.defer()

        dice_num = secrets.randbelow(20) + 1
        embed = discord.Embed(
            title="🎲주사위 [1 ~ 20]",
            description=f"{nickname}님이 주사위를 굴렸습니다!",
            color=discord.Color.blue()
        )
        embed.add_field(name=f"**{dice_num}**", value=f"", inline=False)

        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="야추", description="주사위 5개를 굴립니다.")
    async def 야추(self, interaction: discord.Interaction):
        nickname = interaction.user.display_name

        await interaction.response.defer()

        initial_rolls = [random.randint(1, 6) for _ in range(5)]
        view = DiceRollView(interaction.user, initial_rolls)
        dice_display = ', '.join(str(roll) for roll in initial_rolls)
        embed = discord.Embed(
            title="🎲야추 다이스!",
            description=f"{nickname}님의 주사위: **{dice_display}**",
            color=discord.Color.blue()
        )
        await interaction.followup.send(embed=embed, view=view)
        await view.start_timer()
        
    @app_commands.command(name="경고", description="서버 멤버에게 경고를 부여합니다.")
    async def warn(self, interaction: discord.Interaction):
        # 경고 처리 로직
        allowed_role_name = "1등 ✨"
        #allowed_role_name = "관리자"
        # 사용자의 역할 확인
        user_roles = [role.name for role in interaction.user.roles]
        if allowed_role_name in user_roles:
            view = WarnCommandView(self.bot)
            await view.populate_members(interaction.guild)
            await interaction.response.send_message("경고할 멤버를 선택하세요.", view=view, ephemeral=True)
        else:
            await interaction.response.send_message("경고는 1등만 부여할 수 있습니다.")

    @app_commands.command(name="숫자야구",description="숫자야구 게임을 진행합니다.")
    @app_commands.describe(상대 = "대결할 상대를 고르세요")
    async def 숫자야구(self, interaction: discord.Interaction, 상대:discord.Member):
        challenger = interaction.user.name
        challenger_m = interaction.user
        if 상대.name == challenger:
            warnembed = discord.Embed(title="실패",color = discord.Color.red())
            warnembed.add_field(name="",value="자기 자신에게 도전할 수 없습니다! ❌")
            await interaction.response.send_message(embed = warnembed)
            return

        battle_ref = db.reference("승부예측/대결진행여부")
        is_battle = battle_ref.get()

        if is_battle:
            warnembed = discord.Embed(title="실패",color = discord.Color.red())
            warnembed.add_field(name="",value="다른 대결이 진행중입니다! ❌")
            await interaction.response.send_message(embed = warnembed)
            return

        # 대결 요청
        view = DuelRequestView(challenger, 상대)
        battleembed = discord.Embed(title="대결 요청!", color = discord.Color.blue())
        battleembed.add_field(name="", value=f"{상대.mention}, {challenger_m.mention}의 숫자야구 대결 요청! 수락하시겠습니까?")
        # 메시지 전송
        await interaction.response.send_message(content=상대.mention, view=view, embed=battleembed)
        battle_ref.set(True)

        # 전송된 메시지 객체 가져오기
        view.message = await interaction.original_response()

        done, pending = await asyncio.wait(
            [
                asyncio.create_task(view.start_timer()),
                asyncio.create_task(view.event.wait())
            ],
            return_when=asyncio.FIRST_COMPLETED  # 첫 번째로 끝나는 코루틴을 기다림
        )

        # 아직 끝나지 않은 태스크 취소
        for task in pending:
            task.cancel()
        
        if not view.request_accepted:
            return
            
        class GuessModal(discord.ui.Modal, title="숫자 맞추기"):
            def __init__(self, game, player):
                super().__init__()
                self.game = game
                self.player = player
                self.answer = discord.ui.TextInput(
                    label="네 자리 숫자를 입력하세요 (예: 1234)",
                    style=discord.TextStyle.short,
                    max_length=4
                )
                self.add_item(self.answer)

            async def on_submit(self, interaction: discord.Interaction):
                await interaction.response.defer()
                guess = self.answer.value.strip()
                if not guess.isdigit() or len(set(guess)) != 4 or len(guess) != 4:
                    await interaction.followup.send("🚫 **서로 다른 4개의 숫자로 입력해주세요!**", ephemeral=True)
                    return

                guess = list(map(int, guess))
                result, end = await self.game.check_guess(self.player, guess)

                await interaction.followup.send(embed=result)
                if not end:
                    await self.game.next_turn()  # 턴 넘기기

        class BaseballGameView(discord.ui.View):
            def __init__(self, challenger, opponent):
                super().__init__(timeout = None)
                self.players = [challenger, opponent]
                self.numbers = {challenger.name: self.generate_numbers(), opponent.name: self.generate_numbers()}
                self.turn = 1  # 상대(1) → 도전자(0)
                self.message = None
                self.turn_timer = None
                self.challenger = challenger.name
                self.opponent = opponent.name
                self.challenger_m = challenger
                self.opponent_m = opponent
                self.channel = None
                self.point_limited = False
                self.success = {challenger.name: False, opponent.name: False}

            def generate_numbers(self):
                return random.sample(range(10), 4)

            async def start_game(self, channel):
                """게임 시작 메시지를 보내고, 상대부터 시작"""
                embed = discord.Embed(title="⚾ 숫자야구 대결 시작!", color=discord.Color.blue())
                embed.add_field(name="턴", value=f"🎯 {self.players[self.turn].mention}님의 턴입니다!", inline=False)
                self.message = await channel.send(embed=embed, view=self)
                self.channel = channel
                await self.start_turn_timer()

            async def start_turn_timer(self):
                """2분 타이머 실행, 시간이 지나면 턴 자동 변경"""
                if self.turn_timer:
                    self.turn_timer.cancel()
                self.turn_timer = asyncio.create_task(self.turn_timeout())

            async def turn_timeout(self):
                try:
                    await asyncio.sleep(120)  # 2분 대기
                    if self.turn_timer.done():  # 취소되었는지 확인
                        return

                    if self.turn == 0:
                        if self.success[self.opponent]: # 상대가 정답을 맞춘 상태에서 턴이 변경될 경우
                            baseball_winner = self.opponent_m
                            await self.announce_winner(baseball_winner)
                        else:
                            embed = discord.Embed(title=f"턴 변경!", color=discord.Color.light_gray())
                            embed.add_field(name = "", value = "2분 동안 입력이 없어 턴이 변경되었습니다.", inline = False)
                            await self.channel.send(embed=embed)
                            await self.next_turn(timeout=True)         
                except asyncio.CancelledError:
                    pass

            async def next_turn(self, timeout=False):
                """턴을 변경하고 메시지를 업데이트"""
                self.turn = (self.turn + 1) % 2
                player = self.players[self.turn]
                
                embed = discord.Embed(title="⚾ 숫자야구 진행 중!", color=discord.Color.green())
                embed.add_field(name="턴", value=f"🎯 {player.mention}님의 턴입니다!", inline=False)
                if timeout:
                    embed.add_field(name="⏳ 턴 자동 변경!", value="2분 동안 입력이 없어 턴이 변경되었습니다.", inline=False)

                self.clear_items()
                await self.add_new_buttons()

                await self.message.edit(embed=embed, view=self)
                await self.start_turn_timer()

            async def check_guess(self, player, guess):
                """입력된 숫자를 비교하고 결과를 반환"""
                opponent = self.players[(self.players.index(player) + 1) % 2]  # 상대 플레이어
                answer = self.numbers[opponent.name]
                end = False

                strikes = sum(1 for i in range(4) if guess[i] == answer[i])
                balls = sum(1 for i in range(4) if guess[i] in answer) - strikes
                
                player = self.players[self.turn]
                if player.name == self.challenger:
                    embed = discord.Embed(title=f"{player}의 숫자 맞추기 결과", color=discord.Color.red())
                else:
                    embed = discord.Embed(title=f"{player}의 숫자 맞추기 결과", color=discord.Color.blue())
                embed.add_field(name="입력값", value="".join(map(str, guess)), inline=False)
                
                if strikes == 4:
                    embed.color = discord.Color.gold()
                    embed.add_field(name="🏆 정답!", value=f"{player.mention}님이 **정답을 맞췄습니다!** 🎉")

                    if player.name == self.challenger: # 게임 종료
                        end = True
                        if self.success[self.opponent]: # 상대가 정답을 맞춘 상태라면 무승부!
                            baseball_winner = None
                        else: # 못맞췄다면 도전자 승리!
                            baseball_winner = self.challenger_m

                        await self.announce_winner(baseball_winner)

                    else: # 상대편이 맞추는 지 기다림
                        end = False
                        self.success[self.opponent] = True # 플레이어 정답!
                    
                else:
                    result = f"{strikes} STRIKE, {balls} BALL" if strikes or balls else "⚾ OUT!"
                    embed.add_field(name="결과", value=result, inline=False)
                    if player.name == self.challenger:
                        if self.success[self.opponent]: #상대가 정답을 맞췄다면 상대 승리!
                            end = True
                            baseball_winner = self.opponent_m

                            await self.announce_winner(baseball_winner)
                        else:
                            end = False

                return embed, end

            async def announce_winner(self, baseball_winner):
                self.turn_timer.cancel() # 턴 타이머 종료
                end_embed = discord.Embed(title="⚾ 숫자야구 종료!", color=discord.Color.green())

                for button in self.children:  # 모든 버튼에 대해
                    button.disabled = True

                await self.message.edit(embed=end_embed, view=self)
                
                battle_ref = db.reference("승부예측/대결진행여부")
                battle_ref.set(False)

                if baseball_winner:
                    userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                    userembed.add_field(name="게임 종료", value=f"숫자야구 대결이 종료되었습니다!\n {baseball_winner.mention}의 승리!")

                else:
                    userembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
                    userembed.add_field(name="게임 종료", value=f"배틀이 종료되었습니다!\n무승부!🤝\n")

                channel = interaction.client.get_channel(int(CHANNEL_ID)) #tts 채널
                await channel.send(embed=userembed)

                self.stop()  # 게임 종료

            async def add_new_buttons(self):
                """새로운 버튼을 추가하는 메서드"""
                self.add_item(self.check_numbers)
                self.add_item(self.guess_numbers)

            @discord.ui.button(label="내 숫자 확인", style=discord.ButtonStyle.gray)
            async def check_numbers(self, interaction: discord.Interaction, button: discord.ui.Button):
                """자신의 숫자를 확인하는 버튼"""
                if interaction.user.name not in self.numbers:
                    await interaction.response.send_message("🚫 당신은 이 게임의 참가자가 아닙니다!", ephemeral=True)
                    return
                
                num_str = " ".join(map(str, self.numbers[interaction.user.name]))
                embed = discord.Embed(title="🔢 내 숫자", description=f"🎲 당신의 숫자는 `{num_str}` 입니다!", color=discord.Color.blue())
                await interaction.response.send_message(embed=embed, ephemeral=True)

            @discord.ui.button(label="숫자 맞추기", style=discord.ButtonStyle.success)
            async def guess_numbers(self, interaction: discord.Interaction, button: discord.ui.Button):
                """모달을 열어 숫자 입력 받기"""
                if interaction.user != self.players[self.turn]:
                    await interaction.response.send_message("🚫 **지금은 상대의 턴입니다!**", ephemeral=True)
                    return
            
                await interaction.response.send_modal(GuessModal(self, interaction.user))

        thread = await interaction.channel.create_thread(
            name=f"{challenger_m.display_name} vs {상대.display_name} 숫자야구 대결",
            type=discord.ChannelType.public_thread
        )
        await BaseballGameView(challenger_m, 상대).start_game(thread)
    
    @app_commands.command(name="명령어",description="명령어 목록을 보여줍니다.")
    async def 명령어(self, interaction: discord.Interaction):
        exclude = {"온오프", "정상화", "재부팅", "테스트", "승리", "패배", "포인트지급"}
        commands_list = await self.bot.tree.fetch_commands(guild=discord.Object(id=298064707460268032))  # 동기화된 모든 명령어 가져오기
        commands_list = [cmd for cmd in commands_list if cmd.name not in exclude]
        commands_list.sort(key=lambda x: x.name)

        # 페이지 구분 (한 페이지에 10개씩 표시한다고 가정)
        page_size = 10
        total_pages = (len(commands_list) // page_size) + (1 if len(commands_list) % page_size != 0 else 0)
        
        # 첫 번째 페이지의 명령어 목록을 임베드로 생성
        current_page = 0
        embed = create_embed(commands_list, current_page, page_size)
        
        # 버튼을 만들어 페이지를 넘길 수 있게 처리
        prev_button = discord.ui.Button(label="이전 페이지", style=discord.ButtonStyle.primary, disabled=True)
        next_button = discord.ui.Button(label="다음 페이지", style=discord.ButtonStyle.primary)

        # 버튼 클릭 이벤트 정의
        async def prev_button_callback(interaction: discord.Interaction):
            nonlocal current_page
            if current_page > 0:
                current_page -= 1
                embed = create_embed(commands_list, current_page, page_size)
                next_button.disabled = False
                if current_page == 0:
                    prev_button.disabled = True
                view.clear_items()
                view.add_item(prev_button)
                view.add_item(next_button)
                await interaction.response.edit_message(embed=embed, view=view)

        async def next_button_callback(interaction: discord.Interaction):
            nonlocal current_page
            if current_page < total_pages - 1:
                current_page += 1
                embed = create_embed(commands_list, current_page, page_size)
                prev_button.disabled = False
                if current_page == total_pages - 1:
                    next_button.disabled = True
                view.clear_items()
                view.add_item(prev_button)
                view.add_item(next_button)
                await interaction.response.edit_message(embed=embed, view=view)

        prev_button.callback = prev_button_callback
        next_button.callback = next_button_callback
        
        # View에 버튼을 추가
        view = discord.ui.View()
        view.add_item(prev_button)
        view.add_item(next_button)

        # 처음 명령어 목록을 보여주는 메시지 전송
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="포인트지급", description="포인트를 지급합니다. (관리자 전용)")
    async def give_point(self, interaction: discord.Interaction, user: discord.Member, point: int):
        if interaction.user.name == "toe_kyung":
            cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
            current_predict_season = cur_predict_seasonref.get()
            point_ref = db.reference(f'승부예측/예측시즌/{current_predict_season}/예측포인트/{user.name}')
            predict_data = point_ref.get()
            original_point = predict_data["포인트"]

            point_ref.update({"포인트": original_point + point})
            await interaction.response.send_message(f"{user.mention}에게 {point}포인트가 지급되었습니다!",)
        else:
            await interaction.response.send_message("권한이 없습니다",ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    # await bot.add_cog(
    #     hello(bot),
    #     guilds=[Object(id=298064707460268032)]
    # )
    await bot.add_cog(hello(bot))