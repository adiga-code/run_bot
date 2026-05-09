"""
tests/test_engine/test_available_days_change.py

Смена доступных дней (available_weekdays) в середине цикла.
- parse_available_weekdays: парсинг строки → список
- build_week_plan уважает переданный список дней
- Смена дней применяется со следующей недели (не текущей)
- Non-available дни всегда получают day_type='rest'
"""
import pytest
from types import SimpleNamespace

from engine.week_planner import build_week_plan, parse_available_weekdays


# ─────────────────────────────────────────────────────────────────────────────
# parse_available_weekdays
# ─────────────────────────────────────────────────────────────────────────────

def test_parse_single_day():
    assert parse_available_weekdays("3") == [3]


def test_parse_three_days_mon_wed_fri():
    assert parse_available_weekdays("1,3,5") == [1, 3, 5]


def test_parse_five_days():
    assert parse_available_weekdays("1,2,4,5,6") == [1, 2, 4, 5, 6]


def test_parse_all_seven_days():
    assert parse_available_weekdays("1,2,3,4,5,6,7") == [1, 2, 3, 4, 5, 6, 7]


def test_parse_weekend_only():
    assert parse_available_weekdays("6,7") == [6, 7]


def test_parse_empty_returns_default():
    assert parse_available_weekdays("") == [1, 3, 5]


def test_parse_none_returns_default():
    assert parse_available_weekdays(None) == [1, 3, 5]


def test_parse_sorts_ascending():
    """Независимо от порядка ввода — результат отсортирован."""
    assert parse_available_weekdays("7,1,3") == [1, 3, 7]
    assert parse_available_weekdays("5,2,4") == [2, 4, 5]


def test_parse_spaces_ignored():
    """Пробелы вокруг чисел игнорируются."""
    assert parse_available_weekdays("1, 3, 5") == [1, 3, 5]


def test_parse_tuesday_thursday_saturday():
    assert parse_available_weekdays("2,4,6") == [2, 4, 6]


def test_parse_four_days():
    assert parse_available_weekdays("1,3,5,7") == [1, 3, 5, 7]


# ─────────────────────────────────────────────────────────────────────────────
# Вспомогательные функции
# ─────────────────────────────────────────────────────────────────────────────

