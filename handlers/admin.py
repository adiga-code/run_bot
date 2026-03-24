import logging
from datetime import date

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from handlers.utils import safe_answer
from keyboards.builders import (
    kb_admin_application, kb_admin_approve, kb_admin_day_mode, kb_admin_level_picker,
    kb_admin_manage, kb_admin_menu, kb_admin_report_actions, kb_admin_report_users,
    kb_admin_start_choice, kb_main_menu,
)
from services.user_service import UserService
from services.whitelist_service import WhitelistService

logger = logging.getLogger(__name__)


class AdminActionStates(StatesGroup):
    jump_day = State()
    send_msg = State()

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


@router.callback_query(F.data == "adm:broadcast:checkin")
async def cb_broadcast_checkin(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)

    from datetime import date as date_cls
    from database.models import SessionLog
    from services.session_log_service import SessionLogService

    user_svc = UserService(session)
    log_svc = SessionLogService(session)
    users = await user_svc.all_active()

    sent, skipped = 0, 0
    for user in users:
        day = await user_svc.current_program_day(user)
        if not day:
            skipped += 1
            continue
        # Ensure today's log exists
        await log_svc.get_or_create_today(user.telegram_id, day)
        try:
            await callback.bot.send_message(
                chat_id=user.telegram_id,
                text=(
                    "🌅 Доброе утро!\n\n"
                    "Время пройти утренний чек-ин и узнать свою тренировку на сегодня.\n\n"
                    "Нажми /checkin или кнопку ниже 👇"
                ),
                reply_markup=kb_main_menu(),
            )
            sent += 1
        except Exception:
            skipped += 1

    logger.info("Admin %s broadcast checkin: sent=%s skipped=%s", callback.from_user.id, sent, skipped)
    await callback.message.answer(
        f"✅ Чек-ин отправлен: <b>{sent}</b> пользователей\n"
        f"Пропущено (заблокировали бот или нет дня): <b>{skipped}</b>",
        parse_mode="HTML",
        reply_markup=kb_admin_menu(),
    )


@router.callback_query(F.data.in_({"adm:menu:reports", "adm:menu:back"}))
async def cb_admin_reports(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)

    from sqlalchemy import select
    from database.models import User

    result = await session.execute(
        select(User)
        .where(User.onboarding_complete == True, User.status == "active")
        .order_by(User.full_name)
    )
    users = list(result.scalars().all())

    if not users:
        await callback.message.answer("Нет активных пользователей.", reply_markup=kb_admin_menu())
        return

    await callback.message.answer(
        f"📋 <b>Отчёты</b>\n\nВыбери пользователя ({len(users)}):",
        parse_mode="HTML",
        reply_markup=kb_admin_report_users(users),
    )


@router.callback_query(F.data.startswith("adm:report:view:"))
async def cb_report_view(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)

    user_id = int(callback.data.split(":")[3])
    await _send_report(callback.message, session, user_id, as_file=False)


@router.callback_query(F.data.startswith("adm:report:csv:"))
async def cb_report_csv(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)

    user_id = int(callback.data.split(":")[3])
    await _send_report(callback.message, session, user_id, as_file=True)


