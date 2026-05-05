from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ReferralLink, User


class ReferralService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, code: str, name: str, created_by: int) -> ReferralLink | None:
        existing = await self.get_by_code(code)
        if existing:
            return None
        link = ReferralLink(code=code, name=name, created_by=created_by)
        self.session.add(link)
        await self.session.commit()
        return link

    async def get_by_code(self, code: str) -> ReferralLink | None:
        result = await self.session.execute(
            select(ReferralLink).where(ReferralLink.code == code)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[ReferralLink]:
        result = await self.session.execute(
            select(ReferralLink).order_by(ReferralLink.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_stats(self, code: str) -> dict:
        r = await self.session.execute(
            select(func.count()).select_from(User).where(User.referral_code == code)
        )
        total = r.scalar() or 0

        r = await self.session.execute(
            select(func.count()).select_from(User).where(
                User.referral_code == code,
                User.onboarding_complete == True,
            )
        )
        onboarded = r.scalar() or 0

        r = await self.session.execute(
            select(func.count()).select_from(User).where(
                User.referral_code == code,
                User.status.in_(["active", "completed"]),
            )
        )
        activated = r.scalar() or 0

        return {"total": total, "onboarded": onboarded, "activated": activated}

    async def delete(self, code: str) -> bool:
        link = await self.get_by_code(code)
        if not link:
            return False
        await self.session.delete(link)
        await self.session.commit()
        return True
