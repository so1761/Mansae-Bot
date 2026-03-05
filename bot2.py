import aiohttp
import asyncio
import discord
import firebase_admin
import random
import prediction_vote as p
import os
import json
from collections import defaultdict
from firebase_admin import credentials
from firebase_admin import db
from discord import Intents
from discord.ext import commands
from discord import Game
from discord import Status
from discord import Object
from datetime import datetime,timedelta, timezone
from dotenv import load_dotenv

TARGET_TEXT_CHANNEL_ID = 1289184218135396483
WARNING_CHANNEL_ID = 1314643507490590731
GUILD_ID = 298064707460268032
CHANNEL_ID = '938728993329397781'
NOTICE_CHANNEL_ID = '1232585451911643187'
TOKEN = None
API_KEY = None

REGISTERED_USERS = ['지모','Melon','그럭저럭', '이미름', '박퇴경']

PUUID = {}

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

MEMBER_MAP = {
    "지모" : 270093275673657355,
    "Melon" : 266140074310107136,
    "그럭저럭" : 512990115782590464,
    "이미름" : 298064278328705026,
    "박퇴경" : 298068763335589899
}

class NotFoundError(Exception):
    pass

CHAMPION_ID_NAME_MAP = {}

async def get_latest_ddragon_version():
    url = 'https://ddragon.leagueoflegends.com/api/versions.json'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                versions = await response.json()
                return versions[0]  # 가장 최신 버전
            else:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] 버전 정보 불러오기 실패: {response.status}")
                return None

# 챔피언 데이터 다운로드 함수 (캐시 추가)
async def fetch_champion_data(force_download=False):
    global CHAMPION_ID_NAME_MAP

    cache_path = "champion_cache.json"
    if not force_download and os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            CHAMPION_ID_NAME_MAP = json.load(f)
        return CHAMPION_ID_NAME_MAP

    # 최신 버전 가져오기
    version = await get_latest_ddragon_version()
    if not version:
        return {}

    # 챔피언 데이터 가져오기
    url = f'https://ddragon.leagueoflegends.com/cdn/{version}/data/ko_KR/champion.json'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                data_by_id = {}
                for champ in data["data"].values():
                    champ_id = int(champ["key"])  # 문자열을 정수로
                    champ_name = champ["name"]
                    data_by_id[champ_id] = champ_name
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] {len(data_by_id)}개의 챔피언을 불러왔습니다. (버전: {version})")

                # 로컬 캐시 저장
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(data_by_id, f, ensure_ascii=False, indent=2)

                CHAMPION_ID_NAME_MAP = data_by_id
                return data_by_id
            else:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] 챔피언 데이터 불러오기 실패: {response.status}")
                return {}

# 패치 버전 주기적으로 확인하여 최신 버전이 바뀌면 데이터 갱신
async def fetch_patch_version():

    version = await get_latest_ddragon_version()

    curseasonref = db.reference("전적분석/현재시즌")
    current_season = curseasonref.get()

    season_name = "시즌" + version.split(".")[0]

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [LOG] 현재 시즌 : {season_name}")

    if current_season != season_name:
        curseasonref = db.reference("전적분석")
        curseasonref.update({'현재시즌' : season_name})
    # 최신 버전 가져오기
    await asyncio.sleep(3600)
    
async def fetch_rune_id_to_key_map(force_download=False):
    cache_path = "rune_id_to_key_cache.json"
    if not force_download and os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            rune_id_to_key = json.load(f)
        return rune_id_to_key

    # 최신 버전 가져오기
    version = await get_latest_ddragon_version()
    if not version:
        return {}

    # 룬 데이터 가져오기
    url = f'https://ddragon.leagueoflegends.com/cdn/{version}/data/ko_KR/runesReforged.json'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()

                rune_id_to_key = {
                    str(rune["id"]): rune["key"]
                    for tree in data
                    for rune in tree["slots"][0]["runes"]
                }       

                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] {len(rune_id_to_key)}개의 룬을 불러왔습니다. (버전: {version})")

                # 로컬 캐시 저장
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(rune_id_to_key, f, ensure_ascii=False, indent=2)

                return rune_id_to_key
            else:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] 룬 데이터 불러오기 실패: {response.status}")
                return {}

async def fetch_spell_id_to_key_map(force_download=False):
    cache_path = "spell_id_to_key_cache.json"
    if not force_download and os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            spell_id_to_key = json.load(f)
        return spell_id_to_key

    # 최신 버전 가져오기
    version = await get_latest_ddragon_version()
    if not version:
        return {}

    # 스펠 데이터 가져오기
    url = f'https://ddragon.leagueoflegends.com/cdn/{version}/data/ko_KR/summoner.json'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()

                spell_id_to_key = {
                    str(value["key"]): key  # 예: "11": "SummonerSmite"
                    for key, value in data["data"].items()
                }

                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INFO] {len(spell_id_to_key)}개의 스펠을 불러왔습니다. (버전: {version})")

                # 로컬 캐시 저장
                with open(cache_path, "w", encoding="utf-8") as f:
                    json.dump(spell_id_to_key, f, ensure_ascii=False, indent=2)

                return spell_id_to_key
            else:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] 스펠 데이터 불러오기 실패: {response.status}")
                return {}

