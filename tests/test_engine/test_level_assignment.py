import pytest
from engine.level_assignment import OnboardingAnswers, assign_level


def make_answers(**overrides) -> OnboardingAnswers:
    """Base: a healthy regular runner — Level 4 baseline."""
    defaults = dict(
        frequency="2_3x",
        volume="60_to_120",
        regularity="regularly",
        break_status="no_break",
        pain="none",
        pain_increases="no",
        strength="sometimes",
        location="gym",
    )
    defaults.update(overrides)
    return OnboardingAnswers(**defaults)


def level5_answers(**overrides) -> OnboardingAnswers:
    """Base: high-volume competitive runner — Level 5 baseline."""
    defaults = dict(
        frequency="4plus",
        volume="120plus",
        regularity="regularly",
        break_status="no_break",
        pain="none",
        pain_increases="no",
        strength="regularly",
        location="gym",
    )
    defaults.update(overrides)
    return OnboardingAnswers(**defaults)


# ── Level 1 ──────────────────────────────────────────────────────────────────

def test_level1_active_pain():
    assert assign_level(make_answers(pain="yes")) == 1


def test_level1_no_running():
    assert assign_level(make_answers(frequency="not_at_all")) == 1


def test_level1_long_break():
    assert assign_level(make_answers(break_status="long_break")) == 1


def test_level1_pain_overrides_high_frequency():
    """Even a frequent runner with active pain → Level 1."""
    assert assign_level(make_answers(frequency="4plus", pain="yes")) == 1


# ── Level 2 ──────────────────────────────────────────────────────────────────

def test_level2_had_break():
    assert assign_level(make_answers(break_status="had_break", regularity="sometimes")) == 2


def test_level2_no_system():
    assert assign_level(make_answers(regularity="no_system")) == 2


def test_level2_had_break_and_no_system():
    assert assign_level(make_answers(break_status="had_break", regularity="no_system")) == 2


# ── Level 3 ──────────────────────────────────────────────────────────────────

def test_level3_sometimes_regular_no_break():
    """Runs sometimes, no break, no pain → Level 3 (not quite Level 4)."""
    assert assign_level(make_answers(regularity="sometimes", break_status="no_break")) == 3


def test_level3_once_per_week_regular():
    assert assign_level(make_answers(frequency="once", regularity="regularly")) == 3


# ── Level 4 ──────────────────────────────────────────────────────────────────

def test_level4_perfect_profile():
    assert assign_level(make_answers()) == 4


def test_level4_4plus_frequency():
    assert assign_level(make_answers(frequency="4plus")) == 4


def test_level4_requires_no_break():
    """Level 4 requires no_break; had_break drops to Level 2."""
    assert assign_level(make_answers(break_status="had_break")) == 2


def test_level4_requires_regular():
    """Level 4 requires regularly; sometimes drops to Level 3."""
    assert assign_level(make_answers(regularity="sometimes")) == 3


def test_level4_requires_no_pain():
    """Level 4 requires no pain; little pain → not Level 4."""
    result = assign_level(make_answers(pain="little"))
    assert result in (2, 3)  # depends on other fields, but never 4


def test_level4_high_freq_low_volume_stays_4():
    """4plus frequency + 60_to_120 volume (not 120plus) → Level 4, not 5."""
    assert assign_level(make_answers(frequency="4plus", volume="60_to_120")) == 4


# ── Level 5 ──────────────────────────────────────────────────────────────────

def test_level5_perfect_profile():
    assert assign_level(level5_answers()) == 5


def test_level5_requires_4plus_frequency():
    """2_3x frequency + 120plus volume → not Level 5 (Level 4)."""
    assert assign_level(level5_answers(frequency="2_3x")) == 4


def test_level5_requires_120plus_volume():
    """4plus frequency + 60_to_120 volume → Level 4, not 5."""
    assert assign_level(level5_answers(volume="60_to_120")) == 4


def test_level5_requires_no_break():
    """had_break → falls to Level 2 regardless of frequency/volume."""
    assert assign_level(level5_answers(break_status="had_break")) == 2


def test_level5_requires_no_pain():
    """Active pain overrides everything → Level 1."""
    assert assign_level(level5_answers(pain="yes")) == 1


def test_level5_requires_regular():
    """sometimes regularity → Level 3, not 5."""
    assert assign_level(level5_answers(regularity="sometimes")) == 3