def _make_user(level: int = 2, available_weekdays: str = "1,3,5", **overrides):
    defaults = dict(
        level=level,
        current_period="base",
        injury_return_active=False,
        l1_long_independent=False,
        l1_easy_reached_40min=False,
        growth_streak=0,
        program_week_number=1,
        available_weekdays=available_weekdays,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _active_days(blueprint) -> set[int]:
    return {d.day_of_week for d in blueprint.days if d.day_type != "rest"}


def _rest_days(blueprint) -> set[int]:
    return {d.day_of_week for d in blueprint.days if d.day_type == "rest"}


# ─────────────────────────────────────────────────────────────────────────────
# build_week_plan уважает available_weekdays
# ─────────────────────────────────────────────────────────────────────────────

def test_non_available_days_are_rest():
    """Дни не из списка получают day_type='rest'."""
    user = _make_user(level=2, available_weekdays="1,3,5")
    bp = build_week_plan(
        user=user, week_number=1, period="base",
        target_minutes=150, is_recovery_week=False,
        available_weekdays=[1, 3, 5],
    )
    active = _active_days(bp)
    for day in active:
        assert day in {1, 3, 5}, f"День {day} не должен быть активен"


def test_all_seven_days_available():
    """Когда доступны все 7 дней — ни один день не должен быть 'rest' лишь из-за недоступности."""
    user = _make_user(level=2, available_weekdays="1,2,3,4,5,6,7")
    bp = build_week_plan(
        user=user, week_number=1, period="base",
        target_minutes=200, is_recovery_week=False,
        available_weekdays=[1, 2, 3, 4, 5, 6, 7],
    )
    # Не все 7 будут активны (нет смысла ставить бег 7 дней), но активных >= 4
    assert len(_active_days(bp)) >= 4


def test_weekend_only_days():
    """Только выходные доступны → активные дни только из {6, 7}."""
    user = _make_user(level=1, available_weekdays="6,7")
    bp = build_week_plan(
        user=user, week_number=1, period="base",
        target_minutes=100, is_recovery_week=False,
        available_weekdays=[6, 7],
    )
    active = _active_days(bp)
    for day in active:
        assert day in {6, 7}, f"День {day} вне выходных не должен быть активен"


def test_different_days_produce_different_layout():
    """Разные наборы дней → разные активные дни в плане."""
    user_a = _make_user(level=2, available_weekdays="1,3,5")
    user_b = _make_user(level=2, available_weekdays="2,4,6")

    bp_a = build_week_plan(
        user=user_a, week_number=1, period="base",
        target_minutes=150, is_recovery_week=False,
        available_weekdays=[1, 3, 5],
    )
    bp_b = build_week_plan(
        user=user_b, week_number=1, period="base",
        target_minutes=150, is_recovery_week=False,
        available_weekdays=[2, 4, 6],
    )

    assert _active_days(bp_a).issubset({1, 3, 5})
    assert _active_days(bp_b).issubset({2, 4, 6})
    # Никакого пересечения
    assert _active_days(bp_a).isdisjoint(_active_days(bp_b))


# ─────────────────────────────────────────────────────────────────────────────
# Смена дней применяется на следующей неделе
# ─────────────────────────────────────────────────────────────────────────────

def test_new_days_apply_next_week():
    """
    Изменение available_weekdays на объекте user → при следующем вызове
    build_week_plan берётся уже новый список.
    """
    user = _make_user(level=2, available_weekdays="1,3,5")

    # Неделя 1 — старые дни
    bp1 = build_week_plan(
        user=user, week_number=1, period="base",
        target_minutes=150, is_recovery_week=False,
        available_weekdays=parse_available_weekdays(user.available_weekdays),
    )

    # Пользователь меняет расписание в середине цикла
    user.available_weekdays = "2,4,6"

    # Неделя 2 — новые дни
    bp2 = build_week_plan(
        user=user, week_number=2, period="base",
        target_minutes=150, is_recovery_week=False,
        available_weekdays=parse_available_weekdays(user.available_weekdays),
    )

    assert _active_days(bp1).issubset({1, 3, 5})
    assert _active_days(bp2).issubset({2, 4, 6})


def test_current_week_unaffected_by_change():
    """
    Текущая неделя строилась со старыми днями — новый список не трогает её.
    Это гарантируется тем, что build_week_plan принимает explicit список.
    """
    user = _make_user(level=2, available_weekdays="1,3,5")

    bp_old = build_week_plan(
        user=user, week_number=3, period="base",
        target_minutes=150, is_recovery_week=False,
        available_weekdays=[1, 3, 5],  # передан явно — как при создании
    )

    # После смены user.available_weekdays старый plan не пересчитывается
    user.available_weekdays = "2,4,6"

    # Имитируем получение плана текущей недели (дни не меняются, план уже в БД)
    active_old = _active_days(bp_old)
    assert active_old.issubset({1, 3, 5})


# ─────────────────────────────────────────────────────────────────────────────
# По уровням
# ─────────────────────────────────────────────────────────────────────────────

def test_l1_minimum_3_days():
    """L1 работает с минимальным набором из 3 дней."""
    user = _make_user(level=1, available_weekdays="1,3,5",
                      l1_long_independent=False, l1_easy_reached_40min=False)
    bp = build_week_plan(
        user=user, week_number=1, period="base",
        target_minutes=120, is_recovery_week=False,
        available_weekdays=[1, 3, 5],
    )
    assert len(_active_days(bp)) >= 2  # хотя бы 2 активных дня из 3


def test_l2_4_available_days():
    """L2 с 4 доступными днями — все активные только из этих 4."""
    days = [1, 3, 5, 7]
    user = _make_user(level=2, available_weekdays="1,3,5,7")
    bp = build_week_plan(
        user=user, week_number=1, period="base",
        target_minutes=180, is_recovery_week=False,
        available_weekdays=days,
    )
    active = _active_days(bp)
    for day in active:
        assert day in set(days), f"День {day} вне допустимых"


def test_l3_5_available_days():
    """L3 regular с 5 доступными днями."""
    days = [1, 2, 4, 5, 6]
    user = _make_user(level=3, available_weekdays="1,2,4,5,6")
    bp = build_week_plan(
        user=user, week_number=1, period="base",
        target_minutes=300, is_recovery_week=False,
        available_weekdays=days,
    )
    active = _active_days(bp)
    for day in active:
        assert day in set(days)


def test_all_days_in_blueprint_cover_full_week():
    """WeekBlueprint всегда содержит записи для всех 7 дней."""
    user = _make_user(level=2, available_weekdays="1,3,5")
    bp = build_week_plan(
        user=user, week_number=1, period="base",
        target_minutes=150, is_recovery_week=False,
        available_weekdays=[1, 3, 5],
    )
    dows = {d.day_of_week for d in bp.days}
    assert dows == {1, 2, 3, 4, 5, 6, 7}
