from __future__ import annotations

from typing import Any

import discord
from discord import app_commands


def is_admin_member(member: discord.Member, settings: dict[str, Any]) -> bool:
    role_id = int(settings.get("admin_role_id", 0))
    user_ids = {int(user_id) for user_id in settings.get("admin_user_ids", [])}
    return (
        member.id in user_ids
        or member.guild_permissions.administrator
        or any(role.id == role_id for role in member.roles)
    )


def admin_only() -> app_commands.Check:
    async def predicate(interaction: discord.Interaction) -> bool:
        bot = interaction.client
        settings = getattr(bot, "settings", {})
        member = interaction.user
        if isinstance(member, discord.Member) and is_admin_member(member, settings):
            return True
        raise app_commands.CheckFailure(settings.get("messages", {}).get("admin_only", "Admin only."))

    return app_commands.check(predicate)
