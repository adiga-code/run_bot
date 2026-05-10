"""
tests/test_services/test_recheckin.py

Re-checkin behavior:
- get_or_create_today возвращает created=False при повторном вызове
- recheckin_count инкрементируется
- данные перезаписываются
- блокировка после completion_status
"""
import pytest
from datetime import datetime, timezone

from services.user_service import UserService
from services.session_log_service import SessionLogService


async def _make_user(session, tg_id: int = 1001):
    return await UserService(session).create(telegram_id=tg_id, full_name="Test User")


# ── Базовое поведение get_or_create_today ─────────────────────────────────────

@pytest.mark.asyncio
async def test_first_checkin_created_true(session):
    """Первый вызов get_or_create_today → created=True."""
    await _make_user(session)
    svc = SessionLogService(session)
    _, created = await svc.get_or_create_today(1001, day_index=3)
    assert created is True


@pytest.mark.asyncio
async def test_recheckin_detected_as_not_created(session):
    """Второй вызов get_or_create_today → created=False (re-checkin)."""
    await _make_user(session)
    svc = SessionLogService(session)
    log1, _ = await svc.get_or_create_today(1001, day_index=3)
    log2, created = await svc.get_or_create_today(1001, day_index=3)
    assert created is False
    assert log1.id == log2.id


@pytest.mark.asyncio
async def test_recheckin_count_tracks_reruns(session):
    """recheckin_count = 0 на первом чекине, 1 после первого ре-чекина."""
    await _make_user(session)
    svc = SessionLogService(session)
    log, _ = await svc.get_or_create_today(1001, day_index=3)

    # Первый чекин — не ре-чекин
    log = await svc.update(log, wellbeing=3, checkin_done=True, recheckin_count=0)
    assert log.recheckin_count == 0

    # Повторный — ре-чекин, счётчик растёт
    _, created = await svc.get_or_create_today(1001, day_index=3)
    assert not created
    new_count = (log.recheckin_count or 0) + 1
    log = await svc.update(log, recheckin_count=new_count)
    assert log.recheckin_count == 1


@pytest.mark.asyncio
async def test_recheckin_count_increments_twice(session):
    """Два ре-чекина → recheckin_count == 2."""
    await _make_user(session)
    svc = SessionLogService(session)
    log, _ = await svc.get_or_create_today(1001, day_index=3)
    log = await svc.update(log, checkin_done=True, recheckin_count=0)

    for expected in (1, 2):
        log = await svc.update(log, recheckin_count=(log.recheckin_count or 0) + 1)
        assert log.recheckin_count == expected


# ── Перезапись данных ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recheckin_overwrites_wellbeing(session):
    """Ре-чекин перезаписывает wellbeing/pain/sleep."""
    await _make_user(session)
    svc = SessionLogService(session)
    log, _ = await svc.get_or_create_today(1001, day_index=3)
    log = await svc.update(log, wellbeing=1, pain_level=2, sleep_quality=1, checkin_done=True)

    # Ре-чекин с лучшими показателями
    log = await svc.update(log, wellbeing=3, pain_level=1, sleep_quality=3)
    assert log.wellbeing == 3
    assert log.pain_level == 1
    assert log.sleep_quality == 3


@pytest.mark.asyncio
async def test_recheckin_changes_assigned_version(session):
    """Ре-чекин может изменить assigned_version (например, боль прошла)."""
    await _make_user(session)
    svc = SessionLogService(session)
    log, _ = await svc.get_or_create_today(1001, day_index=3)
    log = await svc.update(log, assigned_version="light", checkin_done=True)
    assert log.assigned_version == "light"

    # После ре-чекина тренер одобряет base
    log = await svc.update(log, assigned_version="base")
    assert log.assigned_version == "base"


@pytest.mark.asyncio
async def test_recheckin_preserves_week_plan_link(session):
    """Ре-чекин не разрывает связь с WeekPlan/DayPlan."""
    await _make_user(session)
    svc = SessionLogService(session)
    log, _ = await svc.get_or_create_today(1001, day_index=3)
    log = await svc.update(log, week_plan_id=42, day_plan_id=7, checkin_done=True)

    _, created = await svc.get_or_create_today(1001, day_index=3)
    assert not created
    assert log.week_plan_id == 42


@pytest.mark.asyncio
async def test_recheckin_updates_last_checkin_at(session):
    """last_checkin_at обновляется при каждом ре-чекине."""
    await _make_user(session)
    svc = SessionLogService(session)
    log, _ = await svc.get_or_create_today(1001, day_index=3)

    # SQLite хранит datetime без tzinfo — сравниваем naive-значения
    t1 = datetime(2026, 5, 7, 9, 0)
    log = await svc.update(log, checkin_done=True, last_checkin_at=t1)
    assert log.last_checkin_at.replace(tzinfo=None) == t1

    t2 = datetime(2026, 5, 7, 9, 30)
    log = await svc.update(log, last_checkin_at=t2)
    assert log.last_checkin_at.replace(tzinfo=None) == t2
    assert log.last_checkin_at.replace(tzinfo=None) != t1


# ── Логика блокировки (handler-level условие, без aiogram) ───────────────────

def _is_recheckin_blocked(log) -> bool:
    """
    Точное условие из handlers/checkin.py cb_menu_checkin:
      checkin_done=True AND completion_status is not None → заблокировано.
    """
    return bool(log.checkin_done and log.completion_status is not None)


def test_blocked_after_completion_done():
    class L:
        checkin_done = True
        completion_status = "done"
    assert _is_recheckin_blocked(L()) is True


def test_blocked_after_completion_skipped():
    class L:
        checkin_done = True
        completion_status = "skipped"
    assert _is_recheckin_blocked(L()) is True


def test_allowed_checkin_done_but_no_completion():
    """Чекин есть, тренировка ещё не отмечена → ре-чекин разрешён."""
    class L:
        checkin_done = True
        completion_status = None
    assert _is_recheckin_blocked(L()) is False


def test_allowed_no_checkin_yet():
    """Никакого чекина ещё не было → точно разрешён."""
    class L:
        checkin_done = False
        completion_status = None
    assert _is_recheckin_blocked(L()) is False


def test_blocked_only_when_both_set():
    """Только оба условия вместе блокируют."""
    class L:
        checkin_done = False
        completion_status = "done"
    # checkin_done=False → не заблокировано (нестандартное состояние)
    assert _is_recheckin_blocked(L()) is False
