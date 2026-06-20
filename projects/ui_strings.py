"""Bilingual UI labels for navigation and settings."""

from __future__ import annotations

LANGUAGE_EL = "el"
LANGUAGE_EN = "en"

_LABELS: dict[str, dict[str, str]] = {
    "nav_dashboard": {"el": "Dashboard", "en": "Dashboard"},
    "nav_projects": {"el": "Έργα", "en": "Projects"},
    "nav_customers": {"el": "Πελάτες", "en": "Customers"},
    "nav_quotes": {"el": "Προσφορές", "en": "Quotes"},
    "nav_calendar": {"el": "Ημερολόγιο", "en": "Calendar"},
    "nav_operational": {"el": "Λειτουργικά", "en": "Operational"},
    "nav_reports": {"el": "Αναφορές", "en": "Reports"},
    "nav_admin": {"el": "Διαχείριση", "en": "Admin"},
    "nav_logout": {"el": "Αποσύνδεση", "en": "Log out"},
    "nav_settings": {"el": "Ρυθμίσεις", "en": "Settings"},
    "nav_menu": {"el": "Μενού", "en": "Menu"},
    "settings_title": {"el": "Ρυθμίσεις", "en": "Settings"},
    "settings_subtitle": {
        "el": "Γλώσσα και εμφάνιση για τον λογαριασμό σου.",
        "en": "Language and appearance for your account.",
    },
    "settings_language": {"el": "Γλώσσα", "en": "Language"},
    "settings_dark_mode": {"el": "Dark mode", "en": "Dark mode"},
    "settings_dark_mode_help": {
        "el": "Σκούρο φόντο και ανοιχτό κείμενο σε όλη την εφαρμογή.",
        "en": "Dark background and light text across the app.",
    },
    "settings_save": {"el": "Αποθήκευση", "en": "Save"},
    "settings_saved": {"el": "Οι ρυθμίσεις αποθηκεύτηκαν.", "en": "Settings saved."},
    "settings_account": {"el": "Λογαριασμός", "en": "Account"},
}


class UIStrings:
    __slots__ = ("lang",)

    def __init__(self, lang: str = LANGUAGE_EL):
        self.lang = LANGUAGE_EN if lang == LANGUAGE_EN else LANGUAGE_EL

    def get(self, key: str, default: str = "") -> str:
        entry = _LABELS.get(key)
        if not entry:
            return default or key
        return entry.get(self.lang) or entry[LANGUAGE_EL]

    def __getattr__(self, key: str) -> str:
        return self.get(key)


def get_ui(lang: str = LANGUAGE_EL) -> UIStrings:
    return UIStrings(lang)
