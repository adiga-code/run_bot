from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Material


class MaterialService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_free(self) -> list[Material]:
        result = await self.session.execute(
            select(Material)
            .where(Material.category == "free", Material.is_active == True)
            .order_by(Material.sort_order, Material.id)
        )
        return list(result.scalars().all())

    async def list_premium(self) -> list[Material]:
        result = await self.session.execute(
            select(Material)
            .where(Material.category == "premium", Material.is_active == True)
            .order_by(Material.sort_order, Material.id)
        )
        return list(result.scalars().all())

    async def get(self, material_id: int) -> Material | None:
        result = await self.session.execute(
            select(Material).where(
                Material.id == material_id,
                Material.is_active == True,
            )
        )
        return result.scalar_one_or_none()
