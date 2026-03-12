from __future__ import annotations

import os

import discord
from discord import app_commands
from discord.ext import commands

from app_helpers import format_days, is_admin
from application_views import (
    ApplicationCancelView,
    ApplicationRaceServerView,
    ForceDeleteRaceServerView,
    WeekdayMultiSelectView,
    make_character_key,
)
from atool import AtoolError, get_character_info
from constants import RACE_OPTIONS, SERVER_OPTIONS, VALID_WEEKDAYS
from party_helpers import (
    can_move_member_to_target,
    convert_rows_to_raid_structure,
    find_first_empty_slot,
    find_matching_generated_member,
    find_matching_generated_members,
    group_party_rows_by_weekday,
    list_members_in_party,
    raid_has_same_user_after_swap,
    split_members_already_assigned_other_weekday,
    build_default_all_slot_rules,
    refresh_candidates_for_party_generation_optimized,
)
from party_views import (
    PartyConfirmVisibilityView,
    PartyReplaceModeView,
    PartyReplaceView,
    PartyRuleSetupView,
)
from raid_logic import build_balanced_raids, exclude_already_generated_characters, flatten_raids_to_party_rows
from settings_views import GuildSettingView, RaidDeleteConfirmView
from storage import (
    clear_raid_parties,
    count_raid_applications,
    create_application,
    create_raid,
    delete_application,
    delete_guild_setting,
    delete_raid,
    delete_raid_applications,
    get_application_by_character,
    get_guild_setting,
    get_raid,
    get_user_application,
    has_party_rules,
    init_db,
    list_applications_by_character_name,
    list_raid_applications_by_weekday,
    list_raid_parties,
    list_raids,
    list_user_applications,
    load_party_rules,
    raid_exists,
    replace_raid_parties,
    save_party_rules,
    swap_party_members_position,
    update_application,
    update_party_member_position,
)
from ui_helpers import (
    build_application_update_embed,
    build_cancel_result_text,
    build_force_delete_result_text,
    build_party_check_embed,
    build_party_update_embed,
    build_raid_application_embed,
    build_raid_result_embed,
    format_party_check_text_for_weekday,
    format_raid_result_text,
    group_applications_by_raid,
    send_long_text_followup,
    format_waiting_only_text,
)

RACE_CHOICES = [app_commands.Choice(name=item["name"], value=item["code"]) for item in RACE_OPTIONS]
SERVER_CHOICES = [app_commands.Choice(name=item["name"], value=item["code"]) for item in SERVER_OPTIONS]
CONDITION_TYPE_CHOICES = [
    app_commands.Choice(name="템렙", value="item_level"),
    app_commands.Choice(name="아툴 점수", value="combat_score"),
]
VIEW_OPTION_CHOICES = [
    app_commands.Choice(name="전체", value="전체"),
    app_commands.Choice(name="요일", value="요일"),
    app_commands.Choice(name="대기", value="대기"),
]


def find_generated_rows_for_target(generated_rows: list[dict], target: dict) -> list[dict]:
    key = make_character_key(target)
    return [row for row in generated_rows if make_character_key(row) == key]





intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.tree.command(name="설정", description="이 디스코드 서버의 기본 아이온2 종족/서버를 설정합니다.")
async def set_default_aion2(interaction: discord.Interaction):
    if interaction.guild is None or not is_admin(interaction):
        await interaction.response.send_message("관리자만 서버 안에서 사용할 수 있습니다.", ephemeral=True)
        return
    await interaction.response.send_message(
        "아이온2 기본 설정을 진행합니다.\n먼저 종족을 선택하세요.",
        view=GuildSettingView(interaction.guild.id, interaction.user.id),
        ephemeral=True,
    )