async def fake_get_current_game_info(puuid):
    import json
    with open("mock_active_game.json", "r", encoding="utf-8") as f:
        return json.load(f)
    
async def get_current_game_info(puuid):
    url = f'https://kr.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}'
    headers = {'X-Riot-Token': API_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            elif response.status == 404:
                return None  # 게임 안 하는 중
            else:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_current_game_info에서 오류 발생: {response.status}")
                return None

async def get_team_champion_embed(username, puuid, get_info_func=get_current_game_info):
    data = await get_info_func(puuid)
    if not data:
        return None

    participants = data.get("participants", [])
    if not participants:
        return None

    team1 = []
    team2 = []

    SPELL_EMOJI_MAP = {
        "SummonerSmite": "<:smite:1369988249417678948>",
        "SummonerFlash": "<:flash:1369988373631991858>",
        "SummonerTeleport": "<:teleport:1369988420276977675>",
        "SummonerHeal": "<:heal:1369988449460944896>",
        "SummonerDot": "<:ignite:1369988477915107378>",
        "SummonerBarrier": "<:barrier:1369988312076390471>",
        "SummonerExhaust": "<:exhaust:1369988518692261888>",
        "SummonerHaste": "<:ghost:1369988552200552528>",
        "SummonerBoost": "<:cleanse:1369988596362379274>"
    }

    RUNE_EMOJI_MAP = {
        "Electrocute": "<:Electrocute:1476931788973670603>",
        "DarkHarvest": "<:DarkHarvest:1476931900755935253>",
        "HailOfBlades": "<:HailOfBlades:1476931917080428585>",
        "GlacialAugment": "<:GlacialAugment:1476931912537866374>",
        "UnsealedSpellbook": "<:UnsealedSpellbook:1476931925498400819>",
        "FirstStrike": "<:FirstStrike:1476931909388079274>",
        "FleetFootwork": "<:FleetFootwork:1476931910897893526>",
        "Conqueror": "<:Conqueror:1476931898533216377>",
        "LethalTempo": "<:LethalTempo:1476931919047299196>",
        "PressTheAttack": "<:PressTheAttack:1476931921606082600>",
        "SummonAery": "<:SummonAery:1476931923459837972>",
        "PhaseRush": "<:PhaseRush:1476931920372699239>",
        "ArcaneComet": "<:ArcaneComet:1476931896624550000>",
        "GraspOfTheUndying": "<:GraspOfTheUndying:1476931913787637762>",
        "Guardian": "<:Guardian:1476931915415027784>",
        "Aftershock": "<:Aftershock:1476931927541026957>"
    }

    CHAMPION_ID_NAME_MAP = await fetch_champion_data(force_download = False)
    SPELL_ID_TO_KEY = await fetch_spell_id_to_key_map()
    RUNE_ID_TO_KEY = await fetch_rune_id_to_key_map()

    for p in participants:
        champ_id = p.get("championId")
        champ_name = CHAMPION_ID_NAME_MAP.get(str(champ_id), f"챔피언ID:{champ_id}")
        summoner_name = p.get("riotId", "Unknown")
        
        spell1_id = str(p.get("spell1Id"))
        spell2_id = str(p.get("spell2Id"))

        spell1_key = SPELL_ID_TO_KEY.get(spell1_id, "")  # 예: 'SummonerSmite'
        spell2_key = SPELL_ID_TO_KEY.get(spell2_id, "")

        spell1_emoji = SPELL_EMOJI_MAP.get(spell1_key, "❓")
        spell2_emoji = SPELL_EMOJI_MAP.get(spell2_key, "❓")

        perks = p.get("perks", {})
        perk_ids = perks.get("perkIds", [])
        rune_id = str(perk_ids[0]) if perk_ids else None

        rune_key = RUNE_ID_TO_KEY.get(rune_id, "")

        rune_emoji = RUNE_EMOJI_MAP.get(rune_key, "❓")
        entry = f"{rune_emoji}{spell1_emoji}{spell2_emoji} **{champ_name}** - {summoner_name}"

        if p.get("teamId") == 100:
            team1.append(entry)
        elif p.get("teamId") == 200:
            team2.append(entry)

    embed = discord.Embed(
        title=f"🔍 {username} 인게임 정보",
        description=f"{username}의 실시간 챔피언 정보입니다.",
        color=discord.Color.green(),
        timestamp = datetime.now(timezone.utc)
    )
    embed.add_field(name="🔵 블루팀", value="\n".join(team1), inline=False)
    embed.add_field(name="🔴 레드팀", value="\n".join(team2), inline=False)

    return embed

async def fake_nowgame(puuid):
    print("🧪 fake_nowgame 호출됨!")
    return True, "솔로랭크"

async def nowgame(puuid, retries=5, delay=5):
    url = f'https://kr.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}'
    headers = {'X-Riot-Token': API_KEY}

    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        game_id = data.get("gameId")
                        game_mode = data.get("gameMode")
                        game_type = data.get("gameType")
                        queue_id = data.get("gameQueueConfigId")

                        if game_mode == "CLASSIC" and game_type == "MATCHED":
                            if queue_id == 420:
                                return True, "솔로랭크", game_id
                            elif queue_id == 440:
                                return True, "자유랭크", game_id
                        
                        return False, None, game_id  # 랭크 게임이 아닐 경우

                    elif response.status == 404:
                        return False, None, None  # 현재 게임이 없으면 재시도할 필요 없음

                    elif response.status in [500, 502, 503, 504, 524]:  # 524 추가
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARNING] nowgame에서 {response.status} 오류 발생, 재시도 중 {attempt + 1}/{retries}...")

                    else:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] nowgame에서 {response.status} 오류 발생")
                        return False, None, None  # 다른 오류는 재시도하지 않음

        except aiohttp.ClientConnectorError as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] nowgame에서 연결 오류 발생: {e}, 재시도 중 {attempt + 1}/{retries}...")
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] nowgame에서 예기치 않은 오류 발생: {e}")
            return False, None, None

        await asyncio.sleep(delay)  # 재시도 간격 증가

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] nowgame에서 모든 재시도 실패")
    return False, None, None

