import secrets

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ReferralLink, User


class ReferralService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, name: str, admin_id: int) -> ReferralLink:
        code = secrets.token_urlsafe(6)
        # Ensure uniqueness (extremely unlikely collision, but check anyway)
        while await self.get_by_code(code):
            code = secrets.token_urlsafe(6)
        link = ReferralLink(code=code, name=name, created_by=admin_id)
        self.session.add(link)
        await self.session.commit()
        await self.session.refresh(link)
        return link

    async def get_by_code(self, code: str) -> ReferralLink | None:
        result = await self.session.execute(
            select(ReferralLink).where(ReferralLink.code == code)
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> list[ReferralLink]:
        result = await self.session.execute(
            select(ReferralLink).order_by(ReferralLink.created_at.desc())
        )
        return list(result.scalars().all())

    async def toggle_active(self, link: ReferralLink) -> ReferralLink:
        link.is_active = not link.is_active
        await self.session.commit()
        return link

    async def get_stats(self, code: str) -> dict:
        """Return total/onboarded/activated counts for a referral code."""
        base = select(func.count()).where(User.referral_code == code)
        total = (await self.session.execute(base)).scalar_one()
        onboarded = (await self.session.execute(
            base.where(User.onboarding_complete == True)
        )).scalar_one()
        activated = (await self.session.execute(
            base.where(User.status == "active")
        )).scalar_one()
        return {"total": total, "onboarded": onboarded, "activated": activated}

    async def get_users(self, code: str) -> list[User]:
        result = await self.session.execute(
            select(User).where(User.referral_code == code).order_by(User.created_at.desc())
        )
        return list(result.scalars().all())