@bot.tree.command(name="설정확인", description="이 디스코드 서버의 현재 기본 설정을 확인합니다.")
async def check_default_aion2(interaction: discord.Interaction):
    if interaction.guild is None or not is_admin(interaction):
        await interaction.response.send_message("관리자만 서버 안에서 사용할 수 있습니다.", ephemeral=True)
        return
    setting = get_guild_setting(interaction.guild.id)
    if setting is None:
        await interaction.response.send_message("이 서버에는 저장된 기본 설정이 없습니다.", ephemeral=True)
        return
    embed = discord.Embed(title="현재 서버 기본 설정", color=discord.Color.blue())
    embed.add_field(name="종족", value=setting["race_name"], inline=True)
    embed.add_field(name="종족서버", value=setting["server_name"], inline=True)
    embed.add_field(name="수정자 ID", value=str(setting["updated_by"]), inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="설정삭제", description="이 디스코드 서버의 기본 설정을 삭제합니다.")
async def delete_default_aion2(interaction: discord.Interaction):
    if interaction.guild is None or not is_admin(interaction):
        await interaction.response.send_message("관리자만 서버 안에서 사용할 수 있습니다.", ephemeral=True)
        return
    deleted = delete_guild_setting(interaction.guild.id)
    if deleted == 0:
        await interaction.response.send_message("삭제할 기본 설정이 없습니다.", ephemeral=True)
        return
    await interaction.response.send_message("이 서버의 기본 설정이 삭제되었습니다.", ephemeral=True)


@bot.tree.command(name="레이드생성", description="이 서버에 레이드를 생성합니다.")
@app_commands.choices(입장조건종류=CONDITION_TYPE_CHOICES)
async def create_raid_command(interaction: discord.Interaction, 레이드이름: str, 입장조건종류: app_commands.Choice[str], 입장조건값: int):
    if interaction.guild is None or not is_admin(interaction):
        await interaction.response.send_message("관리자만 서버 안에서 사용할 수 있습니다.", ephemeral=True)
        return
    if raid_exists(interaction.guild.id, 레이드이름):
        await interaction.response.send_message(f"이 서버에는 이미 `{레이드이름}` 레이드가 존재합니다.", ephemeral=True)
        return
    create_raid(interaction.guild.id, 레이드이름.strip(), 입장조건종류.value, 입장조건값, interaction.user.id)
    await interaction.response.send_message(f"`{레이드이름}` 레이드가 생성되었습니다.", ephemeral=True)


@bot.tree.command(name="레이드확인", description="이 서버에 저장된 레이드 목록을 확인합니다.")
async def list_raids_command(interaction: discord.Interaction):
    if interaction.guild is None or not is_admin(interaction):
        await interaction.response.send_message("관리자만 서버 안에서 사용할 수 있습니다.", ephemeral=True)
        return
    raids = list_raids(interaction.guild.id)
    if not raids:
        await interaction.response.send_message("이 서버에는 생성된 레이드가 없습니다.", ephemeral=True)
        return
    embed = discord.Embed(title="현재 서버 레이드 목록", color=discord.Color.blue())
    for raid in raids:
        label = "템렙" if raid["condition_type"] == "item_level" else "아툴 점수"
        applicant_count = count_raid_applications(interaction.guild.id, raid["raid_name"])
        embed.add_field(name=raid["raid_name"], value=f"입장 조건: {label} {raid['condition_value']}\n신청자 수: {applicant_count}명", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="레이드삭제", description="이 서버의 레이드를 삭제합니다.")
async def delete_raid_command(interaction: discord.Interaction, 레이드이름: str):
    if interaction.guild is None or not is_admin(interaction):
        await interaction.response.send_message("관리자만 서버 안에서 사용할 수 있습니다.", ephemeral=True)
        return
    if get_raid(interaction.guild.id, 레이드이름) is None:
        await interaction.response.send_message(f"`{레이드이름}` 레이드는 존재하지 않습니다.", ephemeral=True)
        return
    applicant_count = count_raid_applications(interaction.guild.id, 레이드이름)
    if applicant_count == 0:
        delete_raid(interaction.guild.id, 레이드이름)
        await interaction.response.send_message(f"`{레이드이름}` 레이드가 삭제되었습니다.", ephemeral=True)
        return
    view = RaidDeleteConfirmView(interaction.guild.id, 레이드이름, interaction.user.id)
    await interaction.response.send_message("신청 내역과 공대 내역까지 같이 삭제하시겠습니까?", view=view, ephemeral=True)
    timeout = await view.wait()
    if timeout or view.value != "delete_with_applications":
        return
    delete_raid_applications(interaction.guild.id, 레이드이름)
    clear_raid_parties(interaction.guild.id, 레이드이름)
    delete_raid(interaction.guild.id, 레이드이름)
    await interaction.followup.send(f"`{레이드이름}` 레이드가 전체 삭제되었습니다.", ephemeral=True)


