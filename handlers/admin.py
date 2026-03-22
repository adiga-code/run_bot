from datetime import date

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from handlers.utils import safe_answer
from keyboards.builders import kb_admin_approve, kb_admin_level_picker, kb_admin_menu, kb_main_menu
from services.user_service import UserService
from services.whitelist_service import WhitelistService

router = Router()

LEVEL_NAMES = {1: "Start", 2: "Return", 3: "Base", 4: "Stability", 5: "Performance"}


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


# ── /admin menu ────────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "🛠 <b>Панель администратора</b>",
        parse_mode="HTML",
        reply_markup=kb_admin_menu(),
    )


@router.callback_query(F.data == "adm:menu:pending")
async def cb_admin_pending(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)

    from sqlalchemy import select
    from database.models import User

    result = await session.execute(
        select(User).where(User.status == "pending", User.onboarding_complete == True)
    )
    users = list(result.scalars().all())

    if not users:
        await callback.message.answer(
            "✅ Нет пользователей, ожидающих подтверждения.",
            reply_markup=kb_admin_menu(),
        )
        return

    await callback.message.answer(f"⏳ Ожидают подтверждения: <b>{len(users)}</b>", parse_mode="HTML")
    for u in users:
        level_name = LEVEL_NAMES.get(u.level, "?")
        await callback.message.answer(
            f"👤 <b>{u.full_name}</b>\n"
            f"ID: <code>{u.telegram_id}</code>\n"
            f"Уровень: <b>{level_name} ({u.level})</b>",
            parse_mode="HTML",
            reply_markup=kb_admin_approve(u.telegram_id, u.level),
        )


@router.callback_query(F.data == "adm:menu:stats")
async def cb_admin_stats(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)

    user_svc = UserService(session)
    users = await user_svc.all_active()

    level_counts = {k: 0 for k in LEVEL_NAMES}
    for u in users:
        if u.level in level_counts:
            level_counts[u.level] += 1

    level_lines = "\n".join(
        f"  Level {lvl} ({name}): {level_counts[lvl]}"
        for lvl, name in LEVEL_NAMES.items()
    )
    await callback.message.answer(
        f"<b>Статистика бота</b>\n\n"
        f"Активных пользователей: <b>{len(users)}</b>\n\n"
        f"По уровням:\n{level_lines}",
        parse_mode="HTML",
        reply_markup=kb_admin_menu(),
    )


@router.callback_query(F.data == "adm:menu:users")
async def cb_admin_users(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)

    from sqlalchemy import select
    from database.models import User

    result = await session.execute(
        select(User).where(User.onboarding_complete == True).order_by(User.created_at.desc())
    )
    users = list(result.scalars().all())

    if not users:
        await callback.message.answer("Нет зарегистрированных пользователей.", reply_markup=kb_admin_menu())
        return

    lines = [f"<b>Все пользователи ({len(users)}):</b>\n"]
    for u in users:
        level_name = LEVEL_NAMES.get(u.level, "?") if u.level else "—"
        status_icon = "✅" if u.status == "active" else "⏳"
        started = u.program_start_date.strftime("%d.%m") if u.program_start_date else "не начата"
        lines.append(
            f"{status_icon} <b>{u.full_name}</b>\n"
            f"   ID: <code>{u.telegram_id}</code> | {level_name} | Старт: {started}"
        )

    # Split into chunks to avoid Telegram message length limit
    chunk, chunks = [], []
    for line in lines:
        chunk.append(line)
        if len("\n".join(chunk)) > 3000:
            chunks.append("\n".join(chunk[:-1]))
            chunk = [line]
    if chunk:
        chunks.append("\n".join(chunk))

    for i, text in enumerate(chunks):
        await callback.message.answer(
            text,
            parse_mode="HTML",
            reply_markup=kb_admin_menu() if i == len(chunks) - 1 else None,
        )


@router.callback_query(F.data == "adm:menu:whitelist")
async def cb_admin_whitelist(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)

    wl_svc = WhitelistService(session)
    entries = await wl_svc.list_all()

    if not entries:
        await callback.message.answer("Whitelist пуст.", reply_markup=kb_admin_menu())
        return

    lines = [f"<b>Whitelist ({len(entries)} пользователей):</b>\n"]
    for e in entries:
        note = f" — {e.note}" if e.note else ""
        lines.append(f"• <code>{e.telegram_id}</code>{note}")

    await callback.message.answer(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=kb_admin_menu(),
    )


# ── Whitelist management ───────────────────────────────────────────────────────

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

    level_counts = {k: 0 for k in LEVEL_NAMES}
    for u in users:
        if u.level in level_counts:
            level_counts[u.level] += 1

    level_lines = "\n".join(
        f"  Level {lvl} ({name}): {level_counts[lvl]}"
        for lvl, name in LEVEL_NAMES.items()
    )
    text = (
        f"<b>Статистика бота</b>\n\n"
        f"Активных пользователей: <b>{len(users)}</b>\n\n"
        f"По уровням:\n{level_lines}\n"
    )
    await message.answer(text, parse_mode="HTML")


