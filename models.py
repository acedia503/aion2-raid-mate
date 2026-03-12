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
    updated_at: str | None = None

    @classmethod
    def from_row(cls, row: dict) -> "GuildSetting":
        return cls(
            guild_id=int(row["guild_id"]),
            race_code=str(row["race_code"]),
            race_name=str(row["race_name"]),
            server_code=str(row["server_code"]),
            server_name=str(row["server_name"]),
            updated_by=int(row["updated_by"]),
            updated_at=str(row["updated_at"]) if row.get("updated_at") is not None else None,
        )


@dataclass
class RaidRuleSlot:
    slot_index: int
    role_type: str = "ALL"
    preferred_jobs: list[str] = field(default_factory=list)

    @classmethod
    def from_row(cls, row: dict) -> "RaidRuleSlot":
        return cls(
            slot_index=int(row["slot_index"]),
            role_type=str(row.get("role_type", "ALL")).upper(),
            preferred_jobs=list(row.get("preferred_jobs") or []),
        )

    def to_dict(self) -> dict:
        return {
            "slot_index": self.slot_index,
            "role_type": self.role_type,
            "preferred_jobs": list(self.preferred_jobs),
        }


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
    peak_combat_score: int = 0
    note: str = ""
    available_days: list[str] = field(default_factory=list)
    guild_id: int = 0
    raid_name: str = ""
    source_application_id: int | None = None

    @classmethod
    def from_atool(
        cls,
        *,
        user_id: int,
        user_name: str,
        race_code: str,
        race_name: str,
        server_code: str,
        server_name: str,
        data: dict,
        note: str = "",
        available_days: list[str] | None = None,
        guild_id: int = 0,
        raid_name: str = "",
    ) -> "CharacterSnapshot":
        return cls(
            user_id=user_id,
            user_name=user_name,
            race_code=str(race_code),
            race_name=str(race_name),
            server_code=str(server_code),
            server_name=str(server_name),
            character_name=str(data.get("nickname", "")).strip(),
            job_name=str(data.get("job_name", "알수없음")).strip(),
            item_level=int(data.get("item_level", 0)),
            combat_score=int(data.get("combat_score", 0)),
            peak_combat_score=int(data.get("peak_combat_score", 0)),
            note=str(note).strip(),
            available_days=list(available_days or []),
            guild_id=int(guild_id),
            raid_name=str(raid_name).strip(),
        )

    @classmethod
    def from_row(cls, row: dict) -> "CharacterSnapshot":
        return cls(
            user_id=int(row.get("user_id", 0)),
            user_name=str(row.get("user_name", "")).strip(),
            race_code=str(row.get("race_code", "")).strip(),
            race_name=str(row.get("race_name", "")).strip(),
            server_code=str(row.get("server_code", "")).strip(),
            server_name=str(row.get("server_name", "")).strip(),
            character_name=str(row.get("character_name", "")).strip(),
            job_name=str(row.get("job_name", "알수없음")).strip(),
            item_level=int(row.get("item_level", 0)),
            combat_score=int(row.get("combat_score", 0)),
            peak_combat_score=int(row.get("peak_combat_score", 0)),
            note=str(row.get("note", "") or "").strip(),
            available_days=list(row.get("available_days") or []),
            guild_id=int(row.get("guild_id", 0)),
            raid_name=str(row.get("raid_name", "")).strip(),
            source_application_id=row.get("source_application_id"),
        )

    def to_application_dict(self) -> dict:
        return {
            "guild_id": self.guild_id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "raid_name": self.raid_name,
            "race_code": self.race_code,
            "race_name": self.race_name,
            "server_code": self.server_code,
            "server_name": self.server_name,
            "character_name": self.character_name,
            "job_name": self.job_name,
            "item_level": self.item_level,
            "combat_score": self.combat_score,
            "peak_combat_score": self.peak_combat_score,
            "available_days": list(self.available_days),
            "note": self.note,
        }
