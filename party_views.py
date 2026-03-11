# party_views.py
# 공대 관련 UI

# =========================================================
# 공대 확인 UI
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
# 공대 수정
# =========================================================

class PartyReplaceView(discord.ui.View):
    def __init__(self, user_id: int, members: list[dict]):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.value: str | None = None
        self.selected_member_id: int | None = None

        self.add_item(PartyReplaceSelect(self, members))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "이 UI는 명령어 실행자만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True

      
# =========================================================
# 교체 대상 선택 UI
# =========================================================

class PartyReplaceSelect(discord.ui.Select):
    def __init__(self, parent_view: "PartyReplaceView", members: list[dict]):
        self.parent_view = parent_view

        options = []
        for m in members:
            options.append(
                discord.SelectOption(
                    label=f"{m['character_name']} ({m['job_name']})"[:100],
                    description=f"{m['item_level']} | {m['combat_score']}"[:100],
                    value=str(m["id"]),
                )
            )

        super().__init__(
            placeholder="대상 파티에서 선택하세요",
            min_values=1,
            max_values=1,
            options=options[:25],
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent_view.user_id:
            await interaction.response.send_message(
                "이 UI는 명령어 실행자만 사용할 수 있습니다.",
                ephemeral=True,
            )
            return

        self.parent_view.selected_member_id = int(self.values[0])
        self.parent_view.value = "submit"

        for item in self.parent_view.children:
            item.disabled = True

        await interaction.response.edit_message(
            content="대상 캐릭터를 선택했습니다.",
            view=self.parent_view,
        )
        self.parent_view.stop()


# =========================================================
# 공대 수정 view
# =========================================================

class PartyReplaceModeView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.value: str | None = None
        # "swap" / "waiting" / "cancel"

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

    @discord.ui.button(label="교체", style=discord.ButtonStyle.primary)
    async def swap_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "swap"
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content="교체 모드를 선택했습니다.",
            view=self,
        )
        self.stop()

    @discord.ui.button(label="대기 이동", style=discord.ButtonStyle.secondary)
    async def waiting_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "waiting"
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content="대기 이동 모드를 선택했습니다.",
            view=self,
        )
        self.stop()

    @discord.ui.button(label="취소", style=discord.ButtonStyle.danger)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = "cancel"
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content="공대 수정이 취소되었습니다.",
            view=self,
        )
        self.stop()
