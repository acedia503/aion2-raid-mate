import discord
from discord.ext import commands

from storage import init_db

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


@bot.event
async def on_ready():
    init_db()
    await bot.tree.sync()
    print(f"{bot.user} 로그인 완료")


bot.run("DISCORD_TOKEN")
