"""Script to add week 5 (days 29-35) workouts to workouts.json."""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
JSON_PATH = ROOT / "data" / "workouts.json"

with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)


def get_text(day: int, version: str) -> str:
    for w in data:
        if w["day"] == day and w["level"] == 1 and w["version"] == version:
            return w["text"]
    return ""


s1_base  = get_text(1, "base")
s1_light = get_text(1, "light")
s2_base  = get_text(11, "base")
s2_light = get_text(11, "light")

WEEK5_TEMPLATE = [
    # Day 29 — strength
    {"day": 29, "day_type": "strength", "version": "base",     "title": "Силовая 1", "text": s1_base,  "micro_learning": "💬 Входим в неделю спокойно, без давления\n🤍 Стабильность важнее усилия"},
    {"day": 29, "day_type": "strength", "version": "light",    "title": "Силовая 1", "text": s1_light, "micro_learning": "💬 Входим в неделю спокойно, без давления\n🤍 Стабильность важнее усилия"},
    {"day": 29, "day_type": "strength", "version": "recovery", "title": "Отдых",     "text": "Отдых",  "micro_learning": None},
    # Day 30 — run (intervals)
    {"day": 30, "day_type": "run", "version": "base",     "title": "Интервальный бег", "text": "3–5 мин быстрая ходьба\n6 мин очень лёгкий бег / 2 мин шаг × 3 (24 мин)\nПульс: ~125–140", "micro_learning": "💬 Возвращаем интервалы, чтобы разгрузить тело\n🤍 Контроль важнее дистанции"},
    {"day": 30, "day_type": "run", "version": "light",    "title": "Интервальный бег", "text": "3–5 мин быстрая ходьба\n5 мин очень лёгкий бег / 2 мин шаг × 3\nПульс: ~125–140",           "micro_learning": "💬 Возвращаем интервалы, чтобы разгрузить тело\n🤍 Контроль важнее дистанции"},
    {"day": 30, "day_type": "run", "version": "recovery", "title": "Прогулка",          "text": "Прогулка 20–25 мин",                                                                          "micro_learning": None},
    # Day 31 — recovery
    {"day": 31, "day_type": "recovery", "version": "base",     "title": "Восстановление", "text": "Прогулка 25–30 мин", "micro_learning": "💬 Лёгкое движение — это тоже тренировка\n🤍 Дай телу переварить нагрузку"},
    {"day": 31, "day_type": "recovery", "version": "light",    "title": "Восстановление", "text": "Прогулка 15–20 мин", "micro_learning": "💬 Лёгкое движение — это тоже тренировка\n🤍 Дай телу переварить нагрузку"},
    {"day": 31, "day_type": "recovery", "version": "recovery", "title": "Отдых",           "text": "Отдых",              "micro_learning": None},
    # Day 32 — run (continuous)
    {"day": 32, "day_type": "run", "version": "base",     "title": "Непрерывный бег", "text": "3–5 мин быстрая ходьба\nЛёгкий непрерывный бег 18–20 мин\nПульс: ~125–140", "micro_learning": "💬 Чуть длиннее непрерывный бег, но без усилия\n🤍 Беги так, чтобы хотелось ещё"},
    {"day": 32, "day_type": "run", "version": "light",    "title": "Непрерывный бег", "text": "3–5 мин быстрая ходьба\nЛёгкий непрерывный бег 12–15 мин\nПульс: ~125–140", "micro_learning": "💬 Чуть длиннее непрерывный бег, но без усилия\n🤍 Беги так, чтобы хотелось ещё"},
    {"day": 32, "day_type": "run", "version": "recovery", "title": "Прогулка",          "text": "Прогулка 20–30 мин",                                                         "micro_learning": None},
    # Day 33 — rest
    {"day": 33, "day_type": "rest", "version": "base",     "title": "Отдых", "text": "Отдых", "micro_learning": "💬 Полная пауза — часть прогресса\n🤍 Ты уже сделал достаточно"},
    {"day": 33, "day_type": "rest", "version": "light",    "title": "Отдых", "text": "Отдых", "micro_learning": "💬 Полная пауза — часть прогресса\n🤍 Ты уже сделал достаточно"},
    {"day": 33, "day_type": "rest", "version": "recovery", "title": "Отдых", "text": "Отдых", "micro_learning": None},
    # Day 34 — strength
    {"day": 34, "day_type": "strength", "version": "base",     "title": "Силовая 2", "text": s2_base,  "micro_learning": "💬 Аккуратно возвращаем силу\n🤍 Качество важнее количества"},
    {"day": 34, "day_type": "strength", "version": "light",    "title": "Силовая 2", "text": s2_light, "micro_learning": "💬 Аккуратно возвращаем силу\n🤍 Качество важнее количества"},
    {"day": 34, "day_type": "strength", "version": "recovery", "title": "Отдых",     "text": "Отдых",  "micro_learning": None},
    # Day 35 — recovery
    {"day": 35, "day_type": "recovery", "version": "base",     "title": "Восстановление", "text": "Прогулка 25–35 мин", "micro_learning": "💬 Завершаем неделю мягко\n🤍 Пусть тело скажет «спасибо»"},
    {"day": 35, "day_type": "recovery", "version": "light",    "title": "Восстановление", "text": "Прогулка 20 мин",    "micro_learning": "💬 Завершаем неделю мягко\n🤍 Пусть тело скажет «спасибо»"},
    {"day": 35, "day_type": "recovery", "version": "recovery", "title": "Отдых",           "text": "Отдых",              "micro_learning": None},
]

existing_days = {w["day"] for w in data}
if any(d in existing_days for d in range(29, 36)):
    print("Days 29-35 already exist — skipping.")
else:
    new_entries = []
    for level in range(1, 6):
        for entry in WEEK5_TEMPLATE:
            new_entries.append({
                "level": level,
                "day": entry["day"],
                "day_type": entry["day_type"],
                "version": entry["version"],
                "title": entry["title"],
                "short_title": None,
                "text": entry["text"],
                "micro_learning": entry["micro_learning"],
                "video_url": None,
                "media_id": None,
            })

    data.extend(new_entries)
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Added {len(new_entries)} entries (days 29-35, levels 1-5).")
    print(f"Total entries now: {len(data)}")
