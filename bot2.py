import aiohttp
import asyncio
import discord
import firebase_admin
import random
import prediction_vote as p
import os
from firebase_admin import credentials
from firebase_admin import db
from discord import Intents
from discord.ext import commands
from discord import Game
from discord import Status
from discord import Object
from datetime import datetime
from dotenv import load_dotenv

TARGET_TEXT_CHANNEL_ID = 1289184218135396483

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
  '개코원숭이','긴팔원숭이','일본원숭이','붉은고함원숭이','알락꼬리여우원숭이','다이아나원숭이','알렌원숭이','코주부원숭이',
]
ANONYM_NAME_LOSE = [
  '사랑앵무','왕관앵무','회색앵무','모란앵무','금강앵무','유황앵무','뉴기니아앵무','장미앵무'
]

CHANNEL_ID = '938728993329397781'
NOTICE_CHANNEL_ID = '1232585451911643187'

async def nowgame(puuid):
    url = f'https://kr.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}'
    headers = {'X-Riot-Token': API_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                if (data["gameMode"] == "CLASSIC" and
                    data["gameType"] == "MATCHED" and
                    data["gameQueueConfigId"] == 420):
                    return True
                else:
                    return False
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

    try:
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
                  raise NotFoundError("404 Error occurred in get_summoner_ranks")
              else:
                  print('get_summoner_ranks Error:', response.status)
                  return None
    except aiohttp.ClientConnectorError as e:
        print(f"get_summoner_ranks Connection error: {e}")
        return None
    except Exception as e:
        print(f"get_summoner_ranks Unexpected error: {e}")
        return None

async def get_summoner_recentmatch_id(puuid):
    url = f'https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=1'
    headers = {'X-Riot-Token': API_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data[0] if data else None
            else:
                print('get_summoner_recentmatch_id Error:', response.status)
                return None

async def get_summoner_matchinfo(matchid):
    url = f'https://asia.api.riotgames.com/lol/match/v5/matches/{matchid}'
    headers = {'X-Riot-Token': API_KEY}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 404:
                    print(f"[ERROR] Match ID {matchid} not found in get_summoner_matchinfo.")
                elif response.status == 400:
                    print(f"[ERROR] Bad Request for match ID {matchid}. Check if it's valid in get_summoner_matchinfo.")
                else:
                    print(f"[ERROR] Riot API returned status {response.status} in get_summoner_matchinfo")
        except Exception as e:
            print(f"[ERROR] Exception occurred while fetching match info in get_summoner_matchinfo: {e}")
    return None

def tier_to_number(tier, rank, lp): # 티어를 레이팅 숫자로 변환
    tier_num = TIER_RANK_MAP.get(tier)
    rank_num = RANK_MAP.get(rank)
    if tier_num is None or rank_num is None:
        return None
    return tier_num * 400 + rank_num * 100 + lp

def get_lp_and_tier_difference(previous_rank, current_rank,name): #이전 랭크와 현재 랭크를 받아 차이를 계산하여 메세지 반환(승급/강등)

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
    save_lp_difference_to_file(lp_difference,current_rank,name)
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

def save_lp_difference_to_file(lp_difference,current_rank,name): #지모의 점수 변화량과 날짜를 파이어베이수에 저장
    # 현재 날짜 가져오기
    current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rank_num = tier_to_number(current_rank["tier"],current_rank["rank"],current_rank["leaguePoints"])

    # 현재 날짜 및 시간 가져오기
    current_datetime = datetime.now()

    # 날짜만 추출하여 저장
    current_date = current_datetime.strftime("%Y-%m-%d")

    # 시간만 추출하여 저장
    current_time = current_datetime.strftime("%H:%M:%S")

    curseasonref = db.reference("현재시즌")
    current_season = curseasonref.get()

    refprev = db.reference(f'{current_season}/점수변동/{name}')
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
    ref = db.reference(f'{current_season}/점수변동/{name}/{current_date}/{current_time}')
    ref.update({'LP 변화량' : lp_difference})
    ref.update({'현재 점수' : rank_num})
    ref.update({"연승": win_streak})
    ref.update({"연패": lose_streak})

    ref2 = db.reference(f'최근연속/{name}')
    if result:
        ref2.update({"연승": win_streak})
        ref2.update({"연패": 0})
    else:
        ref2.update({"연패": lose_streak})
        ref2.update({"연승": 0})

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

async def check_jimo_points(): #지모의 솔로랭크 점수를 20초마다 확인하여 점수 변동이 있을 경우 알림
    await bot.wait_until_ready()
    id = JIMO_ID
    channel = bot.get_channel(int(CHANNEL_ID))
    try:
        last_rank = await get_summoner_ranks(id)
        if not last_rank:
            last_total_match = 0
        else:
            last_win = last_rank['wins']
            last_loss = last_rank['losses']
            last_total_match = last_win + last_loss
    except NotFoundError as e:
        last_total_match = 0

    cur_predict_seasonref = db.reference("현재예측시즌")
    current_predict_season = cur_predict_seasonref.get()

    while not bot.is_closed():
        try:
          current_rank = await get_summoner_ranks(id)
        except Exception as e:
          print(f"Error in check_jimo_points: {e}")
        if not current_rank:
            current_total_match = 0
        else:
            current_win = current_rank['wins']
            current_loss = current_rank['losses']
            current_total_match = current_win + current_loss
            if current_total_match != last_total_match:
                print(last_total_match, current_total_match)
                ref22 = db.reference(f'최근연속/지모')
                points = ref22.get()

                game_win_streak = points["연승"]
                game_lose_streak = points["연패"]
                string = get_lp_and_tier_difference(last_rank, current_rank,"지모")
                await bot.get_channel(int(NOTICE_CHANNEL_ID)).send("\n지모의 솔로랭크 점수 변동이 감지되었습니다!\n"
                                    f"{string}")
                await bot.get_channel(int(CHANNEL_ID)).send("\n지모의 솔로랭크 점수 변동이 감지되었습니다!\n"
                                    f"{string}")

                last_rank = current_rank
                last_total_match = current_total_match

                onoffref = db.reference("투표온오프")
                onoffbool = onoffref.get()
                if not onoffbool:
                    curseasonref = db.reference("현재시즌")
                    current_season = curseasonref.get()

                    # 현재 날짜 및 시간 가져오기
                    current_datetime = datetime.now()

                    # 날짜만 추출하여 저장
                    current_date = current_datetime.strftime("%Y-%m-%d")

                    # 시간만 추출하여 저장
                    current_time = current_datetime.strftime("%H:%M:%S")


                    ref = db.reference(f'{current_season}/점수변동/지모')
                    points = ref.get()

                    # 가장 최근의 날짜를 찾음
                    latest_date = max(points.keys())

                    # 해당 날짜의 시간들을 정렬하여 가장 최근의 시간을 찾음
                    latest_time = max(points[latest_date].keys(), key=lambda t: datetime.strptime(t, '%H:%M:%S'))

                    # 가장 최근의 데이터
                    latest_data = points[latest_date][latest_time]

                    point_change = latest_data['LP 변화량']

                    if point_change > 0:
                        result = True
                    else:
                        result = False

                    userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                    userembed.add_field(name="게임 종료", value=f"지모의 솔로랭크 게임이 종료되었습니다!\n"
                                         f"{'승리!' if result else '패배..'}\n"
                                         f"점수변동 : {point_change}")

                    if result:
                        winners = p.prediction_votes['win']
                        losers = p.prediction_votes['lose']

                        winnerNum = len(winners)
                        loserNum = len(losers)

                        # 연패 보너스
                        if game_lose_streak >= 1:
                          streak_bonus_rate = calculate_bonus(game_lose_streak)
                        else:
                          streak_bonus_rate = 0


                        if winnerNum == 0:
                            BonusRate = 0
                        else:
                            BonusRate = round((((winnerNum+loserNum)/winnerNum) - 1) * 0.5,2) + 1 # 0.5배 배율 적용
                            if BonusRate < 1:
                                BonusRate = 1
                            BonusRate += streak_bonus_rate
                            BonusRate += 0.1

                        # 베팅 포인트를 전부 합산
                        winner_total_point = 0
                        for winner in winners:
                            winner_total_point += winner['points']

                        loser_total_point = 0
                        for loser in losers:
                            loser_total_point += loser['points']

                        remain_loser_total_point = loser_total_point


                        if BonusRate == 0:
                            userembed.add_field(name="",value=f"베팅 배율: {BonusRate}배", inline=False)
                        else:
                            userembed.add_field(name="",value=f"베팅 배율: {BonusRate}배!((({winnerNum+loserNum}/{winnerNum} - 1) x 0.5 + 1) + 역배 배율 {streak_bonus_rate} + 0.1)", inline=False)

                        for winner in winners:
                            ref2 = db.reference(f'{current_predict_season}/예측포인트/{winner["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            prediction_all = originr["총 예측 횟수"]
                            prediction_wins = originr["적중 횟수"]
                            prediction_win_rate = originr["적중률"]
                            win_streak = originr["연승"]
                            lose_streak = originr["연패"]
                            bettingPoint = originr["베팅포인트"]

                            ref3 = db.reference(f'{current_predict_season}/예측포인트변동로그/{current_date}/{current_time}/{winner["name"]}')
                            ref3.update({"포인트" : point})
                            ref3.update({"총 예측 횟수": prediction_all})
                            ref3.update({"적중 횟수" : prediction_wins})
                            ref3.update({"적중률": f"{prediction_win_rate}"})
                            ref3.update({"연승": win_streak})
                            ref3.update({"연패": lose_streak})
                            ref3.update({"베팅포인트" : 0})

                            ref2 = db.reference(f'{current_predict_season}/예측포인트/{winner["name"]}')
                            pointr = ref2.get()
                            point = pointr["포인트"]
                            streakr = ref2.get()
                            win_streak = streakr["연승"]
                            win_streak +=  1
                            lose_streak = streakr["연패"]
                            lose_streak = 0
                            bettingPoint -= winner["points"]


                            prediction_all = pointr["총 예측 횟수"]
                            prediction_wins = pointr["적중 횟수"]

                            prediction_all += 1
                            prediction_wins += 1

                            # 이긴 팀에서 배팅한 비율
                            if winner_total_point == 0:
                                betted_rate = 0
                            else:
                                betted_rate = round(winner['points'] / winner_total_point, 1)

                            get_bet = 0
                            # 진 팀의 배팅 점수를 가져옴
                            get_bet = round(betted_rate * loser_total_point)

                            # 가져올 수 있는 최대 점수
                            get_bet_limit = round(BonusRate * winner['points'])

                            # 가져올 수 있는 최대 점수보다 높으면 최대 점수로 고정
                            if get_bet >= get_bet_limit:
                                get_bet = get_bet_limit

                            remain_loser_total_point -= get_bet

                            prediction_win_rate = round(((prediction_wins * 100) / prediction_all), 2)
                            if win_streak > 1:
                                add_points = point_change + (calculate_points(win_streak)) + round(winner['points']*BonusRate) + get_bet
                                userembed.add_field(name="",value=f"{winner['name']}님이 {win_streak}연속 적중을 이루어내며 {add_points}(연속적중 보너스 + {calculate_points(win_streak)})(베팅 보너스 + {round(winner['points']*BonusRate)} + {get_bet}) 점수를 획득하셨습니다! (베팅 포인트:{winner['points']})", inline=False)
                            else:
                                add_points = point_change + round(winner["points"]*BonusRate) + get_bet
                                userembed.add_field(name="",value=f"{winner['name']}님이 {add_points}(베팅 보너스 + {round(winner['points']*BonusRate)} + {get_bet}) 점수를 획득하셨습니다! (베팅 포인트:{winner['points']})", inline=False)
                            point -= winner['points']
                            point += add_points

                            ref2.update({"포인트": point})
                            ref2.update({"총 예측 횟수": prediction_all})
                            ref2.update({"적중 횟수" : prediction_wins})
                            ref2.update({"적중률": f"{prediction_win_rate}%"})
                            ref2.update({"연승": win_streak})
                            ref2.update({"연패": lose_streak})
                            ref2.update({"베팅포인트" : bettingPoint})


                        for loser in losers:
                            ref2 = db.reference(f'{current_predict_season}/예측포인트/{loser["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            prediction_all = originr["총 예측 횟수"]
                            prediction_wins = originr["적중 횟수"]
                            prediction_win_rate = originr["적중률"]
                            win_streak = originr["연승"]
                            lose_streak = originr["연패"]
                            bettingPoint = originr["베팅포인트"]

                            ref3 = db.reference(f'{current_predict_season}/예측포인트변동로그/{current_date}/{current_time}/{loser["name"]}')
                            ref3.update({"포인트" : point})
                            ref3.update({"총 예측 횟수": prediction_all})
                            ref3.update({"적중 횟수" : prediction_wins})
                            ref3.update({"적중률": f"{prediction_win_rate}"})
                            ref3.update({"연승": win_streak})
                            ref3.update({"연패": lose_streak})
                            ref3.update({"베팅포인트" : 0})


                            ref2 = db.reference(f'{current_predict_season}/예측포인트/{loser["name"]}')
                            pointr = ref2.get()
                            point = pointr["포인트"]
                            streakr = ref2.get()
                            win_streak = streakr["연승"]
                            win_streak = 0
                            lose_streak = streakr["연패"]
                            lose_streak += 1
                            bettingPoint -= loser["points"]

                            prediction_all = pointr["총 예측 횟수"]
                            prediction_wins = pointr["적중 횟수"]

                            prediction_all += 1

                            # 진 팀에서 배팅한 비율
                            if loser_total_point != 0:
                                betted_rate = round(loser['points'] / loser_total_point, 1)
                            else:
                                betted_rate = 0
                            get_bet = 0
                            # 가져갈 포인트
                            get_bet = round(betted_rate * remain_loser_total_point * 0.5)

                            prediction_win_rate = round(((prediction_wins * 100) / prediction_all), 2)

                            if point + get_bet < loser['points']:
                                point = 0
                            else:
                                point -= loser['points']
                                point += get_bet
                            ref2.update({"포인트": point})
                            ref2.update({"총 예측 횟수": prediction_all})
                            ref2.update({"적중 횟수" : prediction_wins})
                            ref2.update({"적중률": f"{prediction_win_rate}%"})
                            ref2.update({"연승": win_streak})
                            ref2.update({"연패": lose_streak})
                            ref2.update({"베팅포인트" : bettingPoint})

                            if loser['points'] == 0:
                                userembed.add_field(name="",value=f"{loser['name']}님이 예측에 실패했습니다! (베팅 포인트:{loser['points']})", inline=False)
                            else:
                                userembed.add_field(name="",value=f"{loser['name']}님이 예측에 실패하여 베팅포인트를 잃었습니다! (베팅 포인트:-{loser['points']}) (환급 포인트:{get_bet})", inline=False)
                    else:
                        winners = p.prediction_votes['lose']
                        losers = p.prediction_votes['win']

                        winnerNum = len(winners)
                        loserNum = len(losers)

                        # 연승 보너스
                        if game_win_streak >= 1:
                          streak_bonus_rate = calculate_bonus(game_win_streak)
                        else:
                          streak_bonus_rate = 0

                        if winnerNum == 0:
                            BonusRate = 0
                        else:
                            BonusRate = round((((winnerNum+loserNum)/winnerNum) - 1) * 0.5,2) + 1  # 0.5배 배율 적용
                            if BonusRate < 1:
                                BonusRate = 1
                            BonusRate += streak_bonus_rate
                            BonusRate += 0.1

                        # 베팅 포인트를 전부 합산
                        winner_total_point = 0
                        for winner in winners:
                            winner_total_point += winner['points']

                        loser_total_point = 0
                        for loser in losers:
                            loser_total_point += loser['points']

                        remain_loser_total_point = loser_total_point

                        if BonusRate == 0:
                            userembed.add_field(name="",value=f"베팅 배율: {BonusRate}배", inline=False)
                        else:
                            userembed.add_field(name="",value=f"베팅 배율: {BonusRate}배!((({winnerNum+loserNum}/{winnerNum} - 1) x 0.5 + 1) + 역배 배율 {streak_bonus_rate} + 0.1)", inline=False)


                        for winner in winners:
                            ref2 = db.reference(f'{current_predict_season}/예측포인트/{winner["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            prediction_all = originr["총 예측 횟수"]
                            prediction_wins = originr["적중 횟수"]
                            prediction_win_rate = originr["적중률"]
                            win_streak = originr["연승"]
                            lose_streak = originr["연패"]
                            bettingPoint = originr["베팅포인트"]

                            ref3 = db.reference(f'{current_predict_season}/예측포인트변동로그/{current_date}/{current_time}/{winner["name"]}')
                            ref3.update({"포인트" : point})
                            ref3.update({"총 예측 횟수": prediction_all})
                            ref3.update({"적중 횟수" : prediction_wins})
                            ref3.update({"적중률": f"{prediction_win_rate}"})
                            ref3.update({"연승": win_streak})
                            ref3.update({"연패": lose_streak})
                            ref3.update({"베팅포인트" : 0})

                            ref2 = db.reference(f'{current_predict_season}/예측포인트/{winner["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            prediction_all = originr["총 예측 횟수"]
                            prediction_wins = originr["적중 횟수"]
                            prediction_win_rate = originr["적중률"]
                            win_streak = originr["연승"]
                            lose_streak = originr["연패"]
                            bettingPoint -= winner["points"]


                            ref2 = db.reference(f'{current_predict_season}/예측포인트/{winner["name"]}')
                            pointr = ref2.get()
                            point = pointr["포인트"]
                            streakr = ref2.get()
                            win_streak = streakr["연승"]
                            win_streak +=  1
                            lose_streak = streakr["연패"]
                            lose_streak = 0

                            winnerNum = len(winners)
                            loserNum = len(losers)

                            prediction_all = pointr["총 예측 횟수"]
                            prediction_wins = pointr["적중 횟수"]

                            prediction_all += 1
                            prediction_wins += 1

                            # 이긴 팀에서 배팅한 비율
                            if winner_total_point == 0:
                                betted_rate = 0
                            else:
                                betted_rate = round(winner['points'] / winner_total_point, 1)

                            get_bet = 0
                            # 진 팀의 배팅 점수를 가져옴
                            get_bet = round(betted_rate * loser_total_point)

                            # 가져올 수 있는 최대 점수
                            get_bet_limit = round(BonusRate * winner['points'])

                            # 가져올 수 있는 최대 점수보다 높으면 최대 점수로 고정
                            if get_bet >= get_bet_limit:
                                get_bet = get_bet_limit

                            remain_loser_total_point -= get_bet

                            prediction_win_rate = round(((prediction_wins * 100) / prediction_all), 2)

                            if win_streak > 1:
                                add_points = -point_change + (calculate_points(win_streak)) + round(winner['points']*BonusRate) + get_bet
                                userembed.add_field(name="",value=f"{winner['name']}님이 {win_streak}연속 적중을 이루어내며 {add_points}(연속적중 보너스 + {calculate_points(win_streak)})(베팅 보너스 + {round(winner['points']*BonusRate)} + {get_bet}) 점수를 획득하셨습니다! (베팅 포인트:{winner['points']})", inline=False)
                            else:
                                add_points = -point_change + round(winner["points"]*BonusRate) + get_bet
                                userembed.add_field(name="",value=f"{winner['name']}님이 {add_points}(베팅 보너스 + {round(winner['points']*BonusRate)} + {get_bet}) 점수를 획득하셨습니다! (베팅 포인트:{winner['points']})", inline=False)

                            point -= winner['points']
                            point += add_points
                            ref2.update({"포인트": point})
                            ref2.update({"총 예측 횟수": prediction_all})
                            ref2.update({"적중 횟수" : prediction_wins})
                            ref2.update({"적중률": f"{prediction_win_rate}%"})
                            ref2.update({"연승": win_streak})
                            ref2.update({"연패": lose_streak})
                            ref2.update({"베팅포인트" : bettingPoint})

                        losers = p.prediction_votes['win']
                        for loser in losers:
                            ref2 = db.reference(f'{current_predict_season}/예측포인트/{loser["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            prediction_all = originr["총 예측 횟수"]
                            prediction_wins = originr["적중 횟수"]
                            prediction_win_rate = originr["적중률"]
                            win_streak = originr["연승"]
                            lose_streak = originr["연패"]
                            bettingPoint = originr["베팅포인트"]


                            ref3 = db.reference(f'{current_predict_season}/예측포인트변동로그/{current_date}/{current_time}/{loser["name"]}')
                            ref3.update({"포인트" : point})
                            ref3.update({"총 예측 횟수": prediction_all})
                            ref3.update({"적중 횟수" : prediction_wins})
                            ref3.update({"적중률": f"{prediction_win_rate}"})
                            ref3.update({"연승": win_streak})
                            ref3.update({"연패": lose_streak})
                            ref3.update({"베팅포인트" : 0})

                            ref2 = db.reference(f'{current_predict_season}/예측포인트/{loser["name"]}')
                            pointr = ref2.get()
                            point = pointr["포인트"]
                            streakr = ref2.get()
                            win_streak = streakr["연승"]
                            win_streak =  0
                            lose_streak = streakr["연패"]
                            lose_streak += 1
                            bettingPoint -= loser["points"]

                            prediction_all = pointr["총 예측 횟수"]
                            prediction_wins = pointr["적중 횟수"]

                            prediction_all += 1

                            # 진 팀에서 배팅한 비율
                            if loser_total_point != 0:
                                betted_rate = round(loser['points'] / loser_total_point, 1)
                            else:
                                betted_rate = 0

                            get_bet = 0
                            # 가져갈 포인트
                            get_bet = round(betted_rate * remain_loser_total_point * 0.5)

                            prediction_win_rate = round(((prediction_wins * 100) / prediction_all), 2)

                            if point + get_bet < loser['points']:
                                point = 0
                            else:
                                point -= loser['points']
                                point += get_bet
                            ref2.update({"포인트": point})
                            ref2.update({"총 예측 횟수": prediction_all})
                            ref2.update({"적중 횟수" : prediction_wins})
                            ref2.update({"적중률": f"{prediction_win_rate}%"})
                            ref2.update({"연승": win_streak})
                            ref2.update({"연패": lose_streak})
                            ref2.update({"베팅포인트" : bettingPoint})

                            if loser['points'] == 0:
                                userembed.add_field(name="",value=f"{loser['name']}님이 예측에 실패했습니다! (베팅 포인트:{loser['points']})", inline=False)
                            else:
                                userembed.add_field(name="",value=f"{loser['name']}님이 예측에 실패하여 베팅포인트를 잃었습니다! (베팅 포인트:-{loser['points']}) (환급 포인트: {get_bet})", inline=False)

                    await channel.send(embed=userembed)
                    p.prediction_votes['win'].clear()
                    p.prediction_votes['lose'].clear()

                    #KDA 결과 도출
                    #await asyncio.sleep(30) # 게임 종료 후 30초간 대기(최근 전적에 올라오는 시간 감안함)
                    jimo_match_id = await get_summoner_recentmatch_id(JIMO_PUUID)
                    match_info = await get_summoner_matchinfo(jimo_match_id)

                    for player in match_info['info']['participants']:
                        if JIMO_PUUID == player['puuid']:
                            if player['deaths'] == 0:
                                jimo_kda = 999
                                jimo_kill = player['kills']
                                jimo_assist = player['assists']
                                jimo_death = player['deaths']
                            else:
                                jimo_kill = player['kills']
                                jimo_assist = player['assists']
                                jimo_death = player['deaths']
                                jimo_kda = round((player['kills'] + player['assists'])/player['deaths'],1)

                    kdaembed = discord.Embed(title="지모 KDA 예측 결과", color=discord.Color.blue())

                    if jimo_kda == 999:
                        kdaembed.add_field(name="지모의 KDA",value=f"{jimo_kill}/{jimo_death}/{jimo_assist}(PERFECT)", inline=False)
                    else:
                        kdaembed.add_field(name="지모의 KDA",value=f"{jimo_kill}/{jimo_death}/{jimo_assist}({jimo_kda})", inline=False)

                    refperfect = db.reference('퍼펙트포인트')
                    perfectr = refperfect.get()
                    perfect_point = perfectr['지모']
                    if jimo_kda > 3:
                        if jimo_kda == 999:
                            perfect_winners = p.kda_votes['perfect']
                            winners = p.kda_votes['up']
                            losers = p.kda_votes['down']
                        else:
                            winners = p.kda_votes['up']
                            losers = p.kda_votes['down'] + p.kda_votes['perfect']
                            perfect_winners = []
                        for perfect_winner in perfect_winners:
                            ref2 = db.reference(f'{current_predict_season}/예측포인트/{perfect_winner["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            ref2.update({"포인트": point + perfect_point})
                            kdaembed.add_field(name="",value=f"{perfect_winner['name']}님이 KDA 퍼펙트 예측에 성공하여 {perfect_point}점을 획득하셨습니다!", inline=False)
                        for winner in winners:
                            ref2 = db.reference(f'{current_predict_season}/예측포인트/{winner["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            ref2.update({"포인트": point + 20})
                            kdaembed.add_field(name="",value=f"{winner['name']}님이 KDA 예측에 성공하여 20점을 획득하셨습니다!", inline=False)
                        for loser in losers:
                            kdaembed.add_field(name="",value=f"{loser['name']}님이 KDA 예측에 실패했습니다!", inline=False)
                    elif jimo_kda < 3:
                        winners = p.kda_votes['down']
                        losers = p.kda_votes['up'] + p.kda_votes['perfect']
                        for winner in winners:
                            ref2 = db.reference(f'{current_predict_season}/예측포인트/{winner["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            ref2.update({"포인트": point + 20})
                            kdaembed.add_field(name="",value=f"{winner['name']}님이 KDA 예측에 성공하여 20점을 획득하셨습니다!", inline=False)
                        for loser in losers:
                            kdaembed.add_field(name="",value=f"{loser['name']}님이 KDA 예측에 실패했습니다!", inline=False)
                    else: # KDA == 3
                        winners = p.kda_votes['up'] + p.kda_votes['down']
                        losers = p.kda_votes['perfect']
                        for winner in winners:
                            ref2 = db.reference(f'{current_predict_season}/예측포인트/{winner["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            ref2.update({"포인트": point + 20})
                            kdaembed.add_field(name="",value=f"{winner['name']}님이 KDA 예측에 성공하여 20점을 획득하셨습니다!", inline=False)
                        for loser in losers:
                            kdaembed.add_field(name="",value=f"{loser['name']}님이 KDA 예측에 실패했습니다!", inline=False)
                    await channel.send(embed=kdaembed)

                    if jimo_kda == 999:
                        refperfect.update({'지모': 500})
                    else:
                        refperfect.update({'지모': perfect_point + 5})
                    p.kda_votes['up'].clear()
                    p.kda_votes['down'].clear()
                    p.kda_votes['perfect'].clear()

                    p.jimo_event.set() # check_game_status의 대기 상태를 해제


        await asyncio.sleep(20)  # 20초마다 반복

async def check_melon_points(): #Melon의 솔로랭크 점수를 20초마다 확인하여 점수 변동이 있을 경우 알림
    await bot.wait_until_ready()
    id = MELON_ID
    channel = bot.get_channel(int(CHANNEL_ID))
    try:
        last_rank = await get_summoner_ranks(id)
        if not last_rank:
            last_total_match = 0
        else:
            last_win = last_rank['wins']
            last_loss = last_rank['losses']
            last_total_match = last_win + last_loss
    except NotFoundError as e:
        last_total_match = 0

    cur_predict_seasonref = db.reference("현재예측시즌")
    current_predict_season = cur_predict_seasonref.get()

    while not bot.is_closed():
        try:
          current_rank = await get_summoner_ranks(id)
        except Exception as e:
          print(f"Error in check_melon_points: {e}")
        if not current_rank:
            current_total_match = 0
        else:
            current_win = current_rank['wins']
            current_loss = current_rank['losses']
            current_total_match = current_win + current_loss
            if current_total_match != last_total_match:
                print(last_total_match, current_total_match)
                ref22 = db.reference(f'최근연속/Melon')
                points = ref22.get()

                game_win_streak = points["연승"]
                game_lose_streak = points["연패"]
                string = get_lp_and_tier_difference(last_rank, current_rank,"Melon")
                await bot.get_channel(int(NOTICE_CHANNEL_ID)).send("\nMelon의 솔로랭크 점수 변동이 감지되었습니다!\n"
                                    f"{string}")
                await bot.get_channel(int(CHANNEL_ID)).send("\nMelon의 솔로랭크 점수 변동이 감지되었습니다!\n"
                                    f"{string}")

                last_rank = current_rank
                last_total_match = current_total_match

                onoffref = db.reference("투표온오프")
                onoffbool = onoffref.get()
                if not onoffbool:
                    curseasonref = db.reference("현재시즌")
                    current_season = curseasonref.get()

                    # 현재 날짜 및 시간 가져오기
                    current_datetime = datetime.now()

                    # 날짜만 추출하여 저장
                    current_date = current_datetime.strftime("%Y-%m-%d")

                    # 시간만 추출하여 저장
                    current_time = current_datetime.strftime("%H:%M:%S")

                    ref = db.reference(f'{current_season}/점수변동/Melon')
                    points = ref.get()

                    # 가장 최근의 날짜를 찾음
                    latest_date = max(points.keys())

                    # 해당 날짜의 시간들을 정렬하여 가장 최근의 시간을 찾음
                    latest_time = max(points[latest_date].keys(), key=lambda t: datetime.strptime(t, '%H:%M:%S'))

                    # 가장 최근의 데이터
                    latest_data = points[latest_date][latest_time]

                    point_change = latest_data['LP 변화량']
                    if point_change > 0:
                        result = True
                    else:
                        result = False

                    userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                    userembed.add_field(name="게임 종료", value=f"Melon의 솔로랭크 게임이 종료되었습니다!\n"
                                         f"{'승리!' if result else '패배..'}\n"
                                         f"점수변동 : {point_change}")

                    if result:
                        winners = p.prediction_votes2['win']
                        losers = p.prediction_votes2['lose']

                        winnerNum = len(winners)
                        loserNum = len(losers)

                        if game_lose_streak >= 1:
                          streak_bonus_rate = calculate_bonus(game_lose_streak)
                        else:
                          streak_bonus_rate = 0

                        if winnerNum == 0:
                            BonusRate = 0
                        else:
                            BonusRate = round((((winnerNum+loserNum)/winnerNum) - 1) * 0.5,2) + 1  # 0.5배 배율 적용
                            BonusRate += streak_bonus_rate
                            BonusRate += 0.1

                        # 베팅 포인트를 전부 합산
                        winner_total_point = 0
                        for winner in winners:
                            winner_total_point += winner['points']

                        loser_total_point = 0
                        for loser in losers:
                            loser_total_point += loser['points']

                        remain_loser_total_point = loser_total_point

                        if BonusRate == 0:
                            userembed.add_field(name="",value=f"베팅 배율: {BonusRate}배", inline=False)
                        else:
                            userembed.add_field(name="",value=f"베팅 배율: {BonusRate}배!((({winnerNum+loserNum}/{winnerNum} - 1) x 0.5 + 1) + 역배 배율 {streak_bonus_rate} + 0.1)", inline=False)

                        for winner in winners:
                            ref2 = db.reference(f'{current_predict_season}/예측포인트/{winner["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            prediction_all = originr["총 예측 횟수"]
                            prediction_wins = originr["적중 횟수"]
                            prediction_win_rate = originr["적중률"]
                            win_streak = originr["연승"]
                            lose_streak = originr["연패"]
                            bettingPoint = originr["베팅포인트"]

                            ref3 = db.reference(f'{current_predict_season}/예측포인트변동로그/{current_date}/{current_time}/{winner["name"]}')
                            ref3.update({"포인트" : point})
                            ref3.update({"총 예측 횟수": prediction_all})
                            ref3.update({"적중 횟수" : prediction_wins})
                            ref3.update({"적중률": f"{prediction_win_rate}"})
                            ref3.update({"연승": win_streak})
                            ref3.update({"연패": lose_streak})
                            ref3.update({"베팅포인트" : 0})


                            ref2 = db.reference(f'{current_predict_season}/예측포인트/{winner["name"]}')
                            pointr = ref2.get()
                            point = pointr["포인트"]
                            streakr = ref2.get()
                            win_streak = streakr["연승"]
                            win_streak +=  1
                            lose_streak = streakr["연패"]
                            lose_streak = 0
                            bettingPoint -= winner['points']

                            prediction_all = pointr["총 예측 횟수"]
                            prediction_wins = pointr["적중 횟수"]

                            prediction_all += 1
                            prediction_wins += 1

                            # 이긴 팀에서 배팅한 비율
                            if winner_total_point == 0:
                                betted_rate = 0
                            else:
                                betted_rate = round(winner['points'] / winner_total_point, 1)

                            get_bet = 0
                            # 진 팀의 배팅 점수를 가져옴
                            get_bet = round(betted_rate * loser_total_point)

                            # 가져올 수 있는 최대 점수
                            get_bet_limit = round(BonusRate * winner['points'])

                            # 가져올 수 있는 최대 점수보다 높으면 최대 점수로 고정
                            if get_bet >= get_bet_limit:
                                get_bet = get_bet_limit

                            remain_loser_total_point -= get_bet

                            prediction_win_rate = round(((prediction_wins * 100) / prediction_all), 2)

                            if win_streak > 1:
                                add_points = point_change + (calculate_points(win_streak)) + round(winner['points']*BonusRate) + get_bet
                                userembed.add_field(name="",value=f"{winner['name']}님이 {win_streak}연속 적중을 이루어내며 {add_points}(연속적중 보너스 + {calculate_points(win_streak)})(베팅 보너스 + {round(winner['points']*BonusRate)} + {get_bet}) 점수를 획득하셨습니다! (베팅 포인트:{winner['points']})", inline=False)
                            else:
                                add_points = point_change + round(winner["points"]*BonusRate) + get_bet
                                userembed.add_field(name="",value=f"{winner['name']}님이 {add_points}(베팅 보너스 + {round(winner['points']*BonusRate)} + {get_bet}) 점수를 획득하셨습니다! (베팅 포인트:{winner['points']})", inline=False)
                        
                            point -= winner['points']
                            point += add_points
                            ref2.update({"포인트": point})
                            ref2.update({"총 예측 횟수": prediction_all})
                            ref2.update({"적중 횟수" : prediction_wins})
                            ref2.update({"적중률": f"{prediction_win_rate}%"})
                            ref2.update({"연승": win_streak})
                            ref2.update({"연패": lose_streak})
                            ref2.update({"베팅포인트" : bettingPoint})

                        for loser in losers:
                            ref2 = db.reference(f'{current_predict_season}/예측포인트/{loser["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            prediction_all = originr["총 예측 횟수"]
                            prediction_wins = originr["적중 횟수"]
                            prediction_win_rate = originr["적중률"]
                            win_streak = originr["연승"]
                            lose_streak = originr["연패"]
                            bettingPoint = originr["베팅포인트"]

                            ref3 = db.reference(f'{current_predict_season}/예측포인트변동로그/{current_date}/{current_time}/{loser["name"]}')
                            ref3.update({"포인트" : point})
                            ref3.update({"총 예측 횟수": prediction_all})
                            ref3.update({"적중 횟수" : prediction_wins})
                            ref3.update({"적중률": f"{prediction_win_rate}"})
                            ref3.update({"연승": win_streak})
                            ref3.update({"연패": lose_streak})
                            ref3.update({"베팅포인트" : 0})

                            ref2 = db.reference(f'{current_predict_season}/예측포인트/{loser["name"]}')
                            pointr = ref2.get()
                            point = pointr["포인트"]
                            streakr = ref2.get()
                            win_streak = streakr["연승"]
                            win_streak = 0
                            lose_streak = streakr["연패"]
                            lose_streak += 1
                            bettingPoint -= loser['points']

                            prediction_all = pointr["총 예측 횟수"]
                            prediction_wins = pointr["적중 횟수"]

                            # 진 팀에서 배팅한 비율
                            if loser_total_point != 0:
                                betted_rate = round(loser['points'] / loser_total_point, 1)
                            else:
                                betted_rate = 0

                            get_bet = 0
                            # 가져갈 포인트
                            get_bet = round(betted_rate * remain_loser_total_point * 0.5)

                            prediction_all += 1

                            prediction_win_rate = round(((prediction_wins * 100) / prediction_all), 2)

                            if point + get_bet < loser['points']:
                                point = 0
                            else:
                                point -= loser['points']
                                point += get_bet
                            ref2.update({"포인트": point})
                            ref2.update({"총 예측 횟수": prediction_all})
                            ref2.update({"적중 횟수" : prediction_wins})
                            ref2.update({"적중률": f"{prediction_win_rate}%"})
                            ref2.update({"연승": win_streak})
                            ref2.update({"연패": lose_streak})
                            ref2.update({"베팅포인트" : bettingPoint})


                            if loser['points'] == 0:
                                userembed.add_field(name="",value=f"{loser['name']}님이 예측에 실패했습니다! (베팅 포인트:{loser['points']})", inline=False)
                            else:
                                userembed.add_field(name="",value=f"{loser['name']}님이 예측에 실패하여 베팅포인트를 잃었습니다! (베팅 포인트:-{loser['points']}) (환급 포인트:{get_bet})", inline=False)

                    else:
                        winners = p.prediction_votes2['lose']
                        losers = p.prediction_votes2['win']

                        winnerNum = len(winners)
                        loserNum = len(losers)

                        # 연승 보너스
                        if game_win_streak >= 1:
                          streak_bonus_rate = calculate_bonus(game_win_streak)
                        else:
                          streak_bonus_rate = 0

                        if winnerNum == 0:
                            BonusRate = 0
                        else:
                            BonusRate = round((((winnerNum+loserNum)/winnerNum) - 1) * 0.5,2) + 1 #0.5배 배율 적용
                            BonusRate += streak_bonus_rate
                            BonusRate += 0.1

                        # 베팅 포인트를 전부 합산
                        winner_total_point = 0
                        for winner in winners:
                            winner_total_point += winner['points']

                        loser_total_point = 0
                        for loser in losers:
                            loser_total_point += loser['points']

                        remain_loser_total_point = loser_total_point

                        if BonusRate == 0:
                            userembed.add_field(name="",value=f"베팅 배율: {BonusRate}배", inline=False)
                        else:
                            userembed.add_field(name="",value=f"베팅 배율: {BonusRate}배!((({winnerNum+loserNum}/{winnerNum} - 1) x 0.5 + 1) + 역배 배율 {streak_bonus_rate} + 0.1)", inline=False)

                        for winner in winners:
                            ref2 = db.reference(f'{current_predict_season}/예측포인트/{winner["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            prediction_all = originr["총 예측 횟수"]
                            prediction_wins = originr["적중 횟수"]
                            prediction_win_rate = originr["적중률"]
                            win_streak = originr["연승"]
                            lose_streak = originr["연패"]
                            bettingPoint = originr["베팅포인트"]

                            ref3 = db.reference(f'{current_predict_season}/예측포인트변동로그/{current_date}/{current_time}/{winner["name"]}')
                            ref3.update({"포인트" : point})
                            ref3.update({"총 예측 횟수": prediction_all})
                            ref3.update({"적중 횟수" : prediction_wins})
                            ref3.update({"적중률": f"{prediction_win_rate}"})
                            ref3.update({"연승": win_streak})
                            ref3.update({"연패": lose_streak})
                            ref3.update({"베팅포인트" : 0})

                            ref2 = db.reference(f'{current_predict_season}/예측포인트/{winner["name"]}')
                            pointr = ref2.get()
                            point = pointr["포인트"]
                            streakr = ref2.get()
                            win_streak = streakr["연승"]
                            win_streak += 1
                            lose_streak = streakr["연패"]
                            lose_streak = 0
                            bettingPoint -= winner["points"]

                            winnerNum = len(winners)
                            loserNum = len(losers)

                            prediction_all = pointr["총 예측 횟수"]
                            prediction_wins = pointr["적중 횟수"]

                            prediction_all += 1
                            prediction_wins += 1

                            # 이긴 팀에서 배팅한 비율
                            if winner_total_point == 0:
                                betted_rate = 0
                            else:
                                betted_rate = round(winner['points'] / winner_total_point, 1)

                            get_bet = 0
                            # 진 팀의 배팅 점수를 가져옴
                            get_bet = round(betted_rate * loser_total_point)

                            # 가져올 수 있는 최대 점수
                            get_bet_limit = round(BonusRate * winner['points'])

                            # 가져올 수 있는 최대 점수보다 높으면 최대 점수로 고정
                            if get_bet >= get_bet_limit:
                                get_bet = get_bet_limit

                            remain_loser_total_point -= get_bet

                            prediction_win_rate = round(((prediction_wins * 100) / prediction_all), 2)

                            if win_streak > 1:
                                add_points = -point_change + (calculate_points(win_streak)) + round(winner['points']*BonusRate) + get_bet
                                userembed.add_field(name="",value=f"{winner['name']}님이 {win_streak}연속 적중을 이루어내며 {add_points}(연속적중 보너스 + {calculate_points(win_streak)})(베팅 보너스 + {round(winner['points']*BonusRate)} + {get_bet}) 점수를 획득하셨습니다! (베팅 포인트:{winner['points']})", inline=False)
                            else:
                                add_points = -point_change + round(winner["points"]*BonusRate) + get_bet
                                userembed.add_field(name="",value=f"{winner['name']}님이 {add_points}(베팅 보너스 + {round(winner['points']*BonusRate)}) 점수를 획득하셨습니다! (베팅 포인트:{winner['points']} + {get_bet})", inline=False)

                            point -= winner['points']
                            point += add_points
                            ref2.update({"포인트": point})
                            ref2.update({"총 예측 횟수": prediction_all})
                            ref2.update({"적중 횟수" : prediction_wins})
                            ref2.update({"적중률": f"{prediction_win_rate}%"})
                            ref2.update({"연승": win_streak})
                            ref2.update({"연패": lose_streak})
                            ref2.update({"베팅포인트" : bettingPoint})

                        losers = p.prediction_votes2['win']
                        for loser in losers:
                            ref2 = db.reference(f'{current_predict_season}/예측포인트/{loser["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            prediction_all = originr["총 예측 횟수"]
                            prediction_wins = originr["적중 횟수"]
                            prediction_win_rate = originr["적중률"]
                            win_streak = originr["연승"]
                            lose_streak = originr["연패"]
                            bettingPoint = originr["베팅포인트"]

                            ref3 = db.reference(f'{current_predict_season}/예측포인트변동로그/{current_date}/{current_time}/{loser["name"]}')
                            ref3.update({"포인트" : point})
                            ref3.update({"총 예측 횟수": prediction_all})
                            ref3.update({"적중 횟수" : prediction_wins})
                            ref3.update({"적중률": f"{prediction_win_rate}"})
                            ref3.update({"연승": win_streak})
                            ref3.update({"연패": lose_streak})
                            ref3.update({"베팅포인트" : 0})

                            ref2 = db.reference(f'{current_predict_season}/예측포인트/{loser["name"]}')
                            pointr = ref2.get()
                            point = pointr["포인트"]
                            streakr = ref2.get()
                            win_streak = streakr["연승"]
                            win_streak = 0
                            lose_streak = streakr["연패"]
                            lose_streak += 1
                            bettingPoint -= loser["points"]

                            prediction_all = pointr["총 예측 횟수"]
                            prediction_wins = pointr["적중 횟수"]

                            prediction_all += 1

                            # 진 팀에서 배팅한 비율
                            if loser_total_point != 0:
                                betted_rate = round(loser['points'] / loser_total_point, 1)
                            else:
                                betted_rate = 0

                            get_bet = 0
                            # 가져갈 포인트
                            get_bet = round(betted_rate * remain_loser_total_point * 0.5)

                            prediction_win_rate = round(((prediction_wins * 100) / prediction_all), 2)

                            if point + get_bet < loser['points']:
                                point = 0
                            else:
                                point -= loser['points']
                                point += get_bet
                            ref2.update({"포인트": point})
                            ref2.update({"총 예측 횟수": prediction_all})
                            ref2.update({"적중 횟수" : prediction_wins})
                            ref2.update({"적중률": f"{prediction_win_rate}%"})
                            ref2.update({"연승": win_streak})
                            ref2.update({"연패": lose_streak})
                            ref2.update({"베팅포인트" : bettingPoint})

                            if loser['points'] == 0:
                                userembed.add_field(name="",value=f"{loser['name']}님이 예측에 실패했습니다! (베팅 포인트:{loser['points']})", inline=False)
                            else:
                                userembed.add_field(name="",value=f"{loser['name']}님이 예측에 실패하여 베팅포인트를 잃었습니다! (베팅 포인트:-{loser['points']}) (환급 포인트:{get_bet})", inline=False)

                    await channel.send(embed=userembed)
                    p.prediction_votes2['win'].clear()
                    p.prediction_votes2['lose'].clear()

                    #KDA 결과 도출
                    #await asyncio.sleep(30) # 게임 종료 후 30초간 대기(최근 전적에 올라오는 시간 감안함)
                    melon_match_id = await get_summoner_recentmatch_id(MELON_PUUID)
                    match_info = await get_summoner_matchinfo(melon_match_id)

                    for player in match_info['info']['participants']:
                        if MELON_PUUID == player['puuid']:
                            if player['deaths'] == 0:
                                melon_kda = 999
                                melon_kill = player['kills']
                                melon_assist = player['assists']
                                melon_death = player['deaths']
                            else:
                                melon_kill = player['kills']
                                melon_assist = player['assists']
                                melon_death = player['deaths']
                                melon_kda = round((player['kills'] + player['assists'])/player['deaths'],1)

                    kdaembed = discord.Embed(title="Melon KDA 예측 결과", color=discord.Color.blue())

                    if melon_kda == 999:
                        kdaembed.add_field(name="Melon의 KDA",value=f"{melon_kill}/{melon_death}/{melon_assist}(PERFECT)", inline=False)
                    else:
                        kdaembed.add_field(name="Melon의 KDA",value=f"{melon_kill}/{melon_death}/{melon_assist}({melon_kda})", inline=False)

                    refperfect = db.reference('퍼펙트포인트')
                    perfectr = refperfect.get()
                    perfect_point = perfectr['Melon']

                    if melon_kda > 3:
                        if melon_kda == 999:
                            perfect_winners = p.kda_votes2['perfect']
                            winners = p.kda_votes2['up']
                            losers = p.kda_votes2['down']
                        else:
                            winners = p.kda_votes2['up']
                            losers = p.kda_votes2['down'] + p.kda_votes2['perfect']
                            perfect_winners = []
                        for perfect_winner in perfect_winners:
                            ref2 = db.reference(f'{current_predict_season}/예측포인트/{perfect_winner["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            ref2.update({"포인트": point + perfect_point})
                            kdaembed.add_field(name="",value=f"{perfect_winner['name']}님이 KDA 퍼펙트 예측에 성공하여 {perfect_point}점을 획득하셨습니다!", inline=False)
                        for winner in winners:
                            ref2 = db.reference(f'{current_predict_season}/예측포인트/{winner["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            ref2.update({"포인트": point + 20})
                            kdaembed.add_field(name="",value=f"{winner['name']}님이 KDA 예측에 성공하여 20점을 획득하셨습니다!", inline=False)
                        for loser in losers:
                            kdaembed.add_field(name="",value=f"{loser['name']}님이 KDA 예측에 실패했습니다!", inline=False)
                    elif melon_kda < 3:
                        winners = p.kda_votes2['down']
                        losers = p.kda_votes2['up']
                        for winner in winners:
                            ref2 = db.reference(f'{current_predict_season}/예측포인트/{winner["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            ref2.update({"포인트": point + 20})
                            kdaembed.add_field(name="",value=f"{winner['name']}님이 KDA 예측에 성공하여 20점을 획득하셨습니다!", inline=False)
                        for loser in losers:
                            kdaembed.add_field(name="",value=f"{loser['name']}님이 KDA 예측에 실패했습니다!", inline=False)
                    else: # KDA == 3
                        winners = p.kda_votes2['up'] + p.kda_votes2['down']
                        for winner in winners:
                            ref2 = db.reference(f'{current_predict_season}/예측포인트/{winner["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            ref2.update({"포인트": point + 20})
                            kdaembed.add_field(name="",value=f"{winner['name']}님이 KDA 예측에 성공하여 20점을 획득하셨습니다!", inline=False)
                    await channel.send(embed=kdaembed)

                    if melon_kda == 999:
                        refperfect.update({'Melon': 500})
                    else:
                        refperfect.update({'Melon': perfect_point + 5})

                    p.kda_votes2['up'].clear()
                    p.kda_votes2['down'].clear()
                    p.kda_votes2['perfect'].clear()

                    p.melon_event.set() # check_game_status2의 대기상태를 해제

        await asyncio.sleep(20)  # 20초마다 반복

async def check_points(puuid, summoner_id, name, channel_id, notice_channel_id, votes, event):
    await bot.wait_until_ready()
    channel = bot.get_channel(int(channel_id)) # 일반 채널
    notice_channel = bot.get_channel(int(notice_channel_id)) # 공지 채널
    
    prediction_votes = votes["prediction"]
    kda_votes = votes["kda"]
    try:
        last_rank = await get_summoner_ranks(summoner_id)
        if not last_rank:
            last_total_match = 0
        else:
            last_win = last_rank['wins']
            last_loss = last_rank['losses']
            last_total_match = last_win + last_loss
    except NotFoundError:
        last_total_match = 0

    cur_predict_seasonref = db.reference("현재예측시즌") # 현재 진행중인 예측 시즌을 가져옴
    current_predict_season = cur_predict_seasonref.get()

    while not bot.is_closed():
        try:
            current_rank = await get_summoner_ranks(summoner_id)
        except Exception as e:
            print(f"Error in check_points: {e}")
            current_rank = None

        if not current_rank:
            current_total_match = 0
        else:
            current_win = current_rank['wins']
            current_loss = current_rank['losses']
            current_total_match = current_win + current_loss
            if current_total_match != last_total_match:
                print(f"{name}의 {current_total_match}번째 게임 완료")
                string = get_lp_and_tier_difference(last_rank, current_rank, name)
                await notice_channel.send(f"\n{name}의 솔로랭크 점수 변동이 감지되었습니다!\n{string}")
                await channel.send(f"\n{name}의 솔로랭크 점수 변동이 감지되었습니다!\n{string}")

                last_rank = current_rank
                last_total_match = current_total_match

                onoffref = db.reference("투표온오프") # 투표가 off 되어있을 경우 결과 출력 X
                onoffbool = onoffref.get()
                if not onoffbool:
                    curseasonref = db.reference("현재시즌")
                    current_season = curseasonref.get()

                    current_datetime = datetime.now() # 데이터베이스에 남길 현재 시각 기록
                    current_date = current_datetime.strftime("%Y-%m-%d")
                    current_time = current_datetime.strftime("%H:%M:%S")

                    ref = db.reference(f'{current_season}/점수변동/{name}')
                    points = ref.get()

                    latest_date = max(points.keys()) # 가장 최근 기록을 가져옴
                    latest_time = max(points[latest_date].keys(), key=lambda t: datetime.strptime(t, '%H:%M:%S'))
                    latest_data = points[latest_date][latest_time]

                    # 게임의 연승/연패 기록을 가져옴 (연승/연패에 따른 추가 배율을 위함)
                    game_win_streak = latest_data["연승"]
                    game_lose_streak = latest_data["연패"]

                    point_change = latest_data['LP 변화량']
                    result = point_change > 0 # result가 True라면 승리

                    userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                    userembed.add_field(name="게임 종료", value=f"{name}의 솔로랭크 게임이 종료되었습니다!\n{'승리!' if result else '패배..'}\n점수변동: {point_change}")

                    winners = prediction_votes['win'] if result else prediction_votes['lose']
                    losers = prediction_votes['lose'] if result else prediction_votes['win']
                    winnerNum = len(winners)
                    loserNum = len(losers)

                    streak_bonus_rate = calculate_bonus(game_lose_streak if result else game_win_streak)

                    BonusRate = 0 if winnerNum == 0 else round((((winnerNum + loserNum) / winnerNum) - 1) * 0.5, 2) + 1 # 0.5배 배율 적용
                    BonusRate += streak_bonus_rate + 0.1

                    winner_total_point = sum(winner['points'] for winner in winners)
                    loser_total_point = sum(loser['points'] for loser in losers)
                    remain_loser_total_point = loser_total_point

                    userembed.add_field(
                        name="", 
                        value=f"베팅 배율: {BonusRate}배" if BonusRate == 0 else 
                        f"베팅 배율: {BonusRate}배!((({winnerNum + loserNum}/{winnerNum} - 1) x 0.5 + 1) + 역배 배율 {streak_bonus_rate} + 0.1)", 
                        inline=False
                    )

                    for winner in winners:
                        point_ref = db.reference(f'{current_predict_season}/예측포인트/{winner["name"]}')
                        predict_data = point_ref.get()
                        point = predict_data["포인트"]
                        bettingPoint = predict_data["베팅포인트"]

                        # 예측 내역 변동 데이터
                        change_ref = db.reference(f'{current_predict_season}/예측포인트변동로그/{current_date}/{current_time}/{winner["name"]}')
                        change_ref.update({"포인트": point, "총 예측 횟수": predict_data["총 예측 횟수"] + 1, "적중 횟수": predict_data["적중 횟수"] + 1, "적중률": f"{round(((predict_data['적중 횟수'] * 100) / (predict_data['총 예측 횟수'] + 1)), 2)}%", "연승": predict_data["연승"] + 1, "연패": 0, "베팅포인트": bettingPoint - winner["points"]})

                        # 예측 내역 업데이트
                        point_ref.update({"포인트": point, "총 예측 횟수": predict_data["총 예측 횟수"] + 1, "적중 횟수": predict_data["적중 횟수"] + 1, "적중률": f"{round(((predict_data['적중 횟수'] * 100) / (predict_data['총 예측 횟수'] + 1)), 2)}%", "연승": predict_data["연승"] + 1, "연패": 0, "베팅포인트": bettingPoint - winner["points"]})

                        betted_rate = round(winner['points'] / winner_total_point, 1) if winner_total_point else 0
                        get_bet = round(betted_rate * loser_total_point)
                        get_bet_limit = round(BonusRate * winner['points'])
                        if get_bet >= get_bet_limit:
                            get_bet = get_bet_limit

                        remain_loser_total_point -= get_bet
                        streak_text = f"{predict_data['연승'] + 1}연속 적중을 이루어내며 " if predict_data['연승'] + 1 > 1 else ""
                        add_points = point_change + (calculate_points(predict_data["연승"] + 1)) + round(winner['points'] * BonusRate) + get_bet if predict_data["연승"] + 1 > 1 else point_change + round(winner["points"] * BonusRate) + get_bet
                        userembed.add_field(name="", value=f"{winner['name']}님이 {streak_text}{add_points}(베팅 보너스 + {round(winner['points'] * BonusRate)} + {get_bet}) 점수를 획득하셨습니다!", inline=False)
                        point_ref.update({"포인트": point + add_points})

                    for loser in losers:
                        point_ref = db.reference(f'{current_predict_season}/예측포인트/{loser["name"]}')
                        predict_data = point_ref.get()
                        point = predict_data["포인트"]
                        bettingPoint = predict_data["베팅포인트"]

                        # 예측 내역 변동 데이터
                        change_ref = db.reference(f'{current_predict_season}/예측포인트변동로그/{current_date}/{current_time}/{loser["name"]}')
                        change_ref.update({"포인트": point, "총 예측 횟수": predict_data["총 예측 횟수"] + 1, "적중 횟수": predict_data["적중 횟수"], "적중률": f"{round(((predict_data['적중 횟수'] * 100) / (predict_data['총 예측 횟수'] + 1)), 2)}%", "연승": 0, "연패": predict_data["연패"] + 1, "베팅포인트": bettingPoint - loser["points"]})
                        
                        # 예측 내역 업데이트
                        point_ref.update({"포인트": point, "총 예측 횟수": predict_data["총 예측 횟수"] + 1, "적중 횟수": predict_data["적중 횟수"], "적중률": f"{round(((predict_data['적중 횟수'] * 100) / (predict_data['총 예측 횟수'] + 1)), 2)}%", "연승": 0, "연패": predict_data["연패"] + 1, "베팅포인트": bettingPoint - loser["points"]})

                        
                        # 남은 포인트를 배팅한 비율에 따라 환급받음 (50%)
                        betted_rate = round(loser['points'] / loser_total_point, 1) if loser_total_point else 0
                        get_bet = round(betted_rate * remain_loser_total_point * 0.5)
                        userembed.add_field(
                            name="",
                            value=f"{loser['name']}님이 예측에 실패하여 베팅포인트를 잃었습니다! " if loser['point'] == 0 else 
                            f"(베팅 포인트:-{loser['points']}) (환급 포인트: {get_bet})",
                            inline=False
                        )
                        if point + get_bet < loser['points']:
                            point_ref.update({"포인트": 0})
                        else:
                            point_ref.update({"포인트": point + get_bet})

                    await channel.send(embed=userembed)
                    prediction_votes['win'].clear()
                    prediction_votes['lose'].clear()

                    # KDA 예측
                    match_id = await get_summoner_recentmatch_id(puuid)
                    match_info = await get_summoner_matchinfo(match_id)

                    for player in match_info['info']['participants']:
                        if puuid == player['puuid']:
                            kda = 999 if player['deaths'] == 0 else round((player['kills'] + player['assists']) / player['deaths'], 1)
                            kdaembed = discord.Embed(title=f"{name} KDA 예측 결과", color=discord.Color.blue())
                            kdaembed.add_field(name=f"{name}의 KDA", value=f"{player['kills']}/{player['deaths']}/{player['assists']}({'PERFECT' if kda == 999 else kda})", inline=False)

                            refperfect = db.reference('퍼펙트포인트')
                            perfect_point = refperfect.get()[name]

                            if kda > 3:
                                perfect_winners = kda_votes['perfect'] if kda == 999 else []
                                winners = kda_votes['up']
                                losers = kda_votes['down'] + (kda_votes['perfect'] if kda != 999 else [])
                                for perfect_winner in perfect_winners:
                                    point_ref = db.reference(f'{current_predict_season}/예측포인트/{perfect_winner["name"]}')
                                    predict_data = point_ref.get()
                                    point_ref.update({"포인트": predict_data["포인트"] + perfect_point})
                                    kdaembed.add_field(name="", value=f"{perfect_winner['name']}님이 KDA 퍼펙트 예측에 성공하여 {perfect_point}점을 획득하셨습니다!", inline=False)
                                for winner in winners:
                                    point_ref = db.reference(f'{current_predict_season}/예측포인트/{winner["name"]}')
                                    predict_data = point_ref.get()
                                    point_ref.update({"포인트": predict_data["포인트"] + 20})
                                    kdaembed.add_field(name="", value=f"{winner['name']}님이 KDA 예측에 성공하여 20점을 획득하셨습니다!", inline=False)
                                for loser in losers:
                                    kdaembed.add_field(name="", value=f"{loser['name']}님이 KDA 예측에 실패했습니다!", inline=False)
                            else:
                                winners = kda_votes['down']
                                losers = kda_votes['up'] + kda_votes['perfect']
                                for winner in winners:
                                    point_ref = db.reference(f'{current_predict_season}/예측포인트/{winner["name"]}')
                                    predict_data = point_ref.get()
                                    point_ref.update({"포인트": predict_data["포인트"] + 20})
                                    kdaembed.add_field(name="", value=f"{winner['name']}님이 KDA 예측에 성공하여 20점을 획득하셨습니다!", inline=False)
                                for loser in losers:
                                    kdaembed.add_field(name="", value=f"{loser['name']}님이 KDA 예측에 실패했습니다!", inline=False)

                            await channel.send(embed=kdaembed)
                            refperfect.update({name: perfect_point + 5 if kda != 999 else 500})
                            kda_votes['up'].clear()
                            kda_votes['down'].clear()
                            kda_votes['perfect'].clear()
                            event.set()

        await asyncio.sleep(20)

async def check_game_status(): #지모의 솔로랭크가 진행중인지 20초마다 확인
    await bot.wait_until_ready()
    channel = bot.get_channel(int(CHANNEL_ID))
    notice_channel = bot.get_channel(int(NOTICE_CHANNEL_ID))

    cur_predict_seasonref = db.reference("현재예측시즌")
    current_predict_season = cur_predict_seasonref.get()

    while not bot.is_closed():
        p.jimo_current_game_state = await nowgame(JIMO_PUUID)
        #current_game_state = await test()
        if p.jimo_current_game_state:
                onoffref = db.reference("투표온오프")
                onoffbool = onoffref.get()

                anonymref = db.reference("익명온오프")
                anonymbool = anonymref.get()

                p.jimo_current_match_id = await get_summoner_recentmatch_id(JIMO_PUUID)

                p.jimo_winbutton = discord.ui.Button(style=discord.ButtonStyle.success,label="승리",disabled=onoffbool)
                p.jimo_losebutton = discord.ui.Button(style=discord.ButtonStyle.danger,label="패배",disabled=onoffbool)
                view = discord.ui.View()
                view.add_item(p.jimo_winbutton)
                view.add_item(p.jimo_losebutton)

                p.jimo_upbutton = discord.ui.Button(style=discord.ButtonStyle.success,label="업",disabled=onoffbool)
                p.jimo_downbutton = discord.ui.Button(style=discord.ButtonStyle.danger,label="다운",disabled=onoffbool)
                p.jimo_perfectbutton = discord.ui.Button(style=discord.ButtonStyle.primary,label="퍼펙트",disabled=onoffbool)
                kdaview = discord.ui.View()
                kdaview.add_item(p.jimo_upbutton)
                kdaview.add_item(p.jimo_downbutton)
                kdaview.add_item(p.jimo_perfectbutton)


                refperfect = db.reference('퍼펙트포인트')
                perfectr = refperfect.get()
                perfect_point = perfectr['지모']

                async def disable_buttons():
                    await asyncio.sleep(180)  # 3분 대기
                    view = discord.ui.View()
                    kdaview = discord.ui.View()
                    p.jimo_winbutton.disabled = True
                    p.jimo_losebutton.disabled = True
                    p.jimo_upbutton.disabled = True
                    p.jimo_downbutton.disabled = True
                    p.jimo_perfectbutton.disabled = True
                    view.add_item(p.jimo_winbutton)
                    view.add_item(p.jimo_losebutton)
                    kdaview.add_item(p.jimo_upbutton)
                    kdaview.add_item(p.jimo_downbutton)
                    kdaview.add_item(p.jimo_perfectbutton)
                    await p.current_message_jimo.edit(view = view)
                    await p.current_message_kda_jimo.edit(view = kdaview)

                async def winbutton_callback(interaction:discord.Interaction): # 승리 버튼을 눌렀을 때의 반응!
                    nickname = interaction.user
                    if (nickname.name not in [winner["name"] for winner in p.prediction_votes['win']] and
                        nickname.name not in [loser["name"] for loser in p.prediction_votes['lose']]):
                        refp = db.reference(f'{current_predict_season}/예측포인트/{nickname.name}')

                        pointr = refp.get()
                        point = pointr["포인트"]
                        bettingPoint = pointr["베팅포인트"]

                        random_number = random.uniform(0.01, 0.1)
                        baseRate = round(random_number, 2)
                        # 자동 베팅
                        if point - bettingPoint >= 500:
                          basePoint = round(point*baseRate)
                        else:
                          basePoint = 0

                        refp.update({"베팅포인트" : bettingPoint + basePoint})
                        p.prediction_votes['win'].append({"name": nickname.name, 'points': basePoint})
                        myindex = len(p.prediction_votes["win"]) - 1
                        p.prediction_embed = discord.Embed(title="예측 현황", color=discord.Color.blue())

                        if anonymbool: # 익명 투표 시
                          win_predictions = "\n".join(
                            f"{ANONYM_NAME_WIN[index]}: ? 포인트" for index,winner in enumerate(p.prediction_votes["win"])) or "없음"
                          lose_predictions = "\n".join(
                            f"{ANONYM_NAME_LOSE[index]}: ? 포인트" for index,loser in enumerate(p.prediction_votes["lose"])) or "없음"
                        else:
                          win_predictions = "\n".join(
                            f"{winner['name']}: {winner['points']}포인트" for winner in p.prediction_votes["win"]) or "없음"
                          lose_predictions = "\n".join(
                            f"{loser['name']}: {loser['points']}포인트" for loser in p.prediction_votes["lose"]) or "없음"
                        p.prediction_embed.add_field(name="승리 예측", value=win_predictions, inline=True)
                        p.prediction_embed.add_field(name="패배 예측", value=lose_predictions, inline=True)

                        if anonymbool: # 익명 투표 시
                          userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                          userembed.add_field(name="",value=f"{ANONYM_NAME_WIN[myindex]}님이 승리에 투표하셨습니다.", inline=True)
                          if basePoint != 0:
                            bettingembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
                            bettingembed.add_field(name="",value=f"누군가가 지모의 승리에 {basePoint}포인트를 베팅했습니다!", inline=False)
                        else:
                          userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                          userembed.add_field(name="",value=f"{nickname}님이 승리에 투표하셨습니다.", inline=True)
                          if basePoint != 0:
                            bettingembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
                            bettingembed.add_field(name="",value=f"{nickname}님이 지모의 승리에 {basePoint}포인트를 베팅했습니다!", inline=False)
                            await channel.send(f"\n",embed = bettingembed)
                        await interaction.response.send_message(embed=userembed)

                    else:
                        userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                        userembed.add_field(name="",value=f"{nickname}님은 이미 투표하셨습니다", inline=True)
                        await interaction.response.send_message(embed=userembed, ephemeral=True)
                        return

                    if p.current_message_jimo:
                        await p.current_message_jimo.edit(embed = p.prediction_embed)
                    if basePoint != 0 and anonymbool:
                        delay = random.uniform(5, 20)
                        await asyncio.sleep(delay)
                        await channel.send(f"\n",embed = bettingembed)

                async def losebutton_callback(interaction:discord.Interaction): # 패배 버튼을 눌렀을 때의 반응!
                    nickname = interaction.user
                    if (nickname.name not in [winner["name"] for winner in p.prediction_votes['win']] and
                        nickname.name not in [loser["name"] for loser in p.prediction_votes['lose']]):

                        refp = db.reference(f'{current_predict_season}/예측포인트/{nickname.name}')

                        pointr = refp.get()
                        point = pointr["포인트"]
                        bettingPoint = pointr["베팅포인트"]
                        random_number = random.uniform(0.01, 0.1)
                        baseRate = round(random_number, 2)
                        # 자동 베팅
                        if point - bettingPoint >= 500:
                          basePoint = round(point*baseRate)
                        else:
                          basePoint = 0

                        refp.update({"베팅포인트" : bettingPoint + basePoint})
                        p.prediction_votes['lose'].append({"name": nickname.name, 'points': basePoint})
                        myindex = len(p.prediction_votes["lose"]) - 1
                        p.prediction_embed = discord.Embed(title="예측 현황", color=discord.Color.blue())

                        if anonymbool: # 익명 투표 시
                          win_predictions = "\n".join(
                            f"{ANONYM_NAME_WIN[index]}: ? 포인트" for index,winner in enumerate(p.prediction_votes["win"])) or "없음"
                          lose_predictions = "\n".join(
                            f"{ANONYM_NAME_LOSE[index]}: ? 포인트" for index,loser in enumerate(p.prediction_votes["lose"])) or "없음"
                        else:
                          win_predictions = "\n".join(
                              f"{winner['name']}: {winner['points']}포인트" for winner in p.prediction_votes["win"]) or "없음"
                          lose_predictions = "\n".join(
                              f"{loser['name']}: {loser['points']}포인트" for loser in p.prediction_votes["lose"]) or "없음"
                        p.prediction_embed.add_field(name="승리 예측", value=win_predictions, inline=True)
                        p.prediction_embed.add_field(name="패배 예측", value=lose_predictions, inline=True)

                        if anonymbool: # 익명 투표 시
                          userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                          userembed.add_field(name="",value=f"{ANONYM_NAME_LOSE[myindex]}님이 패배에 투표하셨습니다.", inline=True)
                          if basePoint != 0:
                            bettingembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
                            bettingembed.add_field(name="",value=f"누군가가 지모의 패배에 {basePoint}포인트를 베팅했습니다!", inline=False)

                        else:
                          userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                          userembed.add_field(name="",value=f"{nickname}님이 패배에 투표하셨습니다.", inline=True)
                          if basePoint != 0:
                            bettingembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
                            bettingembed.add_field(name="",value=f"{nickname}님이 지모의 패배에 {basePoint}포인트를 베팅했습니다!", inline=False)
                            await channel.send(f"\n",embed = bettingembed)

                        await interaction.response.send_message(embed=userembed)
                    else:
                        userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                        userembed.add_field(name="",value=f"{nickname}님은 이미 투표하셨습니다", inline=True)
                        await interaction.response.send_message(embed=userembed, ephemeral=True)
                        return

                    if p.current_message_jimo:
                        await p.current_message_jimo.edit(embed = p.prediction_embed)
                    if basePoint != 0 and anonymbool:
                        delay = random.uniform(5, 20)
                        await asyncio.sleep(delay)
                        await channel.send(f"\n",embed = bettingembed)

                async def upbutton_callback(interaction:discord.Interaction): # 업 버튼을 눌렀을 때의 반응!
                    nickname = interaction.user
                    if (nickname.name not in [upper["name"] for upper in p.kda_votes['up']] and
                    nickname.name not in [downer["name"] for downer in p.kda_votes['down']] and
                    nickname.name not in [perfecter["name"] for perfecter in p.kda_votes['perfect']]):
                        p.kda_votes['up'].append({"name": nickname.name})
                        p.kda_embed = discord.Embed(title="KDA 예측 현황", color=discord.Color.blue())
                        p.kda_embed.add_field(name="퍼펙트 예측성공 포인트", value=perfect_point, inline=False)
                        up_predictions = "".join(
                        f"{len(p.kda_votes['up'])}명")
                        down_predictions = "".join(
                        f"{len(p.kda_votes['down'])}명")
                        perfect_predictions = "".join(
                        f"{len(p.kda_votes['perfect'])}명")
                        p.kda_embed.add_field(name="KDA 3 이상 예측", value=up_predictions, inline=True)
                        p.kda_embed.add_field(name="KDA 3 이하 예측", value=down_predictions, inline=True)
                        p.kda_embed.add_field(name="KDA 퍼펙트 예측", value=perfect_predictions, inline=True)

                        userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                        userembed.add_field(name="",value=f"누군가가 지모의 KDA를 3 이상으로 예측했습니다!", inline=True)
                        await interaction.response.send_message(embed=userembed)

                    else:
                        userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                        userembed.add_field(name="",value=f"{nickname}님은 이미 투표하셨습니다", inline=True)
                        await interaction.response.send_message(embed=userembed, ephemeral=True)
                        return

                    if p.current_message_kda_jimo:
                        await p.current_message_kda_jimo.edit(embed = p.kda_embed)

                async def downbutton_callback(interaction:discord.Interaction): # 다운 버튼을 눌렀을 때의 반응!
                    nickname = interaction.user
                    if (nickname.name not in [upper["name"] for upper in p.kda_votes['up']] and
                    nickname.name not in [downer["name"] for downer in p.kda_votes['down']] and
                    nickname.name not in [perfecter["name"] for perfecter in p.kda_votes['perfect']]):
                        p.kda_votes['down'].append({"name": nickname.name})
                        p.kda_embed = discord.Embed(title="KDA 예측 현황", color=discord.Color.blue())
                        p.kda_embed.add_field(name="퍼펙트 예측성공 포인트", value=perfect_point, inline=False)
                        up_predictions = "".join(
                        f"{len(p.kda_votes['up'])}명")
                        down_predictions = "".join(
                        f"{len(p.kda_votes['down'])}명")
                        perfect_predictions = "".join(
                        f"{len(p.kda_votes['perfect'])}명")
                        p.kda_embed.add_field(name="KDA 3 이상 예측", value=up_predictions, inline=True)
                        p.kda_embed.add_field(name="KDA 3 이하 예측", value=down_predictions, inline=True)
                        p.kda_embed.add_field(name="KDA 퍼펙트 예측", value=perfect_predictions, inline=True)

                        userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                        userembed.add_field(name="",value=f"누군가가 지모의 KDA를 3 이하로 예측했습니다!", inline=True)
                        await interaction.response.send_message(embed=userembed)

                    else:
                        userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                        userembed.add_field(name="",value=f"{nickname}님은 이미 투표하셨습니다", inline=True)
                        await interaction.response.send_message(embed=userembed, ephemeral=True)
                        return
                    if p.current_message_kda_jimo:
                        await p.current_message_kda_jimo.edit(embed = p.kda_embed)

                async def perfectbutton_callback(interaction:discord.Interaction): # 퍼펙트 버튼을 눌렀을 때의 반응!
                    nickname = interaction.user
                    if (nickname.name not in [upper["name"] for upper in p.kda_votes['up']] and
                    nickname.name not in [downer["name"] for downer in p.kda_votes['down']] and
                    nickname.name not in [perfecter["name"] for perfecter in p.kda_votes['perfect']]):
                        p.kda_votes['perfect'].append({"name": nickname.name})
                        p.kda_embed = discord.Embed(title="KDA 예측 현황", color=discord.Color.blue())
                        p.kda_embed.add_field(name="퍼펙트 예측성공 포인트", value=perfect_point, inline=False)
                        up_predictions = "".join(
                        f"{len(p.kda_votes['up'])}명")
                        down_predictions = "".join(
                        f"{len(p.kda_votes['down'])}명")
                        perfect_predictions = "".join(
                        f"{len(p.kda_votes['perfect'])}명")
                        p.kda_embed.add_field(name="KDA 3 이상 예측", value=up_predictions, inline=True)
                        p.kda_embed.add_field(name="KDA 3 이하 예측", value=down_predictions, inline=True)
                        p.kda_embed.add_field(name="KDA 퍼펙트 예측", value=perfect_predictions, inline=True)

                        userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                        userembed.add_field(name="",value=f"누군가가 지모의 KDA를 0 데스, 퍼펙트로 예측했습니다!", inline=True)
                        await interaction.response.send_message(embed=userembed)

                    else:
                        userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                        userembed.add_field(name="",value=f"{nickname}님은 이미 투표하셨습니다", inline=True)
                        await interaction.response.send_message(embed=userembed, ephemeral=True)
                        return
                    if p.current_message_kda_jimo:
                        await p.current_message_kda_jimo.edit(embed = p.kda_embed)

                p.jimo_winbutton.callback = winbutton_callback
                p.jimo_losebutton.callback = losebutton_callback
                p.jimo_upbutton.callback = upbutton_callback
                p.jimo_downbutton.callback = downbutton_callback
                p.jimo_perfectbutton.callback = perfectbutton_callback

                p.prediction_embed = discord.Embed(title="예측 현황", color=discord.Color.blue())

                if anonymbool: # 익명 투표 시
                  win_predictions = "\n".join(
                    f"{ANONYM_NAME_WIN[index]}: ? 포인트" for index,winner in enumerate(p.prediction_votes["win"])) or "없음"
                  lose_predictions = "\n".join(
                    f"{ANONYM_NAME_LOSE[index]}: ? 포인트" for index,loser in enumerate(p.prediction_votes["lose"])) or "없음"
                else:
                  win_predictions = "\n".join(
                      f"{winner['name']}: {winner['points']}포인트" for winner in p.prediction_votes["win"] ) or "없음"
                  lose_predictions = "\n".join(
                      f"{loser['name']}: {loser['points']}포인트" for loser in p.prediction_votes["lose"]) or "없음"
                p.prediction_embed.add_field(name="승리 예측", value=win_predictions, inline=True)
                p.prediction_embed.add_field(name="패배 예측", value=lose_predictions, inline=True)


                p.kda_embed = discord.Embed(title="KDA 예측 현황", color=discord.Color.blue())
                p.kda_embed.add_field(name="퍼펙트 예측성공 포인트", value=perfect_point, inline=False)
                up_predictions = "".join(
                f"{len(p.kda_votes['up'])}명")
                down_predictions = "".join(
                f"{len(p.kda_votes['down'])}명")
                perfect_predictions = "".join(
                f"{len(p.kda_votes['perfect'])}명")

                p.kda_embed.add_field(name="KDA 3 이상 예측", value=up_predictions, inline=True)
                p.kda_embed.add_field(name="KDA 3 이하 예측", value=down_predictions, inline=True)
                p.kda_embed.add_field(name="KDA 퍼펙트 예측", value=perfect_predictions, inline=True)

                curseasonref = db.reference("현재시즌")
                current_season = curseasonref.get()

                refprev = db.reference(f'{current_season}/점수변동/지모')
                points = refprev.get()

                if points is None:
                    game_win_streak = 0
                    game_lose_streak = 0
                else:
                    # 가장 최근의 날짜를 찾음
                    latest_date = max(points.keys())

                    # 해당 날짜의 시간들을 정렬하여 가장 최근의 시간을 찾음
                    latest_time = max(points[latest_date].keys(), key=lambda t: datetime.strptime(t, '%H:%M:%S'))

                    # 가장 최근의 데이터
                    latest_data = points[latest_date][latest_time]

                    game_win_streak = latest_data["연승"]
                    game_lose_streak = latest_data["연패"]

                    if game_win_streak >= 1:
                      streak_bonusRate = calculate_bonus(game_win_streak)
                          
                      p.current_message_jimo = await channel.send("\n지모의 솔로랭크 게임이 감지되었습니다!\n"
                                    "승부예측을 해보세요!\n"
                                    f"{game_win_streak}연승으로 패배 시 배율 {streak_bonusRate} 추가!",
                                    view = view, embed = p.prediction_embed)
                    elif game_lose_streak >= 1:
                      streak_bonusRate = calculate_bonus(game_lose_streak)

                      p.current_message_jimo = await channel.send("\n지모의 솔로랭크 게임이 감지되었습니다!\n"
                                    "승부예측을 해보세요!\n"
                                    f"{game_lose_streak}연패로 승리 시 배율 {streak_bonusRate} 추가!",
                                    view = view, embed = p.prediction_embed)
                    else:
                      p.current_message_jimo = await channel.send("\n지모의 솔로랭크 게임이 감지되었습니다!\n"
                                    "승부예측을 해보세요!\n",
                                    view = view, embed = p.prediction_embed)

                # kda 예측
                    p.current_message_kda_jimo = await channel.send("\n",view = kdaview, embed = p.kda_embed)
                if onoffbool == False:
                    await notice_channel.send("지모의 솔로랭크 게임이 감지되었습니다!\n"
                                            "승부예측을 해보세요!\n")
                p.jimo_event.clear()
                await asyncio.gather(
                    disable_buttons(),
                    p.jimo_event.wait()  # 이 작업은 jimo_event가 set될 때까지 대기
                )
                print("check_game_status 대기 종료")

        await asyncio.sleep(20)  # 20초마다 반복

async def check_game_status2(): #Melon의 솔로랭크가 진행중인지 20초마다 확인
    await bot.wait_until_ready()
    channel = bot.get_channel(int(CHANNEL_ID))
    notice_channel = bot.get_channel(int(NOTICE_CHANNEL_ID))

    cur_predict_seasonref = db.reference("현재예측시즌")
    current_predict_season = cur_predict_seasonref.get()

    while not bot.is_closed():
        p.melon_current_game_state = await nowgame(MELON_PUUID)
        if p.melon_current_game_state:
                onoffref = db.reference("투표온오프")
                onoffbool = onoffref.get()

                anonymref = db.reference("익명온오프")
                anonymbool = anonymref.get()

                p.melon_current_match_id = await get_summoner_recentmatch_id(MELON_PUUID)

                p.melon_winbutton = discord.ui.Button(style=discord.ButtonStyle.success,label="승리",disabled=onoffbool)
                p.melon_losebutton = discord.ui.Button(style=discord.ButtonStyle.danger,label="패배",disabled=onoffbool)
                view = discord.ui.View()
                view.add_item(p.melon_winbutton)
                view.add_item(p.melon_losebutton)

                p.melon_upbutton = discord.ui.Button(style=discord.ButtonStyle.success,label="업",disabled=onoffbool)
                p.melon_downbutton = discord.ui.Button(style=discord.ButtonStyle.danger,label="다운",disabled=onoffbool)
                p.melon_perfectbutton = discord.ui.Button(style=discord.ButtonStyle.primary,label="퍼펙트",disabled=onoffbool)
                kdaview = discord.ui.View()
                kdaview.add_item(p.melon_upbutton)
                kdaview.add_item(p.melon_downbutton)
                kdaview.add_item(p.melon_perfectbutton)

                async def disable_buttons():
                    await asyncio.sleep(180)  # 3분 대기
                    view = discord.ui.View()
                    kdaview = discord.ui.View()
                    p.melon_winbutton.disabled = True
                    p.melon_losebutton.disabled = True
                    p.melon_upbutton.disabled = True
                    p.melon_downbutton.disabled = True
                    p.melon_perfectbutton.disabled = True
                    view.add_item(p.melon_winbutton)
                    view.add_item(p.melon_losebutton)
                    kdaview.add_item(p.melon_upbutton)
                    kdaview.add_item(p.melon_downbutton)
                    kdaview.add_item(p.melon_perfectbutton)
                    await p.current_message_melon.edit(view = view)
                    await p.current_message_kda_melon.edit(view = kdaview)

                refperfect = db.reference('퍼펙트포인트')
                perfectr = refperfect.get()
                perfect_point = perfectr['Melon']

                async def winbutton_callback2(interaction:discord.Interaction):
                    nickname = interaction.user
                    if (nickname.name not in [winner["name"] for winner in p.prediction_votes2['win']] and
                        nickname.name not in [loser["name"] for loser in p.prediction_votes2['lose']]):
                        refp = db.reference(f'{current_predict_season}/예측포인트/{nickname.name}')

                        pointr = refp.get()
                        point = pointr["포인트"]
                        bettingPoint = pointr["베팅포인트"]
                        random_number = random.uniform(0.01, 0.1)
                        baseRate = round(random_number, 2)
                        # 자동 베팅
                        if point - bettingPoint >= 500:
                          basePoint = round(point*baseRate)
                        else:
                          basePoint = 0

                        refp.update({"베팅포인트" : bettingPoint + basePoint})
                        p.prediction_votes2['win'].append({"name": nickname.name, 'points': basePoint})
                        myindex = len(p.prediction_votes2['win']) - 1
                        p.prediction2_embed = discord.Embed(title="예측 현황", color=discord.Color.blue())

                        if anonymbool: # 익명 투표 시
                          win_predictions = "\n".join(
                            f"{ANONYM_NAME_WIN[index]}: ? 포인트" for index,winner in enumerate(p.prediction_votes2["win"])) or "없음"
                          lose_predictions = "\n".join(
                            f"{ANONYM_NAME_LOSE[index]}: ? 포인트" for index,loser in enumerate(p.prediction_votes2["lose"])) or "없음"
                        else:
                          win_predictions = "\n".join(
                            f"{winner['name']}: {winner['points']}포인트" for winner in p.prediction_votes2["win"]) or "없음"
                          lose_predictions = "\n".join(
                            f"{loser['name']}: {loser['points']}포인트" for loser in p.prediction_votes2["lose"]) or "없음"
                        p.prediction2_embed.add_field(name="승리 예측", value=win_predictions, inline=True)
                        p.prediction2_embed.add_field(name="패배 예측", value=lose_predictions, inline=True)

                        if anonymbool: # 익명 투표 시
                          userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                          userembed.add_field(name="",value=f"{ANONYM_NAME_WIN[myindex]}님이 승리에 투표하셨습니다.", inline=True)
                          if basePoint != 0:
                            bettingembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
                            bettingembed.add_field(name="",value=f"누군가가 Melon의 승리에 {basePoint}포인트를 베팅했습니다!", inline=False)
                        else:
                          userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                          userembed.add_field(name="",value=f"{nickname}님이 승리에 투표하셨습니다.", inline=True)
                          if basePoint != 0:
                            bettingembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
                            bettingembed.add_field(name="",value=f"{nickname}님이 Melon의 승리에 {basePoint}포인트를 베팅했습니다!", inline=False)
                            await channel.send(f"\n",embed = bettingembed)

                        await interaction.response.send_message(embed=userembed)
                    else:
                        userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                        userembed.add_field(name="",value=f"{nickname}님은 이미 투표하셨습니다", inline=True)
                        await interaction.response.send_message(embed=userembed, ephemeral=True)
                        return

                    if p.current_message_melon:
                        await p.current_message_melon.edit(embed = p.prediction2_embed)
                    if basePoint != 0 and anonymbool:
                        delay = random.uniform(5, 20)
                        await asyncio.sleep(delay)
                        await channel.send(f"\n",embed = bettingembed)
                async def losebutton_callback2(interaction:discord.Interaction):
                    nickname = interaction.user
                    if (nickname.name not in [winner["name"] for winner in p.prediction_votes2['win']] and
                        nickname.name not in [loser["name"] for loser in p.prediction_votes2['lose']]):
                        refp = db.reference(f'{current_predict_season}/예측포인트/{nickname.name}')

                        pointr = refp.get()
                        point = pointr["포인트"]
                        bettingPoint = pointr["베팅포인트"]
                        random_number = random.uniform(0.01, 0.1)
                        baseRate = round(random_number, 2)
                        # 자동 베팅
                        if point - bettingPoint >= 500:
                          basePoint = round(point*baseRate)
                        else:
                          basePoint = 0

                        refp.update({"베팅포인트" : bettingPoint + basePoint})
                        p.prediction_votes2['lose'].append({"name": nickname.name, 'points': basePoint})
                        myindex = len(p.prediction_votes2['lose']) - 1
                        p.prediction2_embed = discord.Embed(title="예측 현황", color=discord.Color.blue())
                        if anonymbool: # 익명 투표 시
                          win_predictions = "\n".join(
                            f"{ANONYM_NAME_WIN[index]}: ? 포인트" for index,winner in enumerate(p.prediction_votes2["win"])) or "없음"
                          lose_predictions = "\n".join(
                            f"{ANONYM_NAME_LOSE[index]}: ? 포인트" for index,loser in enumerate(p.prediction_votes2["lose"])) or "없음"
                        else:
                          win_predictions = "\n".join(
                              f"{winner['name']}: {winner['points']}포인트" for winner in p.prediction_votes2["win"]) or "없음"
                          lose_predictions = "\n".join(
                              f"{loser['name']}: {loser['points']}포인트" for loser in p.prediction_votes2["lose"]) or "없음"
                        p.prediction2_embed.add_field(name="승리 예측", value=win_predictions, inline=True)
                        p.prediction2_embed.add_field(name="패배 예측", value=lose_predictions, inline=True)

                        if anonymbool: # 익명 투표 시
                          userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                          userembed.add_field(name="",value=f"{ANONYM_NAME_LOSE[myindex]}님이 패배에 투표하셨습니다.", inline=True)
                          if basePoint != 0:
                            bettingembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
                            bettingembed.add_field(name="",value=f"누군가가 Melon의 패배에 {basePoint}포인트를 베팅했습니다!", inline=False)
                        else:
                          userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                          userembed.add_field(name="",value=f"{nickname}님이 패배에 투표하셨습니다.", inline=True)
                          if basePoint != 0:
                            bettingembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
                            bettingembed.add_field(name="",value=f"{nickname}님이 Melon의 패배에 {basePoint}포인트를 베팅했습니다!", inline=False)
                            await channel.send(f"\n",embed = bettingembed)

                        await interaction.response.send_message(embed=userembed)
                    else:
                        userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                        userembed.add_field(name="",value=f"{nickname}님은 이미 투표하셨습니다", inline=True)
                        await interaction.response.send_message(embed=userembed, ephemeral=True)
                        return
                    if p.current_message_melon:
                        await p.current_message_melon.edit(embed = p.prediction2_embed)
                    if basePoint != 0 and anonymbool:
                        delay = random.uniform(5, 20)
                        await asyncio.sleep(delay)
                        await channel.send(f"\n",embed = bettingembed)
                async def upbutton_callback2(interaction:discord.Interaction): # 업 버튼을 눌렀을 때의 반응!
                    nickname = interaction.user
                    if (nickname.name not in [upper["name"] for upper in p.kda_votes2['up']] and
                    nickname.name not in [downer["name"] for downer in p.kda_votes2['down']] and
                    nickname.name not in [perfecter["name"] for perfecter in p.kda_votes2['perfect']]):
                        p.kda_votes2['up'].append({"name": nickname.name})
                        p.kda_embed = discord.Embed(title="KDA 예측 현황", color=discord.Color.blue())
                        p.kda_embed.add_field(name="퍼펙트 예측성공 포인트", value=perfect_point, inline=False)
                        up_predictions = "".join(
                        f"{len(p.kda_votes2['up'])}명")
                        down_predictions = "".join(
                        f"{len(p.kda_votes2['down'])}명")
                        perfect_predictions = "".join(
                        f"{len(p.kda_votes2['perfect'])}명")
                        p.kda_embed.add_field(name="KDA 3 이상 예측", value=up_predictions, inline=True)
                        p.kda_embed.add_field(name="KDA 3 이하 예측", value=down_predictions, inline=True)
                        p.kda_embed.add_field(name="KDA 퍼펙트 예측", value=perfect_predictions, inline=True)

                        userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                        userembed.add_field(name="",value=f"누군가가 Melon의 KDA를 3 이상으로 예측했습니다!", inline=True)
                        await interaction.response.send_message(embed=userembed)

                    else:
                        userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                        userembed.add_field(name="",value=f"{nickname}님은 이미 투표하셨습니다", inline=True)
                        await interaction.response.send_message(embed=userembed, ephemeral=True)
                        return

                    if p.current_message_kda_melon:
                        await p.current_message_kda_melon.edit(embed = p.kda_embed)

                async def downbutton_callback2(interaction:discord.Interaction): # 다운 버튼을 눌렀을 때의 반응!
                    nickname = interaction.user
                    if (nickname.name not in [upper["name"] for upper in p.kda_votes2['up']] and
                    nickname.name not in [downer["name"] for downer in p.kda_votes2['down']] and
                    nickname.name not in [perfecter["name"] for perfecter in p.kda_votes2['perfect']]):
                        p.kda_votes2['down'].append({"name": nickname.name})
                        p.kda_embed = discord.Embed(title="KDA 예측 현황", color=discord.Color.blue())
                        p.kda_embed.add_field(name="퍼펙트 예측성공 포인트", value=perfect_point, inline=False)
                        up_predictions = "".join(
                        f"{len(p.kda_votes2['up'])}명")
                        down_predictions = "".join(
                        f"{len(p.kda_votes2['down'])}명")
                        perfect_predictions = "".join(
                        f"{len(p.kda_votes2['perfect'])}명")
                        p.kda_embed.add_field(name="KDA 3 이상 예측", value=up_predictions, inline=True)
                        p.kda_embed.add_field(name="KDA 3 이하 예측", value=down_predictions, inline=True)
                        p.kda_embed.add_field(name="KDA 퍼펙트 예측", value=perfect_predictions, inline=True)

                        userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                        userembed.add_field(name="",value=f"누군가가 Melon의 KDA를 3 이하로 예측했습니다!", inline=True)
                        await interaction.response.send_message(embed=userembed)

                    else:
                        userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                        userembed.add_field(name="",value=f"{nickname}님은 이미 투표하셨습니다", inline=True)
                        await interaction.response.send_message(embed=userembed, ephemeral=True)
                        return
                    if p.current_message_kda_melon:
                        await p.current_message_kda_melon.edit(embed = p.kda_embed)

                async def perfectbutton_callback2(interaction:discord.Interaction): # 퍼펙트 버튼을 눌렀을 때의 반응!
                    nickname = interaction.user
                    if (nickname.name not in [upper["name"] for upper in p.kda_votes2['up']] and
                    nickname.name not in [downer["name"] for downer in p.kda_votes2['down']] and
                    nickname.name not in [perfecter["name"] for perfecter in p.kda_votes2['perfect']]):
                        p.kda_votes2['perfect'].append({"name": nickname.name})
                        p.kda_embed = discord.Embed(title="KDA 예측 현황", color=discord.Color.blue())
                        p.kda_embed.add_field(name="퍼펙트 예측성공 포인트", value=perfect_point, inline=False)
                        up_predictions = "".join(
                        f"{len(p.kda_votes2['up'])}명")
                        down_predictions = "".join(
                        f"{len(p.kda_votes2['down'])}명")
                        perfect_predictions = "".join(
                        f"{len(p.kda_votes2['perfect'])}명")
                        p.kda_embed.add_field(name="KDA 3 이상 예측", value=up_predictions, inline=True)
                        p.kda_embed.add_field(name="KDA 3 이하 예측", value=down_predictions, inline=True)
                        p.kda_embed.add_field(name="KDA 퍼펙트 예측", value=perfect_predictions, inline=True)

                        userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                        userembed.add_field(name="",value=f"누군가가 Melon의 KDA를 0 데스, 퍼펙트로 예측했습니다!", inline=True)
                        await interaction.response.send_message(embed=userembed)

                    else:
                        userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                        userembed.add_field(name="",value=f"{nickname}님은 이미 투표하셨습니다", inline=True)
                        await interaction.response.send_message(embed=userembed, ephemeral=True)
                        return
                    if p.current_message_kda_melon:
                        await p.current_message_kda_melon.edit(embed = p.kda_embed)

                p.melon_winbutton.callback = winbutton_callback2
                p.melon_losebutton.callback = losebutton_callback2
                p.melon_upbutton.callback = upbutton_callback2
                p.melon_downbutton.callback = downbutton_callback2
                p.melon_perfectbutton.callback = perfectbutton_callback2

                p.prediction2_embed = discord.Embed(title="예측 현황", color=discord.Color.blue())

                if anonymbool: # 익명 투표 시
                  win_predictions = "\n".join(
                    f"{ANONYM_NAME_WIN[index]}: ? 포인트" for index,winner in enumerate(p.prediction_votes2["win"])) or "없음"
                  lose_predictions = "\n".join(
                    f"{ANONYM_NAME_LOSE[index]}: ? 포인트" for index,loser in enumerate(p.prediction_votes2["lose"])) or "없음"
                else:
                  win_predictions = "\n".join(
                    f"{winner['name']}: {winner['points']}포인트" for winner in p.prediction_votes2["win"] ) or "없음"
                  lose_predictions = "\n".join(
                    f"{loser['name']}: {loser['points']}포인트" for loser in p.prediction_votes2["lose"]) or "없음"
                p.prediction2_embed.add_field(name="승리 예측", value=win_predictions, inline=True)
                p.prediction2_embed.add_field(name="패배 예측", value=lose_predictions, inline=True)

                p.kda_embed = discord.Embed(title="KDA 예측 현황", color=discord.Color.blue())
                p.kda_embed.add_field(name="퍼펙트 예측성공 포인트", value=perfect_point, inline=False)
                up_predictions = "".join(
                f"{len(p.kda_votes2['up'])}명")
                down_predictions = "".join(
                f"{len(p.kda_votes2['down'])}명")
                perfect_predictions = "".join(
                f"{len(p.kda_votes2['perfect'])}명")

                p.kda_embed.add_field(name="KDA 3 이상 예측", value=up_predictions, inline=True)
                p.kda_embed.add_field(name="KDA 3 이하 예측", value=down_predictions, inline=True)
                p.kda_embed.add_field(name="KDA 퍼펙트 예측", value=perfect_predictions, inline=True)

                curseasonref = db.reference("현재시즌")
                current_season = curseasonref.get()

                refprev = db.reference(f'{current_season}/점수변동/Melon')
                points = refprev.get()

                if points is None:
                    game_win_streak = 0
                    game_lose_streak = 0
                else:
                    # 가장 최근의 날짜를 찾음
                    latest_date = max(points.keys())

                    # 해당 날짜의 시간들을 정렬하여 가장 최근의 시간을 찾음
                    latest_time = max(points[latest_date].keys(), key=lambda t: datetime.strptime(t, '%H:%M:%S'))

                    # 가장 최근의 데이터
                    latest_data = points[latest_date][latest_time]

                    game_win_streak = latest_data["연승"]
                    game_lose_streak = latest_data["연패"]

                    if game_win_streak >= 1:
                      streak_bonusRate = calculate_bonus(game_win_streak)

                      p.current_message_melon = await channel.send("\nMelon의 솔로랭크 게임이 감지되었습니다!\n"
                                    "승부예측을 해보세요!\n"
                                    f"{game_win_streak}연승으로 패배 시 배율 {streak_bonusRate} 추가!",
                                    view = view, embed = p.prediction2_embed)
                    elif game_lose_streak >= 1:
                      streak_bonusRate = calculate_bonus(game_lose_streak)

                      p.current_message_melon = await channel.send("\nMelon의 솔로랭크 게임이 감지되었습니다!\n"
                                    "승부예측을 해보세요!\n"
                                    f"{game_lose_streak}연패로 승리 시 배율 {streak_bonusRate} 추가!",
                                    view = view, embed = p.prediction2_embed)
                    else:
                      p.current_message_melon = await channel.send("\nMelon의 솔로랭크 게임이 감지되었습니다!\n"
                                    "승부예측을 해보세요!\n",
                                    view = view, embed = p.prediction2_embed)
                # kda 예측
                    p.current_message_kda_melon = await channel.send("\n",view = kdaview, embed = p.kda_embed)
                if onoffbool == False:
                    await notice_channel.send("Melon의 솔로랭크 게임이 감지되었습니다!\n"
                                            "승부예측을 해보세요!\n")
                p.melon_event.clear()
                await asyncio.gather(
                    disable_buttons(),
                    p.melon_event.wait()  # 이 작업은 melon_event가 set될 때까지 대기
                )

        await asyncio.sleep(20)  # 20초마다 반복

async def open_prediction(name, puuid, votes, channel_id, notice_channel_id, event, attrs, buttons, prediction_embed):
    await bot.wait_until_ready()
    channel = bot.get_channel(int(channel_id))
    notice_channel = bot.get_channel(int(notice_channel_id))

    cur_predict_seasonref = db.reference("현재예측시즌")
    current_predict_season = cur_predict_seasonref.get()

    while not bot.is_closed():
        setattr(p, attrs['current_game_state_attr'], await nowgame(puuid))
        if getattr(p, attrs['current_game_state_attr']):
            onoffref = db.reference("투표온오프")
            onoffbool = onoffref.get()

            anonymref = db.reference("익명온오프")
            anonymbool = anonymref.get()

            setattr(p, attrs['current_match_id_attr'], await get_summoner_recentmatch_id(puuid))

            buttons['win_button'] = discord.ui.Button(style=discord.ButtonStyle.success,label="승리",disabled=onoffbool)
            buttons['lose_button'] = discord.ui.Button(style=discord.ButtonStyle.danger,label="패배",disabled=onoffbool)

            prediction_view = discord.ui.View()
            prediction_view.add_item(buttons['win_button'])
            prediction_view.add_item(buttons['lose_button'])

            buttons['up_button'] = discord.ui.Button(style=discord.ButtonStyle.success,label="업",disabled=onoffbool)
            buttons['down_button'] = discord.ui.Button(style=discord.ButtonStyle.danger,label="다운",disabled=onoffbool)
            buttons['perfect_button'] = discord.ui.Button(style=discord.ButtonStyle.primary,label="퍼펙트",disabled=onoffbool)

            kda_view = discord.ui.View()
            kda_view.add_item(buttons['up_button'])
            kda_view.add_item(buttons['down_button'])
            kda_view.add_item(buttons['perfect_button'])
            
            refperfect = db.reference('퍼펙트포인트')
            perfectr = refperfect.get()
            perfect_point = perfectr[name]
                
            async def disable_buttons():
                await asyncio.sleep(180)  # 3분 대기
                prediction_view = discord.ui.View()
                kda_view = discord.ui.View()
                buttons['win_button'].disabled = True
                buttons['lose_button'].disabled = True
                buttons['up_button'].disabled = True
                buttons['down_button'].disabled = True
                buttons['perfect_button'].disabled = True
                prediction_view.add_item(buttons['win_button'])
                prediction_view.add_item(buttons['lose_button'])
                kda_view.add_item(buttons['up_button'])
                kda_view.add_item(buttons['down_button'])
                kda_view.add_item(buttons['perfect_button'])
                await getattr(p, attrs['current_message_attr']).edit(view=prediction_view)
                await getattr(p, attrs['current_message_kda_attr']).edit(view=kda_view)

            prediction_votes = votes["prediction"]
            kda_votes = votes["kda"]
            
            async def bet_button_callback(interaction: discord.Interaction, prediction_type: str, anonym_names: list):
                nickname = interaction.user
                if (nickname.name not in [user["name"] for user in prediction_votes["win"]]) and (nickname.name not in [user["name"] for user in prediction_votes["lose"]]):
                    refp = db.reference(f'{current_predict_season}/예측포인트/{nickname.name}')
                    pointr = refp.get()
                    point = pointr["포인트"]
                    bettingPoint = pointr["베팅포인트"]
                    random_number = random.uniform(0.01, 0.1) # 1% ~ 10% 랜덤 배팅 할 비율을 정합
                    baseRate = round(random_number, 2)
                    basePoint = round(point * baseRate) if point - bettingPoint >= 500 else 0 # 500p 이상 보유 시 자동 베팅

                    refp.update({"베팅포인트": bettingPoint + basePoint})
                    prediction_votes[prediction_type].append({"name": nickname.name, 'points': basePoint})
                    myindex = len(prediction_votes[prediction_type]) - 1 # 투표자의 위치 파악

                    embed = discord.Embed(title="예측 현황", color=discord.Color.blue())
                    if anonymbool:
                        win_predictions = "\n".join(f"{anonym_names[index]}: ? 포인트" for index, user in enumerate(prediction_votes["win"])) or "없음"
                        lose_predictions = "\n".join(f"{anonym_names[index]}: ? 포인트" for index, user in enumerate(prediction_votes["lose"])) or "없음"
                    else:
                        win_predictions = "\n".join(f"{user['name']}: {user['points']}포인트" for user in prediction_votes["win"]) or "없음"
                        lose_predictions = "\n".join(f"{user['name']}: {user['points']}포인트" for user in prediction_votes["lose"]) or "없음"

                    embed.add_field(name="승리 예측", value=win_predictions, inline=True)
                    embed.add_field(name="패배 예측", value=lose_predictions, inline=True)

                    userembed = discord.Embed(title="메세지", color=discord.Color.blue())

                    prediction_value = "승리" if prediction_type == "win" else "패배"
                    if anonymbool:
                        userembed.add_field(name="", value=f"{anonym_names[myindex]}님이 {prediction_value}에 투표하셨습니다.", inline=True)
                        if basePoint != 0:
                            bettingembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
                            bettingembed.add_field(name="", value=f"누군가가 {name}의 {prediction_value}에 {basePoint}포인트를 베팅했습니다!", inline=False)
                    else:
                        userembed.add_field(name="", value=f"{nickname}님이 {prediction_value}에 투표하셨습니다.", inline=True)
                        if basePoint != 0:
                            bettingembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
                            bettingembed.add_field(name="", value=f"{nickname}님이 {name}의 {prediction_value}에 {basePoint}포인트를 베팅했습니다!", inline=False)
                            await channel.send(f"\n", embed=bettingembed)
                    
                    await interaction.response.send_message(embed=userembed)

                    if getattr(p, attrs['current_message_attr']): # p.current_message:
                        await getattr(p, attrs['current_message_attr']).edit(embed=embed)
                    if basePoint != 0 and anonymbool:
                        delay = random.uniform(5, 120) # 5초부터 2분까지 랜덤 시간
                        await asyncio.sleep(delay)
                        await channel.send(f"\n", embed=bettingembed)
                else:
                    userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                    userembed.add_field(name="", value=f"{nickname}님은 이미 투표하셨습니다", inline=True)
                    await interaction.response.send_message(embed=userembed, ephemeral=True)

            async def kda_button_callback(interaction: discord.Interaction, prediction_type: str):
                nickname = interaction.user
                if (nickname.name not in [user["name"] for user in kda_votes["up"]] )and (nickname.name not in [user["name"] for user in kda_votes["down"]]) and (nickname.name not in [user["name"] for user in kda_votes["perfect"]]):
                    kda_votes[prediction_type].append({"name": nickname.name})
                    embed = discord.Embed(title="KDA 예측 현황", color=discord.Color.blue())
                    embed.add_field(name="퍼펙트 예측성공 포인트", value=perfect_point, inline=False)

                    up_predictions = "".join(f"{len(kda_votes['up'])}명")
                    down_predictions = "".join(f"{len(kda_votes['down'])}명")
                    perfect_predictions = "".join(f"{len(kda_votes['perfect'])}명")

                    embed.add_field(name="KDA 3 이상 예측", value=up_predictions, inline=True)
                    embed.add_field(name="KDA 3 이하 예측", value=down_predictions, inline=True)
                    embed.add_field(name="KDA 퍼펙트 예측", value=perfect_predictions, inline=True)

                    userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                    if prediction_type == 'up':
                        userembed.add_field(name="", value=f"누군가가 {name}의 KDA를 3 이상으로 예측했습니다!", inline=True)
                    elif prediction_type == 'down':
                        userembed.add_field(name="", value=f"누군가가 {name}의 KDA를 3 이하로 예측했습니다!", inline=True)
                    else:
                        userembed.add_field(name="", value=f"누군가가 {name}의 KDA를 0 데스, 퍼펙트로 예측했습니다!", inline=True)
                    
                    await interaction.response.send_message(embed=userembed)

                    if getattr(p, attrs['current_message_kda_attr']):
                        await getattr(p, attrs['current_message_kda_attr']).edit(embed=embed)
                else:
                    userembed = discord.Embed(title="메세지", color=discord.Color.blue())
                    userembed.add_field(name="", value=f"{nickname}님은 이미 투표하셨습니다", inline=True)
                    await interaction.response.send_message(embed=userembed, ephemeral=True)

            buttons['win_button'].callback = lambda interaction: bet_button_callback(interaction, 'win', ANONYM_NAME_WIN)
            buttons['lose_button'].callback = lambda interaction: bet_button_callback(interaction, 'lose', ANONYM_NAME_LOSE)
            buttons['up_button'].callback = lambda interaction: kda_button_callback(interaction, 'up')
            buttons['down_button'].callback = lambda interaction: kda_button_callback(interaction, 'down')
            buttons['perfect_button'].callback = lambda interaction: kda_button_callback(interaction, 'perfect')

            prediction_embed = discord.Embed(title="예측 현황", color=discord.Color.blue())

            if anonymbool:  # 익명 투표 시
                win_predictions = "\n".join(
                    f"{ANONYM_NAME_WIN[index]}: ? 포인트" for index, winner in enumerate(prediction_votes["win"])) or "없음"
                lose_predictions = "\n".join(
                    f"{ANONYM_NAME_LOSE[index]}: ? 포인트" for index, loser in enumerate(prediction_votes["lose"])) or "없음"
            else:
                win_predictions = "\n".join(
                    f"{winner['name']}: {winner['points']}포인트" for winner in prediction_votes["win"]) or "없음"
                lose_predictions = "\n".join(
                    f"{loser['name']}: {loser['points']}포인트" for loser in prediction_votes["lose"]) or "없음"
            prediction_embed.add_field(name="승리 예측", value=win_predictions, inline=True)
            prediction_embed.add_field(name="패배 예측", value=lose_predictions, inline=True)

            p.kda_embed = discord.Embed(title="KDA 예측 현황", color=discord.Color.blue())
            p.kda_embed.add_field(name="퍼펙트 예측성공 포인트", value=perfect_point, inline=False)
            up_predictions = "".join(
                f"{len(kda_votes['up'])}명")
            down_predictions = "".join(
                f"{len(kda_votes['down'])}명")
            perfect_predictions = "".join(
                f"{len(kda_votes['perfect'])}명")
            p.kda_embed.add_field(name="KDA 3 이상 예측", value=up_predictions, inline=True)
            p.kda_embed.add_field(name="KDA 3 이하 예측", value=down_predictions, inline=True)
            p.kda_embed.add_field(name="KDA 퍼펙트 예측", value=perfect_predictions, inline=True)

            curseasonref = db.reference("현재시즌")
            current_season = curseasonref.get()

            refprev = db.reference(f'{current_season}/점수변동/{name}')
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
                    setattr(p, attrs['current_message_attr'], await channel.send(f"\n{name}의 솔로랭크 게임이 감지되었습니다!\n승부예측을 해보세요!\n{game_win_streak}연승으로 패배 시 배율 {streak_bonusRate} 추가!", view=prediction_view, embed=prediction_embed))
                elif game_lose_streak >= 1:
                    streak_bonusRate = calculate_bonus(game_lose_streak)
                    setattr(p, attrs['current_message_attr'], await channel.send(f"\n{name}의 솔로랭크 게임이 감지되었습니다!\n승부예측을 해보세요!\n{game_lose_streak}연패로 승리 시 배율 {streak_bonusRate} 추가!", view=prediction_view, embed=prediction_embed))
                else:
                    setattr(p, attrs['current_message_attr'], await channel.send(f"\n{name}의 솔로랭크 게임이 감지되었습니다!\n승부예측을 해보세요!\n", view=prediction_view, embed=prediction_embed))
                setattr(p, attrs['current_message_kda_attr'], await channel.send("\n", view=kda_view, embed=p.kda_embed))

            if not onoffbool:
                await notice_channel.send(f"{name}의 솔로랭크 게임이 감지되었습니다!\n승부예측을 해보세요!\n")

            event.clear()
            await asyncio.gather(
                disable_buttons(),
                event.wait()  # 이 작업은 event가 set될 때까지 대기
            )
            print(f"check_game_status for {name} 대기 종료")

    await asyncio.sleep(20)  # 20초마다 반복

async def check_jimo_remake_status(): # 지모의 다시하기 여부를 확인!
    channel = bot.get_channel(int(CHANNEL_ID))
    last_game_state = False

    cur_predict_seasonref = db.reference("현재예측시즌")
    current_predict_season = cur_predict_seasonref.get()

    while not bot.is_closed():
        current_game_state = await nowgame(JIMO_PUUID)
        # JIMO의 상태가 변했는지 확인
        if current_game_state != last_game_state: # 게임 상태가 변화했을 경우!
            if not current_game_state: # 게임이 종료되었을 경우!
                # 과거 매치 ID를 가져옴
                previous_match_id = p.jimo_current_match_id

                await asyncio.sleep(30) # 게임 종료 후 30초간 대기(최근 전적에 올라오는 시간 감안함)
                # 현재 매치 ID를 가져옴
                current_match_id = await get_summoner_recentmatch_id(JIMO_PUUID)

                if not p.jimo_event.is_set(): # 게임이 정상적으로 끝나지 않았을 경우?
                    # 매치 ID가 바뀌었는지 비교
                    if previous_match_id != current_match_id: #새로운 매치가 추가되었을 경우!
                        match_info = await get_summoner_matchinfo(current_match_id)
                        participant_id = get_participant_id(match_info, JIMO_PUUID)

                        # 다시하기 조건 확인
                        if match_info['info']['participants'][participant_id]['gameEndedInEarlySurrender'] and int(match_info['info']['gameDuration']) <= 240:
                            userembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
                            userembed.add_field(name="게임 종료", value="지모의 솔로랭크 게임이 종료되었습니다!\n다시하기\n")
                            await channel.send(embed=userembed)

                            winners = p.prediction_votes['win']
                            losers = p.prediction_votes['lose']
                            for winner in winners:
                                ref = db.reference(f'{current_predict_season}/예측포인트/{winner["name"]}')
                                originr = ref.get()
                                bettingPoint = originr["베팅포인트"]
                                bettingPoint -= winner['points'] # 베팅 포인트 돌려줌
                                ref.update({"베팅포인트" : bettingPoint})
                            for loser in losers:
                                ref = db.reference(f'{current_predict_season}/예측포인트/{loser["name"]}')
                                originr = ref.get()
                                bettingPoint = originr["베팅포인트"]
                                bettingPoint -= loser['points'] # 베팅 포인트 돌려줌
                                ref.update({"베팅포인트" : bettingPoint})
                            p.jimo_event.set() # check_game_status의 대기상태를 해제!
                            # 투표 결과 초기화
                            p.prediction_votes['win'].clear()
                            p.prediction_votes['lose'].clear()

        # 일정 시간 간격으로 확인
        await asyncio.sleep(20)  # 원하는 간격으로 설정

async def check_melon_remake_status(): # Melon의 다시하기 여부를 확인!
    channel = bot.get_channel(int(CHANNEL_ID))
    last_game_state = False

    cur_predict_seasonref = db.reference("현재예측시즌")
    current_predict_season = cur_predict_seasonref.get()

    while not bot.is_closed():
        current_game_state = await nowgame(MELON_PUUID)
        # Melon의 상태가 변했는지 확인
        if current_game_state != last_game_state: # 게임 상태가 변화했을 경우!
            if not current_game_state: # 게임이 종료되었을 경우!
                # 과거 매치 ID를 가져옴
                previous_match_id = p.melon_current_match_id

                await asyncio.sleep(30) # 게임 종료 후 30초간 대기(최근 전적에 올라오는 시간 감안함)
                # 현재 매치 ID를 가져옴
                current_match_id = await get_summoner_recentmatch_id(MELON_PUUID)


                if not p.melon_event.is_set(): # 게임이 정상적으로 끝나지 않았을 경우?
                    # 매치 ID가 바뀌었는지 비교
                    if previous_match_id != current_match_id: #새로운 매치가 추가되었을 경우!
                        match_info = await get_summoner_matchinfo(current_match_id)
                        participant_id = get_participant_id(match_info, MELON_PUUID)

                        # 다시하기 조건 확인
                        if match_info['info']['participants'][participant_id]['gameEndedInEarlySurrender'] and int(match_info['info']['gameDuration']) <= 240:
                            userembed = discord.Embed(title="메세지", color=discord.Color.light_gray())
                            userembed.add_field(name="게임 종료", value="Melon의 솔로랭크 게임이 종료되었습니다!\n다시하기\n")
                            await channel.send(embed=userembed)

                            winners = p.prediction_votes2['win']
                            losers = p.prediction_votes2['lose']
                            for winner in winners:
                                ref = db.reference(f'{current_predict_season}/예측포인트/{winner["name"]}')
                                originr = ref.get()
                                bettingPoint = originr["베팅포인트"]
                                bettingPoint -= winner['points'] # 베팅 포인트 돌려줌
                                ref.update({"베팅포인트" : bettingPoint})
                            for loser in losers:
                                ref = db.reference(f'{current_predict_season}/예측포인트/{loser["name"]}')
                                originr = ref.get()
                                bettingPoint = originr["베팅포인트"]
                                bettingPoint -= loser['points'] # 베팅 포인트 돌려줌
                                ref.update({"베팅포인트" : bettingPoint})

                            p.melon_event.set() # check_game_status2의 대기상태를 해제!
                            # 투표 결과 초기화
                            p.prediction_votes2['win'].clear()
                            p.prediction_votes2['lose'].clear()

        # 일정 시간 간격으로 확인
        await asyncio.sleep(20)  # 원하는 간격으로 설정

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

        #bot.loop.create_task(check_jimo_points())
        #bot.loop.create_task(check_melon_points())
        #bot.loop.create_task(check_game_status())
        #bot.loop.create_task(check_game_status2())

        # Task for Jimo
        bot.loop.create_task(open_prediction(
            name="지모", 
            puuid=JIMO_PUUID, 
            votes=p.votes['지모'], 
            channel_id=CHANNEL_ID, 
            notice_channel_id=NOTICE_CHANNEL_ID, 
            event=p.jimo_event, 
            attrs={
                'current_game_state_attr': 'jimo_current_game_state', 
                'current_match_id_attr': 'jimo_current_match_id', 
                'current_message_attr': 'current_message_jimo', 
                'current_message_kda_attr': 'current_message_kda_jimo'
            }, 
            buttons={
                'win_button': p.jimo_winbutton, 
                'lose_button': p.jimo_losebutton, 
                'up_button': p.jimo_upbutton, 
                'down_button': p.jimo_downbutton, 
                'perfect_button': p.jimo_perfectbutton
            }, 
            prediction_embed=p.prediction_embed
        ))

        # Task for Melon
        bot.loop.create_task(open_prediction(
            name="Melon", 
            puuid=MELON_PUUID, 
            votes=p.votes['Melon'], 
            channel_id=CHANNEL_ID, 
            notice_channel_id=NOTICE_CHANNEL_ID, 
            event=p.melon_event, 
            attrs={
                'current_game_state_attr': 'melon_current_game_state', 
                'current_match_id_attr': 'melon_current_match_id', 
                'current_message_attr': 'current_message_melon', 
                'current_message_kda_attr': 'current_message_kda_melon'
            }, 
            buttons={
                'win_button': p.melon_winbutton, 
                'lose_button': p.melon_losebutton, 
                'up_button': p.melon_upbutton, 
                'down_button': p.melon_downbutton, 
                'perfect_button': p.melon_perfectbutton
            }, 
            prediction_embed=p.prediction2_embed
        ))

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
        bot.loop.create_task(check_jimo_remake_status())
        bot.loop.create_task(check_melon_remake_status())

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