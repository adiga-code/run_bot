from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.timezones import TIMEZONES
from texts import T


# ── Onboarding ────────────────────────────────────────────────────────────────

def kb_skip(callback_data: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.skip, callback_data=callback_data)
    builder.adjust(1)
    return builder.as_markup()


def kb_gender() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.gender_m, callback_data="onb:gender:m")
    builder.button(text=T.btn.gender_f, callback_data="onb:gender:f")
    builder.adjust(2)
    return builder.as_markup()


def kb_goal() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.goal_start_zero, callback_data="onb:goal:start_zero")
    builder.button(text=T.btn.goal_return,     callback_data="onb:goal:return")
    builder.button(text=T.btn.goal_distance,   callback_data="onb:goal:distance")
    builder.button(text=T.btn.goal_improve,    callback_data="onb:goal:improve")
    builder.button(text=T.btn.goal_no_pain,    callback_data="onb:goal:no_pain")
    builder.button(text=T.btn.goal_health,     callback_data="onb:goal:health")
    builder.adjust(1)
    return builder.as_markup()


def kb_distance() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.dist_5k,   callback_data="onb:distance:5k")
    builder.button(text=T.btn.dist_10k,  callback_data="onb:distance:10k")
    builder.button(text=T.btn.dist_half, callback_data="onb:distance:half")
    builder.button(text=T.btn.dist_full, callback_data="onb:distance:full")
    builder.button(text=T.btn.dist_other, callback_data="onb:distance:other")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def kb_runs() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.runs_no,        callback_data="onb:runs:no")
    builder.button(text=T.btn.runs_irregular, callback_data="onb:runs:irregular")
    builder.button(text=T.btn.runs_regular,   callback_data="onb:runs:regular")
    builder.adjust(1)
    return builder.as_markup()


def kb_frequency() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.freq_0_1,   callback_data="onb:frequency:0_1")
    builder.button(text=T.btn.freq_2_3,   callback_data="onb:frequency:2_3")
    builder.button(text=T.btn.freq_4plus, callback_data="onb:frequency:4plus")
    builder.adjust(1)
    return builder.as_markup()


def kb_volume() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.vol_to_10,  callback_data="onb:volume:to_10")
    builder.button(text=T.btn.vol_10_25,  callback_data="onb:volume:10_25")
    builder.button(text=T.btn.vol_25_50,  callback_data="onb:volume:25_50")
    builder.button(text=T.btn.vol_50plus, callback_data="onb:volume:50plus")
    builder.adjust(1)
    return builder.as_markup()


def kb_structure() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.structure_yes, callback_data="onb:structure:yes")
    builder.button(text=T.btn.structure_no,  callback_data="onb:structure:no")
    builder.adjust(1)
    return builder.as_markup()


def kb_longest_run() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.longest_to_5,   callback_data="onb:longest:to_5")
    builder.button(text=T.btn.longest_5_10,   callback_data="onb:longest:5_10")
    builder.button(text=T.btn.longest_10_15,  callback_data="onb:longest:10_15")
    builder.button(text=T.btn.longest_15plus, callback_data="onb:longest:15plus")
    builder.adjust(2)
    return builder.as_markup()


def kb_experience() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.exp_beginner, callback_data="onb:exp:beginner")
    builder.button(text=T.btn.exp_to_6m,   callback_data="onb:exp:to_6m")
    builder.button(text=T.btn.exp_6_12m,   callback_data="onb:exp:6_12m")
    builder.button(text=T.btn.exp_1_3y,    callback_data="onb:exp:1_3y")
    builder.button(text=T.btn.exp_3plus,   callback_data="onb:exp:3plus")
    builder.adjust(1)
    return builder.as_markup()


def kb_break() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.break_no,    callback_data="onb:break:no")
    builder.button(text=T.btn.break_to_1m, callback_data="onb:break:to_1m")
    builder.button(text=T.btn.break_1_3m,  callback_data="onb:break:1_3m")
    builder.button(text=T.btn.break_3_6m,  callback_data="onb:break:3_6m")
    builder.button(text=T.btn.break_6plus, callback_data="onb:break:6plus")
    builder.adjust(1)
    return builder.as_markup()


