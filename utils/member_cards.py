from __future__ import annotations

import io
import logging
from pathlib import Path

import discord
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


CARD_SIZE = (760, 280)
INNER_SIZE = (610, 170)
CYAN = (0, 194, 255)
BLUE = (30, 65, 135)
BACKGROUND = (12, 15, 24)
PANEL = (9, 18, 42)
TEXT = (235, 240, 255)
MUTED = (150, 166, 195)


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_names = (
        "arialbd.ttf" if bold else "arial.ttf",
        "segoeuib.ttf" if bold else "segoeui.ttf",
        "bahnschrift.ttf",
    )
    font_dirs = (
        Path("C:/Windows/Fonts"),
        Path("/usr/share/fonts/truetype/dejavu"),
        Path("/usr/share/fonts/truetype/liberation2"),
    )
    for directory in font_dirs:
        for font_name in font_names:
            font_path = directory / font_name
            if font_path.exists():
                return ImageFont.truetype(str(font_path), size=size)
    return ImageFont.load_default()


def _fit_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
    if draw.textlength(text, font=font) <= max_width:
        return text

    trimmed = text
    while trimmed and draw.textlength(f"{trimmed}...", font=font) > max_width:
        trimmed = trimmed[:-1]
    return f"{trimmed}..." if trimmed else "..."


def _open_local_logo(base_dir: Path, settings: dict) -> Image.Image | None:
    candidates: list[Path] = []
    configured = str(settings.get("logo", "")).strip()
    if configured:
        candidates.append(base_dir / configured)
    candidates.extend(
        [
            base_dir / "assets" / "Logos.png",
            base_dir / "assets" / "logo.png",
            base_dir / "assets" / "banner.png",
        ]
    )

    for path in candidates:
        if path.exists():
            try:
                return Image.open(path).convert("RGBA")
            except OSError:
                logging.exception("Failed to open member card logo: %s", path)
    return None


async def _avatar_image(member: discord.Member, base_dir: Path, settings: dict) -> Image.Image:
    try:
        avatar_bytes = await member.display_avatar.with_size(256).with_static_format("png").read()
        return Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    except (discord.HTTPException, OSError, AttributeError):
        logging.exception("Failed to read avatar for member card: %s", member.id)

    logo = _open_local_logo(base_dir, settings)
    if logo:
        return logo

    fallback = Image.new("RGBA", (256, 256), (139, 92, 246, 255))
    draw = ImageDraw.Draw(fallback)
    draw.text((128, 128), "V", fill=TEXT, anchor="mm", font=_font(112, bold=True))
    return fallback


def _circle_image(image: Image.Image, size: int) -> Image.Image:
    cover = ImageOps.fit(image, (size, size), method=Image.Resampling.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size - 1, size - 1), fill=255)
    output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    output.paste(cover, (0, 0), mask)
    return output


def _glow_box(size: tuple[int, int], radius: int, color: tuple[int, int, int]) -> Image.Image:
    glow = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    draw.rounded_rectangle((6, 6, size[0] - 6, size[1] - 6), radius=radius, outline=(*color, 180), width=3)
    return glow.filter(ImageFilter.GaussianBlur(10))


async def make_member_card(
    member: discord.Member,
    *,
    joined: bool,
    base_dir: Path,
    settings: dict,
) -> discord.File:
    avatar = await _avatar_image(member, base_dir, settings)
    card = Image.new("RGBA", CARD_SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)

    draw.rounded_rectangle((0, 0, CARD_SIZE[0] - 1, CARD_SIZE[1] - 1), radius=10, fill=BACKGROUND, outline=(44, 48, 60), width=1)
    draw.rounded_rectangle((0, 0, 7, CARD_SIZE[1]), radius=4, fill=CYAN)

    panel_left, panel_top = 44, 35
    panel_right, panel_bottom = CARD_SIZE[0] - 38, CARD_SIZE[1] - 36
    draw.rounded_rectangle((panel_left, panel_top, panel_right, panel_bottom), radius=5, fill=(15, 26, 54))
    panel_gradient = Image.new("RGBA", (panel_right - panel_left, panel_bottom - panel_top), (0, 0, 0, 0))
    gradient_draw = ImageDraw.Draw(panel_gradient)
    for x in range(panel_gradient.width):
        alpha = int(95 * (x / panel_gradient.width))
        gradient_draw.line((x, 0, x, panel_gradient.height), fill=(66, 123, 255, alpha))
    card.alpha_composite(panel_gradient, (panel_left, panel_top))

    inner_left, inner_top = 70, 58
    inner_right = inner_left + INNER_SIZE[0]
    inner_bottom = inner_top + INNER_SIZE[1]
    card.alpha_composite(_glow_box(INNER_SIZE, 12, CYAN), (inner_left, inner_top))
    draw.rounded_rectangle((inner_left, inner_top, inner_right, inner_bottom), radius=12, fill=PANEL, outline=CYAN, width=2)

    avatar_size = 92
    avatar_x = inner_right - 122
    avatar_y = inner_top + 38
    draw.ellipse(
        (avatar_x - 6, avatar_y - 6, avatar_x + avatar_size + 6, avatar_y + avatar_size + 6),
        fill=(10, 21, 46),
        outline=CYAN,
        width=2,
    )
    card.alpha_composite(_circle_image(avatar, avatar_size), (avatar_x, avatar_y))

    title_font = _font(32, bold=True)
    name_font = _font(19)
    small_font = _font(14)
    guild_font = _font(13, bold=True)

    title = "Thanks For Joining!!!" if joined else "See You Again!!!"
    display_name = _fit_text(draw, member.display_name, name_font, 395)
    username = _fit_text(draw, member.name, name_font, 395)
    guild_name = _fit_text(draw, member.guild.name, guild_font, 210)
    count = member.guild.member_count or "-"
    footer = f"Welcome to {guild_name} | Member #{count}" if joined else f"Left {guild_name} | Member #{count}"

    draw.text((inner_left + 28, inner_top + 36), title, fill=TEXT, font=title_font)
    draw.text((inner_left + 30, inner_top + 84), display_name, fill=MUTED, font=name_font)
    draw.text((inner_left + 30, inner_top + 110), username, fill=(82, 174, 255), font=name_font)
    draw.text((inner_left + 30, inner_bottom - 30), footer, fill=MUTED, font=small_font)

    buffer = io.BytesIO()
    card.convert("RGB").save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    filename = f"{'welcome' if joined else 'leave'}-{member.id}.png"
    return discord.File(buffer, filename=filename)