@bot.tree.command(name="아툴", description="아이온2 캐릭터 아툴 정보를 조회합니다.")
@app_commands.choices(종족=RACE_CHOICES, 종족서버=SERVER_CHOICES)
async def search_atool(interaction: discord.Interaction, 캐릭터명: str, 종족: app_commands.Choice[str] | None = None, 종족서버: app_commands.Choice[str] | None = None):
    if interaction.guild is None:
        await interaction.response.send_message("서버 안에서만 사용할 수 있습니다.", ephemeral=True)
        return
    if (종족 is None) != (종족서버 is None):
        await interaction.response.send_message("종족과 종족서버는 둘 다 입력하거나 둘 다 비워야 합니다.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    try:
        if 종족 and 종족서버:
            race_code, race_name = 종족.value, 종족.name
            server_code, server_name = 종족서버.value, 종족서버.name
        else:
            setting = get_guild_setting(interaction.guild.id)
            if setting is None:
                await interaction.followup.send("기본 설정이 없어서 조회할 수 없습니다. `/설정`을 먼저 사용하세요.", ephemeral=True)
                return
            race_code, race_name = setting["race_code"], setting["race_name"]
            server_code, server_name = setting["server_code"], setting["server_name"]
        data = get_character_info(race_code, race_name, server_code, server_name, 캐릭터명.strip())
        embed = discord.Embed(title=f"{data['nickname']} 아툴 조회", color=discord.Color.blue())
        embed.add_field(name="종족", value=data["race_name"], inline=False)
        embed.add_field(name="종족서버", value=data["server_name"], inline=False)
        embed.add_field(name="직업", value=data["job_name"], inline=False)
        embed.add_field(name="템렙", value=str(data["item_level"]), inline=False)
        embed.add_field(name="아툴 점수", value=str(data["combat_score"]), inline=False)
        embed.add_field(name="최고 아툴 점수", value=str(data["peak_combat_score"]), inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"아툴 조회 실패: {e}", ephemeral=True)


@bot.tree.command(name="신청", description="레이드 신청")
async def apply_raid(interaction: discord.Interaction, 레이드이름: str, 캐릭터명: str):
    if interaction.guild is None:
        await interaction.response.send_message("서버 안에서만 사용할 수 있습니다.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    raid = get_raid(interaction.guild.id, 레이드이름.strip())
    if raid is None:
        await interaction.followup.send(f"`{레이드이름}` 레이드는 존재하지 않습니다.", ephemeral=True)
        return
    guild_setting = get_guild_setting(interaction.guild.id)
    used_default_setting = guild_setting is not None
    if guild_setting is None:
        race_server_view = ApplicationRaceServerView(interaction.user.id)
        await interaction.followup.send("신청에 사용할 종족과 종족 서버를 선택하세요.", view=race_server_view, ephemeral=True)
        timeout = await race_server_view.wait()
        if timeout or race_server_view.value != "submit":
            return
        race_code, race_name = race_server_view.selected_race_code, race_server_view.selected_race_name
        server_code, server_name = race_server_view.selected_server_code, race_server_view.selected_server_name
    else:
        race_code, race_name = guild_setting["race_code"], guild_setting["race_name"]
        server_code, server_name = guild_setting["server_code"], guild_setting["server_name"]
    existing = get_application_by_character(interaction.guild.id, 레이드이름, race_code, server_code, 캐릭터명)
    if existing is not None:
        await interaction.followup.send("이미 신청된 캐릭터입니다.", ephemeral=True)
        return
    data = get_character_info(race_code, race_name, server_code, server_name, 캐릭터명)
    current_value = data["item_level"] if raid["condition_type"] == "item_level" else data["combat_score"]
    if current_value < int(raid["condition_value"]):
        await interaction.followup.send("입장 조건을 만족하지 않습니다.", ephemeral=True)
        return
    weekday_view = WeekdayMultiSelectView(interaction.user.id)
    await interaction.followup.send(f"`{캐릭터명}` 신청을 진행합니다. 가능 요일을 선택하세요.", view=weekday_view, ephemeral=True)
    timeout = await weekday_view.wait()
    if timeout or weekday_view.value != "submit":
        return
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
            "available_days": weekday_view.selected_days,
            "note": weekday_view.note,
        }
    )
    embed = discord.Embed(title=f"[{레이드이름}] 신청 완료", color=discord.Color.green())
    embed.add_field(name="캐릭터명", value=data["nickname"], inline=False)
    if not used_default_setting:
        embed.add_field(name="종족/종족서버", value=f"{race_name} / {server_name}", inline=False)
    embed.add_field(name="직업", value=data["job_name"], inline=False)
    embed.add_field(name="템렙", value=str(data["item_level"]), inline=False)
    embed.add_field(name="아툴 점수", value=str(data["combat_score"]), inline=False)
    embed.add_field(name="가능 요일", value=format_days(weekday_view.selected_days), inline=False)
    if weekday_view.note:
        embed.add_field(name="특이사항", value=weekday_view.note, inline=False)
    await interaction.followup.send(embed=embed, ephemeral=False)
    await interaction.followup.send("신청이 저장되었습니다.", ephemeral=True)


