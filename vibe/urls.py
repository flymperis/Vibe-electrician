from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import RedirectView

_LOOKUP_OPTION_ADMIN_SLUGS = (
    "incometypeoption",
    "incomepaymenttypeoption",
    "projectexpensecategoryoption",
    "operationalexpensecategoryoption",
    "quotelinecategoryoption",
    "quoteunitoption",
)


def _legacy_lookup_admin_redirects():
    patterns = []
    for slug in _LOOKUP_OPTION_ADMIN_SLUGS:
        patterns.append(
            path(
                f"admin/projects/{slug}/",
                RedirectView.as_view(
                    url=f"/admin/configurations/{slug}/",
                    permanent=True,
                ),
            )
        )
        patterns.append(
            path(
                f"admin/projects/{slug}/<path:rest>",
                RedirectView.as_view(
                    url=f"/admin/configurations/{slug}/%(rest)s",
                    permanent=True,
                ),
            )
        )
    return patterns


def _legacy_rolepermission_admin_redirects():
    return [
        path(
            "admin/projects/rolepermission/",
            RedirectView.as_view(
                url="/admin/auth/authrole/",
                permanent=True,
                query_string=False,
            ),
        ),
        path(
            "admin/projects/rolepermission/<path:rest>",
            RedirectView.as_view(
                url="/admin/auth/authrole/",
                permanent=True,
                query_string=False,
            ),
        ),
        path(
            "admin/auth/authrolepermission/",
            RedirectView.as_view(
                url="/admin/auth/authrole/",
                permanent=True,
                query_string=False,
            ),
        ),
        path(
            "admin/auth/authrolepermission/<path:rest>",
            RedirectView.as_view(
                url="/admin/auth/authrole/",
                permanent=True,
                query_string=False,
            ),
        ),
    ]


from projects.auth_views import RoleLoginView

urlpatterns = [
    *_legacy_lookup_admin_redirects(),
    *_legacy_rolepermission_admin_redirects(),
    path("admin/", admin.site.urls),
    path("", include("projects.urls")),
    path("export/", include("reports.urls")),
    path("login/", RoleLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "Vibe Electrician"
admin.site.site_title = "Vibe Electrician"
admin.site.index_title = "Διαχείριση"
