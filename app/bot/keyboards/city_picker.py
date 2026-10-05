from typing import Literal

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.prayer_times import City

CITIES_PER_PAGE = 8


class ConfirmCityCallback(CallbackData, prefix="city_confirm"):
    slug: str
    answer: Literal["yes", "no"]


class CityPageCallback(CallbackData, prefix="city_page"):
    page: int


class CitySelectCallback(CallbackData, prefix="city_select"):
    slug: str


def confirm_city_keyboard(slug: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да", callback_data=ConfirmCityCallback(slug=slug, answer="yes").pack()
                ),
                InlineKeyboardButton(
                    text="❌ Нет", callback_data=ConfirmCityCallback(slug=slug, answer="no").pack()
                ),
            ]
        ]
    )


def city_list_keyboard(cities: list[City], page: int) -> InlineKeyboardMarkup:
    ordered = sorted(cities, key=lambda c: c.title)
    total_pages = max(1, (len(ordered) + CITIES_PER_PAGE - 1) // CITIES_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    start = page * CITIES_PER_PAGE
    chunk = ordered[start : start + CITIES_PER_PAGE]

    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text=city.title, callback_data=CitySelectCallback(slug=city.slug).pack())]
        for city in chunk
    ]

    nav_row: list[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=CityPageCallback(page=page - 1).pack())
        )
    if page < total_pages - 1:
        nav_row.append(
            InlineKeyboardButton(text="Вперёд ➡️", callback_data=CityPageCallback(page=page + 1).pack())
        )
    if nav_row:
        rows.append(nav_row)

    return InlineKeyboardMarkup(inline_keyboard=rows)
