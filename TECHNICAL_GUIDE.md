# Технический гайд: новая цикловая система бегового бота

> Актуально для кодовой базы после MASTER_SPEC v1.0  
> 393 теста, 0 failed

---

## 1. Архитектура: две системы в одном боте

### Как определить, в какой системе пользователь

```python
if user.current_period is not None:
    # НОВАЯ цикловая система (L1–L3)
else:
    # СТАРАЯ 28-дневная система (L4–L5 или старые пользователи)
```

Эта проверка делается в каждом хэндлере:  
`handlers/checkin.py`, `handlers/progress.py`, `handlers/admin.py`, `scheduler/tasks.py`.

Старые пользователи продолжают работать **без изменений**. Новая система включается только при `user.current_period is not None`.

---

## 2. Поток жизни пользователя в новой системе

```
Онбординг
    → assign_level()         → уровень 1–4
    → route_to_program()     → "new" (L1–L3) или "manual" (L4–L5)
    → assign_entry_point()   → "base_in" или "base"
    → assign_initial_period()→ первый период
    → assign_starting_volume()→ стартовый объём мин/нед
    → тренер одобряет
    → create_first_week()    → первый WeekPlan + 7 DayPlan

Каждое утро (чекин)
    → пользователь отвечает на 4 вопроса
    → decide_workout_version() → версия тренировки
    → тренер одобряет
    → пользователь получает тренировку

Каждое воскресенье 23:55 UTC (scheduler)
    → evaluate_week()        → оценка недели
    → decide_next_week()     → следующий объём
    → check_period_transition()→ смена периода?
    → check_cycle_end()      → конец цикла?
    → create_for_next_week() → новый WeekPlan
```

---

## 3. Модели данных (новые таблицы)

### User — ключевые новые поля

```python
# Состояние программы
current_period: str | None      # "base_in"/"base"/"preparatory"/"specialized"/"recovery_period"
period_start_date: date | None
period_week_number: int         # неделя внутри текущего периода
program_week_number: int        # неделя от начала программы
cycle_number: int               # номер макроцикла

# Объёмы
weekly_target_minutes: int      # цель текущей недели
peak_volume_minutes: int        # пик в текущем 3-недельном блоке
last_successful_volume: int     # объём последней успешной недели
macrocycle_peak_volume: int     # пик всего макроцикла (для recovery_period)

# Прогрессия
growth_streak: int              # успешных недель подряд
weeks_since_recovery: int       # недель с последней разгрузки

# Флаги
red_flag_active: bool
red_flag_reason: str | None
has_goal_race: bool
injury_return_active: bool      # пользователь в return-mode (после перерыва)

# L1 long
l1_long_independent: bool       # перешёл на стадию 2 длинного бега
l1_easy_reached_40min: bool
```

### WeekPlan — план недели

```python
id, user_id, week_number, cycle_number
period                   # к какому периоду относится
period_week_number
start_date, end_date     # Пн–Вс
weekly_target_minutes
is_recovery_week: bool   # разгрузочная неделя (×0.6)
is_rollback_week: bool   # неделя после red flag

# Закрытие (воскресенье)
actual_running_minutes
completion_rate          # 0.0–1.0
keys_completed: bool
growth_eligible: bool
no_growth_reason: str | None
closed_at: datetime | None

# ORM-связь
days: list[DayPlan]      # через relationship
```

### DayPlan — план конкретного дня

```python
id, week_plan_id
day_of_week              # 1=Пн..7=Вс
day_type                 # "run"/"strength"/"recovery"/"rest"/"mobility"
run_subtype              # "easy"/"aerobic"/"recovery_run"/"long"/"tempo"/"intervals"/"run_walk"
planned_minutes          # сколько минут
intensity                # None/"z3_inclusions"/"tempo"/"intervals"
is_key: bool             # ключевая тренировка
```

### SessionLog — обновлённые поля

```python
# Связь с новой системой
week_plan_id: int | None
day_plan_id: int | None
day_of_week: int | None
planned_minutes: int | None

# Чекин
wellbeing, sleep_quality, pain_level, stress_level  # 1–3
checkin_done: bool
assigned_version: str | None  # "base"/"light"/"recovery"/"rest"

# Ре-чекин
recheckin_count: int
last_checkin_at: datetime | None
```

