from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User
from engine.access import has_access
from handlers.utils import safe_answer
from keyboards.builders import kb_material_back, kb_materials_list, kb_materials_menu
from services.material_service import MaterialService
from texts import T

router = Router()


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
    result = await session.execute(
        select(User).where(User.telegram_id == callback.from_user.id)
    )
    user = result.scalar_one_or_none()
    if user is None or not has_access(user):
        await callback.message.answer(
            T.mat.premium_locked,
            parse_mode="HTML",
        )
        return
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

    if material.category == "premium":
        result = await session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        if user is None or not has_access(user):
            await callback.message.answer(T.mat.access_denied, parse_mode="HTML")
            return

    section_cb = "mat:section:free" if material.category == "free" else "mat:section:premium"

    if material.description:
        desc_text = T.mat.detail_text.format(
            title=material.title,
            description=material.description,
        )
        if material.price_label:
            desc_text += T.mat.detail_price_suffix.format(price_label=material.price_label)
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
