from __future__ import annotations

from app_helpers import safe_int, safe_str


def build_default_all_slot_rules() -> list[dict]:
    return [{"slot_index": i, "role_type": "ALL", "preferred_jobs": []} for i in range(1, 9)]
    

def normalize_party_member_row(row: dict) -> dict:
    return {
        "id": safe_int(row.get("id")),
        "guild_id": safe_int(row.get("guild_id")),
        "raid_name": safe_str(row.get("raid_name"), "-"),
        "weekday": safe_str(row.get("weekday"), "-"),
        "raid_no": safe_int(row.get("raid_no")),
        "party_no": safe_int(row.get("party_no")) if row.get("party_no") is not None else None,
        "slot_no": safe_int(row.get("slot_no")) if row.get("slot_no") is not None else None,
        "status": safe_str(row.get("status"), "-"),
        "user_id": safe_int(row.get("user_id")),
        "user_name": safe_str(row.get("user_name"), "-"),
        "race_code": safe_str(row.get("race_code"), "-"),
        "race_name": safe_str(row.get("race_name"), "-"),
        "server_code": safe_str(row.get("server_code"), "-"),
        "server_name": safe_str(row.get("server_name"), "-"),
        "character_name": safe_str(row.get("character_name"), "-"),
        "job_name": safe_str(row.get("job_name"), "알수없음"),
        "item_level": safe_int(row.get("item_level")),
        "combat_score": safe_int(row.get("combat_score")),
        "note": safe_str(row.get("note"), ""),
        "source_application_id": safe_int(row.get("source_application_id")) if row.get("source_application_id") is not None else None,
    }


def list_members_in_party(rows: list[dict], raid_no: int, party_no: int) -> list[dict]:
    result: list[dict] = []
    for row in rows:
        member = normalize_party_member_row(row)
        if (
            safe_int(member.get("raid_no")) == safe_int(raid_no)
            and safe_int(member.get("party_no")) == safe_int(party_no)
            and safe_str(member.get("status")) == "ASSIGNED"
        ):
            result.append(member)
    result.sort(key=lambda x: safe_int(x.get("slot_no")))
    return result


def get_party_size(rows: list[dict], raid_no: int, party_no: int) -> int:
    return len(list_members_in_party(rows, raid_no, party_no))


def find_first_empty_slot(rows: list[dict], raid_no: int, party_no: int) -> int | None:
    used_slots = {
        safe_int(r.get("slot_no"))
        for r in rows
        if safe_int(r.get("raid_no")) == safe_int(raid_no)
        and safe_int(r.get("party_no")) == safe_int(party_no)
        and safe_str(r.get("status")) == "ASSIGNED"
    }
    for slot_no in range(1, 5):
        if slot_no not in used_slots:
            return slot_no
    return None


def get_party_slot_member(rows: list[dict], raid_no: int, party_no: int, slot_no: int) -> dict | None:
    for row in rows:
        member = normalize_party_member_row(row)
        if (
            safe_int(member.get("raid_no")) == safe_int(raid_no)
            and safe_int(member.get("party_no")) == safe_int(party_no)
            and safe_int(member.get("slot_no")) == safe_int(slot_no)
            and safe_str(member.get("status")) == "ASSIGNED"
        ):
            return member
    return None


def find_matching_generated_members(rows: list[dict], character_name: str) -> list[dict]:
    result: list[dict] = []
    for row in rows:
        member = normalize_party_member_row(row)
        if safe_str(member.get("character_name")) == safe_str(character_name):
            result.append(member)
    return result


def find_matching_generated_member(rows: list[dict], race_code: str, server_code: str, character_name: str) -> dict | None:
    for row in rows:
        member = normalize_party_member_row(row)
        if (
            safe_str(member.get("race_code")) == safe_str(race_code)
            and safe_str(member.get("server_code")) == safe_str(server_code)
            and safe_str(member.get("character_name")) == safe_str(character_name)
        ):
            return member
    return None


def target_raid_has_other_same_user(rows: list[dict], target_raid_no: int, moving_member: dict) -> bool:
    moving_row_id = safe_int(moving_member.get("id"))
    moving_user_id = safe_int(moving_member.get("user_id"))

    for row in rows:
        member = normalize_party_member_row(row)
        if safe_int(member.get("id")) == moving_row_id:
            continue
        if safe_int(member.get("raid_no")) != safe_int(target_raid_no):
            continue
        if safe_str(member.get("status")) != "ASSIGNED":
            continue
        if safe_int(member.get("user_id")) == moving_user_id:
            return True
    return False


