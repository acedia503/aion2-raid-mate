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
  
get_party_size


# =========================================================
#  2. 슬롯 관
# =========================================================

find_first_empty_slot
get_party_slot_member


# =========================================================
# 3. 캐릭터 위치 찾
# =========================================================

find_member_in_saved_parties


# =========================================================
# 4. 교체 대상
# =========================================================

find_replace_candidate_in_party


# =========================================================
# 5. 공대 수정용 유
# =========================================================

remove_member_from_saved_parties
place_member_to_destination
