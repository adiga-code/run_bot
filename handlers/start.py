from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from handlers.onboarding import OnboardingStates
from handlers.utils import safe_answer
from keyboards.builders import kb_apply, kb_admin_application, kb_main_menu
from services.user_service import UserService
from services.whitelist_service import WhitelistService
from texts import T

router = Router()


class ApplicationStates(StatesGroup):
    waiting_name = State()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user_id = message.from_user.id

    wl_svc = WhitelistService(session)
    is_admin = user_id in settings.admin_ids

    if not is_admin and not await wl_svc.is_allowed(user_id):
        await state.clear()
        await message.answer(T.start.not_allowed, reply_markup=kb_apply())
        return

    user_svc = UserService(session)
    user, created = await user_svc.get_or_create(
        telegram_id=user_id,
        full_name=message.from_user.full_name or "Участник",
    )

    # Store referral code on first visit (deep link: /start <code>)
    if created and not user.referral_code:
        payload = message.text.split(maxsplit=1)[1] if " " in (message.text or "") else ""
        if payload:
            from services.referral_service import ReferralService
            ref_svc = ReferralService(session)
            ref_link = await ref_svc.get_by_code(payload)
            if ref_link and ref_link.is_active:
                await user_svc.update(user, referral_code=payload)

    if created or not user.onboarding_complete:
        await state.set_state(OnboardingStates.last_name)
        await message.answer(T.start.onboarding_intro, parse_mode="HTML")
        return

    await message.answer(
        T.start.welcome_back.format(name=user.full_name.split()[0]),
        reply_markup=kb_main_menu(),
    )


# ── Application flow ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "app:start")
async def cb_apply_start(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_answer(callback)
    await state.set_state(ApplicationStates.waiting_name)
    await callback.message.answer(T.start.ask_app_name, parse_mode="HTML")


@router.message(ApplicationStates.waiting_name)
async def apply_name(message: Message, state: FSMContext, session: AsyncSession) -> None:
    name = message.text.strip()
    if len(name) < 2:
        await message.answer(T.start.err_name)
        return

    await state.clear()

    # Save name to DB now so onboarding won't ask for it again
    user_svc = UserService(session)
    user, _ = await user_svc.get_or_create(telegram_id=message.from_user.id, full_name=name)
    if user.full_name != name:
        await user_svc.update(user, full_name=name)

    user_id = message.from_user.id
    tg_link = f"@{message.from_user.username}" if message.from_user.username else f"id:{user_id}"

    admin_text = T.start.admin_new_app.format(name=name, tg_link=tg_link, user_id=user_id)

    sent = False
    for admin_id in settings.admin_ids:
        try:
            await message.bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                parse_mode="HTML",
                reply_markup=kb_admin_application(user_id),
            )
            sent = True
        except Exception:
            pass

    if sent:
        await message.answer(T.start.application_sent, parse_mode="HTML")
    else:
        await message.answer(T.start.application_failed)
