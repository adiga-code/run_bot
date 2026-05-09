from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Event, EventRegistration


class EventService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ── Events CRUD ────────────────────────────────────────────────────────────

    async def create(
        self,
        title: str,
        date_label: str,
        description: str,
        channel_link: str | None,
        created_by: int,
    ) -> Event:
        event = Event(
            title=title,
            date_label=date_label,
            description=description,
            channel_link=channel_link,
            created_by=created_by,
        )
        self.session.add(event)
        await self.session.commit()
        return event

    async def get(self, event_id: int) -> Event | None:
        result = await self.session.execute(select(Event).where(Event.id == event_id))
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Event]:
        result = await self.session.execute(select(Event).order_by(Event.created_at.desc()))
        return list(result.scalars().all())

    async def list_active(self) -> list[Event]:
        result = await self.session.execute(
            select(Event).where(Event.is_active == True).order_by(Event.created_at.desc())
        )
        return list(result.scalars().all())

    async def toggle_active(self, event_id: int) -> Event | None:
        event = await self.get(event_id)
        if not event:
            return None
        event.is_active = not event.is_active
        await self.session.commit()
        return event

    async def delete(self, event_id: int) -> bool:
        event = await self.get(event_id)
        if not event:
            return False
        await self.session.delete(event)
        await self.session.commit()
        return True

    # ── Registrations ──────────────────────────────────────────────────────────

    async def register(
        self,
        event_id: int,
        telegram_id: int,
        tg_username: str | None,
        full_name: str,
        phone: str,
        email: str | None,
    ) -> EventRegistration:
        reg = EventRegistration(
            event_id=event_id,
            telegram_id=telegram_id,
            tg_username=tg_username,
            full_name=full_name,
            phone=phone,
            email=email,
        )
        self.session.add(reg)
        await self.session.commit()
        return reg

    async def already_registered(self, event_id: int, telegram_id: int) -> bool:
        result = await self.session.execute(
            select(EventRegistration).where(
                EventRegistration.event_id == event_id,
                EventRegistration.telegram_id == telegram_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_registrations(self, event_id: int) -> list[EventRegistration]:
        result = await self.session.execute(
            select(EventRegistration)
            .where(EventRegistration.event_id == event_id)
            .order_by(EventRegistration.created_at)
        )
        return list(result.scalars().all())

    async def count_registrations(self, event_id: int) -> int:
        regs = await self.get_registrations(event_id)
        return len(regs)
