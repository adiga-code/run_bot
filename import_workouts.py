"""
Импорт тренировок из CSV или JSON в базу данных.

Использование:
  python import_workouts.py data/workouts.csv          # вставить новые (пропустить дубли)
  python import_workouts.py data/workouts.csv --update # вставить + перезаписать дубли
  python import_workouts.py data/workouts.csv --dry-run # проверить без записи в БД
  python import_workouts.py data/workouts.json         # поддерживает и JSON
"""

import argparse
import asyncio
import csv
import json
import sys
from pathlib import Path

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Подгружаем настройки и модели
from config import settings
from database.models import Base, Workout

VALID_DAY_TYPES = {"run", "strength", "recovery", "rest"}
VALID_VERSIONS = {"base", "light", "recovery"}
REQUIRED_COLUMNS = {"level", "day", "day_type", "version", "title", "text"}
OPTIONAL_COLUMNS = {"short_title", "video_url", "media_id"}


# ── Валидация ─────────────────────────────────────────────────────────────────

class ValidationError(Exception):
    pass


def validate_row(row: dict, row_num: int) -> dict:
    # Normalize all values to strings for uniform handling
    row = {k: str(v) if v is not None else "" for k, v in row.items()}

    errors = []

    # Обязательные поля
    for col in REQUIRED_COLUMNS:
        if not row.get(col, "").strip():
            errors.append(f"  строка {row_num}: пустое обязательное поле '{col}'")

    if errors:
        raise ValidationError("\n".join(errors))

    # level
    try:
        level = int(row["level"])
        if level not in (1, 2, 3, 4):
            raise ValueError
    except (ValueError, KeyError):
        raise ValidationError(f"  строка {row_num}: поле 'level' должно быть 1, 2, 3 или 4, получено: '{row.get('level')}'")

    # day
    try:
        day = int(row["day"])
        if not 1 <= day <= 28:
            raise ValueError
    except (ValueError, KeyError):
        raise ValidationError(f"  строка {row_num}: поле 'day' должно быть от 1 до 28, получено: '{row.get('day')}'")

    # day_type
    day_type = row["day_type"].strip().lower()
    if day_type not in VALID_DAY_TYPES:
        raise ValidationError(f"  строка {row_num}: поле 'day_type' должно быть одним из {VALID_DAY_TYPES}, получено: '{day_type}'")

    # version
    version = row["version"].strip().lower()
    if version not in VALID_VERSIONS:
        raise ValidationError(f"  строка {row_num}: поле 'version' должно быть одним из {VALID_VERSIONS}, получено: '{version}'")

    # Предупреждение: rest-день не должен иметь версий
    if day_type == "rest":
        print(f"  [WARN]  строка {row_num}: day_type='rest' — текст тренировки для дня отдыха игнорируется ботом")

    return {
        "level": level,
        "day": day,
        "day_type": day_type,
        "version": version,
        "title": row["title"].strip(),
        "short_title": row.get("short_title", "").strip() or None,
        "text": row["text"].strip(),
        "micro_learning": row.get("micro_learning", "").strip() or None,
        "video_url": row.get("video_url", "").strip() or None,
        "media_id": row.get("media_id", "").strip() or None,
    }


# ── Загрузка файла ────────────────────────────────────────────────────────────

def load_csv(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):  # строка 1 = заголовок
            rows.append((i, dict(row)))
    return rows


