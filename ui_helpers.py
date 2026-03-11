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


def group_applications_by_raid(applications: list[dict]) -> dict[str, list[dict]]:
    ...

def build_raid_application_embed(raid_name: str, applications: list[dict]) -> discord.Embed:
    ...

def format_party_member_line(member: dict) -> str:
    ...

def format_raid_result_text(...):
    ...

def build_raid_result_embed(...):
    ...

def build_party_check_embed(...):
    ...

def build_application_update_embed(...):
    ...

def build_party_update_embed(...):
    ...

def build_cancel_result_text(application: dict) -> str:
    ...

def build_force_delete_result_text(application: dict) -> str:
    ...
