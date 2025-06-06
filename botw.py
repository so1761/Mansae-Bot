import firebase_admin
import os
from firebase_admin import credentials
from discord import Intents
from discord.ext import commands
from discord import Game
from discord import Status
from dotenv import load_dotenv

TARGET_TEXT_CHANNEL_ID = 1289184218135396483
TOKEN = None
API_KEY = None

CHANNEL_ID = '938728993329397781'

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=Intents.all(),
            sync_command=True,
            application_id=1234122732459921418
        )
        self.initial_extension = [
            "Cogs.battle_commands"
        ]

    async def setup_hook(self):
        for ext in self.initial_extension:
            await self.load_extension(ext)

        #await bot.tree.sync(guild=Object(id=298064707460268032))
        await bot.tree.sync()

    async def on_ready(self):
        print('Logged on as', self.user)
        await self.change_presence(status=Status.online,
                                    activity=Game("배틀"))
        cred = credentials.Certificate("mykey.json")
        firebase_admin.initialize_app(cred,{
            'databaseURL' : 'https://mansaebot-default-rtdb.firebaseio.com/'
        })
        #await self.tree.sync(guild=Object(id=298064707460268032))

bot = MyBot()
@bot.event
async def on_message(message):

    if message.author == bot.user:
        return


load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN_WEAPON")

bot.run(TOKEN)