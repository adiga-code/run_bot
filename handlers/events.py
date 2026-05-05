import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from handlers.utils import safe_answer
from keyboards.builders import (
    kb_admin_event_detail, kb_admin_events_list, kb_admin_menu,
    kb_event_detail, kb_events_list, kb_skip_email, kb_welcome,
)
from services.event_service import EventService
from texts import T

router = Router()

_PHONE_RE = re.compile(r"^[\d\s\+\-\(\)]{7,20}$")


class EventRegStates(StatesGroup):
    waiting_name  = State()
    waiting_phone = State()
    waiting_email = State()


class EventCreateStates(StatesGroup):
    waiting_title       = State()
    waiting_date_label  = State()
    waiting_description = State()
    waiting_channel     = State()


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


# ═══════════════════════════════════════════════════════════════════════════════
# USER FLOW
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "ev:list")
async def cb_events_list(callback: CallbackQuery, session: AsyncSession) -> None:
    await safe_answer(callback)
    svc = EventService(session)
    events = await svc.list_active()
    if not events:
        await callback.message.answer(T.events.no_events)
        return
    await callback.message.answer(
        T.events.events_header,
        parse_mode="HTML",
        reply_markup=kb_events_list(events),
    )


@router.callback_query(F.data.startswith("ev:view:"))
async def cb_event_view(callback: CallbackQuery, session: AsyncSession) -> None:
    await safe_answer(callback)
    event_id = int(callback.data.split(":")[2])
    svc = EventService(session)
    event = await svc.get(event_id)
    if not event or not event.is_active:
        await callback.message.answer(T.events.no_events)
        return
    text = T.events.event_detail.format(
        title=event.title,
        date_label=event.date_label,
        description=event.description,
    )
    await callback.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=kb_event_detail(event_id),
    )


@router.callback_query(F.data.startswith("ev:reg:"))
async def cb_event_reg_start(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await safe_answer(callback)
    event_id = int(callback.data.split(":")[2])
    svc = EventService(session)
    event = await svc.get(event_id)
    if not event or not event.is_active:
        await callback.message.answer(T.events.no_events)
        return
    if await svc.already_registered(event_id, callback.from_user.id):
        await callback.message.answer(T.events.already_registered)
        return
    await state.update_data(reg_event_id=event_id)
    await state.set_state(EventRegStates.waiting_name)
    await callback.message.answer(T.events.ask_name, parse_mode="HTML")


@router.message(EventRegStates.waiting_name)
async def ev_reg_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer(T.events.err_name)
        return
    await state.update_data(reg_name=name)
    await state.set_state(EventRegStates.waiting_phone)
    await message.answer(T.events.ask_phone, parse_mode="HTML")


@router.message(EventRegStates.waiting_phone)
async def ev_reg_phone(message: Message, state: FSMContext) -> None:
    phone = (message.text or "").strip()
    if not _PHONE_RE.match(phone):
        await message.answer(T.events.err_phone)
        return
    await state.update_data(reg_phone=phone)
    await state.set_state(EventRegStates.waiting_email)
    await message.answer(T.events.ask_email, parse_mode="HTML", reply_markup=kb_skip_email())


@router.callback_query(F.data == "ev:skip_email")
async def ev_reg_skip_email(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await safe_answer(callback)
    await _finish_registration(callback.message, state, session, callback.from_user, email=None)


@router.message(EventRegStates.waiting_email)
async def ev_reg_email(message: Message, state: FSMContext, session: AsyncSession) -> None:
    email = (message.text or "").strip() or None
    await _finish_registration(message, state, session, message.from_user, email=email)


async def _finish_registration(message, state, session, tg_user, email):
    data = await state.get_data()
    await state.clear()

    event_id = data["reg_event_id"]
    full_name = data["reg_name"]
    phone = data["reg_phone"]

    svc = EventService(session)
    event = await svc.get(event_id)
    if not event:
        await message.answer(T.events.no_events)
        return

    reg = await svc.register(
        event_id=event_id,
        telegram_id=tg_user.id,
        tg_username=tg_user.username,
        full_name=full_name,
        phone=phone,
        email=email,
    )

    # Notify admins
    tg_link = f"@{tg_user.username}" if tg_user.username else f"id:{tg_user.id}"
    admin_text = T.events.admin_new_reg.format(
        event_title=event.title,
        full_name=full_name,
        phone=phone,
        email=email or "—",
        tg_link=tg_link,
        telegram_id=tg_user.id,
    )
    for admin_id in settings.admin_ids:
        try:
            await message.bot.send_message(chat_id=admin_id, text=admin_text, parse_mode="HTML")
        except Exception:
            pass

    # Thank-you message
    if event.channel_link:
        text = T.events.registered_ok.format(
            title=event.title,
            date_label=event.date_label,
            channel_link=event.channel_link,
        )
    else:
        text = T.events.registered_no_link
    await message.answer(text, parse_mode="HTML")


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN — EVENT MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "adm:menu:events")
async def cb_admin_events(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)
    svc = EventService(session)
    events = await svc.list_all()
    await callback.message.answer(
        T.events.adm_panel_header,
        parse_mode="HTML",
        reply_markup=kb_admin_events_list(events),
    )


@router.callback_query(F.data == "adm:ev:back")
async def cb_adm_ev_back(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)
    await callback.message.answer(T.admin.panel_header, parse_mode="HTML", reply_markup=kb_admin_menu())


@router.callback_query(F.data.startswith("adm:ev:view:"))
async def cb_adm_event_view(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)
    event_id = int(callback.data.split(":")[3])
    svc = EventService(session)
    event = await svc.get(event_id)
    if not event:
        await callback.message.answer("Мероприятие не найдено.")
        return
    reg_count = await svc.count_registrations(event_id)
    icon = T.events.adm_active_icon if event.is_active else T.events.adm_inactive_icon
    text = T.events.adm_event_detail.format(
        active_icon=icon,
        title=event.title,
        date_label=event.date_label,
        channel_link=event.channel_link or "—",
        reg_count=reg_count,
        description=event.description,
    )
    await callback.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=kb_admin_event_detail(event_id, event.is_active),
    )