async def get_summoner_puuid(riot_id, tagline):
    url = f'https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{riot_id}/{tagline}'
    headers = {'X-Riot-Token': API_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data['puuid']
            else:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_puuid에서 {response.status} 오류 발생")
                return None

async def get_summoner_ranks(puuid, type="솔로랭크", retries=5, delay=5):
    url = f'https://kr.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}'
    headers = {'X-Riot-Token': API_KEY}

    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        if type == "솔로랭크":
                            filtered_data = [entry for entry in data if entry.get("queueType") == "RANKED_SOLO_5x5"]
                        elif type == "자유랭크":
                            filtered_data = [entry for entry in data if entry.get("queueType") == "RANKED_FLEX_SR"]
                        return filtered_data[0] if filtered_data else []

                    elif response.status == 404:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_ranks에서 404 오류 발생")
                        return None  # 소환사 정보가 없으면 재시도할 필요 없음

                    elif response.status in [500, 502, 503, 504, 524]:  
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARNING] get_summoner_ranks에서 {response.status} 오류 발생, 재시도 중 {attempt + 1}/{retries}...")  
                    else:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_ranks에서 {response.status} 오류 발생")
                        return None  # 다른 오류는 재시도 없이 종료

        except aiohttp.ClientConnectorError as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_ranks에서 연결 오류 발생: {e}, 재시도 중 {attempt + 1}/{retries}...")
        except aiohttp.ClientOSError as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_ranks에서 클라이언트 오류 발생 (서버 연결 해제): {e}, 재시도 중 {attempt + 1}/{retries}...")
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_ranks에서 예기치 않은 오류 발생: {e}, 재시도 중 {attempt + 1}/{retries}...")

        await asyncio.sleep(delay)  # 재시도 간격

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_ranks 모든 재시도 실패")
    return None

async def get_summoner_recentmatch_id(puuid, retries=5, delay=5):
    url = f'https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=1'
    headers = {'X-Riot-Token': API_KEY}

    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data[0] if data else None

                    elif response.status == 404:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_recentmatch_id에서 404 오류 발생: PUUID {puuid}에 대한 매치가 없습니다.")
                        return None  # PUUID가 잘못된 경우는 재시도할 필요 없음

                    elif response.status in [500, 502, 503, 504, 524]:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARNING] get_summoner_recentmatch_id에서 {response.status} 오류 발생, 재시도 중 {attempt + 1}/{retries}...")
                    else:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_recentmatch_id에서 {response.status} 오류 발생")
                        return None

        except aiohttp.ClientConnectorError as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_recentmatch_id에서 연결 오류 발생: {e}, 재시도 중 {attempt + 1}/{retries}...")
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_recentmatch_id에서 예기치 않은 오류 발생: {e}, 재시도 중 {attempt + 1}/{retries}...")
            return None

        await asyncio.sleep(delay)  # 재시도 간격

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_recentmatch_id 모든 재시도 실패")
    return None

async def get_summoner_matchinfo(matchid, retries=5, delay=5):
    url = f'https://asia.api.riotgames.com/lol/match/v5/matches/{matchid}'
    headers = {'X-Riot-Token': API_KEY}

    for attempt in range(retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()

                    elif response.status == 404:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_matchinfo에서 404 오류 발생: 매치 ID {matchid}를 찾을 수 없습니다.")
                        return None  # 매치 ID가 잘못된 경우는 재시도할 필요 없음

                    elif response.status == 400:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_matchinfo에서 400 오류 발생: 잘못된 매치 ID {matchid}.")
                        return None  # 잘못된 요청이라면 재시도할 필요 없음

                    elif response.status in [500, 502, 503, 504, 524]:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [WARNING] get_summoner_matchinfo에서 {response.status} 오류 발생, 재시도 중 {attempt + 1}/{retries}...")
                    else:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_matchinfo에서 {response.status} 오류 발생")
                        return None

        except aiohttp.ClientConnectorError as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_matchinfo에서 연결 오류 발생: {e}, 재시도 중 {attempt + 1}/{retries}...")
        except Exception as e:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_matchinfo에서 예기치 않은 오류 발생: {e}, 재시도 중 {attempt + 1}/{retries}...")
            return None

        await asyncio.sleep(delay)  # 재시도 간격

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] get_summoner_matchinfo 모든 재시도 실패")
    return None

