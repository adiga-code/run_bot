# ПЛАН РЕАЛИЗАЦИИ
# Миграция бегового бота на новую логику (MASTER_SPEC v1.0)

> Дата: 2026-05-03  
> Исполнитель: Claude  
> База: Alembic (данные сохраняются). Старая 28-дневная логика продолжает работать.

---

## СТАТУС КОДОВОЙ БАЗЫ

| Файл / компонент | Состояние |
|---|---|
| `engine/constants.py` | ✅ создан — все числовые параметры |
| `engine/week_planner.py` | ✅ создан — build_week_plan, split_running_minutes |
| `engine/week_evaluator.py` | ✅ создан — evaluate_week, decide_next_week |
| `engine/period_transitions.py` | ✅ создан — check_period_transition, check_cycle_end |
| `engine/workout_renderer.py` | ✅ создан — render_workout |
| `engine/fatigue.py` | ⚠️ deprecated-заглушка (старые 28-дн. пользователи) |
| `engine/rule_engine.py` | ✅ переписан — новый приоритет без fatigue |
| `engine/red_flags.py` | ✅ переписан — detect_high_pain_streak |
| `engine/level_assignment.py` | ✅ расширен — assign_initial_period, assign_entry_point |
| `services/week_plan_service.py` | ✅ создан — get_current, close_week, create_for_next_week |
| `database/models.py` — User | ✅ ~25 новых полей добавлены |
| `database/models.py` — WeekPlan | ✅ создана |
| `database/models.py` — DayPlan | ✅ создана |
| `database/models.py` — WorkoutTemplate | ✅ создана |
| `handlers/onboarding.py` | ✅ q_continuous_run_test, q_available_days добавлены |
| `handlers/checkin.py` | ✅ WeekPlan/DayPlan логика добавлена |
| `handlers/workout.py` | ✅ partial убран из UI |
| `handlers/admin.py` | ✅ red flag кнопка + coach override + minutes override |
| `scheduler/tasks.py` | ✅ _check_week_new_system, _create_log_new_system |
| `scripts/migrate_workouts_to_templates.py` | ✅ создан — 546 записей → WorkoutTemplate |
| Alembic | ✅ настроен — async env.py + revision |

---

## 10 ШАГОВ РЕАЛИЗАЦИИ

### ШАГ 0 — Alembic

- Добавить `alembic` и `alembic-utils` в requirements.txt
- `alembic init alembic`
- Настроить `alembic/env.py` — async SQLAlchemy + DATABASE_URL
- Генерировать все миграции через `alembic revision --autogenerate`

---

### ШАГ 1 — Модели БД

**`database/models.py`** — добавляем к существующим таблицам:

#### User — новые поля (~25 штук)
```python
# Доступные дни и объём
available_weekdays: str | None          # "1,3,5" (1=Пн..7=Вс)
weekly_target_minutes: int | None       # текущая цель недели (мин бега)
peak_volume_minutes: int | None         # пик в текущем блоке 3-х недель
last_successful_volume: int | None      # объём последней успешной недели

# Период и цикл
current_period: str | None              # base_in/base/preparatory/specialized/recovery_period
period_start_date: date | None
period_week_number: int = 1
cycle_number: int = 1
cycle_start_date: date | None
program_week_number: int = 1

# Счётчики прогрессии
growth_streak: int = 0
weeks_since_recovery: int = 0

# Red flag / откат
red_flag_active: bool = False
red_flag_reason: str | None
red_flag_at: date | None

# Точка входа и цель
has_goal_race: bool = False
entry_point: str | None                 # base_in / base

# Return-mode (после перерыва)
injury_return_active: bool = False
target_level: int | None
return_mode_started_at: date | None

# L3 regular recovery period
in_macrocycle_recovery: bool = False
macrocycle_recovery_week: int = 0
macrocycle_peak_volume: int | None

# L1 long stage
l1_long_independent: bool = False
l1_no_pain_streak_weeks: int = 0
l1_easy_reached_40min: bool = False

# Онбординг — новые ответы
q_continuous_run_test: str | None       # yes/no/unsure
```

#### Новые таблицы