@router.callback_query(F.data.startswith("adm:ev:toggle:"))
async def cb_adm_event_toggle(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)
    event_id = int(callback.data.split(":")[3])
    svc = EventService(session)
    event = await svc.toggle_active(event_id)
    if not event:
        await callback.message.answer("Мероприятие не найдено.")
        return
    msg = T.events.adm_toggled_on if event.is_active else T.events.adm_toggled_off
    await callback.message.answer(
        msg,
        reply_markup=kb_admin_event_detail(event_id, event.is_active),
    )


@router.callback_query(F.data.startswith("adm:ev:regs:"))
async def cb_adm_event_regs(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)
    event_id = int(callback.data.split(":")[3])
    svc = EventService(session)
    event = await svc.get(event_id)
    if not event:
        await callback.message.answer("Мероприятие не найдено.")
        return
    regs = await svc.get_registrations(event_id)
    if not regs:
        await callback.message.answer(T.events.adm_no_regs)
        return
    lines = [T.events.adm_regs_header.format(title=event.title, n=len(regs))]
    for i, reg in enumerate(regs, 1):
        tg_link = f"@{reg.tg_username}" if reg.tg_username else f"id:{reg.telegram_id}"
        lines.append(T.events.adm_reg_line.format(
            i=i,
            full_name=reg.full_name,
            phone=reg.phone,
            email=reg.email or "—",
            tg_link=tg_link,
        ))
    await callback.message.answer("\n".join(lines), parse_mode="HTML")


@router.callback_query(F.data.startswith("adm:ev:del:"))
async def cb_adm_event_delete(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)
    event_id = int(callback.data.split(":")[3])
    svc = EventService(session)
    event = await svc.get(event_id)
    if not event:
        await callback.message.answer("Мероприятие не найдено.")
        return
    title = event.title
    await svc.delete(event_id)
    await callback.message.answer(
        T.events.adm_deleted.format(title=title),
        parse_mode="HTML",
        reply_markup=kb_admin_menu(),
    )


# ── Create event FSM ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "adm:ev:create")
async def cb_adm_ev_create_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)
    await state.set_state(EventCreateStates.waiting_title)
    await callback.message.answer(T.events.ask_title, parse_mode="HTML")


@router.message(EventCreateStates.waiting_title)
async def ev_create_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer(T.events.ask_title, parse_mode="HTML")
        return
    await state.update_data(ev_title=title)
    await state.set_state(EventCreateStates.waiting_date_label)
    await message.answer(T.events.ask_date_label, parse_mode="HTML")


@router.message(EventCreateStates.waiting_date_label)
async def ev_create_date(message: Message, state: FSMContext) -> None:
    date_label = (message.text or "").strip()
    if not date_label:
        await message.answer(T.events.ask_date_label, parse_mode="HTML")
        return
    await state.update_data(ev_date_label=date_label)
    await state.set_state(EventCreateStates.waiting_description)
    await message.answer(T.events.ask_description, parse_mode="HTML")


@router.message(EventCreateStates.waiting_description)
async def ev_create_description(message: Message, state: FSMContext) -> None:
    description = (message.text or "").strip()
    if not description:
        await message.answer(T.events.ask_description, parse_mode="HTML")
        return
    await state.update_data(ev_description=description)
    await state.set_state(EventCreateStates.waiting_channel)
    await message.answer(T.events.ask_channel, parse_mode="HTML", reply_markup=kb_skip_email())


@router.callback_query(F.data == "ev:skip_email", EventCreateStates.waiting_channel)
async def ev_create_skip_channel(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await safe_answer(callback)
    await _finish_create_event(callback.message, state, session, callback.from_user.id, channel=None)


@router.message(EventCreateStates.waiting_channel)
async def ev_create_channel(message: Message, state: FSMContext, session: AsyncSession) -> None:
    channel = (message.text or "").strip() or None
    await _finish_create_event(message, state, session, message.from_user.id, channel=channel)


async def _finish_create_event(message, state, session, admin_id, channel):
    data = await state.get_data()
    await state.clear()
    svc = EventService(session)
    event = await svc.create(
        title=data["ev_title"],
        date_label=data["ev_date_label"],
        description=data["ev_description"],
        channel_link=channel,
        created_by=admin_id,
    )
    await message.answer(
        T.events.adm_created.format(title=event.title, date_label=event.date_label),
        parse_mode="HTML",
        reply_markup=kb_admin_event_detail(event.id, event.is_active),
    )
