# views.py
from __future__ import annotations

import discord

from storage import upsert_guild_setting

# =========================================================
# 아이온2 종족 / 서버 데이터
# =========================================================

RACE_OPTIONS = [
    {"name": "천족", "code": "1"},
    {"name": "마족", "code": "2"},
]

# 예시 서버 데이터
# 실제 사용하는 서버명/코드로 바꿔서 쓰면 됨
SERVER_OPTIONS = [
    {"name": "루", "code": "1001"},
    {"name": "시엘", "code": "1002"},
    {"name": "이스라펠", "code": "1003"},
    {"name": "진", "code": "2019"},
    {"name": "트리니엘", "code": "2020"},
    {"name": "카이시넬", "code": "2021"},
]


# =========================================================
# 요일 선택 데이터
# =========================================================

WEEKDAY_OPTIONS = [
    discord.SelectOption(label="월", value="월"),
    discord.SelectOption(label="화", value="화"),
    discord.SelectOption(label="수", value="수"),
    discord.SelectOption(label="목", value="목"),
    discord.SelectOption(label="금", value="금"),
    discord.SelectOption(label="토", value="토"),
    discord.SelectOption(label="일", value="일"),
]


# =========================================================
# 직업군/직업 데이터
# =========================================================

ROLE_OPTIONS = [
    discord.SelectOption(label="ALL", value="ALL"),
    discord.SelectOption(label="TANK", value="TANK"),
    discord.SelectOption(label="DPS", value="DPS"),
    discord.SelectOption(label="HEAL", value="HEAL"),
]

ROLE_JOB_OPTIONS = {
    "ALL": [
        discord.SelectOption(label="수호성", value="수호성"),
        discord.SelectOption(label="검성", value="검성"),
        discord.SelectOption(label="치유성", value="치유성"),
        discord.SelectOption(label="호법성", value="호법성"),
        discord.SelectOption(label="궁성", value="궁성"),
        discord.SelectOption(label="살성", value="살성"),
        discord.SelectOption(label="마도성", value="마도성"),
        discord.SelectOption(label="정령성", value="정령성"),
    ],
    "TANK": [
        discord.SelectOption(label="수호성", value="수호성"),
        discord.SelectOption(label="검성", value="검성"),
    ],
    "DPS": [
        discord.SelectOption(label="검성", value="검성"),
        discord.SelectOption(label="호법성", value="호법성"),
        discord.SelectOption(label="궁성", value="궁성"),
        discord.SelectOption(label="살성", value="살성"),
        discord.SelectOption(label="마도성", value="마도성"),
        discord.SelectOption(label="정령성", value="정령성"),
    ],
    "HEAL": [
        discord.SelectOption(label="치유성", value="치유성"),
        discord.SelectOption(label="호법성", value="호법성"),
    ],
}


def get_servers_for_race(race_code: str) -> list[dict]:
    return [server for server in SERVER_OPTIONS if str(server["code"]).startswith(str(race_code))]


