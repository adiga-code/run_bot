import logging

import httpx
from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from handlers.utils import safe_answer
from keyboards.builders import kb_material_back, kb_materials_list, kb_materials_menu
from services.material_service import MaterialService
from texts import T

router = Router()
logger = logging.getLogger(__name__)

ADMIN_BACKEND = settings.admin_backend_url


def _buy_keyboard(material_id: int, purchase_id: int, payment_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=T.mat.btn_check_payment, callback_data=f"mat:buy_check:{purchase_id}:{material_id}")],
        [InlineKeyboardButton(text="🔗 Перейти к оплате", url=payment_url)],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="mat:section:premium")],
    ])


@router.callback_query(F.data == "mat:menu")
async def cb_mat_menu(callback: CallbackQuery) -> None:
    await safe_answer(callback)
    await callback.message.answer(
        T.mat.menu_text,
        parse_mode="HTML",
        reply_markup=kb_materials_menu(),
    )


@router.callback_query(F.data == "mat:section:free")
async def cb_mat_free(callback: CallbackQuery, session: AsyncSession) -> None:
    await safe_answer(callback)
    svc = MaterialService(session)
    items = await svc.list_free()
    if not items:
        await callback.message.answer(T.mat.base_empty)
        return
    await callback.message.answer(
        T.mat.base_header,
        parse_mode="HTML",
        reply_markup=kb_materials_list(items, back_callback="mat:menu"),
    )


@router.callback_query(F.data == "mat:section:premium")
async def cb_mat_premium(callback: CallbackQuery, session: AsyncSession) -> None:
    await safe_answer(callback)
    svc = MaterialService(session)
    items = await svc.list_premium()
    if not items:
        await callback.message.answer(T.mat.premium_empty)
        return
    await callback.message.answer(
        T.mat.premium_header,
        parse_mode="HTML",
        reply_markup=kb_materials_list(items, back_callback="mat:menu"),
    )


@router.callback_query(F.data.startswith("mat:get:"))
async def cb_mat_get(callback: CallbackQuery, session: AsyncSession) -> None:
    await safe_answer(callback)
    try:
        material_id = int(callback.data.split(":")[2])
    except (IndexError, ValueError):
        await callback.message.answer(T.mat.not_found)
        return

    svc = MaterialService(session)
    material = await svc.get(material_id)
    if not material:
        await callback.message.answer(T.mat.not_found)
        return

    section_cb = "mat:section:free" if material.category == "free" else "mat:section:premium"

    if material.category == "premium" and material.price_rub:
        # Check if already purchased
        purchased = await svc.has_purchased(callback.from_user.id, material_id)
        if not purchased:
            # Show item details with buy button
            if material.description:
                desc_text = T.mat.detail_text.format(
                    title=material.title,
                    description=material.description,
                )
            else:
                desc_text = T.mat.detail_no_desc.format(title=material.title)
            desc_text += T.mat.detail_price_suffix.format(price=material.price_rub)

            buy_kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=T.mat.btn_buy.format(price=material.price_rub),
                    callback_data=f"mat:buy:{material_id}",
                )],
                [InlineKeyboardButton(text="◀️ Назад", callback_data=section_cb)],
            ])
            await callback.message.answer(desc_text, parse_mode="HTML", reply_markup=buy_kb)
            return

    # Free item or already purchased premium — deliver file
    if material.description:
        desc_text = T.mat.detail_text.format(
            title=material.title,
            description=material.description,
        )
    else:
        desc_text = T.mat.detail_no_desc.format(title=material.title)

    await callback.message.answer(
        desc_text,
        parse_mode="HTML",
        reply_markup=kb_material_back(section_cb),
    )

    try:
        await callback.message.answer_document(
            document=material.file_id,
            caption=material.title,
        )
    except Exception:
        await callback.message.answer(T.mat.send_error)


@router.callback_query(F.data.startswith("mat:buy:"))
async def cb_mat_buy(callback: CallbackQuery, session: AsyncSession) -> None:
    await safe_answer(callback)
    try:
        material_id = int(callback.data.split(":")[2])
    except (IndexError, ValueError):
        await callback.message.answer(T.mat.not_found)
        return

    svc = MaterialService(session)
    material = await svc.get(material_id)
    if not material or not material.price_rub:
        await callback.message.answer(T.mat.not_found)
        return

    # Check if already purchased
    if await svc.has_purchased(callback.from_user.id, material_id):
        # Already purchased — deliver file
        await callback.message.answer_document(
            document=material.file_id,
            caption=material.title,
        )
        return

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{ADMIN_BACKEND}/api/materials/{material_id}/purchase",
                json={"user_id": callback.from_user.id},
                headers={"X-Internal-Token": settings.internal_token},
            )
            if resp.status_code == 409:
                # Race condition — already purchased
                await callback.message.answer_document(document=material.file_id, caption=material.title)
                return
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error("Material purchase create error: %s", e)
        await callback.message.answer(T.mat.buy_error)
        return

    purchase_id = data["purchase_id"]
    payment_url = data["payment_url"]

    await callback.message.answer(
        T.mat.payment_link_text,
        reply_markup=_buy_keyboard(material_id, purchase_id, payment_url),
    )


@router.callback_query(F.data.startswith("mat:buy_check:"))
async def cb_mat_buy_check(callback: CallbackQuery) -> None:
    await safe_answer(callback)
    try:
        parts = callback.data.split(":")
        purchase_id = int(parts[2])
        material_id = int(parts[3])
    except (IndexError, ValueError):
        await callback.message.answer(T.mat.not_found)
        return

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{ADMIN_BACKEND}/api/materials/purchase/{purchase_id}/status",
                headers={"X-Internal-Token": settings.internal_token},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error("Material purchase status check error: %s", e)
        await callback.message.answer(T.mat.buy_pending)
        return

    if data["status"] == "confirmed":
        await callback.message.answer(T.mat.buy_success)
        file_id = data.get("file_id")
        title = data.get("title", "")
        if file_id:
            try:
                await callback.message.answer_document(document=file_id, caption=title)
            except Exception:
                await callback.message.answer(T.mat.send_error)
    else:
        await callback.message.answer(T.mat.buy_pending)