**`WeekPlan`** — план недели:
```python
id, user_id (FK), week_number, cycle_number, period, period_week_number
start_date, end_date
weekly_target_minutes
is_recovery_week: bool = False
is_rollback_week: bool = False
# Итоги (закрытие недели)
actual_running_minutes: int | None
completion_rate: float | None
keys_completed: bool | None
growth_eligible: bool | None
no_growth_reason: str | None
closed_at: datetime | None
```

**`DayPlan`** — план конкретного дня:
```python
id, week_plan_id (FK, indexed), day_of_week (1=Пн..7=Вс)
day_type: str               # run/strength/recovery/rest/mobility
run_subtype: str | None     # easy/aerobic/recovery_run/long/tempo/intervals/run_walk
planned_minutes: int
intensity: str | None       # null/z3_inclusions/tempo/intervals
is_key: bool = False
is_key_completed: bool | None
session_log_id: int | None  # FK SessionLog
UNIQUE(week_plan_id, day_of_week)
```

**`WorkoutTemplate`** — библиотека шаблонов (заменяет старый `Workout` для новых юзеров):
```python
id, level: int, day_type, run_subtype, version, intensity_kind
period: str | None          # base_in/base/preparatory/null (универсал)
strength_format: str | None # gym/home/null
title, text (с плейсхолдерами {minutes}), short_title
micro_learning, video_url, media_id
```

**`SessionLog`** — новые поля:
```python
# Связь с новой моделью
week_plan_id: int | None    (FK week_plans)
day_plan_id: int | None     (FK day_plans)
day_of_week: int | None     (1-7)
planned_minutes: int | None

# Coach override
coach_override: bool = False
override_version: str | None
override_workout_template_id: int | None
override_text: str | None
override_minutes: int | None
approved_by_admin_id: int | None
approved_at: datetime | None

# Absence-flow аналитика
absence_reason: str | None
absence_reason_text: str | None
absence_responded_at: datetime | None

# Re-checkin tracking
recheckin_count: int = 0
last_checkin_at: datetime | None

# day_index — оставляем (нужен для старых пользователей)
# fatigue_reduction — оставляем как deprecated (не пишем новые, не удаляем)
```

**Индексы:**
- `WeekPlan(user_id, start_date)`
- `WeekPlan(user_id, closed_at)`
- `DayPlan(week_plan_id, day_of_week)` — UNIQUE
- `DayPlan(week_plan_id, is_key)`

**Alembic миграция** — `scripts/migrate_v2.sql` генерируется автоматически.

---

### ШАГ 2 — `engine/constants.py` (НОВЫЙ)

Все цифры из MASTER_SPEC ЧАСТЬ VII в одном месте:
- `GROWTH_MULTIPLIER`, `RECOVERY_MULTIPLIER`, `SUCCESS_THRESHOLD`
- `GROWTH_STREAK_FOR_RECOVERY`, `FAILSAFE_WEEKS_WITHOUT_RECOVERY`
- `MAX_LIGHT_DAYS_PER_WEEK`, `MAX_RECOVERY_DAYS_PER_WEEK`
- `ROLLBACK_PAIN_DAYS`, `ROLLBACK_AUTO_LIFT_WEEKS`
- L1, L2, L3_REGULAR, L3_RETURN, L2_RETURN константы
- `compute_recovery_period_weeks(level, injury_return, cycle_stats) -> int`
- `get_growth_multiplier(level, period, injury_return) -> float`
- `MAX_INTENSITY_PER_WEEK` словарь

---

### ШАГ 3 — engine/week_planner.py + engine/workout_renderer.py (НОВЫЕ)

**`week_planner.py`:**
```python
def build_week_plan(user, week_number, period, target_minutes,
                    is_recovery, available_weekdays) -> WeekPlan
def split_running_minutes(weekly_target, period, level,
                          is_long_independent, long_stage2) -> dict
def can_add_intensity(user, period, recent_weeks) -> bool
```
Логика раскладки по дням:
- Long — последний доступный день
- Силовая не перед long / не перед tempo/intervals
- Минимум 1 день без бега между беговыми
- L3 regular: совмещение силовая + лёгкий бег в один день
- Расчёт минут по уровню/периоду/стадии long