---

## 4. Принятие решения о тренировке (rule_engine.py)

```
Приоритет (сверху вниз):

1. day_type == "rest"                         → version="rest"
2. pain_level == 3                            → version="recovery"
3. pain_level == 2                            → version="light"
4. wellbeing == 1                             → version="light"
5. sleep_quality == 1 ИЛИ stress_level == 3  → version="light"
6. вчера pain_level >= 2, сегодня pain == 1  → version="light"
7. всё остальное                              → version="base"
```

**Код:**
```python
from engine.rule_engine import CheckinData, RecentDayData, decide_workout_version

checkin = CheckinData(wellbeing=2, sleep_quality=3, pain_level=1, stress_level=1)
yesterday = RecentDayData(pain_level=1)
decision = decide_workout_version(checkin, day_type="run", yesterday=yesterday)
# decision.version → "base"
# decision.reason  → "all_ok"
```

---

## 5. Построение недельного плана (week_planner.py)

### Правила раскладки дней

- **Long** — всегда последний из беговых дней
- **Силовая** — не стоит день-перед-long
- **Силовая** — не стоит перед tempo/intervals
- **Между беговыми** — минимум 1 день без бега (L1/L2)
- **L3 regular** — можно совмещать силовую с лёгким бегом в один день

### Количество беговых дней по уровням

| Уровень | Беговых дней |
|---------|-------------|
| L1 | min(n_доступных, 3) |
| L2 / L3 return | min(n_доступных − 1, 4) |
| L3 regular | min(n_доступных − 2, 5) |

### Распределение минут

```python
from engine.week_planner import split_running_minutes

mins = split_running_minutes(
    weekly_target=200,
    level=2,
    period="base",
    injury_return=False,
    n_run_days=4,
    is_long_independent=False,
    is_recovery_week=False,
)
# → {"long": 70, "easy": 43, "aerobic": 50, "recovery_run": 40}
# Каждое значение — минуты НА ОДНУ тренировку, не суммарно!
```

### Создание плана

```python
from engine.week_planner import build_week_plan, parse_available_weekdays

blueprint = build_week_plan(
    user=user,
    week_number=3,
    period="base",
    target_minutes=200,
    is_recovery_week=False,
    available_weekdays=[1, 3, 5, 7],  # Пн, Ср, Пт, Вс
)
# blueprint.days → список DaySlot (day_of_week, day_type, run_subtype, planned_minutes, is_key)
```

---

## 6. Оценка недели (week_evaluator.py)

### 7 условий успешной недели

```
1. completion_rate >= 0.85            (≥85% тренировок выполнено)
2. keys_completed == True             (все ключевые тренировки сделаны)
3. high_pain_streak < 3              (нет 3 дней подряд с pain==3)
4. mild_pain_streak < 3              (нет 3 дней подряд с pain==2)
5. light_days <= 2                   (не более 2 дней light-версии)
6. recovery_days <= 1                (не более 1 дня recovery-версии)
7. no_checkin_streak < 3             (нет 3 дней подряд без чекина)
```

Любое нарушение → `growth_eligible = False`, `no_growth_reason = "..."`.

### Специальный случай: recovery_period

В `recovery_period` неделя **всегда** `growth_eligible = False` (независимо от выполнения),  
но `triggers_rollback` всё равно детектируется.

### Red flag (triggers_rollback)

Если `high_pain_streak >= 3` — три дня подряд `pain == 3`:
- `triggers_rollback = True`
- `user.red_flag_active = True`
- Следующая неделя — откат к `last_successful_volume`

**Важно:** `NULL` (день без чекина) **сбрасывает** счётчик боли.

```python
from engine.week_evaluator import evaluate_week

evaluation = evaluate_week(week_plan, logs)
# evaluation.growth_eligible   → True/False
# evaluation.triggers_rollback → True/False
# evaluation.actual_minutes    → сколько минут реально выполнено
```

---

