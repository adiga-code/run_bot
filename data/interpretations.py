"""
Pre-written check-in interpretation texts shown to the user after morning check-in.
All text lives in texts.py → T.interpretations.
"""

from texts import T


def get_interpretation(
    version: str,
    checkin_wellbeing: int,
    red_flag: bool,
    fatigue_reduction: bool,
    pain_level: int = 1,
) -> str:
    """
    Return the right interpretation text based on rule engine output.

    Priority (mirrors rule_engine.py):
      rest             → rest
      red_flag         → red_flag
      fatigue→recovery → fatigue
      fatigue→light    → fatigue_light  (fatigue_reduction=True, version=light)
      pain=2           → light_pain
      wellbeing=1      → light_wellbeing
      sleep/stress     → light_sleep
      base, great wb   → base_great
      base, ok wb      → base_ok
    """
    if version == "rest":
        return T.interpretations.rest

    if red_flag:
        return T.interpretations.red_flag

    if version == "recovery":
        if fatigue_reduction:
            return T.interpretations.fatigue
        return T.interpretations.red_flag

    if version == "light":
        if fatigue_reduction:
            return T.interpretations.fatigue_light
        if pain_level == 2:
            return T.interpretations.light_pain
        if checkin_wellbeing == 1:
            return T.interpretations.light_wellbeing
        return T.interpretations.light_sleep

    # base
    if checkin_wellbeing >= 3:
        return T.interpretations.base_great
    return T.interpretations.base_ok
