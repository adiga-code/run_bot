"""Access control helpers — trial / paid / ambassador."""
from __future__ import annotations

from datetime import date, timedelta

TRIAL_DAYS = 10
PLAN_PRICES = {"monthly": 1990, "annual": 14990}
PLAN_DAYS = {"monthly": 28, "annual": 365}


def get_access_status(user) -> str:
    """
    Returns one of:
      'active'         — paid access is valid
      'trial'          — in trial, >2 days left
      'trial_warning'  — in trial, ≤2 days left
      'free'           — ambassador / fully free
      'expired'        — no valid access
    """
    if user.subscription_type in ("ambassador", "free"):
        return "free"

    today = date.today()

    if user.access_until and user.access_until >= today:
        return "active"

    if user.trial_started_at:
        trial_end = (user.trial_started_at.date() + timedelta(days=TRIAL_DAYS))
        days_left = (trial_end - today).days
        if days_left > 2:
            return "trial"
        if days_left >= 0:
            return "trial_warning"

    return "expired"


def has_access(user) -> bool:
    return get_access_status(user) in ("active", "trial", "trial_warning", "free")


def trial_days_left(user) -> int | None:
    if not user.trial_started_at:
        return None
    trial_end = user.trial_started_at.date() + timedelta(days=TRIAL_DAYS)
    return max(0, (trial_end - date.today()).days)
