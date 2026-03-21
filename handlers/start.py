from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from services.user_service import UserService
from services.whitelist_service import WhitelistService
from keyboards.builders import kb_main_menu

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession) -> None:
    user_id = message.from_user.id

    wl_svc = WhitelistService(session)
    from config import settings
    is_admin = user_id in settings.admin_ids

    if not is_admin and not await wl_svc.is_allowed(user_id):
        await message.answer(
            "👋 Привет!\n\n"
            "Этот бот доступен только участникам беговой программы.\n"
            "Обратитесь к организатору для получения доступа."
        )
        return

    user_svc = UserService(session)
    user, created = await user_svc.get_or_create(
        telegram_id=user_id,
        full_name=message.from_user.full_name or "Участник",
    )

    if created or not user.onboarding_complete:
        from aiogram.fsm.context import FSMContext
        # Onboarding start is handled separately via FSM — just trigger it
        await message.answer(
            "👋 Привет! Я твой беговой помощник на 28 дней.\n\n"
            "Давай познакомимся и подберём программу под тебя.\n"
            "Это займёт около 2 минут.\n\n"
            "Напиши своё <b>полное имя</b> (ФИО):",
            parse_mode="HTML",
        )
        from handlers.onboarding import OnboardingStates
        # FSMContext is injected by aiogram when handler requests it
        # We re-route to onboarding via a separate message trigger
        # The state is set in the onboarding router's entry point
        return

    await message.answer(
        f"С возвращением, {user.full_name.split()[0]}! 👋\n\n"
        "Что делаем сегодня?",
        reply_markup=kb_main_menu(),
    )
