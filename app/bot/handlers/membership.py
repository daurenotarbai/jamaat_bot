import logging

from aiogram import Bot, Router
from aiogram.types import ChatMemberUpdated
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.group import Group
from app.database.repositories.group_repository import GroupRepository

logger = logging.getLogger(__name__)
router = Router(name="membership")

_REMOVED_STATUSES = {"left", "kicked"}


@router.my_chat_member()
async def handle_membership_change(
    event: ChatMemberUpdated, bot: Bot, group: Group, session: AsyncSession
) -> None:
    if event.new_chat_member.user.id != bot.id:
        return

    if event.new_chat_member.status in _REMOVED_STATUSES:
        await GroupRepository(session).deactivate(group.id)
        logger.info("Bot removed from group_id=%s (telegram_chat_id=%s)", group.id, group.telegram_chat_id)
