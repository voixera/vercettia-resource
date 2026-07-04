from __future__ import annotations

import logging
from typing import Any

import discord
from discord.ext import commands


PanelRecord = dict[str, int]


def _panel_records(settings: dict[str, Any]) -> list[PanelRecord]:
    raw_records = settings.setdefault("verify_panel_messages", [])
    if not isinstance(raw_records, list):
        settings["verify_panel_messages"] = []
        return settings["verify_panel_messages"]

    records: list[PanelRecord] = []
    for record in raw_records:
        if not isinstance(record, dict):
            continue
        try:
            records.append(
                {
                    "guild_id": int(record["guild_id"]),
                    "channel_id": int(record["channel_id"]),
                    "message_id": int(record["message_id"]),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
    settings["verify_panel_messages"] = records
    return records


async def remember_verify_panel(bot: commands.Bot, message: discord.Message) -> None:
    if message.guild is None:
        return

    settings = getattr(bot, "settings", {})
    records = _panel_records(settings)
    new_record = {
        "guild_id": int(message.guild.id),
        "channel_id": int(message.channel.id),
        "message_id": int(message.id),
    }
    records[:] = [
        record
        for record in records
        if not (
            record["guild_id"] == new_record["guild_id"]
            and record["channel_id"] == new_record["channel_id"]
            and record["message_id"] == new_record["message_id"]
        )
    ]
    records.append(new_record)

    save_settings = getattr(bot, "save_settings_config", None)
    if save_settings:
        await save_settings()


async def refresh_verify_panels(bot: commands.Bot, guild: discord.Guild) -> None:
    settings = getattr(bot, "settings", {})
    records = _panel_records(settings)
    guild_records = [record for record in records if record["guild_id"] == guild.id]
    if not guild_records:
        return

    from utils.views import VerifyPanelView

    kept_records: list[PanelRecord] = []
    changed = False
    for record in records:
        if record["guild_id"] != guild.id:
            kept_records.append(record)
            continue

        channel = guild.get_channel(record["channel_id"])
        if channel is None:
            try:
                channel = await bot.fetch_channel(record["channel_id"])
            except discord.HTTPException:
                changed = True
                logging.warning("Removing stale verify panel record: %s", record)
                continue

        if not isinstance(channel, discord.TextChannel):
            changed = True
            continue

        try:
            message = await channel.fetch_message(record["message_id"])
            await message.edit(view=VerifyPanelView(guild, settings))
            kept_records.append(record)
        except discord.NotFound:
            changed = True
            logging.warning("Verify panel message no longer exists: %s", record)
        except discord.HTTPException:
            kept_records.append(record)
            logging.exception("Failed to refresh verify panel: %s", record)

    if changed:
        settings["verify_panel_messages"] = kept_records
        save_settings = getattr(bot, "save_settings_config", None)
        if save_settings:
            await save_settings()
