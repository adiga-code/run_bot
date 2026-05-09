"""
scripts/migrate_workouts_to_templates.py

Мигрирует записи из data/workouts.json в таблицу workout_templates.

Что делает:
  - Читает все 546 записей из workouts.json
  - Для силовых тренировок с объединённым текстом (🏋 Зал + 🏠 Дома):
      → создаёт две записи WorkoutTemplate (strength_format=gym и home)
  - Для остальных: создаёт одну запись WorkoutTemplate без period и day-привязки
  - Определяет run_subtype и intensity_kind из заголовка/текста
  - Заменяет итоговые "(N мин)" на "{minutes}" там, где паттерн однозначен
  - Устойчив к повторному запуску: пропускает уже существующие записи

Запуск:
    python scripts/migrate_workouts_to_templates.py
    python scripts/migrate_workouts_to_templates.py --dry-run    # без записи в БД
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

# ── Добавляем корень проекта в sys.path ──────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ══════════════════════════════════════════════════════════════════════════════
# Определение run_subtype и intensity_kind по тексту / заголовку
# ══════════════════════════════════════════════════════════════════════════════

def _detect_run_subtype(title: str, text: str) -> str | None:
    """Определяет run_subtype из заголовка и текста тренировки."""
    t = (title + " " + text).lower()

    if any(k in t for k in ("прогулка", "ходьба")):
        return "recovery_run"
    if any(k in t for k in ("мин бег / ", "бег / ", "бег/шаг", "run_walk", "ходьба/бег")):
        return "run_walk"
    if any(k in t for k in ("длинный бег", "long", "длинная пробежка")):
        return "long"
    if any(k in t for k in ("темповый", "темп", "tempo")):
        return "tempo"
    if any(k in t for k in ("интервал", "interval", "ускорен")):
        return "intervals"
    if any(k in t for k in ("лёгкий бег", "лёгкая пробежка", "лёгкий")):
        return "easy"
    if any(k in t for k in ("аэробн", "aerobic")):
        return "aerobic"

    return "easy"  # дефолт для run


def _detect_intensity_kind(run_subtype: str | None, title: str, text: str) -> str | None:
    """Определяет intensity_kind (null / tempo / intervals)."""
    if run_subtype == "tempo":
        return "tempo"
    if run_subtype == "intervals":
        return "intervals"
    t = (title + " " + text).lower()
    if "z3" in t or "пульсовая зона 3" in t:
        return "z3_inclusions"
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Замена минут на {minutes}
# ══════════════════════════════════════════════════════════════════════════════

def _replace_total_minutes(text: str) -> str:
    """
    Заменяет итоговое количество минут в скобках на {minutes}.
    Паттерн: "(NN мин)" или "(~NN мин)" в конце строки.
    Не трогает частичные минуты ("1 мин бег", "2 мин шаг").
    """
    # Паттерн: "( [~≈]? число мин )" в конце строки или предложения
    pattern = r'\(~?(\d+)\s*мин\)'
    def replacer(m: re.Match) -> str:
        return "({minutes} мин)"

    return re.sub(pattern, replacer, text)


def _replace_walkrun_minutes(text: str) -> str:
    """Для одиночных строк вида 'Прогулка NN мин' — заменяем на {minutes}."""
    # "Прогулка 20 мин" → "Прогулка {minutes} мин"
    # "Лёгкий бег 30 мин" → "Лёгкий бег {minutes} мин"
    single_patterns = [
        (r'^(Прогулка\s+)\d+(?:–\d+)?\s*мин', r'\g<1>{minutes} мин'),
        (r'^(Лёгкий бег\s+)\d+(?:–\d+)?\s*мин', r'\g<1>{minutes} мин'),
        (r'^(Бег\s+)\d+(?:–\d+)?\s*мин', r'\g<1>{minutes} мин'),
    ]
    for pat, repl in single_patterns:
        text = re.sub(pat, repl, text, flags=re.MULTILINE)
    return text


def apply_minute_placeholders(text: str, day_type: str) -> str:
    """Применяет замену минут на {minutes} для run-тренировок."""
    if day_type != "run":
        return text
    text = _replace_total_minutes(text)
    text = _replace_walkrun_minutes(text)
    return text


# ══════════════════════════════════════════════════════════════════════════════
# Разбивка силовой тренировки на gym/home
# ══════════════════════════════════════════════════════════════════════════════

def split_gym_home(text: str) -> tuple[str | None, str | None]:
    """
    Разбивает комбинированный текст силовой тренировки на gym и home части.
    Возвращает (gym_text, home_text).
    Если одной из частей нет — возвращает None для неё.
    """
    home_markers = ["\n\n🏠 Дома", "\n🏠 Дома", "🏠 Дома"]
    gym_markers  = ["🏋️ Зал", "🏋 Зал"]

    has_gym  = any(m in text for m in gym_markers)
    has_home = any(m in text for m in home_markers)

    if not has_gym and not has_home:
        return text, None  # ни того, ни другого — возвращаем как gym

    if has_gym and not has_home:
        return text, None

    if not has_gym and has_home:
        return None, text

    # Найдём точку разрыва между gym и home
    split_idx = -1
    for marker in ["\n\n🏠 Дома", "\n🏠 Дома"]:
        idx = text.find(marker)
        if idx != -1:
            split_idx = idx
            break

    if split_idx == -1:
        return text, None

    gym_part  = text[:split_idx].strip()
    home_part = text[split_idx:].strip()
    return gym_part, home_part


# ══════════════════════════════════════════════════════════════════════════════
# Основная логика миграции
# ══════════════════════════════════════════════════════════════════════════════

def build_template_records(workouts: list[dict]) -> list[dict]:
    """
    Преобразует список записей workouts.json в список параметров
    для создания WorkoutTemplate.
    """
    records: list[dict] = []

    for w in workouts:
        level    = w["level"]
        day_type = w["day_type"]
        version  = w["version"]
        title    = w.get("title") or "Тренировка"
        text     = w.get("text") or ""
        sf       = w.get("strength_format")  # None / "gym" / "home"

        # ── Силовые: разбиваем на gym/home ────────────────────────────────────
        if day_type == "strength" and sf is None and (
            any(m in text for m in ["🏋️ Зал", "🏋 Зал"]) and "🏠 Дома" in text
        ):
            gym_text, home_text = split_gym_home(text)
            if gym_text:
                records.append(_make_record(
                    level=level, day_type=day_type, version=version,
                    title=title, text=gym_text, strength_format="gym",
                    run_subtype=None, intensity_kind=None,
                    w=w,
                ))
            if home_text:
                records.append(_make_record(
                    level=level, day_type=day_type, version=version,
                    title=title, text=home_text, strength_format="home",
                    run_subtype=None, intensity_kind=None,
                    w=w,
                ))
        else:
            # ── Беговые: определяем subtype и заменяем минуты ────────────────
            if day_type == "run":
                run_subtype    = _detect_run_subtype(title, text)
                intensity_kind = _detect_intensity_kind(run_subtype, title, text)
                text           = apply_minute_placeholders(text, day_type)
            else:
                run_subtype    = None
                intensity_kind = None

            records.append(_make_record(
                level=level, day_type=day_type, version=version,
                title=title, text=text, strength_format=sf,
                run_subtype=run_subtype, intensity_kind=intensity_kind,
                w=w,
            ))

    return records


def _make_record(
    level: int,
    day_type: str,
    version: str,
    title: str,
    text: str,
    strength_format: str | None,
    run_subtype: str | None,
    intensity_kind: str | None,
    w: dict,
) -> dict:
    return {
        "level":           level,
        "day_type":        day_type,
        "version":         version,
        "title":           title,
        "short_title":     w.get("short_title"),
        "text":            text,
        "strength_format": strength_format,
        "run_subtype":     run_subtype,
        "intensity_kind":  intensity_kind,
        "period":          None,  # универсальный (не привязан к периоду)
        "micro_learning":  w.get("micro_learning"),
        "video_url":       w.get("video_url"),
        "media_id":        w.get("media_id"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# Запись в БД
# ══════════════════════════════════════════════════════════════════════════════

async def run_migration(dry_run: bool = False) -> None:
    from database.models import WorkoutTemplate
    from database.engine import get_session_maker  # type: ignore[import]
    from sqlalchemy import select

    # Загружаем workouts.json
    json_path = PROJECT_ROOT / "data" / "workouts.json"
    workouts = json.loads(json_path.read_text(encoding="utf-8"))
    print(f"[migrate] Loaded {len(workouts)} records from workouts.json")

    records = build_template_records(workouts)
    print(f"[migrate] Generated {len(records)} WorkoutTemplate records "
          f"(strength gym/home split applied)")

    if dry_run:
        print("[migrate] --dry-run: no DB writes.")
        for r in records[:5]:
            print(f"  level={r['level']} {r['day_type']}/{r['version']} "
                  f"sf={r['strength_format']} sub={r['run_subtype']} "
                  f"title={r['title']!r}")
        print(f"  ... (+{len(records)-5} more)")
        return

    # Подключаемся к БД
    try:
        session_maker = get_session_maker()
    except Exception as exc:
        # Fallback: попробуем создать engine напрямую из config
        from config import settings
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
        engine = create_async_engine(str(settings.database_url), echo=False)
        session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    created = 0
    skipped = 0

    async with session_maker() as session:
        # Проверяем что таблица существует
        existing_count_result = await session.execute(
            select(WorkoutTemplate).limit(1)
        )
        existing_first = existing_count_result.scalar_one_or_none()

        for rec in records:
            # Проверяем на дубль (идемпотентность)
            q = select(WorkoutTemplate).where(
                WorkoutTemplate.level       == rec["level"],
                WorkoutTemplate.day_type    == rec["day_type"],
                WorkoutTemplate.version     == rec["version"],
                WorkoutTemplate.title       == rec["title"],
            )
            if rec["strength_format"] is not None:
                q = q.where(WorkoutTemplate.strength_format == rec["strength_format"])
            else:
                q = q.where(WorkoutTemplate.strength_format.is_(None))

            if rec["period"] is not None:
                q = q.where(WorkoutTemplate.period == rec["period"])
            else:
                q = q.where(WorkoutTemplate.period.is_(None))

            existing = (await session.execute(q.limit(1))).scalar_one_or_none()
            if existing:
                skipped += 1
                continue

            tmpl = WorkoutTemplate(
                level           = rec["level"],
                day_type        = rec["day_type"],
                run_subtype     = rec["run_subtype"],
                version         = rec["version"],
                intensity_kind  = rec["intensity_kind"],
                period          = rec["period"],
                strength_format = rec["strength_format"],
                title           = rec["title"],
                short_title     = rec["short_title"],
                text            = rec["text"],
                micro_learning  = rec["micro_learning"],
                video_url       = rec["video_url"],
                media_id        = rec["media_id"],
            )
            session.add(tmpl)
            created += 1

        await session.commit()

    print(f"[migrate] Done: created={created}  skipped(duplicate)={skipped}")


# ══════════════════════════════════════════════════════════════════════════════
# CLI entry point
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate workouts.json → WorkoutTemplate table"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview what would be inserted without writing to DB",
    )
    args = parser.parse_args()
    asyncio.run(run_migration(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
