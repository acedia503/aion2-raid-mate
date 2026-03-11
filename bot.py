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
    get_user_application,
    get_application_by_character,
    create_application,
    list_user_applications,
    list_applications_by_character_name,
    delete_application,
    update_application,
    list_raid_applications_by_weekday,
    list_raid_parties,
    replace_raid_parties,
    move_party_member_to_slot,
    move_party_member_to_waiting,
    load_party_rules,
    save_party_rules,
    has_party_rules,
    update_party_member_position,
    swap_party_members_position,
)

from raid_logic import (
    build_balanced_raids,
    exclude_already_generated_characters,
    flatten_raids_to_party_rows,
    PartyConfirmVisibilityView,
    find_matching_generated_members,
    find_matching_generated_member,
    can_move_member_to_target,
    find_first_empty_slot,
    find_replace_candidate_in_party,
    list_members_in_party,
)

from views import (
    GuildSettingView,
    RaidDeleteConfirmView,
    ApplicationRaceServerView,
    WeekdayMultiSelectView,
    ApplicationCancelView,
    ForceDeleteRaceServerView,
    PartyRuleSetupView
    PartyReplaceModeView,
    PartyReplaceView,
)

from atool import get_character_info, AtoolError

# ========================================================
# 슬래시 선택지 정의
# ========================================================

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


# 취소 완료 메시지용
def build_cancel_result_text(application: dict) -> str:
    days = application.get("available_days") or []
    days_text = ", ".join(days) if days else "-"
    note = (application.get("note") or "").strip() or "-"

    return (
        f"신청이 취소되었습니다.\n"
        f"- 레이드: {application['raid_name']}\n"
        f"- 캐릭터: {application['character_name']}\n"
        f"- 종족/종족서버: {application['race_name']} / {application['server_name']}\n"
        f"- 직업: {application['job_name']}\n"
        f"- 템렙: {application['item_level']}\n"
        f"- 아툴 점수: {application['combat_score']}\n"
        f"- 가능 요일: {days_text}\n"
        f"- 특이사항: {note}"
    )

# 강제삭제 결과 메시지용
def build_force_delete_result_text(application: dict) -> str:
    days = application.get("available_days") or []
    days_text = ", ".join(days) if days else "-"
    note = (application.get("note") or "").strip() or "-"

    return (
        f"신청 내역이 강제삭제되었습니다.\n"
        f"- 신청자: {application['user_name']}\n"
        f"- 레이드: {application['raid_name']}\n"
        f"- 캐릭터: {application['character_name']}\n"
        f"- 종족/종족서버: {application['race_name']} / {application['server_name']}\n"
        f"- 직업: {application['job_name']}\n"
        f"- 템렙: {application['item_level']}\n"
        f"- 아툴 점수: {application['combat_score']}\n"
        f"- 가능 요일: {days_text}\n"
        f"- 특이사항: {note}"
    )



# 기본 슬롯 규칙 함수
def build_default_all_slot_rules() -> list[dict]:
    return [
        {"slot_index": 1, "role_type": "ALL", "preferred_jobs": []},
        {"slot_index": 2, "role_type": "ALL", "preferred_jobs": []},
        {"slot_index": 3, "role_type": "ALL", "preferred_jobs": []},
        {"slot_index": 4, "role_type": "ALL", "preferred_jobs": []},
        {"slot_index": 5, "role_type": "ALL", "preferred_jobs": []},
        {"slot_index": 6, "role_type": "ALL", "preferred_jobs": []},
        {"slot_index": 7, "role_type": "ALL", "preferred_jobs": []},
        {"slot_index": 8, "role_type": "ALL", "preferred_jobs": []},
    ]

# 공대 확인용
def group_party_rows_by_weekday(rows: list[dict]) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    for row in rows:
        weekday = str(row.get("weekday", "-")).strip()
        if weekday not in result:
            result[weekday] = []
        result[weekday].append(row)
    return result


