from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class PrivateUser(Base):
    """A user who has messaged the bot in a private chat (the bot itself only works in groups,
    so this table exists purely for usage statistics)."""

    __tablename__ = "private_users"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    telegram_user_id: Mapped[int] = mapped_column(sa.BigInteger, nullable=False, unique=True)
    username: Mapped[str | None] = mapped_column(sa.String(255))
    first_name: Mapped[str | None] = mapped_column(sa.String(255))
    first_seen_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now())
    last_seen_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now())