def can_move_member_to_target(rows: list[dict], moving_member: dict, target_raid_no: int, target_party_no: int) -> tuple[bool, str]:
    current_raid_no = safe_int(moving_member.get("raid_no"))
    current_party_no = safe_int(moving_member.get("party_no") or 0)

    if current_raid_no == safe_int(target_raid_no) and current_party_no == safe_int(target_party_no):
        return False, "이미 해당 공대/파티에 배치되어 있습니다."

    if target_raid_has_other_same_user(rows, target_raid_no, moving_member):
        return False, "대상 공대에는 이미 같은 디스코드 계정의 다른 캐릭터가 있습니다."

    return True, ""


def raid_has_same_user_after_swap(rows: list[dict], moving_member: dict, replaced_member: dict, target_raid_no: int) -> bool:
    moving_user_id = safe_int(moving_member.get("user_id"))
    moving_id = safe_int(moving_member.get("id"))
    replaced_id = safe_int(replaced_member.get("id"))

    for row in rows:
        member = normalize_party_member_row(row)
        member_id = safe_int(member.get("id"))
        if member_id in {moving_id, replaced_id}:
            continue
        if safe_int(member.get("raid_no")) != safe_int(target_raid_no):
            continue
        if safe_str(member.get("status")) != "ASSIGNED":
            continue
        if safe_int(member.get("user_id")) == moving_user_id:
            return True
    return False


def group_party_rows_by_weekday(rows: list[dict]) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    for row in rows:
        weekday = safe_str(row.get("weekday"), "-")
        result.setdefault(weekday, []).append(row)
    return result


def convert_rows_to_raid_structure(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    raid_map: dict[int, dict] = {}
    waiting_members: list[dict] = []

    for raw in rows:
        row = normalize_party_member_row(raw)
        status = safe_str(row.get("status"))

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

        raid_no = safe_int(row.get("raid_no"))
        party_no = safe_int(row.get("party_no"))
        slot_no = safe_int(row.get("slot_no"))

        if raid_no not in raid_map:
            raid_map[raid_no] = {"raid_no": raid_no, "party1": [], "party2": []}

        raid = raid_map[raid_no]
        party_key = "party1" if party_no == 1 else "party2"
        party = raid[party_key]

        while len(party) < slot_no:
            party.append({})
        party[slot_no - 1] = member

    raids: list[dict] = []
    for raid_no in sorted(raid_map.keys()):
        raid = raid_map[raid_no]
        raid["party1"] = [m for m in raid["party1"] if m]
        raid["party2"] = [m for m in raid["party2"] if m]
        raids.append(raid)

    return raids, waiting_members


def split_members_already_assigned_other_weekday(
    candidates: list[dict],
    other_weekday_assigned_rows: list[dict],
) -> tuple[list[dict], list[dict]]:
    assigned_map: dict[tuple[str, str, str], dict] = {}

    for row in other_weekday_assigned_rows:
        normalized = normalize_party_member_row(row)
        key = (
            safe_str(normalized.get("race_code")),
            safe_str(normalized.get("server_code")),
            safe_str(normalized.get("character_name")),
        )
        assigned_map[key] = normalized

    available_candidates: list[dict] = []
    cross_weekday_members: list[dict] = []

    for candidate in candidates:
        key = (
            safe_str(candidate.get("race_code")),
            safe_str(candidate.get("server_code")),
            safe_str(candidate.get("character_name")),
        )
        matched = assigned_map.get(key)
        if matched:
            cross_weekday_members.append(
                {
                    "character_name": candidate.get("character_name"),
                    "race_name": candidate.get("race_name"),
                    "server_name": candidate.get("server_name"),
                    "job_name": candidate.get("job_name"),
                    "item_level": candidate.get("item_level"),
                    "combat_score": candidate.get("combat_score"),
                    "assigned_weekday": matched.get("weekday"),
                    "assigned_raid_no": matched.get("raid_no"),
                    "assigned_party_no": matched.get("party_no"),
                    "assigned_slot_no": matched.get("slot_no"),
                }
            )
        else:
            available_candidates.append(candidate)

    return available_candidates, cross_weekday_members
