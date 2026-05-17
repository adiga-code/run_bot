from datetime import timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Material, MaterialPurchase


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

    async def has_purchased(self, user_id: int, material_id: int) -> bool:
        result = await self.session.execute(
            select(MaterialPurchase).where(
                MaterialPurchase.user_id == user_id,
                MaterialPurchase.material_id == material_id,
                MaterialPurchase.status == "confirmed",
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_pending_purchase(self, user_id: int, material_id: int) -> MaterialPurchase | None:
        result = await self.session.execute(
            select(MaterialPurchase).where(
                MaterialPurchase.user_id == user_id,
                MaterialPurchase.material_id == material_id,
                MaterialPurchase.status == "pending",
            )
        )
        return result.scalar_one_or_none()

    async def get_purchase_by_yookassa(self, yookassa_id: str) -> MaterialPurchase | None:
        result = await self.session.execute(
            select(MaterialPurchase).where(MaterialPurchase.yookassa_id == yookassa_id)
        )
        return result.scalar_one_or_none()

    async def create_purchase(
        self, user_id: int, material_id: int, amount: int, yookassa_id: str
    ) -> MaterialPurchase:
        from datetime import datetime
        purchase = MaterialPurchase(
            user_id=user_id,
            material_id=material_id,
            amount=amount,
            yookassa_id=yookassa_id,
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(purchase)
        await self.session.commit()
        await self.session.refresh(purchase)
        return purchase

    async def confirm_purchase(self, purchase: MaterialPurchase) -> MaterialPurchase:
        from datetime import datetime
        purchase.status = "confirmed"
        purchase.confirmed_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(purchase)
        return purchase
