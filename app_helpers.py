# app_helpers.py
# 신청/공대와 상관없이 공통으로 쓰는 작은 유틸 모음

#safe_int

#safe_str

#format_days

#get_race_name_by_code bot.py
def get_race_name_by_code(race_code: str) -> str | None:
    for choice in RACE_CHOICES:
        if str(choice.value) == str(race_code):
            return choice.name
    return None


#get_server_name_by_code bot.py
def get_server_name_by_code(server_code: str) -> str | None:
    for choice in SERVER_CHOICES:
        if str(choice.value) == str(server_code):
            return choice.name
    return None

  
#is_admin bot.py
def is_admin(interaction: discord.Interaction) -> bool:
    if interaction.guild is None:
        return False
    return interaction.user.guild_permissions.administrator

#split_text_by_lines