async def refresh_prediction(name, prediction_votes):
    """
    주어진 소환사의 예측 현황을 업데이트합니다.
    Args:
        name: 소환사 이름
        prediction_votes: 예측 투표 데이터 (승리 예측과 패배 예측을 포함하는 딕셔너리)
    Returns:
        None
    """
    embed = discord.Embed(title=f"{name} 예측 현황", color=0x000000) # Black
   
    win_predictions = "\n".join(f"{user['name'].display_name}" for user in prediction_votes["win"]) or "없음"
    lose_predictions = "\n".join(f"{user['name'].display_name}" for user in prediction_votes["lose"]) or "없음"
    
    embed.add_field(name="승리 예측", value=win_predictions, inline=True)
    embed.add_field(name="패배 예측", value=lose_predictions, inline=True)
        
    await p.current_messages[name].edit(embed=embed)

async def refresh_kda_prediction(name, kda_votes):
    """
    주어진 소환사의 KDA 예측 현황을 업데이트합니다.
    Args:
        name: 소환사 이름
        kda_votes: KDA 예측 투표 데이터 (KDA 3 이상, KDA 3 이하, 퍼펙트를 포함하는 딕셔너리)
    Returns:
        None
    """
    embed = discord.Embed(title=f"{name} KDA 예측 현황", color=0x000000) # Black

    up_predictions = "\n".join(f"{user['name'].display_name}" for user in kda_votes["up"]) or "없음"
    down_predictions = "\n".join(f"{user['name'].display_name}" for user in kda_votes["down"]) or "없음"
    perfect_predictions = "\n".join(f"{user['name'].display_name}" for user in kda_votes["perfect"]) or "없음"

    embed.add_field(name="KDA 3 이상", value=up_predictions, inline=False)
    embed.add_field(name="KDA 3 이하", value=down_predictions, inline=False)
    embed.add_field(name="퍼펙트", value=perfect_predictions, inline=False)
    
    await p.current_messages_kda[name].edit(embed=embed)

def tier_to_number(tier, rank, lp): # 티어를 레이팅 숫자로 변환
    """
    주어진 소환사의 티어를 숫자로 변환합니다.
    Args:
        tier: 소환사 티어
        rank: 소환사 랭크
        lp: 소환사 LP
    Returns:
        소환사의 티어를 숫자로 변환한 값 (예: Iron IV 0LP -> 0,  EMERALD II 69LP -> 2669)
    """
    tier_num = TIER_RANK_MAP.get(tier)
    rank_num = RANK_MAP.get(rank)
    if tier_num is None or rank_num is None:
        return None
    return tier_num * 400 + rank_num * 100 + lp

def get_lp_and_tier_difference(previous_rank, current_rank,rank_type,name): # 이전 랭크와 현재 랭크를 받아 차이를 계산하여 메세지 반환(승급/강등)

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
                        return f"@here\n{name}(이)가 {current_rank['tier']}(으)로 승급하였습니다!:partying_face:"
                    elif current_tier_num < prev_tier_num:
                        return f"{name}(이)가 {current_rank['tier']}(으)로 강등되었습니다."
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

def save_lp_difference_to_file(lp_difference,current_rank,rank_type,name): # 사용자의 점수 변화량과 날짜를 파이어베이스에 저장
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
    bonus = 3 * streak
    return bonus

opened_games = set()
active_games = defaultdict(list)
tracked_users = set()
monitored_games = set()
async def monitor_games():
    """
    게임 모니터링: REGISTERED_USERS들이 게임을 시작했는지 주기적으로 확인하여 예측 오픈
    """
    await bot.wait_until_ready()
    while not bot.is_closed():
        # 전체 플레이어를 한번에 검사
        for username in REGISTERED_USERS:
            
            if username in tracked_users:
                continue  # 이미 추적 중인 플레이어는 건너뜀
            puuid = PUUID[username]

            ingame, mode, game_id = await nowgame(puuid)

            if ingame:
                tracked_users.add(username)  # 추적 중인 플레이어로 추가
                active_games[game_id].append((username, mode))
                print(f"[LOG] [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {username}이(가) 게임 중입니다! (게임 ID: {game_id}, 모드: {mode})")  

        #print(f"active_games: {dict(active_games)}")
        # 게임 id 단위로 처리
        for game_id, players in active_games.items():
            
            if game_id in opened_games: # 이미 예측이 열린 게임이라면
                continue

            # 같은 게임 id를 가진 플레이어들 중에서 랜덤으로 한 명을 선택하여 예측 오픈
            selected_user, mode = random.choice(players)

            # 진행중인 게임 목록에 게임 id 추가
            opened_games.add(game_id)

            # 예측 오픈
            bot.loop.create_task(
                open_prediction(
                    name=selected_user,
                    mode=mode,
                    game_id=game_id
                )
            )

        await asyncio.sleep(20)