def kb_run_feel() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.feel_hard,   callback_data="onb:feel:hard")
    builder.button(text=T.btn.feel_medium, callback_data="onb:feel:medium")
    builder.button(text=T.btn.feel_easy,   callback_data="onb:feel:easy")
    builder.adjust(1)
    return builder.as_markup()


def kb_pain() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.pain_none,   callback_data="onb:pain:none")
    builder.button(text=T.btn.pain_little, callback_data="onb:pain:little")
    builder.button(text=T.btn.pain_yes,    callback_data="onb:pain:yes")
    builder.adjust(1)
    return builder.as_markup()


def kb_pain_location(selected: list[str]) -> InlineKeyboardMarkup:
    options = [
        (T.btn.pain_loc_knees,    "knees"),
        (T.btn.pain_loc_feet,     "feet"),
        (T.btn.pain_loc_shin,     "shin"),
        (T.btn.pain_loc_achilles, "achilles"),
        (T.btn.pain_loc_back,     "back"),
        (T.btn.pain_loc_other,    "other"),
    ]
    builder = InlineKeyboardBuilder()
    for label, value in options:
        prefix = "✅ " if value in selected else ""
        builder.button(text=f"{prefix}{label}", callback_data=f"onb:pain_loc:{value}")
    builder.button(text=T.btn.done_arrow, callback_data="onb:pain_loc:done")
    builder.adjust(2)
    return builder.as_markup()


def kb_injury_history() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.injury_no,  callback_data="onb:injury:no")
    builder.button(text=T.btn.injury_yes, callback_data="onb:injury:yes")
    builder.adjust(2)
    return builder.as_markup()


def kb_other_sports(selected: list[str]) -> InlineKeyboardMarkup:
    options = [
        (T.btn.sports_gym,   "gym"),
        (T.btn.sports_bike,  "bike"),
        (T.btn.sports_swim,  "swim"),
        (T.btn.sports_other, "other"),
    ]
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✅ " + T.btn.sports_none if "none" in selected else T.btn.sports_none,
        callback_data="onb:sports:none",
    )
    for label, value in options:
        prefix = "✅ " if value in selected else ""
        builder.button(text=f"{prefix}{label}", callback_data=f"onb:sports:{value}")
    builder.button(text=T.btn.done_arrow, callback_data="onb:sports:done")
    builder.adjust(2)
    return builder.as_markup()


def kb_strength_frequency() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.str_freq_no,        callback_data="onb:str_freq:no")
    builder.button(text=T.btn.str_freq_sometimes, callback_data="onb:str_freq:sometimes")
    builder.button(text=T.btn.str_freq_regularly, callback_data="onb:str_freq:regularly")
    builder.adjust(1)
    return builder.as_markup()


def kb_self_level() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.self_level_beginner, callback_data="onb:self_lvl:beginner")
    builder.button(text=T.btn.self_level_base,     callback_data="onb:self_lvl:base")
    builder.button(text=T.btn.self_level_medium,   callback_data="onb:self_lvl:medium")
    builder.button(text=T.btn.self_level_advanced, callback_data="onb:self_lvl:advanced")
    builder.adjust(1)
    return builder.as_markup()


def kb_pain_increases() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.pain_inc_no,       callback_data="onb:pain_inc:no")
    builder.button(text=T.btn.pain_inc_yes,      callback_data="onb:pain_inc:yes")
    builder.button(text=T.btn.pain_inc_not_sure, callback_data="onb:pain_inc:not_sure")
    builder.adjust(1)
    return builder.as_markup()


def kb_strength() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.str_freq_no,        callback_data="onb:strength:no")
    builder.button(text=T.btn.str_freq_sometimes, callback_data="onb:strength:sometimes")
    builder.button(text=T.btn.str_freq_regularly, callback_data="onb:strength:regularly")
    builder.adjust(1)
    return builder.as_markup()


def kb_location() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.location_home, callback_data="onb:location:home")
    builder.button(text=T.btn.location_gym,  callback_data="onb:location:gym")
    builder.adjust(2)
    return builder.as_markup()


def kb_timezone() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for tz in TIMEZONES:
        builder.button(
            text=tz["label"],
            callback_data=f"onb:tz:{tz['offset']}",
        )
    builder.adjust(1)
    return builder.as_markup()


