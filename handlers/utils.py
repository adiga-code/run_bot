import logging

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

logger = logging.getLogger(__name__)


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
