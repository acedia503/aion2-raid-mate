from __future__ import annotations

VALID_WEEKDAYS = {"월", "화", "수", "목", "금", "토", "일"}
WEEKDAY_ORDER = ["월", "화", "수", "목", "금", "토", "일"]

WEEKDAY_OPTIONS = [
    {"name": day, "value": day}
    for day in WEEKDAY_ORDER
]

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

SERVER_OPTIONS = [
    # 천족
    {"name": "시엘 - [시엘]", "code": "1001", "race_code": "1", "race_name": "천족"},
    {"name": "네자칸 - [네자]", "code": "1002", "race_code": "1", "race_name": "천족"},
    {"name": "바이젤 - [바이]", "code": "1003", "race_code": "1", "race_name": "천족"},
    {"name": "카이시넬 - [카이]", "code": "1004", "race_code": "1", "race_name": "천족"},
    {"name": "유스티엘 - [유스]", "code": "1005", "race_code": "1", "race_name": "천족"},
    {"name": "아리엘 - [아리]", "code": "1006", "race_code": "1", "race_name": "천족"},
    {"name": "프레기온 - [프레]", "code": "1007", "race_code": "1", "race_name": "천족"},
    {"name": "메스람타에다 - [메스]", "code": "1008", "race_code": "1", "race_name": "천족"},
    {"name": "히타니에 - [히타]", "code": "1009", "race_code": "1", "race_name": "천족"},
    {"name": "나니아 - [나니]", "code": "1010", "race_code": "1", "race_name": "천족"},
    {"name": "타하바타 - [타하]", "code": "1011", "race_code": "1", "race_name": "천족"},
    {"name": "루터스 - [루터]", "code": "1012", "race_code": "1", "race_name": "천족"},
    {"name": "페르노스 - [페르]", "code": "1013", "race_code": "1", "race_name": "천족"},
    {"name": "다미누 - [다미]", "code": "1014", "race_code": "1", "race_name": "천족"},
    {"name": "카사카 - [카사]", "code": "1015", "race_code": "1", "race_name": "천족"},
    {"name": "바카르마 - [바카]", "code": "1016", "race_code": "1", "race_name": "천족"},
    {"name": "챈가룽 - [챈가]", "code": "1017", "race_code": "1", "race_name": "천족"},
    {"name": "코치룽 - [코치]", "code": "1018", "race_code": "1", "race_name": "천족"},
    {"name": "이슈타르 - [이슈]", "code": "1019", "race_code": "1", "race_name": "천족"},
    {"name": "티아마트 - [티아]", "code": "1020", "race_code": "1", "race_name": "천족"},
    {"name": "포에타 - [포에]", "code": "1021", "race_code": "1", "race_name": "천족"},

    # 마족
    {"name": "이스라펠 - [이스]", "code": "2001", "race_code": "2", "race_name": "마족"},
    {"name": "지켈 - [지켈]", "code": "2002", "race_code": "2", "race_name": "마족"},
    {"name": "트리니엘 - [트리]", "code": "2003", "race_code": "2", "race_name": "마족"},
    {"name": "루미엘 - [루미]", "code": "2004", "race_code": "2", "race_name": "마족"},
    {"name": "마르쿠탄 - [마르]", "code": "2005", "race_code": "2", "race_name": "마족"},
    {"name": "아스펠 - [아스]", "code": "2006", "race_code": "2", "race_name": "마족"},
    {"name": "에레슈키갈 - [에레]", "code": "2007", "race_code": "2", "race_name": "마족"},
    {"name": "브리트라 - [브리]", "code": "2008", "race_code": "2", "race_name": "마족"},
    {"name": "네몬 - [네몬]", "code": "2009", "race_code": "2", "race_name": "마족"},
    {"name": "하달 - [하달]", "code": "2010", "race_code": "2", "race_name": "마족"},
    {"name": "루드라 - [루드]", "code": "2011", "race_code": "2", "race_name": "마족"},
    {"name": "울고른 - [울고]", "code": "2012", "race_code": "2", "race_name": "마족"},
    {"name": "무닌 - [무닌]", "code": "2013", "race_code": "2", "race_name": "마족"},
    {"name": "오다르 - [오다]", "code": "2014", "race_code": "2", "race_name": "마족"},
    {"name": "젠카카 - [젠카]", "code": "2015", "race_code": "2", "race_name": "마족"},
    {"name": "크로메데 - [크로]", "code": "2016", "race_code": "2", "race_name": "마족"},
    {"name": "콰이링 - [콰이]", "code": "2017", "race_code": "2", "race_name": "마족"},
    {"name": "바바룽 - [바바]", "code": "2018", "race_code": "2", "race_name": "마족"},
    {"name": "파프니르 - [파프]", "code": "2019", "race_code": "2", "race_name": "마족"},
    {"name": "인드나흐 - [인드]", "code": "2020", "race_code": "2", "race_name": "마족"},
    {"name": "이스할겐 - [이스]", "code": "2021", "race_code": "2", "race_name": "마족"},
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
    "수호성": {"TANK"},
    "검성": {"TANK", "DPS"},
    "치유성": {"HEAL"},
    "호법성": {"HEAL", "DPS"},
    "궁성": {"DPS"},
    "살성": {"DPS"},
    "마도성": {"DPS"},
    "정령성": {"DPS"},
}
