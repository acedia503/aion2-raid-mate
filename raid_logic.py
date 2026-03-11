# raid_logic.py
from __future__ import annotations

from typing import Any


# =========================
# 직업 역할 매핑
# =========================
# 실제 게임 기준에 맞게 수정 가능
JOB_ROLE_MAP: dict[str, set[str]] = {
    "수호성": {"TANK"},
    "검성": {"TANK", "DPS"},
    "치유성": {"HEAL"},
    "호법성": {"HEAL", "DPS"},
    "궁성": {"DPS"},
    "살성": {"DPS"},
    "마도성": {"DPS"},
    "정령성": {"DPS"},
}


# =========================
# 정규화 / 공통 유틸
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


def normalize_application_row(row: dict) -> dict:
    return {
        "id": safe_int(row.get("id")),
        "guild_id": safe_int(row.get("guild_id")),
        "user_id": safe_int(row.get("user_id")),
        "user_name": safe_str(row.get("user_name"), "-"),
        "raid_name": safe_str(row.get("raid_name"), "-"),
        "race_code": safe_str(row.get("race_code"), "-"),
        "race_name": safe_str(row.get("race_name"), "-"),
        "server_code": safe_str(row.get("server_code"), "-"),
        "server_name": safe_str(row.get("server_name"), "-"),
        "character_name": safe_str(row.get("character_name"), "-"),
        "job_name": safe_str(row.get("job_name"), "알수없음"),
        "item_level": safe_int(row.get("item_level")),
        "combat_score": safe_int(row.get("combat_score")),
        "peak_combat_score": safe_int(row.get("peak_combat_score")),
        "available_days": list(row.get("available_days") or []),
        "note": safe_str(row.get("note"), ""),
    }


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


def member_identity(member: dict) -> tuple:
    return (
        safe_str(member.get("race_code")),
        safe_str(member.get("server_code")),
        safe_str(member.get("character_name")),
    )


def member_display_key(member: dict) -> str:
    return (
        f"{member.get('character_name', '-')}"
        f" ({member.get('race_name', '-')}/{member.get('server_name', '-')})"
    )


# =========================
# 요일 / 후보 필터링
# =========================

def has_weekday(member: dict, weekday: str) -> bool:
    days = member.get("available_days") or []
    return weekday in days


def filter_candidates_by_weekday(applications: list[dict], weekday: str) -> list[dict]:
    result: list[dict] = []
    for row in applications:
        member = normalize_application_row(row)
        if has_weekday(member, weekday):
            result.append(member)
    return result


def exclude_already_generated_characters(
    candidates: list[dict],
    existing_members: list[dict],
) -> list[dict]:
    existing_ids = {
        member_identity(normalize_party_member_row(row))
        for row in existing_members
    }

    result: list[dict] = []
    for candidate in candidates:
        if member_identity(candidate) not in existing_ids:
            result.append(candidate)
    return result


# =========================
# 역할 / 직업 매칭
# =========================

def get_job_roles(job_name: str) -> set[str]:
    return JOB_ROLE_MAP.get(safe_str(job_name), {"DPS"})


def job_matches_role(job_name: str, role_type: str) -> bool:
    role_type = safe_str(role_type).upper()
    if role_type == "ALL":
        return True
    return role_type in get_job_roles(job_name)


def job_matches_preferred(job_name: str, preferred_jobs: list[str]) -> bool:
    if not preferred_jobs:
        return True
    return safe_str(job_name) in {safe_str(job) for job in preferred_jobs}


def can_place_member_in_slot(member: dict, slot_rule: dict) -> bool:
    role_type = safe_str(slot_rule.get("role_type"), "ALL").upper()
    preferred_jobs = list(slot_rule.get("preferred_jobs") or [])

    if not job_matches_role(member["job_name"], role_type):
        return False

    # ALL은 누구나 가능, preferred_jobs는 우선순위용
    if role_type == "ALL":
        return True

    # 탱/딜/힐은 역할만 맞으면 일단 가능
    return True


