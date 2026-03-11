# ui_helpers.py
# 보여주기 위한 출력용 함수

from __future__ import annotations
import discord

def format_days(days: list[str]) -> str:
    return ", ".join(days) if days else "-"

def split_text_by_lines(text: str, limit: int = 1800) -> list[str]:
    ...
    
def format_application_line(app: dict) -> str:
    ...

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
