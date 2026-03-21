import pytest
from datetime import date

from services.user_service import UserService
from services.session_log_service import SessionLogService


async def _make_user(session, tg_id: int = 1001):
    svc = UserService(session)
    return await svc.create(telegram_id=tg_id, full_name="Test User")


@pytest.mark.asyncio
async def test_get_or_create_today_creates(session):
    await _make_user(session)
    svc = SessionLogService(session)
    log, created = await svc.get_or_create_today(user_id=1001, day_index=1)
    assert created is True
    assert log.day_index == 1
    assert log.date == date.today()


@pytest.mark.asyncio
async def test_get_or_create_today_returns_existing(session):
    await _make_user(session)
    svc = SessionLogService(session)
    log1, _ = await svc.get_or_create_today(user_id=1001, day_index=1)
    log2, created = await svc.get_or_create_today(user_id=1001, day_index=1)
    assert created is False
    assert log1.id == log2.id


@pytest.mark.asyncio
async def test_update_log(session):
    await _make_user(session)
    svc = SessionLogService(session)
    log, _ = await svc.get_or_create_today(user_id=1001, day_index=1)
    log = await svc.update(log, wellbeing=3, sleep_quality=2, pain_level=1, checkin_done=True)
    assert log.wellbeing == 3
    assert log.checkin_done is True


@pytest.mark.asyncio
async def test_completed_count(session):
    await _make_user(session)
    svc = SessionLogService(session)
    log, _ = await svc.get_or_create_today(user_id=1001, day_index=1)
    await svc.update(log, completion_status="done")
    count = await svc.completed_count(user_id=1001)
    assert count == 1


@pytest.mark.asyncio
async def test_completed_count_excludes_skipped(session):
    await _make_user(session)
    svc = SessionLogService(session)
    log, _ = await svc.get_or_create_today(user_id=1001, day_index=1)
    await svc.update(log, completion_status="skipped")
    count = await svc.completed_count(user_id=1001)
    assert count == 0


@pytest.mark.asyncio
async def test_streak_no_skips(session):
    await _make_user(session)
    svc = SessionLogService(session)
    log, _ = await svc.get_or_create_today(user_id=1001, day_index=1)
    await svc.update(log, completion_status="done", checkin_done=True)
    streak = await svc.streak(user_id=1001)
    assert streak == 1


@pytest.mark.asyncio
async def test_streak_breaks_on_skip(session):
    await _make_user(session)
    svc = SessionLogService(session)
    log, _ = await svc.get_or_create_today(user_id=1001, day_index=1)
    await svc.update(log, completion_status="skipped", checkin_done=True)
    streak = await svc.streak(user_id=1001)
    assert streak == 0


@pytest.mark.asyncio
async def test_get_recent_empty(session):
    await _make_user(session)
    svc = SessionLogService(session)
    recent = await svc.get_recent(user_id=1001)
    assert recent == []


@pytest.mark.asyncio
async def test_get_recent_returns_data(session):
    await _make_user(session)
    svc = SessionLogService(session)
    log, _ = await svc.get_or_create_today(user_id=1001, day_index=3)
    await svc.update(log, sleep_quality=1, effort_level=5, checkin_done=True, completion_status="done")
    recent = await svc.get_recent(user_id=1001)
    assert len(recent) == 1
    assert recent[0].effort_level == 5
    assert recent[0].sleep_quality == 1
