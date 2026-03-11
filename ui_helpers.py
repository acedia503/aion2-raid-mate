# ui_helpers.py
# 보여주기 위한 출력용 함수

from __future__ import annotations
import discord

def format_days(days: list[str]) -> str:
    return ", ".join(days) if days else "-"

# 긴 메시지 분할
def split_text_by_lines(text: str, limit: int = 1800) -> list[str]:
    if not text:
        return ["-"]

    lines = text.splitlines()
    chunks: list[str] = []
    current = ""

    for line in lines:
        next_text = line if not current else f"{current}\n{line}"
        if len(next_text) <= limit:
            current = next_text
            continue

        if current:
            chunks.append(current)
        current = line

    if current:
        chunks.append(current)

    return chunks if chunks else ["-"]

# 긴 코드블록 전
async def send_long_text_followup(
    interaction: discord.Interaction,
    text: str,
    ephemeral: bool = False,
    limit: int = 1800,
):
    chunks = split_text_by_lines(text, limit=limit)
    for chunk in chunks:
        await interaction.followup.send(
            f"```text\n{chunk}\n```",
            ephemeral=ephemeral,
        )

    
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


# 레이드별 신청내역 그룹화
def group_applications_by_raid(applications: list[dict]) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}

    for app in applications:
        raid_name = app["raid_name"]
        if raid_name not in result:
            result[raid_name] = []
        result[raid_name].append(app)

    return result


# 레이드별 Embed 생성 함수
def build_raid_application_embed(raid_name: str, applications: list[dict]) -> discord.Embed:
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


# 공대 결과 포맷
def party_score_sum(party: list[dict]) -> int:
    return sum(int(member.get("combat_score", 0)) for member in party)


def raid_score_sum_for_display(raid: dict) -> int:
    return party_score_sum(raid.get("party1", [])) + party_score_sum(raid.get("party2", []))


def format_party_member_line(member: dict) -> str:
    return (
        f"{member.get('character_name', '-')} | "
        f"{member.get('race_name', '-')} / {member.get('server_name', '-')} | "
        f"{member.get('job_name', '-')} | "
        f"{member.get('item_level', 0)} | "
        f"{member.get('combat_score', 0)}"
    )


def format_raid_result_text(
    raid_name: str,
    weekday: str,
    raids: list[dict],
    waiting_members: list[dict],
    source_note: str | None = None,
) -> str:
    lines: list[str] = []
    lines.append(f"[{raid_name}] {weekday} 공대 생성 결과")
    lines.append("")

    for raid in raids:
        raid_no = raid.get("raid_no", 0)
        party1 = raid.get("party1", [])
        party2 = raid.get("party2", [])

        total_members = len(party1) + len(party2)
        total_score = raid_score_sum_for_display(raid)
        avg_score = total_score // total_members if total_members else 0

        lines.append(f"{raid_no}공대 | 총 아툴 {total_score} | 평균 {avg_score}")

        lines.append("  1파티")
        if party1:
            for member in party1:
                lines.append(f"    - {format_party_member_line(member)}")
        else:
            lines.append("    - 비어 있음")

        lines.append("")
        lines.append("  2파티")
        if party2:
            for member in party2:
                lines.append(f"    - {format_party_member_line(member)}")
        else:
            lines.append("    - 비어 있음")

        lines.append("")

    lines.append("대기 인원")
    if waiting_members:
        for member in waiting_members:
            lines.append(f"  - {format_party_member_line(member)}")
    else:
        lines.append("  - 없음")

    if source_note:
        lines.append("")
        lines.append(f"※ {source_note}")

    return "\n".join(lines)


def build_raid_result_embed(
    raid_name: str,
    weekday: str,
    raids: list[dict],
    waiting_members: list[dict],
    source_note: str | None = None,
) -> discord.Embed:
    assigned_count = sum(len(raid.get("party1", [])) + len(raid.get("party2", [])) for raid in raids)
    waiting_count = len(waiting_members)

    embed = discord.Embed(
        title=f"[{raid_name}] {weekday} 공대 생성 결과",
        color=discord.Color.green(),
    )
    embed.add_field(name="생성 공대 수", value=str(len(raids)), inline=False)
    embed.add_field(name="배정 인원", value=str(assigned_count), inline=False)
    embed.add_field(name="대기 인원", value=str(waiting_count), inline=False)

    if source_note:
        embed.set_footer(text=source_note)

    return embed


def build_party_check_embed(
    raid_name: str,
    weekday: str | None,
    raids: list[dict],
    waiting_members: list[dict],
) -> discord.Embed:
    assigned_count = sum(len(raid.get("party1", [])) + len(raid.get("party2", [])) for raid in raids)
    waiting_count = len(waiting_members)

    title = f"[{raid_name}] 공대 확인" if weekday is None else f"[{raid_name}] {weekday} 공대 확인"

    embed = discord.Embed(
        title=title,
        color=discord.Color.blurple(),
    )
    embed.add_field(name="생성 공대 수", value=str(len(raids)), inline=False)
    embed.add_field(name="배정 인원", value=str(assigned_count), inline=False)
    embed.add_field(name="대기 인원", value=str(waiting_count), inline=False)
    embed.set_footer(text="※ 템렙/아툴 점수는 공대 생성 시점 기준입니다.")
    return embed


def format_party_check_text_for_weekday(
    raid_name: str,
    weekday: str,
    raids: list[dict],
    waiting_members: list[dict],
) -> str:
    return format_raid_result_text(
        raid_name=raid_name,
        weekday=weekday,
        raids=raids,
        waiting_members=waiting_members,
        source_note="공대 확인의 템렙/아툴 점수는 공대 생성 시점 기준입니다.",
    )


# 수정완료 공개 메시지용
def build_application_update_embed(
    raid_name: str,
    data: dict,
    available_days: list[str],
    note: str,
    show_race_server: bool = True,
) -> discord.Embed:
    embed = discord.Embed(
        title=f"[{raid_name}] 신청 수정 완료",
        color=discord.Color.orange(),
    )
    embed.add_field(name="캐릭터명", value=data["nickname"], inline=False)

    if show_race_server:
        embed.add_field(
            name="종족/종족서버",
            value=f"{data['race_name']} / {data['server_name']}",
            inline=False,
        )

    embed.add_field(name="직업", value=data["job_name"], inline=False)
    embed.add_field(name="템렙", value=str(data["item_level"]), inline=False)
    embed.add_field(name="아툴 점수", value=str(data["combat_score"]), inline=False)
    embed.add_field(name="가능 요일", value=format_days(available_days), inline=False)

    if note:
        embed.add_field(name="특이사항", value=note, inline=False)

    return embed


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
