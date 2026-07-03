from __future__ import annotations

import discord


def _safe_channel_name(value: str) -> str:
    safe_name = "".join(character.lower() if character.isalnum() else "-" for character in value)
    return safe_name.strip("-") or "user"


def staff_mention(guild: discord.Guild, settings: dict) -> str:
    staff_role = guild.get_role(int(settings.get("staff_role_id", 0)))
    admin_role = guild.get_role(int(settings.get("admin_role_id", 0)))
    mentions = [role.mention for role in (staff_role, admin_role) if role]
    mentions.extend(f"<@{int(user_id)}>" for user_id in settings.get("admin_user_ids", []))
    return " ".join(dict.fromkeys(mentions))


async def create_private_ticket_channel(
    guild: discord.Guild,
    user: discord.abc.User,
    settings: dict,
    *,
    prefix: str,
    reason: str,
) -> discord.TextChannel:
    category_id = int(settings.get("ticket_category_id", 0))
    category = guild.get_channel(category_id) if category_id else None
    staff_role = guild.get_role(int(settings.get("staff_role_id", 0)))
    admin_role = guild.get_role(int(settings.get("admin_role_id", 0)))
    unique_suffix = str(user.id)[-6:]
    time_suffix = discord.utils.utcnow().strftime("%H%M%S")
    channel_name = f"{prefix}-{_safe_channel_name(user.name)}-{unique_suffix}-{time_suffix}"[:90]

    overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
    }
    if guild.me:
        overwrites[guild.me] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True,
        )
    for role in (staff_role, admin_role):
        if role:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
            )
    for user_id in settings.get("admin_user_ids", []):
        try:
            admin_member = guild.get_member(int(user_id)) or await guild.fetch_member(int(user_id))
        except (discord.HTTPException, ValueError):
            continue
        overwrites[admin_member] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True,
        )

    return await guild.create_text_channel(
        name=channel_name,
        category=category if isinstance(category, discord.CategoryChannel) else None,
        overwrites=overwrites,
        reason=reason,
    )