async def _send_report(message, session: AsyncSession, user_id: int, as_file: bool) -> None:
    import io
    from sqlalchemy import select
    from database.models import User, SessionLog, Workout

    user_svc = UserService(session)
    user = await user_svc.get(user_id)
    if not user:
        await message.answer("Пользователь не найден.")
        return

    result = await session.execute(
        select(SessionLog, Workout)
        .outerjoin(Workout, SessionLog.assigned_workout_id == Workout.id)
        .where(SessionLog.user_id == user_id)
        .order_by(SessionLog.day_index)
    )
    rows = result.all()

    WELLBEING = {1: "Плохо", 2: "Тяжеловато", 3: "Нормально", 4: "Отлично"}
    SLEEP = {1: "Плохо", 2: "Нормально", 3: "Хорошо"}
    PAIN = {1: "Нет", 2: "Немного", 3: "Есть"}
    STATUS = {"done": "✅ Выполнено", "partial": "⚡ Частично", "skipped": "❌ Пропущено"}
    VERSION = {"base": "Base", "light": "Light", "recovery": "Recovery"}
    DAY_TYPE = {"run": "Бег", "strength": "Силовая", "recovery": "Восстановление", "rest": "Отдых"}

    level_name = LEVEL_NAMES.get(user.level, "?")
    current_day = await user_svc.current_program_day(user) or "?"

    if as_file:
        buf = io.StringIO()
        buf.write("День,Дата,Тип,Режим,Самочувствие,Сон,Боль,Статус\n")
        for log, workout in rows:
            buf.write(",".join([
                str(log.day_index),
                str(log.date),
                DAY_TYPE.get(workout.day_type, "—") if workout else "—",
                VERSION.get(log.assigned_version, "—") if log.assigned_version else "—",
                WELLBEING.get(log.wellbeing, "—") if log.wellbeing else "—",
                SLEEP.get(log.sleep_quality, "—") if log.sleep_quality else "—",
                PAIN.get(log.pain_level, "—") if log.pain_level else "—",
                log.completion_status or "—",
            ]) + "\n")

        from aiogram.types import BufferedInputFile
        file = BufferedInputFile(
            buf.getvalue().encode("utf-8-sig"),
            filename=f"report_{user.full_name.replace(' ', '_')}.csv",
        )
        await message.answer_document(
            file,
            caption=f"📥 Отчёт: {user.full_name}",
        )
        return

    # Text view
    if not rows:
        await message.answer(
            f"По пользователю <b>{user.full_name}</b> данных нет.",
            parse_mode="HTML",
            reply_markup=kb_admin_menu(),
        )
        return

    lines = [f"📋 <b>{user.full_name}</b> | {level_name} | День {current_day}/28\n"]
    for log, workout in rows:
        day_type = DAY_TYPE.get(workout.day_type, "—") if workout else "—"
        version = VERSION.get(log.assigned_version, "—") if log.assigned_version else "—"
        status = STATUS.get(log.completion_status, "—") if log.completion_status else "—"
        lines.append(f"День {log.day_index:>2} | {day_type:<14} | {version:<8} | {status}")

    text = "\n".join(lines)
    # Split if too long
    chunks = [text[i:i+3800] for i in range(0, len(text), 3800)]
    for i, chunk in enumerate(chunks):
        await message.answer(
            f"<pre>{chunk}</pre>" if i > 0 else chunk,
            parse_mode="HTML",
            reply_markup=kb_admin_report_actions(user_id) if i == len(chunks) - 1 else None,
        )


# ── User management ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm:manage:"))
async def cb_admin_manage(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)

    user_id = int(callback.data.split(":")[2])
    user_svc = UserService(session)
    user = await user_svc.get(user_id)
    if not user:
        await callback.message.answer("Пользователь не найден.")
        return

    current_day = await user_svc.current_program_day(user) or "?"
    level_name = LEVEL_NAMES.get(user.level, "?")
    await callback.message.answer(
        f"⚙️ <b>{user.full_name}</b>\n"
        f"Уровень: {level_name} | День: {current_day}/28",
        parse_mode="HTML",
        reply_markup=kb_admin_manage(user_id),
    )


@router.callback_query(F.data.startswith("adm:mode:") & ~F.data.startswith("adm:mode:set:"))
async def cb_admin_mode_picker(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)

    user_id = int(callback.data.split(":")[2])
    await callback.message.answer(
        "Выбери режим на сегодня:",
        reply_markup=kb_admin_day_mode(user_id),
    )


