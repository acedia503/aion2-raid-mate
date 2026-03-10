import discord
from discord import app_commands
from discord.ext import commands

from storage import (
    init_db,
    get_guild_setting,
    delete_guild_setting,
    create_raid,
    get_raid,
    list_raids,
    delete_raid,
    raid_exists,
    count_raid_applications,
    delete_raid_applications,
    clear_raid_parties,
    get_application_by_character,
    create_application,
)

from views import (
    GuildSettingView,
    RaidDeleteConfirmView,
    ApplicationRaceServerView,
    WeekdayMultiSelectView,
)

from atool import get_character_info, AtoolError

# ========================================================
# 슬래시 선택지 정의
# ========================================================

RACE_CHOICES = [
    app_commands.Choice(name="천족", value="1"),
    app_commands.Choice(name="마족", value="2"),
]

SERVER_CHOICES = [
    app_commands.Choice(name="루", value="1001"),
    app_commands.Choice(name="시엘", value="1002"),
    app_commands.Choice(name="이스라펠", value="1003"),
    app_commands.Choice(name="진", value="2019"),
    app_commands.Choice(name="트리니엘", value="2020"),
    app_commands.Choice(name="카이시넬", value="2021"),
]

CONDITION_TYPE_CHOICES = [
    app_commands.Choice(name="템렙", value="item_level"),
    app_commands.Choice(name="아툴 점수", value="combat_score"),
]


# ========================================================
# 공통 유틸 함수
# ========================================================

def is_admin(interaction: discord.Interaction) -> bool:
    if interaction.guild is None:
        return False
    return interaction.user.guild_permissions.administrator


def get_race_name_by_code(race_code: str) -> str | None:
    for choice in RACE_CHOICES:
        if str(choice.value) == str(race_code):
            return choice.name
    return None


def get_server_name_by_code(server_code: str) -> str | None:
    for choice in SERVER_CHOICES:
        if str(choice.value) == str(server_code):
            return choice.name
    return None


def format_days(days: list[str]) -> str:
    return ", ".join(days) if days else "-"


# 레이드별 신청내역 그룹화
def group_applications_by_raid(applications: list[dict]) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}

    for app in applications:
        raid_name = app["raid_name"]
        if raid_name not in result:
            result[raid_name] = []
        result[raid_name].append(app)

    return result

# 신청 한 줄 포맷 함수
def format_application_line(app: dict) -> str:
    days = app.get("available_days") or []
    days_text = ", ".join(days) if days else "-"

    note = (app.get("note") or "").strip()
    note_text = note if note else "-"

    return (
        f"{app['character_name']} | "
        f"{app['race_name']} / {app['server_name']} | "
        f"{app['job_name']} | "
        f"{app['item_level']} | "
        f"{app['combat_score']} | "
        f"{days_text} | "
        f"{note_text}"
    )

# 레이드별 Embed 생성 함수
def build_raid_application_embed(
    raid_name: str,
    applications: list[dict],
) -> discord.Embed:

    embed = discord.Embed(
        title=f"[{raid_name}] 신청 내역",
        color=discord.Color.blue(),
    )

    header = (
        "캐릭터 | 종족/서버 | 직업 | 템렙 | 아툴 | 가능요일 | 특이사항"
    )

    separator = "-" * len(header)

    lines = []

    for app in applications:
        lines.append(format_application_line(app))

    body = "\n".join(lines) if lines else "-"

    embed.description = (
        "```"
        f"{header}\n"
        f"{separator}\n"
        f"{body}"
        "```"
    )

    return embed
    

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


# =========================================================
# /레이드생성 명령어
# =========================================================

# 관리자만 가능
# 동일 이름의 레이드 생성 불가

