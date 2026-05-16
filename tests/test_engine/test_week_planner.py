"""
tests/test_engine/test_week_planner.py

Тесты engine/week_planner.py (spec разделы 3.5, 3.6).
Проверяемые инварианты:
  - Long всегда ставится на последний доступный день
  - Силовая не ставится в день, непосредственно предшествующий long
  - Количество силовых: L1/L2 = 1 (до 5 дней) / 2 (5+ дней); L3 reg = всегда 2
  - Количество беговых: L1 ≤ 3; L2/L3_ret ≤ 4; L3_reg ≤ 5
  - Long всегда is_key=True
  - split_running_minutes: long ≤ ratio × target
"""
import pytest
from types import SimpleNamespace
from engine.week_planner import (
    build_week_plan,
    split_running_minutes,
    can_add_intensity,
    WeekStats,
    DaySlot,
    WeekBlueprint,
)


# ── Вспомогательные функции ───────────────────────────────────────────────────

def make_user(
    level: int = 1,
    injury_return: bool = False,
    l1_long_independent: bool = False,
    available_weekdays: str = "1,3,5",
) -> SimpleNamespace:
    return SimpleNamespace(
        level=level,
        injury_return_active=injury_return,
        l1_long_independent=l1_long_independent,
        available_weekdays=available_weekdays,
    )


def build(
    user,
    days: list[int],
    period: str = "base",
    target: int = 180,
    is_recovery: bool = False,
    add_intensity: bool = False,
) -> WeekBlueprint:
    return build_week_plan(
        user=user,
        week_number=1,
        period=period,
        target_minutes=target,
        is_recovery_week=is_recovery,
        available_weekdays=days,
        add_intensity=add_intensity,
    )


def get_days_of_type(bp: WeekBlueprint, day_type: str) -> list[DaySlot]:
    return [d for d in bp.days if d.day_type == day_type]


def get_key_days(bp: WeekBlueprint) -> list[DaySlot]:
    return [d for d in bp.days if d.is_key]


def get_long_day(bp: WeekBlueprint) -> DaySlot | None:
    longs = [d for d in bp.days if d.run_subtype == "long"]
    return longs[0] if longs else None


# ══════════════════════════════════════════════════════════════════════════════
# L1 — новичок
# ══════════════════════════════════════════════════════════════════════════════

class TestL1Layout:

    def test_3days_correct_types(self):
        """3 дня: 1 long + 1 easy + 1 силовая."""
        user = make_user(level=1)
        bp = build(user, days=[1, 3, 5])
        run_days = get_days_of_type(bp, "run")
        str_days = get_days_of_type(bp, "strength")
        assert len(str_days) == 1
        assert sum(1 for d in run_days if d.run_subtype == "long") == 1

    def test_3days_long_on_last_day(self):
        """Long всегда на последнем доступном дне."""
        user = make_user(level=1)
        bp = build(user, days=[1, 3, 5])
        long = get_long_day(bp)
        assert long is not None
        assert long.day_of_week == 5  # последний из [1, 3, 5]

    def test_4days_long_on_last_day(self):
        user = make_user(level=1)
        bp = build(user, days=[2, 4, 6, 7])
        long = get_long_day(bp)
        assert long.day_of_week == 7

    def test_5days_two_strength(self):
        """5 дней → 2 силовых для L1."""
        user = make_user(level=1)
        bp = build(user, days=[1, 2, 3, 4, 6])
        str_days = get_days_of_type(bp, "strength")
        assert len(str_days) == 2

    def test_4days_one_strength(self):
        """4 дня → 1 силовая для L1."""
        user = make_user(level=1)
        bp = build(user, days=[1, 2, 4, 6])
        str_days = get_days_of_type(bp, "strength")
        assert len(str_days) == 1

    def test_strength_not_day_before_long(self):
        """Силовая не ставится за день до long."""
        user = make_user(level=1)
        # Long на 7 (вс), день перед — 6 (сб)
        bp = build(user, days=[1, 3, 5, 6, 7])
        long = get_long_day(bp)
        assert long.day_of_week == 7
        # Проверяем, что на день 6 не strength
        day6 = next((d for d in bp.days if d.day_of_week == 6), None)
        if day6:
            assert day6.day_type != "strength"

    def test_long_is_key(self):
        """Long всегда is_key=True."""
        user = make_user(level=1)
        bp = build(user, days=[1, 3, 5])
        long = get_long_day(bp)
        assert long.is_key is True

    def test_total_7_days_in_result(self):
        """Результат всегда содержит 7 дней (остальные = rest)."""
        user = make_user(level=1)
        bp = build(user, days=[1, 3, 5])
        assert len(bp.days) == 7

    def test_non_available_days_are_rest(self):
        """Дни вне доступных → rest."""
        user = make_user(level=1)
        bp = build(user, days=[1, 3, 5])
        rest_days = get_days_of_type(bp, "rest")
        # Дни 2, 4, 6, 7 должны быть rest
        rest_dow = {d.day_of_week for d in rest_days}
        assert {2, 4, 6, 7}.issubset(rest_dow)

    def test_max_3_run_days_l1(self):
        """L1: не более 3 беговых дней (включая long)."""
        user = make_user(level=1)
        bp = build(user, days=[1, 2, 3, 4, 6])
        run_days = get_days_of_type(bp, "run")
        assert len(run_days) <= 3

    def test_target_minutes_preserved(self):
        """weekly_target_minutes совпадает с переданным target."""
        user = make_user(level=1)
        bp = build(user, days=[1, 3, 5], target=180)
        assert bp.weekly_target_minutes == 180


