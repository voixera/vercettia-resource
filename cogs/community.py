from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import admin_only
from utils.member_cards import make_member_card
from utils.views import VerifyPanelView


class Community(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.bot:
            return
        await self._send_member_log(member, joined=True)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        if member.bot:
            return
        await self._send_member_log(member, joined=False)

    @app_commands.command(name="welcome_setup", description="Set channel welcome Vercettia.")
    @app_commands.default_permissions(administrator=True)
    @admin_only()
    async def welcome_setup(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        self.bot.settings["welcome_channel_id"] = channel.id
        await self.bot.save_settings_config()
        await interaction.response.send_message(f"Welcome channel diset ke {channel.mention}.", ephemeral=True)

    @app_commands.command(name="leave_setup", description="Set channel leave Vercettia.")
    @app_commands.default_permissions(administrator=True)
    @admin_only()
    async def leave_setup(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        self.bot.settings["leave_channel_id"] = channel.id
        await self.bot.save_settings_config()
        await interaction.response.send_message(f"Leave channel diset ke {channel.mention}.", ephemeral=True)

    @app_commands.command(name="verify_panel", description="Kirim panel verify dan set role member.")
    @app_commands.default_permissions(administrator=True)
    @admin_only()
    async def verify_panel(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        channel: discord.TextChannel | None = None,
        rules_channel: discord.TextChannel | None = None,
        lockdown: bool = True,
    ) -> None:
        target_channel = channel or interaction.channel
        if not isinstance(target_channel, discord.TextChannel):
            await interaction.response.send_message("Pilih text channel untuk panel verify.", ephemeral=True)
            return
        if interaction.guild is None:
            await interaction.response.send_message("Command ini hanya bisa digunakan di server.", ephemeral=True)
            return

        bot_member = interaction.guild.me
        if bot_member and role >= bot_member.top_role:
            await interaction.response.send_message(
                "Role member harus berada di bawah role bot agar bisa diberikan otomatis.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        self.bot.settings["member_role_id"] = role.id
        if rules_channel:
            self.bot.settings["rules_channel_id"] = rules_channel.id
        await self.bot.save_settings_config()

        effective_rules_channel = rules_channel or self._configured_rules_channel(interaction.guild)
        await target_channel.send(view=VerifyPanelView(interaction.guild, self.bot.settings))
        rules_text = f" Rules: {effective_rules_channel.mention}." if effective_rules_channel else ""
        lockdown_text = ""
        if lockdown:
            applied, protected, failed = await self._apply_verify_lockdown(
                interaction.guild,
                role,
                target_channel,
                effective_rules_channel,
            )
            lockdown_text = f"\nLockdown: {applied} channel diset, {protected} private channel dijaga, {failed} gagal."

        await interaction.followup.send(
            f"Panel verify dikirim ke {target_channel.mention}. Role member: {role.mention}.{rules_text}{lockdown_text}",
            ephemeral=True,
        )

    @app_commands.command(name="rules_setup", description="Set channel rules untuk flow verify.")
    @app_commands.default_permissions(administrator=True)
    @admin_only()
    async def rules_setup(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        self.bot.settings["rules_channel_id"] = channel.id
        await self.bot.save_settings_config()
        await interaction.response.send_message(f"Rules channel diset ke {channel.mention}.", ephemeral=True)

    @app_commands.command(name="verify_lockdown", description="Sembunyikan channel untuk member yang belum verify.")
    @app_commands.default_permissions(administrator=True)
    @admin_only()
    async def verify_lockdown(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        verify_channel: discord.TextChannel,
        rules_channel: discord.TextChannel | None = None,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Command ini hanya bisa digunakan di server.", ephemeral=True)
            return

        bot_member = interaction.guild.me
        if bot_member and role >= bot_member.top_role:
            await interaction.response.send_message(
                "Role member harus berada di bawah role bot agar permission bisa diatur.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        self.bot.settings["member_role_id"] = role.id
        if rules_channel:
            self.bot.settings["rules_channel_id"] = rules_channel.id
        await self.bot.save_settings_config()

        effective_rules_channel = rules_channel or self._configured_rules_channel(interaction.guild)
        applied, protected, failed = await self._apply_verify_lockdown(
            interaction.guild,
            role,
            verify_channel,
            effective_rules_channel,
        )
        await interaction.followup.send(
            f"Verify lockdown selesai. {applied} channel diset, {protected} private channel dijaga, {failed} gagal.",
            ephemeral=True,
        )

    @app_commands.command(name="give_role", description="Berikan role ke member.")
    @app_commands.default_permissions(administrator=True)
    @admin_only()
    async def give_role(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        role: discord.Role,
        reason: str | None = None,
    ) -> None:
        await self._give_role(interaction, member, role, reason)

    @app_commands.command(name="gift_role", description="Gift role ke member.")
    @app_commands.default_permissions(administrator=True)
    @admin_only()
    async def gift_role(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        role: discord.Role,
        reason: str | None = None,
    ) -> None:
        await self._give_role(interaction, member, role, reason)

    @app_commands.command(name="remove_role", description="Hapus role dari member.")
    @app_commands.default_permissions(administrator=True)
    @admin_only()
    async def remove_role(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        role: discord.Role,
        reason: str | None = None,
    ) -> None:
        if not await self._can_manage_role(interaction, role):
            return

        try:
            await member.remove_roles(role, reason=reason or f"Removed by {interaction.user}")
        except discord.Forbidden:
            await interaction.response.send_message("Bot belum punya izin untuk menghapus role itu.", ephemeral=True)
            return
        await interaction.response.send_message(
            f"Role {role.mention} sudah dihapus dari {member.mention}.",
            ephemeral=True,
        )

    @app_commands.command(name="join_voice", description="Masukkan bot ke voice channel.")
    @app_commands.default_permissions(administrator=True)
    @admin_only()
    async def join_voice(
        self,
        interaction: discord.Interaction,
        channel: discord.VoiceChannel | None = None,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Command ini hanya bisa digunakan di server.", ephemeral=True)
            return

        target_channel = channel
        if target_channel is None and isinstance(interaction.user, discord.Member) and interaction.user.voice:
            target_channel = interaction.user.voice.channel

        if target_channel is None:
            await interaction.response.send_message(
                "Masuk voice dulu atau pilih voice channel di command.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            voice_client = interaction.guild.voice_client
            if voice_client and voice_client.is_connected():
                await voice_client.move_to(target_channel)
            else:
                await target_channel.connect()
        except discord.Forbidden:
            await interaction.followup.send("Bot belum punya izin connect ke voice channel itu.", ephemeral=True)
            return
        except RuntimeError:
            await interaction.followup.send(
                "Voice dependency belum aktif. Jalankan install requirements agar PyNaCl terpasang.",
                ephemeral=True,
            )
            return

        await interaction.followup.send(f"Bot masuk ke voice channel {target_channel.mention}.", ephemeral=True)

    @app_commands.command(name="leave_voice", description="Keluarkan bot dari voice channel.")
    @app_commands.default_permissions(administrator=True)
    @admin_only()
    async def leave_voice(self, interaction: discord.Interaction) -> None:
        voice_client = interaction.guild.voice_client if interaction.guild else None
        if not voice_client or not voice_client.is_connected():
            await interaction.response.send_message("Bot sedang tidak berada di voice channel.", ephemeral=True)
            return

        await voice_client.disconnect(force=True)
        await interaction.response.send_message("Bot sudah keluar dari voice channel.", ephemeral=True)

    async def _send_member_log(self, member: discord.Member, *, joined: bool) -> None:
        settings = getattr(self.bot, "settings", {})
        channel_key = "welcome_channel_id" if joined else "leave_channel_id"
        channel_id = int(settings.get(channel_key, 0))
        if not channel_id:
            return

        channel = member.guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return

        content = (
            f"Welcome {member.mention} to {member.guild.name}!"
            if joined
            else f"{member.mention} left {member.guild.name}."
        )
        card = await make_member_card(
            member,
            joined=joined,
            base_dir=self.bot.base_dir,
            settings=settings,
        )
        await channel.send(
            content=content,
            file=card,
            allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
        )

    async def _give_role(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        role: discord.Role,
        reason: str | None,
    ) -> None:
        if not await self._can_manage_role(interaction, role):
            return

        try:
            await member.add_roles(role, reason=reason or f"Given by {interaction.user}")
        except discord.Forbidden:
            await interaction.response.send_message("Bot belum punya izin untuk memberi role itu.", ephemeral=True)
            return
        await interaction.response.send_message(
            f"Role {role.mention} sudah diberikan ke {member.mention}.",
            ephemeral=True,
        )

    async def _can_manage_role(self, interaction: discord.Interaction, role: discord.Role) -> bool:
        if interaction.guild is None:
            await interaction.response.send_message("Command ini hanya bisa digunakan di server.", ephemeral=True)
            return False

        if role.is_default():
            await interaction.response.send_message("Role @everyone tidak bisa dikelola lewat command ini.", ephemeral=True)
            return False

        bot_member = interaction.guild.me
        if bot_member and role >= bot_member.top_role:
            await interaction.response.send_message(
                "Role target harus berada di bawah role bot.",
                ephemeral=True,
            )
            return False

        if isinstance(interaction.user, discord.Member) and not interaction.user.guild_permissions.administrator:
            admin_role_id = int(getattr(self.bot, "settings", {}).get("admin_role_id", 0))
            admin_role = interaction.guild.get_role(admin_role_id) if admin_role_id else None
            if admin_role and role >= admin_role:
                await interaction.response.send_message(
                    "Role ini hanya bisa dikelola oleh administrator server.",
                    ephemeral=True,
                )
                return False

        return True

    def _configured_rules_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
        channel_id = int(getattr(self.bot, "settings", {}).get("rules_channel_id", 0))
        channel = guild.get_channel(channel_id) if channel_id else None
        return channel if isinstance(channel, discord.TextChannel) else None

    async def _apply_verify_lockdown(
        self,
        guild: discord.Guild,
        member_role: discord.Role,
        verify_channel: discord.TextChannel,
        rules_channel: discord.TextChannel | None,
    ) -> tuple[int, int, int]:
        allowed_unverified_ids = {verify_channel.id}
        if rules_channel:
            allowed_unverified_ids.add(rules_channel.id)

        applied = 0
        protected_private = 0
        failed = 0
        manageable_types = (
            discord.CategoryChannel,
            discord.TextChannel,
            discord.VoiceChannel,
            discord.StageChannel,
            discord.ForumChannel,
        )

        for channel in guild.channels:
            if not isinstance(channel, manageable_types):
                continue

            try:
                everyone_overwrite = channel.overwrites_for(guild.default_role)
                member_overwrite = channel.overwrites_for(member_role)

                if channel.id in allowed_unverified_ids:
                    everyone_overwrite.view_channel = True
                    if isinstance(channel, discord.TextChannel):
                        everyone_overwrite.send_messages = False
                        everyone_overwrite.read_message_history = True
                    await channel.set_permissions(
                        guild.default_role,
                        overwrite=everyone_overwrite,
                        reason="Vercettia verify channel access",
                    )
                    applied += 1
                    continue

                was_public = everyone_overwrite.view_channel is not False
                member_already_allowed = member_overwrite.view_channel is True

                everyone_overwrite.view_channel = False
                await channel.set_permissions(
                    guild.default_role,
                    overwrite=everyone_overwrite,
                    reason="Vercettia verify lockdown",
                )

                if was_public or member_already_allowed:
                    member_overwrite.view_channel = True
                    if isinstance(channel, discord.TextChannel):
                        member_overwrite.read_message_history = True
                    await channel.set_permissions(
                        member_role,
                        overwrite=member_overwrite,
                        reason="Vercettia member channel access",
                    )
                else:
                    protected_private += 1

                applied += 1
            except discord.HTTPException:
                failed += 1

        return applied, protected_private, failed


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Community(bot))
