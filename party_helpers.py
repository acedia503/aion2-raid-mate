# party_helpers.py
# 공대 데이터 조작 유틸 담당

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


def get_party_size(rows, raid_no, party_no):
    return len(list_members_in_party(rows, raid_no, party_no))
    

# =========================================================
#  2. 슬롯 관
# =========================================================

def find_first_empty_slot(rows, raid_no, party_no):
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


def get_party_slot_member(rows, raid_no, party_no, slot_no):
    for r in rows:
        if (
            r["raid_no"] == raid_no
            and r["party_no"] == party_no
            and r["slot_no"] == slot_no
        ):
            return r
    return None


# =========================================================
# 3. 캐릭터 위치 찾
# =========================================================

def find_member_in_saved_parties(rows, character_name):
    for r in rows:
        if r["character_name"] == character_name:
            return r
    return None


# =========================================================
# 4. 교체 대상
# =========================================================

find_replace_candidate_in_party


# =========================================================
# 5. 공대 수정용 유
# =========================================================

remove_member_from_saved_parties
place_member_to_destination
