# constants.py
# 변하지 않는 설정값 / 선택지 / 맵핑

from __future__ import annotations


# =========================
# 요일
# =========================

VALID_WEEKDAYS = {"월", "화", "수", "목", "금", "토", "일"}

WEEKDAY_OPTIONS = [
    {"name": "월", "value": "월"},
    {"name": "화", "value": "화"},
    {"name": "수", "value": "수"},
    {"name": "목", "value": "목"},
    {"name": "금", "value": "금"},
    {"name": "토", "value": "토"},
    {"name": "일", "value": "일"},
]


# =========================
# 종족
# =========================

RACE_OPTIONS = [
    {
        "name": "천족",
        "code": "1",
        "emoji": "🪽",
        "button_style": "primary",
    },
    {
        "name": "마족",
        "code": "2",
        "emoji": "🔥",
        "button_style": "danger",
    },
]


# =========================
# 서버 정의
# =========================
# 서버는 race_code 기준으로 관리
# 1 = 천족
# 2 = 마족

SERVER_OPTIONS = [

    # ---------- 천족 ----------
    {"name": "이스라펠", "code": "1001", "race_code": "1", "race_name": "천족"},
    {"name": "티아마트", "code": "1002", "race_code": "1", "race_name": "천족"},
    {"name": "카이시넬", "code": "1003", "race_code": "1", "race_name": "천족"},
    {"name": "유스티엘", "code": "1004", "race_code": "1", "race_name": "천족"},
    {"name": "아스펠", "code": "1005", "race_code": "1", "race_name": "천족"},
    # 여기부터 천족 서버 계속 추가 (21개)

    # ---------- 마족 ----------
    {"name": "지켈", "code": "2001", "race_code": "2", "race_name": "마족"},
    {"name": "루미엘", "code": "2002", "race_code": "2", "race_name": "마족"},
    {"name": "바젤", "code": "2003", "race_code": "2", "race_name": "마족"},
    {"name": "트리니엘", "code": "2004", "race_code": "2", "race_name": "마족"},
    {"name": "네자칸", "code": "2005", "race_code": "2", "race_name": "마족"},
    # 여기부터 마족 서버 계속 추가 (21개)
]


# =========================
# 서버 lookup 캐시
# =========================

SERVER_CODE_MAP = {s["code"]: s for s in SERVER_OPTIONS}


# =========================
# 종족별 서버 목록
# =========================

SERVERS_BY_RACE: dict[str, list[dict]] = {}

for server in SERVER_OPTIONS:
    race_code = server["race_code"]
    SERVERS_BY_RACE.setdefault(race_code, []).append(server)


# =========================
# 공대 직업 설정
# =========================

ROLE_OPTIONS = [
    {"label": "ALL", "value": "ALL"},
    {"label": "TANK", "value": "TANK"},
    {"label": "DPS", "value": "DPS"},
    {"label": "HEAL", "value": "HEAL"},
]


ROLE_JOB_OPTIONS = {
    "ALL": ["수호성", "검성", "치유성", "호법성", "궁성", "살성", "마도성", "정령성"],
    "TANK": ["수호성", "검성"],
    "DPS": ["검성", "호법성", "궁성", "살성", "마도성", "정령성"],
    "HEAL": ["치유성", "호법성"],
}


JOB_ROLE_MAP = {
    "수호성": {"TANK"},
    "검성": {"TANK", "DPS"},
    "치유성": {"HEAL"},
    "호법성": {"HEAL", "DPS"},
    "궁성": {"DPS"},
    "살성": {"DPS"},
    "마도성": {"DPS"},
    "정령성": {"DPS"},
}
