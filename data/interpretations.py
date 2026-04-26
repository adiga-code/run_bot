"""
Pre-written check-in interpretation texts shown to the user after morning check-in.
All text lives in texts.py → T.interpretations.
"""

from texts import T


def get_interpretation(version: str, checkin_wellbeing: int, red_flag: bool, fatigue_reduction: bool) -> str:
    """
    Return the right interpretation text based on rule engine output.

    Priority (mirrors rule_engine.py):
      rest            → rest
      red_flag        → red_flag or persistent_pain
      pain=3          → red_flag  (handled by red_flag=True above)
      fatigue→recovery → fatigue
      pain=2          → light_pain
      pain recovery   → light_pain_recovery  (fatigue_reduction=True, version=light)
      wellbeing=1     → light_wellbeing
      sleep/stress    → light_sleep
      fatigue→light   → fatigue_light
      base, great wb  → base_great
      base, ok wb     → base_ok
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
            return T.interpretations.light_pain_recovery
        if checkin_wellbeing == 1:
            return T.interpretations.light_wellbeing
        return T.interpretations.light_sleep

    # base
    if checkin_wellbeing >= 3:
        return T.interpretations.base_great
    return T.interpretations.base_ok