def score_member_for_slot(member: dict, slot_rule: dict) -> int:
    score = 0
    role_type = safe_str(slot_rule.get("role_type"), "ALL").upper()
    preferred_jobs = list(slot_rule.get("preferred_jobs") or [])

    if job_matches_role(member["job_name"], role_type):
        score += 100

    if preferred_jobs and job_matches_preferred(member["job_name"], preferred_jobs):
        score += 50

    score += safe_int(member.get("combat_score")) // 1000
    return score


# =========================
# 공대 / 파티 점수 계산
# =========================

def party_score_sum(party: list[dict]) -> int:
    return sum(safe_int(member.get("combat_score")) for member in party)


def raid_score_sum(raid: dict) -> int:
    return party_score_sum(raid["party1"]) + party_score_sum(raid["party2"])


def party_average_score(party: list[dict]) -> int:
    if not party:
        return 0
    return party_score_sum(party) // len(party)


def raid_average_score(raid: dict) -> int:
    members = raid["party1"] + raid["party2"]
    if not members:
        return 0
    return raid_score_sum(raid) // len(members)


# =========================
# 공대 기본 구조
# =========================

def make_empty_raid(raid_no: int) -> dict:
    return {
        "raid_no": raid_no,
        "party1": [],
        "party2": [],
    }


def slot_index_to_party_slot(slot_index: int) -> tuple[int, int]:
    # 1~4 -> party1 slot1~4
    # 5~8 -> party2 slot1~4
    if 1 <= slot_index <= 4:
        return 1, slot_index
    return 2, slot_index - 4


def get_party_by_no(raid: dict, party_no: int) -> list[dict]:
    return raid["party1"] if party_no == 1 else raid["party2"]


def get_slot_member(raid: dict, slot_index: int) -> dict | None:
    party_no, slot_no = slot_index_to_party_slot(slot_index)
    party = get_party_by_no(raid, party_no)
    idx = slot_no - 1

    if idx < len(party):
        return party[idx]
    return None


def set_slot_member(raid: dict, slot_index: int, member: dict) -> None:
    party_no, slot_no = slot_index_to_party_slot(slot_index)
    party = get_party_by_no(raid, party_no)
    idx = slot_no - 1

    while len(party) <= idx:
        party.append({})

    party[idx] = member


def is_slot_filled(raid: dict, slot_index: int) -> bool:
    member = get_slot_member(raid, slot_index)
    return bool(member)


# =========================
# 중복 규칙
# =========================

def raid_has_same_user_id(raid: dict, user_id: int) -> bool:
    for party_name in ("party1", "party2"):
        for member in raid[party_name]:
            if member and safe_int(member.get("user_id")) == safe_int(user_id):
                return True
    return False


# =========================
# 후보 정렬
# =========================

def role_priority(member: dict) -> int:
    roles = get_job_roles(member["job_name"])
    if "HEAL" in roles:
        return 0
    if "TANK" in roles:
        return 1
    return 2


def sort_candidates_for_generation(candidates: list[dict]) -> list[dict]:
    return sorted(
        candidates,
        key=lambda m: (
            role_priority(m),
            -safe_int(m.get("combat_score")),
            -safe_int(m.get("item_level")),
            safe_str(m.get("character_name")),
        ),
    )


# =========================
# 슬롯 규칙 구조화
# =========================

def make_slot_map_from_rules(rules: list[dict]) -> dict[int, dict]:
    slot_map: dict[int, dict] = {}
    for rule in rules:
        slot_index = safe_int(rule.get("slot_index"))
        slot_map[slot_index] = {
            "slot_index": slot_index,
            "role_type": safe_str(rule.get("role_type"), "ALL").upper(),
            "preferred_jobs": list(rule.get("preferred_jobs") or []),
        }
    return slot_map


# =========================
# 배치 로직
# =========================

def find_best_raid_for_member(
    member: dict,
    raids: list[dict],
    slot_index: int,
) -> dict | None:
    available_raids = [
        raid for raid in raids
        if not raid_has_same_user_id(raid, member["user_id"])
        and not is_slot_filled(raid, slot_index)
    ]

    if not available_raids:
        return None

    # 총 아툴이 가장 낮은 공대 우선
    available_raids.sort(key=raid_score_sum)
    return available_raids[0]


