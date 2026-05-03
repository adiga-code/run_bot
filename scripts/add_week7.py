"""Script to add week 7 (days 43-49) workouts to workouts.json."""
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


WEEK7_TEMPLATE = [
    # Day 43 — recovery
    {"day": 43, "day_type": "recovery", "version": "base",     "title": "Восстановление", "text": "Прогулка 25–35 мин", "micro_learning": "💬 Снимаем накопленную нагрузку\n🤍 Тело должно «выдохнуть»"},
    {"day": 43, "day_type": "recovery", "version": "light",    "title": "Восстановление", "text": "Прогулка 20 мин",     "micro_learning": "💬 Снимаем накопленную нагрузку\n🤍 Тело должно «выдохнуть»"},
    {"day": 43, "day_type": "recovery", "version": "recovery", "title": "Отдых",           "text": "Отдых",              "micro_learning": None},
    # Day 44 — strength
    {"day": 44, "day_type": "strength", "version": "base",     "title": "Силовая 1", "text": None,    "micro_learning": "💬 Возвращаем силу спокойно\n🤍 Без спешки"},
    {"day": 44, "day_type": "strength", "version": "light",    "title": "Силовая 1", "text": None,    "micro_learning": "💬 Возвращаем силу спокойно\n🤍 Без спешки"},
    {"day": 44, "day_type": "strength", "version": "recovery", "title": "Отдых",     "text": "Отдых", "micro_learning": None},
    # Day 45 — run (intervals)
    {"day": 45, "day_type": "run", "version": "base",     "title": "Интервальный бег", "text": "3–5 мин быстрая ходьба\n10 мин бег / 2 мин шаг × 2 (24 мин)\nПульс: ~125–140", "micro_learning": "💬 Лёгкий бег после силовой\n🤍 Мягко включаемся"},
    {"day": 45, "day_type": "run", "version": "light",    "title": "Интервальный бег", "text": "3–5 мин быстрая ходьба\n8 мин бег / 2 мин шаг × 2\nПульс: ~125–140",            "micro_learning": "💬 Лёгкий бег после силовой\n🤍 Мягко включаемся"},
    {"day": 45, "day_type": "run", "version": "recovery", "title": "Прогулка",          "text": "Прогулка 20–25 мин",                                                             "micro_learning": None},
    # Day 46 — recovery
    {"day": 46, "day_type": "recovery", "version": "base",     "title": "Восстановление", "text": "Прогулка 25–30 мин", "micro_learning": "💬 Переварить нагрузку — задача дня\n🤍 Это тоже часть прогресса"},
    {"day": 46, "day_type": "recovery", "version": "light",    "title": "Восстановление", "text": "Прогулка 15–20 мин", "micro_learning": "💬 Переварить нагрузку — задача дня\n🤍 Это тоже часть прогресса"},
    {"day": 46, "day_type": "recovery", "version": "recovery", "title": "Отдых",           "text": "Отдых",              "micro_learning": None},
    # Day 47 — run (continuous)
    {"day": 47, "day_type": "run", "version": "base",     "title": "Непрерывный бег", "text": "3–5 мин быстрая ходьба\nЛёгкий непрерывный бег 25–28 мин\nПульс: ~125–140", "micro_learning": "💬 Чуть длиннее непрерывный бег\n🤍 Всё ещё легко"},
    {"day": 47, "day_type": "run", "version": "light",    "title": "Непрерывный бег", "text": "3–5 мин быстрая ходьба\n18–22 мин лёгкий бег\nПульс: ~125–140",               "micro_learning": "💬 Чуть длиннее непрерывный бег\n🤍 Всё ещё легко"},
    {"day": 47, "day_type": "run", "version": "recovery", "title": "Прогулка",          "text": "Прогулка 20–30 мин",                                                           "micro_learning": None},
    # Day 48 — rest
    {"day": 48, "day_type": "rest", "version": "base",     "title": "Отдых", "text": "Отдых", "micro_learning": "💬 Полная пауза перед лонгом\n🤍 Восстановись заранее"},
    {"day": 48, "day_type": "rest", "version": "light",    "title": "Отдых", "text": "Отдых", "micro_learning": "💬 Полная пауза перед лонгом\n🤍 Восстановись заранее"},
    {"day": 48, "day_type": "rest", "version": "recovery", "title": "Отдых", "text": "Отдых", "micro_learning": None},
    # Day 49 — long run
    {"day": 49, "day_type": "run", "version": "base",     "title": "Длинный бег", "text": "3–5 мин быстрая ходьба\nЛёгкий непрерывный бег 32–36 мин\nПульс: ~125–140", "micro_learning": "💬 Длинный, но спокойный бег\n🤍 Дыши ровно, не спеши"},
    {"day": 49, "day_type": "run", "version": "light",    "title": "Длинный бег", "text": "3–5 мин быстрая ходьба\n24–28 мин лёгкий бег\nПульс: ~125–140",              "micro_learning": "💬 Длинный, но спокойный бег\n🤍 Дыши ровно, не спеши"},
    {"day": 49, "day_type": "run", "version": "recovery", "title": "Прогулка",     "text": "Прогулка 30–40 мин",                                                          "micro_learning": None},
]

existing_days = {w["day"] for w in data}
if any(d in existing_days for d in range(43, 50)):
    print("Days 43-49 already exist — skipping.")
else:
    new_entries = []
    for level in range(1, 6):
        s1_base  = get_text(level, 1,  "base")
        s1_light = get_text(level, 1,  "light")

        for entry in WEEK7_TEMPLATE:
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
    print(f"Added {len(new_entries)} entries (days 43-49, levels 1-5).")
    print(f"Total entries now: {len(data)}")
