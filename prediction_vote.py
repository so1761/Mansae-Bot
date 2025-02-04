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

current_message_jimo = ""
current_message_melon = ""

current_message_kda_jimo = ""
current_message_kda_melon = ""

jimo_current_match_id = ""
melon_current_match_id = ""

jimo_current_game_state = False
melon_current_game_state = False

jimo_event = asyncio.Event()
melon_event = asyncio.Event()