from .permissions import (
    can_access_admin,
    can_manage_business,
    can_manage_schedules,
    get_user_role,
)
from .ui_strings import LANGUAGE_EL, get_ui


def roles(request):
    if not request.user.is_authenticated:
        return {}
    role = get_user_role(request.user)
    return {
        "user_role": role,
        "can_manage_business": can_manage_business(request.user),
        "can_manage_schedules": can_manage_schedules(request.user),
        "can_access_admin": can_access_admin(request.user),
    }


def user_preferences(request):
    if not request.user.is_authenticated:
        ui = get_ui()
        return {
            "user_language": ui.lang,
            "user_dark_mode": False,
            "theme": "light",
            "ui": ui,
        }
    profile = getattr(request.user, "profile", None)
    language = profile.language if profile else LANGUAGE_EL
    dark_mode = profile.dark_mode if profile else False
    ui = get_ui(language)
    return {
        "user_language": language,
        "user_dark_mode": dark_mode,
        "theme": "dark" if dark_mode else "light",
        "ui": ui,
    }
