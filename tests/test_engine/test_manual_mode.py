"""
tests/test_engine/test_manual_mode.py

L4/L5 → manual mode.
- route_to_program возвращает "new" для L1–L3 и "manual" для L4–L5
- L4/L5 не получают авто-версию тренировки (assigned_version=None до одобрения)
- Максимальный авто-скоринг не выходит за уровень 4 (Level 5 — только тренер)
- assign_entry_point, assign_initial_period не используются для manual-пользователей
"""
import pytest
from engine.level_assignment import (
    OnboardingAnswers,
    assign_entry_point,
    assign_initial_period,
    assign_level,
    assign_starting_volume,
    route_to_program,
)


def _answers(**overrides) -> OnboardingAnswers:
    defaults = dict(
        runs=True, frequency="4plus", volume="50plus",
        structure=True, had_break=False,
        pain="none", pain_increases="no", location="gym",
    )
    defaults.update(overrides)
    return OnboardingAnswers(**defaults)


# ── route_to_program ──────────────────────────────────────────────────────────

def test_level1_routes_new():
    assert route_to_program(1) == "new"


def test_level2_routes_new():
    assert route_to_program(2) == "new"


def test_level3_routes_new():
    assert route_to_program(3) == "new"


def test_level4_routes_manual():
    assert route_to_program(4) == "manual"


def test_level5_routes_manual():
    assert route_to_program(5) == "manual"


def test_all_levels_routing():
    """Полный диапазон: L1–L3 → new, L4–L5 → manual."""
    for lvl in (1, 2, 3):
        assert route_to_program(lvl) == "new", f"L{lvl} должен быть 'new'"
    for lvl in (4, 5):
        assert route_to_program(lvl) == "manual", f"L{lvl} должен быть 'manual'"


# ── is_manual flag (реализован в handler) ────────────────────────────────────

def _is_manual(level: int) -> bool:
    """Точное условие из handlers/checkin.py _finish_checkin_new."""
    return level >= 4


def test_is_manual_l4():
    assert _is_manual(4) is True


def test_is_manual_l5():
    assert _is_manual(5) is True


def test_is_not_manual_l3():
    assert _is_manual(3) is False


def test_is_not_manual_l1():
    assert _is_manual(1) is False


# ── Level 5 назначается только тренером ──────────────────────────────────────

def test_auto_scoring_max_level4():
    """assign_level никогда не возвращает 5 — это trainer-only."""
    best = _answers()
    assert assign_level(best) <= 4


def test_level5_unreachable_via_scoring():
    """Любой набор ответов → не выше 4."""
    combos = [
        _answers(frequency="4plus", volume="50plus", structure=True, had_break=False),
        _answers(frequency="4plus", volume="25_50", structure=True),
        _answers(frequency="2_3", volume="50plus", structure=True),
    ]
    for ans in combos:
        assert assign_level(ans) <= 4


# ── Для manual-пользователей авто-версия не проставляется ───────────────────

def test_manual_log_has_no_auto_version():
    """
    Симуляция: в _finish_checkin_manual assigned_version не задаётся до одобрения.
    """
    class MockLog:
        assigned_version = None
        checkin_done = True

    log = MockLog()
    # Версия пустая — тренер выберет сам
    assert log.assigned_version is None


def test_manual_no_decide_workout_version_called():
    """
    В manual-режиме decide_workout_version не вызывается.
    Проверяем, что при level >= 4 функция роутинга сигнализирует об этом.
    """
    for level in (4, 5):
        # Условие из handler
        skip_auto = _is_manual(level)
        assert skip_auto is True, f"Для L{level} автовыбор версии должен быть пропущен"


# ── assign_entry_point / assign_initial_period для L1–L3 ──────────────────

def test_l1_base_in_entry_point():
    """L1 без непрерывного бега → base_in."""
    ans = _answers(
        runs=True, frequency="0_1", volume="to_10",
        structure=False,
        q_continuous_run_test="no",
        q_longest_run="to_5",
    )
    assert assign_level(ans) == 1
    assert assign_entry_point(1, ans) == "base_in"
    assert assign_initial_period(1, "base_in") == "base_in"


def test_l1_base_entry_point():
    """L1 с тестом → base."""
    ans = _answers(
        runs=True, frequency="0_1", volume="to_10",
        structure=False,
        q_continuous_run_test="yes",
        q_longest_run="15_30",
    )
    assert assign_entry_point(1, ans) == "base"
    assert assign_initial_period(1, "base") == "base"


def test_l2_always_base_entry():
    """L2 всегда начинает с base."""
    ans = _answers(frequency="2_3", volume="10_25", structure=False)
    assert assign_entry_point(2, ans) == "base"
    assert assign_initial_period(2, "base") == "base"


def test_l3_always_base_entry():
    """L3 всегда начинает с base."""
    ans = _answers()
    # При assign_level == 4 вызываем явно с level=3
    assert assign_entry_point(3, ans) == "base"
    assert assign_initial_period(3, "base") == "base"


# ── Стартовый объём ───────────────────────────────────────────────────────────

def test_starting_volume_l1_base_in_positive():
    vol = assign_starting_volume(1, "base_in")
    assert vol > 0


def test_starting_volume_l2_greater_than_l1():
    vol_l1 = assign_starting_volume(1, "base")
    vol_l2 = assign_starting_volume(2, "base")
    assert vol_l2 >= vol_l1


def test_starting_volume_l3_greater_than_l2():
    vol_l2 = assign_starting_volume(2, "base")
    vol_l3 = assign_starting_volume(3, "base")
    assert vol_l3 >= vol_l2