# ── Check-in ──────────────────────────────────────────────────────────────────

def kb_wellbeing() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.wellbeing_1, callback_data="ci:wellbeing:1")
    builder.button(text=T.btn.wellbeing_2, callback_data="ci:wellbeing:2")
    builder.button(text=T.btn.wellbeing_3, callback_data="ci:wellbeing:3")
    builder.adjust(3)
    return builder.as_markup()


def kb_stress() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.stress_1, callback_data="ci:stress:1")
    builder.button(text=T.btn.stress_2, callback_data="ci:stress:2")
    builder.button(text=T.btn.stress_3, callback_data="ci:stress:3")
    builder.adjust(3)
    return builder.as_markup()


def kb_sleep() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.sleep_1, callback_data="ci:sleep:1")
    builder.button(text=T.btn.sleep_2, callback_data="ci:sleep:2")
    builder.button(text=T.btn.sleep_3, callback_data="ci:sleep:3")
    builder.adjust(3)
    return builder.as_markup()


def kb_pain_checkin() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.pain_ci_1, callback_data="ci:pain:1")
    builder.button(text=T.btn.pain_ci_2, callback_data="ci:pain:2")
    builder.button(text=T.btn.pain_ci_3, callback_data="ci:pain:3")
    builder.button(text=T.btn.pain_ci_info, callback_data="ci:pain_info")
    builder.adjust(1)
    return builder.as_markup()


def kb_yesterday_completion() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.yesterday_done,    callback_data="ci:yday:done")
    builder.button(text=T.btn.yesterday_partial, callback_data="ci:yday:partial")
    builder.button(text=T.btn.yesterday_no,      callback_data="ci:yday:skipped")
    builder.adjust(3)
    return builder.as_markup()


def kb_checkin_repeat() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.recheck_yes, callback_data="ci:recheck:yes")
    builder.button(text=T.btn.recheck_no,  callback_data="ci:recheck:no")
    builder.adjust(2)
    return builder.as_markup()


def kb_pain_increases_checkin() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.pain_inc_ci_no,       callback_data="ci:pain_inc:no")
    builder.button(text=T.btn.pain_inc_ci_yes,      callback_data="ci:pain_inc:yes")
    builder.button(text=T.btn.pain_inc_ci_not_sure, callback_data="ci:pain_inc:not_sure")
    builder.adjust(2)
    return builder.as_markup()


# ── Workout completion ────────────────────────────────────────────────────────

def kb_completion() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.completion_done,    callback_data="wk:status:done")
    builder.button(text=T.btn.completion_partial, callback_data="wk:status:partial")
    builder.button(text=T.btn.completion_skipped, callback_data="wk:status:skipped")
    builder.adjust(1)
    return builder.as_markup()


def kb_completion_strength() -> InlineKeyboardMarkup:
    """Completion buttons + custom workout option for strength days."""
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.completion_done,    callback_data="wk:status:done")
    builder.button(text=T.btn.completion_partial, callback_data="wk:status:partial")
    builder.button(text=T.btn.completion_skipped, callback_data="wk:status:skipped")
    builder.button(text=T.btn.completion_custom,  callback_data="wk:custom")
    builder.adjust(1)
    return builder.as_markup()


def kb_effort() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    labels = {
        1: T.btn.effort_1,
        2: T.btn.effort_2,
        3: T.btn.effort_3,
        4: T.btn.effort_4,
        5: T.btn.effort_5,
    }
    for i in range(1, 6):
        builder.button(text=labels[i], callback_data=f"wk:effort:{i}")
    builder.adjust(5)
    return builder.as_markup()


def kb_had_pain() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.had_pain_no,  callback_data="wk:pain:no")
    builder.button(text=T.btn.had_pain_yes, callback_data="wk:pain:yes")
    builder.adjust(2)
    return builder.as_markup()


# ── Admin approval ────────────────────────────────────────────────────────────

def kb_apply() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.apply_start, callback_data="app:start")
    builder.adjust(1)
    return builder.as_markup()


def kb_admin_application(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.adm_approve_app, callback_data=f"adm:app:approve:{user_id}")
    builder.button(text=T.btn.adm_reject_app,  callback_data=f"adm:app:reject:{user_id}")
    builder.adjust(2)
    return builder.as_markup()


