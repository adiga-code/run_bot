import pytest
from services.whitelist_service import WhitelistService


@pytest.mark.asyncio
async def test_add_to_whitelist(session):
    svc = WhitelistService(session)
    entry = await svc.add(telegram_id=2001, added_by=1, note="тест")
    assert entry.telegram_id == 2001
    assert entry.note == "тест"


@pytest.mark.asyncio
async def test_is_allowed_true(session):
    svc = WhitelistService(session)
    await svc.add(telegram_id=2002, added_by=1)
    assert await svc.is_allowed(2002) is True


@pytest.mark.asyncio
async def test_is_allowed_false(session):
    svc = WhitelistService(session)
    assert await svc.is_allowed(9999) is False


@pytest.mark.asyncio
async def test_remove_from_whitelist(session):
    svc = WhitelistService(session)
    await svc.add(telegram_id=2003, added_by=1)
    removed = await svc.remove(2003)
    assert removed is True
    assert await svc.is_allowed(2003) is False


@pytest.mark.asyncio
async def test_remove_nonexistent(session):
    svc = WhitelistService(session)
    removed = await svc.remove(9999)
    assert removed is False


@pytest.mark.asyncio
async def test_list_all(session):
    svc = WhitelistService(session)
    await svc.add(telegram_id=3001, added_by=1)
    await svc.add(telegram_id=3002, added_by=1)
    entries = await svc.list_all()
    ids = [e.telegram_id for e in entries]
    assert 3001 in ids
    assert 3002 in ids
