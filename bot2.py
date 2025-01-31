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

PREDICT_SEASON = "예측시즌3"
CURRENT_SEASON = "시즌15"
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
                        if game_lose_streak >= 3:
                          streak_bonus = game_lose_streak * 3
                          streak_bonus_rate = round(game_lose_streak * 0.3,1)
                        else:
                          streak_bonus = 0
                          streak_bonus_rate = 0


                        if winnerNum == 0:
                            BonusRate = 0
                        else:
                            BonusRate = ((winnerNum+loserNum)/winnerNum)
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
                            userembed.add_field(name="",value=f"베팅 배율: {BonusRate}배!({winnerNum+loserNum}/{winnerNum} + 역배 배율 {streak_bonus_rate} + 0.1)", inline=False)

                        for winner in winners:
                            ref2 = db.reference(f'{PREDICT_SEASON}/예측포인트/{winner["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            prediction_all = originr["총 예측 횟수"]
                            prediction_wins = originr["적중 횟수"]
                            prediction_win_rate = originr["적중률"]
                            win_streak = originr["연승"]
                            lose_streak = originr["연패"]
                            bettingPoint = originr["베팅포인트"]

                            ref3 = db.reference(f'{PREDICT_SEASON}/예측포인트변동로그/{current_date}/{current_time}/{winner["name"]}')
                            ref3.update({"포인트" : point})
                            ref3.update({"총 예측 횟수": prediction_all})
                            ref3.update({"적중 횟수" : prediction_wins})
                            ref3.update({"적중률": f"{prediction_win_rate}"})
                            ref3.update({"연승": win_streak})
                            ref3.update({"연패": lose_streak})
                            ref3.update({"베팅포인트" : 0})

                            ref2 = db.reference(f'{PREDICT_SEASON}/예측포인트/{winner["name"]}')
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
                              if streak_bonus == 0:
                                add_points = point_change + (win_streak * 2) + round(winner['points']*BonusRate) + get_bet
                                userembed.add_field(name="",value=f"{winner['name']}님이 {win_streak}연속 적중을 이루어내며 {add_points}(연속적중 보너스 + {win_streak * 2})(베팅 보너스 + {round(winner['points']*BonusRate)} + {get_bet}) 점수를 획득하셨습니다! (베팅 포인트:{winner['points']})", inline=False)
                              else:
                                add_points = point_change + (win_streak * 2) + round(winner['points']*BonusRate) + streak_bonus + get_bet
                                userembed.add_field(name="",value=f"{winner['name']}님이 {win_streak}연속 적중을 이루어내며 {add_points}(연속적중 보너스 + {win_streak * 2})(베팅 보너스 + {round(winner['points']*BonusRate)} + {get_bet})(역배 보너스 + {streak_bonus}) 점수를 획득하셨습니다! (베팅 포인트:{winner['points']})", inline=False)
                            else:
                              if streak_bonus == 0:
                                add_points = point_change + round(winner["points"]*BonusRate) + get_bet
                                userembed.add_field(name="",value=f"{winner['name']}님이 {add_points}(베팅 보너스 + {round(winner['points']*BonusRate)} + {get_bet}) 점수를 획득하셨습니다! (베팅 포인트:{winner['points']})", inline=False)
                              else:
                                add_points = point_change + round(winner["points"]*BonusRate) + streak_bonus + get_bet
                                userembed.add_field(name="",value=f"{winner['name']}님이 {add_points}(베팅 보너스 + {round(winner['points']*BonusRate)} + {get_bet})(역배 보너스 + {streak_bonus}) 점수를 획득하셨습니다! (베팅 포인트:{winner['points']})", inline=False)

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
                            ref2 = db.reference(f'{PREDICT_SEASON}/예측포인트/{loser["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            prediction_all = originr["총 예측 횟수"]
                            prediction_wins = originr["적중 횟수"]
                            prediction_win_rate = originr["적중률"]
                            win_streak = originr["연승"]
                            lose_streak = originr["연패"]
                            bettingPoint = originr["베팅포인트"]

                            ref3 = db.reference(f'{PREDICT_SEASON}/예측포인트변동로그/{current_date}/{current_time}/{loser["name"]}')
                            ref3.update({"포인트" : point})
                            ref3.update({"총 예측 횟수": prediction_all})
                            ref3.update({"적중 횟수" : prediction_wins})
                            ref3.update({"적중률": f"{prediction_win_rate}"})
                            ref3.update({"연승": win_streak})
                            ref3.update({"연패": lose_streak})
                            ref3.update({"베팅포인트" : 0})


                            ref2 = db.reference(f'{PREDICT_SEASON}/예측포인트/{loser["name"]}')
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
                        if game_win_streak >= 3:
                          streak_bonus = game_win_streak * 3
                          streak_bonus_rate = round(game_win_streak * 0.3,1)
                        else:
                          streak_bonus = 0
                          streak_bonus_rate = 0

                        if winnerNum == 0:
                            BonusRate = 0
                        else:
                            BonusRate = ((winnerNum+loserNum)/winnerNum)
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
                            userembed.add_field(name="",value=f"베팅 배율: {BonusRate}배!({winnerNum+loserNum}/{winnerNum} + 역배 배율 {streak_bonus_rate} + 0.1)", inline=False)


                        for winner in winners:
                            ref2 = db.reference(f'{PREDICT_SEASON}/예측포인트/{winner["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            prediction_all = originr["총 예측 횟수"]
                            prediction_wins = originr["적중 횟수"]
                            prediction_win_rate = originr["적중률"]
                            win_streak = originr["연승"]
                            lose_streak = originr["연패"]
                            bettingPoint = originr["베팅포인트"]

                            ref3 = db.reference(f'{PREDICT_SEASON}/예측포인트변동로그/{current_date}/{current_time}/{winner["name"]}')
                            ref3.update({"포인트" : point})
                            ref3.update({"총 예측 횟수": prediction_all})
                            ref3.update({"적중 횟수" : prediction_wins})
                            ref3.update({"적중률": f"{prediction_win_rate}"})
                            ref3.update({"연승": win_streak})
                            ref3.update({"연패": lose_streak})
                            ref3.update({"베팅포인트" : 0})

                            ref2 = db.reference(f'{PREDICT_SEASON}/예측포인트/{winner["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            prediction_all = originr["총 예측 횟수"]
                            prediction_wins = originr["적중 횟수"]
                            prediction_win_rate = originr["적중률"]
                            win_streak = originr["연승"]
                            lose_streak = originr["연패"]
                            bettingPoint -= winner["points"]


                            ref2 = db.reference(f'{PREDICT_SEASON}/예측포인트/{winner["name"]}')
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
                              if streak_bonus == 0:
                                add_points = -point_change + (win_streak * 2) + round(winner['points']*BonusRate)
                                userembed.add_field(name="",value=f"{winner['name']}님이 {win_streak}연속 적중을 이루어내며 {add_points}(연속적중 보너스 + {win_streak * 2})(베팅 보너스 + {round(winner['points']*BonusRate)} + {get_bet}) 점수를 획득하셨습니다! (베팅 포인트:{winner['points']})", inline=False)
                              else:
                                add_points = -point_change + (win_streak * 2) + round(winner['points']*BonusRate) + streak_bonus
                                userembed.add_field(name="",value=f"{winner['name']}님이 {win_streak}연속 적중을 이루어내며 {add_points}(연속적중 보너스 + {win_streak * 2})(베팅 보너스 + {round(winner['points']*BonusRate)} + {get_bet})(역배 보너스 + {streak_bonus}) 점수를 획득하셨습니다! (베팅 포인트:{winner['points']})", inline=False)
                            else:
                              if streak_bonus == 0:
                                add_points = -point_change + round(winner["points"]*BonusRate)
                                userembed.add_field(name="",value=f"{winner['name']}님이 {add_points}(베팅 보너스 + {round(winner['points']*BonusRate)} + {get_bet}) 점수를 획득하셨습니다! (베팅 포인트:{winner['points']})", inline=False)
                              else:
                                add_points = -point_change + round(winner["points"]*BonusRate) + streak_bonus
                                userembed.add_field(name="",value=f"{winner['name']}님이 {add_points}(베팅 보너스 + {round(winner['points']*BonusRate)} + {get_bet})(역배 보너스 + {streak_bonus}) 점수를 획득하셨습니다! (베팅 포인트:{winner['points']})", inline=False)

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
                            ref2 = db.reference(f'{PREDICT_SEASON}/예측포인트/{loser["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            prediction_all = originr["총 예측 횟수"]
                            prediction_wins = originr["적중 횟수"]
                            prediction_win_rate = originr["적중률"]
                            win_streak = originr["연승"]
                            lose_streak = originr["연패"]
                            bettingPoint = originr["베팅포인트"]


                            ref3 = db.reference(f'{PREDICT_SEASON}/예측포인트변동로그/{current_date}/{current_time}/{loser["name"]}')
                            ref3.update({"포인트" : point})
                            ref3.update({"총 예측 횟수": prediction_all})
                            ref3.update({"적중 횟수" : prediction_wins})
                            ref3.update({"적중률": f"{prediction_win_rate}"})
                            ref3.update({"연승": win_streak})
                            ref3.update({"연패": lose_streak})
                            ref3.update({"베팅포인트" : 0})

                            ref2 = db.reference(f'{PREDICT_SEASON}/예측포인트/{loser["name"]}')
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
                            ref2 = db.reference(f'{PREDICT_SEASON}/예측포인트/{perfect_winner["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            ref2.update({"포인트": point + perfect_point})
                            kdaembed.add_field(name="",value=f"{perfect_winner['name']}님이 KDA 퍼펙트 예측에 성공하여 {perfect_point}점을 획득하셨습니다!", inline=False)
                        for winner in winners:
                            ref2 = db.reference(f'{PREDICT_SEASON}/예측포인트/{winner["name"]}')
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
                            ref2 = db.reference(f'{PREDICT_SEASON}/예측포인트/{winner["name"]}')
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
                            ref2 = db.reference(f'{PREDICT_SEASON}/예측포인트/{winner["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            ref2.update({"포인트": point + 20})
                            kdaembed.add_field(name="",value=f"{winner['name']}님이 KDA 예측에 성공하여 20점을 획득하셨습니다!", inline=False)
                        for loser in losers:
                            kdaembed.add_field(name="",value=f"{loser['name']}님이 KDA 예측에 실패했습니다!", inline=False)
                    await channel.send(embed=kdaembed)

                    if jimo_kda == 999:
                        refperfect.update({'지모': 200})
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

                        if game_lose_streak >= 3:
                          streak_bonus = game_lose_streak * 3
                          streak_bonus_rate = round(game_lose_streak * 0.3,1)
                        else:
                          streak_bonus = 0
                          streak_bonus_rate = 0

                        if winnerNum == 0:
                            BonusRate = 0
                        else:
                            BonusRate = ((winnerNum+loserNum)/winnerNum)
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
                            userembed.add_field(name="",value=f"베팅 배율: {BonusRate}배!({winnerNum+loserNum}/{winnerNum} + 역배 배율 {streak_bonus_rate} + 0.1)", inline=False)

                        for winner in winners:
                            ref2 = db.reference(f'{PREDICT_SEASON}/예측포인트/{winner["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            prediction_all = originr["총 예측 횟수"]
                            prediction_wins = originr["적중 횟수"]
                            prediction_win_rate = originr["적중률"]
                            win_streak = originr["연승"]
                            lose_streak = originr["연패"]
                            bettingPoint = originr["베팅포인트"]

                            ref3 = db.reference(f'{PREDICT_SEASON}/예측포인트변동로그/{current_date}/{current_time}/{winner["name"]}')
                            ref3.update({"포인트" : point})
                            ref3.update({"총 예측 횟수": prediction_all})
                            ref3.update({"적중 횟수" : prediction_wins})
                            ref3.update({"적중률": f"{prediction_win_rate}"})
                            ref3.update({"연승": win_streak})
                            ref3.update({"연패": lose_streak})
                            ref3.update({"베팅포인트" : 0})


                            ref2 = db.reference(f'{PREDICT_SEASON}/예측포인트/{winner["name"]}')
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
                              if streak_bonus == 0:
                                add_points = point_change + (win_streak * 2) + round(winner['points']*BonusRate) + get_bet
                                userembed.add_field(name="",value=f"{winner['name']}님이 {win_streak}연속 적중을 이루어내며 {add_points}(연속적중 보너스 + {win_streak * 2})(베팅 보너스 + {round(winner['points']*BonusRate)} + {get_bet}) 점수를 획득하셨습니다! (베팅 포인트:{winner['points']})", inline=False)
                              else:
                                add_points = point_change + (win_streak * 2) + round(winner['points']*BonusRate) + streak_bonus + get_bet
                                userembed.add_field(name="",value=f"{winner['name']}님이 {win_streak}연속 적중을 이루어내며 {add_points}(연속적중 보너스 + {win_streak * 2})(베팅 보너스 + {round(winner['points']*BonusRate)} + {get_bet})(역배 보너스 + {streak_bonus}) 점수를 획득하셨습니다! (베팅 포인트:{winner['points']})", inline=False)
                            else:
                              if streak_bonus == 0:
                                add_points = point_change + round(winner["points"]*BonusRate) + get_bet
                                userembed.add_field(name="",value=f"{winner['name']}님이 {add_points}(베팅 보너스 + {round(winner['points']*BonusRate)} + {get_bet}) 점수를 획득하셨습니다! (베팅 포인트:{winner['points']})", inline=False)
                              else:
                                add_points = point_change + round(winner["points"]*BonusRate) + streak_bonus + get_bet
                                userembed.add_field(name="",value=f"{winner['name']}님이 {add_points}(베팅 보너스 + {round(winner['points']*BonusRate)} + {get_bet})(역배 보너스 + {streak_bonus}) 점수를 획득하셨습니다! (베팅 포인트:{winner['points']})", inline=False)

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
                            ref2 = db.reference(f'{PREDICT_SEASON}/예측포인트/{loser["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            prediction_all = originr["총 예측 횟수"]
                            prediction_wins = originr["적중 횟수"]
                            prediction_win_rate = originr["적중률"]
                            win_streak = originr["연승"]
                            lose_streak = originr["연패"]
                            bettingPoint = originr["베팅포인트"]

                            ref3 = db.reference(f'{PREDICT_SEASON}/예측포인트변동로그/{current_date}/{current_time}/{loser["name"]}')
                            ref3.update({"포인트" : point})
                            ref3.update({"총 예측 횟수": prediction_all})
                            ref3.update({"적중 횟수" : prediction_wins})
                            ref3.update({"적중률": f"{prediction_win_rate}"})
                            ref3.update({"연승": win_streak})
                            ref3.update({"연패": lose_streak})
                            ref3.update({"베팅포인트" : 0})

                            ref2 = db.reference(f'{PREDICT_SEASON}/예측포인트/{loser["name"]}')
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

                        if game_win_streak >= 3:
                          streak_bonus = game_win_streak * 3
                          streak_bonus_rate = round(game_win_streak * 0.3,1)
                        else:
                          streak_bonus = 0
                          streak_bonus_rate = 0

                        if winnerNum == 0:
                            BonusRate = 0
                        else:
                            BonusRate = ((winnerNum+loserNum)/winnerNum)
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
                            userembed.add_field(name="",value=f"베팅 배율: {BonusRate}배!({winnerNum+loserNum}/{winnerNum} + 역배 배율 {streak_bonus_rate} + 0.1)", inline=False)

                        for winner in winners:
                            ref2 = db.reference(f'{PREDICT_SEASON}/예측포인트/{winner["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            prediction_all = originr["총 예측 횟수"]
                            prediction_wins = originr["적중 횟수"]
                            prediction_win_rate = originr["적중률"]
                            win_streak = originr["연승"]
                            lose_streak = originr["연패"]
                            bettingPoint = originr["베팅포인트"]

                            ref3 = db.reference(f'{PREDICT_SEASON}/예측포인트변동로그/{current_date}/{current_time}/{winner["name"]}')
                            ref3.update({"포인트" : point})
                            ref3.update({"총 예측 횟수": prediction_all})
                            ref3.update({"적중 횟수" : prediction_wins})
                            ref3.update({"적중률": f"{prediction_win_rate}"})
                            ref3.update({"연승": win_streak})
                            ref3.update({"연패": lose_streak})
                            ref3.update({"베팅포인트" : 0})

                            ref2 = db.reference(f'{PREDICT_SEASON}/예측포인트/{winner["name"]}')
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
                              if streak_bonus == 0:
                                add_points = -point_change + (win_streak * 2) + round(winner['points']*BonusRate) + get_bet
                                userembed.add_field(name="",value=f"{winner['name']}님이 {win_streak}연속 적중을 이루어내며 {add_points}(연속적중 보너스 + {win_streak * 2})(베팅 보너스 + {round(winner['points']*BonusRate)} + {get_bet}) 점수를 획득하셨습니다! (베팅 포인트:{winner['points']})", inline=False)
                              else:
                                add_points = -point_change + (win_streak * 2) + round(winner['points']*BonusRate) + streak_bonus + get_bet
                                userembed.add_field(name="",value=f"{winner['name']}님이 {win_streak}연속 적중을 이루어내며 {add_points}(연속적중 보너스 + {win_streak * 2})(베팅 보너스 + {round(winner['points']*BonusRate)} + {get_bet})(역배 보너스 + {streak_bonus}) 점수를 획득하셨습니다! (베팅 포인트:{winner['points']})", inline=False)
                            else:
                              if streak_bonus == 0:
                                add_points = -point_change + round(winner["points"]*BonusRate) + get_bet
                                userembed.add_field(name="",value=f"{winner['name']}님이 {add_points}(베팅 보너스 + {round(winner['points']*BonusRate)}) 점수를 획득하셨습니다! (베팅 포인트:{winner['points']} + {get_bet})", inline=False)
                              else:
                                add_points = -point_change + round(winner["points"]*BonusRate) + streak_bonus + get_bet
                                userembed.add_field(name="",value=f"{winner['name']}님이 {add_points}(베팅 보너스 + {round(winner['points']*BonusRate)} + {get_bet})(역배 보너스 + {streak_bonus}) 점수를 획득하셨습니다! (베팅 포인트:{winner['points']})", inline=False)

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
                            ref2 = db.reference(f'{PREDICT_SEASON}/예측포인트/{loser["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            prediction_all = originr["총 예측 횟수"]
                            prediction_wins = originr["적중 횟수"]
                            prediction_win_rate = originr["적중률"]
                            win_streak = originr["연승"]
                            lose_streak = originr["연패"]
                            bettingPoint = originr["베팅포인트"]

                            ref3 = db.reference(f'{PREDICT_SEASON}/예측포인트변동로그/{current_date}/{current_time}/{loser["name"]}')
                            ref3.update({"포인트" : point})
                            ref3.update({"총 예측 횟수": prediction_all})
                            ref3.update({"적중 횟수" : prediction_wins})
                            ref3.update({"적중률": f"{prediction_win_rate}"})
                            ref3.update({"연승": win_streak})
                            ref3.update({"연패": lose_streak})
                            ref3.update({"베팅포인트" : 0})

                            ref2 = db.reference(f'{PREDICT_SEASON}/예측포인트/{loser["name"]}')
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
                            ref2 = db.reference(f'{PREDICT_SEASON}/예측포인트/{perfect_winner["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            ref2.update({"포인트": point + perfect_point})
                            kdaembed.add_field(name="",value=f"{perfect_winner['name']}님이 KDA 퍼펙트 예측에 성공하여 {perfect_point}점을 획득하셨습니다!", inline=False)
                        for winner in winners:
                            ref2 = db.reference(f'{PREDICT_SEASON}/예측포인트/{winner["name"]}')
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
                            ref2 = db.reference(f'{PREDICT_SEASON}/예측포인트/{winner["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            ref2.update({"포인트": point + 20})
                            kdaembed.add_field(name="",value=f"{winner['name']}님이 KDA 예측에 성공하여 20점을 획득하셨습니다!", inline=False)
                        for loser in losers:
                            kdaembed.add_field(name="",value=f"{loser['name']}님이 KDA 예측에 실패했습니다!", inline=False)
                    else: # KDA == 3
                        winners = p.kda_votes2['up'] + p.kda_votes2['down']
                        for winner in winners:
                            ref2 = db.reference(f'{PREDICT_SEASON}/예측포인트/{winner["name"]}')
                            originr = ref2.get()
                            point = originr["포인트"]
                            ref2.update({"포인트": point + 20})
                            kdaembed.add_field(name="",value=f"{winner['name']}님이 KDA 예측에 성공하여 20점을 획득하셨습니다!", inline=False)
                    await channel.send(embed=kdaembed)

                    if melon_kda == 999:
                        refperfect.update({'Melon': 200})
                    else:
                        refperfect.update({'Melon': perfect_point + 5})

                    p.kda_votes2['up'].clear()
                    p.kda_votes2['down'].clear()
                    p.kda_votes2['perfect'].clear()

                    p.melon_event.set() # check_game_status2의 대기상태를 해제

        await asyncio.sleep(20)  # 20초마다 반복

async def check_game_status(): #지모의 솔로랭크가 진행중인지 20초마다 확인
    await bot.wait_until_ready()
    channel = bot.get_channel(int(CHANNEL_ID))
    notice_channel = bot.get_channel(int(NOTICE_CHANNEL_ID))

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
                        refp = db.reference(f'{PREDICT_SEASON}/예측포인트/{nickname.name}')

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

                        refp = db.reference(f'{PREDICT_SEASON}/예측포인트/{nickname.name}')

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

                    if game_win_streak >= 3:
                      streak_bonus = game_win_streak * 3
                      p.current_message_jimo = await channel.send("\n지모의 솔로랭크 게임이 감지되었습니다!\n"
                                    "승부예측을 해보세요!\n"
                                    f"{game_win_streak}연승으로 패배에 +{streak_bonus}점!\n",
                                    view = view, embed = p.prediction_embed)
                    elif game_lose_streak >= 3:
                      streak_bonus = game_lose_streak * 3
                      p.current_message_jimo = await channel.send("\n지모의 솔로랭크 게임이 감지되었습니다!\n"
                                    "승부예측을 해보세요!\n"
                                    f"{game_lose_streak}연패로 승리에 +{streak_bonus}점!\n",
                                    view = view, embed = p.prediction_embed)
                    else:
                      streak_bonus = 0
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
                        refp = db.reference(f'{PREDICT_SEASON}/예측포인트/{nickname.name}')

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
                        refp = db.reference(f'{PREDICT_SEASON}/예측포인트/{nickname.name}')

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

                    if game_win_streak >= 3:
                      streak_bonus = game_win_streak * 3
                      p.current_message_melon = await channel.send("\nMelon의 솔로랭크 게임이 감지되었습니다!\n"
                                    "승부예측을 해보세요!\n"
                                    f"{game_win_streak}연승으로 패배에 +{streak_bonus}점!\n",
                                    view = view, embed = p.prediction2_embed)
                    elif game_lose_streak >= 3:
                      streak_bonus = game_lose_streak * 3
                      p.current_message_melon = await channel.send("\nMelon의 솔로랭크 게임이 감지되었습니다!\n"
                                    "승부예측을 해보세요!\n"
                                    f"{game_lose_streak}연패로 승리에 +{streak_bonus}점!\n",
                                    view = view, embed = p.prediction2_embed)
                    else:
                      streak_bonus = 0
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

async def check_jimo_remake_status(): # 지모의 다시하기 여부를 확인!
    channel = bot.get_channel(int(CHANNEL_ID))
    last_game_state = False
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
                                ref = db.reference(f'{PREDICT_SEASON}/예측포인트/{winner["name"]}')
                                originr = ref.get()
                                bettingPoint = originr["베팅포인트"]
                                bettingPoint -= winner['points'] # 베팅 포인트 돌려줌
                                ref.update({"베팅포인트" : bettingPoint})
                            for loser in losers:
                                ref = db.reference(f'{PREDICT_SEASON}/예측포인트/{loser["name"]}')
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
                                ref = db.reference(f'{PREDICT_SEASON}/예측포인트/{winner["name"]}')
                                originr = ref.get()
                                bettingPoint = originr["베팅포인트"]
                                bettingPoint -= winner['points'] # 베팅 포인트 돌려줌
                                ref.update({"베팅포인트" : bettingPoint})
                            for loser in losers:
                                ref = db.reference(f'{PREDICT_SEASON}/예측포인트/{loser["name"]}')
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

        bot.loop.create_task(check_jimo_points())
        bot.loop.create_task(check_melon_points())
        bot.loop.create_task(check_game_status())
        bot.loop.create_task(check_game_status2())
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