## 7. Принятие решения по следующей неделе (week_evaluator.py)

### Логика объёма

```
Если red_flag → откат к last_successful_volume (или стартовый объём уровня)
Если recovery_period → macrocycle_peak_volume × 0.60
Если weekly unload нужен → peak × 0.60

Иначе:
  Если growth_eligible:
    L3 regular preparatory → × 1.15 (+15%)
    Всё остальное          → × 1.10 (+10%)
    Применить потолок уровня
  Иначе:
    Сохранить current_target (неделя не растёт)
```

### Когда нужна разгрузочная неделя (weekly unload)

```python
from engine.period_transitions import should_apply_weekly_unload

# Нужна разгрузка если:
# 1. growth_streak >= 3 (три успешных недели подряд)
# 2. weeks_since_recovery >= 6 (failsafe)
# НО: если до recovery_period <= 2 недели — НЕ делаем (двойной отдых не нужен)
result = should_apply_weekly_unload(user, weeks_until_recovery_period=5)
```

### Потолки по уровням

| Уровень | Потолок |
|---------|---------|
| L1 | 240 мин/нед |
| L2 | 300 мин/нед |
| L3 after break | 420 мин/нед |
| L3 regular | 600 мин/нед |

---

## 8. Переходы периодов (period_transitions.py)

### L1: base_in → base
```
Условия:
  • period_week_number >= 4  (≥4 недели в base_in)
  • avg_completion >= 0.85
  • user.q_continuous_run_test == "yes"  (может бежать 20 мин непрерывно)
  • нет active pain в последних 2 неделях
```

### L1: base → specialized
```
  • period_week_number >= 6
  • user.has_goal_race == True
  • avg_completion >= 0.85
  • нет active pain
```

### L2/L3: base → preparatory
```
  • period_week_number >= 6
  • avg_completion >= 0.85
  • нет active pain
```

### Конец цикла
```
check_cycle_end() возвращает True если:
  • program_week_number >= max_weeks для уровня
  • ИЛИ recovery_period завершён (период закрыт, min_weeks выполнены)
```

### Начало нового цикла
```python
from engine.period_transitions import start_new_cycle

# mode: "advance" → уровень +1 (L1→L2, L2→L3, L3 остаётся L3)
#       "stay"    → остаться, объём = peak × 1.4
#       "redo"    → провальный цикл, объём = peak × 0.6
start_new_cycle(user, mode="advance")
# Сбрасывает: growth_streak, weeks_since_recovery, macrocycle_peak_volume
# Применяет потолок нового уровня
```

---

## 9. Рендер тренировки (workout_renderer.py)

```python
from engine.workout_renderer import render_workout, render_rest_day, render_recovery_day

# Шаблон WorkoutTemplate содержит текст с плейсхолдерами {minutes}
rendered = render_workout(
    template=template,
    target_minutes=55,
    version="base",          # "base"/"light"/"recovery"
    intensity_kind="long",   # run_subtype
    long_stage=2,            # стадия L1 long
)
# rendered.title           → "Длинная пробежка"
# rendered.text            → финальный текст тренировки с подставленными минутами
# rendered.planned_minutes → 55 (или 44 для light: 55 × 0.80)
```

**Версии:**
- `base` → полный план, `{minutes}` → target_minutes
- `light` → `{minutes}` → target_minutes × 0.80, интервалы/темп заменяются на easy
- `recovery` → всегда «прогулка 20–30 мин, зона Z1»
- `rest` → «День отдыха»

---

## 10. Обнаружение боли (red_flags.py)

```python
from engine.red_flags import DayPainData, detect_high_pain_streak, detect_mild_pain_streak

logs = [DayPainData(pain_level=3), DayPainData(pain_level=3), DayPainData(pain_level=3)]
detect_high_pain_streak(logs)   # → True  (3 дня pain==3 → red flag)
detect_mild_pain_streak(logs)   # → False (это не pain==2)

logs2 = [DayPainData(pain_level=2), DayPainData(pain_level=None), DayPainData(pain_level=2)]
detect_mild_pain_streak(logs2)  # → False (None сбрасывает счётчик)
```