def convert_rows_to_raid_structure(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    raid_map: dict[int, dict] = {}
    waiting_members: list[dict] = []

    for row in rows:
        status = str(row.get("status", "")).strip()

        member = {
            "id": row.get("id"),
            "user_id": row.get("user_id"),
            "user_name": row.get("user_name"),
            "race_code": row.get("race_code"),
            "race_name": row.get("race_name"),
            "server_code": row.get("server_code"),
            "server_name": row.get("server_name"),
            "character_name": row.get("character_name"),
            "job_name": row.get("job_name"),
            "item_level": row.get("item_level"),
            "combat_score": row.get("combat_score"),
            "note": row.get("note"),
            "source_application_id": row.get("source_application_id"),
        }

        if status == "WAITING":
            waiting_members.append(member)
            continue

        raid_no = int(row.get("raid_no", 0))
        party_no = int(row.get("party_no", 0))
        slot_no = int(row.get("slot_no", 0))

        if raid_no not in raid_map:
            raid_map[raid_no] = {
                "raid_no": raid_no,
                "party1": [],
                "party2": [],
            }

        raid = raid_map[raid_no]
        party_key = "party1" if party_no == 1 else "party2"
        party = raid[party_key]

        while len(party) < slot_no:
            party.append({})

        party[slot_no - 1] = member

    raids = []
    for raid_no in sorted(raid_map.keys()):
        raid = raid_map[raid_no]
        raid["party1"] = [m for m in raid["party1"] if m]
        raid["party2"] = [m for m in raid["party2"] if m]
        raids.append(raid)

    return raids, waiting_members



# 공대 수정용
def build_party_update_embed(
    raid_name: str,
    source_weekday: str,
    moved_member: dict,
    target_weekday: str,
    target_raid_no: int | None,
    target_party_no: int | None,
    target_slot_no: int | None,
    replaced_member: dict | None = None,
    replace_mode: str | None = None,
) -> discord.Embed:
    embed = discord.Embed(
        title=f"[{raid_name}] 공대 수정 완료",
        color=discord.Color.orange(),
    )

    embed.add_field(
        name="이동 캐릭터",
        value=(
            f"{moved_member['character_name']} | "
            f"{moved_member['race_name']} / {moved_member['server_name']} | "
            f"{moved_member['job_name']} | "
            f"{moved_member['item_level']} | "
            f"{moved_member['combat_score']}"
        ),
        inline=False,
    )

    source_position = (
        "대기"
        if str(moved_member.get("status")) == "WAITING"
        else f"{source_weekday} / {moved_member.get('raid_no')}공대 {moved_member.get('party_no')}파티 {moved_member.get('slot_no')}번"
    )
    embed.add_field(name="기존 위치", value=source_position, inline=False)

    if target_party_no is None or target_slot_no is None:
        target_position = f"{target_weekday} / 대기"
    else:
        target_position = f"{target_weekday} / {target_raid_no}공대 {target_party_no}파티 {target_slot_no}번"

    embed.add_field(name="이동 위치", value=target_position, inline=False)

    if replaced_member is not None:
        if replace_mode == "swap":
            embed.add_field(
                name="교체 캐릭터",
                value=(
                    f"{replaced_member['character_name']} | "
                    f"{replaced_member['race_name']} / {replaced_member['server_name']} | "
                    f"{replaced_member['job_name']} | "
                    f"{replaced_member['item_level']} | "
                    f"{replaced_member['combat_score']}"
                ),
                inline=False,
            )
        elif replace_mode == "waiting":
            embed.add_field(
                name="대기 이동 캐릭터",
                value=(
                    f"{replaced_member['character_name']} | "
                    f"{replaced_member['race_name']} / {replaced_member['server_name']} | "
                    f"{replaced_member['job_name']} | "
                    f"{replaced_member['item_level']} | "
                    f"{replaced_member['combat_score']}"
                ),
                inline=False,
            )

    embed.set_footer(text="※ 템렙/아툴 점수는 공대 생성 시 기준입니다.")
    return embed


# Atool 재조회

def refresh_candidate_with_atool(candidate: dict) -> dict:
    """
    applications의 신청 원본 데이터를 기반으로
    공대 생성 시점 아툴 정보를 다시 조회해 최신값으로 덮어쓴다.
    조회 실패 시 기존 DB 값 유지.
    """
    refreshed = dict(candidate)

    try:
        data = get_character_info(
            race_code=str(candidate["race_code"]),
            race_name=str(candidate["race_name"]),
            server_code=str(candidate["server_code"]),
            server_name=str(candidate["server_name"]),
            character_name=str(candidate["character_name"]),
        )

        refreshed["character_name"] = data["nickname"]
        refreshed["job_name"] = data["job_name"]
        refreshed["item_level"] = data["item_level"]
        refreshed["combat_score"] = data["combat_score"]
        refreshed["peak_combat_score"] = data["peak_combat_score"]

    except AtoolError:
        # 재조회 실패 시 신청 DB 저장값 그대로 유지
        pass
    except Exception:
        # 예기치 않은 오류도 생성 전체를 막지 않고 기존 값 유지
        pass

    return refreshed


def refresh_candidates_for_party_generation(candidates: list[dict]) -> tuple[list[dict], list[str]]:
    """
    후보 전원을 공대 생성 시점 기준으로 재조회.
    실패한 경우는 기존 값 유지하고 warning만 남긴다.
    """
    refreshed_candidates: list[dict] = []
    warnings: list[str] = []

    for candidate in candidates:
        original_score = int(candidate.get("combat_score", 0))
        original_level = int(candidate.get("item_level", 0))

        refreshed = dict(candidate)

        try:
            data = get_character_info(
                race_code=str(candidate["race_code"]),
                race_name=str(candidate["race_name"]),
                server_code=str(candidate["server_code"]),
                server_name=str(candidate["server_name"]),
                character_name=str(candidate["character_name"]),
            )

            refreshed["character_name"] = data["nickname"]
            refreshed["job_name"] = data["job_name"]
            refreshed["item_level"] = data["item_level"]
            refreshed["combat_score"] = data["combat_score"]
            refreshed["peak_combat_score"] = data["peak_combat_score"]

            if (
                int(data["combat_score"]) != original_score
                or int(data["item_level"]) != original_level
            ):
                warnings.append(
                    f"재조회 반영: {candidate['character_name']} | "
                    f"템렙 {original_level}→{data['item_level']} | "
                    f"아툴 {original_score}→{data['combat_score']}"
                )

        except AtoolError as e:
            warnings.append(
                f"재조회 실패(기존값 유지): {candidate['character_name']} | {e}"
            )
        except Exception as e:
            warnings.append(
                f"재조회 오류(기존값 유지): {candidate['character_name']} | {e}"
            )

        refreshed_candidates.append(refreshed)

    return refreshed_candidates, warnings


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


# =========================================================
# /신청취소
# =========================================================

@bot.tree.command(name="신청취소", description="내 레이드 신청을 취소합니다.")
@app_commands.describe(
    레이드이름="취소할 레이드 이름",
    캐릭터명="취소할 캐릭터명",
)
async def cancel_application_command(
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
        applications = list_user_applications(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            raid_name=레이드이름,
        )

        if not applications:
            await interaction.followup.send(
                f"`{레이드이름}` 레이드에 신청한 내역이 없습니다.",
                ephemeral=True,
            )
            return

        matched = [
            app for app in applications
            if str(app["character_name"]).strip() == 캐릭터명
        ]

        if not matched:
            await interaction.followup.send(
                f"`{레이드이름}` 레이드에 `{캐릭터명}` 캐릭터 신청 내역이 없습니다.",
                ephemeral=True,
            )
            return

        # 같은 레이드 안에서 같은 캐릭터명은 유니크 구조라 보통 1건이어야 함
        target = matched[0]

        deleted = delete_application(int(target["id"]))
        if not deleted:
            await interaction.followup.send(
                "신청 취소에 실패했습니다.",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            build_cancel_result_text(target),
            ephemeral=True,
        )

    except Exception as e:
        await interaction.followup.send(
            f"신청 취소 중 오류가 발생했습니다.\n`{e}`",
            ephemeral=True,
        )


# ========================================================
# /강제삭제
# ========================================================

@bot.tree.command(name="강제삭제", description="관리자가 레이드 신청 내역을 강제로 삭제합니다.")
@app_commands.describe(
    레이드이름="삭제할 레이드 이름",
    캐릭터명="삭제할 캐릭터명",
)
async def force_delete_application_command(
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

    if not is_admin(interaction):
        await interaction.response.send_message(
            "관리자만 사용할 수 있는 명령어입니다.",
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
        matched = list_applications_by_character_name(
            guild_id=interaction.guild.id,
            raid_name=레이드이름,
            character_name=캐릭터명,
        )

        if not matched:
            await interaction.followup.send(
                f"`{레이드이름}` 레이드에 `{캐릭터명}` 캐릭터 신청 내역이 없습니다.",
                ephemeral=True,
            )
            return

        # 1건이면 바로 삭제
        if len(matched) == 1:
            target = matched[0]
            deleted = delete_application(int(target["id"]))

            if deleted:
                await interaction.followup.send(
                    build_force_delete_result_text(target),
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    "강제삭제에 실패했습니다.",
                    ephemeral=True,
                )
            return

        # 여러 건이면 종족/서버 선택
        view = ForceDeleteRaceServerView(
            user_id=interaction.user.id,
            applications=matched,
        )

        await interaction.followup.send(
            f"`{레이드이름}` 레이드에 `{캐릭터명}` 이름의 신청이 여러 건 있습니다.\n"
            "삭제할 종족/서버를 선택하세요.",
            view=view,
            ephemeral=True,
        )

        timeout = await view.wait()
        if timeout:
            await interaction.followup.send(
                "강제삭제 선택 시간이 초과되었습니다.",
                ephemeral=True,
            )
            return

        if view.value != "submit" or view.selected_application is None:
            return

        target = view.selected_application
        deleted = delete_application(int(target["id"]))

        if deleted:
            await interaction.followup.send(
                build_force_delete_result_text(target),
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                "강제삭제에 실패했습니다.",
                ephemeral=True,
            )

    except Exception as e:
        await interaction.followup.send(
            f"강제삭제 중 오류가 발생했습니다.\n`{e}`",
            ephemeral=True,
        )


# ========================================================
# /신청수정
# ========================================================

@bot.tree.command(name="신청수정", description="내 레이드 신청 내역을 수정합니다.")
@app_commands.describe(
    레이드이름="수정할 레이드 이름",
    캐릭터명="수정할 캐릭터명",
)
async def update_application_command(
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

        # 2) 서버 기본 설정 확인
        guild_setting = get_guild_setting(interaction.guild.id)

        if guild_setting is not None:
            race_code = str(guild_setting["race_code"])
            race_name = str(guild_setting["race_name"])
            server_code = str(guild_setting["server_code"])
            server_name = str(guild_setting["server_name"])
            used_default_setting = True
        else:
            used_default_setting = False

            # 캐릭터명 동일, 레이드 동일인 내 신청건들을 먼저 조회해
            # 같은 이름이 여러 종족/서버에 있을 수 있으니 후보를 넓게 찾는다.
            my_apps = list_user_applications(
                guild_id=interaction.guild.id,
                user_id=interaction.user.id,
                raid_name=레이드이름,
            )

            name_matched = [
                app for app in my_apps
                if str(app["character_name"]).strip() == 캐릭터명
            ]

            if not name_matched:
                await interaction.followup.send(
                    f"`{레이드이름}` 레이드에 `{캐릭터명}` 캐릭터 신청 내역이 없습니다.",
                    ephemeral=True,
                )
                return

            # 설정이 없는 경우, 기존 신청건이 1건이면 그 신청건의 종족/서버를 기본값처럼 사용
            # 여러 건이면 새로 선택받는다.
            if len(name_matched) == 1:
                target_existing = name_matched[0]
                race_code = str(target_existing["race_code"])
                race_name = str(target_existing["race_name"])
                server_code = str(target_existing["server_code"])
                server_name = str(target_existing["server_name"])
            else:
                race_server_view = ApplicationRaceServerView(user_id=interaction.user.id)
                await interaction.followup.send(
                    "이 서버에는 기본 종족/서버 설정이 없습니다.\n"
                    "수정할 신청에 해당하는 종족과 종족 서버를 선택하세요.",
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

        # 3) 수정 대상 신청건 조회 (본인 기준)
        existing = get_user_application(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            raid_name=레이드이름,
            race_code=race_code,
            server_code=server_code,
            character_name=캐릭터명,
        )

        if existing is None:
            await interaction.followup.send(
                f"`{레이드이름}` 레이드에 `{캐릭터명}` 신청 내역이 없습니다.",
                ephemeral=True,
            )
            return

        # 4) 아툴 재조회
        data = get_character_info(
            race_code=race_code,
            race_name=race_name,
            server_code=server_code,
            server_name=server_name,
            character_name=캐릭터명,
        )

        # 5) 입장 조건 재검사
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
                f"수정 불가: `{레이드이름}` 레이드의 입장 조건은 "
                f"`{condition_label} {condition_value}` 이상입니다.\n"
                f"현재 캐릭터 수치: `{current_value}`",
                ephemeral=True,
            )
            return

        # 6) 요일/특이사항 다시 입력
        initial_days = existing.get("available_days") or []
        initial_note = (existing.get("note") or "").strip()

        weekday_view = WeekdayMultiSelectView(
            user_id=interaction.user.id,
            initial_days=initial_days,
            initial_note=initial_note,
        )

        await interaction.followup.send(
            f"`{캐릭터명}` 신청 수정을 진행합니다.\n"
            f"현재 가능 요일: {format_days(initial_days)}\n"
            f"현재 특이사항: {initial_note or '-'}\n"
            "가능 요일과 특이사항을 다시 입력하세요.",
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

        # 7) DB 수정
        update_application(
            int(existing["id"]),
            {
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
            },
        )

        # 8) 공개 수정 완료 메시지
        embed = build_application_update_embed(
            raid_name=레이드이름,
            data=data,
            available_days=available_days,
            note=note,
            show_race_server=not used_default_setting,
        )
        await interaction.followup.send(embed=embed, ephemeral=False)

        await interaction.followup.send(
            "신청 수정이 저장되었습니다.",
            ephemeral=True,
        )

    except AtoolError as e:
        await interaction.followup.send(
            f"아툴 조회 실패: {e}",
            ephemeral=True,
        )
    except Exception as e:
        await interaction.followup.send(
            f"신청 수정 중 오류가 발생했습니다.\n`{e}`",
            ephemeral=True,
        )


# ========================================================
# /공대생성
# ========================================================

# 관리자만 사용 가능

@bot.tree.command(name="공대생성", description="레이드 공대를 자동 생성합니다.")
@app_commands.describe(
    레이드이름="공대를 생성할 레이드 이름",
    요일="공대 생성 대상 요일",
)
async def create_parties_command(
    interaction: discord.Interaction,
    레이드이름: str,
    요일: str,
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

    raid_name = 레이드이름.strip()
    weekday = 요일.strip()

    if not raid_name:
        await interaction.response.send_message(
            "레이드 이름이 비어 있습니다.",
            ephemeral=True,
        )
        return

    if weekday not in VALID_WEEKDAYS:
        await interaction.response.send_message(
            "요일은 월, 화, 수, 목, 금, 토, 일 중 하나여야 합니다.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True, thinking=True)

    try:
        # 1) 레이드 존재 확인
        raid = get_raid(interaction.guild.id, raid_name)
        if raid is None:
            await interaction.followup.send(
                f"`{raid_name}` 레이드는 존재하지 않습니다.",
                ephemeral=True,
            )
            return

        # 2) 해당 요일 신청자 조회
        applications = list_raid_applications_by_weekday(
            guild_id=interaction.guild.id,
            raid_name=raid_name,
            weekday=weekday,
        )

        if not applications:
            await interaction.followup.send(
                f"`{raid_name}` 레이드의 `{weekday}` 신청자가 없습니다.",
                ephemeral=True,
            )
            return

        # 3) 이미 생성된 공대 내역 조회
        existing_rows = list_raid_parties(
            guild_id=interaction.guild.id,
            raid_name=raid_name,
            weekday=weekday,
        )

        # 4) 이미 생성된 캐릭터 제외
        candidates = exclude_already_generated_characters(applications, existing_rows)

        if not candidates:
            await interaction.followup.send(
                f"`{raid_name}` 레이드의 `{weekday}` 신청자 중 "
                "새로 생성할 수 있는 캐릭터가 없습니다.\n"
                "이미 생성된 공대에 모두 포함되어 있을 수 있습니다.",
                ephemeral=True,
            )
            return

        # 5) 공대 생성 시점 기준 아툴 재조회
        refreshed_candidates, refresh_warnings = refresh_candidates_for_party_generation(candidates)

        # 6) 기존 규칙 불러오기
        initial_rules = load_party_rules(interaction.guild.id, raid_name)
        if not initial_rules:
            initial_rules = build_default_all_slot_rules()

        # 7) 규칙 UI
        rule_view = PartyRuleSetupView(
            user_id=interaction.user.id,
            initial_rules=initial_rules,
        )

        rule_message = "공대 생성 규칙을 설정하세요."
        if has_party_rules(interaction.guild.id, raid_name):
            rule_message += "\n기존 저장 규칙을 불러왔습니다."

        await interaction.followup.send(
            f"{rule_message}\n\n```text\n{rule_view.build_summary_text()}\n```",
            view=rule_view,
            ephemeral=True,
        )

        timeout = await rule_view.wait()
        if timeout:
            await interaction.followup.send(
                "공대 생성 규칙 입력 시간이 초과되었습니다.",
                ephemeral=True,
            )
            return

        if rule_view.value != "submit" or rule_view.exported_rules is None:
            return

        slot_rules = rule_view.exported_rules

        # 8) 규칙 저장
        save_party_rules(
            guild_id=interaction.guild.id,
            raid_name=raid_name,
            slots=slot_rules,
            updated_by=interaction.user.id,
        )

        # 9) 재조회된 값으로 공대 생성
        raids, waiting_members, warnings = build_balanced_raids(
            candidates=refreshed_candidates,
            slot_rules=slot_rules,
        )

        if not raids and not waiting_members:
            await interaction.followup.send(
                "공대 생성 결과가 비어 있습니다.",
                ephemeral=True,
            )
            return

        # 10) DB 저장용 row 변환
        rows = flatten_raids_to_party_rows(
            guild_id=interaction.guild.id,
            raid_name=raid_name,
            weekday=weekday,
            raids=raids,
            waiting_members=waiting_members,
        )

        # 11) 저장
        replace_raid_parties(
            guild_id=interaction.guild.id,
            raid_name=raid_name,
            weekday=weekday,
            members=rows,
        )

        # 12) 결과 출력
        source_note = "설정한 공대 규칙 기준 / 신청 DB 저장값 기준"
        embed = build_raid_result_embed(
            raid_name=raid_name,
            weekday=weekday,
            raids=raids,
            waiting_members=waiting_members,
            source_note=source_note,
        )

        text = format_raid_result_text(
            raid_name=raid_name,
            weekday=weekday,
            raids=raids,
            waiting_members=waiting_members,
            source_note=source_note,
        )

        await interaction.followup.send(embed=embed, ephemeral=False)
        await send_long_text_followup(interaction, text, ephemeral=False)

        all_warnings = []
        all_warnings.extend(refresh_warnings)
        all_warnings.extend(warnings)

        if all_warnings:
            warning_text = "\n".join(f"- {w}" for w in all_warnings[:30])
            await interaction.followup.send(
                f"생성 참고 사항\n```text\n{warning_text}\n```",
                ephemeral=True,
            )

    except Exception as e:
        await interaction.followup.send(
            f"공대 생성 중 오류가 발생했습니다.\n`{e}`",
            ephemeral=True,
        )


# ========================================================
# /공대확인
# ========================================================

# 요일이 없으면 레이드에 생성된 모든 공대가 표시됨
# 요일이 있으면 해당 요일의 레이드 공대가 표시됨
# 기본적으로 나만 보기, 관리자의 경우 공개 여부 설정 가능

@bot.tree.command(name="공대확인", description="생성된 공대 내역을 확인합니다.")
@app_commands.describe(
    레이드이름="확인할 레이드 이름",
    요일="확인할 요일 (선택)",
)
async def check_parties_command(
    interaction: discord.Interaction,
    레이드이름: str,
    요일: str | None = None,
):
    if interaction.guild is None:
        await interaction.response.send_message(
            "서버 안에서만 사용할 수 있는 명령어입니다.",
            ephemeral=True,
        )
        return

    레이드이름 = 레이드이름.strip()
    weekday = 요일.strip() if 요일 else None

    if not 레이드이름:
        await interaction.response.send_message(
            "레이드 이름이 비어 있습니다.",
            ephemeral=True,
        )
        return

    if weekday and weekday not in VALID_WEEKDAYS:
        await interaction.response.send_message(
            "요일은 월, 화, 수, 목, 금, 토, 일 중 하나여야 합니다.",
            ephemeral=True,
        )
        return

    try:
        if is_admin(interaction):
            view = PartyConfirmVisibilityView(user_id=interaction.user.id)
            await interaction.response.send_message(
                "공대 확인 결과를 공개할지 선택해주세요.",
                view=view,
                ephemeral=True,
            )

            timeout = await view.wait()
            if timeout:
                return

            if view.value == "cancel" or view.value is None:
                return

            result_ephemeral = (view.value != "public")
        else:
            await interaction.response.defer(ephemeral=True, thinking=True)
            result_ephemeral = True

        rows = list_raid_parties(
            guild_id=interaction.guild.id,
            raid_name=레이드이름,
            weekday=weekday,
        )

        if not rows:
            if weekday:
                await interaction.followup.send(
                    f"`{레이드이름}` 레이드의 `{weekday}` 공대 생성 내역이 없습니다.",
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    f"`{레이드이름}` 레이드의 공대 생성 내역이 없습니다.",
                    ephemeral=True,
                )
            return

        if weekday:
            raids, waiting_members = convert_rows_to_raid_structure(rows)

            embed = build_party_check_embed(
                raid_name=레이드이름,
                weekday=weekday,
                raids=raids,
                waiting_members=waiting_members,
            )
            text = format_party_check_text_for_weekday(
                raid_name=레이드이름,
                weekday=weekday,
                raids=raids,
                waiting_members=waiting_members,
            )

            await interaction.followup.send(embed=embed, ephemeral=result_ephemeral)
            await send_long_text_followup(
                interaction,
                text,
                ephemeral=result_ephemeral,
            )
            return

        # 요일 없이 전체 확인
        grouped = group_party_rows_by_weekday(rows)

        all_rows_count = len(rows)
        total_assigned = sum(1 for row in rows if str(row.get("status")) == "ASSIGNED")
        total_waiting = sum(1 for row in rows if str(row.get("status")) == "WAITING")

        summary_embed = discord.Embed(
            title=f"[{레이드이름}] 전체 요일 공대 확인",
            color=discord.Color.blurple(),
        )
        summary_embed.add_field(name="전체 저장 행 수", value=str(all_rows_count), inline=False)
        summary_embed.add_field(name="전체 배정 인원", value=str(total_assigned), inline=False)
        summary_embed.add_field(name="전체 대기 인원", value=str(total_waiting), inline=False)
        summary_embed.set_footer(text="※ 템렙/아툴 점수는 DB 저장 시점 기준입니다.")

        await interaction.followup.send(embed=summary_embed, ephemeral=result_ephemeral)

        for grouped_weekday in sorted(grouped.keys()):
            weekday_rows = grouped[grouped_weekday]
            raids, waiting_members = convert_rows_to_raid_structure(weekday_rows)

            embed = build_party_check_embed(
                raid_name=레이드이름,
                weekday=grouped_weekday,
                raids=raids,
                waiting_members=waiting_members,
            )
            text = format_party_check_text_for_weekday(
                raid_name=레이드이름,
                weekday=grouped_weekday,
                raids=raids,
                waiting_members=waiting_members,
            )

            await interaction.followup.send(embed=embed, ephemeral=result_ephemeral)
            await send_long_text_followup(
                interaction,
                text,
                ephemeral=result_ephemeral,
            )

    except Exception as e:
        if interaction.response.is_done():
            await interaction.followup.send(
                f"공대 확인 중 오류가 발생했습니다.\n`{e}`",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f"공대 확인 중 오류가 발생했습니다.\n`{e}`",
                ephemeral=True,
            )


# ========================================================
# /공대초기화
# ========================================================

# 관리자만 사용 가능
# 요일 없으면 해당 레이드의 모든 공대가 삭제
# 요일 있으면 해당 레이드의 해당 요일의 공대만 삭제

@bot.tree.command(name="공대초기화", description="생성된 공대 내역을 초기화합니다.")
@app_commands.describe(
    레이드이름="초기화할 레이드 이름",
    요일="초기화할 요일 (선택)",
)
async def reset_parties_command(
    interaction: discord.Interaction,
    레이드이름: str,
    요일: str | None = None,
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
    weekday = 요일.strip() if 요일 else None

    if not 레이드이름:
        await interaction.response.send_message(
            "레이드 이름이 비어 있습니다.",
            ephemeral=True,
        )
        return

    if weekday and weekday not in VALID_WEEKDAYS:
        await interaction.response.send_message(
            "요일은 월, 화, 수, 목, 금, 토, 일 중 하나여야 합니다.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True, thinking=True)

    try:
        raid = get_raid(interaction.guild.id, 레이드이름)
        if raid is None:
            await interaction.followup.send(
                f"`{레이드이름}` 레이드는 존재하지 않습니다.",
                ephemeral=True,
            )
            return

        deleted_count = clear_raid_parties(
            guild_id=interaction.guild.id,
            raid_name=레이드이름,
            weekday=weekday,
        )

        if weekday:
            if deleted_count == 0:
                await interaction.followup.send(
                    f"`{레이드이름}` 레이드의 `{weekday}` 공대 생성 내역이 없습니다.",
                    ephemeral=True,
                )
                return

            await interaction.followup.send(
                f"`{레이드이름}` 레이드의 `{weekday}` 공대 생성 내역이 초기화되었습니다.\n"
                f"- 삭제된 행 수: {deleted_count}\n"
                "- 신청 원본 내역은 유지됩니다.",
                ephemeral=True,
            )
            return

        if deleted_count == 0:
            await interaction.followup.send(
                f"`{레이드이름}` 레이드의 공대 생성 내역이 없습니다.",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            f"`{레이드이름}` 레이드의 전체 공대 생성 내역이 초기화되었습니다.\n"
            f"- 삭제된 행 수: {deleted_count}\n"
            "- 신청 원본 내역은 유지됩니다.",
            ephemeral=True,
        )

    except Exception as e:
        await interaction.followup.send(
            f"공대초기화 중 오류가 발생했습니다.\n`{e}`",
            ephemeral=True,
        )


# ========================================================
# /공대수정
# ========================================================

# 관리자만 사용 가능

@bot.tree.command(name="공대수정", description="생성된 공대 내역에서 캐릭터를 이동합니다.")
@app_commands.describe(
    레이드이름="수정할 레이드 이름",
    요일="수정할 요일",
    캐릭터명="이동할 캐릭터명",
    공대="이동할 공대 번호",
    파티="이동할 파티 번호 (1 또는 2)",
)
async def update_party_member_command(
    interaction: discord.Interaction,
    레이드이름: str,
    요일: str,
    캐릭터명: str,
    공대: int,
    파티: int,
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

    raid_name = 레이드이름.strip()
    weekday = 요일.strip()
    character_name = 캐릭터명.strip()

    if not raid_name:
        await interaction.response.send_message(
            "레이드 이름이 비어 있습니다.",
            ephemeral=True,
        )
        return

    if weekday not in VALID_WEEKDAYS:
        await interaction.response.send_message(
            "요일은 월, 화, 수, 목, 금, 토, 일 중 하나여야 합니다.",
            ephemeral=True,
        )
        return

    if not character_name:
        await interaction.response.send_message(
            "캐릭터명이 비어 있습니다.",
            ephemeral=True,
        )
        return

    if 공대 < 1:
        await interaction.response.send_message(
            "공대 번호는 1 이상이어야 합니다.",
            ephemeral=True,
        )
        return

    if 파티 not in (1, 2):
        await interaction.response.send_message(
            "파티 번호는 1 또는 2만 가능합니다.",
            ephemeral=True,
        )
        return

    await interaction.response.defer(ephemeral=True, thinking=True)

    try:
        raid = get_raid(interaction.guild.id, raid_name)
        if raid is None:
            await interaction.followup.send(
                f"`{raid_name}` 레이드는 존재하지 않습니다.",
                ephemeral=True,
            )
            return

        rows = list_raid_parties(
            guild_id=interaction.guild.id,
            raid_name=raid_name,
            weekday=weekday,
        )

        if not rows:
            await interaction.followup.send(
                f"`{raid_name}` 레이드의 `{weekday}` 공대 생성 내역이 없습니다.",
                ephemeral=True,
            )
            return

        # 1) 이동 대상 캐릭터 찾기
        guild_setting = get_guild_setting(interaction.guild.id)
        moving_member = None

        if guild_setting is not None:
            moving_member = find_matching_generated_member(
                rows=rows,
                race_code=str(guild_setting["race_code"]),
                server_code=str(guild_setting["server_code"]),
                character_name=character_name,
            )
        else:
            matched = find_matching_generated_members(rows, character_name)

            if not matched:
                await interaction.followup.send(
                    f"`{raid_name}` 레이드의 `{weekday}` 공대에서 `{character_name}` 캐릭터를 찾을 수 없습니다.",
                    ephemeral=True,
                )
                return

            if len(matched) == 1:
                moving_member = matched[0]
            else:
                race_server_view = ApplicationRaceServerView(user_id=interaction.user.id)
                await interaction.followup.send(
                    f"`{character_name}` 이름의 캐릭터가 여러 종족/서버에 있습니다.\n"
                    "이동할 캐릭터의 종족/서버를 선택하세요.",
                    view=race_server_view,
                    ephemeral=True,
                )

                timeout = await race_server_view.wait()
                if timeout:
                    await interaction.followup.send(
                        "종족/서버 선택 시간이 초과되었습니다.",
                        ephemeral=True,
                    )
                    return

                if race_server_view.value != "submit":
                    return

                moving_member = find_matching_generated_member(
                    rows=rows,
                    race_code=str(race_server_view.selected_race_code),
                    server_code=str(race_server_view.selected_server_code),
                    character_name=character_name,
                )

        if moving_member is None:
            await interaction.followup.send(
                f"`{raid_name}` 레이드의 `{weekday}` 공대에서 `{character_name}` 캐릭터를 찾을 수 없습니다.",
                ephemeral=True,
            )
            return

        # 2) 이동 가능성 검사
        can_move, reason = can_move_member_to_target(
            rows=rows,
            moving_member=moving_member,
            target_raid_no=공대,
            target_party_no=파티,
        )

        if not can_move:
            await interaction.followup.send(
                f"공대 이동 불가: {reason}",
                ephemeral=True,
            )
            return

                # 목표 파티 빈 슬롯 찾기
        empty_slot = find_first_empty_slot(
            rows=rows,
            target_raid_no=공대,
            target_party_no=파티,
        )

        replaced_member = None
        replace_mode = None
        target_slot_no = None

        source_weekday = str(moving_member["weekday"])
        source_raid_no = int(moving_member["raid_no"])
        source_party_no = moving_member.get("party_no")
        source_slot_no = moving_member.get("slot_no")
        source_status = str(moving_member["status"])

        # 1) 빈 슬롯 있으면 바로 이동
        if empty_slot is not None:
            target_slot_no = empty_slot

            update_party_member_position(
                party_row_id=int(moving_member["id"]),
                weekday=weekday,
                raid_no=공대,
                party_no=파티,
                slot_no=target_slot_no,
                status="ASSIGNED",
            )

        # 2) 파티가 가득 차면 처리 방식 선택
        else:
            mode_view = PartyReplaceModeView(user_id=interaction.user.id)
            await interaction.followup.send(
                "대상 파티가 가득 찼습니다. 처리 방식을 선택하세요.",
                view=mode_view,
                ephemeral=True,
            )

            timeout = await mode_view.wait()
            if timeout:
                await interaction.followup.send(
                    "처리 방식 선택 시간이 초과되었습니다.",
                    ephemeral=True,
                )
                return

            if mode_view.value in (None, "cancel"):
                return

            replace_mode = mode_view.value

            party_members = list_members_in_party(
                rows=rows,
                raid_no=공대,
                party_no=파티,
            )

            replace_view = PartyReplaceView(
                user_id=interaction.user.id,
                members=party_members,
            )

            if replace_mode == "swap":
                await interaction.followup.send(
                    "교체할 캐릭터를 선택하세요.",
                    view=replace_view,
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    "대기 인원으로 이동시킬 캐릭터를 선택하세요.",
                    view=replace_view,
                    ephemeral=True,
                )

            timeout = await replace_view.wait()
            if timeout:
                await interaction.followup.send(
                    "대상 캐릭터 선택 시간이 초과되었습니다.",
                    ephemeral=True,
                )
                return

            if replace_view.value != "submit" or replace_view.selected_member_id is None:
                return

            selected_id = int(replace_view.selected_member_id)
            for m in party_members:
                if int(m["id"]) == selected_id:
                    replaced_member = m
                    break

            if replaced_member is None:
                await interaction.followup.send(
                    "선택한 교체 대상을 찾을 수 없습니다.",
                    ephemeral=True,
                )
                return

            target_slot_no = int(replaced_member["slot_no"])

            # 2-1) swap
            if replace_mode == "swap":
                swap_party_members_position(
                    first_row_id=int(moving_member["id"]),
                    first_weekday=source_weekday,
                    first_raid_no=source_raid_no,
                    first_party_no=source_party_no,
                    first_slot_no=source_slot_no,
                    first_status=source_status,
                    second_row_id=int(replaced_member["id"]),
                    second_weekday=weekday,
                    second_raid_no=공대,
                    second_party_no=파티,
                    second_slot_no=target_slot_no,
                    second_status="ASSIGNED",
                )

            # 2-2) 대기 이동
            elif replace_mode == "waiting":
                update_party_member_position(
                    party_row_id=int(replaced_member["id"]),
                    weekday=weekday,
                    raid_no=공대,
                    party_no=None,
                    slot_no=None,
                    status="WAITING",
                )

                update_party_member_position(
                    party_row_id=int(moving_member["id"]),
                    weekday=weekday,
                    raid_no=공대,
                    party_no=파티,
                    slot_no=target_slot_no,
                    status="ASSIGNED",
                )

        # 4) DB 갱신
        if replaced_member is not None:
            move_party_member_to_waiting(
                party_row_id=int(replaced_member["id"]),
                raid_no=공대,
            )

        move_party_member_to_slot(
            party_row_id=int(moving_member["id"]),
            raid_no=공대,
            party_no=파티,
            slot_no=target_slot_no,
        )

        # 5) 결과 표시
        embed = build_party_update_embed(
            raid_name=raid_name,
            source_weekday=source_weekday,
            moved_member=moving_member,
            target_weekday=weekday,
            target_raid_no=공대 if replace_mode != "waiting" or target_slot_no is not None else None,
            target_party_no=파티 if target_slot_no is not None else None,
            target_slot_no=target_slot_no,
            replaced_member=replaced_member,
            replace_mode=replace_mode,
        )

        await interaction.followup.send(embed=embed, ephemeral=False)
        await interaction.followup.send(
            "공대 수정이 저장되었습니다.",
            ephemeral=True,
        )

    except Exception as e:
        await interaction.followup.send(
            f"공대수정 중 오류가 발생했습니다.\n`{e}`",
            ephemeral=True,
        )


# =========================================================
# //공대 규칙 UI 테스트
# =========================================================

@bot.tree.command(name="공대규칙테스트", description="공대 규칙 UI 테스트")
async def test_party_rules(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message("서버 안에서만 가능합니다.", ephemeral=True)
        return

    if not is_admin(interaction):
        await interaction.response.send_message("관리자만 가능합니다.", ephemeral=True)
        return

    view = PartyRuleSetupView(user_id=interaction.user.id)
    await interaction.response.send_message(
        view.build_summary_text(),
        view=view,
        ephemeral=True,
    )

    timeout = await view.wait()
    if timeout:
        return

    if view.value == "submit" and view.exported_rules is not None:
        await interaction.followup.send(
            f"규칙 저장 완료\n```python\n{view.exported_rules}\n```",
            ephemeral=True,
        )

@bot.event
async def on_ready():
    init_db()
    await bot.tree.sync()
    print(f"{bot.user} 로그인 완료")


bot.run("DISCORD_TOKEN")
