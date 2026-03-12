# party_helpers.py
# 공대 데이터 조작 유틸 담당

from __future__ import annotations

from app_helpers import safe_int, safe_str


def normalize_party_member_row(row: dict) -> dict:
    return {
        "id": safe_int(row.get("id")),
        "guild_id": safe_int(row.get("guild_id")),
        "raid_name": safe_str(row.get("raid_name"), "-"),
        "weekday": safe_str(row.get("weekday"), "-"),
        "raid_no": safe_int(row.get("raid_no")),
        "party_no": row.get("party_no"),
        "slot_no": row.get("slot_no"),
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
        "source_application_id": row.get("source_application_id"),
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


def get_party_slot_member(
    rows: list[dict],
    raid_no: int,
    party_no: int,
    slot_no: int,
) -> dict | None:
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


def find_member_in_saved_parties(
    rows: list[dict],
    character_name: str,
    race_code: str | None = None,
    server_code: str | None = None,
) -> dict | None:
    for row in rows:
        member = normalize_party_member_row(row)

        if safe_str(member.get("character_name")) != safe_str(character_name):
            continue

        if race_code is not None and safe_str(member.get("race_code")) != safe_str(race_code):
            continue

        if server_code is not None and safe_str(member.get("server_code")) != safe_str(server_code):
            continue

        return member

    return None


def find_replace_candidate_in_party(
    rows: list[dict],
    target_raid_no: int,
    target_party_no: int,
    exclude_row_id: int | None = None,
) -> dict | None:
    party_members = list_members_in_party(rows, target_raid_no, target_party_no)

    if exclude_row_id is not None:
        party_members = [
            member for member in party_members
            if safe_int(member.get("id")) != safe_int(exclude_row_id)
        ]

    if not party_members:
        return None

    party_members.sort(
        key=lambda m: (
            safe_int(m.get("combat_score")),
            safe_int(m.get("slot_no")),
        )
    )
    return party_members[0]


# 해당 보조 함수 찾으면 여기에 넣기
# remove_member_from_saved_parties
# place_member_to_destination

# =========================
# 공대수정용 보조 함수
# =========================

def find_matching_generated_members(
    rows: list[dict],
    character_name: str,
) -> list[dict]:
    result: list[dict] = []
    for row in rows:
        member = normalize_party_member_row(row)
        if safe_str(member.get("character_name")) == safe_str(character_name):
            result.append(member)
    return result


def find_matching_generated_member(
    rows: list[dict],
    race_code: str,
    server_code: str,
    character_name: str,
) -> dict | None:
    for row in rows:
        member = normalize_party_member_row(row)
        if (
            safe_str(member.get("race_code")) == safe_str(race_code)
            and safe_str(member.get("server_code")) == safe_str(server_code)
            and safe_str(member.get("character_name")) == safe_str(character_name)
        ):
            return member
    return None


def target_raid_has_other_same_user(
    rows: list[dict],
    target_raid_no: int,
    moving_member: dict,
) -> bool:
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


def can_move_member_to_target(
    rows: list[dict],
    moving_member: dict,
    target_raid_no: int,
    target_party_no: int,
) -> tuple[bool, str]:
    current_raid_no = safe_int(moving_member.get("raid_no"))
    current_party_no = safe_int(moving_member.get("party_no") or 0)

    if current_raid_no == safe_int(target_raid_no) and current_party_no == safe_int(target_party_no):
        return False, "이미 해당 공대/파티에 배치되어 있습니다."

    if target_raid_has_other_same_user(rows, target_raid_no, moving_member):
        return False, "대상 공대에는 이미 같은 디스코드 계정의 다른 캐릭터가 있습니다."

    return True, ""


def list_members_in_raid_no(rows: list[dict], raid_no: int) -> list[dict]:
    result: list[dict] = []
    for row in rows:
        member = normalize_party_member_row(row)
        if safe_int(member.get("raid_no")) == safe_int(raid_no):
            result.append(member)
    return result


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

        raid_no = safe_int(row.get("raid_no", 0))
        party_no = safe_int(row.get("party_no", 0))
        slot_no = safe_int(row.get("slot_no", 0))

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
