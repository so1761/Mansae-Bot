import discord
import asyncio
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

jimo_winbutton = discord.ui.Button(style=discord.ButtonStyle.success,label="승리")

melon_winbutton = discord.ui.Button(style=discord.ButtonStyle.success,label="승리")

global current_message_jimo
global current_message_melon
current_message_jimo = None
current_message_melon = None

current_message_kda_jimo = None
current_message_kda_melon = None

jimo_current_match_id = None
melon_current_match_id = None

jimo_current_game_state = False
melon_current_game_state = False

jimo_event = asyncio.Event()
melon_event = asyncio.Event()

current_test_message = ""