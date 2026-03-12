from __future__ import annotations

import threading
import time
from typing import Any

import requests

from app_helpers import safe_int

ATOOL_SEARCH_URL = "https://www.aion2tool.com/api/character/search"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": "https://www.aion2tool.com",
    "Referer": "https://www.aion2tool.com/",
}
ATOOL_CACHE_TTL_SECONDS = 60
ATOOL_MIN_REQUEST_INTERVAL_SECONDS = 0.6
ATOOL_MAX_RETRIES = 3
ATOOL_RETRY_BACKOFF_SECONDS = 1.2

_session = requests.Session()
_request_lock = threading.Lock()
_cache_lock = threading.Lock()
_last_request_at = 0.0
_CACHE: dict[tuple[str, str, str], tuple[float, dict[str, Any]]] = {}


class AtoolError(Exception):
    pass


def make_cache_key(race_code: str | int, server_code: str | int, character_name: str) -> tuple[str, str, str]:
    return (str(race_code).strip(), str(server_code).strip(), str(character_name).strip().lower())


def get_cached_character_info(race_code: str | int, server_code: str | int, character_name: str) -> dict[str, Any] | None:
    key = make_cache_key(race_code, server_code, character_name)
    now = time.monotonic()
    with _cache_lock:
        cached = _CACHE.get(key)
        if not cached:
            return None
        saved_at, value = cached
        if now - saved_at > ATOOL_CACHE_TTL_SECONDS:
            _CACHE.pop(key, None)
            return None
        return dict(value)


def set_cached_character_info(race_code: str | int, server_code: str | int, character_name: str, value: dict[str, Any]) -> None:
    with _cache_lock:
        _CACHE[make_cache_key(race_code, server_code, character_name)] = (time.monotonic(), dict(value))


def clear_expired_cache() -> None:
    now = time.monotonic()
    with _cache_lock:
        for key, (saved_at, _) in list(_CACHE.items()):
            if now - saved_at > ATOOL_CACHE_TTL_SECONDS:
                _CACHE.pop(key, None)


def normalize_character_payload(raw: dict[str, Any], race_code: str | int, race_name: str, server_code: str | int, server_name: str) -> dict[str, Any]:
    return {
        "race_code": str(race_code),
        "race_name": str(race_name).strip(),
        "server_code": str(server_code),
        "server_name": str(server_name).strip(),
        "nickname": str(raw.get("nickname", "")).strip(),
        "job_name": str(raw.get("job", "")).strip() or "알수없음",
        "item_level": safe_int(raw.get("combat_power", 0)),
        "combat_score": safe_int(raw.get("combat_score", 0)),
        "peak_combat_score": safe_int(raw.get("max_combat_score", raw.get("peak_combat_score", raw.get("combat_score", 0)))),
    }


def _extract_character_data(data: Any) -> dict[str, Any] | None:
    if isinstance(data, dict):
        if any(key in data for key in ("job", "combat_power", "combat_score")):
            return data
        for key in ("data", "result", "character"):
            value = data.get(key)
            if isinstance(value, dict) and any(k in value for k in ("job", "combat_power", "combat_score")):
                return value
        for key in ("data", "results", "characters", "items", "list"):
            value = data.get(key)
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return value[0]
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    return None


def _wait_for_global_rate_limit() -> None:
    global _last_request_at
    with _request_lock:
        now = time.monotonic()
        elapsed = now - _last_request_at
        if elapsed < ATOOL_MIN_REQUEST_INTERVAL_SECONDS:
            time.sleep(ATOOL_MIN_REQUEST_INTERVAL_SECONDS - elapsed)
        _last_request_at = time.monotonic()


def _do_post(payload: dict[str, Any], timeout: int) -> requests.Response:
    _wait_for_global_rate_limit()
    return _session.post(ATOOL_SEARCH_URL, json=payload, headers=DEFAULT_HEADERS, timeout=timeout)


def get_character_info(race_code: str | int, race_name: str, server_code: str | int, server_name: str, character_name: str, timeout: int = 15, use_cache: bool = True) -> dict[str, Any]:
    keyword = str(character_name).strip()
    if not keyword:
        raise AtoolError("캐릭터명이 비어 있습니다.")
    if use_cache:
        cached = get_cached_character_info(race_code, server_code, keyword)
        if cached is not None:
            return cached

    payload = {"race": safe_int(race_code), "server_id": safe_int(server_code), "keyword": keyword}
    last_error: Exception | None = None

    for attempt in range(1, ATOOL_MAX_RETRIES + 1):
        try:
            response = _do_post(payload, timeout)
            if response.status_code == 429 or 500 <= response.status_code < 600:
                raise requests.HTTPError(f"{response.status_code} Server/RateLimit Error", response=response)
            response.raise_for_status()
            try:
                data = response.json()
            except ValueError as e:
                raise AtoolError("아툴 응답이 JSON 형식이 아닙니다.") from e

            character = _extract_character_data(data)
            if not character:
                raise AtoolError("캐릭터 정보를 찾을 수 없습니다.")

            result = normalize_character_payload(character, race_code, race_name, server_code, server_name)
            if not result["nickname"]:
                result["nickname"] = keyword
            if result["job_name"] == "알수없음" and result["item_level"] == 0 and result["combat_score"] == 0:
                raise AtoolError("캐릭터 조회 결과가 비어 있습니다.")
            if use_cache:
                set_cached_character_info(race_code, server_code, keyword, result)
                clear_expired_cache()
            return result
        except requests.HTTPError as e:
            last_error = e
            status_code = getattr(e.response, "status_code", None)
            if attempt >= ATOOL_MAX_RETRIES:
                if status_code == 429:
                    raise AtoolError("아툴 호출이 일시적으로 많습니다. 잠시 후 다시 시도해주세요.") from e
                raise AtoolError(f"아툴 요청 실패: HTTP {status_code}") from e
            time.sleep(ATOOL_RETRY_BACKOFF_SECONDS * attempt)
        except requests.RequestException as e:
            last_error = e
            if attempt >= ATOOL_MAX_RETRIES:
                raise AtoolError(f"아툴 요청 실패: {e}") from e
            time.sleep(ATOOL_RETRY_BACKOFF_SECONDS * attempt)

    raise AtoolError(f"아툴 요청 실패: {last_error}")