class RaceSelect(discord.ui.Select):
    def __init__(self, parent_view: "GuildSettingView"):
        self.parent_view = parent_view

        options = [
            discord.SelectOption(label=race["name"], value=race["code"])
            for race in RACE_OPTIONS
        ]

        super().__init__(
            placeholder="아이온2 종족을 선택하세요",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent_view.user_id:
            await interaction.response.send_message(
                "이 설정 UI는 명령어를 실행한 관리자만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return

        selected_code = self.values[0]
        selected_race = next((r for r in RACE_OPTIONS if r["code"] == selected_code), None)

        if selected_race is None:
            await interaction.response.send_message(
                "선택한 종족 정보를 찾을 수 없습니다.",
                ephemeral=True,
            )
            return

        self.parent_view.selected_race_code = selected_race["code"]
        self.parent_view.selected_race_name = selected_race["name"]

        # 종족 바꾸면 서버 선택값 초기화
        self.parent_view.selected_server_code = None
        self.parent_view.selected_server_name = None

        # 서버 select 갱신
        self.parent_view.refresh_server_select()

        await interaction.response.edit_message(
            content=(
                f"종족: **{self.parent_view.selected_race_name}** 선택됨\n"
                "이제 종족 서버를 선택하세요."
            ),
            view=self.parent_view,
        )


class ServerSelect(discord.ui.Select):
    def __init__(self, parent_view: "GuildSettingView", race_code: str):
        self.parent_view = parent_view
        servers = get_servers_for_race(race_code)

        options = [
            discord.SelectOption(label=server["name"], value=server["code"])
            for server in servers
        ]

        super().__init__(
            placeholder="아이온2 종족 서버를 선택하세요",
            min_values=1,
            max_values=1,
            options=options,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent_view.user_id:
            await interaction.response.send_message(
                "이 설정 UI는 명령어를 실행한 관리자만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return

        selected_code = self.values[0]
        servers = get_servers_for_race(self.parent_view.selected_race_code or "")
        selected_server = next((s for s in servers if s["code"] == selected_code), None)

        if selected_server is None:
            await interaction.response.send_message(
                "선택한 서버 정보를 찾을 수 없습니다.",
                ephemeral=True,
            )
            return

        self.parent_view.selected_server_code = selected_server["code"]
        self.parent_view.selected_server_name = selected_server["name"]

        await interaction.response.edit_message(
            content=(
                f"종족: **{self.parent_view.selected_race_name}**\n"
                f"종족 서버: **{self.parent_view.selected_server_name}**\n"
                "저장 버튼을 눌러 설정을 저장하세요."
            ),
            view=self.parent_view,
        )


class GuildSettingView(discord.ui.View):
    def __init__(self, guild_id: int, user_id: int):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self.user_id = user_id

        self.selected_race_code: str | None = None
        self.selected_race_name: str | None = None
        self.selected_server_code: str | None = None
        self.selected_server_name: str | None = None

        self.race_select = RaceSelect(self)
        self.server_select: ServerSelect | None = None

        self.add_item(self.race_select)

    def refresh_server_select(self) -> None:
        if self.server_select is not None:
            self.remove_item(self.server_select)
            self.server_select = None

        if self.selected_race_code:
            self.server_select = ServerSelect(self, self.selected_race_code)
            self.add_item(self.server_select)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "이 설정 UI는 명령어를 실행한 관리자만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True

    @discord.ui.button(label="저장", style=discord.ButtonStyle.success, row=2)
    async def save_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_race_code or not self.selected_server_code:
            await interaction.response.send_message(
                "종족과 종족 서버를 모두 선택한 뒤 저장하세요.",
                ephemeral=True,
            )
            return

        try:
            upsert_guild_setting(
                guild_id=self.guild_id,
                race_code=self.selected_race_code,
                race_name=self.selected_race_name or "",
                server_code=self.selected_server_code,
                server_name=self.selected_server_name or "",
                updated_by=interaction.user.id,
            )

            for item in self.children:
                item.disabled = True

            await interaction.response.edit_message(
                content=(
                    "기본 설정이 저장되었습니다.\n"
                    f"- 종족: **{self.selected_race_name}**\n"
                    f"- 종족 서버: **{self.selected_server_name}**"
                ),
                view=self,
            )
        except Exception as e:
            await interaction.response.send_message(
                f"설정 저장 중 오류가 발생했습니다.\n`{e}`",
                ephemeral=True,
            )

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary, row=2)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content="설정이 취소되었습니다.",
            view=self,
        )


# =========================================================
# 신청/공대 삭제용
# =========================================================

class RaidDeleteConfirmView(discord.ui.View):
    def __init__(self, guild_id: int, raid_name: str, user_id: int):
        super().__init__(timeout=120)
        self.guild_id = guild_id
        self.raid_name = raid_name
        self.user_id = user_id
        self.value: str | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "이 삭제 확인 UI는 명령어를 실행한 관리자만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True

    @discord.ui.button(label="신청자까지 같이 삭제", style=discord.ButtonStyle.danger)
    async def delete_with_applications(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        self.value = "delete_with_applications"
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            content=f"`{self.raid_name}` 레이드를 신청 내역/공대 내역과 함께 삭제합니다.",
            view=self,
        )
        self.stop()

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary)
    async def cancel_delete(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        self.value = "cancel"
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            content="레이드 삭제가 취소되었습니다.",
            view=self,
        )
        self.stop()


# =========================================================
# 특이사항 입력
# =========================================================

class ApplicationNoteModal(discord.ui.Modal, title="특이사항 입력"):
    특이사항 = discord.ui.TextInput(
        label="특이사항",
        placeholder="예: 평일 22시 이후 가능 / 트라이팟 가능",
        required=False,
        max_length=300,
        style=discord.TextStyle.paragraph,
    )

    def __init__(self, parent_view: "WeekdayMultiSelectView"):
        super().__init__()
        self.parent_view = parent_view

        if parent_view.note:
            self.특이사항.default = parent_view.note

    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.parent_view.note = str(self.특이사항.value).strip()
        self.parent_view.value = "submit_with_note"

        for item in self.parent_view.children:
            item.disabled = True

        await interaction.response.edit_message(
            content=self.parent_view.build_summary_text(saved=False, note_entered=True),
            view=self.parent_view,
        )
        self.parent_view.stop()


class WeekdaySelect(discord.ui.Select):
    def __init__(self, parent_view: "WeekdayMultiSelectView"):
        self.parent_view = parent_view

        super().__init__(
            placeholder="가능 요일을 선택하세요 (중복 선택 가능)",
            min_values=1,
            max_values=7,
            options=WEEKDAY_OPTIONS,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent_view.user_id:
            await interaction.response.send_message(
                "이 신청 UI는 명령어를 실행한 사용자만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return

        self.parent_view.selected_days = list(self.values)

        await interaction.response.edit_message(
            content=self.parent_view.build_summary_text(saved=False, note_entered=bool(self.parent_view.note)),
            view=self.parent_view,
        )


class WeekdayMultiSelectView(discord.ui.View):
    def __init__(
        self,
        user_id: int,
        initial_days: list[str] | None = None,
        initial_note: str | None = None,
    ):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.selected_days: list[str] = initial_days[:] if initial_days else []
        self.note: str = (initial_note or "").strip()

        # 결과 상태
        self.value: str | None = None
        # "submit" / "submit_with_note" / "cancel"

        self.weekday_select = WeekdaySelect(self)

        if self.selected_days:
            self.weekday_select.default_values = self.selected_days

        self.add_item(self.weekday_select)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "이 신청 UI는 명령어를 실행한 사용자만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True

    def build_summary_text(self, saved: bool = False, note_entered: bool = False) -> str:
        days_text = ", ".join(self.selected_days) if self.selected_days else "-"
        note_text = self.note if self.note else "-"

        if saved:
            return (
                "신청 입력이 완료되었습니다.\n"
                f"- 가능 요일: {days_text}\n"
                f"- 특이사항: {note_text}"
            )

        if not self.selected_days:
            return "가능 요일을 선택하세요."

        if note_entered:
            return (
                "가능 요일이 선택되었습니다.\n"
                f"- 가능 요일: {days_text}\n"
                f"- 특이사항: {note_text}\n"
                "저장 버튼을 누르면 완료됩니다."
            )

        return (
            "가능 요일이 선택되었습니다.\n"
            f"- 가능 요일: {days_text}\n"
            "특이사항을 입력하거나, 바로 저장할 수 있습니다."
        )

    @discord.ui.button(label="특이사항 입력", style=discord.ButtonStyle.primary, row=1)
    async def open_note_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_days:
            await interaction.response.send_message(
                "먼저 가능 요일을 선택하세요.",
                ephemeral=True,
            )
            return

        await interaction.response.send_modal(ApplicationNoteModal(self))

    @discord.ui.button(label="바로 저장", style=discord.ButtonStyle.success, row=1)
    async def submit_without_note(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_days:
            await interaction.response.send_message(
                "먼저 가능 요일을 선택하세요.",
                ephemeral=True,
            )
            return

        self.value = "submit"

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content=self.build_summary_text(saved=True, note_entered=bool(self.note)),
            view=self,
        )
        self.stop()

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary, row=1)
    async def cancel_input(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "cancel"

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content="신청 입력이 취소되었습니다.",
            view=self,
        )
        self.stop()

        
# =========================================================
# 신청용 종족/서버 선택 UI
# =========================================================

class ApplicationRaceSelect(discord.ui.Select):
    def __init__(self, parent_view: "ApplicationRaceServerView"):
        self.parent_view = parent_view

        options = [
            discord.SelectOption(label=race["name"], value=race["code"])
            for race in RACE_OPTIONS
        ]

        super().__init__(
            placeholder="아이온2 종족을 선택하세요",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent_view.user_id:
            await interaction.response.send_message(
                "이 UI는 명령어를 실행한 사용자만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return

        selected_code = self.values[0]
        selected_race = next((r for r in RACE_OPTIONS if r["code"] == selected_code), None)
        if selected_race is None:
            await interaction.response.send_message(
                "선택한 종족 정보를 찾을 수 없습니다.",
                ephemeral=True,
            )
            return

        self.parent_view.selected_race_code = selected_race["code"]
        self.parent_view.selected_race_name = selected_race["name"]

        self.parent_view.selected_server_code = None
        self.parent_view.selected_server_name = None
        self.parent_view.refresh_server_select()

        await interaction.response.edit_message(
            content=(
                f"종족: **{self.parent_view.selected_race_name}** 선택됨\n"
                "이제 종족 서버를 선택하세요."
            ),
            view=self.parent_view,
        )


class ApplicationServerSelect(discord.ui.Select):
    def __init__(self, parent_view: "ApplicationRaceServerView", race_code: str):
        self.parent_view = parent_view
        servers = get_servers_for_race(race_code)

        options = [
            discord.SelectOption(label=server["name"], value=server["code"])
            for server in servers
        ]

        super().__init__(
            placeholder="아이온2 종족 서버를 선택하세요",
            min_values=1,
            max_values=1,
            options=options,
            row=1,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent_view.user_id:
            await interaction.response.send_message(
                "이 UI는 명령어를 실행한 사용자만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return

        selected_code = self.values[0]
        servers = get_servers_for_race(self.parent_view.selected_race_code or "")
        selected_server = next((s for s in servers if s["code"] == selected_code), None)

        if selected_server is None:
            await interaction.response.send_message(
                "선택한 서버 정보를 찾을 수 없습니다.",
                ephemeral=True,
            )
            return

        self.parent_view.selected_server_code = selected_server["code"]
        self.parent_view.selected_server_name = selected_server["name"]

        await interaction.response.edit_message(
            content=(
                f"종족: **{self.parent_view.selected_race_name}**\n"
                f"종족 서버: **{self.parent_view.selected_server_name}**\n"
                "확인 버튼을 누르면 계속 진행합니다."
            ),
            view=self.parent_view,
        )


class ApplicationRaceServerView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=180)
        self.user_id = user_id

        self.selected_race_code: str | None = None
        self.selected_race_name: str | None = None
        self.selected_server_code: str | None = None
        self.selected_server_name: str | None = None

        self.value: str | None = None
        # "submit" / "cancel"

        self.race_select = ApplicationRaceSelect(self)
        self.server_select: ApplicationServerSelect | None = None

        self.add_item(self.race_select)

    def refresh_server_select(self) -> None:
        if self.server_select is not None:
            self.remove_item(self.server_select)
            self.server_select = None

        if self.selected_race_code:
            self.server_select = ApplicationServerSelect(self, self.selected_race_code)
            self.add_item(self.server_select)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "이 UI는 명령어를 실행한 사용자만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True

    @discord.ui.button(label="확인", style=discord.ButtonStyle.success, row=2)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_race_code or not self.selected_server_code:
            await interaction.response.send_message(
                "종족과 종족 서버를 모두 선택하세요.",
                ephemeral=True,
            )
            return

        self.value = "submit"
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content=(
                "종족/종족 서버 선택이 완료되었습니다.\n"
                f"- 종족: **{self.selected_race_name}**\n"
                f"- 종족 서버: **{self.selected_server_name}**"
            ),
            view=self,
        )
        self.stop()

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary, row=2)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "cancel"
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content="종족/종족 서버 선택이 취소되었습니다.",
            view=self,
        )
        self.stop()

        
# =========================================================
# 같은 캐릭터명이 여러 종족/서버로 있을 때 선택
# =========================================================
class ForceDeleteRaceServerSelect(discord.ui.Select):
    def __init__(self, parent_view: "ForceDeleteRaceServerView", applications: list[dict]):
        self.parent_view = parent_view
        self.applications = applications

        options: list[discord.SelectOption] = []
        for app in applications[:25]:
            days = app.get("available_days") or []
            days_text = ", ".join(days) if days else "-"
            description = (
                f"{app['race_name']} / {app['server_name']} | "
                f"{app['job_name']} | {days_text}"
            )
            options.append(
                discord.SelectOption(
                    label=f"{app['race_name']} / {app['server_name']}"[:100],
                    value=str(app["id"]),
                    description=description[:100],
                )
            )

        super().__init__(
            placeholder="삭제할 종족/서버를 선택하세요",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent_view.user_id:
            await interaction.response.send_message(
                "이 UI는 명령어를 실행한 관리자만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return

        selected_id = int(self.values[0])
        selected_app = next(
            (app for app in self.applications if int(app["id"]) == selected_id),
            None,
        )

        if selected_app is None:
            await interaction.response.send_message(
                "선택한 신청 내역을 찾을 수 없습니다.",
                ephemeral=True,
            )
            return

        self.parent_view.selected_application = selected_app
        self.parent_view.value = "submit"

        for item in self.parent_view.children:
            item.disabled = True

        await interaction.response.edit_message(
            content=(
                "삭제할 신청 내역이 선택되었습니다.\n"
                f"- 레이드: **{selected_app['raid_name']}**\n"
                f"- 캐릭터: **{selected_app['character_name']}**\n"
                f"- 종족/서버: **{selected_app['race_name']} / {selected_app['server_name']}**\n"
                f"- 신청자: **{selected_app['user_name']}**"
            ),
            view=self.parent_view,
        )
        self.parent_view.stop()


class ForceDeleteRaceServerView(discord.ui.View):
    def __init__(self, user_id: int, applications: list[dict]):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.applications = applications

        self.value: str | None = None
        self.selected_application: dict | None = None

        self.add_item(ForceDeleteRaceServerSelect(self, applications))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "이 UI는 명령어를 실행한 관리자만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary, row=1)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "cancel"

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content="강제삭제가 취소되었습니다.",
            view=self,
        )
        self.stop()


# =========================================================
# 공
# =========================================================

class PartyConfirmVisibilityView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.value: str | None = None
        # "private" / "public" / "cancel"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "이 UI는 명령어를 실행한 관리자만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True

    @discord.ui.button(label="나만 보기", style=discord.ButtonStyle.secondary)
    async def private_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "private"
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content="공대 확인 결과를 나만 보기로 표시합니다.",
            view=self,
        )
        self.stop()

    @discord.ui.button(label="공개", style=discord.ButtonStyle.primary)
    async def public_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "public"
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content="공대 확인 결과를 공개로 표시합니다.",
            view=self,
        )
        self.stop()

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "cancel"
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content="공대 확인이 취소되었습니다.",
            view=self,
        )
        self.stop()