@router.callback_query(F.data.startswith("adm:mode:set:"))
async def cb_admin_mode_set(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return

    parts = callback.data.split(":")
    # adm:mode:set:<user_id>:<version>
    user_id, version = int(parts[3]), parts[4]
    await safe_answer(callback)

    from datetime import date as date_cls
    from sqlalchemy import select
    from database.models import SessionLog

    result = await session.execute(
        select(SessionLog).where(
            SessionLog.user_id == user_id,
            SessionLog.date == date_cls.today(),
        )
    )
    log = result.scalar_one_or_none()
    if not log:
        await callback.message.answer("Лог на сегодня не найден. Пользователь ещё не начал день.")
        return

    log.assigned_version = version
    await session.commit()

    version_names = {"base": "Base (полная)", "light": "Light (лёгкая)", "recovery": "Recovery (восстановление)"}
    await callback.message.answer(f"✅ Режим изменён на <b>{version_names[version]}</b>.", parse_mode="HTML")

    try:
        await callback.bot.send_message(
            chat_id=user_id,
            text=f"🔄 Тренер скорректировал твою тренировку на сегодня.\n\n"
                 f"Новый режим: <b>{version_names[version]}</b>\n\n"
                 f"Нажми «Сегодняшняя тренировка» чтобы увидеть обновлённый план.",
            parse_mode="HTML",
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("adm:jump:"))
async def cb_admin_jump(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)

    user_id = int(callback.data.split(":")[2])
    await state.set_state(AdminActionStates.jump_day)
    await state.update_data(target_user_id=user_id)
    await callback.message.answer("Введи номер дня (1–28) куда перенести пользователя:")


@router.message(AdminActionStates.jump_day)
async def admin_jump_day_input(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    target_user_id = data["target_user_id"]

    try:
        target_day = int(message.text.strip())
        assert 1 <= target_day <= 28
    except Exception:
        await message.answer("Введи число от 1 до 28.")
        return

    await state.clear()

    from datetime import timedelta
    user_svc = UserService(session)
    user = await user_svc.get(target_user_id)
    if not user:
        await message.answer("Пользователь не найден.")
        return

    new_start = date.today() - timedelta(days=target_day - 1)
    await user_svc.update(user, program_start_date=new_start, week_repeat_count=0)

    # Delete today's SessionLog so the next checkin creates a fresh one with the correct day_index
    from database.models import SessionLog
    await session.execute(
        delete(SessionLog).where(
            SessionLog.user_id == target_user_id,
            SessionLog.date == date.today(),
        )
    )
    await session.commit()
    logger.info("Admin %s jumped user %s to day %s; deleted today's SessionLog", message.from_user.id, target_user_id, target_day)

    await message.answer(f"✅ Пользователь переведён на <b>день {target_day}</b>.", parse_mode="HTML")

    try:
        await message.bot.send_message(
            chat_id=target_user_id,
            text=f"📅 Тренер скорректировал твой прогресс.\n\nСегодня у тебя <b>день {target_day}</b>.",
            parse_mode="HTML",
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("adm:msg:"))
async def cb_admin_send_msg(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)

    user_id = int(callback.data.split(":")[2])
    await state.set_state(AdminActionStates.send_msg)
    await state.update_data(target_user_id=user_id)
    await callback.message.answer("Напиши сообщение для пользователя:")


@router.message(AdminActionStates.send_msg)
async def admin_send_msg_input(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    target_user_id = data["target_user_id"]
    await state.clear()

    try:
        await message.bot.send_message(
            chat_id=target_user_id,
            text=f"💬 <b>Сообщение от тренера:</b>\n\n{message.text}",
            parse_mode="HTML",
        )
        await message.answer("✅ Сообщение отправлено.")
    except Exception as e:
        await message.answer(f"❌ Не удалось отправить: {e}")


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


# ── Application approve / reject ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm:app:approve:"))
async def cb_app_approve(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return

    user_id = int(callback.data.split(":")[3])
    wl_svc = WhitelistService(session)

    if await wl_svc.is_allowed(user_id):
        await safe_answer(callback, text="Уже в whitelist.", show_alert=True)
        return

    await wl_svc.add(telegram_id=user_id, added_by=callback.from_user.id, note="заявка")
    await callback.message.edit_reply_markup()
    await callback.message.edit_text(
        callback.message.text + "\n\n✅ <b>Одобрено</b>",
        parse_mode="HTML",
    )
    await safe_answer(callback)

    try:
        await callback.bot.send_message(
            chat_id=user_id,
            text=(
                "🎉 <b>Твоя заявка одобрена!</b>\n\n"
                "Добро пожаловать в программу! Нажми /start чтобы начать."
            ),
            parse_mode="HTML",
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("adm:app:reject:"))
async def cb_app_reject(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return

    user_id = int(callback.data.split(":")[3])
    await callback.message.edit_reply_markup()
    await callback.message.edit_text(
        callback.message.text + "\n\n❌ <b>Отклонено</b>",
        parse_mode="HTML",
    )
    await safe_answer(callback)

    try:
        await callback.bot.send_message(
            chat_id=user_id,
            text=(
                "😔 К сожалению, твоя заявка не была одобрена.\n\n"
                "Если считаешь это ошибкой — обратись к тренеру напрямую."
            ),
        )
    except Exception:
        pass


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


# ── Reset user progress ────────────────────────────────────────────────────────

@router.message(Command("reset_user"))
async def cmd_reset_user(message: Message, session: AsyncSession) -> None:
    """/reset_user <user_id> — reset progress, send back to onboarding."""
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /reset_user <telegram_id>")
        return

    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer("Telegram ID должен быть числом.")
        return

    user_svc = UserService(session)
    user = await user_svc.get(target_id)
    if not user:
        await message.answer(f"Пользователь {target_id} не найден.")
        return

    await user_svc.reset_progress(user)
    await message.answer(
        f"✅ Прогресс пользователя <code>{target_id}</code> сброшен.\n"
        f"Онбординг будет пройден заново при следующем /start.",
        parse_mode="HTML",
    )

    try:
        await message.bot.send_message(
            chat_id=target_id,
            text=(
                "🔄 Тренер сбросил твой прогресс.\n\n"
                "Напиши /start чтобы пройти анкету заново."
            ),
        )
    except Exception:
        pass


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
    logger.info("Admin %s set user %s to level=%s (%s)", message.from_user.id, target_id, new_level, level_name)
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
    start_today: bool,
) -> None:
    """Activate user with given level and start date."""
    from datetime import timedelta
    user_svc = UserService(session)
    user = await user_svc.get(user_id)

    if not user:
        await safe_answer(callback, text="Пользователь не найден.", show_alert=True)
        return

    if user.status == "active":
        await safe_answer(callback, text="Уже активирован.", show_alert=True)
        return

    start_date = date.today() if start_today else date.today() + timedelta(days=1)
    await user_svc.update(user, level=level, status="active", program_start_date=start_date)

    if start_today:
        from database.models import SessionLog
        day1_log = SessionLog(
            user_id=user.telegram_id,
            date=date.today(),
            day_index=1,
        )
        session.add(day1_log)
        await session.commit()
        logger.info("Admin %s activated user %s with start_today; created Day 1 SessionLog", callback.from_user.id, user_id)
    else:
        logger.info("Admin %s activated user %s (start tomorrow, level=%s)", callback.from_user.id, user_id, level)

    level_name = LEVEL_NAMES[level]
    start_label = "сегодня" if start_today else "завтра"

    await callback.message.edit_text(
        callback.message.text + f"\n\n✅ <b>Активирован. Уровень: {level_name} ({level}). Старт: {start_label}</b>",
        parse_mode="HTML",
        reply_markup=None,
    )
    await safe_answer(callback)

    user_text = (
        f"🎉 <b>Тренер подтвердил твой уровень!</b>\n\n"
        f"Твой уровень: <b>{level_name}</b>\n"
        f"Программа стартует <b>{start_label}</b>!\n\n"
        f"Каждое утро я буду спрашивать о самочувствии и показывать тренировку."
    )
    if start_today:
        user_text += "\n\nНачинай прямо сейчас 👇"
    try:
        await callback.bot.send_message(
            chat_id=user_id,
            text=user_text,
            parse_mode="HTML",
            reply_markup=kb_main_menu() if start_today else None,
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("adm:approve:"))
async def cb_approve(callback: CallbackQuery, session: AsyncSession) -> None:
    """adm:approve:today:<user_id>:<level> or adm:approve:tomorrow:<user_id>:<level>"""
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return

    parts = callback.data.split(":")
    # parts: ['adm', 'approve', 'today'/'tomorrow', user_id, level]
    start_today = parts[2] == "today"
    user_id, level = int(parts[3]), int(parts[4])
    await _activate_user(callback, session, user_id, level, start_today)


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
async def cb_set_level_callback(callback: CallbackQuery) -> None:
    """adm:setlvl:<user_id>:<level> — show start date choice."""
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return

    _, _, user_id_str, level_str = callback.data.split(":")
    level_name = LEVEL_NAMES[int(level_str)]
    await safe_answer(callback)
    await callback.message.answer(
        f"Уровень: <b>{level_name} ({level_str})</b>. Когда начинаем?",
        parse_mode="HTML",
        reply_markup=kb_admin_start_choice(int(user_id_str), int(level_str)),
    )