def kb_admin_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.adm_pending,   callback_data="adm:menu:pending")
    builder.button(text=T.btn.adm_users,     callback_data="adm:menu:users")
    builder.button(text=T.btn.adm_reports,   callback_data="adm:menu:reports")
    builder.button(text=T.btn.adm_stats,     callback_data="adm:menu:stats")
    builder.button(text=T.btn.adm_whitelist, callback_data="adm:menu:whitelist")
    builder.button(text=T.btn.adm_broadcast, callback_data="adm:broadcast:checkin")
    builder.adjust(1)
    return builder.as_markup()


def kb_admin_report_users(users: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for u in users:
        icon = "🏁" if getattr(u, "status", None) == "completed" else ""
        label = f"{icon} {u.full_name}".strip() if icon else u.full_name
        builder.button(text=label, callback_data=f"adm:report:view:{u.telegram_id}")
    builder.button(text=T.btn.back, callback_data="adm:menu:back")
    builder.adjust(1)
    return builder.as_markup()


def kb_admin_report_actions(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.adm_download_csv, callback_data=f"adm:report:csv:{user_id}")
    builder.button(text=T.btn.adm_manage,       callback_data=f"adm:manage:{user_id}")
    builder.button(text=T.btn.back_list,         callback_data="adm:menu:reports")
    builder.adjust(1)
    return builder.as_markup()


def kb_admin_manage(user_id: int, extended: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.adm_change_mode,  callback_data=f"adm:mode:{user_id}")
    builder.button(text=T.btn.adm_jump_day,     callback_data=f"adm:jump:{user_id}")
    builder.button(text=T.btn.adm_change_level, callback_data=f"adm:pick:{user_id}")
    builder.button(text=T.btn.adm_mark_workout, callback_data=f"adm:markday:{user_id}")
    builder.button(text=T.btn.adm_send_msg,     callback_data=f"adm:msg:{user_id}")
    if not extended:
        builder.button(text=T.btn.adm_extend_week5, callback_data=f"adm:extend:{user_id}")
    else:
        builder.button(text=T.btn.adm_week5_active, callback_data=f"adm:extend:off:{user_id}")
    builder.button(text="🗑 Удалить пользователя", callback_data=f"adm:delete:{user_id}")
    builder.button(text=T.btn.back, callback_data=f"adm:report:view:{user_id}")
    builder.adjust(1)
    return builder.as_markup()


def kb_admin_delete_confirm(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить навсегда", callback_data=f"adm:delete:confirm:{user_id}")
    builder.button(text="❌ Отмена",               callback_data=f"adm:manage:{user_id}")
    builder.adjust(1)
    return builder.as_markup()


def kb_admin_mark_day_picker(user_id: int, logs: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for log in logs:
        builder.button(
            text=f"День {log.day_index} ({log.date.strftime('%d.%m')})",
            callback_data=f"adm:markday:day:{user_id}:{log.day_index}",
        )
    builder.button(text=T.btn.back, callback_data=f"adm:manage:{user_id}")
    builder.adjust(1)
    return builder.as_markup()


def kb_admin_mark_day_status(user_id: int, day_index: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.adm_mark_done,    callback_data=f"adm:markday:set:{user_id}:{day_index}:done")
    builder.button(text=T.btn.adm_mark_partial, callback_data=f"adm:markday:set:{user_id}:{day_index}:partial")
    builder.button(text=T.btn.adm_mark_skipped, callback_data=f"adm:markday:set:{user_id}:{day_index}:skipped")
    builder.button(text=T.btn.back,             callback_data=f"adm:markday:{user_id}")
    builder.adjust(1)
    return builder.as_markup()


def kb_checkin_approve(user_id: int) -> InlineKeyboardMarkup:
    """Sent to admin after user completes check-in — choose workout version."""
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.adm_ci_base,     callback_data=f"adm:ca:{user_id}:base")
    builder.button(text=T.btn.adm_ci_light,    callback_data=f"adm:ca:{user_id}:light")
    builder.button(text=T.btn.adm_ci_recovery, callback_data=f"adm:ca:{user_id}:recovery")
    builder.button(text=T.btn.adm_ci_rest,     callback_data=f"adm:ca:{user_id}:rest")
    builder.adjust(2)
    return builder.as_markup()


def kb_admin_day_mode(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.adm_mode_base,     callback_data=f"adm:mode:set:{user_id}:base")
    builder.button(text=T.btn.adm_mode_light,    callback_data=f"adm:mode:set:{user_id}:light")
    builder.button(text=T.btn.adm_mode_recovery, callback_data=f"adm:mode:set:{user_id}:recovery")
    builder.button(text=T.btn.back,              callback_data=f"adm:manage:{user_id}")
    builder.adjust(1)
    return builder.as_markup()


def kb_admin_approve(user_id: int, level: int) -> InlineKeyboardMarkup:
    """Sent to admin when a new user completes onboarding."""
    level_names = {1: "Start", 2: "Return", 3: "Base", 4: "Stability", 5: "Performance"}
    name = level_names[level]
    builder = InlineKeyboardBuilder()
    builder.button(
        text=T.btn.adm_start_today_fmt.format(level=level, name=name),
        callback_data=f"adm:approve:today:{user_id}:{level}",
    )
    builder.button(
        text=T.btn.adm_start_tomorrow_fmt.format(level=level, name=name),
        callback_data=f"adm:approve:tomorrow:{user_id}:{level}",
    )
    builder.button(text=T.btn.adm_edit_level, callback_data=f"adm:pick:{user_id}")
    builder.adjust(1)
    return builder.as_markup()


def kb_admin_start_choice(user_id: int, level: int) -> InlineKeyboardMarkup:
    """After admin picks a custom level — choose start date."""
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.adm_start_today,    callback_data=f"adm:approve:today:{user_id}:{level}")
    builder.button(text=T.btn.adm_start_tomorrow, callback_data=f"adm:approve:tomorrow:{user_id}:{level}")
    builder.adjust(2)
    return builder.as_markup()


def kb_admin_level_picker(user_id: int) -> InlineKeyboardMarkup:
    """Level selector for admin to override auto-detected level."""
    level_names = {1: "Start", 2: "Return", 3: "Base", 4: "Stability", 5: "Performance"}
    builder = InlineKeyboardBuilder()
    for lvl, name in level_names.items():
        builder.button(text=f"{lvl} — {name}", callback_data=f"adm:setlvl:{user_id}:{lvl}")
    builder.adjust(1)
    return builder.as_markup()


# ── Evening reminder mark button ──────────────────────────────────────────────

def kb_mark_workout() -> InlineKeyboardMarkup:
    """Single button for evening reminder — triggers the completion FSM."""
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.mark_workout, callback_data="wk:mark")
    builder.adjust(1)
    return builder.as_markup()