**NULL-правило:** `pain_level=None` (день без чекина) **всегда сбрасывает** счётчик.  
Это означает: пропуск дня не накапливает боль.

---

## 11. Как тестировать

### Запуск всех тестов

```bash
cd C:\Users\Hezh PC\Desktop\projects\фриланс_19_03
python -m pytest --tb=short -q
# 393 passed, 0 failed
```

### Запуск конкретного модуля

```bash
python -m pytest tests/test_engine/test_week_evaluator.py -v
python -m pytest tests/test_engine/test_progression.py -v
python -m pytest tests/test_services/test_recheckin.py -v
```

### Структура тестов

```
tests/
├── conftest.py                         ← фикстура session (async SQLite in-memory)
├── test_engine/
│   ├── test_rule_engine.py             ← 7 приоритетов, 22 теста
│   ├── test_red_flags.py               ← DayPainData, NULL-сброс, 31 тест
│   ├── test_fatigue.py                 ← старый detector (deprecated), 12 тестов
│   ├── test_level_assignment.py        ← scoring 1–4, hard stops, 26 тестов
│   ├── test_week_planner.py            ← раскладка дней, long последний, 41 тест
│   ├── test_week_evaluator.py          ← 7 условий успеха, rollback, 37 тестов
│   ├── test_progression.py             ← +10%/+15%, ×0.6, потолки, 20 тестов
│   ├── test_period_transitions.py      ← переходы периодов, цикл, 33 теста
│   ├── test_long_calculations.py       ← long-бег по уровням/стадиям, 22 теста
│   ├── test_intensity_rules.py         ← tempo/intervals когда запрещены, 28 тестов
│   ├── test_rollback.py                ← red flag, откат объёма, 13 тестов
│   ├── test_recovery_period_safety.py  ← recovery_period без роста, 12 тестов
│   ├── test_no_checkin_days.py         ← дни без чекина, NULL-сброс, 12 тестов
│   ├── test_manual_mode.py             ← L4/L5 routing, 18 тестов
│   └── test_available_days_change.py   ← parse_weekdays, смена дней, 22 теста
└── test_services/
    ├── test_session_log_service.py     ← streak, completed_count, get_recent
    ├── test_user_service.py
    ├── test_whitelist_service.py
    └── test_recheckin.py               ← ре-чекин, блокировка, 14 тестов
```

### Паттерн написания нового теста для движка

```python
# Чистые функции — тесты без DB
def test_rule_engine_pain3_gives_recovery():
    from engine.rule_engine import CheckinData, RecentDayData, decide_workout_version
    checkin = CheckinData(wellbeing=3, sleep_quality=3, pain_level=3, stress_level=1)
    decision = decide_workout_version(checkin, "run", RecentDayData(pain_level=1))
    assert decision.version == "recovery"
```

### Паттерн написания нового теста для сервисов

```python
# Сервисы требуют DB — используют фикстуру session из conftest.py
@pytest.mark.asyncio
async def test_something(session):
    user = await UserService(session).create(telegram_id=1001, full_name="Test")
    svc = SessionLogService(session)
    log, created = await svc.get_or_create_today(1001, day_index=3)
    assert created is True
```

### Conftest (как устроена тестовая БД)

```python
# tests/conftest.py
# - in-memory SQLite
# - создаёт все таблицы перед тестом
# - откатывает транзакцию после каждого теста (изоляция)
# - pytest-asyncio в режиме auto
```

---

## 12. Переход на новую систему: пошаговая инструкция

### Шаг 1 — Применить миграцию БД (если ещё не сделано)

```bash
# Из директории проекта
alembic upgrade head
```

Это создаёт таблицы `week_plans`, `day_plans`, `workout_templates` и добавляет ~25 полей в `users` и ~10 полей в `session_logs`.

**Существующие данные не трогаются.** Все старые пользователи продолжают работать.

### Шаг 2 — Загрузить WorkoutTemplate (если ещё не сделано)

```bash
python scripts/migrate_workouts_to_templates.py
```

Скрипт читает `data/workouts.json` (546 строк старых тренировок), конвертирует числа минут в плейсхолдеры `{minutes}` и создаёт записи `WorkoutTemplate`.

