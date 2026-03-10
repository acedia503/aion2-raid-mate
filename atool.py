# atool.py
from __future__ import annotations

from typing import Any

import requests


ATOOL_SEARCH_URL = "https://www.aion2tool.com/api/character/search"

# 아툴 호출 시 너무 빈약한 헤더로 보내면 막히는 경우가 있어서
# 브라우저에 가까운 헤더를 넣는 편이 안전하다.
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/145.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": "https://www.aion2tool.com",
    "Referer": "https://www.aion2tool.com/",
}


class AtoolError(Exception):
    """아툴 조회 실패용 예외"""


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_character_payload(
    raw: dict[str, Any],
    race_code: str | int,
    race_name: str,
    server_code: str | int,
    server_name: str,
) -> dict[str, Any]:
    """
    아툴 응답을 우리 봇에서 쓰는 공통 형식으로 정규화
    """
    return {
        "race_code": str(race_code),
        "race_name": str(race_name).strip(),
        "server_code": str(server_code),
        "server_name": str(server_name).strip(),
        "nickname": str(raw.get("nickname", "")).strip(),
        "job_name": str(raw.get("job", "")).strip() or "알수없음",
        "item_level": safe_int(raw.get("combat_power", 0)),
        "combat_score": safe_int(raw.get("combat_score", 0)),
        "peak_combat_score": safe_int(
            raw.get("max_combat_score", raw.get("peak_combat_score", raw.get("combat_score", 0)))
        ),
    }


def _extract_character_data(data: Any) -> dict[str, Any] | None:
    """
    응답 형식이 바뀌어도 최대한 유연하게 꺼내기 위한 함수
    """
    if isinstance(data, dict):
        # 1) 바로 캐릭터 dict가 오는 경우
        if "job" in data or "combat_power" in data or "combat_score" in data:
            return data

        # 2) data/result/character 하위에 들어있는 경우
        for key in ("data", "result", "character"):
            value = data.get(key)
            if isinstance(value, dict):
                if "job" in value or "combat_power" in value or "combat_score" in value:
                    return value

        # 3) list가 들어있는 경우
        for key in ("data", "results", "characters", "items", "list"):
            value = data.get(key)
            if isinstance(value, list) and value:
                first = value[0]
                if isinstance(first, dict):
                    return first

    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            return first

    return None


def get_character_info(
    race_code: str | int,
    race_name: str,
    server_code: str | int,
    server_name: str,
    character_name: str,
    timeout: int = 15,
) -> dict[str, Any]:
    """
    아툴 캐릭터 조회

    반환 예시:
    {
        "race_code": "2",
        "race_name": "마족",
        "server_code": "2019",
        "server_name": "진",
        "nickname": "버터와플",
        "job_name": "수호성",
        "item_level": 3335,
        "combat_score": 39187,
        "peak_combat_score": 42237,
    }
    """
    keyword = str(character_name).strip()
    if not keyword:
        raise AtoolError("캐릭터명이 비어 있습니다.")

    payload = {
        "race": safe_int(race_code),
        "server_id": safe_int(server_code),
        "keyword": keyword,
    }

    try:
        response = requests.post(
            ATOOL_SEARCH_URL,
            json=payload,
            headers=DEFAULT_HEADERS,
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        raise AtoolError(f"아툴 요청 실패: {e}") from e

    try:
        data = response.json()
    except ValueError as e:
        raise AtoolError("아툴 응답이 JSON 형식이 아닙니다.") from e

    character = _extract_character_data(data)
    if not character:
        raise AtoolError("캐릭터 정보를 찾을 수 없습니다.")

    result = normalize_character_payload(
        raw=character,
        race_code=race_code,
        race_name=race_name,
        server_code=server_code,
        server_name=server_name,
    )

    if not result["nickname"]:
        result["nickname"] = keyword

    # 핵심 값이 너무 비어 있으면 실패 처리
    if result["job_name"] == "알수없음" and result["item_level"] == 0 and result["combat_score"] == 0:
        raise AtoolError("캐릭터 조회 결과가 비어 있습니다.")

    return result
