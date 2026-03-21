from datetime import datetime, timezone

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import WhitelistEntry


class WhitelistService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, telegram_id: int, added_by: int, note: str | None = None) -> WhitelistEntry:
        entry = WhitelistEntry(
            telegram_id=telegram_id,
            added_by=added_by,
            note=note,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(entry)
        await self.session.commit()
        await self.session.refresh(entry)
        return entry

    async def remove(self, telegram_id: int) -> bool:
        result = await self.session.execute(
            delete(WhitelistEntry).where(WhitelistEntry.telegram_id == telegram_id)
        )
        await self.session.commit()
        return result.rowcount > 0

    async def is_allowed(self, telegram_id: int) -> bool:
        result = await self.session.execute(
            select(WhitelistEntry).where(WhitelistEntry.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none() is not None

    async def list_all(self) -> list[WhitelistEntry]:
        result = await self.session.execute(
            select(WhitelistEntry).order_by(WhitelistEntry.created_at.desc())
        )
        return list(result.scalars().all())