# ── Strength day options ──────────────────────────────────────────────────────

def kb_strength_day_options() -> InlineKeyboardMarkup:
    """Shown after strength workout is displayed: mark it or do a custom workout."""
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.mark_workout,        callback_data="wk:mark")
    builder.button(text=T.btn.completion_custom,   callback_data="wk:custom")
    builder.button(text=T.btn.menu_progress,       callback_data="menu:progress")
    builder.button(text=T.btn.menu_reminders,      callback_data="menu:reminders")
    builder.adjust(1)
    return builder.as_markup()


# ── Progress / Main menu ──────────────────────────────────────────────────────

def kb_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.menu_today,     callback_data="menu:today")
    builder.button(text=T.btn.menu_progress,  callback_data="menu:progress")
    builder.button(text=T.btn.menu_reminders, callback_data="menu:reminders")
    builder.adjust(1)
    return builder.as_markup()


def kb_progress_menu() -> InlineKeyboardMarkup:
    """Progress view with reset day option."""
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.menu_reset_day, callback_data="menu:reset_day")
    builder.button(text=T.btn.menu_today,     callback_data="menu:today")
    builder.button(text=T.btn.menu_reminders, callback_data="menu:reminders")
    builder.adjust(1)
    return builder.as_markup()


def kb_reschedule() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T.btn.reschedule, callback_data="wk:reschedule")
    builder.button(text=T.btn.keep,       callback_data="wk:keep")
    builder.adjust(1)
    return builder.as_markup()
