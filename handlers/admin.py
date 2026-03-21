from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from services.whitelist_service import WhitelistService
from services.user_service import UserService

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


@router.message(Command("add_user"))
async def cmd_add_user(message: Message, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        await message.answer("Использование: /add_user <telegram_id> [заметка]")
        return

    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer("Telegram ID должен быть числом.")
        return

    note = parts[2] if len(parts) == 3 else None
    svc = WhitelistService(session)

    if await svc.is_allowed(target_id):
        await message.answer(f"Пользователь {target_id} уже в списке.")
        return

    await svc.add(telegram_id=target_id, added_by=message.from_user.id, note=note)
    await message.answer(f"✅ Пользователь {target_id} добавлен в whitelist.")


@router.message(Command("remove_user"))
async def cmd_remove_user(message: Message, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /remove_user <telegram_id>")
        return

    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer("Telegram ID должен быть числом.")
        return

    svc = WhitelistService(session)
    removed = await svc.remove(target_id)
    if removed:
        await message.answer(f"✅ Пользователь {target_id} удалён из whitelist.")
    else:
        await message.answer(f"Пользователь {target_id} не найден в whitelist.")


@router.message(Command("list_users"))
async def cmd_list_users(message: Message, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return

    wl_svc = WhitelistService(session)
    entries = await wl_svc.list_all()

    if not entries:
        await message.answer("Whitelist пуст.")
        return

    lines = [f"<b>Whitelist ({len(entries)} пользователей):</b>\n"]
    for e in entries:
        note = f" — {e.note}" if e.note else ""
        lines.append(f"• <code>{e.telegram_id}</code>{note}")

    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return

    user_svc = UserService(session)
    users = await user_svc.all_active()

    level_counts = {1: 0, 2: 0, 3: 0, 4: 0}
    for u in users:
        if u.level in level_counts:
            level_counts[u.level] += 1

    text = (
        f"<b>Статистика бота</b>\n\n"
        f"Активных пользователей: <b>{len(users)}</b>\n\n"
        f"По уровням:\n"
        f"  Level 1 (Start): {level_counts[1]}\n"
        f"  Level 2 (Return): {level_counts[2]}\n"
        f"  Level 3 (Base): {level_counts[3]}\n"
        f"  Level 4 (Stability): {level_counts[4]}\n"
    )
    await message.answer(text, parse_mode="HTML")