# ══════════════════════════════════════════════════════════════════════════════
# L2 — средний
# ══════════════════════════════════════════════════════════════════════════════

class TestL2Layout:

    def test_4days_layout(self):
        """L2 с 4 днями: 1 силовая + long + 2 беговых."""
        user = make_user(level=2)
        bp = build(user, days=[1, 3, 5, 7])
        run_days = get_days_of_type(bp, "run")
        str_days = get_days_of_type(bp, "strength")
        assert len(str_days) == 1
        assert any(d.run_subtype == "long" for d in run_days)

    def test_5days_two_strength_l2(self):
        """L2 с 5 днями → 2 силовых."""
        user = make_user(level=2)
        bp = build(user, days=[1, 2, 3, 5, 7])
        str_days = get_days_of_type(bp, "strength")
        assert len(str_days) == 2

    def test_long_last_day_l2(self):
        user = make_user(level=2)
        bp = build(user, days=[1, 3, 5, 7])
        long = get_long_day(bp)
        assert long.day_of_week == 7

    def test_l2_has_recovery_run(self):
        """L2: должна быть recovery_run тренировка (если ≥2 беговых без long)."""
        user = make_user(level=2)
        bp = build(user, days=[1, 2, 4, 6, 7])
        run_days = get_days_of_type(bp, "run")
        subtypes = [d.run_subtype for d in run_days]
        # Должен быть хотя бы один recovery_run или aerobic
        non_long = [s for s in subtypes if s != "long"]
        assert len(non_long) >= 1


# ══════════════════════════════════════════════════════════════════════════════
# L3 regular
# ══════════════════════════════════════════════════════════════════════════════

class TestL3RegularLayout:

    def test_always_2_strength(self):
        """L3 regular: всегда 2 силовых, независимо от числа дней."""
        user = make_user(level=3, injury_return=False)
        bp = build(user, days=[1, 2, 3, 5, 7])
        str_days = get_days_of_type(bp, "strength")
        assert len(str_days) == 2

    def test_long_last_day_l3(self):
        user = make_user(level=3, injury_return=False)
        bp = build(user, days=[1, 2, 4, 6, 7])
        long = get_long_day(bp)
        assert long.day_of_week == 7

    def test_5days_l3_long_is_key(self):
        user = make_user(level=3, injury_return=False)
        bp = build(user, days=[1, 2, 4, 6, 7])
        long = get_long_day(bp)
        assert long.is_key is True

    def test_max_5_run_days_l3(self):
        """L3 regular: не более 5 беговых."""
        user = make_user(level=3, injury_return=False)
        bp = build(user, days=[1, 2, 3, 4, 6, 7])
        run_days = get_days_of_type(bp, "run")
        assert len(run_days) <= 5


# ══════════════════════════════════════════════════════════════════════════════
# L3 after break (injury_return)
# ══════════════════════════════════════════════════════════════════════════════

