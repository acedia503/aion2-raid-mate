from storage import init_db

@bot.event
async def on_ready():
    init_db()
    await bot.tree.sync()
    print(f"{bot.user} 로그인 완료")
