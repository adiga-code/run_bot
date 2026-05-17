"""Script to add weeks 9–12 (days 57–84) workouts to workouts.json."""
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


# ── WEEK 9 (days 57–63) — РАЗГРУЗОЧНАЯ ───────────────────────────────────────
WEEK9_TEMPLATE = [
    # Day 57 — восстановление (прогулка + мобильность)
    {"day": 57, "day_type": "recovery", "version": "base",     "title": "Восстановление", "text": "Прогулка 30 мин\nМобильность 10 мин",      "micro_learning": "💬 Снимаем накопленную усталость\n🤍 Восстановление — тоже часть прогресса"},
    {"day": 57, "day_type": "recovery", "version": "light",    "title": "Восстановление", "text": "Прогулка 20 мин\nМобильность 10 мин",      "micro_learning": "💬 Снимаем накопленную усталость\n🤍 Восстановление — тоже часть прогресса"},
    {"day": 57, "day_type": "recovery", "version": "recovery", "title": "Восстановление", "text": "Прогулка 20 мин\nМобильность 10 мин",      "micro_learning": None},
    # Day 58 — бег (интервалы)
    {"day": 58, "day_type": "run", "version": "base",     "title": "Лёгкий бег", "text": "5 мин быстрая ходьба\n10 мин лёгкий бег\n2 мин шаг\n8 мин лёгкий бег\nПульс: 125–138",       "micro_learning": "💬 Возвращаем лёгкость в движении\n🤍 Сегодня задача — закончить свежим"},
    {"day": 58, "day_type": "run", "version": "light",    "title": "Лёгкий бег", "text": "5 мин ходьба\n8 мин бег\n2 мин шаг\n6 мин бег\n2 мин шаг\nПульс: 125–138",               "micro_learning": "💬 Возвращаем лёгкость в движении\n🤍 Сегодня задача — закончить свежим"},
    {"day": 58, "day_type": "run", "version": "recovery", "title": "Прогулка",    "text": "Прогулка 25 мин",                                                                          "micro_learning": None},
    # Day 59 — отдых
    {"day": 59, "day_type": "rest", "version": "base",     "title": "Отдых", "text": "Отдых", "micro_learning": "💬 Полная пауза\n🤍 Тело восстанавливается и становится сильнее"},
    {"day": 59, "day_type": "rest", "version": "light",    "title": "Отдых", "text": "Отдых", "micro_learning": "💬 Полная пауза\n🤍 Тело восстанавливается и становится сильнее"},
    {"day": 59, "day_type": "rest", "version": "recovery", "title": "Отдых", "text": "Отдых", "micro_learning": None},
    # Day 60 — силовая (облегчённая)
    {"day": 60, "day_type": "strength", "is_reduced": True, "reduction_base": 30, "reduction_light": 40, "version": "base",     "title": "Силовая 1", "text": None, "micro_learning": "💬 Только поддержка мышц\n🤍 Без тяжёлой работы"},
    {"day": 60, "day_type": "strength", "is_reduced": True, "reduction_base": 30, "reduction_light": 40, "version": "light",    "title": "Силовая 1", "text": None, "micro_learning": "💬 Только поддержка мышц\n🤍 Без тяжёлой работы"},
    {"day": 60, "day_type": "strength", "is_reduced": True, "reduction_base": 30, "reduction_light": 40, "version": "recovery", "title": "Отдых",     "text": "Отдых", "micro_learning": None},
    # Day 61 — восстановление
    {"day": 61, "day_type": "recovery", "version": "base",     "title": "Восстановление", "text": "Прогулка 30 мин", "micro_learning": "💬 Спокойное движение после силовой\n🤍 Дай мышцам отдохнуть"},
    {"day": 61, "day_type": "recovery", "version": "light",    "title": "Восстановление", "text": "Прогулка 20 мин", "micro_learning": "💬 Спокойное движение после силовой\n🤍 Дай мышцам отдохнуть"},
    {"day": 61, "day_type": "recovery", "version": "recovery", "title": "Отдых",           "text": "Отдых",          "micro_learning": None},
    # Day 62 — бег (непрерывный)
    {"day": 62, "day_type": "run", "version": "base",     "title": "Лёгкий бег", "text": "20 мин непрерывного лёгкого бега\nПульс: 125–140",  "micro_learning": "💬 Спокойный ровный бег\n🤍 Не ускоряемся"},
    {"day": 62, "day_type": "run", "version": "light",    "title": "Лёгкий бег", "text": "15 мин лёгкого бега\nПульс: до 138",                "micro_learning": "💬 Спокойный ровный бег\n🤍 Не ускоряемся"},
    {"day": 62, "day_type": "run", "version": "recovery", "title": "Прогулка",    "text": "Прогулка 25 мин",                                   "micro_learning": None},
    # Day 63 — отдых
    {"day": 63, "day_type": "rest", "version": "base",     "title": "Отдых", "text": "Отдых", "micro_learning": "💬 Завершаем разгрузочную неделю\n🤍 Тело готово к новой нагрузке"},
    {"day": 63, "day_type": "rest", "version": "light",    "title": "Отдых", "text": "Отдых", "micro_learning": "💬 Завершаем разгрузочную неделю\n🤍 Тело готово к новой нагрузке"},
    {"day": 63, "day_type": "rest", "version": "recovery", "title": "Отдых", "text": "Отдых", "micro_learning": None},
]