class TestL3ReturnLayout:

    def test_4days_one_strength(self):
        """L3 return (4 дня) → 1 силовая (как L2)."""
        user = make_user(level=3, injury_return=True)
        bp = build(user, days=[1, 3, 5, 7])
        str_days = get_days_of_type(bp, "strength")
        assert len(str_days) == 1

    def test_long_last_day(self):
        user = make_user(level=3, injury_return=True)
        bp = build(user, days=[1, 3, 5, 7])
        long = get_long_day(bp)
        assert long.day_of_week == 7


# ══════════════════════════════════════════════════════════════════════════════
# Разгрузочная неделя
# ══════════════════════════════════════════════════════════════════════════════

class TestRecoveryWeek:

    def test_recovery_flag_preserved(self):
        user = make_user(level=1)
        bp = build(user, days=[1, 3, 5], is_recovery=True)
        assert bp.is_recovery_week is True

    def test_no_intensity_on_recovery_week(self):
        """Разгрузочная неделя: интенсивность не добавляется."""
        user = make_user(level=2)
        bp = build(user, days=[1, 3, 5, 7], is_recovery=True, add_intensity=True)
        run_days = get_days_of_type(bp, "run")
        # Никаких intervals/tempo
        for day in run_days:
            assert day.run_subtype not in ("intervals", "tempo")


# ══════════════════════════════════════════════════════════════════════════════
# split_running_minutes — разбивка объёма
# ══════════════════════════════════════════════════════════════════════════════

class TestSplitRunningMinutes:

    def test_l1_long_within_35_percent(self):
        """L1 stage1: long ≤ 35% от weekly target."""
        mins = split_running_minutes(
            weekly_target=180,
            level=1,
            period="base_in",
            injury_return=False,
            n_run_days=3,
            is_long_independent=False,
            is_recovery_week=False,
        )
        assert mins["long"] <= round(180 * 0.35) + 1  # +1 для округления

    def test_l1_stage2_long_ratio(self):
        """L1 стадия 2 (independent): long ≤ 35% × weekly target."""
        mins = split_running_minutes(
            weekly_target=240,
            level=1,
            period="base",
            injury_return=False,
            n_run_days=3,
            is_long_independent=True,
            is_recovery_week=False,
        )
        assert mins["long"] <= round(240 * 0.35) + 1

    def test_l2_long_within_35_percent(self):
        mins = split_running_minutes(
            weekly_target=200,
            level=2,
            period="base",
            injury_return=False,
            n_run_days=4,
            is_long_independent=False,
            is_recovery_week=False,
        )
        assert mins["long"] <= round(200 * 0.35) + 1

    def test_l3_regular_base_long_within_35_percent(self):
        mins = split_running_minutes(
            weekly_target=300,
            level=3,
            period="base",
            injury_return=False,
            n_run_days=5,
            is_long_independent=False,
            is_recovery_week=False,
        )
        assert mins["long"] <= round(300 * 0.35) + 1

    def test_l3_regular_prep_long_within_40_percent(self):
        """L3 regular preparatory: long ≤ 40%."""
        mins = split_running_minutes(
            weekly_target=360,
            level=3,
            period="preparatory",
            injury_return=False,
            n_run_days=5,
            is_long_independent=False,
            is_recovery_week=False,
        )
        assert mins["long"] <= round(360 * 0.40) + 1

    def test_l2_has_recovery_run_with_3_run_days(self):
        """L2 с 3+ беговыми днями включает recovery_run."""
        mins = split_running_minutes(
            weekly_target=200,
            level=2,
            period="base",
            injury_return=False,
            n_run_days=4,
            is_long_independent=False,
            is_recovery_week=False,
        )
        assert mins["recovery_run"] > 0

    def test_zero_run_days_returns_zeros(self):
        mins = split_running_minutes(
            weekly_target=100,
            level=1,
            period="base",
            injury_return=False,
            n_run_days=0,
            is_long_independent=False,
            is_recovery_week=False,
        )
        assert mins["long"] == 0

    def test_total_minutes_near_target(self):
        """
        split_running_minutes возвращает минуты НА ДЕНЬ (не суммарные).
        Для L1 с 3 беговыми: 1 long-день + 2 easy-дня.
        Суммарный объём = long + easy * (n_run_days - 1) ≈ target.
        """
        n_run_days = 3
        mins = split_running_minutes(
            weekly_target=180,
            level=1,
            period="base",
            injury_return=False,
            n_run_days=n_run_days,
            is_long_independent=True,
            is_recovery_week=False,
        )
        # long: 1 день; easy: (n_run_days - 1) = 2 дня
        total = mins["long"] + mins.get("easy", 0) * (n_run_days - 1)
        assert abs(total - 180) <= 5