**`workout_renderer.py`:**
```python
def render_workout(template, target_minutes, version,
                   intensity_kind, long_stage=None) -> str
```
- Base: полный план без изменений
- Light: −20%, интервалы/темп → easy
- Recovery: всегда «прогулка 20-30 мин Z1»
- Подстановка `{minutes}` в шаблонах

---

### ШАГ 4 — engine/week_evaluator.py + engine/period_transitions.py (НОВЫЕ)

**`week_evaluator.py`:**
```python
@dataclass
class WeekEvaluation:
    completion_rate, keys_completed, had_high_pain
    high_pain_streak, mild_pain_streak
    light_days, recovery_days, actual_minutes
    growth_eligible, no_growth_reason, triggers_rollback

def evaluate_week(week_plan, logs) -> WeekEvaluation
def decide_next_week(user, current_week, evaluation) -> NextWeekDecision
```
7 условий успешной недели (раздел 3.9.1 spec):
1. ≥85% выполнения
2. Все 3 ключевые выполнены
3. Нет pain==3
4. pain==2 ≤ 2 дней
5. Light ≤ 2 дней
6. Recovery ≤ 1 дня
7. Не 3+ дней без чек-ина

Прогрессия: actual × growth_mult (10% / 15% для L3 prep).  
Weekly unload: growth_streak==3 или fail-safe weeks_since_recovery==6 → × 0.6.

**`period_transitions.py`:**
```python
def check_period_transition(user, recent_weeks) -> str | None
def check_cycle_end(user, current_week_evaluation) -> bool
def start_new_cycle(user, mode: "advance"|"stay"|"redo") -> None
def check_l1_long_stage_transition(user, recent_weeks) -> bool
def check_injury_return_exit(user, recent_weeks) -> bool
def should_apply_weekly_unload(user, weeks_until_recovery_period: int) -> bool
```

Условия переходов периодов:
- L1 base_in→base: 4+ нед, ≥85%, может бежать 20 мин, нет боли
- L1 base→specialized: 6+ нед, есть цель, ≥85%, нет боли
- L2/L3 base→preparatory: 6+ нед, ≥85%, нет боли

После конца цикла: спрашиваем пользователя «Перейти выше / Остаться?»

---

### ШАГ 5 — Переписать engine/rule_engine.py, удалить fatigue.py, переписать red_flags.py

**`rule_engine.py`** — новый упрощённый приоритет (раздел 3.7.1):
```
1. day_type == "rest"                       → Rest
2. pain == 3                                → Recovery
3. pain == 2                                → Light
4. wellbeing == 1                           → Light
5. sleep == 1 ИЛИ stress == 3              → Light
6. вчера pain ≥ 2, сегодня pain == 1        → Light (1 день)
7. иначе                                    → Base
```
Убрать: cumulative_fatigue, severe_fatigue, detect_persistent_pain, «плохо + стресс → recovery».

**`fatigue.py`** — файл удаляем. Все импорты заменяем.

**`red_flags.py`** — переписываем:
```python
def detect_high_pain_streak(recent_logs, days=3) -> bool  # 3 дня pain==3 → red flag
def detect_mild_pain_streak(recent_logs, days=3) -> bool  # 3 дня pain==2 → блок роста
```
NULL (нет чек-ина) — сбрасывает счётчик.

---

### ШАГ 6 — Сервисы

**`services/week_plan_service.py`** (НОВЫЙ):
```python
class WeekPlanService:
    get_current(user_id) -> WeekPlan | None
    get_last(user_id) -> WeekPlan | None
    get_last_successful(user_id) -> WeekPlan | None
    create_for_next_week(user, decision) -> WeekPlan
    close_week(week_plan, evaluation) -> None
    get_logs_for_week_plan(week_plan_id) -> list[SessionLog]
```

**`services/user_service.py`** — обновление:
- Удалить: `current_calendar_day`, `current_template_day`, `current_program_day`,
  `_max_day`, `current_week_range`, `log_calendar_day`  
  → Оставить как deprecated (нужны для старых пользователей!)
- Добавить: `current_week_plan(user)`, `current_day_in_week(user) -> int`
- Обновить `reset_progress`: чистить WeekPlan + DayPlan тоже

**`services/session_log_service.py`** — обновление:
- Добавить: `completion_rate_for_week_plan(week_plan_id) -> float`
- Добавить: `get_logs_for_week_plan(week_plan_id) -> list[SessionLog]`
- `get_recent()` — переписать без импорта fatigue.py
- `week_completion_rate` — оставить для старой логики (deprecated)

