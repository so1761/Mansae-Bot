import discord
import asyncio
# 데이터 저장 파일
# 예측한 사람들을 저장할 딕셔너리
prediction_votes = {
    "win": [],
    "lose": []
} #지모

kda_votes = {
    "up": [],
    "down": [],
    "perfect": []
} #지모 KDA

prediction_votes2 = {
    "win": [],
    "lose": []
} #동성

kda_votes2 = {
    "up": [],
    "down": [],
    "perfect": []
} #동성 KDA


# 예측한 사람들을 저장할 딕셔너리
votes = {
    "지모": {
        "prediction": {
            "win": [],
            "lose": []
        },
        "kda": {
            "up": [],
            "down": [],
            "perfect": []
        }
    },
    "Melon": {
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
}


prediction_embed = discord.Embed()
prediction2_embed = discord.Embed()

kda_embed = discord.Embed()
kda2_embed = discord.Embed()

jimo_winbutton = discord.ui.Button()
jimo_losebutton = discord.ui.Button()

jimo_upbutton = discord.ui.Button()
jimo_downbutton = discord.ui.Button()
jimo_perfectbutton = discord.ui.Button()

melon_winbutton = discord.ui.Button()
melon_losebutton = discord.ui.Button()

melon_upbutton = discord.ui.Button()
melon_downbutton = discord.ui.Button()
melon_perfectbutton = discord.ui.Button()

global current_message_jimo
global current_message_melon

global current_message_kda_jimo
global current_message_kda_melon

global jimo_current_match_id
global melon_current_match_id

jimo_current_game_state = False
melon_current_game_state = False

jimo_event = asyncio.Event()
melon_event = asyncio.Event()