from __future__ import annotations

from typing import Any

import discord

from constants import RACE_OPTIONS, SERVER_OPTIONS, SERVERS_BY_RACE


# =========================
# 기본 유틸
# =========================

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


# =========================
# lookup 캐시 (속도 개선)
# =========================

RACE_CODE_MAP = {safe_str(r["code"]): r for r in RACE_OPTIONS}
SERVER_CODE_MAP = {safe_str(s["code"]): s for s in SERVER_OPTIONS}


# =========================
# race 조회
# =========================

def get_race_by_code(race_code: str) -> dict | None:
    return RACE_CODE_MAP.get(safe_str(race_code))


def get_race_name_by_code(race_code: str) -> str | None:
    race = get_race_by_code(race_code)
    if race:
        return safe_str(race.get("name"))
    return None


# =========================
# server 조회
# =========================

def get_server_by_code(server_code: str) -> dict | None:
    return SERVER_CODE_MAP.get(safe_str(server_code))


def get_server_name_by_code(server_code: str) -> str | None:
    server = get_server_by_code(server_code)
    if server:
        return safe_str(server.get("name"))
    return None


# =========================
# race별 서버 목록
# =========================

def get_servers_for_race(race_code: str) -> list[dict]:
    return [dict(server) for server in SERVERS_BY_RACE.get(safe_str(race_code), [])]


# =========================
# 관리자 체크
# =========================

def is_admin(interaction: discord.Interaction) -> bool:
    if interaction.guild is None:
        return False
    return interaction.user.guild_permissions.administrator


# =========================
# 이건 뭐지..?
# =========================

def make_character_key(row: dict) -> tuple[str, str, str]:
    return (
        str(row.get("race_code", "")).strip(),
        str(row.get("server_code", "")).strip(),
        str(row.get("character_name", "")).strip().lower(),
    )
