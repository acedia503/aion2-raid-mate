# constants.py
# 변하지 않는 설정값/선택지/맵핑

from __future__ import annotations

VALID_WEEKDAYS = {"월", "화", "수", "목", "금", "토", "일"}

RACE_OPTIONS = [
    {"name": "천족", "code": "1"},
    {"name": "마족", "code": "2"},
]

SERVER_OPTIONS = [
    {"name": "루", "code": "1001"},
    {"name": "시엘", "code": "1002"},
    {"name": "이스라펠", "code": "1003"},
    {"name": "진", "code": "2019"},
    {"name": "트리니엘", "code": "2020"},
    {"name": "카이시넬", "code": "2021"},
]

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
    "수호성": {"TANK", "DPS"},
    "검성": {"TANK", "DPS"},
    "치유성": {"HEAL"},
    "호법성": {"HEAL", "DPS"},
    "궁성": {"DPS"},
    "살성": {"DPS"},
    "마도성": {"DPS"},
    "정령성": {"DPS"},
}
