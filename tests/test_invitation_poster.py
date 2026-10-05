from PIL import Image, ImageDraw, ImageFont

from app.services.invitation import compose_poster, generate_qr_code


def _wrap_text_lines():
    from app.services.invitation import _wrap_text

    image = Image.new("RGB", (10, 10))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    long_title = 'Вы можете присоединиться к группе "Dauren & Ернияз, Jamaat Namaz Bot", если хотите совершать намаз с джамаатом.'
    lines = _wrap_text(draw, long_title, font, max_width=200)
    return draw, font, lines


def test_wrap_text_keeps_every_line_within_max_width():
    draw, font, lines = _wrap_text_lines()
    assert len(lines) > 1
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        assert bbox[2] - bbox[0] <= 200


def test_compose_poster_handles_long_group_title_without_error():
    qr_image = generate_qr_code("https://t.me/+testinvitelink")
    poster_bytes = compose_poster(
        qr_image, 'Dauren & Ернияз, очень длинное название группы для намазхана', "jamaat_namaz_bot"
    )
    assert poster_bytes[:8] == b"\x89PNG\r\n\x1a\n"