---

### ШАГ 7 — Хэндлеры

**`handlers/onboarding.py`**:
- Новые состояния `OnboardingStates`:
  - `q_continuous_run_test` — после `q_longest_run` (ТОЛЬКО для L1 после предварит. уровня)
  - `q_available_days` — после `q_strength_frequency` (мультивыбор дней, минимум по уровню)
- L4 пропускает `q_available_days` (manual режим)
- Валидация: L3 regular ≥ 5 дней, L3 after break ≥ 4, L1/L2 ≥ 3
- После одобрения тренером → создать первый `WeekPlan` немедленно
- Расширить `engine/level_assignment.py`:
  - `assign_entry_point(level, answers) -> str`
  - `assign_starting_volume(level, entry_point) -> int`
  - `detect_level3_after_break(level, answers) -> bool`
  - `assign_initial_period(level, entry_point) -> str`
  - `route_to_program(level) -> "new" | "manual"`

**`handlers/checkin.py`**:
- В `_finish_checkin`: читать `day_type` из `DayPlan` (WeekPlan), не из старой `Workout`
- Использовать новый `engine/rule_engine.py`
- Использовать `engine/workout_renderer.py` для текста
- Re-checkin flow: перезаписать поля, сбросить override, approval_pending=True снова
- Manual-режим (L4): чек-ин сохраняет ответы, но `decide_workout_version` не вызывается

**`handlers/workout.py`**:
- Убрать кнопку `partial` из `kb_completion()`
- Допустимые значения completion_status: только `done` / `skipped`

**`handlers/admin.py`**:
- Добавить кнопку «Снять red flag» (обнуляет `red_flag_active`)
- Показывать текущий `WeekPlan` пользователя в карточке
- Coach override flow: кнопки Одобрить / Изменить версию / Кастомный текст / Изменить минуты
- Предупреждение при снятии red flag после 23:55 воскресенья (план уже создан)
- Таймлайн: T+0..10 мин тренер правит, T>10 мин кнопки скрываются

---

### ШАГ 8 — scheduler/tasks.py

**`_create_daily_logs`** — переделать:
- Брать `day_of_week` из текущего `WeekPlan` пользователя
- Если нет `WeekPlan` на эту неделю — создать (первая неделя или ошибка)
- Для manual-пользователей (L4/L5): создавать пустой `SessionLog` без WeekPlan
- Убрать логику `status="completed"` (программа теперь циклическая)
- Старые пользователи (без `current_period`): оставить старую логику

**`_check_week_completion`** — переписать полностью:
```python
# Воскресенье 23:55 UTC
for user in active_users:
    if not user.current_period: continue  # старый пользователь — пропускаем
    if user.level in (4, 5): continue     # manual — пропускаем

    current_week_plan = await week_plan_svc.get_current(user.id)
    if not is_week_ending_today(current_week_plan): continue

    logs = await log_svc.get_logs_for_week_plan(current_week_plan.id)
    evaluation = evaluate_week(current_week_plan, logs)
    await week_plan_svc.close_week(current_week_plan, evaluation)

    if evaluation.triggers_rollback:
        await activate_red_flag(user, evaluation)

    decision = decide_next_week(user, current_week_plan, evaluation)

    new_period = check_period_transition(user, recent_weeks)
    if new_period:
        await transition_period(user, new_period)

    if check_cycle_end(user, evaluation):
        await prompt_user_for_next_cycle_choice(user)
        continue

    if user.level == 1 and not user.l1_long_independent:
        if check_l1_long_stage_transition(user, recent_weeks):
            await user_svc.update(user, l1_long_independent=True)

    if user.injury_return_active:
        if check_injury_return_exit(user, recent_weeks):
            await exit_injury_return(user)

    await week_plan_svc.create_for_next_week(user, decision)
```

**Cron-расписание** — без изменений (`* * * * *` × 3, `0 5 *`, `55 23 *`).

---

### ШАГ 9 — scripts/migrate_workouts_to_templates.py