# ── WEEK 10 (days 64–70) — СТАБИЛИЗАЦИЯ ──────────────────────────────────────
WEEK10_TEMPLATE = [
    # Day 64 — силовая 1
    {"day": 64, "day_type": "strength", "version": "base",     "title": "Силовая 1", "text": None,    "micro_learning": "💬 Возвращаемся к нагрузке без скачка\n🤍 Стабильность важнее"},
    {"day": 64, "day_type": "strength", "version": "light",    "title": "Силовая 1", "text": None,    "micro_learning": "💬 Возвращаемся к нагрузке без скачка\n🤍 Стабильность важнее"},
    {"day": 64, "day_type": "strength", "version": "recovery", "title": "Отдых",     "text": "Отдых", "micro_learning": None},
    # Day 65 — бег (интервалы)
    {"day": 65, "day_type": "run", "version": "base",     "title": "Интервальный бег", "text": "5 мин ходьба\n12 мин бег\n2 мин шаг\n12 мин бег\nПульс: 125–140",           "micro_learning": "💬 Контроль важнее длительности\n🤍 Бег остаётся лёгким"},
    {"day": 65, "day_type": "run", "version": "light",    "title": "Интервальный бег", "text": "5 мин ходьба\n10 мин бег\n2 мин шаг\n8 мин бег\n2 мин шаг\nПульс: до 140", "micro_learning": "💬 Контроль важнее длительности\n🤍 Бег остаётся лёгким"},
    {"day": 65, "day_type": "run", "version": "recovery", "title": "Прогулка",          "text": "Прогулка 25 мин",                                                           "micro_learning": None},
    # Day 66 — восстановление
    {"day": 66, "day_type": "recovery", "version": "base",     "title": "Восстановление", "text": "Прогулка 35 мин", "micro_learning": "💬 Организм адаптируется к нагрузке\n🤍 Сейчас важна устойчивость"},
    {"day": 66, "day_type": "recovery", "version": "light",    "title": "Восстановление", "text": "Прогулка 20 мин", "micro_learning": "💬 Организм адаптируется к нагрузке\n🤍 Сейчас важна устойчивость"},
    {"day": 66, "day_type": "recovery", "version": "recovery", "title": "Отдых",           "text": "Отдых",          "micro_learning": None},
    # Day 67 — бег (непрерывный)
    {"day": 67, "day_type": "run", "version": "base",     "title": "Непрерывный бег", "text": "30 мин лёгкого непрерывного бега\nПульс: 125–140", "micro_learning": "💬 Спокойный непрерывный бег\n🤍 Должно оставаться ощущение запаса"},
    {"day": 67, "day_type": "run", "version": "light",    "title": "Непрерывный бег", "text": "22 мин лёгкого бега\nПульс: до 140",               "micro_learning": "💬 Спокойный непрерывный бег\n🤍 Должно оставаться ощущение запаса"},
    {"day": 67, "day_type": "run", "version": "recovery", "title": "Прогулка",          "text": "Прогулка 30 мин",                                 "micro_learning": None},
    # Day 68 — отдых
    {"day": 68, "day_type": "rest", "version": "base",     "title": "Отдых", "text": "Отдых", "micro_learning": "💬 Полная пауза перед силовой\n🤍 Накопленная усталость должна уйти"},
    {"day": 68, "day_type": "rest", "version": "light",    "title": "Отдых", "text": "Отдых", "micro_learning": "💬 Полная пауза перед силовой\n🤍 Накопленная усталость должна уйти"},
    {"day": 68, "day_type": "rest", "version": "recovery", "title": "Отдых", "text": "Отдых", "micro_learning": None},
    # Day 69 — силовая 2
    {"day": 69, "day_type": "strength", "strength_num": 2, "version": "base",     "title": "Силовая 2", "text": None,    "micro_learning": "💬 Разнообразие — ключ к прогрессу\n🤍 Работаем аккуратно"},
    {"day": 69, "day_type": "strength", "strength_num": 2, "version": "light",    "title": "Силовая 2", "text": None,    "micro_learning": "💬 Разнообразие — ключ к прогрессу\n🤍 Работаем аккуратно"},
    {"day": 69, "day_type": "strength", "strength_num": 2, "version": "recovery", "title": "Отдых",     "text": "Отдых", "micro_learning": None},
    # Day 70 — длинный бег
    {"day": 70, "day_type": "run", "version": "base",     "title": "Длинный бег", "text": "36 мин лёгкого бега\nПульс: 125–140", "micro_learning": "💬 Очень спокойный длительный бег\n🤍 Заканчиваем с ощущением, что могли ещё"},
    {"day": 70, "day_type": "run", "version": "light",    "title": "Длинный бег", "text": "28 мин лёгкого бега\nПульс: до 140",  "micro_learning": "💬 Очень спокойный длительный бег\n🤍 Заканчиваем с ощущением, что могли ещё"},
    {"day": 70, "day_type": "run", "version": "recovery", "title": "Прогулка",    "text": "Прогулка 35 мин",                     "micro_learning": None},
]