def place_member_into_slot(
    member: dict,
    raids: list[dict],
    slot_index: int,
    slot_rule: dict,
) -> bool:
    if not can_place_member_in_slot(member, slot_rule):
        return False

    target_raid = find_best_raid_for_member(member, raids, slot_index)
    if target_raid is None:
        return False

    set_slot_member(target_raid, slot_index, member)
    return True


def find_fillable_slot_indices(raid: dict, slot_map: dict[int, dict], member: dict) -> list[int]:
    result: list[int] = []
    for slot_index in range(1, 9):
        if is_slot_filled(raid, slot_index):
            continue

        slot_rule = slot_map.get(slot_index, {"slot_index": slot_index, "role_type": "ALL", "preferred_jobs": []})
        if can_place_member_in_slot(member, slot_rule):
            result.append(slot_index)
    return result


def find_best_open_slot_for_member(
    member: dict,
    raids: list[dict],
    slot_map: dict[int, dict],
) -> tuple[dict, int] | None:
    candidates: list[tuple[int, int, dict, int]] = []
    # (raid_score, -slot_score, raid, slot_index)

    for raid in raids:
        if raid_has_same_user_id(raid, member["user_id"]):
            continue

        fillable_slots = find_fillable_slot_indices(raid, slot_map, member)
        for slot_index in fillable_slots:
            slot_rule = slot_map.get(slot_index, {"slot_index": slot_index, "role_type": "ALL", "preferred_jobs": []})
            slot_score = score_member_for_slot(member, slot_rule)
            candidates.append((raid_score_sum(raid), -slot_score, raid, slot_index))

    if not candidates:
        return None

    candidates.sort(key=lambda x: (x[0], x[1], x[3]))
    _, _, raid, slot_index = candidates[0]
    return raid, slot_index


def build_balanced_raids(
    candidates: list[dict],
    slot_rules: list[dict],
) -> tuple[list[dict], list[dict], list[str]]:
    """
    반환:
    - raids
    - waiting_members
    - warnings
    """
    warnings: list[str] = []
    candidates = [normalize_application_row(row) for row in candidates]
    candidates = sort_candidates_for_generation(candidates)

    if not candidates:
        return [], [], warnings

    # 필요 공대 수 계산: 8명당 1공대
    raid_count = (len(candidates) + 7) // 8
    raids = [make_empty_raid(i + 1) for i in range(raid_count)]

    slot_map = make_slot_map_from_rules(slot_rules)

    assigned_identities: set[tuple] = set()
    waiting_members: list[dict] = []

    # 1차: 규칙 강한 슬롯부터 채움 (탱/힐 우선)
    prioritized_slots = []
    for slot_index in range(1, 9):
        rule = slot_map.get(slot_index, {"slot_index": slot_index, "role_type": "ALL", "preferred_jobs": []})
        role_type = rule["role_type"]
        priority = 0 if role_type in ("TANK", "HEAL") else 1
        prioritized_slots.append((priority, slot_index))

    prioritized_slots.sort()

    remaining = candidates[:]

    for _, slot_index in prioritized_slots:
        slot_rule = slot_map.get(slot_index, {"slot_index": slot_index, "role_type": "ALL", "preferred_jobs": []})

        next_remaining: list[dict] = []
        for member in remaining:
            identity = member_identity(member)
            if identity in assigned_identities:
                continue

            placed = place_member_into_slot(member, raids, slot_index, slot_rule)
            if placed:
                assigned_identities.add(identity)
            else:
                next_remaining.append(member)

        remaining = next_remaining

    # 2차: 남은 사람을 빈 자리 어디든 최대한 배치
    still_remaining: list[dict] = []
    for member in remaining:
        identity = member_identity(member)
        if identity in assigned_identities:
            continue

        result = find_best_open_slot_for_member(member, raids, slot_map)
        if result is None:
            still_remaining.append(member)
            continue

        raid, slot_index = result
        set_slot_member(raid, slot_index, member)
        assigned_identities.add(identity)

    # 3차: 못 들어간 인원은 대기
    for member in still_remaining:
        waiting_members.append(member)
        warnings.append(f"대기 배정: {member_display_key(member)}")

    # 빈 dict 제거 및 party 길이 정리
    for raid in raids:
        raid["party1"] = [m for m in raid["party1"] if m]
        raid["party2"] = [m for m in raid["party2"] if m]

    return raids, waiting_members, warnings


