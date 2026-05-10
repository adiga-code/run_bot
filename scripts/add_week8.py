"""Script to add week 8 (days 50-56) workouts to workouts.json."""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
JSON_PATH = ROOT / "data" / "workouts.json"

with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)


def get_text(level: int, day: int, version: str) -> str:
    for w in data:
        if w["day"] == day and w["level"] == level and w["version"] == version:
            return w["text"]
    return ""


WEEK8_TEMPLATE = [
    # Day 50 — recovery (after long run)
    {"day": 50, "day_type": "recovery", "version": "base",     "title": "Восстановление", "text": "Прогулка 30–40 мин",  "micro_learning": "💬 После лонга телу нужен спокойный день\n🤍 Восстановление делает тебя сильнее"},
    {"day": 50, "day_type": "recovery", "version": "light",    "title": "Восстановление", "text": "Прогулка 20–25 мин", "micro_learning": "💬 После лонга телу нужен спокойный день\n🤍 Восстановление делает тебя сильнее"},
    {"day": 50, "day_type": "recovery", "version": "recovery", "title": "Отдых",           "text": "Отдых",             "micro_learning": None},
    # Day 51 — strength
    {"day": 51, "day_type": "strength", "version": "base",     "title": "Силовая 1", "text": None,    "micro_learning": "💬 Возвращаем стабильность и контроль\n🤍 Работаем аккуратно"},
    {"day": 51, "day_type": "strength", "version": "light",    "title": "Силовая 1", "text": None,    "micro_learning": "💬 Возвращаем стабильность и контроль\n🤍 Работаем аккуратно"},
    {"day": 51, "day_type": "strength", "version": "recovery", "title": "Отдых",     "text": "Отдых", "micro_learning": None},
    # Day 52 — run (intervals)
    {"day": 52, "day_type": "run", "version": "base",     "title": "Интервальный бег", "text": "3–5 мин быстрая ходьба\n12 мин бег / 2 мин шаг × 2 (28 мин)\nПульс: ~125–140", "micro_learning": "💬 Немного увеличиваем рабочие интервалы\n🤍 Темп всё ещё очень лёгкий"},
    {"day": 52, "day_type": "run", "version": "light",    "title": "Интервальный бег", "text": "3–5 мин быстрая ходьба\n10 мин бег / 2 мин шаг × 2\nПульс: ~125–140",              "micro_learning": "💬 Немного увеличиваем рабочие интервалы\n🤍 Темп всё ещё очень лёгкий"},
    {"day": 52, "day_type": "run", "version": "recovery", "title": "Прогулка",          "text": "Прогулка 20–30 мин",                                                               "micro_learning": None},
    # Day 53 — recovery
    {"day": 53, "day_type": "recovery", "version": "base",     "title": "Восстановление", "text": "Прогулка 25–35 мин", "micro_learning": "💬 Даём организму адаптироваться\n🤍 Сейчас важна устойчивость"},
    {"day": 53, "day_type": "recovery", "version": "light",    "title": "Восстановление", "text": "Прогулка 20 мин",     "micro_learning": "💬 Даём организму адаптироваться\n🤍 Сейчас важна устойчивость"},
    {"day": 53, "day_type": "recovery", "version": "recovery", "title": "Отдых",           "text": "Отдых",             "micro_learning": None},
    # Day 54 — run (continuous)
    {"day": 54, "day_type": "run", "version": "base",     "title": "Непрерывный бег", "text": "3–5 мин быстрая ходьба\nЛёгкий непрерывный бег 28–32 мин\nПульс: ~125–140", "micro_learning": "💬 Спокойный непрерывный бег становится привычнее\n🤍 Беги расслабленно"},
    {"day": 54, "day_type": "run", "version": "light",    "title": "Непрерывный бег", "text": "3–5 мин быстрая ходьба\n22–25 мин лёгкий бег\nПульс: ~125–140",                "micro_learning": "💬 Спокойный непрерывный бег становится привычнее\n🤍 Беги расслабленно"},
    {"day": 54, "day_type": "run", "version": "recovery", "title": "Прогулка",          "text": "Прогулка 20–30 мин",                                                            "micro_learning": None},
    # Day 55 — rest
    {"day": 55, "day_type": "rest", "version": "base",     "title": "Отдых", "text": "Отдых", "micro_learning": "💬 Полностью отпускаем нагрузку\n🤍 Накопленная усталость должна уйти"},
    {"day": 55, "day_type": "rest", "version": "light",    "title": "Отдых", "text": "Отдых", "micro_learning": "💬 Полностью отпускаем нагрузку\n🤍 Накопленная усталость должна уйти"},
    {"day": 55, "day_type": "rest", "version": "recovery", "title": "Отдых", "text": "Отдых", "micro_learning": None},
    # Day 56 — long run
    {"day": 56, "day_type": "run", "version": "base",     "title": "Длинный бег", "text": "3–5 мин быстрая ходьба\nЛёгкий непрерывный бег 36–40 мин\nПульс: ~125–145", "micro_learning": "💬 Длинный лёгкий бег — уже новая база\n🤍 Сохраняй ощущение запаса сил"},
    {"day": 56, "day_type": "run", "version": "light",    "title": "Длинный бег", "text": "3–5 мин быстрая ходьба\n28–32 мин лёгкий бег\nПульс: ~125–140",               "micro_learning": "💬 Длинный лёгкий бег — уже новая база\n🤍 Сохраняй ощущение запаса сил"},
    {"day": 56, "day_type": "run", "version": "recovery", "title": "Прогулка",     "text": "Прогулка 35–45 мин",                                                           "micro_learning": None},
]

existing_days = {w["day"] for w in data}
if any(d in existing_days for d in range(50, 57)):
    print("Days 50-56 already exist — skipping.")
else:
    new_entries = []
    for level in range(1, 6):
        s1_base  = get_text(level, 1,  "base")
        s1_light = get_text(level, 1,  "light")

        for entry in WEEK8_TEMPLATE:
            text = entry["text"]
            if entry["day_type"] == "strength" and entry["version"] != "recovery":
                text = s1_base if entry["version"] == "base" else s1_light

            new_entries.append({
                "level": level,
                "day": entry["day"],
                "day_type": entry["day_type"],
                "version": entry["version"],
                "title": entry["title"],
                "short_title": None,
                "text": text,
                "micro_learning": entry["micro_learning"],
                "video_url": None,
                "media_id": None,
            })

    data.extend(new_entries)
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Added {len(new_entries)} entries (days 50-56, levels 1-5).")
    print(f"Total entries now: {len(data)}")