# ── WEEK 11 (days 71–77) — МЯГКОЕ РАЗВИТИЕ ВЫНОСЛИВОСТИ ─────────────────────
WEEK11_TEMPLATE = [
    # Day 71 — восстановление
    {"day": 71, "day_type": "recovery", "version": "base",     "title": "Восстановление", "text": "Прогулка 30 мин", "micro_learning": "💬 Делаем текущий объём привычным\n🤍 Тело адаптируется"},
    {"day": 71, "day_type": "recovery", "version": "light",    "title": "Восстановление", "text": "Прогулка 20 мин", "micro_learning": "💬 Делаем текущий объём привычным\n🤍 Тело адаптируется"},
    {"day": 71, "day_type": "recovery", "version": "recovery", "title": "Отдых",           "text": "Отдых",          "micro_learning": None},
    # Day 72 — бег (интервалы)
    {"day": 72, "day_type": "run", "version": "base",     "title": "Интервальный бег", "text": "14 мин бег\n2 мин шаг\n12 мин бег\n2 мин шаг\nПульс: 125–140", "micro_learning": "💬 Интервалы остаются мягкими\n🤍 Не уходим в тяжесть"},
    {"day": 72, "day_type": "run", "version": "light",    "title": "Интервальный бег", "text": "10 мин бег\n2 мин шаг\n8 мин бег\n2 мин шаг\nПульс: до 140",   "micro_learning": "💬 Интервалы остаются мягкими\n🤍 Не уходим в тяжесть"},
    {"day": 72, "day_type": "run", "version": "recovery", "title": "Прогулка",          "text": "Прогулка 25 мин",                                               "micro_learning": None},
    # Day 73 — силовая 1
    {"day": 73, "day_type": "strength", "version": "base",     "title": "Силовая 1", "text": None,    "micro_learning": "💬 Силовая поддерживает бег\n🤍 Работаем стабильно"},
    {"day": 73, "day_type": "strength", "version": "light",    "title": "Силовая 1", "text": None,    "micro_learning": "💬 Силовая поддерживает бег\n🤍 Работаем стабильно"},
    {"day": 73, "day_type": "strength", "version": "recovery", "title": "Отдых",     "text": "Отдых", "micro_learning": None},
    # Day 74 — восстановление
    {"day": 74, "day_type": "recovery", "version": "base",     "title": "Восстановление", "text": "Прогулка 30 мин", "micro_learning": "💬 Переварить нагрузку — задача дня\n🤍 Это тоже часть прогресса"},
    {"day": 74, "day_type": "recovery", "version": "light",    "title": "Восстановление", "text": "Прогулка 20 мин", "micro_learning": "💬 Переварить нагрузку — задача дня\n🤍 Это тоже часть прогресса"},
    {"day": 74, "day_type": "recovery", "version": "recovery", "title": "Отдых",           "text": "Отдых",          "micro_learning": None},
    # Day 75 — бег (непрерывный)
    {"day": 75, "day_type": "run", "version": "base",     "title": "Непрерывный бег", "text": "32 мин непрерывного бега\nПульс: 125–140", "micro_learning": "💬 Ровный лёгкий бег\n🤍 Комфорт — главный ориентир"},
    {"day": 75, "day_type": "run", "version": "light",    "title": "Непрерывный бег", "text": "24 мин лёгкого бега\nПульс: до 140",       "micro_learning": "💬 Ровный лёгкий бег\n🤍 Комфорт — главный ориентир"},
    {"day": 75, "day_type": "run", "version": "recovery", "title": "Прогулка",          "text": "Прогулка 30 мин",                         "micro_learning": None},
    # Day 76 — отдых
    {"day": 76, "day_type": "rest", "version": "base",     "title": "Отдых", "text": "Отдых", "micro_learning": "💬 Полная пауза перед длинным бегом\n🤍 Восстановись заранее"},
    {"day": 76, "day_type": "rest", "version": "light",    "title": "Отдых", "text": "Отдых", "micro_learning": "💬 Полная пауза перед длинным бегом\n🤍 Восстановись заранее"},
    {"day": 76, "day_type": "rest", "version": "recovery", "title": "Отдых", "text": "Отдых", "micro_learning": None},
    # Day 77 — длинный бег
    {"day": 77, "day_type": "run", "version": "base",     "title": "Длинный бег", "text": "40 мин лёгкого бега\nПульс: 125–140", "micro_learning": "💬 Длинный спокойный бег\n🤍 Лучше медленнее, чем тяжелее"},
    {"day": 77, "day_type": "run", "version": "light",    "title": "Длинный бег", "text": "30 мин лёгкого бега\nПульс: до 140",  "micro_learning": "💬 Длинный спокойный бег\n🤍 Лучше медленнее, чем тяжелее"},
    {"day": 77, "day_type": "run", "version": "recovery", "title": "Прогулка",    "text": "Прогулка 40 мин",                     "micro_learning": None},
]

