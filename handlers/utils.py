import json
import logging
import os

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

logger = logging.getLogger(__name__)

_TIPS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "day_tips.json")
with open(_TIPS_PATH, encoding="utf-8") as _f:
    _DAY_TIPS: dict = json.load(_f)


def get_tip_lines(level: int, day: int) -> str:
    tip = _DAY_TIPS.get(str(level), {}).get(str(day), {})
    motivation = tip.get("motivation", "")
    hint = tip.get("tip", "")
    parts = []
    if motivation:
        parts.append(f"💬 <i>{motivation}</i>")
    if hint:
        parts.append(f"🤍 <i>{hint}</i>")
    return "\n".join(parts)


async def send_workout_to_user(
    bot: Bot,
    user_id: int,
    day_index: int,
    workout,
    day_type: str,
    version: str,
    strength_format: str | None,
    level: int,
    calendar_day: int | None = None,
) -> None:
    """Send the final workout message to the user.

    day_index   — template day (1-28), used for tips lookup and workout context.
    calendar_day — display day shown to user as "День X из 28".
                   Falls back to day_index when not provided.
    """
    from keyboards.builders import kb_completion, kb_completion_strength
    workout_text = filter_strength_text(
        workout.text,
        strength_format if day_type == "strength" else None,
    )
    is_strength = day_type == "strength" and version != "recovery"
    tips = get_tip_lines(level, day_index)  # tips keyed by template day
    tips_block = f"\n\n{tips}" if tips else ""
    display_day = calendar_day if calendar_day is not None else day_index
    await bot.send_message(
        chat_id=user_id,
        text=f"📋 <b>День {display_day} из 28 — {workout.title}</b>{tips_block}\n\n{workout_text}",
        parse_mode="HTML",
        reply_markup=kb_completion_strength() if is_strength else kb_completion(),
    )


async def safe_answer(callback: CallbackQuery, text: str = "", show_alert: bool = False) -> None:
    """Answer a callback query, silently ignoring expired-query errors."""
    try:
        await callback.answer(text, show_alert=show_alert)
    except TelegramBadRequest as e:
        if "query is too old" in str(e) or "query ID is invalid" in str(e):
            logger.warning("Expired callback query %s ignored", callback.id)
        else:
            raise


def filter_strength_text(text: str, strength_format: str | None) -> str:
    """
    For combined gym+home strength workout texts, return only the relevant section.

    Text format expected:
        <intro line(s)>

        🏋️ Зал — ...:
        - ...

        🏠 Дома — ...:
        - ...

    If strength_format is None or neither marker is found, returns the full text.
    """
    if not strength_format:
        return text

    GYM = "🏋️"
    HOME = "🏠"

    if GYM not in text and HOME not in text:
        return text  # no format sections — return as-is

    parts = text.split("\n\n")
    intro, gym_parts, home_parts = [], [], []

    for part in parts:
        stripped = part.lstrip()
        if stripped.startswith(GYM):
            gym_parts.append(part)
        elif stripped.startswith(HOME):
            home_parts.append(part)
        else:
            intro.append(part)

    if strength_format == "gym":
        selected = gym_parts if gym_parts else []
    else:
        selected = home_parts if home_parts else []

    sections = intro + selected
    return "\n\n".join(sections).strip() if sections else text
