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
    kb_admin_application, kb_admin_approve, kb_admin_day_mode, kb_admin_delete_confirm,
    kb_admin_level_picker, kb_admin_manage, kb_admin_mark_day_picker, kb_admin_mark_day_status,
    kb_admin_menu, kb_admin_report_actions, kb_admin_report_users,
    kb_admin_ref_detail, kb_admin_referrals,
    kb_admin_start_choice, kb_main_menu,
)
from services.user_service import UserService
from services.whitelist_service import WhitelistService
from texts import T

logger = logging.getLogger(__name__)


class AdminActionStates(StatesGroup):
    jump_day = State()
    send_msg = State()
    ref_name = State()

router = Router()

LEVEL_NAMES = {1: "Start", 2: "Return", 3: "Base", 4: "Stability", 5: "Performance"}


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


# ── /admin menu ────────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return
    await message.answer(T.admin.panel_header, parse_mode="HTML", reply_markup=kb_admin_menu())


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
        await callback.message.answer(T.admin.no_pending, reply_markup=kb_admin_menu())
        return

    await callback.message.answer(
        T.admin.pending_count.format(count=len(users)), parse_mode="HTML"
    )
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
        T.admin.stats_text.format(count=len(users), level_lines=level_lines),
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
        await callback.message.answer(T.admin.no_users, reply_markup=kb_admin_menu())
        return

    lines = [T.admin.all_users_header.format(count=len(users))]
    for u in users:
        level_name = LEVEL_NAMES.get(u.level, "?") if u.level else "—"
        status_icon = "✅" if u.status == "active" else "⏳"
        started = u.program_start_date.strftime("%d.%m") if u.program_start_date else T.admin.not_started
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

    from services.session_log_service import SessionLogService

    user_svc = UserService(session)
    log_svc = SessionLogService(session)
    users = await user_svc.all_active()

    sent, skipped = 0, 0
    skipped_users: list[str] = []

    for user in users:
        day = await user_svc.current_program_day(user)
        if not day:
            skipped += 1
            skipped_users.append(
                f"• <b>{user.full_name}</b> (id: <code>{user.telegram_id}</code>) — {T.admin.broadcast_skipped_no_day}"
            )
            continue
        await log_svc.get_or_create_today(user.telegram_id, day)
        try:
            await callback.bot.send_message(
                chat_id=user.telegram_id,
                text=T.scheduler.morning_reminder,
                reply_markup=kb_main_menu(),
            )
            sent += 1
        except Exception:
            skipped += 1
            skipped_users.append(
                f"• <b>{user.full_name}</b> (id: <code>{user.telegram_id}</code>) — {T.admin.broadcast_skipped_blocked}"
            )

    logger.info("Admin %s broadcast checkin: sent=%s skipped=%s", callback.from_user.id, sent, skipped)

    result_text = T.admin.broadcast_result.format(sent=sent, skipped=skipped)
    if skipped_users:
        result_text += T.admin.broadcast_skipped_header + "\n".join(skipped_users)

    await callback.message.answer(
        result_text,
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
        .where(
            User.onboarding_complete == True,
            User.status.in_(["active", "completed"]),
        )
        .order_by(User.full_name)
    )
    users = list(result.scalars().all())

    if not users:
        await callback.message.answer(T.admin.no_active_users, reply_markup=kb_admin_menu())
        return

    await callback.message.answer(
        T.admin.reports_header.format(count=len(users)),
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
        await message.answer(T.admin.user_not_found)
        return

    result = await session.execute(
        select(SessionLog, Workout)
        .outerjoin(Workout, SessionLog.assigned_workout_id == Workout.id)
        .where(SessionLog.user_id == user_id)
        .order_by(SessionLog.date)
    )
    rows = result.all()

    WELLBEING = T.admin.wellbeing_labels
    SLEEP     = T.admin.sleep_labels
    PAIN      = T.admin.pain_labels
    STATUS    = T.admin.status_labels
    VERSION   = T.admin.version_labels
    DAY_TYPE  = T.admin.day_type_labels

    level_name = LEVEL_NAMES.get(user.level, "?")
    current_day = await user_svc.current_calendar_day(user) or "?"

    if as_file:
        buf = io.StringIO()
        buf.write(T.admin.csv_header)
        for log, workout in rows:
            buf.write(",".join([
                str(user_svc.log_calendar_day(user, log)),
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
            caption=T.admin.report_caption.format(name=user.full_name),
        )
        return

    if not rows:
        await message.answer(
            T.admin.report_no_data.format(name=user.full_name),
            parse_mode="HTML",
            reply_markup=kb_admin_menu(),
        )
        return

    lines = [T.admin.report_header.format(name=user.full_name, level_name=level_name, day=current_day)]
    for log, workout in rows:
        day_type = DAY_TYPE.get(workout.day_type, "—") if workout else "—"
        version  = VERSION.get(log.assigned_version, "—") if log.assigned_version else "—"
        status   = STATUS.get(log.completion_status, "—") if log.completion_status else "—"
        cal_day  = user_svc.log_calendar_day(user, log)
        lines.append(f"День {cal_day:>2} | {day_type:<14} | {version:<8} | {status}")

    text = "\n".join(lines)
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
        await callback.message.answer(T.admin.user_not_found)
        return

    current_day = await user_svc.current_calendar_day(user) or "?"
    level_name = LEVEL_NAMES.get(user.level, "?")
    max_day = 42 if getattr(user, "extended_week5", False) else 28
    week5_status = T.admin.week5_label if getattr(user, "extended_week5", False) else ""
    goal_line = T.onb.goal_labels.get(user.q_goal or "", "—")
    if user.q_goal == "distance":
        goal_line += f" | {T.onb.dist_labels.get(user.q_distance or '', '—')} | {user.q_race_date or '—'}"

    await callback.message.answer(
        T.admin.manage_header.format(
            name=user.full_name,
            level_name=level_name,
            day=current_day,
            max_day=max_day,
            week5_status=week5_status,
            city=user.city or "—",
            district=user.district or "—",
            goal_line=goal_line,
        ),
        parse_mode="HTML",
        reply_markup=kb_admin_manage(user_id, extended=getattr(user, "extended_week5", False)),
    )


@router.callback_query(F.data.startswith("adm:extend:"))
async def cb_admin_extend_week5(callback: CallbackQuery, session: AsyncSession) -> None:
    """Toggle week 5 extension for a user."""
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)

    parts = callback.data.split(":")
    if parts[2] == "off":
        user_id = int(parts[3])
        activate = False
    else:
        user_id = int(parts[2])
        activate = True

    user_svc = UserService(session)
    user = await user_svc.get(user_id)
    if not user:
        await callback.message.answer(T.admin.user_not_found)
        return

    await user_svc.update(user, extended_week5=activate)

    # If enabling extension for a completed user still within 42 days → reactivate immediately
    if activate and user.status == "completed" and user.program_start_date:
        from datetime import date as _date
        from services.session_log_service import SessionLogService as _LogSvc
        raw_day = (_date.today() - user.program_start_date).days + 1
        if raw_day <= 42:
            await user_svc.update(user, status="active")
            # Create today's log so user gets check-in right away
            log_svc = _LogSvc(session)
            day = await user_svc.current_program_day(user)
            if day is not None:
                await log_svc.get_or_create_today(user_id, day)
            logger.info("Immediately reactivated completed user %s for week 6 (day %d)", user_id, raw_day)
            try:
                await callback.bot.send_message(
                    chat_id=user_id,
                    text=(
                        "🏃 Твоя программа продолжается!\n\n"
                        "6-я неделя начинается — ты справился, и мы идём дальше. "
                        "Продолжай в том же темпе 💪"
                    ),
                    reply_markup=kb_main_menu(),
                )
            except Exception:
                pass

    status_text = T.admin.week5_activated if activate else T.admin.week5_disabled
    await callback.message.answer(
        T.admin.week5_for_user.format(status=status_text, name=user.full_name),
        parse_mode="HTML",
        reply_markup=kb_admin_manage(user_id, extended=activate),
    )
    logger.info("Admin %s %s week5 for user %s", callback.from_user.id, "activated" if activate else "deactivated", user_id)


@router.callback_query(F.data.startswith("adm:mode:") & ~F.data.startswith("adm:mode:set:"))
async def cb_admin_mode_picker(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)

    user_id = int(callback.data.split(":")[2])
    await callback.message.answer(T.admin.choose_mode, reply_markup=kb_admin_day_mode(user_id))


@router.callback_query(F.data.startswith("adm:ca:"))
async def cb_checkin_approve(callback: CallbackQuery, session: AsyncSession) -> None:
    """Admin approves (or overrides) a pending check-in and sends workout to user."""
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return

    parts = callback.data.split(":")
    user_id, version = int(parts[2]), parts[3]
    await safe_answer(callback)

    from datetime import date as date_cls
    from sqlalchemy import select
    from database.models import SessionLog
    from services.session_log_service import SessionLogService
    from services.workout_service import WorkoutService
    from handlers.utils import send_workout_to_user

    result = await session.execute(
        select(SessionLog).where(
            SessionLog.user_id == user_id,
            SessionLog.date == date_cls.today(),
        )
    )
    log = result.scalar_one_or_none()
    if not log:
        await callback.message.answer(T.admin.log_not_found)
        return

    if not log.approval_pending:
        await callback.message.answer(T.admin.already_sent)
        return

    log_svc = SessionLogService(session)
    wk_svc = WorkoutService(session)
    user_svc = UserService(session)
    user = await user_svc.get_or_raise(user_id)

    day_type = await wk_svc.get_day_type(user.level, log.day_index) or "run"

    if version == "rest":
        await log_svc.update(log, assigned_version="rest", approval_pending=False)
        await callback.bot.send_message(
            chat_id=user_id,
            text=T.checkin.rest_day,
            reply_markup=kb_main_menu(),
        )
        version_label = T.admin.version_labels.get("rest", "rest")
    else:
        workout = await wk_svc.get(
            user.level, log.day_index, version,
            strength_format=user.strength_format if day_type == "strength" else None,
        )
        await log_svc.update(log, assigned_version=version, approval_pending=False)
        if workout:
            await send_workout_to_user(
                callback.bot, user_id, log.day_index,
                workout, day_type, version, user.strength_format, user.level,
                calendar_day=user_svc.log_calendar_day(user, log),
                max_day=user_svc._max_day(user),
            )
        version_label = T.admin.version_labels.get(version, version)

    logger.info("Admin %s approved checkin for user %s → %s", callback.from_user.id, user_id, version)
    await callback.message.edit_reply_markup()
    await callback.message.answer(T.admin.sent_ok.format(version_label=version_label, name=user.full_name))


@router.callback_query(F.data.startswith("adm:preview:"))
async def cb_workout_preview(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show the admin a preview of the recommended workout without sending it to the user."""
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return

    user_id = int(callback.data.split(":")[2])
    await safe_answer(callback)

    from datetime import date as date_cls
    from sqlalchemy import select
    from database.models import SessionLog
    from services.session_log_service import SessionLogService
    from services.workout_service import WorkoutService
    from handlers.utils import filter_strength_text

    result = await session.execute(
        select(SessionLog).where(
            SessionLog.user_id == user_id,
            SessionLog.date == date_cls.today(),
        )
    )
    log = result.scalar_one_or_none()
    if not log:
        await callback.message.answer(T.admin.log_not_found)
        return

    wk_svc = WorkoutService(session)
    user_svc = UserService(session)
    user = await user_svc.get_or_raise(user_id)

    version = log.assigned_version or "base"
    day_type = await wk_svc.get_day_type(user.level, log.day_index) or "run"
    workout = await wk_svc.get(
        user.level, log.day_index, version,
        strength_format=user.strength_format if day_type == "strength" else None,
    )

    version_label = T.admin.version_labels.get(version, version)
    if not workout:
        await callback.message.answer(f"Тренировка не найдена (уровень {user.level}, день {log.day_index}, версия {version}).")
        return

    workout_text = filter_strength_text(
        workout.text,
        user.strength_format if day_type == "strength" else None,
    )
    calendar_day = user_svc.log_calendar_day(user, log)
    preview_header = (
        f"👁 <b>Предпросмотр — {user.full_name}</b>\n"
        f"День {calendar_day} | {version_label}\n"
        f"<b>{workout.title}</b>\n\n"
    )
    await callback.message.answer(
        preview_header + workout_text,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("adm:mode:set:"))
async def cb_admin_mode_set(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return

    parts = callback.data.split(":")
    user_id, version = int(parts[3]), parts[4]
    await safe_answer(callback)

    from datetime import date as date_cls
    from sqlalchemy import select
    from database.models import SessionLog
    from services.session_log_service import SessionLogService
    from services.workout_service import WorkoutService
    from handlers.utils import filter_strength_text, get_tip_lines
    from keyboards.builders import kb_completion, kb_completion_strength
    from texts import T as _T  # re-import to avoid UnboundLocalError

    result = await session.execute(
        select(SessionLog).where(
            SessionLog.user_id == user_id,
            SessionLog.date == date_cls.today(),
        )
    )
    log = result.scalar_one_or_none()
    if not log:
        await callback.message.answer(T.admin.log_not_found_no_day)
        return

    log.assigned_version = version
    await session.commit()

    version_names = {
        "base":     _T.btn.adm_mode_base,
        "light":    _T.btn.adm_mode_light,
        "recovery": _T.btn.adm_mode_recovery,
    }
    await callback.message.answer(
        T.admin.mode_changed.format(mode=version_names.get(version, version)),
        parse_mode="HTML",
    )

    try:
        user_svc = UserService(session)
        wk_svc = WorkoutService(session)

        user = await user_svc.get_or_raise(user_id)
        day_index = log.day_index
        day_type = await wk_svc.get_day_type(user.level, day_index) or "run"
        workout = await wk_svc.get(
            user.level, day_index, version,
            strength_format=user.strength_format if day_type == "strength" else None,
        )

        await callback.bot.send_message(
            chat_id=user_id,
            text=T.admin.mode_correction.format(mode=version_names.get(version, version)),
            parse_mode="HTML",
        )

        if workout:
            workout_text = filter_strength_text(
                workout.text,
                user.strength_format if day_type == "strength" else None,
            )
            is_strength = day_type == "strength" and version != "recovery"
            tips = get_tip_lines(user.level, day_index)
            tips_block = f"\n\n{tips}" if tips else ""
            calendar_day = user_svc.log_calendar_day(user, log)
            from texts import T as _T2
            await callback.bot.send_message(
                chat_id=user_id,
                text=_T2.checkin.workout_header.format(calendar_day=calendar_day, max_day=user_svc._max_day(user), title=workout.title) + tips_block + f"\n\n{workout_text}",
                parse_mode="HTML",
                reply_markup=kb_completion_strength() if is_strength else kb_completion(),
            )
    except Exception:
        logger.exception("Failed to send updated workout to user %s after mode override", user_id)


@router.callback_query(F.data.startswith("adm:jump:"))
async def cb_admin_jump(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)

    user_id = int(callback.data.split(":")[2])
    await state.set_state(AdminActionStates.jump_day)
    await state.update_data(target_user_id=user_id)
    await callback.message.answer(T.admin.jump_ask_day)


@router.message(AdminActionStates.jump_day)
async def admin_jump_day_input(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    target_user_id = data["target_user_id"]

    try:
        target_day = int(message.text.strip())
        assert 1 <= target_day <= 42
    except Exception:
        await message.answer(T.admin.jump_invalid)
        return

    await state.clear()

    from datetime import timedelta
    user_svc = UserService(session)
    user = await user_svc.get(target_user_id)
    if not user:
        await message.answer(T.admin.user_not_found)
        return

    new_start = date.today() - timedelta(days=target_day - 1)
    await user_svc.update(
        user,
        program_start_date=new_start,
        week_repeat_count=0,
        status="active",  # reactivate if user was completed
    )

    from database.models import SessionLog
    await session.execute(
        delete(SessionLog).where(
            SessionLog.user_id == target_user_id,
            SessionLog.date == date.today(),
        )
    )
    await session.commit()
    logger.info("Admin %s jumped user %s to day %s; deleted today's SessionLog", message.from_user.id, target_user_id, target_day)

    await message.answer(T.admin.jump_done_admin.format(day=target_day), parse_mode="HTML")

    try:
        await message.bot.send_message(
            chat_id=target_user_id,
            text=T.admin.jump_done_user.format(day=target_day),
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
    await callback.message.answer(T.admin.ask_message)


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
            text=T.admin.message_to_user.format(text=message.text),
            parse_mode="HTML",
        )
        await message.answer(T.admin.message_sent)
    except Exception as e:
        await message.answer(T.admin.message_failed.format(error=e))


@router.callback_query(F.data == "adm:menu:whitelist")
async def cb_admin_whitelist(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)

    wl_svc = WhitelistService(session)
    entries = await wl_svc.list_all()

    if not entries:
        await callback.message.answer(T.admin.whitelist_empty, reply_markup=kb_admin_menu())
        return

    lines = [T.admin.whitelist_header.format(count=len(entries))]
    for e in entries:
        note = f" — {e.note}" if e.note else ""
        lines.append(f"• <code>{e.telegram_id}</code>{note}")

    await callback.message.answer("\n".join(lines), parse_mode="HTML", reply_markup=kb_admin_menu())


# ── Application approve / reject ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm:app:approve:"))
async def cb_app_approve(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return

    user_id = int(callback.data.split(":")[3])
    wl_svc = WhitelistService(session)

    if await wl_svc.is_allowed(user_id):
        await safe_answer(callback, text=T.admin.already_whitelist, show_alert=True)
        return

    await wl_svc.add(telegram_id=user_id, added_by=callback.from_user.id, note="заявка")
    await callback.message.edit_reply_markup()
    await callback.message.edit_text(
        callback.message.text + "\n\n" + T.admin.approved_label,
        parse_mode="HTML",
    )
    await safe_answer(callback)

    try:
        await callback.bot.send_message(
            chat_id=user_id,
            text=T.admin.application_approved,
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
        callback.message.text + "\n\n" + T.admin.rejected_label,
        parse_mode="HTML",
    )
    await safe_answer(callback)

    try:
        await callback.bot.send_message(chat_id=user_id, text=T.admin.application_rejected)
    except Exception:
        pass


# ── Mark day completion (admin) ────────────────────────────────────────────────

@router.callback_query(
    F.data.startswith("adm:markday:")
    & ~F.data.startswith("adm:markday:day:")
    & ~F.data.startswith("adm:markday:set:")
)
async def cb_admin_mark_day(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show list of all past unmarked days for the user."""
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)

    from services.session_log_service import SessionLogService

    user_id = int(callback.data.split(":")[2])
    user_svc = UserService(session)
    log_svc = SessionLogService(session)

    user = await user_svc.get(user_id)
    if not user:
        await callback.message.answer(T.admin.user_not_found)
        return

    logs = await log_svc.get_unmarked_past(user_id)
    if not logs:
        await callback.message.answer(
            T.admin.no_unmarked.format(name=user.full_name),
            parse_mode="HTML",
            reply_markup=kb_admin_manage(user_id),
        )
        return

    await callback.message.answer(
        T.admin.pick_day.format(name=user.full_name),
        parse_mode="HTML",
        reply_markup=kb_admin_mark_day_picker(user_id, logs),
    )


@router.callback_query(F.data.startswith("adm:markday:day:"))
async def cb_admin_mark_day_pick(callback: CallbackQuery) -> None:
    """Show done/partial/skipped buttons for the chosen day."""
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)

    parts = callback.data.split(":")  # adm:markday:day:<user_id>:<day_index>
    user_id, day_index = int(parts[3]), int(parts[4])
    await callback.message.answer(
        T.admin.pick_status.format(day=day_index),
        parse_mode="HTML",
        reply_markup=kb_admin_mark_day_status(user_id, day_index),
    )


@router.callback_query(F.data.startswith("adm:markday:set:"))
async def cb_admin_mark_day_set(callback: CallbackQuery, session: AsyncSession) -> None:
    """Save completion status for the selected day."""
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)

    from sqlalchemy import select as sa_select
    from database.models import SessionLog

    parts = callback.data.split(":")  # adm:markday:set:<user_id>:<day_index>:<status>
    user_id, day_index, status = int(parts[3]), int(parts[4]), parts[5]

    result = await session.execute(
        sa_select(SessionLog).where(
            SessionLog.user_id == user_id,
            SessionLog.day_index == day_index,
        )
    )
    log = result.scalar_one_or_none()
    if not log:
        await callback.message.answer(T.admin.log_not_found_generic, reply_markup=kb_admin_manage(user_id))
        return

    log.completion_status = status
    await session.commit()

    logger.info("Admin %s marked user %s day %s as %s", callback.from_user.id, user_id, day_index, status)
    await callback.message.answer(
        T.admin.day_marked.format(day=day_index, status=T.admin.status_labels.get(status, status)),
        parse_mode="HTML",
        reply_markup=kb_admin_manage(user_id),
    )


