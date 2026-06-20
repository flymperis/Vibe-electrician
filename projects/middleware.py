from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import Resolver404, resolve

from .permissions import (
    can_access_admin,
    get_login_redirect_url,
    has_permission,
    user_must_change_password,
)
from .role_permissions import URL_PERMISSION_MAP

_PASSWORD_CHANGE_ALLOWED_URLS = frozenset({"password_change_required", "logout"})


class RoleAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            path = request.path

            if user_must_change_password(request.user):
                if not path.startswith("/static/") and not path.startswith(
                    settings.MEDIA_URL
                ):
                    try:
                        match = resolve(path)
                        if match.url_name not in _PASSWORD_CHANGE_ALLOWED_URLS:
                            return redirect("projects:password_change_required")
                    except Resolver404:
                        return redirect("projects:password_change_required")

            if path.startswith("/admin/") and not can_access_admin(request.user):
                messages.error(request, "Η διαχείριση Django είναι μόνο για admin.")
                return redirect(get_login_redirect_url(request.user))

            try:
                match = resolve(path)
            except Resolver404:
                return self.get_response(request)

            permission_code = URL_PERMISSION_MAP.get(match.url_name)
            if permission_code and not has_permission(request.user, permission_code):
                messages.error(request, "Δεν έχεις δικαίωμα πρόσβασης σε αυτή τη σελίδα.")
                return redirect(get_login_redirect_url(request.user))

        return self.get_response(request)