**Проверка:**
```bash
python -c "
import asyncio
from database.engine import get_async_session
from database.models import WorkoutTemplate
from sqlalchemy import select, func

async def check():
    async for session in get_async_session():
        r = await session.execute(select(func.count()).select_from(WorkoutTemplate))
        print('WorkoutTemplate count:', r.scalar_one())

asyncio.run(check())
"
```

### Шаг 3 — Активировать нового пользователя

Новый пользователь проходит онбординг → тренер видит карточку с кнопками «Активировать сегодня / завтра».

При активации через `adm:approve:today:<user_id>:<level>`:
1. `user.level` = выбранный уровень
2. `user.status = "active"`
3. `user.program_start_date = today`
4. Если `level <= 3` и `user.current_period is not None`:
   - Автоматически создаётся первый `WeekPlan` через `wk_plan_svc.create_first_week(user)`

**Ключевое поле для переключения:** `user.current_period`.  
Если оно `None` → старая система. Если не `None` → новая.

### Шаг 4 — Ручное переключение существующего пользователя на новую систему

```python
# Через сессию SQLAlchemy (например в скрипте или через /admin)
from services.user_service import UserService
from services.week_plan_service import WeekPlanService
from engine.level_assignment import assign_initial_period, assign_starting_volume

async def migrate_user_to_new_system(session, telegram_id: int, level: int):
    user_svc = UserService(session)
    user = await user_svc.get(telegram_id)

    entry_point = "base"  # или "base_in" для L1 без опыта
    initial_period = assign_initial_period(level, entry_point)
    start_volume = assign_starting_volume(level, entry_point)

    user = await user_svc.update(user,
        level=level,
        current_period=initial_period,
        period_week_number=1,
        program_week_number=1,
        cycle_number=1,
        weekly_target_minutes=start_volume,
        growth_streak=0,
        weeks_since_recovery=0,
        status="active",
    )

    wk_svc = WeekPlanService(session)
    await wk_svc.create_first_week(user)
```

### Шаг 5 — Что происходит каждую неделю автоматически

**Воскресенье 23:55 UTC** — `_check_week_new_system` в `scheduler/tasks.py`:

```
1. Берёт текущий WeekPlan для каждого активного пользователя (current_period != None)
2. Собирает все SessionLog за эту неделю
3. evaluate_week()         → оценивает 7 критериев
4. close_week()            → сохраняет результаты в WeekPlan
5. Если triggers_rollback  → red_flag_active = True, уведомляет тренера
6. decide_next_week()      → считает объём следующей недели
7. check_period_transition()→ переводит в следующий период (если пора)
8. check_cycle_end()       → если цикл кончился, спрашивает пользователя
9. create_for_next_week()  → создаёт новый WeekPlan + 7 DayPlan
```

**Понедельник 00:05 UTC** — `_create_daily_logs`:
```
Для новой системы: берёт DayPlan на сегодняшний день из текущего WeekPlan,
создаёт SessionLog(week_plan_id=..., day_plan_id=..., day_of_week=...).
```

### Шаг 6 — Проверить, что всё работает

```bash
# 1. Тесты
python -m pytest --tb=short -q

# 2. Импорт всех модулей (проверка ошибок)
python -c "
from engine.rule_engine import decide_workout_version
from engine.week_planner import build_week_plan
from engine.week_evaluator import evaluate_week, decide_next_week
from engine.period_transitions import check_period_transition, check_cycle_end
from engine.workout_renderer import render_workout
from services.week_plan_service import WeekPlanService
print('Все модули импортированы успешно')
"

# 3. Запустить бота и пройти онбординг тестового пользователя
```

---

## 13. Часто задаваемые вопросы

### Q: Как добавить нового пользователя сразу в новую систему?

Просто активируйте через обычную кнопку `/admin` → Pending. Для L1–L3 WeekPlan создаётся автоматически.

### Q: Как откатить конкретного пользователя к старой системе?

```python
await user_svc.update(user, current_period=None)
# Пользователь переходит на 28-дневную логику
# Все старые SessionLog остаются нетронутыми
```

