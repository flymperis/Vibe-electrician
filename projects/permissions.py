"""Ρόλοι χρηστών και έλεγχος πρόσβασης."""

from __future__ import annotations

from functools import lru_cache, wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse

from .role_permissions import (
    PERM_ACCESS_DJANGO_ADMIN,
    PERM_MANAGE_SCHEDULES,
    PERM_VIEW_CALENDAR,
    PERM_VIEW_DASHBOARD,
)

ROLE_ADMIN = "admin"
ROLE_OWNER = "owner"
ROLE_WORKER = "worker"


def clear_permission_cache() -> None:
    _role_permissions_snapshot.cache_clear()


@lru_cache(maxsize=1)
def _role_permissions_snapshot() -> dict[str, dict[str, bool]]:
    from .models import RolePermission

    snapshot: dict[str, dict[str, bool]] = {}
    for row in RolePermission.objects.select_related("role").values(
        "role__code", "permission", "allowed"
    ):
        snapshot.setdefault(row["role__code"], {})[row["permission"]] = row["allowed"]
    return snapshot


def get_user_profile(user):
    from .models import UserProfile

    try:
        return user.profile
    except UserProfile.DoesNotExist:
        return None


def user_must_change_password(user) -> bool:
    profile = get_user_profile(user)
    return bool(profile and profile.must_change_password)


def get_user_role(user) -> str | None:
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return ROLE_ADMIN
    profile = get_user_profile(user)
    if profile is None or profile.role_id is None:
        return ROLE_WORKER
    return profile.role.code


def has_permission(user, permission_code: str) -> bool:
    if not user.is_authenticated or not permission_code:
        return False
    role = get_user_role(user)
    if role is None:
        return False
    if role == ROLE_ADMIN and user.is_superuser:
        return True
    role_perms = _role_permissions_snapshot().get(role, {})
    if permission_code in role_perms:
        return role_perms[permission_code]
    return False


def can_manage_business(user) -> bool:
    return has_permission(user, PERM_VIEW_DASHBOARD)


def can_access_admin(user) -> bool:
    return has_permission(user, PERM_ACCESS_DJANGO_ADMIN)


def can_manage_schedules(user) -> bool:
    return has_permission(user, PERM_MANAGE_SCHEDULES)


def can_view_calendar(user) -> bool:
    return has_permission(user, PERM_VIEW_CALENDAR)


def get_login_redirect_url(user) -> str:
    if can_view_calendar(user) and not can_manage_business(user):
        return reverse("projects:work_calendar")
    return reverse("projects:dashboard")


def user_display_name(user) -> str:
    if not user:
        return "—"
    profile = get_user_profile(user)
    if profile is not None:
        return profile.display_name
    full = (user.get_full_name() or "").strip()
    return full or user.username


def assignable_workers_queryset():
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return (
        User.objects.filter(is_active=True, profile__role__is_assignable=True)
        .select_related("profile", "profile__role")
        .order_by("first_name", "last_name", "username")
    )


def owner_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not can_manage_business(request.user):
            messages.error(request, "Δεν έχεις δικαίωμα πρόσβασης σε αυτή τη σελίδα.")
            return redirect(get_login_redirect_url(request.user))
        return view_func(request, *args, **kwargs)

    return wrapped


def schedule_manager_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not can_manage_schedules(request.user):
            messages.error(request, "Δεν έχεις δικαίωμα να επεξεργαστείς εργασίες.")
            return redirect("projects:work_calendar")
        return view_func(request, *args, **kwargs)

    return wrapped
