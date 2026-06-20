from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from .permissions import get_login_redirect_url, get_user_profile, user_must_change_password


class RoleLoginView(LoginView):
    template_name = "registration/login.html"

    def get_success_url(self):
        if user_must_change_password(self.request.user):
            return reverse("projects:password_change_required")
        return get_login_redirect_url(self.request.user)


@login_required
def password_change_required(request):
    profile = get_user_profile(request.user)
    if not profile or not profile.must_change_password:
        return redirect(get_login_redirect_url(request.user))

    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            profile.must_change_password = False
            profile.save(update_fields=["must_change_password"])
            messages.success(request, "Ο κωδικός ενημερώθηκε.")
            return redirect(get_login_redirect_url(request.user))
    else:
        form = PasswordChangeForm(request.user)

    return render(
        request,
        "registration/password_change_required.html",
        {"form": form},
    )