# 플레이어 별 게임 종료 모니터링 (동시 처리)
async def monitor_single_player_ending(name, game_id, current_game_type, channel, notice_channel):
    puuid = PUUID[name]
    
    # 마지막으로 확인한 랭크 정보 가져오기
    try:
        last_rank = await get_summoner_ranks(puuid, current_game_type) 
    except NotFoundError:
        last_rank = None

    recent_match_id = None
    while not bot.is_closed():
        # 게임 종료 체크
        ingame, _, _ = await nowgame(puuid)
        if not ingame: # 게임 종료 의심 상태
            await asyncio.sleep(30) # 30초 후 재확인
            recent_match_id = await get_summoner_recentmatch_id(puuid)
            if recent_match_id.split("_")[1] == str(game_id): # 최근 매치가 해당 게임과 동일하다면 게임이 종료된 것으로 간주
                break
        await asyncio.sleep(20)  # API 호출 간 20초 대기
    
    if recent_match_id is None:
        return

    # 다시하기 여부 확인
    match_info = await get_summoner_matchinfo(recent_match_id)
    participant_id = get_participant_id(match_info, puuid)

    if match_info['info']['participants'][participant_id]['gameEndedInEarlySurrender']:
        userembed = discord.Embed(title=f"{name}의 게임 종료!", color=discord.Color.light_gray())
        userembed.add_field(name=f"{name}의 랭크게임이 종료되었습니다!", value="결과 : 다시하기!")
        await channel.send(embed=userembed)

        if name in p.votes:
            votes = p.votes[name]
            votes['prediction']['win'].clear()
            votes['prediction']['lose'].clear()
            votes['kda']['up'].clear()
            votes['kda']['down'].clear()
            votes['kda']['perfect'].clear()         
        
            p.events[name].set()
        return

    try:
        current_rank = await get_summoner_ranks(puuid, current_game_type)
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] monitor_single_player_ending에서 예기치 않은 오류 발생: {e}")
        current_rank= None

    if not current_rank:
        current_total_match = 0
    else:
        current_win = current_rank['wins']
        current_loss = current_rank['losses']
        current_total_match = current_win + current_loss

        if last_rank:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [LOG] {name}의 {current_total_match}번째 {current_game_type} 게임 완료")
            string = get_lp_and_tier_difference(last_rank, current_rank, current_game_type, name)
            await notice_channel.send(f"\n{name}의 {current_game_type} 점수 변동이 감지되었습니다!\n{string}")
            await channel.send(f"\n{name}의 {current_game_type} 점수 변동이 감지되었습니다!\n{string}")

    active_games.pop(game_id) # 게임 종료된 게임 id는 active_games에서 제거
    tracked_users.discard(name) # 게임 종료된 플레이어는 추적 대상에서 제거
    await predict_results(name,current_game_type) # 예측 결과 처리

# 게임 종료 모니터링: 게임이 종료되었는지 주기적으로 확인하여 점수 변동 감지 및 예측 결과 처리 (동시에 모든 플레이어 모니터링)
async def monitor_endings():
    await bot.wait_until_ready()
    channel = bot.get_channel(int(CHANNEL_ID)) # 일반 채널
    notice_channel = bot.get_channel(int(NOTICE_CHANNEL_ID)) # 공지 채널
    
    # 게임 진행중인 플레이어들에 대해서 게임 종료 여부 동시에 확인
    while not bot.is_closed():
        for game_id, players in active_games.items():

            if game_id in monitored_games:
                continue

            monitored_games.add(game_id)

            for name, current_game_type in players:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [LOG] {name}의 게임 종료를 모니터링 중입니다. (게임 ID: {game_id}, 모드: {current_game_type})")
                asyncio.create_task(monitor_single_player_ending(name, game_id, current_game_type, channel, notice_channel))
        
        await asyncio.sleep(10)
# 예측 결과 처리
async def predict_results(name, current_game_type):
    # 예측 결과 처리
    onoffref = db.reference("승부예측/투표온오프") # 투표가 off 되어있을 경우 결과 출력 X
    onoffbool = onoffref.get()

    if name not in p.votes:
        prediction_opened = False
    else:
        prediction_opened = True
        

    if not onoffbool or not prediction_opened: # 투표가 off 되어있거나 예측이 열리지 않았을 경우 결과 출력 X
        
        curseasonref = db.reference("전적분석/현재시즌")
        current_season = curseasonref.get()

        ref = db.reference(f'전적분석/{current_season}/점수변동/{name}/{current_game_type}')
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
            userembed = discord.Embed(title=f"{name}의 게임 종료!", color=discord.Color.blue())
        else:
            userembed = discord.Embed(title=f"{name}의 게임 종료!", color=discord.Color.red())
        

        userembed.add_field(name=f"{name}의 {current_game_type} 게임이 종료되었습니다!", value=f"결과 : **{'승리!' if result else '패배..'}**\n점수변동: {point_change}")
        await calculate_points(name, result, userembed) # 예측 포인트 정산