@bot.tree.command(name="신청확인", description="내 레이드 신청 내역을 확인합니다.")
async def check_my_applications(interaction: discord.Interaction, 레이드이름: str | None = None):
    if interaction.guild is None:
        await interaction.response.send_message("서버 안에서만 사용할 수 있습니다.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    apps = list_user_applications(interaction.guild.id, interaction.user.id, 레이드이름.strip() if 레이드이름 else None)
    if not apps:
        await interaction.followup.send("신청 내역이 없습니다.", ephemeral=True)
        return
    grouped = group_applications_by_raid(apps)
    for raid_name, items in grouped.items():
        await interaction.followup.send(embed=build_raid_application_embed(raid_name, items), ephemeral=True)


@bot.tree.command(name="신청취소", description="내 레이드 신청을 취소합니다.")
async def cancel_application_command(interaction: discord.Interaction, 레이드이름: str, 캐릭터명: str):
    if interaction.guild is None:
        await interaction.response.send_message("서버 안에서만 사용할 수 있습니다.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    applications = list_user_applications(interaction.guild.id, interaction.user.id, 레이드이름)
    matched = [app for app in applications if str(app["character_name"]).strip() == 캐릭터명.strip()]
    if not matched:
        await interaction.followup.send("취소할 신청 내역이 없습니다.", ephemeral=True)
        return
    target = matched[0]
    if len(matched) > 1:
        view = ApplicationCancelView(interaction.user.id, matched)
        await interaction.followup.send("취소할 신청 내역을 선택하세요.", view=view, ephemeral=True)
        timeout = await view.wait()
        if timeout or view.value != "submit" or view.selected_application is None:
            return
        target = view.selected_application
    generated_rows = list_raid_parties(interaction.guild.id, 레이드이름, None)
    if find_generated_rows_for_target(generated_rows, target):
        await interaction.followup.send("이미 공대 생성에 반영된 신청 내역이라 바로 취소할 수 없습니다.", ephemeral=True)
        return
    delete_application(int(target["id"]))
    await interaction.followup.send(build_cancel_result_text(target), ephemeral=True)


@bot.tree.command(name="강제삭제", description="관리자가 레이드 신청 내역을 강제로 삭제합니다.")
async def force_delete_application_command(interaction: discord.Interaction, 레이드이름: str, 캐릭터명: str):
    if interaction.guild is None or not is_admin(interaction):
        await interaction.response.send_message("관리자만 서버 안에서 사용할 수 있습니다.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    matched = list_applications_by_character_name(interaction.guild.id, 레이드이름, 캐릭터명)
    if not matched:
        await interaction.followup.send("삭제할 신청 내역이 없습니다.", ephemeral=True)
        return
    target = matched[0]
    if len(matched) > 1:
        view = ForceDeleteRaceServerView(interaction.user.id, matched)
        await interaction.followup.send("삭제할 종족/서버를 선택하세요.", view=view, ephemeral=True)
        timeout = await view.wait()
        if timeout or view.value != "submit" or view.selected_application is None:
            return
        target = view.selected_application
    generated_rows = list_raid_parties(interaction.guild.id, 레이드이름, None)
    if find_generated_rows_for_target(generated_rows, target):
        await interaction.followup.send("이미 공대 생성에 반영된 신청 내역이라 강제삭제할 수 없습니다.", ephemeral=True)
        return
    delete_application(int(target["id"]))
    await interaction.followup.send(build_force_delete_result_text(target), ephemeral=True)


@bot.tree.command(name="신청수정", description="내 레이드 신청 내역을 수정합니다.")
async def update_application_command(interaction: discord.Interaction, 레이드이름: str, 캐릭터명: str):
    if interaction.guild is None:
        await interaction.response.send_message("서버 안에서만 사용할 수 있습니다.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    guild_setting = get_guild_setting(interaction.guild.id)
    used_default_setting = guild_setting is not None
    if guild_setting:
        race_code, race_name = guild_setting["race_code"], guild_setting["race_name"]
        server_code, server_name = guild_setting["server_code"], guild_setting["server_name"]
    else:
        my_apps = list_user_applications(interaction.guild.id, interaction.user.id, 레이드이름)
        name_matched = [app for app in my_apps if str(app["character_name"]).strip() == 캐릭터명.strip()]
        if not name_matched:
            await interaction.followup.send("수정할 신청 내역이 없습니다.", ephemeral=True)
            return
        if len(name_matched) == 1:
            target_existing = name_matched[0]
            race_code, race_name = target_existing["race_code"], target_existing["race_name"]
            server_code, server_name = target_existing["server_code"], target_existing["server_name"]
        else:
            view = ApplicationRaceServerView(interaction.user.id)
            await interaction.followup.send("수정할 신청의 종족/서버를 선택하세요.", view=view, ephemeral=True)
            timeout = await view.wait()
            if timeout or view.value != "submit":
                return
            race_code, race_name = view.selected_race_code, view.selected_race_name
            server_code, server_name = view.selected_server_code, view.selected_server_name
    existing = get_user_application(interaction.guild.id, interaction.user.id, 레이드이름, race_code, server_code, 캐릭터명)
    if existing is None:
        await interaction.followup.send("수정할 신청 내역이 없습니다.", ephemeral=True)
        return
    generated_rows = list_raid_parties(interaction.guild.id, 레이드이름, None)
    already_generated = bool(find_generated_rows_for_target(generated_rows, existing))
    data = get_character_info(race_code, race_name, server_code, server_name, 캐릭터명)
    view = WeekdayMultiSelectView(interaction.user.id, existing.get("available_days") or [], existing.get("note") or "")
    await interaction.followup.send("가능 요일과 특이사항을 다시 입력하세요.", view=view, ephemeral=True)
    timeout = await view.wait()
    if timeout or view.value != "submit":
        return
    update_application(int(existing["id"]), {
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
        "available_days": view.selected_days,
        "note": view.note,
    })
    await interaction.followup.send(embed=build_application_update_embed(레이드이름, data, view.selected_days, view.note, not used_default_setting), ephemeral=False)
    msg = "신청 수정이 저장되었습니다."
    if already_generated:
        msg += "\n※ 이미 생성된 공대에는 이번 주 자동 반영되지 않습니다."
    await interaction.followup.send(msg, ephemeral=True)


@bot.tree.command(name="공대생성", description="레이드 공대를 자동 생성합니다.")
async def create_parties_command(interaction: discord.Interaction, 레이드이름: str, 요일: str):
    if interaction.guild is None or not is_admin(interaction):
        await interaction.response.send_message("관리자만 서버 안에서 사용할 수 있습니다.", ephemeral=True)
        return
    raid_name = 레이드이름.strip()
    weekday = 요일.strip()
    if weekday not in VALID_WEEKDAYS:
        await interaction.response.send_message("요일은 월~일 중 하나여야 합니다.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    if get_raid(interaction.guild.id, raid_name) is None:
        await interaction.followup.send("레이드가 존재하지 않습니다.", ephemeral=True)
        return
    applications = list_raid_applications_by_weekday(interaction.guild.id, raid_name, weekday)
    if not applications:
        await interaction.followup.send("해당 요일 신청자가 없습니다.", ephemeral=True)
        return
    all_party_rows = list_raid_parties(interaction.guild.id, raid_name, None)
    existing_same_weekday_rows = [row for row in all_party_rows if str(row.get("weekday", "")).strip() == weekday]
    candidates = exclude_already_generated_characters(applications, existing_same_weekday_rows)
    other_weekday_assigned_rows = [
        row for row in all_party_rows
        if str(row.get("weekday", "")).strip() != weekday and str(row.get("status", "")).strip() == "ASSIGNED"
    ]
    candidates, cross_weekday_members = split_members_already_assigned_other_weekday(candidates, other_weekday_assigned_rows)
    if not candidates and not cross_weekday_members:
        await interaction.followup.send("새로 생성할 대상이 없습니다.", ephemeral=True)
        return
    refreshed_candidates, refresh_warnings = refresh_candidates_for_party_generation_optimized(candidates)
    initial_rules = load_party_rules(interaction.guild.id, raid_name) or build_default_all_slot_rules()
    rule_view = PartyRuleSetupView(interaction.user.id, initial_rules)
    await interaction.followup.send(f"```text\n{rule_view.build_summary_text()}\n```", view=rule_view, ephemeral=True)
    timeout = await rule_view.wait()
    if timeout or rule_view.value != "submit" or rule_view.exported_rules is None:
        return
    save_party_rules(interaction.guild.id, raid_name, rule_view.exported_rules, interaction.user.id)
    raids, waiting_members, warnings = build_balanced_raids(refreshed_candidates, rule_view.exported_rules)
    rows = flatten_raids_to_party_rows(interaction.guild.id, raid_name, weekday, raids, waiting_members)
    replace_raid_parties(interaction.guild.id, raid_name, weekday, rows)
    source_note = "설정한 공대 규칙 기준 / 공대 생성 시점 기준"
    embed = build_raid_result_embed(raid_name, weekday, raids, waiting_members, cross_weekday_members, source_note)
    text = format_raid_result_text(raid_name, weekday, raids, waiting_members, cross_weekday_members, source_note)
    await interaction.followup.send(embed=embed, ephemeral=False)
    await send_long_text_followup(interaction, text, ephemeral=False)
    all_warnings = refresh_warnings + warnings
    if all_warnings:
        await interaction.followup.send("```text\n" + "\n".join(all_warnings[:30]) + "\n```", ephemeral=True)


@bot.tree.command(name="공대확인", description="생성된 공대 내역을 확인합니다.")
@app_commands.choices(보기옵션=VIEW_OPTION_CHOICES)
async def check_parties_command(interaction: discord.Interaction, 레이드이름: str, 보기옵션: app_commands.Choice[str], 요일: str | None = None):
    if interaction.guild is None:
        await interaction.response.send_message("서버 안에서만 사용할 수 있습니다.", ephemeral=True)
        return
    raid_name = 레이드이름.strip()
    view_option = 보기옵션.value
    weekday = 요일.strip() if 요일 else None
    if view_option in ("요일", "대기") and weekday not in VALID_WEEKDAYS:
        await interaction.response.send_message("요일을 올바르게 입력하세요.", ephemeral=True)
        return
    result_ephemeral = True
    if is_admin(interaction):
        view = PartyConfirmVisibilityView(interaction.user.id)
        await interaction.response.send_message("공개 여부를 선택하세요.", view=view, ephemeral=True)
        timeout = await view.wait()
        if timeout or view.value in (None, "cancel"):
            return
        result_ephemeral = view.value != "public"
    else:
        await interaction.response.defer(ephemeral=True)
    all_party_rows = list_raid_parties(interaction.guild.id, raid_name, None)
    if view_option == "전체":
        if not all_party_rows:
            await interaction.followup.send("공대 생성 내역이 없습니다.", ephemeral=True)
            return
        grouped = group_party_rows_by_weekday(all_party_rows)
        for grouped_weekday in sorted(grouped.keys()):
            raids, waiting_members = convert_rows_to_raid_structure(grouped[grouped_weekday])
            await interaction.followup.send(embed=build_party_check_embed(raid_name, grouped_weekday, raids, waiting_members), ephemeral=result_ephemeral)
            await send_long_text_followup(interaction, format_party_check_text_for_weekday(raid_name, grouped_weekday, raids, waiting_members), ephemeral=result_ephemeral)
        return
    if view_option == "요일":
        weekday_rows = [row for row in all_party_rows if str(row.get("weekday", "")).strip() == weekday]
        raids, waiting_members = convert_rows_to_raid_structure(weekday_rows)
        await interaction.followup.send(embed=build_party_check_embed(raid_name, weekday, raids, waiting_members), ephemeral=result_ephemeral)
        await send_long_text_followup(interaction, format_party_check_text_for_weekday(raid_name, weekday, raids, waiting_members), ephemeral=result_ephemeral)
        return
    weekday_applications = list_raid_applications_by_weekday(interaction.guild.id, raid_name, weekday)
    other_weekday_assigned_rows = [row for row in all_party_rows if str(row.get("weekday", "")).strip() != weekday and str(row.get("status", "")).strip() == "ASSIGNED"]
    waiting_candidates, assigned_other_weekday_candidates = split_members_already_assigned_other_weekday(weekday_applications, other_weekday_assigned_rows)
    embed = discord.Embed(title=f"[{raid_name}] {weekday} 대기 확인", color=discord.Color.orange())
    embed.add_field(name="대기 인원", value=str(len(waiting_candidates)), inline=False)
    embed.add_field(name="타 요일 배정 인원", value=str(len(assigned_other_weekday_candidates)), inline=False)
    await interaction.followup.send(embed=embed, ephemeral=result_ephemeral)
    await send_long_text_followup(interaction, format_waiting_only_text(raid_name, weekday, waiting_candidates, assigned_other_weekday_candidates), ephemeral=result_ephemeral)


@bot.tree.command(name="공대초기화", description="생성된 공대 내역을 초기화합니다.")
async def reset_parties_command(interaction: discord.Interaction, 레이드이름: str, 요일: str | None = None):
    if interaction.guild is None or not is_admin(interaction):
        await interaction.response.send_message("관리자만 서버 안에서 사용할 수 있습니다.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    deleted_count = clear_raid_parties(interaction.guild.id, 레이드이름.strip(), 요일.strip() if 요일 else None)
    await interaction.followup.send(f"초기화 완료: {deleted_count}건 삭제", ephemeral=True)


@bot.tree.command(name="공대수정", description="생성된 공대 내역에서 캐릭터를 이동합니다.")
async def update_party_member_command(interaction: discord.Interaction, 레이드이름: str, 요일: str, 캐릭터명: str, 공대: int, 파티: int):
    if interaction.guild is None or not is_admin(interaction):
        await interaction.response.send_message("관리자만 서버 안에서 사용할 수 있습니다.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    rows = list_raid_parties(interaction.guild.id, 레이드이름.strip(), 요일.strip())
    guild_setting = get_guild_setting(interaction.guild.id)
    moving_member = None
    if guild_setting:
        moving_member = find_matching_generated_member(rows, guild_setting["race_code"], guild_setting["server_code"], 캐릭터명.strip())
    else:
        matched = find_matching_generated_members(rows, 캐릭터명.strip())
        if len(matched) == 1:
            moving_member = matched[0]
        elif len(matched) > 1:
            view = ApplicationRaceServerView(interaction.user.id)
            await interaction.followup.send("이동할 캐릭터의 종족/서버를 선택하세요.", view=view, ephemeral=True)
            timeout = await view.wait()
            if timeout or view.value != "submit":
                return
            moving_member = find_matching_generated_member(rows, view.selected_race_code, view.selected_server_code, 캐릭터명.strip())
    if moving_member is None:
        await interaction.followup.send("이동할 캐릭터를 찾을 수 없습니다.", ephemeral=True)
        return
    can_move, reason = can_move_member_to_target(rows, moving_member, 공대, 파티)
    if not can_move:
        await interaction.followup.send(reason, ephemeral=True)
        return
    empty_slot = find_first_empty_slot(rows, 공대, 파티)
    replaced_member = None
    replace_mode = None
    target_slot_no = empty_slot
    source_weekday = str(moving_member["weekday"])
    source_raid_no = int(moving_member["raid_no"])
    source_party_no = moving_member.get("party_no")
    source_slot_no = moving_member.get("slot_no")
    source_status = str(moving_member["status"])
    if empty_slot is not None:
        update_party_member_position(int(moving_member["id"]), 요일.strip(), 공대, 파티, empty_slot, "ASSIGNED")
    else:
        mode_view = PartyReplaceModeView(interaction.user.id)
        await interaction.followup.send("대상 파티가 가득 찼습니다. 처리 방식을 선택하세요.", view=mode_view, ephemeral=True)
        timeout = await mode_view.wait()
        if timeout or mode_view.value in (None, "cancel"):
            return
        replace_mode = mode_view.value
        party_members = list_members_in_party(rows, 공대, 파티)
        replace_view = PartyReplaceView(interaction.user.id, party_members)
        await interaction.followup.send("대상 캐릭터를 선택하세요.", view=replace_view, ephemeral=True)
        timeout = await replace_view.wait()
        if timeout or replace_view.value != "submit" or replace_view.selected_member_id is None:
            return
        replaced_member = next((m for m in party_members if int(m["id"]) == int(replace_view.selected_member_id)), None)
        if replaced_member is None:
            await interaction.followup.send("선택한 대상을 찾을 수 없습니다.", ephemeral=True)
            return
        if replace_mode == "swap":
            if raid_has_same_user_after_swap(rows, moving_member, replaced_member, 공대):
                await interaction.followup.send("교체 후 같은 디스코드 계정의 다른 캐릭터가 남게 되어 이동할 수 없습니다.", ephemeral=True)
                return
            target_slot_no = int(replaced_member["slot_no"])
            swap_party_members_position(
                int(moving_member["id"]), source_weekday, source_raid_no, source_party_no, source_slot_no, source_status,
                int(replaced_member["id"]), 요일.strip(), 공대, 파티, target_slot_no, "ASSIGNED",
            )
        else:
            target_slot_no = int(replaced_member["slot_no"])
            update_party_member_position(int(replaced_member["id"]), 요일.strip(), 공대 + 1, None, None, "WAITING")
            update_party_member_position(int(moving_member["id"]), 요일.strip(), 공대, 파티, target_slot_no, "ASSIGNED")
    await interaction.followup.send(embed=build_party_update_embed(레이드이름.strip(), source_weekday, moving_member, 요일.strip(), 공대, 파티 if target_slot_no else None, target_slot_no, replaced_member, replace_mode), ephemeral=False)
    await interaction.followup.send("공대 수정이 저장되었습니다.", ephemeral=True)


@bot.tree.command(name="공대규칙테스트", description="공대 규칙 UI 테스트")
async def test_party_rules(interaction: discord.Interaction):
    if interaction.guild is None or not is_admin(interaction):
        await interaction.response.send_message("관리자만 가능합니다.", ephemeral=True)
        return
    view = PartyRuleSetupView(interaction.user.id)
    await interaction.response.send_message(view.build_summary_text(), view=view, ephemeral=True)


@bot.event
async def on_ready():
    init_db()
    try:
        await bot.tree.sync()
    except Exception:
        pass
    print(f"{bot.user} 로그인 완료")


bot.run(os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN"))
