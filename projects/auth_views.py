from django.contrib.auth.views import LoginView

from .permissions import get_login_redirect_url


class RoleLoginView(LoginView):
    template_name = "registration/login.html"

    def get_success_url(self):
        return get_login_redirect_url(self.request.user)
