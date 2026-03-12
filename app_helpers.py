# app_helpers.py
# 신청/공대와 상관없이 공통으로 쓰는 작은 유틸 모음

from __future__ import annotations

from typing import Any

import discord

from constants import RACE_OPTIONS, SERVER_OPTIONS


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def format_days(days: list[str]) -> str:
    return ", ".join(days) if days else "-"


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





def get_race_name_by_code(race_code: str) -> str | None:
    for race in RACE_OPTIONS:
        if str(race["code"]) == str(race_code):
            return race["name"]
    return None


def get_server_name_by_code(server_code: str) -> str | None:
    for server in SERVER_OPTIONS:
        if str(server["code"]) == str(server_code):
            return server["name"]
    return None


def get_servers_for_race(race_code: str) -> list[dict]:
    return [
        server
        for server in SERVER_OPTIONS
        if str(server["code"]).startswith(str(race_code))
    ]


def is_admin(interaction: discord.Interaction) -> bool:
    if interaction.guild is None:
        return False
    return interaction.user.guild_permissions.administrator