- Читает `data/workouts.json` (546 строк)
- Группирует по `(level, day_type, run_subtype, version, strength_format)`
- Создаёт записи `WorkoutTemplate` без привязки к day 1-28
- Числа минут → плейсхолдеры `{minutes}` в тексте
- Тексты упражнений сохраняются 1-в-1

---

### ШАГ 10 — Тесты

Файлы в `tests/`:

| Файл | Что тестируем |
|---|---|
| `test_week_planner.py` | Раскладка дней, long последний, силовая не перед long |
| `test_rule_engine.py` | Приоритеты версий (новая логика, без fatigue) |
| `test_week_evaluator.py` | 7 условий успешной недели, triggers_rollback |
| `test_progression.py` | +10%, разгрузка ×0.6, потолки L1=240, L2=300, L3_regular=600, L3_return=420 |
| `test_rollback.py` | red_flag, откат, снятие флага |
| `test_period_transitions.py` | Переходы периодов, конец цикла |
| `test_long_calculations.py` | Расчёт long (стадии L1, L2, L3) |
| `test_recheckin.py` | Re-checkin до/после completion_status |
| `test_no_checkin_days.py` | Дни без чек-ина и pain streak |
| `test_recovery_period_safety.py` | recovery_period: нет роста, red_flag детектится |
| `test_manual_mode.py` | L4/L5 → manual mode |
| `test_available_days_change.py` | Смена дней в середине цикла |
| `test_intensity_rules.py` | Tempo/intervals: когда запрещено, когда разрешено |

---

## КЛЮЧЕВЫЕ РЕШЕНИЯ / ДОГОВОРЁННОСТИ

| Вопрос | Решение |
|---|---|
| DB-миграция | **Alembic** — данные не теряются |
| Старые пользователи | Старая 28-дн. логика продолжает работать (пользователь без `current_period`) |
| L3 regular ceiling | 600 мин/нед |
| L3 after break ceiling | 420 мин/нед |
| Тест 5.4 "L3 — 420" | Это L3 after break, тест разбивается на два сценария |
| `q_continuous_run_test` | Только для L1, после определения предварительного уровня |
| L3 regular min дней | 5; L3 after break — 4 |
| Первый WeekPlan | Создаётся сразу после одобрения тренером (не ждёт воскресенья) |
| L2 after break | Облегчённая логика L1 base (run-walk, +10%, без интенсивности) |
| Long L3 regular | base period ≤ 35%, preparatory ≤ 40% недельного объёма |
| `weeks_until_recovery_period` | Считается из period + period_week_number + min_weeks константы |
| L4→L3 кнопка | Откладываем на следующий этап |
| `absence_reason` | Реализуем (поля в SessionLog уже частично есть в handlers) |
| `partial` статус | Удаляем из UI / новых записей; старые данные не трогаем |
| WorkoutTemplate | Скрипт миграции из workouts.json с плейсхолдерами {minutes} |

---

## ПОРЯДОК ВЫПОЛНЕНИЯ ВНУТРИ СЕССИИ

```
[0]  ✅ Alembic setup
[1]  ✅ models.py → новые поля + таблицы → alembic revision
[2]  ✅ engine/constants.py
[3]  ✅ engine/level_assignment.py (расширение)
[4]  ✅ engine/rule_engine.py (переписать)
[5]  ✅ engine/red_flags.py (переписать)
[6]  ✅ engine/fatigue.py → deprecated-заглушка (импорты совместимы)
[7]  ✅ engine/week_planner.py (новый)
[8]  ✅ engine/workout_renderer.py (новый)
[9]  ✅ engine/week_evaluator.py (новый)
[10] ✅ engine/period_transitions.py (новый)
[11] ✅ services/week_plan_service.py (новый)
[12] ✅ services/user_service.py (обновить)
[13] ✅ services/session_log_service.py (обновить)
[14] ✅ handlers/onboarding.py (новые шаги)
[15] ✅ handlers/checkin.py (WeekPlan логика)
[16] ✅ handlers/workout.py (убрать partial)
[17] ✅ handlers/admin.py (red flag кнопка + coach override)
[18] ✅ scheduler/tasks.py (переписать)
[19] ✅ scripts/migrate_workouts_to_templates.py (новый)
[20] ✅ tests/ (все файлы из ШАГ 10) — 312 passed, 0 failed
```

---

**КОНЕЦ ПЛАНА**
