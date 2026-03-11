# views.py
from __future__ import annotations

import discord

from storage import upsert_guild_setting


def get_servers_for_race(race_code: str) -> list[dict]:
    return [server for server in SERVER_OPTIONS if str(server["code"]).startswith(str(race_code))]

        
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