# ── WEEK 12 (days 78–84) — ЗАКРЕПЛЕНИЕ ───────────────────────────────────────
WEEK12_TEMPLATE = [
    # Day 78 — силовая 2
    {"day": 78, "day_type": "strength", "strength_num": 2, "version": "base",     "title": "Силовая 2", "text": None,    "micro_learning": "💬 Начинаем неделю закрепления\n🤍 Объём устойчивым без перегруза"},
    {"day": 78, "day_type": "strength", "strength_num": 2, "version": "light",    "title": "Силовая 2", "text": None,    "micro_learning": "💬 Начинаем неделю закрепления\n🤍 Объём устойчивым без перегруза"},
    {"day": 78, "day_type": "strength", "strength_num": 2, "version": "recovery", "title": "Отдых",     "text": "Отдых", "micro_learning": None},
    # Day 79 — бег (непрерывный)
    {"day": 79, "day_type": "run", "version": "base",     "title": "Лёгкий бег", "text": "28 мин лёгкого бега\nПульс: 125–140",    "micro_learning": "💬 Лёгкий контролируемый бег\n🤍 Без ускорений и резких движений"},
    {"day": 79, "day_type": "run", "version": "light",    "title": "Лёгкий бег", "text": "22 мин лёгкого бега\nПульс: до 140",     "micro_learning": "💬 Лёгкий контролируемый бег\n🤍 Без ускорений и резких движений"},
    {"day": 79, "day_type": "run", "version": "recovery", "title": "Прогулка",    "text": "Прогулка 25–30 мин",                    "micro_learning": None},
    # Day 80 — восстановление
    {"day": 80, "day_type": "recovery", "version": "base",     "title": "Восстановление", "text": "Прогулка 30 мин", "micro_learning": "💬 Даём организму закрепить результат\n🤍 Спокойный день — часть тренировки"},
    {"day": 80, "day_type": "recovery", "version": "light",    "title": "Восстановление", "text": "Прогулка 20 мин", "micro_learning": "💬 Даём организму закрепить результат\n🤍 Спокойный день — часть тренировки"},
    {"day": 80, "day_type": "recovery", "version": "recovery", "title": "Отдых",           "text": "Отдых",          "micro_learning": None},
    # Day 81 — бег (непрерывный)
    {"day": 81, "day_type": "run", "version": "base",     "title": "Непрерывный бег", "text": "34 мин лёгкого бега\nПульс: 125–140", "micro_learning": "💬 Спокойный стабильный бег\n🤍 Без борьбы с темпом"},
    {"day": 81, "day_type": "run", "version": "light",    "title": "Непрерывный бег", "text": "26 мин лёгкого бега\nПульс: до 140",  "micro_learning": "💬 Спокойный стабильный бег\n🤍 Без борьбы с темпом"},
    {"day": 81, "day_type": "run", "version": "recovery", "title": "Прогулка",          "text": "Прогулка 30 мин",                     "micro_learning": None},
    # Day 82 — отдых
    {"day": 82, "day_type": "rest", "version": "base",     "title": "Отдых", "text": "Отдых", "micro_learning": "💬 Полная пауза перед лонгом\n🤍 Накопленная усталость должна уйти"},
    {"day": 82, "day_type": "rest", "version": "light",    "title": "Отдых", "text": "Отдых", "micro_learning": "💬 Полная пауза перед лонгом\n🤍 Накопленная усталость должна уйти"},
    {"day": 82, "day_type": "rest", "version": "recovery", "title": "Отдых", "text": "Отдых", "micro_learning": None},
    # Day 83 — силовая 1
    {"day": 83, "day_type": "strength", "version": "base",     "title": "Силовая 1", "text": None,    "micro_learning": "💬 Последняя силовая — держим качество\n🤍 Без спешки"},
    {"day": 83, "day_type": "strength", "version": "light",    "title": "Силовая 1", "text": None,    "micro_learning": "💬 Последняя силовая — держим качество\n🤍 Без спешки"},
    {"day": 83, "day_type": "strength", "version": "recovery", "title": "Отдых",     "text": "Отдых", "micro_learning": None},
    # Day 84 — длинный бег (завершение блока)
    {"day": 84, "day_type": "run", "version": "base",     "title": "Длинный бег", "text": "5 мин быстрая ходьба\n42 мин лёгкого бега\nПульс: 125–140", "micro_learning": "💬 Спокойное завершение блока\n🤍 После бега должны остаться силы"},
    {"day": 84, "day_type": "run", "version": "light",    "title": "Длинный бег", "text": "5 мин быстрая ходьба\n32 мин лёгкого бега\nПульс: до 140",  "micro_learning": "💬 Спокойное завершение блока\n🤍 После бега должны остаться силы"},
    {"day": 84, "day_type": "run", "version": "recovery", "title": "Прогулка",    "text": "Прогулка 40 мин",                                              "micro_learning": None},
]