# ── Pending users list ─────────────────────────────────────────────────────────

@router.message(Command("pending"))
async def cmd_pending(message: Message, session: AsyncSession) -> None:
    """List users waiting for level confirmation."""
    if not is_admin(message.from_user.id):
        return

    from sqlalchemy import select
    from database.models import User

    result = await session.execute(
        select(User).where(User.status == "pending", User.onboarding_complete == True)
    )
    users = list(result.scalars().all())

    if not users:
        await message.answer("Нет пользователей, ожидающих подтверждения.")
        return

    for u in users:
        level_name = LEVEL_NAMES.get(u.level, "?")
        text = (
            f"👤 <b>{u.full_name}</b>\n"
            f"ID: <code>{u.telegram_id}</code>\n"
            f"Уровень: <b>{level_name} ({u.level})</b>"
        )
        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=kb_admin_approve(u.telegram_id, u.level),
        )


# ── Level change command (admin can adjust active user's level anytime) ────────

@router.message(Command("set_level"))
async def cmd_set_level(message: Message, session: AsyncSession) -> None:
    """/set_level <user_id> <level 1-5>"""
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Использование: /set_level <telegram_id> <уровень 1-5>")
        return

    try:
        target_id = int(parts[1])
        new_level = int(parts[2])
        assert 1 <= new_level <= 5
    except Exception:
        await message.answer("Неверные аргументы. Пример: /set_level 123456 3")
        return

    user_svc = UserService(session)
    user = await user_svc.get(target_id)
    if not user:
        await message.answer(f"Пользователь {target_id} не найден.")
        return

    await user_svc.update(user, level=new_level)
    level_name = LEVEL_NAMES[new_level]
    await message.answer(
        f"✅ Уровень пользователя <code>{target_id}</code> изменён на "
        f"<b>{level_name} ({new_level})</b>.",
        parse_mode="HTML",
    )


# ── Approval callbacks ─────────────────────────────────────────────────────────

async def _activate_user(
    callback: CallbackQuery,
    session: AsyncSession,
    user_id: int,
    level: int,
) -> None:
    """Common: activate user with given level, notify them, update admin message."""
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return

    user_svc = UserService(session)
    user = await user_svc.get(user_id)

    if not user:
        await safe_answer(callback, text="Пользователь не найден.", show_alert=True)
        return

    if user.status == "active":
        await safe_answer(callback, text="Уже активирован.", show_alert=True)
        return

    await user_svc.update(
        user,
        level=level,
        status="active",
        program_start_date=date.today(),
    )

    level_name = LEVEL_NAMES[level]

    # Edit admin message to mark done
    await callback.message.edit_text(
        callback.message.text + f"\n\n✅ <b>Активирован. Уровень: {level_name} ({level})</b>",
        parse_mode="HTML",
        reply_markup=None,
    )
    await safe_answer(callback)

    # Notify the user
    try:
        await callback.bot.send_message(
            chat_id=user_id,
            text=(
                f"🎉 <b>Тренер подтвердил твой уровень!</b>\n\n"
                f"Твой уровень: <b>{level_name}</b>\n"
                f"Программа стартует <b>сегодня</b>!\n\n"
                f"Каждое утро я буду спрашивать о самочувствии и показывать тренировку.\n"
                f"Начинай прямо сейчас — нажми «Сегодняшняя тренировка» 👇"
            ),
            parse_mode="HTML",
            reply_markup=kb_main_menu(),
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("adm:approve:"))
async def cb_approve(callback: CallbackQuery, session: AsyncSession) -> None:
    """adm:approve:<user_id>:<level>"""
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return

    _, _, user_id_str, level_str = callback.data.split(":")
    await _activate_user(callback, session, int(user_id_str), int(level_str))


@router.callback_query(F.data.startswith("adm:pick:"))
async def cb_pick_level(callback: CallbackQuery) -> None:
    """adm:pick:<user_id> — show level selector."""
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return

    user_id = int(callback.data.split(":")[2])
    await safe_answer(callback)
    await callback.message.answer(
        "Выбери уровень для этого пользователя:",
        reply_markup=kb_admin_level_picker(user_id),
    )


@router.callback_query(F.data.startswith("adm:setlvl:"))
async def cb_set_level_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    """adm:setlvl:<user_id>:<level> — set level and activate."""
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return

    _, _, user_id_str, level_str = callback.data.split(":")
    await callback.message.edit_reply_markup()
    await _activate_user(callback, session, int(user_id_str), int(level_str))
