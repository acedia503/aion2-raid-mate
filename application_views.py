# application_views.py
# 신청 관련 UI

from __future__ import annotations

import discord

from app_helpers import get_servers_for_race, format_days
from constants import RACE_OPTIONS, WEEKDAY_OPTIONS


# =========================================================
# 종족/서버 선택
# =========================================================

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
# 종족 선택
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

# =========================================================
# 서버 선택
# =========================================================

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


# =========================================================
# 요일 및 특이사항 입력
# =========================================================

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
        days_text = format_days(self.selected_days)
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
# 요일 멀티 선택
# =========================================================

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
