from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from engine.access import get_access_status, has_access, trial_days_left, PLAN_PRICES
from handlers.onboarding import OnboardingStates
from handlers.utils import safe_answer
from keyboards.builders import kb_apply, kb_admin_application, kb_main_menu, kb_welcome
from services.user_service import UserService
from services.whitelist_service import WhitelistService
from texts import T

_REF_PREFIX = "ref_"

router = Router()


class ApplicationStates(StatesGroup):
    waiting_name = State()


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    command: CommandObject,
) -> None:
    user_id = message.from_user.id

    # Extract referral code from deep link param (e.g. /start ref_summer24)
    ref_code: str | None = None
    if command.args and command.args.startswith(_REF_PREFIX):
        ref_code = command.args[len(_REF_PREFIX):]

    # Always create/find the user so we can save referral code
    user_svc = UserService(session)
    user, created = await user_svc.get_or_create(
        telegram_id=user_id,
        full_name=message.from_user.full_name or "Участник",
    )
    if ref_code and not user.referral_code:
        await user_svc.update(user, referral_code=ref_code)

    # Onboarding complete — check access status
    if user.onboarding_complete:
        await state.clear()
        access = get_access_status(user)

        if access == "expired":
            from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
            await message.answer(
                "🔒 Ваш пробный период завершён.\n\n"
                f"Оформите подписку, чтобы продолжить тренировки:\n"
                f"• Месяц — {PLAN_PRICES['monthly']} ₽\n"
                f"• Год — {PLAN_PRICES['annual']} ₽",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="💳 Оформить подписку", callback_data="pay:choose_plan")
                ]]),
            )
            return

        name = (user.full_name or "").split()[0]
        if access in ("trial", "trial_warning"):
            days = trial_days_left(user)
            trial_note = f"\n\n⏳ Пробный период: осталось {days} дн." if days is not None else ""
        else:
            trial_note = ""

        await message.answer(
            T.start.welcome_back.format(name=name) + trial_note,
            reply_markup=kb_main_menu(),
        )
        return

    # Everyone else (new users, guests) — welcome screen with Мероприятия / Тренировки
    await state.clear()
    await message.answer(T.events.welcome, parse_mode="HTML", reply_markup=kb_welcome())


# ── "Тренировки" button from welcome screen ───────────────────────────────────

@router.callback_query(F.data == "ev:trainings")
async def cb_welcome_trainings(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await safe_answer(callback)
    user_id = callback.from_user.id
    is_admin_user = user_id in settings.admin_ids

    user_svc = UserService(session)
    user, _ = await user_svc.get_or_create(
        telegram_id=user_id,
        full_name=callback.from_user.full_name or "Участник",
    )

    wl_svc = WhitelistService(session)
    if not is_admin_user and not await wl_svc.is_allowed(user_id):
        # Auto-approve if user came via a referral link with auto_approve=True
        auto_approved = False
        if user.referral_code:
            from services.referral_service import ReferralService
            ref_svc = ReferralService(session)
            ref_link = await ref_svc.get_by_code(user.referral_code)
            if ref_link and ref_link.is_active and ref_link.auto_approve:
                await wl_svc.add(telegram_id=user_id, added_by=0, note=f"авто: {user.referral_code}")
                auto_approved = True

        if not auto_approved:
            await callback.message.answer(T.start.not_allowed, reply_markup=kb_apply())
            return
    await state.set_state(OnboardingStates.last_name)
    await callback.message.answer(T.start.onboarding_intro, parse_mode="HTML")


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
