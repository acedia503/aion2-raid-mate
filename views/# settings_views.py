# settings_views.py
# 관리자가 사전 설정하는 부분 UI

from __future__ import annotations

import discord

from constants import RACE_OPTIONS
from app_helpers import get_servers_for_race
from storage import upsert_guild_setting


# =========================================================
# 종족 버튼
# =========================================================

class SettingRaceButton(discord.ui.Button):
    def __init__(self, parent_view: "GuildSettingView", race_option: dict):
        style_map = {
            "primary": discord.ButtonStyle.primary,
            "danger": discord.ButtonStyle.danger,
            "secondary": discord.ButtonStyle.secondary,
            "success": discord.ButtonStyle.success,
        }

        super().__init__(
            label=str(race_option["name"]),
            emoji=race_option.get("emoji"),
            style=style_map.get(str(race_option.get("button_style", "primary")), discord.ButtonStyle.primary),
            row=0,
        )

        self.parent_view = parent_view
        self.race_option = race_option

    async def callback(self, interaction: discord.Interaction):

        if interaction.user.id != self.parent_view.user_id:
            await interaction.response.send_message(
                "이 설정 UI는 명령어를 실행한 관리자만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return

        self.parent_view.selected_race_code = str(self.race_option["code"])
        self.parent_view.selected_race_name = str(self.race_option["name"])

        # 종족 변경 시 서버 초기화
        self.parent_view.selected_server_code = None
        self.parent_view.selected_server_name = None

        self.parent_view.refresh_server_select()

        await interaction.response.edit_message(
            content=(
                f"종족: **{self.parent_view.selected_race_name}** 선택됨\n"
                "이제 서버를 선택하세요."
            ),
            view=self.parent_view,
        )


# =========================================================
# 서버 선택
# =========================================================

class SettingServerSelect(discord.ui.Select):

    def __init__(self, parent_view: "GuildSettingView", race_code: str):

        self.parent_view = parent_view
        servers = get_servers_for_race(race_code)

        options = [
            discord.SelectOption(
                label=str(server["name"])[:100],
                value=str(server["code"]),
            )
            for server in servers[:25]
        ]

        super().__init__(
            placeholder="아이온2 서버를 선택하세요",
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

        selected_server = next(
            (s for s in servers if str(s["code"]) == str(selected_code)),
            None,
        )

        if selected_server is None:
            await interaction.response.send_message(
                "선택한 서버 정보를 찾을 수 없습니다.",
                ephemeral=True,
            )
            return

        self.parent_view.selected_server_code = str(selected_server["code"])
        self.parent_view.selected_server_name = str(selected_server["name"])

        await interaction.response.edit_message(
            content=(
                f"종족: **{self.parent_view.selected_race_name}**\n"
                f"서버: **{self.parent_view.selected_server_name}**\n"
                "저장 버튼을 눌러 설정을 저장하세요."
            ),
            view=self.parent_view,
        )


# =========================================================
# 설정 View
# =========================================================

class GuildSettingView(discord.ui.View):

    def __init__(self, guild_id: int, user_id: int):

        super().__init__(timeout=180)

        self.guild_id = guild_id
        self.user_id = user_id

        self.selected_race_code: str | None = None
        self.selected_race_name: str | None = None

        self.selected_server_code: str | None = None
        self.selected_server_name: str | None = None

        self.server_select: SettingServerSelect | None = None

        # 종족 버튼 추가
        for race in RACE_OPTIONS:
            self.add_item(SettingRaceButton(self, race))

    # -------------------------

    def refresh_server_select(self):

        if self.server_select is not None:
            self.remove_item(self.server_select)
            self.server_select = None

        if self.selected_race_code:
            self.server_select = SettingServerSelect(self, self.selected_race_code)
            self.add_item(self.server_select)

    # -------------------------

    async def interaction_check(self, interaction: discord.Interaction) -> bool:

        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "이 설정 UI는 명령어를 실행한 관리자만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return False

        return True

    # -------------------------

    async def on_timeout(self):

        for item in self.children:
            item.disabled = True

        self.stop()

    # =========================================================
    # 저장
    # =========================================================

    @discord.ui.button(label="저장", style=discord.ButtonStyle.success, row=2)
    async def save_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not self.selected_race_code or not self.selected_server_code:
            await interaction.response.send_message(
                "종족과 서버를 모두 선택하세요.",
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
                    f"- 서버: **{self.selected_server_name}**"
                ),
                view=self,
            )

            self.stop()

        except Exception as e:

            await interaction.response.send_message(
                f"설정 저장 중 오류가 발생했습니다.\n`{e}`",
                ephemeral=True,
            )

    # =========================================================
    # 취소
    # =========================================================

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary, row=2)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content="설정이 취소되었습니다.",
            view=self,
        )

        self.stop()


# =========================================================
# 레이드 삭제 확인
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

    async def on_timeout(self):

        for item in self.children:
            item.disabled = True

        self.stop()

    @discord.ui.button(label="신청자까지 같이 삭제", style=discord.ButtonStyle.danger)
    async def delete_with_applications(self, interaction: discord.Interaction, button: discord.ui.Button):

        self.value = "delete_with_applications"

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content=f"`{self.raid_name}` 레이드를 신청 내역/공대 내역과 함께 삭제합니다.",
            view=self,
        )

        self.stop()

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary)
    async def cancel_delete(self, interaction: discord.Interaction, button: discord.ui.Button):

        self.value = "cancel"

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content="레이드 삭제가 취소되었습니다.",
            view=self,
        )

        self.stop()