### Q: Что будет если WeekPlan не создался?

В `_finish_checkin_new` есть ветка:
```python
if not week_plan or not day_plan:
    # Сохраняем чекин без тренировки
    await callback.message.answer(T.checkin.no_plan_yet, ...)
```
Пользователь получит сообщение, тренер увидит ситуацию и создаст план вручную.

### Q: Можно ли изменить доступные дни в середине цикла?

Да. Изменение `user.available_weekdays` применяется со **следующей** недели — текущий WeekPlan уже создан и хранится в БД. Следующий `create_for_next_week()` прочитает новые дни.

### Q: Как работает ре-чекин?

```
Условие блокировки (из handlers/checkin.py):
  if log.checkin_done and log.completion_status is not None:
      → заблокировано (тренировка уже отмечена)

  if log.checkin_done and log.completion_status is None:
      → разрешено (чекин можно переделать до отметки тренировки)
```
При ре-чекине `recheckin_count += 1`, данные перезаписываются, `approval_pending = True` снова.

### Q: Что такое growth_streak и когда он сбрасывается?

```
growth_streak += 1  когда growth_eligible == True (успешная неделя)
growth_streak = 0   когда growth_eligible == False (неуспешная неделя)
                    когда is_recovery_week == True (разгрузка)
```
При `growth_streak >= 3` следующая неделя становится разгрузочной (×0.60),  
`growth_streak` сбрасывается в 0 после разгрузки.

### Q: Чем отличается recovery_week от recovery_period?

| | recovery_week | recovery_period |
|---|---|---|
| Что | Одна разгрузочная неделя | Несколько недель в конце цикла |
| Когда | growth_streak==3 или failsafe | Конец макроцикла |
| Объём | peak × 0.60 | macrocycle_peak × 0.60 |
| Рост | Нет | Нет |
| Уровни | Все | Только L1 и L3 regular |
| WeekPlan.is_recovery_week | True | False (но period == "recovery_period") |

### Q: Что делает тренер при red flag?

1. Получает уведомление в боте
2. Идёт в `/admin` → управление пользователем
3. Видит «🚩 Red flag: три дня pain==3»
4. Связывается с пользователем
5. Нажимает «🚩 Снять red flag» когда ситуация разрешена
6. Следующая неделя автоматически откатывается к `last_successful_volume`

---

## 14. Ключевые числа (engine/constants.py)

| Константа | Значение | Смысл |
|-----------|----------|-------|
| `GROWTH_MULTIPLIER` | 1.10 | +10% при росте |
| `RECOVERY_MULTIPLIER` | 0.60 | разгрузка = −40% |
| `SUCCESS_THRESHOLD` | 0.85 | 85% выполнения → успех |
| `GROWTH_STREAK_FOR_RECOVERY` | 3 | 3 успешных недели → разгрузка |
| `FAILSAFE_WEEKS_WITHOUT_RECOVERY` | 6 | принудительная разгрузка |
| `MAX_LIGHT_DAYS_PER_WEEK` | 2 | ≥3 light → неуспешная неделя |
| `MAX_RECOVERY_DAYS_PER_WEEK` | 1 | ≥2 recovery → неуспешная неделя |
| `ROLLBACK_PAIN_DAYS` | 3 | 3 дня pain==3 → red flag |
| `L1_CEILING` | 240 | мин/нед потолок L1 |
| `L2_CEILING` | 300 | мин/нед потолок L2 |
| `L3_RETURN_CEILING` | 420 | мин/нед потолок L3 после перерыва |
| `L3_REGULAR_CEILING` | 600 | мин/нед потолок L3 regular |
| `L3_REGULAR_GROWTH_MULTIPLIERS["preparatory"]` | 1.15 | +15% для L3 в подготовительном |
| `CYCLE_END_STAY_VOLUME_MULTIPLIER` | 1.40 | остаться = peak × 1.4 |
| `CYCLE_END_REDO_VOLUME_MULTIPLIER` | 0.60 | переделать = peak × 0.6 |

Все числа можно менять **только в `engine/constants.py`**, не трогая логику.
