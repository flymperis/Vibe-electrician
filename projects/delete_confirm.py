from django.contrib import messages
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme

CONFIRM_PASSWORD_FIELD = "confirm_password"


def password_confirmed_for_delete(request) -> bool:
    password = request.POST.get(CONFIRM_PASSWORD_FIELD, "")
    if not password:
        messages.error(request, "Εισάγετε τον κωδικό σας για επιβεβαίωση διαγραφής.")
        return False
    if not request.user.check_password(password):
        messages.error(request, "Λανθασμένος κωδικός. Η διαγραφή ακυρώθηκε.")
        return False
    return True


def redirect_after_failed_delete(request, *, fallback: str):
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
    ):
        return redirect(next_url)
    return redirect(fallback)
