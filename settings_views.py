from __future__ import annotations

import discord

from app_helpers import get_servers_for_race
from constants import RACE_OPTIONS
from storage import upsert_guild_setting


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
        self.stop()

    @discord.ui.button(label="저장", style=discord.ButtonStyle.success, row=2)
    async def save_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        if not self.selected_race_code or not self.selected_server_code:
            await interaction.response.send_message("종족과 종족 서버를 모두 선택한 뒤 저장하세요.", ephemeral=True)
            return
        upsert_guild_setting(
            guild_id=self.guild_id,
            race_code=self.selected_race_code,
            race_name=self.selected_race_name or "",
            server_code=self.selected_server_code,
            server_name=self.selected_server_name or "",
            updated_by=interaction.user.id,
        )
        await interaction.response.edit_message(
            content=f"기본 설정이 저장되었습니다.\n- 종족: **{self.selected_race_name}**\n- 종족 서버: **{self.selected_server_name}**",
            view=None,
        )
        self.stop()

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary, row=2)
    async def cancel_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        await interaction.response.edit_message(content="설정이 취소되었습니다.", view=None)
        self.stop()


class RaceSelect(discord.ui.Select):
    def __init__(self, parent_view: GuildSettingView):
        self.parent_view = parent_view
        options = [discord.SelectOption(label=race["name"], value=race["code"]) for race in RACE_OPTIONS]
        super().__init__(placeholder="아이온2 종족을 선택하세요", min_values=1, max_values=1, options=options, row=0)

    async def callback(self, interaction: discord.Interaction):
        selected = next((r for r in RACE_OPTIONS if r["code"] == self.values[0]), None)
        if selected is None:
            await interaction.response.send_message("선택한 종족 정보를 찾을 수 없습니다.", ephemeral=True)
            return
        self.parent_view.selected_race_code = selected["code"]
        self.parent_view.selected_race_name = selected["name"]
        self.parent_view.selected_server_code = None
        self.parent_view.selected_server_name = None
        self.parent_view.refresh_server_select()
        await interaction.response.edit_message(content=f"종족: **{selected['name']}** 선택됨\n이제 종족 서버를 선택하세요.", view=self.parent_view)


class ServerSelect(discord.ui.Select):
    def __init__(self, parent_view: GuildSettingView, race_code: str):
        self.parent_view = parent_view
        servers = get_servers_for_race(race_code)
        options = [discord.SelectOption(label=server["name"], value=server["code"]) for server in servers]
        super().__init__(placeholder="아이온2 종족 서버를 선택하세요", min_values=1, max_values=1, options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        servers = get_servers_for_race(self.parent_view.selected_race_code or "")
        selected = next((s for s in servers if s["code"] == self.values[0]), None)
        if selected is None:
            await interaction.response.send_message("선택한 서버 정보를 찾을 수 없습니다.", ephemeral=True)
            return
        self.parent_view.selected_server_code = selected["code"]
        self.parent_view.selected_server_name = selected["name"]
        await interaction.response.edit_message(
            content=f"종족: **{self.parent_view.selected_race_name}**\n종족 서버: **{selected['name']}**\n저장 버튼을 눌러 설정을 저장하세요.",
            view=self.parent_view,
        )

class RaidDeleteConfirmView(discord.ui.View):
    def __init__(self, guild_id: int, raid_name: str, user_id: int):
        super().__init__(timeout=120)
        self.guild_id = guild_id
        self.raid_name = raid_name
        self.user_id = user_id
        self.value: str | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("이 삭제 확인 UI는 명령어를 실행한 관리자만 사용할 수 있습니다.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="신청자까지 같이 삭제", style=discord.ButtonStyle.danger)
    async def delete_with_applications(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.value = "delete_with_applications"
        await interaction.response.edit_message(content=f"`{self.raid_name}` 레이드를 신청 내역/공대 내역과 함께 삭제합니다.", view=None)
        self.stop()

    @discord.ui.button(label="취소", style=discord.ButtonStyle.secondary)
    async def cancel_delete(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.value = "cancel"
        await interaction.response.edit_message(content="레이드 삭제가 취소되었습니다.", view=None)
        self.stop()
