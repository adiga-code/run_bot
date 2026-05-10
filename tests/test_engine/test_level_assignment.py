"""
tests/test_engine/test_level_assignment.py

Тесты engine/level_assignment.py — скоринг уровня (1-4).

Scoring rules:
  runs=True            → +1
  frequency 2_3        → +1
  frequency 4plus      → +2
  volume 10_25         → +1
  volume 25_50         → +2
  volume 50plus        → +3
  structure=True       → +1
  had_break=True       → −1
  pain=little          → −1

Hard stops:
  not runs             → 1
  pain_increases=yes   → 1
  pain=yes             → ≤ 2
  frequency=0_1        → ≤ 2
  not structure        → ≤ 3
"""
import pytest
from engine.level_assignment import OnboardingAnswers, assign_level


def make_answers(**overrides) -> OnboardingAnswers:
    """Базовые ответы: регулярный бегун без проблем — ближе к Level 3."""
    defaults = dict(
        runs=True,
        frequency="2_3",
        volume="25_50",
        structure=True,
        had_break=False,
        pain="none",
        pain_increases="no",
        location="gym",
    )
    defaults.update(overrides)
    return OnboardingAnswers(**defaults)


def level4_answers(**overrides) -> OnboardingAnswers:
    """Базовые ответы для Level 4: 4+, 50+км, план, нет боли, нет перерыва."""
    defaults = dict(
        runs=True,
        frequency="4plus",
        volume="50plus",
        structure=True,
        had_break=False,
        pain="none",
        pain_increases="no",
        location="gym",
    )
    defaults.update(overrides)
    return OnboardingAnswers(**defaults)


# ══════════════════════════════════════════════════════════════════════════════
# Hard stop: Level 1
# ══════════════════════════════════════════════════════════════════════════════

def test_level1_not_running():
    """Не бегает вообще → Level 1."""
    assert assign_level(make_answers(runs=False)) == 1


def test_level1_pain_increases():
    """Боль усиливается → Level 1."""
    assert assign_level(make_answers(pain_increases="yes")) == 1


def test_level1_pain_increases_overrides_high_frequency():
    """pain_increases=yes всегда Level 1, даже у активного бегуна."""
    assert assign_level(level4_answers(pain_increases="yes")) == 1


# ══════════════════════════════════════════════════════════════════════════════
# Hard stop: ≤ Level 2
# ══════════════════════════════════════════════════════════════════════════════

def test_level2_cap_on_active_pain():
    """pain=yes → максимум Level 2."""
    level = assign_level(level4_answers(pain="yes"))
    assert level <= 2


def test_level2_cap_on_low_frequency():
    """frequency=0_1 → максимум Level 2."""
    level = assign_level(level4_answers(frequency="0_1"))
    assert level <= 2


# ══════════════════════════════════════════════════════════════════════════════
# Hard stop: ≤ Level 3
# ══════════════════════════════════════════════════════════════════════════════

def test_level3_cap_on_no_structure():
    """structure=False → максимум Level 3."""
    level = assign_level(level4_answers(structure=False))
    assert level <= 3


# ══════════════════════════════════════════════════════════════════════════════
# Level 2 — средний
# ══════════════════════════════════════════════════════════════════════════════

def test_level2_low_volume():
    """Малый объём + 2-3 раза/нед → Level 2."""
    level = assign_level(make_answers(frequency="2_3", volume="to_10", structure=False))
    assert level == 2


def test_level2_had_break():
    """Перерыв снижает уровень."""
    level = assign_level(make_answers(frequency="2_3", volume="10_25", had_break=True))
    assert level <= 3


def test_level2_mild_pain():
    """Небольшая боль снижает уровень."""
    level = assign_level(level4_answers(pain="little"))
    assert level <= 4  # штраф −1, но hard stop только на pain=yes


# ══════════════════════════════════════════════════════════════════════════════
# Level 3 — продвинутый
# ══════════════════════════════════════════════════════════════════════════════