def load_json(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return [(i + 2, row) for i, row in enumerate(data)]


def load_file(path: Path) -> list[dict]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return load_csv(path)
    elif suffix == ".json":
        return load_json(path)
    else:
        print(f"[ERR] Неподдерживаемый формат файла: {suffix}. Используйте .csv или .json")
        sys.exit(1)


# ── Импорт в БД ───────────────────────────────────────────────────────────────

async def import_workouts(
    rows: list[dict],
    update: bool,
    dry_run: bool,
) -> None:
    engine = create_async_engine(settings.database_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    inserted = 0
    updated = 0
    skipped = 0

    async with maker() as session:
        for row in rows:
            # Проверяем есть ли запись с таким key (level + day + version)
            result = await session.execute(
                select(Workout).where(
                    Workout.level == row["level"],
                    Workout.day == row["day"],
                    Workout.version == row["version"],
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                if update:
                    if not dry_run:
                        for key, value in row.items():
                            setattr(existing, key, value)
                    updated += 1
                else:
                    skipped += 1
            else:
                if not dry_run:
                    session.add(Workout(**row))
                inserted += 1

        if not dry_run:
            await session.commit()

    await engine.dispose()

    mode = "[DRY RUN] " if dry_run else ""
    print(f"\n{mode}Результат импорта:")
    print(f"  [OK] Добавлено:    {inserted}")
    print(f"  [UPD] Обновлено:   {updated}")
    print(f"  [SKIP]  Пропущено:   {skipped}")
    if skipped and not update:
        print(f"     (используй --update чтобы перезаписать существующие записи)")


# ── Отчёт о структуре ─────────────────────────────────────────────────────────

def print_summary(valid_rows: list[dict]) -> None:
    from collections import defaultdict
    by_level = defaultdict(lambda: defaultdict(int))
    for row in valid_rows:
        by_level[row["level"]][row["day_type"]] += 1

    print("\nСтруктура импортируемых данных:")
    print(f"  Всего записей: {len(valid_rows)}")
    for level in sorted(by_level):
        counts = by_level[level]
        total = sum(counts.values())
        breakdown = ", ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
        print(f"  Уровень {level}: {total} записей  ({breakdown})")


# ── Проверка полноты данных ───────────────────────────────────────────────────

def check_completeness(valid_rows: list[dict]) -> None:
    from collections import defaultdict
    index = defaultdict(set)
    for row in valid_rows:
        key = (row["level"], row["day"], row["day_type"])
        index[key].add(row["version"])

    missing = []
    for (level, day, day_type), versions in sorted(index.items()):
        if day_type == "rest":
            continue
        for v in VALID_VERSIONS:
            if v not in versions:
                missing.append(f"  уровень {level}, день {day}, тип {day_type}: отсутствует версия '{v}'")

    if missing:
        print(f"\n[WARN]  Пропущенные версии ({len(missing)}):")
        for m in missing[:20]:
            print(m)
        if len(missing) > 20:
            print(f"  ... и ещё {len(missing) - 20}")
    else:
        print("\n[OK] Все версии (base/light/recovery) для каждого дня заполнены")


# ── Точка входа ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Импорт тренировок в БД из CSV или JSON")
    parser.add_argument("file", type=Path, help="Путь к файлу (CSV или JSON)")
    parser.add_argument("--update", action="store_true", help="Перезаписать существующие записи")
    parser.add_argument("--dry-run", action="store_true", help="Проверить без записи в БД")
    args = parser.parse_args()

    if not args.file.exists():
        print(f"[ERR] Файл не найден: {args.file}")
        sys.exit(1)

    print(f"[FILE] Загружаем файл: {args.file}")
    raw_rows = load_file(args.file)
    print(f"   Строк в файле: {len(raw_rows)}")

    # Валидация
    valid_rows = []
    errors = []
    for row_num, row in raw_rows:
        try:
            valid_rows.append(validate_row(row, row_num))
        except ValidationError as e:
            errors.append(str(e))

    if errors:
        print(f"\n[ERR] Ошибки валидации ({len(errors)}):")
        for err in errors:
            print(err)
        print(f"\nИсправь ошибки и запусти снова.")
        sys.exit(1)

    print(f"[OK] Валидация прошла успешно")
    print_summary(valid_rows)
    check_completeness(valid_rows)

    if args.dry_run:
        print("\n[DRY RUN] Записи в БД не вносятся.")

    asyncio.run(import_workouts(valid_rows, update=args.update, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
