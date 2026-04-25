"""
Pre-written check-in interpretation texts shown to the user after morning check-in.
All text lives in texts.py → T.interpretations.
"""

from texts import T


def get_interpretation(version: str, checkin_wellbeing: int, red_flag: bool, fatigue_reduction: bool) -> str:
    """Return the right interpretation text based on rule engine output."""
    if version == "rest":
        return T.interpretations.rest
    if red_flag:
        return T.interpretations.red_flag
    if fatigue_reduction:
        if version == "recovery":
            return T.interpretations.fatigue_recovery
        return T.interpretations.fatigue_light
    if version == "recovery":
        return T.interpretations.red_flag  # recovery without explicit red flag → same message
    if version == "light":
        return T.interpretations.light_wellbeing
    # base
    if checkin_wellbeing >= 4:
        return T.interpretations.base_great
    return T.interpretations.base_ok