# 예측 포인트 정산
async def calculate_points(name, result, userembed):
    channel = bot.get_channel(int(CHANNEL_ID)) # 일반 채널
    puuid = PUUID[name]
    event = p.events[name]
    prediction_votes = p.votes[name]["prediction"]
    kda_votes = p.votes[name]["kda"]
    
    winners = prediction_votes['win'] if result else prediction_votes['lose']
    losers = prediction_votes['lose'] if result else prediction_votes['win']

    cur_predict_seasonref = db.reference("승부예측/현재예측시즌") # 현재 진행중인 예측 시즌을 가져옴
    current_predict_season = cur_predict_seasonref.get()

    for winner in winners:
        point_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner['name'].name}")
        predict_data = point_ref.get()

        if predict_data is None:
            predict_data = {}
        
        point = predict_data.get("포인트",0)

        prediction_value = "승리" if result else "패배"
        prediction_opposite_value = "패배" if result else "승리"
        # 예측 내역 업데이트
        point_ref.update({
            "포인트": point,
            "총 예측 횟수": predict_data.get("총 예측 횟수",0) + 1,
            "적중 횟수": predict_data.get("적중 횟수",0) + 1,
            "적중률": f"{round((((predict_data.get('적중 횟수',0) + 1) * 100) / (predict_data.get('총 예측 횟수',0) + 1)), 2)}%",
            "연승": predict_data.get("연승",0) + 1,
            "연패": 0,
        
            # 추가 데이터
            f"{name}적중": predict_data.get(f"{name}적중", 0) + 1,
            f"{name}{prediction_value}예측": predict_data.get(f"{name}{prediction_value}예측", 0) + 1,
            f"{prediction_value}예측연속": predict_data.get(f"{prediction_value}예측연속", 0) + 1,
            f"{prediction_opposite_value}예측연속": 0
        })

        win_streak = predict_data.get('연승', 0) + 1
        streak_bonus = calculate_bonus(win_streak)
        streak_text = f"{win_streak}연속 적중으로 " if win_streak > 1 else ""
        streak_bonus_text = f"(+{streak_bonus})" if win_streak > 1 else ""
        
        add_points = 20 + streak_bonus if win_streak > 1 else 20
        userembed.add_field(name="", value=f"**{winner['name'].display_name}**님이 {streak_text}**{add_points}**{streak_bonus_text}점을 획득하셨습니다!", inline=False)

        point_ref.update({"포인트": point + add_points})
    for loser in losers:
        point_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{loser['name'].name}")
        predict_data = point_ref.get()

        if predict_data is None:
            predict_data = {}

        point = predict_data.get("포인트",0)
        
        prediction_value = "패배" if result else "승리"
        prediction_opposite_value = "승리" if result else "패배"
        # 예측 내역 업데이트
        point_ref.update({
            "포인트": point,
            "총 예측 횟수": predict_data.get("총 예측 횟수",0) + 1,
            "적중 횟수": predict_data.get("적중 횟수",0),
            "적중률": f"{round((((predict_data.get('적중 횟수',0)) * 100) / (predict_data.get('총 예측 횟수',0) + 1)), 2)}%",
            "연승": 0,
            "연패": predict_data.get("연패",0) + 1,

            # 추가 데이터
            f"{name}{prediction_value}예측": predict_data.get(f"{name}{prediction_value}예측", 0) + 1,
            f"{prediction_value}예측연속": predict_data.get(f"{prediction_value}예측연속", 0) + 1,
            f"{prediction_opposite_value}예측연속": 0
        })

    await channel.send(embed=userembed)

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
            
            if kda > 3:
                perfect_winners = kda_votes['perfect'] if kda == 999 else []
                winners = kda_votes['up']
                losers = kda_votes['down'] + (kda_votes['perfect'] if kda != 999 else [])
                for perfect_winner in perfect_winners:
                    point_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{perfect_winner['name'].name}")
                    predict_data = point_ref.get()

                    if predict_data is None:
                        predict_data = {}

                    point_ref.update({"포인트": predict_data["포인트"] + 100})
                    kdaembed.add_field(name="", value=f"{perfect_winner['name'].display_name}님이 KDA 퍼펙트 예측에 성공하여 100점을 획득하셨습니다!", inline=False)

                for winner in winners:
                    point_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner['name'].name}")
                    predict_data = point_ref.get()

                    if predict_data is None:
                        predict_data = {}

                    point_ref.update({"포인트": predict_data["포인트"] + 20})
                    kdaembed.add_field(name="", value=f"{winner['name'].display_name}님이 KDA 예측에 성공하여 20점을 획득하셨습니다!", inline=False)
            elif kda == 3:
                winners = kda_votes['up'] + kda_votes['down']
                losers = kda_votes['perfect']

                for winner in winners:
                    point_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner['name'].name}")
                    predict_data = point_ref.get()

                    if predict_data is None:
                        predict_data = {}

                    kdaembed.add_field(name="", value=f"{winner['name'].display_name}님이 KDA 예측에 성공하여 20점을 획득하셨습니다!", inline=False)
            else:
                winners = kda_votes['down']
                losers = kda_votes['up'] + kda_votes['perfect']
                for winner in winners:
                    point_ref = db.reference(f"승부예측/예측시즌/{current_predict_season}/예측포인트/{winner['name'].name}")
                    predict_data = point_ref.get()

                    if predict_data is None:
                        predict_data = {}

                    kdaembed.add_field(name="", value=f"{winner['name'].display_name}님이 KDA 예측에 성공하여 20점을 획득하셨습니다!", inline=False)

            await channel.send(embed=kdaembed)

            kda_votes['up'].clear()
            kda_votes['down'].clear()
            kda_votes['perfect'].clear()
            prediction_votes['win'].clear()
            prediction_votes['lose'].clear()

            event.set()       