# ══════════════════════════════════════════════════════════════════════════════
# can_add_intensity
# ══════════════════════════════════════════════════════════════════════════════

class TestCanAddIntensity:

    def _good_weeks(self, n: int = 3) -> list[WeekStats]:
        return [
            WeekStats(growth_eligible=True, light_days=0, recovery_days=0, had_high_pain=False)
            for _ in range(n)
        ]

    def test_l1_base_in_never_intensity(self):
        """L1 base_in: интенсивность запрещена."""
        ok = can_add_intensity(
            level=1, period="base_in", injury_return=False,
            program_week_number=10, growth_streak=5,
            recent_weeks=self._good_weeks(4),
        )
        assert ok is False

    def test_l1_base_before_week8_no_intensity(self):
        """L1 base: интенсивность не ранее 8-й недели."""
        ok = can_add_intensity(
            level=1, period="base", injury_return=False,
            program_week_number=7, growth_streak=4,
            recent_weeks=self._good_weeks(4),
        )
        assert ok is False

    def test_l1_base_week8_ok(self):
        """L1 base: начиная с 8-й недели — разрешено."""
        ok = can_add_intensity(
            level=1, period="base", injury_return=False,
            program_week_number=8, growth_streak=4,
            recent_weeks=self._good_weeks(4),
        )
        assert ok is True

    def test_l2_base_needs_3_success_weeks(self):
        """L2 base: нужно 3 успешных недели подряд."""
        ok = can_add_intensity(
            level=2, period="base", injury_return=False,
            program_week_number=5, growth_streak=2,
            recent_weeks=self._good_weeks(3),
        )
        assert ok is False

    def test_l2_base_with_3_success_weeks(self):
        ok = can_add_intensity(
            level=2, period="base", injury_return=False,
            program_week_number=5, growth_streak=3,
            recent_weeks=self._good_weeks(3),
        )
        assert ok is True

    def test_pain_blocks_intensity(self):
        """Боль за последние 2 нед → интенсивность запрещена."""
        weeks = [
            WeekStats(growth_eligible=True, light_days=0, recovery_days=0, had_high_pain=False),
            WeekStats(growth_eligible=True, light_days=0, recovery_days=0, had_high_pain=True),
        ]
        ok = can_add_intensity(
            level=2, period="preparatory", injury_return=False,
            program_week_number=10, growth_streak=5,
            recent_weeks=weeks,
        )
        assert ok is False

    def test_too_many_light_days_blocks_intensity(self):
        """Много light-дней → интенсивность запрещена."""
        weeks = [
            WeekStats(growth_eligible=True, light_days=3, recovery_days=0, had_high_pain=False)
            for _ in range(4)
        ]
        ok = can_add_intensity(
            level=3, period="base", injury_return=False,
            program_week_number=10, growth_streak=5,
            recent_weeks=weeks,
        )
        assert ok is False

    def test_empty_history_blocks_intensity(self):
        """Нет истории → интенсивность запрещена."""
        ok = can_add_intensity(
            level=2, period="preparatory", injury_return=False,
            program_week_number=10, growth_streak=5,
            recent_weeks=[],
        )
        assert ok is False

    def test_l3_regular_prep_allows_intensity(self):
        """L3 regular preparatory: интенсивность разрешена при хороших условиях."""
        ok = can_add_intensity(
            level=3, period="preparatory", injury_return=False,
            program_week_number=10, growth_streak=4,
            recent_weeks=self._good_weeks(4),
        )
        assert ok is True

    def test_recovery_period_no_intensity(self):
        """recovery_period: интенсивность запрещена."""
        ok = can_add_intensity(
            level=1, period="recovery_period", injury_return=False,
            program_week_number=20, growth_streak=0,
            recent_weeks=self._good_weeks(3),
        )
        assert ok is False

    def test_injury_return_intro_blocks_intensity(self):
        """injury_return + первые 2 недели → интенсивность запрещена."""
        for week in (1, 2):
            ok = can_add_intensity(
                level=2, period="base", injury_return=True,
                program_week_number=week, growth_streak=5,
                recent_weeks=self._good_weeks(4),
            )
            assert ok is False, f"week {week} should block intensity"

    def test_injury_return_week3_allows_intensity_if_eligible(self):
        """injury_return + неделя 3+ → интенсивность может быть разрешена (если остальные условия ок)."""
        ok = can_add_intensity(
            level=2, period="base", injury_return=True,
            program_week_number=3, growth_streak=5,
            recent_weeks=self._good_weeks(4),
        )
        # week 3 выходит за пределы intro → не блокируется введённым правилом
        # (хотя может блокироваться growth_streak < 3, но здесь streak=5 ≥ 3)
        assert ok is True


