import discord
from discord import app_commands
from discord.ext import commands

from storage import (
    init_db,
    get_guild_setting,
    delete_guild_setting,
)

from views import GuildSettingView

# ========================================================
# 슬래시 선택지 정의
# ========================================================

RACE_OPTIONS = [
    {"name": "천족", "code": "1"},
    {"name": "마족", "code": "2"},
]

SERVER_OPTIONS = [
    {"name": "루", "code": "1001"},
    {"name": "시엘", "code": "1002"},
    {"name": "이스라펠", "code": "1003"},
    {"name": "루드라", "code": "2019"},
    {"name": "트리니엘", "code": "2020"},
]


# ========================================================
# 공통 유틸 함수
# ========================================================

def is_admin(interaction: discord.Interaction) -> bool:
    if interaction.guild is None:
        return False
    return interaction.user.guild_permissions.administrator


# ========================================================
# 봇 생성
# ========================================================

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# =========================================================
# /설정 명령어
# =========================================================

# 관리자만 가능
# 같은 서버에서 다시 실행하면 수정
# 서버당 1개 설정만 유지

@bot.tree.command(name="설정", description="이 디스코드 서버의 기본 아이온2 종족/서버를 설정합니다.")
async def set_default_aion2(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message(
            "서버 안에서만 사용할 수 있는 명령어입니다.",
            ephemeral=True,
        )
        return

    if not is_admin(interaction):
        await interaction.response.send_message(
            "관리자만 사용할 수 있는 명령어입니다.",
            ephemeral=True,
        )
        return

    view = GuildSettingView(
        guild_id=interaction.guild.id,
        user_id=interaction.user.id,
    )

    await interaction.response.send_message(
        "아이온2 기본 설정을 진행합니다.\n먼저 종족을 선택하세요.",
        view=view,
        ephemeral=True,
    )


# =========================================================
# /설정확인 명령어
# =========================================================

# 관리자만 가능
# 현재 서버 설정이 있으면 보여주고, 없으면 없다고 안내.

@bot.tree.command(name="설정확인", description="이 디스코드 서버의 현재 기본 설정을 확인합니다.")
async def check_default_aion2(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message(
            "서버 안에서만 사용할 수 있는 명령어입니다.",
            ephemeral=True,
        )
        return

    if not is_admin(interaction):
        await interaction.response.send_message(
            "관리자만 사용할 수 있는 명령어입니다.",
            ephemeral=True,
        )
        return

    try:
        setting = get_guild_setting(interaction.guild.id)

        if setting is None:
            await interaction.response.send_message(
                "이 서버에는 저장된 기본 설정이 없습니다.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="현재 서버 기본 설정",
            color=discord.Color.blue(),
        )
        embed.add_field(name="종족", value=setting["race_name"], inline=True)
        embed.add_field(name="종족서버", value=setting["server_name"], inline=True)
        embed.add_field(name="수정자 ID", value=str(setting["updated_by"]), inline=False)
        embed.set_footer(text=f"수정 시각: {setting['updated_at']}")

        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(
            f"설정 확인 중 오류가 발생했습니다.\n`{e}`",
            ephemeral=True,
        )


# =========================================================
# /설정삭제 명령어
# =========================================================

# 관리자만 가능
# 현재 서버의 기본 설정 삭제
# 기존 신청 DB나 공대 DB는 영향 없게 설계

@bot.tree.command(name="설정삭제", description="이 디스코드 서버의 기본 설정을 삭제합니다.")
async def delete_default_aion2(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message(
            "서버 안에서만 사용할 수 있는 명령어입니다.",
            ephemeral=True,
        )
        return

    if not is_admin(interaction):
        await interaction.response.send_message(
            "관리자만 사용할 수 있는 명령어입니다.",
            ephemeral=True,
        )
        return

    try:
        deleted = delete_guild_setting(interaction.guild.id)

        if deleted == 0:
            await interaction.response.send_message(
                "삭제할 기본 설정이 없습니다.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            "이 서버의 기본 설정이 삭제되었습니다.\n"
            "기존 신청 내역과 공대 생성 내역은 유지됩니다.",
            ephemeral=True,
        )
    except Exception as e:
        await interaction.response.send_message(
            f"설정 삭제 중 오류가 발생했습니다.\n`{e}`",
            ephemeral=True,
        )



@bot.event
async def on_ready():
    init_db()
    await bot.tree.sync()
    print(f"{bot.user} 로그인 완료")


bot.run("DISCORD_TOKEN")
