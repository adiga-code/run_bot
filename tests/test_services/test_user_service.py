import pytest
from datetime import date, timedelta

from services.user_service import UserService
from database.models import User


@pytest.mark.asyncio
async def test_create_user(session):
    svc = UserService(session)
    user = await svc.create(telegram_id=111, full_name="Иван Иванов")
    assert user.telegram_id == 111
    assert user.full_name == "Иван Иванов"
    assert user.onboarding_complete is False
    assert user.role == "athlete"


@pytest.mark.asyncio
async def test_get_user(session):
    svc = UserService(session)
    await svc.create(telegram_id=222, full_name="Мария")
    user = await svc.get(222)
    assert user is not None
    assert user.full_name == "Мария"


@pytest.mark.asyncio
async def test_get_nonexistent_user(session):
    svc = UserService(session)
    user = await svc.get(999)
    assert user is None


@pytest.mark.asyncio
async def test_get_or_raise_raises(session):
    svc = UserService(session)
    with pytest.raises(ValueError):
        await svc.get_or_raise(999)


@pytest.mark.asyncio
async def test_get_or_create_creates_new(session):
    svc = UserService(session)
    user, created = await svc.get_or_create(333, "Пётр")
    assert created is True
    assert user.telegram_id == 333


@pytest.mark.asyncio
async def test_get_or_create_returns_existing(session):
    svc = UserService(session)
    await svc.create(telegram_id=444, full_name="Анна")
    user, created = await svc.get_or_create(444, "Анна другая")
    assert created is False
    assert user.full_name == "Анна"  # original name preserved


@pytest.mark.asyncio
async def test_update_user(session):
    svc = UserService(session)
    user = await svc.create(telegram_id=555, full_name="Тест")
    updated = await svc.update(user, level=3, onboarding_complete=True)
    assert updated.level == 3
    assert updated.onboarding_complete is True


@pytest.mark.asyncio
async def test_current_program_day_not_started(session):
    svc = UserService(session)
    user = await svc.create(telegram_id=666, full_name="Нет старта")
    day = await svc.current_program_day(user)
    assert day is None


@pytest.mark.asyncio
async def test_current_program_day_day1(session):
    svc = UserService(session)
    user = await svc.create(telegram_id=777, full_name="Старт сегодня")
    await svc.update(user, program_start_date=date.today())
    day = await svc.current_program_day(user)
    assert day == 1


@pytest.mark.asyncio
async def test_current_program_day_day5(session):
    svc = UserService(session)
    user = await svc.create(telegram_id=888, full_name="5 дней назад")
    start = date.today() - timedelta(days=4)
    await svc.update(user, program_start_date=start)
    day = await svc.current_program_day(user)
    assert day == 5


@pytest.mark.asyncio
async def test_current_program_day_capped_at_28(session):
    svc = UserService(session)
    user = await svc.create(telegram_id=999, full_name="Финиш")
    start = date.today() - timedelta(days=40)
    await svc.update(user, program_start_date=start)
    day = await svc.current_program_day(user)
    assert day == 28
