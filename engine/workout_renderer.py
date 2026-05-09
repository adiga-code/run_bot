"""
engine/workout_renderer.py
Рендер текста тренировки из шаблона + параметров дня.
Spec раздел 3.7.2.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from engine.constants import LIGHT_VOLUME_MULTIPLIER, round_int

if TYPE_CHECKING:
    from database.models import WorkoutTemplate


@dataclass
class RenderedWorkout:
    title: str
    text: str
    planned_minutes: int       # скорректированные минуты (Light = −20%)
    version: str               # base / light / recovery / rest
    micro_learning: str | None = None
    video_url: str | None = None
    media_id: str | None = None


def render_workout(
    template: "WorkoutTemplate",
    target_minutes: int,
    version: str,             # base / light / recovery / rest
    intensity_kind: str | None = None,
    long_stage: int | None = None,   # 1 или 2 для L1
) -> RenderedWorkout:
    """
    Берёт шаблон + параметры → финальный текст тренировки.

    Base:     полный план, target_minutes без изменений.
    Light:    −20%, интервалы/темп → заменяем на easy-описание.
    Recovery: всегда «прогулка 20-30 мин Z1», независимо от шаблона.
    Rest:     «день отдыха».
    """
    if version == "rest":
        return RenderedWorkout(
            title="День отдыха 🛌",
            text="Сегодня полный отдых. Можно лёгкая мобильность по желанию.",
            planned_minutes=0,
            version="rest",
        )

    if version == "recovery":
        return RenderedWorkout(
            title="Восстановление 🚶",
            text=(
                "Сегодня вместо тренировки — восстановление.\n\n"
                "🚶 Прогулка 20–30 мин в лёгком темпе (Z1 — разговорный темп).\n"
                "По желанию: растяжка или мобильность 10–15 мин.\n\n"
                "Никакого бега и силовых сегодня — тело восстанавливается."
            ),
            planned_minutes=25,
            version="recovery",
        )

    # ── Считаем минуты ───────────────────────────────────────────────────────
    if version == "light":
        actual_minutes = round_int(target_minutes * LIGHT_VOLUME_MULTIPLIER)
    else:
        actual_minutes = target_minutes

    # ── Формируем контекст для подстановки ──────────────────────────────────
    ctx = _build_context(actual_minutes, template)

    # ── Light с интенсивностью → заменяем на easy ────────────────────────────
    is_intensity = intensity_kind in ("tempo", "intervals") or (
        template.run_subtype in ("tempo", "intervals")
    )

    if version == "light" and is_intensity:
        text = _render_light_instead_of_intensity(actual_minutes, template)
        title = f"[Лайт] Лёгкий бег {actual_minutes} мин"
    else:
        raw_text = template.text or ""
        text = _substitute(raw_text, ctx)
        prefix = "[Лайт] " if version == "light" else ""
        title = prefix + (template.title or "Тренировка")

    # ── Long + Light: не заменяем на easy, только −20% ───────────────────────
    if version == "light" and template.run_subtype == "long":
        raw_text = template.text or ""
        text = _substitute(raw_text, ctx)
        title = f"[Лайт] {template.title or 'Длинная'} {actual_minutes} мин"

    return RenderedWorkout(
        title=title,
        text=text,
        planned_minutes=actual_minutes,
        version=version,
        micro_learning=template.micro_learning,
        video_url=template.video_url,
        media_id=template.media_id,
    )


def _build_context(minutes: int, template: "WorkoutTemplate") -> dict:
    """Готовит словарь плейсхолдеров для подстановки в шаблон."""
    warmup = min(15, round_int(minutes * 0.20))
    cooldown = min(15, round_int(minutes * 0.15))
    main = max(5, minutes - warmup - cooldown)

    return {
        "minutes": minutes,
        "warmup_minutes": warmup,
        "main_minutes": main,
        "cooldown_minutes": cooldown,
        "total_minutes": minutes,
    }


def _substitute(text: str, ctx: dict) -> str:
    """Безопасная подстановка плейсхолдеров {minutes}, {warmup_minutes} и т.п."""
    try:
        return text.format(**ctx)
    except (KeyError, ValueError):
        # Если шаблон содержит неизвестные плейсхолдеры — оставляем как есть
        return text


def _render_light_instead_of_intensity(minutes: int, template: "WorkoutTemplate") -> str:
    """
    Когда Light заменяет интенсивную тренировку (tempo/intervals) —
    рендерим как лёгкий аэробный бег.
    """
    return (
        f"Сегодня вместо интенсивной тренировки — лёгкий бег.\n\n"
        f"🏃 {minutes} мин в лёгком темпе (Z1-Z2, разговорный темп).\n"
        f"Разминка: 5 мин шаг, заминка: 5 мин шаг.\n\n"
        f"Без ускорений и темповых отрезков — дай телу восстановиться."
    )


def render_rest_day() -> RenderedWorkout:
    """Быстрый рендер для дня отдыха без шаблона."""
    return RenderedWorkout(
        title="День отдыха 🛌",
        text="Сегодня полный отдых. Можно лёгкая мобильность по желанию.",
        planned_minutes=0,
        version="rest",
    )


def render_recovery_day() -> RenderedWorkout:
    """Быстрый рендер для дня восстановления без шаблона."""
    return RenderedWorkout(
        title="Восстановление 🚶",
        text=(
            "Сегодня вместо тренировки — восстановление.\n\n"
            "🚶 Прогулка 20–30 мин в лёгком темпе (Z1).\n"
            "По желанию: растяжка или мобильность 10–15 мин."
        ),
        planned_minutes=25,
        version="recovery",
    )
