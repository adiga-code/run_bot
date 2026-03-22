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
        await message.answer(
            "👋 Привет!\n\n"
            "Этот бот доступен только участникам беговой программы.\n\n"
            "Хочешь присоединиться? Подай заявку — тренер рассмотрит её и даст доступ 👇",
            reply_markup=kb_apply(),
        )
        return

    user_svc = UserService(session)
    user, created = await user_svc.get_or_create(
        telegram_id=user_id,
        full_name=message.from_user.full_name or "Участник",
    )

    if created or not user.onboarding_complete:
        await state.set_state(OnboardingStates.full_name)
        await message.answer(
            "👋 Привет! Я твой беговой помощник на 28 дней.\n\n"
            "Давай познакомимся и подберём программу под тебя.\n"
            "Это займёт около 2 минут.\n\n"
            "Напиши своё <b>полное имя</b> (ФИО):",
            parse_mode="HTML",
        )
        return

    await message.answer(
        f"С возвращением, {user.full_name.split()[0]}! 👋\n\n"
        "Что делаем сегодня?",
        reply_markup=kb_main_menu(),
    )


# ── Application flow ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "app:start")
async def cb_apply_start(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_answer(callback)
    await state.set_state(ApplicationStates.waiting_name)
    await callback.message.answer(
        "Напиши своё <b>имя и фамилию</b> — тренер увидит их в заявке:",
        parse_mode="HTML",
    )


@router.message(ApplicationStates.waiting_name)
async def apply_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Пожалуйста, введи настоящее имя.")
        return

    await state.clear()

    user_id = message.from_user.id
    tg_link = f"@{message.from_user.username}" if message.from_user.username else f"id:{user_id}"

    admin_text = (
        f"📝 <b>Новая заявка на участие!</b>\n\n"
        f"Имя: <b>{name}</b>\n"
        f"Telegram: {tg_link}\n"
        f"ID: <code>{user_id}</code>"
    )

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
        await message.answer(
            "✅ <b>Заявка отправлена!</b>\n\n"
            "Тренер рассмотрит её и даст тебе доступ. Ожидай сообщения от бота.",
            parse_mode="HTML",
        )
    else:
        await message.answer(
            "⚠️ Не удалось отправить заявку. Обратитесь к тренеру напрямую."
        )