# =========================================================
# 슬롯별 역할 선택 Select
# =========================================================

class PartyRuleRoleSelect(discord.ui.Select):
    def __init__(self, parent_view: "PartyRuleSetupView", slot_index: int):
        self.parent_view = parent_view
        self.slot_index = slot_index

        current_role = parent_view.slot_rules[slot_index]["role_type"]

        options = []
        for option in ROLE_OPTIONS:
            options.append(
                discord.SelectOption(
                    label=option.label,
                    value=option.value,
                    default=(option.value == current_role),
                )
            )

        party_no = 1 if slot_index <= 4 else 2
        slot_no = slot_index if slot_index <= 4 else slot_index - 4

        super().__init__(
            placeholder=f"{party_no}파티 {slot_no}번 역할 선택",
            min_values=1,
            max_values=1,
            options=options,
            row=(slot_index - 1) % 5,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent_view.user_id:
            await interaction.response.send_message(
                "이 UI는 명령어를 실행한 관리자만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return

        selected_role = self.values[0]
        self.parent_view.slot_rules[self.slot_index]["role_type"] = selected_role
        self.parent_view.slot_rules[self.slot_index]["preferred_jobs"] = []

        await interaction.response.edit_message(
            content=self.parent_view.build_summary_text(),
            view=self.parent_view,
        )


# =========================================================
# 슬롯별 선호 직업 선택 Select
# =========================================================

class PartyRuleJobSelect(discord.ui.Select):
    def __init__(self, parent_view: "PartyRuleSetupView", slot_index: int):
        self.parent_view = parent_view
        self.slot_index = slot_index

        current_role = parent_view.slot_rules[slot_index]["role_type"]
        current_jobs = set(parent_view.slot_rules[slot_index]["preferred_jobs"])

        options = []
        for option in ROLE_JOB_OPTIONS.get(current_role, []):
            options.append(
                discord.SelectOption(
                    label=option.label,
                    value=option.value,
                    default=(option.value in current_jobs),
                )
            )

        party_no = 1 if slot_index <= 4 else 2
        slot_no = slot_index if slot_index <= 4 else slot_index - 4

        super().__init__(
            placeholder=f"{party_no}파티 {slot_no}번 선호 직업 선택",
            min_values=0,
            max_values=max(1, len(options)),
            options=options[:25],
            row=((slot_index - 1) % 5),
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent_view.user_id:
            await interaction.response.send_message(
                "이 UI는 명령어를 실행한 관리자만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return

        self.parent_view.slot_rules[self.slot_index]["preferred_jobs"] = list(self.values)

        await interaction.response.edit_message(
            content=self.parent_view.build_summary_text(),
            view=self.parent_view,
        )


# =========================================================
# 공대 생성 규칙 설정 UI
# =========================================================

class PartyRuleSetupView(discord.ui.View):
    def __init__(self, user_id: int, initial_rules: list[dict] | None = None):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.page = 1
        self.value: str | None = None
        self.exported_rules: list[dict] | None = None

        self.slot_rules: dict[int, dict] = {
            i: {
                "slot_index": i,
                "role_type": "ALL",
                "preferred_jobs": [],
            }
            for i in range(1, 9)
        }

        if initial_rules:
            for rule in initial_rules:
                slot_index = int(rule["slot_index"])
                self.slot_rules[slot_index] = {
                    "slot_index": slot_index,
                    "role_type": str(rule.get("role_type", "ALL")).upper(),
                    "preferred_jobs": list(rule.get("preferred_jobs", [])),
                }

        self.refresh_components()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "이 UI는 명령어를 실행한 관리자만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True

    def current_slot_range(self) -> range:
        return range(1, 5) if self.page == 1 else range(5, 9)

    def build_summary_text(self) -> str:
        lines = []
        lines.append("공대 생성 규칙 설정")
        lines.append("")

        lines.append("1파티")
        for slot_index in range(1, 5):
            rule = self.slot_rules[slot_index]
            jobs = ", ".join(rule["preferred_jobs"]) if rule["preferred_jobs"] else "-"
            lines.append(
                f"  {slot_index}번 | {rule['role_type']} | 선호 직업: {jobs}"
            )

        lines.append("")
        lines.append("2파티")
        for slot_index in range(5, 9):
            rule = self.slot_rules[slot_index]
            jobs = ", ".join(rule["preferred_jobs"]) if rule["preferred_jobs"] else "-"
            lines.append(
                f"  {slot_index - 4}번 | {rule['role_type']} | 선호 직업: {jobs}"
            )

        lines.append("")
        lines.append(f"현재 페이지: {self.page}/2")
        return "\n".join(lines)

    def refresh_components(self) -> None:
        self.clear_items()

        for slot_index in self.current_slot_range():
            self.add_item(PartyRuleRoleSelect(self, slot_index))
            self.add_item(PartyRuleJobSelect(self, slot_index))

        self.add_item(self.prev_button)
        self.add_item(self.next_button)
        self.add_item(self.save_button)
        self.add_item(self.cancel_button)

    def export_rules(self) -> list[dict]:
        return [
            {
                "slot_index": i,
                "role_type": self.slot_rules[i]["role_type"],
                "preferred_jobs": list(self.slot_rules[i]["preferred_jobs"]),
            }
            for i in range(1, 9)
        ]

    @discord.ui.button(label="이전", style=discord.ButtonStyle.secondary, row=4)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 1:
            self.page -= 1
        self.refresh_components()
        await interaction.response.edit_message(
            content=self.build_summary_text(),
            view=self,
        )

    @discord.ui.button(label="다음", style=discord.ButtonStyle.secondary, row=4)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < 2:
            self.page += 1
        self.refresh_components()
        await interaction.response.edit_message(
            content=self.build_summary_text(),
            view=self,
        )

    @discord.ui.button(label="저장", style=discord.ButtonStyle.success, row=4)
    async def save_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "submit"
        self.exported_rules = self.export_rules()

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content="공대 생성 규칙이 저장되었습니다.",
            view=self,
        )
        self.stop()

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary, row=4)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "cancel"

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content="공대 생성 규칙 설정이 취소되었습니다.",
            view=self,
        )
        self.stop()
