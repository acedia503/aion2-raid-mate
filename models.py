# models.py
# dataclass 몇개
# 타입성 있는 구조 이름 붙이기

from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class GuildSetting:
    guild_id: int
    race_code: str
    race_name: str
    server_code: str
    server_name: str
    updated_by: int

@dataclass
class RaidRuleSlot:
    slot_index: int
    role_type: str = "ALL"
    preferred_jobs: list[str] = field(default_factory=list)

@dataclass
class CharacterSnapshot:
    user_id: int
    user_name: str
    race_code: str
    race_name: str
    server_code: str
    server_name: str
    character_name: str
    job_name: str
    item_level: int
    combat_score: int
    note: str = ""
