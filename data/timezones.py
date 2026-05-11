"""
Timezone options for onboarding keyboard.
Each entry: (utc_offset, display_label, callback_value)
"""

TIMEZONES: list[dict] = [
    # ── Северная и Южная Америка ──────────────────────────────────────────────
    {"offset": -10, "label": "UTC−10 — Гавайи"},
    {"offset": -9,  "label": "UTC−9  — Аляска"},
    {"offset": -8,  "label": "UTC−8  — Лос-Анджелес, Ванкувер (PST)"},
    {"offset": -7,  "label": "UTC−7  — Денвер, Феникс (MST)"},
    {"offset": -6,  "label": "UTC−6  — Чикаго, Мехико (CST)"},
    {"offset": -5,  "label": "UTC−5  — Нью-Йорк, Торонто (EST)"},
    {"offset": -4,  "label": "UTC−4  — Галифакс, Каракас"},
    {"offset": -3,  "label": "UTC−3  — Сан-Паулу, Буэнос-Айрес"},
    # ── Европа ────────────────────────────────────────────────────────────────
    {"offset": 0,   "label": "UTC+0  — Лондон, Лиссабон"},
    {"offset": 1,   "label": "UTC+1  — Берлин, Париж, Варшава"},
    {"offset": 2,   "label": "UTC+2  — Калининград"},
    {"offset": 3,   "label": "UTC+3  — Москва, Питер, Минск"},
    # ── Ближний Восток и Азия ─────────────────────────────────────────────────
    {"offset": 4,   "label": "UTC+4  — Самара, Баку, ОАЭ"},
    {"offset": 5,   "label": "UTC+5  — Екатеринбург, Ташкент"},
    {"offset": 6,   "label": "UTC+6  — Омск, Алматы"},
    {"offset": 7,   "label": "UTC+7  — Красноярск, Новосибирск, Бангкок"},
    {"offset": 8,   "label": "UTC+8  — Иркутск, Пекин, Сингапур"},
    {"offset": 9,   "label": "UTC+9  — Якутск, Токио, Сеул"},
    {"offset": 10,  "label": "UTC+10 — Владивосток"},
    {"offset": 11,  "label": "UTC+11 — Магадан, Сахалин"},
    {"offset": 12,  "label": "UTC+12 — Камчатка"},
]
