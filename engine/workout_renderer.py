"""
engine/workout_renderer.py

Рендер тренировок для новой цикловой системы.

Беговые тренировки генерируются АВТОМАТИЧЕСКИ из constants.py —
никакого шаблона в БД не нужно.

Силовые тренировки берутся из WorkoutTemplate (gym/home, конкретные упражнения).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from engine import constants as C
from engine.constants import LIGHT_VOLUME_MULTIPLIER, round_int

if TYPE_CHECKING:
    from database.models import WorkoutTemplate


@dataclass
class RenderedWorkout:
    title: str
    text: str
    planned_minutes: int
    version: str
    micro_learning: str | None = None
    video_url: str | None = None
    media_id: str | None = None


# ═════════════════════════════════════════════════════════════════════════════
# Публичный API
# ═════════════════════════════════════════════════════════════════════════════

def render_run_workout(
    run_subtype: str,
    target_minutes: int,
    version: str,
    level: int,
    period: str | None,
    long_stage: int = 1,
) -> RenderedWorkout:
    """
    Генерирует беговую тренировку из constants.py.
    Не требует WorkoutTemplate в БД.

    version:
        base     — полный объём
        light    — −20%, для tempo/intervals заменяем на лёгкий бег
        recovery — прогулка 20-30 мин Z1 (игнорирует subtype и minutes)
        rest     — день отдыха
    """
    if version == "rest":
        return render_rest_day()
    if version == "recovery":
        return render_recovery_day()

    # Light: уменьшаем объём, интенсивные → лёгкий бег
    if version == "light":
        actual = round_int(target_minutes * LIGHT_VOLUME_MULTIPLIER)
        if run_subtype in ("tempo", "intervals"):
            return _render_easy(actual, level, label_prefix="[Лайт] ")
    else:
        actual = target_minutes

    match run_subtype:
        case "long":
            return _render_long(actual, level, period, long_stage, version)
        case "aerobic":
            return _render_aerobic(actual, level, version)
        case "easy":
            return _render_easy(actual, level)
        case "recovery_run":
            return _render_recovery_run(actual)
        case "run_walk":
            return _render_run_walk(actual, level)
        case "tempo":
            return _render_tempo(actual, level, period, version)
        case "intervals":
            return _render_intervals(actual, level, period, version)
        case _:
            return _render_easy(actual, level)


def render_strength_from_template(
    template: "WorkoutTemplate",
    target_minutes: int,
    version: str,
) -> RenderedWorkout:
    """
    Силовая тренировка из WorkoutTemplate.
    Текст берётся из БД — там конкретные упражнения, подходы, повторения.
    """
    if version == "rest":
        return render_rest_day()
    if version == "recovery":
        return render_recovery_day()

    if version == "light":
        actual = round_int(target_minutes * LIGHT_VOLUME_MULTIPLIER)
        prefix = "[Лайт] "
    else:
        actual = target_minutes
        prefix = ""

    ctx = _build_context(actual, template)
    text = _substitute(template.text or "", ctx)
    title = prefix + (template.title or "Силовая")

    return RenderedWorkout(
        title=title,
        text=text,
        planned_minutes=actual,
        version=version,
        micro_learning=template.micro_learning,
        video_url=template.video_url,
        media_id=template.media_id,
    )


def render_rest_day() -> RenderedWorkout:
    return RenderedWorkout(
        title="День отдыха 🛌",
        text="Сегодня полный отдых. По желанию — лёгкая мобильность или растяжка.",
        planned_minutes=0,
        version="rest",
    )


def render_recovery_day() -> RenderedWorkout:
    return RenderedWorkout(
        title="Восстановление 🚶",
        text=(
            "Сегодня вместо тренировки — восстановление.\n\n"
            "🚶 Прогулка 20–30 мин в лёгком темпе (Z1 — очень легко, можно петь).\n"
            "По желанию: растяжка или мобильность 10–15 мин.\n\n"
            "Никакого бега и силовых сегодня — тело восстанавливается."
        ),
        planned_minutes=25,
        version="recovery",
    )


# ═════════════════════════════════════════════════════════════════════════════
# Генераторы по типам бега
# ═════════════════════════════════════════════════════════════════════════════

def _render_easy(minutes: int, level: int, label_prefix: str = "") -> RenderedWorkout:
    warmup, main, cooldown = _split_wmc(minutes)
    zone = "Z1-Z2 — разговорный темп" if level == 1 else "Z2 — можно говорить короткими фразами"
    text = (
        f"🦶 Разминка: {warmup} мин ходьба\n"
        f"🏃 Лёгкий бег: {main} мин ({zone})\n"
        f"🦶 Заминка: {cooldown} мин ходьба\n\n"
        f"⏱ Итого: {minutes} мин"
    )
    return RenderedWorkout(
        title=f"{label_prefix}Лёгкий бег {minutes} мин",
        text=text,
        planned_minutes=minutes,
        version="light" if label_prefix else "base",
        micro_learning="Лёгкий бег в разговорном темпе развивает аэробную базу и ускоряет восстановление.",
    )


def _render_aerobic(minutes: int, level: int, version: str) -> RenderedWorkout:
    warmup, main, cooldown = _split_wmc(minutes)
    if level == 2:
        zone = "Z2 — можно говорить короткими фразами"
        tip = "Аэробный бег укрепляет сердце и развивает выносливость без накопления усталости."
    else:
        zone = "Z2 — аэробный темп, короткие фразы"
        tip = "Основная зона тренировок. Z2 формирует аэробный движок — основу всей скорости."

    text = (
        f"🦶 Разминка: {warmup} мин ходьба или лёгкий бег\n"
        f"🏃 Аэробный бег: {main} мин ({zone})\n"
        f"🦶 Заминка: {cooldown} мин ходьба\n\n"
        f"⏱ Итого: {minutes} мин"
    )
    prefix = "[Лайт] " if version == "light" else ""
    return RenderedWorkout(
        title=f"{prefix}Аэробный бег {minutes} мин",
        text=text,
        planned_minutes=minutes,
        version=version,
        micro_learning=tip,
    )


def _render_long(
    minutes: int, level: int, period: str | None, long_stage: int, version: str,
) -> RenderedWorkout:
    warmup = min(15, round_int(minutes * 0.15))
    cooldown = min(15, round_int(minutes * 0.15))
    main = max(10, minutes - warmup - cooldown)

    if level == 1 and long_stage == 1:
        zone_note = "Z1-Z2 — бег/шаг чередование, без усилия"
        tip = "Длинный бег развивает выносливость. На этом этапе можно чередовать бег и шаг."
    else:
        zone_note = "Z1-Z2 — очень легко, разговорный темп"
        tip = "Длинный бег — ключевая тренировка недели. Темп должен быть очень комфортным."

    text = (
        f"🦶 Разминка: {warmup} мин ходьба\n"
        f"🏃 Длинный бег: {main} мин ({zone_note})\n"
        f"🦶 Заминка + растяжка: {cooldown} мин\n\n"
        f"⏱ Итого: {minutes} мин\n\n"
        f"⭐ Ключевая тренировка недели — не торопись, держи лёгкий темп."
    )
    prefix = "[Лайт] " if version == "light" else ""
    return RenderedWorkout(
        title=f"{prefix}Длинный бег {minutes} мин",
        text=text,
        planned_minutes=minutes,
        version=version,
        micro_learning=tip,
    )


def _render_recovery_run(minutes: int) -> RenderedWorkout:
    text = (
        f"🚶 Восстановительная пробежка: {minutes} мин\n\n"
        f"Очень лёгкий темп — Z1, можно петь.\n"
        f"Если тяжело — замени на прогулку.\n\n"
        f"Цель: размяться, не нагружаться."
    )
    return RenderedWorkout(
        title=f"Восстановительный бег {minutes} мин",
        text=text,
        planned_minutes=minutes,
        version="base",
        micro_learning="Восстановительный бег снимает молочную кислоту и ускоряет восстановление мышц.",
    )


def _render_run_walk(minutes: int, level: int) -> RenderedWorkout:
    cycle = 3  # 1 мин бег + 2 мин шаг
    cycles = max(4, minutes // cycle)
    actual = cycles * cycle
    text = (
        f"Бег/шаг интервалы:\n\n"
        f"🔁 {cycles} × (1 мин бег + 2 мин шаг)\n"
        f"⏱ Итого: ~{actual} мин\n\n"
        f"Бег — очень лёгкий темп (Z1), шаг — обычная ходьба.\n"
        f"Если чувствуешь усталость — добавь шаг, убери один интервал."
    )
    return RenderedWorkout(
        title=f"Бег/шаг {actual} мин",
        text=text,
        planned_minutes=actual,
        version="base",
        micro_learning="Чередование бега и ходьбы — лучший способ начать бегать без перегрузки.",
    )


def _render_tempo(minutes: int, level: int, period: str | None, version: str) -> RenderedWorkout:
    s = C.L3_REGULAR_TEMPO_STRUCTURE if level == 3 else C.L2_TEMPO_STRUCTURE
    warmup, cooldown = s["warmup"], s["cooldown"]
    main = max(s["main_min"], min(s["main_max"], minutes - warmup - cooldown))
    total = warmup + main + cooldown
    zone = _zone_label(s["main_zone"])

    text = (
        f"🦶 Разминка: {warmup} мин лёгкий бег (Z1-Z2)\n"
        f"⚡ Темповый бег: {main} мин ({zone})\n"
        f"🦶 Заминка: {cooldown} мин лёгкий бег\n\n"
        f"⏱ Итого: {total} мин\n\n"
        f"Темп — ощущение «сложно, но контролируемо». "
        f"Можешь говорить только отдельные слова."
    )
    return RenderedWorkout(
        title=f"Темповый бег {total} мин",
        text=text,
        planned_minutes=total,
        version=version,
        micro_learning="Темповый бег поднимает лактатный порог — ты учишься бежать быстрее при той же нагрузке.",
    )


def _render_intervals(minutes: int, level: int, period: str | None, version: str) -> RenderedWorkout:
    if level == 3:
        s = C.L3_REGULAR_INTERVALS_PREP if period == "preparatory" else C.L3_REGULAR_INTERVALS_BASE
    else:
        s = C.L2_INTERVALS_STRUCTURE

    warmup, cooldown = s["warmup"], s["cooldown"]
    rep_dur = (s["rep_duration_min"] + s["rep_duration_max"]) // 2
    rest_dur = (s["rest_min"] + s["rest_max"]) // 2
    cycle = rep_dur + rest_dur
    available = max(0, minutes - warmup - cooldown)
    reps = max(s["reps_min"], min(s["reps_max"], available // cycle))
    total = warmup + reps * cycle + cooldown

    zone_rep = _zone_label(s["rep_zone"])
    zone_rest = _zone_label(s["rest_zone"])

    text = (
        f"🦶 Разминка: {warmup} мин лёгкий бег (Z1-Z2)\n"
        f"⚡ Интервалы: {reps} × {rep_dur} мин ({zone_rep})\n"
        f"   Отдых: {rest_dur} мин трусца ({zone_rest})\n"
        f"🦶 Заминка: {cooldown} мин лёгкий бег\n\n"
        f"⏱ Итого: ~{total} мин\n\n"
        f"Интервалы — тяжело, но не до отказа. "
        f"После каждого должна оставаться пара повторений в запасе."
    )
    return RenderedWorkout(
        title=f"Интервалы {reps}×{rep_dur} мин",
        text=text,
        planned_minutes=total,
        version=version,
        micro_learning="Интервальный бег развивает МПК (VO2max) — твой потолок скорости.",
    )


# ═════════════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════════════

def _split_wmc(minutes: int) -> tuple[int, int, int]:
    warmup = min(15, round_int(minutes * 0.20))
    cooldown = min(15, round_int(minutes * 0.15))
    main = max(5, minutes - warmup - cooldown)
    return warmup, main, cooldown


def _zone_label(zone: str) -> str:
    return {
        "z1":       "Z1 — очень легко",
        "z1_z2":    "Z1-Z2 — разговорный темп",
        "z2":       "Z2 — короткие фразы",
        "z3":       "Z3 — сложно разговаривать",
        "z3_z4":    "Z3-Z4 — тяжело",
        "z4":       "Z4 — очень тяжело",
        "z3.5_z4":  "Z3.5-Z4 — почти максимально",
    }.get(zone.lower(), zone.upper())


def _build_context(minutes: int, template: "WorkoutTemplate") -> dict:
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
    try:
        return text.format(**ctx)
    except (KeyError, ValueError):
        return text


# ═════════════════════════════════════════════════════════════════════════════
# Обратная совместимость — старая 28-дневная система (L4/L5)
# ═════════════════════════════════════════════════════════════════════════════

def render_workout(
    template: "WorkoutTemplate",
    target_minutes: int,
    version: str,
    intensity_kind: str | None = None,
    long_stage: int | None = None,
) -> RenderedWorkout:
    """Используется только для старой 28-дневной системы (L4/L5)."""
    if version == "rest":
        return render_rest_day()
    if version == "recovery":
        return render_recovery_day()

    if version == "light":
        actual = round_int(target_minutes * LIGHT_VOLUME_MULTIPLIER)
        is_intensity = intensity_kind in ("tempo", "intervals") or (
            getattr(template, "run_subtype", None) in ("tempo", "intervals")
        )
        if is_intensity:
            return _render_easy(actual, level=2)
    else:
        actual = target_minutes

    ctx = _build_context(actual, template)
    text = _substitute(template.text or "", ctx)
    prefix = "[Лайт] " if version == "light" else ""

    return RenderedWorkout(
        title=prefix + (template.title or "Тренировка"),
        text=text,
        planned_minutes=actual,
        version=version,
        micro_learning=template.micro_learning,
        video_url=template.video_url,
        media_id=template.media_id,
    )
