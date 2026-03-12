from __future__ import annotations

VALID_WEEKDAYS = {"월", "화", "수", "목", "금", "토", "일"}
WEEKDAY_ORDER = ["월", "화", "수", "목", "금", "토", "일"]

WEEKDAY_OPTIONS = [
    {"name": day, "value": day}
    for day in WEEKDAY_ORDER
]

RACE_OPTIONS = [
    {"name": "천족", "code": "1"},
    {"name": "마족", "code": "2"},
]

SERVERS_BY_RACE: dict[str, list[dict[str, str]]] = {
    "1": [
        {"name": "시엘", "code": "1001"},
        {"name": "네자칸", "code": "1002"},
        {"name": "바이젤", "code": "1003"},
        {"name": "카이시넬", "code": "1004"},
        {"name": "유스티엘", "code": "1005"},
        {"name": "아리엘", "code": "1006"},
        {"name": "프레기온", "code": "1007"},
        {"name": "메스람타에다", "code": "1008"},
        {"name": "히타니에", "code": "1009"},
        {"name": "나니아", "code": "1010"},
        {"name": "타하바타", "code": "1011"},
        {"name": "루터스", "code": "1012"},
        {"name": "페르노스", "code": "1013"},
        {"name": "다미누", "code": "1014"},
        {"name": "카사카", "code": "1015"},
        {"name": "바카르마", "code": "1016"},
        {"name": "챈가룽", "code": "1017"},
        {"name": "코치룽", "code": "1018"},
        {"name": "이슈타르", "code": "1019"},
        {"name": "티아마트", "code": "1020"},
        {"name": "포에타", "code": "1021"},
    ],
    "2": [
        {"name": "이스라펠", "code": "2001"},
        {"name": "지켈", "code": "2002"},
        {"name": "트리니엘", "code": "2003"},
        {"name": "루미엘", "code": "2004"},
        {"name": "마르쿠탄", "code": "2005"},
        {"name": "아스펠", "code": "2006"},
        {"name": "에레슈키갈", "code": "2007"},
        {"name": "브리트라", "code": "2008"},
        {"name": "네몬", "code": "2009"},
        {"name": "하달", "code": "2010"},
        {"name": "루드라", "code": "2011"},
        {"name": "울고른", "code": "2012"},
        {"name": "무닌", "code": "2013"},
        {"name": "오다르", "code": "2014"},
        {"name": "젠카카", "code": "2015"},
        {"name": "크로메데", "code": "2016"},
        {"name": "콰이링", "code": "2017"},
        {"name": "바바룽", "code": "2018"},
        {"name": "파프니르", "code": "2019"},
        {"name": "인드나흐", "code": "2020"},
        {"name": "이스할겐", "code": "2021"},
    ],
}

SERVER_OPTIONS = [server for servers in SERVERS_BY_RACE.values() for server in servers]

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
