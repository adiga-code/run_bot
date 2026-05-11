import secrets

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ReferralLink, User


class ReferralService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        name: str,
        admin_id: int | None = None,
        created_by: int | None = None,
        code: str | None = None,
        auto_approve: bool = False,
    ) -> ReferralLink:
        actual_creator = admin_id or created_by or 0
        if not code:
            code = secrets.token_urlsafe(6)
            while await self.get_by_code(code):
                code = secrets.token_urlsafe(6)
        link = ReferralLink(code=code, name=name, created_by=actual_creator, auto_approve=auto_approve)
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

    # Alias for compatibility with main-branch handlers
    async def list_all(self) -> list[ReferralLink]:
        return await self.get_all()

    async def toggle_active(self, link: ReferralLink) -> ReferralLink:
        link.is_active = not link.is_active
        await self.session.commit()
        return link

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

    async def get_users(self, code: str) -> list[User]:
        result = await self.session.execute(
            select(User).where(User.referral_code == code).order_by(User.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete(self, code: str) -> bool:
        link = await self.get_by_code(code)
        if not link:
            return False
        await self.session.delete(link)
        await self.session.commit()
        return True