@bot.tree.command(name="레이드생성", description="이 서버에 레이드를 생성합니다.")
@app_commands.describe(
    레이드이름="생성할 레이드 이름",
    입장조건종류="입장조건 종류",
    입장조건값="입장조건 값",
)
@app_commands.choices(입장조건종류=CONDITION_TYPE_CHOICES)
async def create_raid_command(
    interaction: discord.Interaction,
    레이드이름: str,
    입장조건종류: app_commands.Choice[str],
    입장조건값: int,
):
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

    레이드이름 = 레이드이름.strip()
    if not 레이드이름:
        await interaction.response.send_message(
            "레이드 이름이 비어 있습니다.",
            ephemeral=True,
        )
        return

    if 입장조건값 < 0:
        await interaction.response.send_message(
            "입장조건 값은 0 이상이어야 합니다.",
            ephemeral=True,
        )
        return

    try:
        if raid_exists(interaction.guild.id, 레이드이름):
            await interaction.response.send_message(
                f"이 서버에는 이미 `{레이드이름}` 레이드가 존재합니다.",
                ephemeral=True,
            )
            return

        create_raid(
            guild_id=interaction.guild.id,
            raid_name=레이드이름,
            condition_type=입장조건종류.value,
            condition_value=입장조건값,
            created_by=interaction.user.id,
        )

        condition_label = "템렙" if 입장조건종류.value == "item_level" else "아툴 점수"

        embed = discord.Embed(
            title="레이드 생성 완료",
            color=discord.Color.green(),
        )
        embed.add_field(name="레이드 이름", value=레이드이름, inline=False)
        embed.add_field(name="입장 조건", value=f"{condition_label} {입장조건값}", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(
            f"레이드 생성 중 오류가 발생했습니다.\n`{e}`",
            ephemeral=True,
        )

# =========================================================
# /레이드확인
# =========================================================

# 관리자만 가능
# 현재 서버 레이드 목록 + 입장조건 + 신청자 수

@bot.tree.command(name="레이드확인", description="이 서버에 저장된 레이드 목록을 확인합니다.")
async def list_raids_command(interaction: discord.Interaction):
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
        raids = list_raids(interaction.guild.id)

        if not raids:
            await interaction.response.send_message(
                "이 서버에는 생성된 레이드가 없습니다.",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="현재 서버 레이드 목록",
            color=discord.Color.blue(),
        )

        for raid in raids:
            raid_name = raid["raid_name"]
            condition_type = raid["condition_type"]
            condition_value = raid["condition_value"]
            applicant_count = count_raid_applications(interaction.guild.id, raid_name)

            condition_label = "템렙" if condition_type == "item_level" else "아툴 점수"

            embed.add_field(
                name=raid_name,
                value=(
                    f"입장 조건: {condition_label} {condition_value}\n"
                    f"신청자 수: {applicant_count}명"
                ),
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(
            f"레이드 확인 중 오류가 발생했습니다.\n`{e}`",
            ephemeral=True,
        )


# =========================================================
# /레이드삭제
# =========================================================

# 관리자만 가능
# 레이드 존재 확인
# 신청자 수 확인
# 신청자 없으면 바로 삭제
# 신청자 있으면 UI로 물어봄
# “신청자까지 같이 삭제” 선택 시: applications 삭제, raid_parties 삭제, raids 삭제

@bot.tree.command(name="레이드삭제", description="이 서버의 레이드를 삭제합니다.")
@app_commands.describe(레이드이름="삭제할 레이드 이름")
async def delete_raid_command(interaction: discord.Interaction, 레이드이름: str):
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

    레이드이름 = 레이드이름.strip()
    if not 레이드이름:
        await interaction.response.send_message(
            "레이드 이름이 비어 있습니다.",
            ephemeral=True,
        )
        return

    try:
        raid = get_raid(interaction.guild.id, 레이드이름)
        if raid is None:
            await interaction.response.send_message(
                f"`{레이드이름}` 레이드는 존재하지 않습니다.",
                ephemeral=True,
            )
            return

        applicant_count = count_raid_applications(interaction.guild.id, 레이드이름)

        if applicant_count == 0:
            deleted = delete_raid(interaction.guild.id, 레이드이름)
            if deleted:
                await interaction.response.send_message(
                    f"`{레이드이름}` 레이드가 삭제되었습니다.",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    "레이드 삭제에 실패했습니다.",
                    ephemeral=True,
                )
            return

        view = RaidDeleteConfirmView(
            guild_id=interaction.guild.id,
            raid_name=레이드이름,
            user_id=interaction.user.id,
        )

        await interaction.response.send_message(
            f"`{레이드이름}` 레이드에는 현재 신청자 {applicant_count}명이 있습니다.\n"
            "신청자 목록과 생성된 공대 내역까지 같이 삭제하시겠습니까?",
            view=view,
            ephemeral=True,
        )

        timeout = await view.wait()
        if timeout:
            return

        if view.value == "cancel":
            return

        if view.value == "delete_with_applications":
            deleted_applications = delete_raid_applications(interaction.guild.id, 레이드이름)
            deleted_parties = clear_raid_parties(interaction.guild.id, 레이드이름)
            deleted_raid = delete_raid(interaction.guild.id, 레이드이름)

            if deleted_raid:
                await interaction.followup.send(
                    f"`{레이드이름}` 레이드 삭제 완료\n"
                    f"- 신청 삭제: {deleted_applications}건\n"
                    f"- 공대 내역 삭제: {deleted_parties}건",
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    "레이드 삭제 중 오류가 발생했습니다.",
                    ephemeral=True,
                )

    except Exception as e:
        if interaction.response.is_done():
            await interaction.followup.send(
                f"레이드 삭제 중 오류가 발생했습니다.\n`{e}`",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"레이드 삭제 중 오류가 발생했습니다.\n`{e}`",
                ephemeral=True,
            )

# =========================================================
# /아툴
# =========================================================

# 1) 종족/서버 둘 다 안 넣음
# 현재 디스코드 서버의 guild_settings 사용
# 설정이 없으면 안내 메시지 출력

# 2) 종족/서버 둘 다 넣음
# 입력한 값으로 직접 조회

# 3) 둘 중 하나만 넣음
# 에러 메시지 출력

@bot.tree.command(name="아툴", description="아이온2 캐릭터 아툴 정보를 조회합니다.")
@app_commands.describe(
    캐릭터명="조회할 캐릭터 이름",
    종족="직접 지정할 종족 (선택)",
    종족서버="직접 지정할 종족 서버 (선택)",
)
@app_commands.choices(종족=RACE_CHOICES, 종족서버=SERVER_CHOICES)
async def search_atool(
    interaction: discord.Interaction,
    캐릭터명: str,
    종족: app_commands.Choice[str] | None = None,
    종족서버: app_commands.Choice[str] | None = None,
):
    if interaction.guild is None:
        await interaction.response.send_message(
            "서버 안에서만 사용할 수 있는 명령어입니다.",
            ephemeral=True,
        )
        return

    캐릭터명 = 캐릭터명.strip()
    if not 캐릭터명:
        await interaction.response.send_message(
            "캐릭터명이 비어 있습니다.",
            ephemeral=True,
        )
        return

    # 둘 중 하나만 입력한 경우 에러
    if (종족 is None) != (종족서버 is None):
        await interaction.response.send_message(
            "종족과 종족서버는 둘 다 입력하거나, 둘 다 입력하지 않아야 합니다.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True, thinking=True)

    try:
        # 1) 직접 입력한 경우
        if 종족 is not None and 종족서버 is not None:
            race_code = str(종족.value)
            race_name = str(종족.name)
            server_code = str(종족서버.value)
            server_name = str(종족서버.name)

        # 2) 직접 입력이 없으면 guild 기본 설정 사용
        else:
            setting = get_guild_setting(interaction.guild.id)
            if setting is None:
                await interaction.followup.send(
                    "이 서버에는 기본 종족/서버 설정이 없습니다.\n"
                    "관리자가 `/설정`을 먼저 해두었거나, `/아툴`에서 종족과 종족서버를 직접 모두 입력해야 합니다.",
                    ephemeral=True,
                )
                return

            race_code = str(setting["race_code"])
            race_name = str(setting["race_name"])
            server_code = str(setting["server_code"])
            server_name = str(setting["server_name"])

        data = get_character_info(
            race_code=race_code,
            race_name=race_name,
            server_code=server_code,
            server_name=server_name,
            character_name=캐릭터명,
        )

        embed = discord.Embed(
            title=f"{data['nickname']} 아툴 조회",
            color=discord.Color.blue(),
        )
        embed.add_field(name="종족", value=data["race_name"], inline=False)
        embed.add_field(name="종족서버", value=data["server_name"], inline=False)
        embed.add_field(name="직업", value=data["job_name"], inline=False)
        embed.add_field(name="템렙", value=str(data["item_level"]), inline=False)
        embed.add_field(name="아툴 점수", value=str(data["combat_score"]), inline=False)
        embed.add_field(name="최고 아툴 점수", value=str(data["peak_combat_score"]), inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

    except AtoolError as e:
        await interaction.followup.send(
            f"아툴 조회 실패: {e}",
            ephemeral=True,
        )
    except Exception as e:
        await interaction.followup.send(
            f"아툴 조회 중 오류가 발생했습니다.\n`{e}`",
            ephemeral=True,
        )


# =========================================================
# /신청 명령어
# =========================================================

@bot.tree.command(name="신청", description="레이드 신청")
@app_commands.describe(
    레이드이름="신청할 레이드 이름",
    캐릭터명="아툴에서 조회할 캐릭터명",
)
async def apply_raid(
    interaction: discord.Interaction,
    레이드이름: str,
    캐릭터명: str,
):
    if interaction.guild is None:
        await interaction.response.send_message(
            "서버 안에서만 사용할 수 있는 명령어입니다.",
            ephemeral=True,
        )
        return

    레이드이름 = 레이드이름.strip()
    캐릭터명 = 캐릭터명.strip()

    if not 레이드이름:
        await interaction.response.send_message(
            "레이드 이름이 비어 있습니다.",
            ephemeral=True,
        )
        return

    if not 캐릭터명:
        await interaction.response.send_message(
            "캐릭터명이 비어 있습니다.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True, thinking=True)

    try:
        # 1) 레이드 존재 확인
        raid = get_raid(interaction.guild.id, 레이드이름)
        if raid is None:
            await interaction.followup.send(
                f"`{레이드이름}` 레이드는 존재하지 않습니다.",
                ephemeral=True,
            )
            return

        # 2) guild 기본 설정 확인
        guild_setting = get_guild_setting(interaction.guild.id)

        if guild_setting is not None:
            race_code = str(guild_setting["race_code"])
            race_name = str(guild_setting["race_name"])
            server_code = str(guild_setting["server_code"])
            server_name = str(guild_setting["server_name"])
            used_default_setting = True
        else:
            used_default_setting = False

            race_server_view = ApplicationRaceServerView(user_id=interaction.user.id)
            await interaction.followup.send(
                "이 서버에는 기본 종족/서버 설정이 없습니다.\n"
                "신청에 사용할 종족과 종족 서버를 선택하세요.",
                view=race_server_view,
                ephemeral=True,
            )

            timeout = await race_server_view.wait()
            if timeout:
                await interaction.followup.send(
                    "종족/종족 서버 선택 시간이 초과되었습니다.",
                    ephemeral=True,
                )
                return

            if race_server_view.value != "submit":
                return

            race_code = str(race_server_view.selected_race_code)
            race_name = str(race_server_view.selected_race_name)
            server_code = str(race_server_view.selected_server_code)
            server_name = str(race_server_view.selected_server_name)

        # 3) 중복 신청 확인
        existing = get_application_by_character(
            guild_id=interaction.guild.id,
            raid_name=레이드이름,
            race_code=race_code,
            server_code=server_code,
            character_name=캐릭터명,
        )
        if existing is not None:
            await interaction.followup.send(
                f"`{레이드이름}` 레이드에는 이미 `{캐릭터명}` 캐릭터가 신청되어 있습니다.",
                ephemeral=True,
            )
            return

        # 4) 아툴 조회
        data = get_character_info(
            race_code=race_code,
            race_name=race_name,
            server_code=server_code,
            server_name=server_name,
            character_name=캐릭터명,
        )

        # 5) 입장 조건 검사
        condition_type = str(raid["condition_type"])
        condition_value = int(raid["condition_value"])

        if condition_type == "item_level":
            current_value = int(data["item_level"])
            condition_label = "템렙"
        else:
            current_value = int(data["combat_score"])
            condition_label = "아툴 점수"

        if current_value < condition_value:
            await interaction.followup.send(
                f"신청 불가: `{레이드이름}` 레이드의 입장 조건은 "
                f"`{condition_label} {condition_value}` 이상입니다.\n"
                f"현재 캐릭터 수치: `{current_value}`",
                ephemeral=True,
            )
            return

        # 6) 가능 요일 / 특이사항 입력
        weekday_view = WeekdayMultiSelectView(user_id=interaction.user.id)

        await interaction.followup.send(
            f"`{캐릭터명}` 신청을 진행합니다.\n"
            "가능 요일을 선택하세요.",
            view=weekday_view,
            ephemeral=True,
        )

        timeout = await weekday_view.wait()
        if timeout:
            await interaction.followup.send(
                "가능 요일 입력 시간이 초과되었습니다.",
                ephemeral=True,
            )
            return

        if weekday_view.value not in ("submit", "submit_with_note"):
            return

        available_days = weekday_view.selected_days
        note = weekday_view.note

        # 7) DB 저장
        create_application(
            {
                "guild_id": interaction.guild.id,
                "user_id": interaction.user.id,
                "user_name": interaction.user.display_name,
                "raid_name": 레이드이름,
                "race_code": race_code,
                "race_name": race_name,
                "server_code": server_code,
                "server_name": server_name,
                "character_name": data["nickname"],
                "job_name": data["job_name"],
                "item_level": data["item_level"],
                "combat_score": data["combat_score"],
                "peak_combat_score": data["peak_combat_score"],
                "available_days": available_days,
                "note": note,
            }
        )

        # 8) 공개 신청 완료 메시지
        embed = discord.Embed(
            title=f"[{레이드이름}] 신청 완료",
            color=discord.Color.green(),
        )
        embed.add_field(name="캐릭터명", value=data["nickname"], inline=False)

        # 관리자 기본 설정이 없었을 때만 종족/서버 표시
        if not used_default_setting:
            embed.add_field(
                name="종족/종족서버",
                value=f"{race_name} / {server_name}",
                inline=False,
            )

        embed.add_field(name="직업", value=data["job_name"], inline=False)
        embed.add_field(name="템렙", value=str(data["item_level"]), inline=False)
        embed.add_field(name="아툴 점수", value=str(data["combat_score"]), inline=False)
        embed.add_field(name="가능 요일", value=format_days(available_days), inline=False)

        if note:
            embed.add_field(name="특이사항", value=note, inline=False)

        await interaction.followup.send(embed=embed, ephemeral=False)

        await interaction.followup.send(
            "신청이 저장되었습니다.",
            ephemeral=True,
        )

    except AtoolError as e:
        await interaction.followup.send(
            f"아툴 조회 실패: {e}",
            ephemeral=True,
        )
    except Exception as e:
        await interaction.followup.send(
            f"신청 처리 중 오류가 발생했습니다.\n`{e}`",
            ephemeral=True,
        )


# =========================================================
# /신청확인
# =========================================================

@bot.tree.command(name="신청확인", description="내 레이드 신청 내역을 확인합니다.")
@app_commands.describe(
    레이드이름="확인할 레이드 이름 (선택)",
)
async def check_my_applications(
    interaction: discord.Interaction,
    레이드이름: str | None = None,
):

    if interaction.guild is None:
        await interaction.response.send_message(
            "서버 안에서만 사용할 수 있는 명령어입니다.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True)

    try:
        raid_name = 레이드이름.strip() if 레이드이름 else None

        applications = list_user_applications(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            raid_name=raid_name,
        )

        if not applications:
            if raid_name:
                await interaction.followup.send(
                    f"`{raid_name}` 레이드 신청 내역이 없습니다.",
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    "신청한 레이드 내역이 없습니다.",
                    ephemeral=True,
                )
            return

        grouped = group_applications_by_raid(applications)

        await interaction.followup.send(
            f"신청 내역 {len(applications)}건입니다.",
            ephemeral=True,
        )

        for raid_name, apps in grouped.items():
            embed = build_raid_application_embed(raid_name, apps)
            await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.followup.send(
            f"신청 확인 중 오류가 발생했습니다.\n`{e}`",
            ephemeral=True,
        )

@bot.event
async def on_ready():
    init_db()
    await bot.tree.sync()
    print(f"{bot.user} 로그인 완료")


bot.run("DISCORD_TOKEN")