ALL_TEMPLATES = WEEK9_TEMPLATE + WEEK10_TEMPLATE + WEEK11_TEMPLATE + WEEK12_TEMPLATE

existing_days = {w["day"] for w in data}
if any(d in existing_days for d in range(57, 85)):
    print("Days 57–84 already exist — skipping.")
else:
    new_entries = []
    for level in range(1, 6):
        s1_base  = get_text(level, 1,  "base")
        s1_light = get_text(level, 1,  "light")
        s2_base  = get_text(level, 11, "base")
        s2_light = get_text(level, 11, "light")

        for entry in ALL_TEMPLATES:
            text = entry["text"]

            if entry["day_type"] == "strength" and entry["version"] != "recovery":
                strength_num = entry.get("strength_num", 1)
                is_reduced   = entry.get("is_reduced", False)

                if strength_num == 2:
                    base_text = s2_base if entry["version"] == "base" else s2_light
                else:
                    base_text = s1_base if entry["version"] == "base" else s1_light

                if is_reduced:
                    reduction = (
                        entry["reduction_base"]
                        if entry["version"] == "base"
                        else entry["reduction_light"]
                    )
                    prefix = f"⬇️ Сегодня минус {reduction}% объёма\n\n"
                    text = prefix + base_text if base_text else prefix.strip()
                else:
                    text = base_text

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
    print(f"Added {len(new_entries)} entries (days 57–84, levels 1–5).")
    print(f"Total entries now: {len(data)}")
