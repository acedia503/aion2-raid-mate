# party_helpers.py
# 공대 데이터 조작 유틸 담당

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


# =========================================================
# 1. 파티 상태 조회
# =========================================================

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
    

# =========================================================
#  2. 슬롯 관련
# =========================================================

def find_first_empty_slot(rows: list[dict], raid_no: int, party_no: int) -> int | None:
    used = {
        r["slot_no"]
        for r in rows
        if r["raid_no"] == raid_no
        and r["party_no"] == party_no
    }

    for i in range(1, 5):
        if i not in used:
            return i

    return None


def find_first_empty_slot(rows: list[dict], raid_no: int, party_no: int) -> int | None:
    for r in rows:
        if (
            r["raid_no"] == raid_no
            and r["party_no"] == party_no
            and r["slot_no"] == slot_no
        ):
            return r
    return None


# =========================================================
# 3. 캐릭터 위치 찾기
# =========================================================

def find_member_in_saved_parties(rows: list[dict], character_name: str) -> dict | None:
    for r in rows:
        if r["character_name"] == character_name:
            return r
    return None


# =========================================================
# 4. 교체 대상
# =========================================================

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



# =========================================================
# 5. 공대 수정용 유틸
# =========================================================

# 해당 보조 함수 찾으면 여기에 넣기
# remove_member_from_saved_parties
# place_member_to_destination