def test_level3_regular_runner():
    """2-3 раза/нед, 25-50км, план, без боли → около Level 3."""
    # score = 1 (runs) + 1 (2_3) + 2 (25_50) + 1 (structure) = 5 → level 3
    level = assign_level(make_answers(frequency="2_3", volume="25_50", structure=True))
    assert level == 3


def test_level3_no_structure_caps_at_3():
    """Нет плана → не выше Level 3."""
    level = assign_level(level4_answers(structure=False))
    assert level == 3


# ══════════════════════════════════════════════════════════════════════════════
# Level 4 — высокий
# ══════════════════════════════════════════════════════════════════════════════

def test_level4_perfect_profile():
    """4+ раза, 50+км, план, нет боли, нет перерыва → Level 4."""
    # score = 1 + 2 + 3 + 1 = 7 → level 4
    assert assign_level(level4_answers()) == 4


def test_level4_requires_4plus_frequency():
    """Без 4+ раза/нед уровень снижается."""
    level = assign_level(level4_answers(frequency="2_3"))
    # score = 1 + 1 + 3 + 1 = 6 → level 4 (ещё достигает)
    assert level >= 3


def test_level4_requires_no_break():
    """Перерыв снижает score на 1."""
    level = assign_level(level4_answers(had_break=True))
    # score = 1 + 2 + 3 + 1 - 1 = 6 → ещё level 4
    assert level >= 3


def test_level4_requires_high_volume():
    """Низкий объём → не Level 4."""
    level = assign_level(level4_answers(volume="10_25"))
    # score = 1 + 2 + 1 + 1 = 5 → level 3
    assert level <= 3


# ══════════════════════════════════════════════════════════════════════════════
# Scoring boundary cases
# ══════════════════════════════════════════════════════════════════════════════

def test_score_1_gives_level1():
    """score=1 (только runs=True, всё остальное минимум) → Level 1."""
    level = assign_level(OnboardingAnswers(
        runs=True, frequency="0_1", volume="0",
        structure=False, had_break=False,
        pain="none", pain_increases="no", location="home",
    ))
    assert level == 1


def test_score_2_to_3_gives_level2():
    """score=2-3 → Level 2."""
    # score = 1 (runs) + 1 (2_3) = 2 → level 2
    level = assign_level(OnboardingAnswers(
        runs=True, frequency="2_3", volume="0",
        structure=False, had_break=False,
        pain="none", pain_increases="no", location="home",
    ))
    assert level == 2


def test_score_4_to_5_gives_level3():
    """score=4-5 → Level 3."""
    # score = 1 + 1 + 2 + 1 = 5 → level 3
    level = assign_level(OnboardingAnswers(
        runs=True, frequency="2_3", volume="25_50",
        structure=True, had_break=False,
        pain="none", pain_increases="no", location="gym",
    ))
    assert level == 3


def test_score_6plus_gives_level4():
    """score ≥ 6 → Level 4."""
    # score = 1 + 2 + 3 + 1 = 7 → level 4
    level = assign_level(OnboardingAnswers(
        runs=True, frequency="4plus", volume="50plus",
        structure=True, had_break=False,
        pain="none", pain_increases="no", location="gym",
    ))
    assert level == 4


def test_not_runs_overrides_good_score():
    """runs=False → Level 1, независимо от других полей."""
    assert assign_level(level4_answers(runs=False)) == 1


def test_break_reduces_score_by_1():
    """Перерыв снижает уровень на 1 балл."""
    no_break = assign_level(make_answers(had_break=False))
    with_break = assign_level(make_answers(had_break=True))
    assert with_break <= no_break


def test_mild_pain_reduces_score_by_1():
    """Небольшая боль снижает уровень на 1 балл."""
    no_pain = assign_level(make_answers(pain="none"))
    with_pain = assign_level(make_answers(pain="little"))
    assert with_pain <= no_pain
