from __future__ import annotations

import html
import logging
import os
import secrets
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import aiohttp
import discord
from aiohttp import web
from discord.ext import commands


DISCORD_API = "https://discord.com/api/v10"
DEFAULT_RULES = [
    "Hormati seluruh member dan staff. Toxic, harassment, diskriminasi, dan provokasi tidak ditoleransi.",
    "Dilarang spam chat, mention, sticker, emoji, atau membuat ticket tanpa kebutuhan jelas.",
    "Promosi store, server, jasa, atau sosial media lain wajib mendapat izin staff.",
    "Pembayaran yang sudah berhasil bersifat final. Refund hanya diproses jika produk tidak dapat dikirim oleh Vercettia Store.",
    "Jaga keamanan akun pribadi. Jangan bagikan password, kode OTP, atau data sensitif kepada siapa pun.",
    "Produk yang dibeli tidak boleh disalahgunakan, dieksploitasi, atau dijual ulang tanpa izin.",
    "Bukti pembayaran palsu, chargeback, dan aktivitas fraud akan berujung blacklist permanen.",
    "Ketersediaan produk dapat berubah mengikuti layanan terkait. Staff akan memberi informasi jika ada perubahan penting.",
    "Ikuti arahan staff saat order, support, atau penyelesaian kendala agar proses tetap cepat dan rapi.",
    "Seluruh member wajib mengikuti Discord Terms of Service dan Community Guidelines.",
]


@dataclass(slots=True)
class OAuthState:
    user_id: int
    guild_id: int
    created_at: float


@dataclass(slots=True)
class VerifySession:
    user_id: int
    guild_id: int
    created_at: float


