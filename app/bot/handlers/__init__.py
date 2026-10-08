from aiogram import Router

from app.bot.handlers import (
    help as help_handler,
    invitation,
    juma,
    location,
    membership,
    prayer_notifications,
    prayer_settings,
    prayer_times,
    settings,
    start,
    stats,
)

routers: list[Router] = [
    start.router,
    help_handler.router,
    settings.router,
    location.router,
    prayer_notifications.router,
    prayer_settings.router,
    prayer_times.router,
    juma.router,
    invitation.router,
    membership.router,
    stats.router,
]
