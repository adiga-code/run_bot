import re

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from handlers.utils import safe_answer
from keyboards.builders import kb_admin_menu, kb_admin_referral_detail, kb_admin_referral_list
from services.referral_service import ReferralService
from texts import T

router = Router()

_CODE_RE = re.compile(r"^[a-zA-Z0-9_]{1,50}$")


class ReferralStates(StatesGroup):
    waiting_code = State()
    waiting_name = State()


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_bot_username(message_or_callback) -> str:
    obj = message_or_callback
    bot_me = await obj.bot.get_me()
    return bot_me.username or "bot"


async def _render_link_item(link, bot_username: str, stats: dict) -> str:
    return T.referral.link_item.format(
        name=link.name,
        code=link.code,
        bot_username=bot_username,
        total=stats["total"],
        onboarded=stats["onboarded"],
        activated=stats["activated"],
    )


# ── Admin panel entry ──────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:menu:referrals")
async def cb_admin_referrals(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)

    svc = ReferralService(session)
    links = await svc.list_all()
    bot_username = await _get_bot_username(callback)

    if not links:
        await callback.message.answer(
            T.referral.panel_header + "\n\n" + T.referral.empty,
            parse_mode="HTML",
            reply_markup=kb_admin_referral_list([]),
        )
        return

    lines = [T.referral.panel_header + "\n"]
    for link in links:
        stats = await svc.get_stats(link.code)
        lines.append(await _render_link_item(link, bot_username, stats))

    await callback.message.answer(
        "\n\n".join(lines),
        parse_mode="HTML",
        reply_markup=kb_admin_referral_list(links),
    )


@router.callback_query(F.data == "adm:ref:back")
async def cb_ref_back(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)
    await callback.message.answer(T.admin.panel_header, parse_mode="HTML", reply_markup=kb_admin_menu())


# ── View single link ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm:ref:view:"))
async def cb_ref_view(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)

    code = callback.data.split(":", 3)[3]
    svc = ReferralService(session)
    link = await svc.get_by_code(code)
    if not link:
        await callback.message.answer(T.referral.not_found)
        return

    bot_username = await _get_bot_username(callback)
    stats = await svc.get_stats(code)
    text = await _render_link_item(link, bot_username, stats)

    await callback.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=kb_admin_referral_detail(code),
    )


# ── Create via FSM ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:ref:create")
async def cb_ref_create_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)
    await state.set_state(ReferralStates.waiting_code)
    await callback.message.answer(T.referral.ask_code, parse_mode="HTML")


@router.message(ReferralStates.waiting_code)
async def ref_input_code(message: Message, state: FSMContext, session: AsyncSession) -> None:
    code = message.text.strip() if message.text else ""

    if not code:
        await message.answer(T.referral.err_code_empty)
        return

    if not _CODE_RE.match(code):
        await message.answer(T.referral.err_code_invalid, parse_mode="HTML")
        return

    svc = ReferralService(session)
    if await svc.get_by_code(code):
        await message.answer(T.referral.err_code_exists)
        return

    await state.update_data(ref_code=code)
    await state.set_state(ReferralStates.waiting_name)
    await message.answer(T.referral.ask_name, parse_mode="HTML")


@router.message(ReferralStates.waiting_name)
async def ref_input_name(message: Message, state: FSMContext, session: AsyncSession) -> None:
    name = message.text.strip() if message.text else ""

    if not name:
        await message.answer(T.referral.err_name_empty)
        return

    data = await state.get_data()
    code = data.get("ref_code", "")
    await state.clear()

    svc = ReferralService(session)
    link = await svc.create(code=code, name=name, created_by=message.from_user.id)
    if not link:
        await message.answer(T.referral.err_code_exists)
        return

    bot_username = await _get_bot_username(message)
    await message.answer(
        T.referral.created.format(name=name, code=code, bot_username=bot_username),
        parse_mode="HTML",
        reply_markup=kb_admin_referral_detail(code),
    )


# ── Delete ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm:ref:del:"))
async def cb_ref_delete(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)

    code = callback.data.split(":", 3)[3]
    svc = ReferralService(session)
    link = await svc.get_by_code(code)
    if not link:
        await callback.message.answer(T.referral.not_found)
        return

    name = link.name
    await svc.delete(code)
    await callback.message.answer(
        T.referral.deleted.format(name=name),
        parse_mode="HTML",
        reply_markup=kb_admin_menu(),
    )


# ── Slash command shortcut ─────────────────────────────────────────────────────

@router.message(Command("ref_create"))
async def cmd_ref_create(message: Message, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return

    parts = (message.text or "").split(maxsplit=2)
    # /ref_create <code> <name>
    if len(parts) < 3:
        await message.answer(
            "Использование: /ref_create &lt;код&gt; &lt;название&gt;\n"
            "Пример: <code>/ref_create summer24 Летняя кампания</code>",
            parse_mode="HTML",
        )
        return

    code = parts[1].strip()
    name = parts[2].strip()

    if not _CODE_RE.match(code):
        await message.answer(T.referral.err_code_invalid, parse_mode="HTML")
        return

    svc = ReferralService(session)
    link = await svc.create(code=code, name=name, created_by=message.from_user.id)
    if not link:
        await message.answer(T.referral.err_code_exists)
        return

    bot_username = await _get_bot_username(message)
    await message.answer(
        T.referral.created.format(name=name, code=code, bot_username=bot_username),
        parse_mode="HTML",
        reply_markup=kb_admin_referral_detail(code),
    )