class OAuthVerificationServer:
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.client_id = os.getenv("DISCORD_CLIENT_ID", "").strip()
        self.client_secret = os.getenv("DISCORD_CLIENT_SECRET", "").strip()
        self.redirect_uri = self._redirect_uri()
        self.host = os.getenv("VERIFY_HTTP_HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", os.getenv("VERIFY_HTTP_PORT", "8080")))
        self.enabled = self._env_bool("VERIFY_OAUTH_ENABLED", True)
        self.state_ttl_seconds = int(os.getenv("VERIFY_STATE_TTL_SECONDS", "600"))
        self._states: dict[str, OAuthState] = {}
        self._sessions: dict[str, VerifySession] = {}
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None

    @property
    def is_ready(self) -> bool:
        return self.enabled and bool(self.client_id and self.client_secret and self.redirect_uri)

    async def start(self) -> None:
        if not self.enabled:
            logging.info("OAuth verification server disabled.")
            return
        if not self.is_ready:
            logging.warning(
                "OAuth verification is not configured. Set DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, "
                "and DISCORD_OAUTH_REDIRECT_URI or PUBLIC_BASE_URL."
            )

        app = web.Application()
        app.add_routes(
            [
                web.get("/health", self.health),
                web.get("/verify/callback", self.callback),
                web.post("/verify/complete", self.complete),
            ]
        )
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self.host, self.port)
        await self._site.start()
        logging.info("OAuth verification server listening on %s:%s.", self.host, self.port)

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
            self._site = None

    def create_authorize_url(self, user_id: int, guild_id: int) -> str:
        self._cleanup()
        state = secrets.token_urlsafe(32)
        self._states[state] = OAuthState(user_id=user_id, guild_id=guild_id, created_at=time.time())
        query = urlencode(
            {
                "client_id": self.client_id,
                "response_type": "code",
                "redirect_uri": self.redirect_uri,
                "scope": "identify",
                "state": state,
                "prompt": "consent",
            }
        )
        return f"https://discord.com/oauth2/authorize?{query}"

    async def health(self, _: web.Request) -> web.Response:
        return web.json_response({"ok": True, "service": "vercettia-verify"})

    async def callback(self, request: web.Request) -> web.Response:
        code = request.query.get("code", "")
        state_key = request.query.get("state", "")
        state = self._states.pop(state_key, None)
        if not code or state is None or self._expired(state.created_at):
            return self._html_response(self._page("Verification Expired", "Sesi verify sudah expired. Buka ulang panel verify di Discord."))

        user = await self._fetch_oauth_user(code)
        if not user:
            return self._html_response(self._page("Authorization Failed", "Discord OAuth gagal. Coba verify ulang dari server."))

        try:
            oauth_user_id = int(user["id"])
        except (KeyError, TypeError, ValueError):
            return self._html_response(self._page("Authorization Failed", "Data akun Discord tidak valid."))

        if oauth_user_id != state.user_id:
            return self._html_response(self._page("Account Mismatch", "Akun Discord yang diauthorize tidak sama dengan akun yang membuka verify."))

        session_token = secrets.token_urlsafe(32)
        self._sessions[session_token] = VerifySession(
            user_id=state.user_id,
            guild_id=state.guild_id,
            created_at=time.time(),
        )
        return self._html_response(self._rules_page(session_token, user))

    async def complete(self, request: web.Request) -> web.Response:
        form = await request.post()
        token = str(form.get("token", ""))
        session = self._sessions.pop(token, None)
        if session is None or self._expired(session.created_at):
            return self._html_response(self._page("Verification Expired", "Sesi verify sudah expired. Buka ulang panel verify di Discord."))

        success, message = await self._grant_role(session.user_id, session.guild_id)
        title = "Verification Complete" if success else "Verification Failed"
        return self._html_response(self._page(title, message))

    async def _fetch_oauth_user(self, code: str) -> dict[str, Any] | None:
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{DISCORD_API}/oauth2/token", data=data) as response:
                if response.status >= 400:
                    logging.warning("Discord OAuth token exchange failed with status %s.", response.status)
                    return None
                token_data = await response.json()

            access_token = token_data.get("access_token")
            if not access_token:
                return None

            headers = {"Authorization": f"Bearer {access_token}"}
            async with session.get(f"{DISCORD_API}/users/@me", headers=headers) as response:
                if response.status >= 400:
                    logging.warning("Discord OAuth user fetch failed with status %s.", response.status)
                    return None
                return await response.json()

    async def _grant_role(self, user_id: int, guild_id: int) -> tuple[bool, str]:
        settings = getattr(self.bot, "settings", {})
        role_id = int(settings.get("member_role_id", 0))
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return False, "Bot tidak menemukan server. Pastikan bot masih berada di server Vercettia."

        role = guild.get_role(role_id) if role_id else None
        if role is None:
            return False, "Role member belum diset. Admin perlu menjalankan /verify_panel ulang."

        try:
            member = guild.get_member(user_id) or await guild.fetch_member(user_id)
        except discord.HTTPException:
            return False, "Member tidak ditemukan di server. Join server terlebih dahulu lalu ulangi verify."

        if role in member.roles:
            return True, f"Akun kamu sudah terverifikasi. Role {role.name} sudah aktif."

        try:
            await member.add_roles(role, reason="Vercettia OAuth verification")
        except discord.Forbidden:
            return False, "Bot belum punya izin memberi role. Naikkan role bot di atas role member."

        return True, f"Verify berhasil. Role {role.name} sudah aktif di akun kamu."

    def _rules_page(self, token: str, user: dict[str, Any]) -> str:
        username = html.escape(str(user.get("global_name") or user.get("username") or "Discord User"))
        rules = "\n".join(f"<li>{html.escape(rule)}</li>" for rule in self._rules())
        return f"""
        <!doctype html>
        <html lang="id">
        <head>{self._head("Vercettia Verification")}</head>
        <body>
          <main class="card">
            <p class="eyebrow">Vercettia Store</p>
            <h1>Rules Verification</h1>
            <p class="muted">Halo, <strong>{username}</strong>. Baca rules berikut sebelum menyelesaikan verify member.</p>
            <ol class="rules">{rules}</ol>
            <form method="post" action="/verify/complete">
              <input type="hidden" name="token" value="{html.escape(token)}" />
              <button type="submit">Saya Setuju dan Verify Member</button>
            </form>
          </main>
        </body>
        </html>
        """

    def _page(self, title: str, message: str) -> str:
        return f"""
        <!doctype html>
        <html lang="id">
        <head>{self._head(title)}</head>
        <body>
          <main class="card">
            <p class="eyebrow">Vercettia Store</p>
            <h1>{html.escape(title)}</h1>
            <p class="muted">{html.escape(message)}</p>
            <p class="hint">Kamu bisa kembali ke Discord sekarang.</p>
          </main>
        </body>
        </html>
        """

    @staticmethod
    def _head(title: str) -> str:
        return f"""
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>{html.escape(title)}</title>
        <style>
          :root {{ color-scheme: dark; }}
          * {{ box-sizing: border-box; }}
          body {{
            margin: 0;
            min-height: 100vh;
            display: grid;
            place-items: center;
            padding: 28px;
            font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background:
              radial-gradient(circle at 20% 20%, rgba(139, 92, 246, .28), transparent 32%),
              radial-gradient(circle at 82% 10%, rgba(109, 40, 217, .18), transparent 26%),
              #050505;
            color: #f5f3ff;
          }}
          .card {{
            width: min(620px, 100%);
            border: 1px solid rgba(255,255,255,.12);
            border-radius: 22px;
            background: rgba(15, 15, 18, .82);
            box-shadow: 0 30px 90px rgba(0,0,0,.48), 0 0 0 1px rgba(139,92,246,.08) inset;
            padding: 28px;
            backdrop-filter: blur(18px);
          }}
          .eyebrow {{
            margin: 0 0 10px;
            color: #a78bfa;
            font-size: 13px;
            font-weight: 700;
            letter-spacing: .08em;
            text-transform: uppercase;
          }}
          h1 {{ margin: 0 0 14px; font-size: clamp(28px, 7vw, 44px); line-height: 1.05; }}
          .muted, .hint {{ color: rgba(245,243,255,.78); line-height: 1.6; }}
          .rules {{ display: grid; gap: 10px; margin: 22px 0; padding-left: 22px; color: rgba(245,243,255,.9); line-height: 1.55; }}
          button {{
            width: 100%;
            border: 0;
            border-radius: 14px;
            padding: 15px 18px;
            color: white;
            font-weight: 800;
            background: linear-gradient(135deg, #8B5CF6, #6D28D9);
            box-shadow: 0 16px 42px rgba(139,92,246,.28);
            cursor: pointer;
          }}
        </style>
        """

    def _rules(self) -> list[str]:
        settings = getattr(self.bot, "settings", {})
        rules = settings.get("verification_rules")
        if isinstance(rules, list) and rules:
            return [str(rule) for rule in rules]
        return DEFAULT_RULES

    def _cleanup(self) -> None:
        self._states = {
            key: state for key, state in self._states.items() if not self._expired(state.created_at)
        }
        self._sessions = {
            key: session for key, session in self._sessions.items() if not self._expired(session.created_at)
        }

    def _expired(self, created_at: float) -> bool:
        return (time.time() - created_at) > self.state_ttl_seconds

    def _redirect_uri(self) -> str:
        redirect_uri = os.getenv("DISCORD_OAUTH_REDIRECT_URI", "").strip()
        if redirect_uri:
            return redirect_uri

        public_base_url = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
        if public_base_url:
            return f"{public_base_url}/verify/callback"
        return ""

    @staticmethod
    def _env_bool(name: str, default: bool = False) -> bool:
        value = os.getenv(name)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _html_response(content: str, status: int = 200) -> web.Response:
        return web.Response(text=content, content_type="text/html", status=status)
