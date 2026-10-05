from io import BytesIO

import qrcode
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from PIL import Image, ImageDraw, ImageFont

POSTER_SIZE = (1200, 1600)
QR_SIZE = 800
BG_COLOR = "#ffffff"
ACCENT_COLOR = "#000000"
BORDER_WIDTH = 6


class InsufficientRightsError(Exception):
    """Raised when the bot lacks the rights to obtain an invite link for the chat."""


async def get_or_create_invite_link(bot: Bot, chat_id: int) -> str:
    try:
        link = await bot.export_chat_invite_link(chat_id)
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        raise InsufficientRightsError(str(exc)) from exc
    return link


def generate_qr_code(data: str) -> Image.Image:
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    # NEAREST keeps module edges perfectly sharp black/white -- any smoothing
    # interpolation (the PIL default) blurs edges into gray, which hurts both
    # print quality and scannability.
    return image.resize((QR_SIZE, QR_SIZE), Image.Resampling.NEAREST)


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in ("DejaVuSans-Bold.ttf", "arialbd.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


SIDE_MARGIN = 80


def compose_poster(qr_image: Image.Image, group_title: str, bot_username: str) -> bytes:
    poster = Image.new("RGB", POSTER_SIZE, color=BG_COLOR)
    draw = ImageDraw.Draw(poster)

    # Pure black/white, high-contrast design -- printable on any black-and-white printer.
    draw.rectangle(
        [(BORDER_WIDTH // 2, BORDER_WIDTH // 2), (POSTER_SIZE[0] - BORDER_WIDTH // 2, POSTER_SIZE[1] - BORDER_WIDTH // 2)],
        outline=ACCENT_COLOR,
        width=BORDER_WIDTH,
    )

    title_font = _load_font(64)
    body_font = _load_font(36)
    footer_font = _load_font(32)
    credit_font = _load_font(24)
    max_text_width = POSTER_SIZE[0] - 2 * SIDE_MARGIN

    title_text = "Присоединяйтесь к группе"
    body_text = f'Вы можете присоединиться к группе\n"{group_title}",\nесли хотите совершать намаз с джамаатом.'
    footer_text = "Отсканируйте QR-код камерой телефона"

    y = 90
    y += _draw_centered_text(draw, title_text, title_font, y=y, width=POSTER_SIZE[0], fill=ACCENT_COLOR, max_width=max_text_width)
    y += 50
    y += _draw_centered_text(draw, body_text, body_font, y=y, width=POSTER_SIZE[0], fill=ACCENT_COLOR, max_width=max_text_width)
    y += 60

    qr_x = (POSTER_SIZE[0] - QR_SIZE) // 2
    poster.paste(qr_image, (qr_x, y))
    draw.rectangle(
        [(qr_x, y), (qr_x + QR_SIZE, y + QR_SIZE)],
        outline=ACCENT_COLOR,
        width=BORDER_WIDTH,
    )
    y += QR_SIZE + 60

    y += _draw_centered_text(
        draw, footer_text, footer_font, y=y, width=POSTER_SIZE[0], fill=ACCENT_COLOR, max_width=max_text_width
    )
    y += 30
    _draw_centered_text(
        draw,
        f"Постер создан с помощью бота @{bot_username}",
        credit_font,
        y=y,
        width=POSTER_SIZE[0],
        fill=ACCENT_COLOR,
        max_width=max_text_width,
    )

    buffer = BytesIO()
    poster.save(buffer, format="PNG")
    return buffer.getvalue()


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            bbox = draw.textbbox((0, 0), candidate, font=font)
            if not current or bbox[2] - bbox[0] <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    *,
    y: int,
    width: int,
    fill: str,
    max_width: int | None = None,
) -> int:
    """Draws word-wrapped, centered text starting at `y` and returns the block's height."""
    lines = _wrap_text(draw, text, font, max_width or width)
    line_height = font.getbbox("Ag")[3] or 1
    line_gap = 16
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        x = (width - line_width) // 2
        draw.text((x, y + i * (line_height + line_gap)), line, font=font, fill=fill)
    return len(lines) * (line_height + line_gap) if lines else 0
