"""Script to add week 6 (days 36-42) workouts to workouts.json."""
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


WEEK6_TEMPLATE = [
    # Day 36 — strength 1
    {"day": 36, "day_type": "strength", "version": "base",     "title": "Силовая 1", "text": None,   "micro_learning": "💬 Спокойный вход в неделю\n🤍 Держим контроль"},
    {"day": 36, "day_type": "strength", "version": "light",    "title": "Силовая 1", "text": None,   "micro_learning": "💬 Спокойный вход в неделю\n🤍 Держим контроль"},
    {"day": 36, "day_type": "strength", "version": "recovery", "title": "Отдых",     "text": "Отдых", "micro_learning": None},
    # Day 37 — run (intervals)
    {"day": 37, "day_type": "run", "version": "base",     "title": "Интервальный бег", "text": "3–5 мин быстрая ходьба\n8 мин бег / 2 мин шаг × 3 (30 мин)\nПульс: ~125–140", "micro_learning": "💬 Интервалы для мягкой нагрузки\n🤍 Легко и ровно"},
    {"day": 37, "day_type": "run", "version": "light",    "title": "Интервальный бег", "text": "3–5 мин быстрая ходьба\n6 мин бег / 2 мин шаг × 3\nПульс: ~125–140",           "micro_learning": "💬 Интервалы для мягкой нагрузки\n🤍 Легко и ровно"},
    {"day": 37, "day_type": "run", "version": "recovery", "title": "Прогулка",          "text": "Прогулка 20–25 мин",                                                             "micro_learning": None},
    # Day 38 — recovery
    {"day": 38, "day_type": "recovery", "version": "base",     "title": "Восстановление", "text": "Прогулка 25–30 мин", "micro_learning": "💬 Даём телу адаптироваться\n🤍 Без давления"},
    {"day": 38, "day_type": "recovery", "version": "light",    "title": "Восстановление", "text": "Прогулка 15–20 мин", "micro_learning": "💬 Даём телу адаптироваться\n🤍 Без давления"},
    {"day": 38, "day_type": "recovery", "version": "recovery", "title": "Отдых",           "text": "Отдых",              "micro_learning": None},
    # Day 39 — run (continuous)
    {"day": 39, "day_type": "run", "version": "base",     "title": "Непрерывный бег", "text": "3–5 мин быстрая ходьба\nЛёгкий непрерывный бег 22–25 мин\nПульс: ~125–140", "micro_learning": "💬 Основной непрерывный бег\n🤍 Комфорт — главный ориентир"},
    {"day": 39, "day_type": "run", "version": "light",    "title": "Непрерывный бег", "text": "3–5 мин быстрая ходьба\n15–18 мин лёгкий бег\nПульс: ~125–140",               "micro_learning": "💬 Основной непрерывный бег\n🤍 Комфорт — главный ориентир"},
    {"day": 39, "day_type": "run", "version": "recovery", "title": "Прогулка",          "text": "Прогулка 20–30 мин",                                                           "micro_learning": None},
    # Day 40 — rest
    {"day": 40, "day_type": "rest", "version": "base",     "title": "Отдых", "text": "Отдых", "micro_learning": "💬 Полная пауза\n🤍 Восстановление закрепляет результат"},
    {"day": 40, "day_type": "rest", "version": "light",    "title": "Отдых", "text": "Отдых", "micro_learning": "💬 Полная пауза\n🤍 Восстановление закрепляет результат"},
    {"day": 40, "day_type": "rest", "version": "recovery", "title": "Отдых", "text": "Отдых", "micro_learning": None},
    # Day 41 — strength 2
    {"day": 41, "day_type": "strength", "version": "base",     "title": "Силовая 2", "text": None,   "micro_learning": "💬 Поддержка мышц без перегруза\n🤍 Качество важнее"},
    {"day": 41, "day_type": "strength", "version": "light",    "title": "Силовая 2", "text": None,   "micro_learning": "💬 Поддержка мышц без перегруза\n🤍 Качество важнее"},
    {"day": 41, "day_type": "strength", "version": "recovery", "title": "Отдых",     "text": "Отдых", "micro_learning": None},
    # Day 42 — long run
    {"day": 42, "day_type": "run", "version": "base",     "title": "Длинный бег", "text": "3–5 мин быстрая ходьба\nЛёгкий непрерывный бег 28–32 мин\nПульс: ~125–140", "micro_learning": "💬 Спокойный длинный бег — без геройства\n🤍 Оставь силы «в запасе»"},
    {"day": 42, "day_type": "run", "version": "light",    "title": "Длинный бег", "text": "3–5 мин быстрая ходьба\n20–24 мин лёгкий бег\nПульс: ~125–140",              "micro_learning": "💬 Спокойный длинный бег — без геройства\n🤍 Оставь силы «в запасе»"},
    {"day": 42, "day_type": "run", "version": "recovery", "title": "Прогулка",     "text": "Прогулка 30–40 мин",                                                          "micro_learning": None},
]

existing_days = {w["day"] for w in data}
if any(d in existing_days for d in range(36, 43)):
    print("Days 36-42 already exist — skipping.")
else:
    new_entries = []
    for level in range(1, 6):
        s1_base  = get_text(level, 1,  "base")
        s1_light = get_text(level, 1,  "light")
        s2_base  = get_text(level, 11, "base")
        s2_light = get_text(level, 11, "light")

        for entry in WEEK6_TEMPLATE:
            text = entry["text"]
            # Fill strength texts per level
            if entry["day_type"] == "strength" and entry["version"] != "recovery":
                if entry["title"] == "Силовая 1":
                    text = s1_base if entry["version"] == "base" else s1_light
                elif entry["title"] == "Силовая 2":
                    text = s2_base if entry["version"] == "base" else s2_light

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
    print(f"Added {len(new_entries)} entries (days 36-42, levels 1-5).")
    print(f"Total entries now: {len(data)}")