# ── User deletion ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm:delete:") & ~F.data.startswith("adm:delete:confirm:"))
async def cb_admin_delete_ask(callback: CallbackQuery, session: AsyncSession) -> None:
    """Show deletion confirmation prompt."""
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)

    user_id = int(callback.data.split(":")[2])
    user_svc = UserService(session)
    user = await user_svc.get(user_id)
    if not user:
        await callback.message.answer(T.admin.user_not_found)
        return

    await callback.message.answer(
        f"⚠️ <b>Удалить пользователя безвозвратно?</b>\n\n"
        f"<b>{user.full_name}</b> (ID: <code>{user_id}</code>)\n\n"
        f"Будут удалены: профиль и все логи тренировок.",
        parse_mode="HTML",
        reply_markup=kb_admin_delete_confirm(user_id),
    )


@router.callback_query(F.data.startswith("adm:delete:confirm:"))
async def cb_admin_delete_confirm(callback: CallbackQuery, session: AsyncSession) -> None:
    """Permanently delete user and all their session logs."""
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)

    user_id = int(callback.data.split(":")[3])
    user_svc = UserService(session)
    user = await user_svc.get(user_id)
    if not user:
        await callback.message.answer(T.admin.user_not_found)
        return

    full_name = user.full_name

    from database.models import SessionLog, WhitelistEntry
    await session.execute(delete(SessionLog).where(SessionLog.user_id == user_id))
    await session.execute(delete(WhitelistEntry).where(WhitelistEntry.telegram_id == user_id))
    await session.delete(user)
    await session.commit()

    logger.info("Admin %s permanently deleted user %s (%s)", callback.from_user.id, user_id, full_name)
    await callback.message.answer(
        f"🗑 Пользователь <b>{full_name}</b> (ID: <code>{user_id}</code>) удалён.",
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
        await message.answer(T.admin.cmd_add_user_usage)
        return

    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer(T.admin.cmd_id_not_number)
        return

    note = parts[2] if len(parts) == 3 else None
    svc = WhitelistService(session)

    if await svc.is_allowed(target_id):
        await message.answer(T.admin.user_in_whitelist.format(user_id=target_id))
        return

    await svc.add(telegram_id=target_id, added_by=message.from_user.id, note=note)
    await message.answer(T.admin.user_added_whitelist.format(user_id=target_id))


@router.message(Command("remove_user"))
async def cmd_remove_user(message: Message, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(T.admin.cmd_remove_user_usage)
        return

    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer(T.admin.cmd_id_not_number)
        return

    svc = WhitelistService(session)
    removed = await svc.remove(target_id)
    if removed:
        await message.answer(T.admin.user_removed_whitelist.format(user_id=target_id))
    else:
        await message.answer(T.admin.user_not_in_whitelist.format(user_id=target_id))


@router.message(Command("list_users"))
async def cmd_list_users(message: Message, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return

    wl_svc = WhitelistService(session)
    entries = await wl_svc.list_all()

    if not entries:
        await message.answer(T.admin.whitelist_empty)
        return

    lines = [T.admin.whitelist_header.format(count=len(entries))]
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
    await message.answer(
        T.admin.stats_text.format(count=len(users), level_lines=level_lines),
        parse_mode="HTML",
    )


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
        await message.answer(T.admin.no_pending_users)
        return

    for u in users:
        level_name = LEVEL_NAMES.get(u.level, "?")
        text = (
            f"👤 <b>{u.full_name}</b>\n"
            f"ID: <code>{u.telegram_id}</code>\n"
            f"Уровень: <b>{level_name} ({u.level})</b>"
        )
        await message.answer(text, parse_mode="HTML", reply_markup=kb_admin_approve(u.telegram_id, u.level))


# ── Reset user progress ────────────────────────────────────────────────────────

@router.message(Command("reset_user"))
async def cmd_reset_user(message: Message, session: AsyncSession) -> None:
    """/reset_user <user_id> — reset progress, send back to onboarding."""
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(T.admin.cmd_reset_user_usage)
        return

    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer(T.admin.cmd_id_not_number)
        return

    user_svc = UserService(session)
    user = await user_svc.get(target_id)
    if not user:
        await message.answer(T.admin.user_not_found_id.format(user_id=target_id))
        return

    await user_svc.reset_progress(user)
    await message.answer(T.admin.progress_reset_admin.format(user_id=target_id), parse_mode="HTML")

    try:
        await message.bot.send_message(chat_id=target_id, text=T.admin.progress_reset_user)
    except Exception:
        pass


# ── Level change command ────────────────────────────────────────────────────────

@router.message(Command("set_level"))
async def cmd_set_level(message: Message, session: AsyncSession) -> None:
    """/set_level <user_id> <level 1-5>"""
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()
    if len(parts) < 3:
        await message.answer(T.admin.cmd_set_level_usage)
        return

    try:
        target_id = int(parts[1])
        new_level = int(parts[2])
        assert 1 <= new_level <= 5
    except Exception:
        await message.answer(T.admin.cmd_set_level_invalid)
        return

    user_svc = UserService(session)
    user = await user_svc.get(target_id)
    if not user:
        await message.answer(T.admin.user_not_found_id.format(user_id=target_id))
        return

    await user_svc.update(user, level=new_level)
    level_name = LEVEL_NAMES[new_level]
    logger.info("Admin %s set user %s to level=%s (%s)", message.from_user.id, target_id, new_level, level_name)
    await message.answer(
        T.admin.level_set.format(user_id=target_id, level_name=level_name, level=new_level),
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
        await safe_answer(callback, text=T.admin.user_not_found, show_alert=True)
        return

    if user.status == "active":
        await safe_answer(callback, text=T.admin.already_active, show_alert=True)
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
    start_label = T.admin.start_today_word if start_today else T.admin.start_tomorrow_word

    await callback.message.edit_text(
        callback.message.text + f"\n\n" + T.admin.activated_label.format(
            level_name=level_name, level=level, start_label=start_label
        ),
        parse_mode="HTML",
        reply_markup=None,
    )
    await safe_answer(callback)

    user_text = T.admin.user_activated_msg.format(level_name=level_name, start_label=start_label)
    if start_today:
        user_text += T.admin.user_activated_today_suffix
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
    await callback.message.answer(T.admin.choose_level, reply_markup=kb_admin_level_picker(user_id))


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
        T.admin.level_chosen.format(level_name=level_name, level=level_str),
        parse_mode="HTML",
        reply_markup=kb_admin_start_choice(int(user_id_str), int(level_str)),
    )


# ── Referral links ─────────────────────────────────────────────────────────────

async def _show_referrals(target, session: AsyncSession) -> None:
    from services.referral_service import ReferralService
    ref_svc = ReferralService(session)
    links = await ref_svc.get_all()
    if not links:
        text = T.admin.ref_menu_empty
    else:
        lines = []
        for link in links:
            stats = await ref_svc.get_stats(link.code)
            status = "✅" if link.is_active else "❌"
            lines.append(T.admin.ref_list_line.format(
                status=status, name=link.name,
                total=stats["total"], onboarded=stats["onboarded"], activated=stats["activated"],
            ))
        text = T.admin.ref_menu_header.format(count=len(links), lines="\n".join(lines))
    msg = target.message if isinstance(target, CallbackQuery) else target
    await msg.answer(text, parse_mode="HTML", reply_markup=kb_admin_referrals(links))
    if isinstance(target, CallbackQuery):
        await safe_answer(target)


@router.callback_query(F.data == "adm:menu:referrals")
async def cb_admin_referrals(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await _show_referrals(callback, session)


@router.callback_query(F.data == "adm:ref:new")
async def cb_ref_new(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)
    await state.set_state(AdminActionStates.ref_name)
    await callback.message.answer(T.admin.ref_ask_name)


@router.message(AdminActionStates.ref_name)
async def admin_ref_name_input(message: Message, state: FSMContext, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        return
    name = message.text.strip()
    if not name:
        await message.answer(T.admin.ref_ask_name)
        return
    await state.clear()

    from services.referral_service import ReferralService
    ref_svc = ReferralService(session)
    link = await ref_svc.create(name=name, admin_id=message.from_user.id)

    me = await message.bot.get_me()
    bot_link = f"https://t.me/{me.username}?start={link.code}"
    await message.answer(
        T.admin.ref_created.format(name=link.name, link=bot_link),
        parse_mode="HTML",
        reply_markup=kb_admin_referrals(await ref_svc.get_all()),
    )


@router.callback_query(F.data.startswith("adm:ref:view:"))
async def cb_ref_view(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)

    code = callback.data.split(":", 3)[3]
    from services.referral_service import ReferralService
    ref_svc = ReferralService(session)
    link = await ref_svc.get_by_code(code)
    if not link:
        await callback.message.answer(T.admin.ref_not_found)
        return

    stats = await ref_svc.get_stats(code)
    me = await callback.bot.get_me()
    bot_link = f"https://t.me/{me.username}?start={code}"
    status_label = "активна ✅" if link.is_active else "неактивна ❌"
    await callback.message.answer(
        T.admin.ref_detail_header.format(
            name=link.name, status=status_label,
            total=stats["total"], onboarded=stats["onboarded"], activated=stats["activated"],
        ) + f"\n\n🔗 <code>{bot_link}</code>",
        parse_mode="HTML",
        reply_markup=kb_admin_ref_detail(code, link.is_active),
    )


@router.callback_query(F.data.startswith("adm:ref:toggle:"))
async def cb_ref_toggle(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)

    code = callback.data.split(":", 3)[3]
    from services.referral_service import ReferralService
    ref_svc = ReferralService(session)
    link = await ref_svc.get_by_code(code)
    if not link:
        await callback.message.answer(T.admin.ref_not_found)
        return

    await ref_svc.toggle_active(link)
    text = T.admin.ref_toggled_on.format(name=link.name) if link.is_active else T.admin.ref_toggled_off.format(name=link.name)
    await callback.message.answer(text, parse_mode="HTML")
    await _show_referrals(callback.message, session)


@router.callback_query(F.data.startswith("adm:ref:users:"))
async def cb_ref_users(callback: CallbackQuery, session: AsyncSession) -> None:
    if not is_admin(callback.from_user.id):
        await safe_answer(callback)
        return
    await safe_answer(callback)

    code = callback.data.split(":", 3)[3]
    from services.referral_service import ReferralService
    from services.user_service import UserService as _UserSvc
    ref_svc = ReferralService(session)
    user_svc = _UserSvc(session)
    link = await ref_svc.get_by_code(code)
    if not link:
        await callback.message.answer(T.admin.ref_not_found)
        return

    users = await ref_svc.get_users(code)
    if not users:
        await callback.message.answer(
            T.admin.ref_users_empty,
            reply_markup=kb_admin_ref_detail(code, link.is_active),
        )
        return

    STATUS_MAP = {"active": "активен", "pending": "ожидает", "completed": "завершил"}
    lines = []
    for u in users:
        cal_day = await user_svc.current_calendar_day(u) or "—"
        status = STATUS_MAP.get(u.status, u.status)
        lines.append(T.admin.ref_user_line.format(name=u.full_name, status=status, day=cal_day))

    text = T.admin.ref_users_header.format(name=link.name, lines="\n".join(lines))
    await callback.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=kb_admin_ref_detail(code, link.is_active),
    )