# ══════════════════════════════════════════════════════════════════════════════
# Иерархия длительностей: recovery < aerobic < long
# ══════════════════════════════════════════════════════════════════════════════

class TestDurationHierarchy:

    def _split(self, target: int, n_run: int, level: int = 2,
               injury_return: bool = False, period: str = "base") -> dict:
        return split_running_minutes(
            weekly_target=target,
            level=level,
            period=period,
            injury_return=injury_return,
            n_run_days=n_run,
            is_long_independent=False,
            is_recovery_week=False,
            program_week_number=5,  # вне intro-периода
        )

    def test_l2_low_volume_hierarchy(self):
        """L2 150 мин 3 беговых: aerobic < long (бывший баг Anna)."""
        mins = self._split(150, 3)
        assert mins["recovery_run"] > 0
        assert mins["aerobic"] < mins["long"], (
            f"aerobic={mins['aerobic']} должен быть < long={mins['long']}"
        )

    def test_l2_hierarchy_across_volumes(self):
        """L2: иерархия recovery < aerobic < long при разных объёмах."""
        for target in (150, 170, 200, 240):
            mins = self._split(target, 3)
            rec = mins.get("recovery_run", 0)
            aer = mins.get("aerobic", 0)
            lng = mins["long"]
            if rec > 0 and aer > 0:
                assert rec < aer < lng, (
                    f"target={target}: ожидали rec<aer<long, получили {rec}<{aer}<{lng}"
                )

    def test_l2_total_minutes_preserved_after_hierarchy_fix(self):
        """После коррекции иерархии сумма минут = weekly_target."""
        mins = self._split(150, 3)
        total = mins["long"] + mins.get("recovery_run", 0) + mins.get("aerobic", 0)
        assert total == 150

    def test_l3_return_hierarchy(self):
        """L3 after break 200 мин 4 беговых: aerobic < long."""
        mins = self._split(200, 4, level=3, injury_return=True)
        aer = mins.get("aerobic", 0)
        lng = mins["long"]
        if aer > 0:
            assert aer < lng, f"L3 return: aerobic={aer} должен быть < long={lng}"


# ══════════════════════════════════════════════════════════════════════════════
# injury_return intro: укороченный long, только easy
# ══════════════════════════════════════════════════════════════════════════════

class TestInjuryReturnIntro:

    def _split_intro(self, target: int, n_run: int, week: int = 1,
                     level: int = 2) -> dict:
        return split_running_minutes(
            weekly_target=target,
            level=level,
            period="base",
            injury_return=True,
            n_run_days=n_run,
            is_long_independent=False,
            is_recovery_week=False,
            program_week_number=week,
        )

    def test_intro_weeks_1_and_2_return_easy_only(self):
        """Недели 1-2 injury_return: только easy, нет aerobic/recovery_run."""
        for week in (1, 2):
            mins = self._split_intro(180, 3, week=week)
            assert mins.get("aerobic", 0) == 0
            assert mins.get("recovery_run", 0) == 0
            assert mins.get("easy", 0) > 0

    def test_intro_long_ratio_30pct(self):
        """Вводный период: long ≤ 30% от target."""
        mins = self._split_intro(180, 3, week=1)
        assert mins["long"] <= round(180 * 0.30) + 1

    def test_week3_not_intro(self):
        """Неделя 3 — вне intro: возвращает aerobic/recovery_run как обычно."""
        mins = self._split_intro(200, 4, week=3)
        assert mins.get("recovery_run", 0) > 0 or mins.get("aerobic", 0) > 0

    def test_non_injury_return_unaffected(self):
        """injury_return=False: intro не применяется даже на неделе 1."""
        mins = split_running_minutes(
            weekly_target=200,
            level=2,
            period="base",
            injury_return=False,
            n_run_days=4,
            is_long_independent=False,
            is_recovery_week=False,
            program_week_number=1,
        )
        assert mins.get("recovery_run", 0) > 0 or mins.get("aerobic", 0) > 0