# =========================
# DB 저장용 변환
# =========================

def flatten_raids_to_party_rows(
    guild_id: int,
    raid_name: str,
    weekday: str,
    raids: list[dict],
    waiting_members: list[dict],
) -> list[dict]:
    rows: list[dict] = []

    for raid in raids:
        raid_no = safe_int(raid.get("raid_no"))

        for party_no, party_key in ((1, "party1"), (2, "party2")):
            party = raid.get(party_key, [])
            for slot_no, member in enumerate(party, start=1):
                rows.append(
                    {
                        "guild_id": guild_id,
                        "raid_name": raid_name,
                        "weekday": weekday,
                        "raid_no": raid_no,
                        "party_no": party_no,
                        "slot_no": slot_no,
                        "status": "ASSIGNED",
                        "user_id": safe_int(member.get("user_id")),
                        "user_name": safe_str(member.get("user_name"), "-"),
                        "race_code": safe_str(member.get("race_code"), "-"),
                        "race_name": safe_str(member.get("race_name"), "-"),
                        "server_code": safe_str(member.get("server_code"), "-"),
                        "server_name": safe_str(member.get("server_name"), "-"),
                        "character_name": safe_str(member.get("character_name"), "-"),
                        "job_name": safe_str(member.get("job_name"), "알수없음"),
                        "item_level": safe_int(member.get("item_level")),
                        "combat_score": safe_int(member.get("combat_score")),
                        "note": safe_str(member.get("note"), ""),
                        "source_application_id": member.get("id"),
                    }
                )

    waiting_raid_no = len(raids) + 1 if raids else 1
    for member in waiting_members:
        rows.append(
            {
                "guild_id": guild_id,
                "raid_name": raid_name,
                "weekday": weekday,
                "raid_no": waiting_raid_no,
                "party_no": None,
                "slot_no": None,
                "status": "WAITING",
                "user_id": safe_int(member.get("user_id")),
                "user_name": safe_str(member.get("user_name"), "-"),
                "race_code": safe_str(member.get("race_code"), "-"),
                "race_name": safe_str(member.get("race_name"), "-"),
                "server_code": safe_str(member.get("server_code"), "-"),
                "server_name": safe_str(member.get("server_name"), "-"),
                "character_name": safe_str(member.get("character_name"), "-"),
                "job_name": safe_str(member.get("job_name"), "알수없음"),
                "item_level": safe_int(member.get("item_level")),
                "combat_score": safe_int(member.get("combat_score")),
                "note": safe_str(member.get("note"), ""),
                "source_application_id": member.get("id"),
            }
        )


# =========================
# 공대수정용 보조 함수
# =========================

def list_members_in_raid_no(rows: list[dict], raid_no: int) -> list[dict]:
    result: list[dict] = []
    for row in rows:
        member = normalize_party_member_row(row)
        if safe_int(member.get("raid_no")) == safe_int(raid_no):
            result.append(member)
    return result





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


def find_first_empty_slot(
    rows: list[dict],
    target_raid_no: int,
    target_party_no: int,
) -> int | None:
    used_slots: set[int] = set()

    for row in rows:
        member = normalize_party_member_row(row)
        if (
            safe_int(member.get("raid_no")) == safe_int(target_raid_no)
            and safe_int(member.get("party_no")) == safe_int(target_party_no)
            and safe_str(member.get("status")) == "ASSIGNED"
        ):
            used_slots.add(safe_int(member.get("slot_no")))

    for slot_no in (1, 2, 3, 4):
        if slot_no not in used_slots:
            return slot_no

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

    # 1차 규칙:
    # 파티가 가득 차 있으면 아툴 점수가 가장 낮은 멤버를 대기로 이동
    party_members.sort(
        key=lambda m: (
            safe_int(m.get("combat_score")),
            safe_int(m.get("slot_no")),
        )
    )
    return party_members[0]

    return rows