# 예측 오픈 함수: 게임이 감지되면 해당 게임에 대한 예측을 오픈하는 함수
async def open_prediction(name, mode, game_id):
    await bot.wait_until_ready()
    channel = bot.get_channel(int(CHANNEL_ID))
    notice_channel = bot.get_channel(int(NOTICE_CHANNEL_ID))

    cur_predict_seasonref = db.reference("승부예측/현재예측시즌")
    current_predict_season = cur_predict_seasonref.get()

    puuid = PUUID[name]

    p.votes[name] = {
        "prediction": {
            "win": [],
            "lose": []
        },
        "kda": {
            "up": [],
            "down": [],
            "perfect": []
        }
    }

    votes = p.votes[name]

    p.events[name] = asyncio.Event()
    event = p.events[name]

    p.winbuttons[name] = discord.ui.Button(style=discord.ButtonStyle.success,label="승리")
    winbutton = p.winbuttons[name]

    p.current_match_id_flex[name] = ""
    p.current_match_id_solo[name] = ""
    
    onoffref = db.reference("승부예측/투표온오프")
    onoffbool = onoffref.get()

    # 이전 게임의 match_id를 저장
    if mode == "솔로랭크":
        p.current_match_id_solo[name] = await get_summoner_recentmatch_id(puuid)
    else:
        p.current_match_id_flex[name] = await get_summoner_recentmatch_id(puuid)
    p.current_predict_season[name] = current_predict_season

    winbutton.disabled = onoffbool
    losebutton = discord.ui.Button(style=discord.ButtonStyle.danger,label="패배",disabled=onoffbool)

    
    prediction_view = discord.ui.View()
    prediction_view.add_item(winbutton)
    prediction_view.add_item(losebutton)

    upbutton = discord.ui.Button(style=discord.ButtonStyle.success,label="업",disabled=onoffbool)
    downbutton = discord.ui.Button(style=discord.ButtonStyle.danger,label="다운",disabled=onoffbool)
    perfectbutton = discord.ui.Button(style=discord.ButtonStyle.primary,label="퍼펙트",disabled=onoffbool)

    kda_view = discord.ui.View()
    kda_view.add_item(upbutton)
    kda_view.add_item(downbutton)
    kda_view.add_item(perfectbutton)
        
    async def disable_buttons():
        if onoffbool: #투표 꺼져있다면 안함
            return
        await asyncio.sleep(150)  # 2분 30초 대기
        alarm_embed = discord.Embed(title="알림", description=f"{name}의 예측 종료까지 30초 남았습니다! ⏰", color=discord.Color.red())
        await channel.send(embed=alarm_embed)
        await asyncio.sleep(30) # 30초 대기
        winbutton.disabled = True
        losebutton.disabled = True
        upbutton.disabled = True
        downbutton.disabled = True
        perfectbutton.disabled = True
        prediction_view = discord.ui.View()
        kda_view = discord.ui.View()
        prediction_view.add_item(winbutton)
        prediction_view.add_item(losebutton)
        kda_view.add_item(upbutton)
        kda_view.add_item(downbutton)
        kda_view.add_item(perfectbutton)

        await p.current_messages[name].edit(view=prediction_view)
        await p.current_messages_kda[name].edit(view=kda_view)

    prediction_votes = votes["prediction"]
    kda_votes = votes["kda"]
    
    async def bet_button_callback(interaction: discord.Interaction = None, prediction_type: str = "", nickname: discord.Member = None):
        if interaction:
            nickname = interaction.user
            await interaction.response.defer()  # 응답 지연 (버튼 눌렀을 때 오류 방지)

        # 사용자가 이미 투표한 유형이 있는지 확인
        current_prediction_type = None

        for p_type in ["win", "lose"]:
            if nickname.name in [user['name'].name for user in prediction_votes[p_type]]:
                current_prediction_type = p_type
                break
        
        # 사용자가 같은 유형으로 투표하려는 경우, 이미 투표했다는 메시지를 보내고 함수 종료
        if current_prediction_type == prediction_type:
            userembed = discord.Embed(title="메세지", color=discord.Color.blue())
            userembed.add_field(name="", value=f"{nickname.display_name}님은 이미 {prediction_type}에 투표하셨습니다", inline=True)
            if interaction:
                await interaction.followup.send(embed=userembed, ephemeral=True)
            return
        
        # 사용자가 다른 유형으로 투표하려는 경우, 기존 투표를 제거하고 새로운 투표 추가
        if current_prediction_type:
            prediction_votes[current_prediction_type] = [user for user in prediction_votes[current_prediction_type] if user['name'].name != nickname.name]
            await refresh_prediction(name,prediction_votes) # 새로고침

        prediction_votes[prediction_type].append({"name": nickname})
        await refresh_prediction(name,prediction_votes) # 새로고침

    async def kda_button_callback(interaction: discord.Interaction, prediction_type: str):
        nickname = interaction.user
        await interaction.response.defer()

        # 사용자가 이미 투표한 유형이 있는지 확인
        current_prediction_type = None

        for kda_type in ["up", "down", "perfect"]:
            if nickname.name in [user['name'].name for user in kda_votes[kda_type]]:
                current_prediction_type = kda_type
                break
        
        # 사용자가 같은 유형으로 투표하려는 경우, 이미 투표했다는 메시지를 보내고 함수 종료
        if current_prediction_type == prediction_type:
            userembed = discord.Embed(title="메세지", color=discord.Color.dark_gray())
            userembed.add_field(name="", value=f"{nickname.display_name}님은 이미 {prediction_type}에 투표하셨습니다", inline=True)
            await interaction.followup.send(embed=userembed, ephemeral=True)
            return
        
        # 사용자가 다른 유형으로 투표하려는 경우, 기존 투표를 제거하고 새로운 투표 추가
        if current_prediction_type:
            kda_votes[current_prediction_type] = [user for user in kda_votes[current_prediction_type] if user['name'].name != nickname.name]
            await refresh_kda_prediction(name,kda_votes)
        
        kda_votes[prediction_type].append({"name": nickname})
        await refresh_kda_prediction(name,kda_votes)

    winbutton.callback = lambda interaction: bet_button_callback(interaction, 'win')
    losebutton.callback = lambda interaction: bet_button_callback(interaction, 'lose')
    upbutton.callback = lambda interaction: kda_button_callback(interaction, 'up')
    downbutton.callback = lambda interaction: kda_button_callback(interaction, 'down')
    perfectbutton.callback = lambda interaction: kda_button_callback(interaction, 'perfect')

    prediction_embed = discord.Embed(title=f"{name} 예측 현황", color=0x000000) # Black

    win_predictions = "\n".join(
        f"{winner['name'].display_name}" for winner in prediction_votes["win"]) or "없음"
    lose_predictions = "\n".join(
        f"{loser['name'].display_name}" for loser in prediction_votes["lose"]) or "없음"

    prediction_embed.add_field(name="승리 예측", value=win_predictions, inline=True)
    prediction_embed.add_field(name="패배 예측", value=lose_predictions, inline=True)

    kda_embed = discord.Embed(title=f"{name} KDA 예측 현황", color=0x000000) # Black

    up_predictions = "\n".join(f"{user['name'].display_name}" for user in kda_votes["up"]) or "없음"
    down_predictions = "\n".join(f"{user['name'].display_name}" for user in kda_votes["down"]) or "없음"
    perfect_predictions = "\n".join(f"{user['name'].display_name}" for user in kda_votes["perfect"]) or "없음"

    kda_embed.add_field(name="KDA 3 이상", value=up_predictions, inline=False)
    kda_embed.add_field(name="KDA 3 이하", value=down_predictions, inline=False)
    kda_embed.add_field(name="퍼펙트", value=perfect_predictions, inline=False)

    curseasonref = db.reference("전적분석/현재시즌")
    current_season = curseasonref.get()

    refprev = db.reference(f'전적분석/{current_season}/점수변동/{name}/{mode}')
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
    

    onoffref = db.reference("승부예측/이벤트온오프")

    streak_message = ""
    if game_win_streak >= 1:
        streak_message = f"{game_win_streak}연승 중!"
    elif game_lose_streak >= 1:        
        streak_message = f"{game_lose_streak}연패 중!"


    p.current_messages[name] = await channel.send(f"\n{name}의 {mode} 게임이 감지되었습니다!\n승부예측을 해보세요!\n{streak_message}", view=prediction_view, embed=prediction_embed)

    p.current_messages_kda[name] = await channel.send("\n", view=kda_view, embed=kda_embed)

    if not onoffbool:
        await notice_channel.send(f"{name}의 {mode} 게임이 감지되었습니다!\n승부예측을 해보세요!\n")
    
    guild = bot.get_guild(GUILD_ID)
    game_player = guild.get_member(MEMBER_MAP[name])
    await bet_button_callback(prediction_type='win', nickname=game_player)

    info_embed = await get_team_champion_embed(name, puuid, get_info_func=get_current_game_info)
    info_embed.color = 0x000000
    await channel.send("",embed=info_embed) # 그 판의 조합을 나타내는 embed를 보냄

    event.clear()
    await asyncio.gather(
        disable_buttons(),
        event.wait()  # 이 작업은 event가 set될 때까지 대기
    )
    opened_games.discard(game_id)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [LOG] {name}의 게임 종료! (게임 ID: {game_id}, 모드: {mode}")

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

        #await bot.tree.sync(guild=Object(id=298064707460268032))
        await bot.tree.sync()

    async def on_ready(self):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [LOG] {self.user}로 로그인 완료!")
        await self.change_presence(status=Status.online,
                                    activity=Game("만세중"))
        cred = credentials.Certificate("mykey.json")
        firebase_admin.initialize_app(cred,{
            'databaseURL' : 'https://mansaebot-default-rtdb.firebaseio.com/'
        })
        #await self.tree.sync(guild=Object(id=298064707460268032))
        
        await fetch_champion_data(True) # 챔피언 데이터를 받음
        await fetch_rune_id_to_key_map(True)
        await fetch_spell_id_to_key_map(True)

        bot.loop.create_task(monitor_games())
        bot.loop.create_task(monitor_endings())
    
        bot.loop.create_task(fetch_patch_version())
bot = MyBot()
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
API_KEY = os.getenv("RIOT_API_KEY")

PUUID = {
    "지모" : os.getenv("JIMO_PUUID"),
    "Melon" : os.getenv("MELON_PUUID"),
    "그럭저럭" : os.getenv("YOON_PUUID"),
    "이미름" : os.getenv("LEE_PUUID"),
    "박퇴경" : os.getenv("PARK_PUUID")
}

bot.run(TOKEN)