from django.urls import path

from . import views
from .auth_views import password_change_required

app_name = "projects"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("erga/", views.project_list, name="project_list"),
    path("pelates/", views.customer_list, name="customer_list"),
    path("pelates/neo/", views.customer_create, name="customer_create"),
    path("pelates/<int:pk>/", views.customer_detail, name="customer_detail"),
    path("pelates/<int:pk>/epexergasia/", views.customer_edit, name="customer_edit"),
    path("pelates/<int:pk>/apenergopoihsi/", views.customer_deactivate, name="customer_deactivate"),
    path("pelates/<int:pk>/json/", views.customer_json, name="customer_json"),
    path("pelates/search/", views.customer_search, name="customer_search"),
    path("erga/neo/", views.project_create, name="project_create"),
    path("ergo/<int:pk>/", views.project_detail, name="project_detail"),
    path("ergo/<int:pk>/epexergasia/", views.project_edit, name="project_edit"),
    path("ergo/<int:pk>/katastasi/", views.project_update_status, name="project_update_status"),
    path("ergo/<int:pk>/diagrafi/", views.project_delete, name="project_delete"),
    path(
        "ergo/<int:project_pk>/esodo/<int:pk>/epexergasia/",
        views.project_income_edit,
        name="project_income_edit",
    ),
    path(
        "ergo/<int:project_pk>/esodo/<int:pk>/diagrafi/",
        views.project_income_delete,
        name="project_income_delete",
    ),
    path(
        "ergo/<int:project_pk>/exodo/<int:pk>/epexergasia/",
        views.project_expense_edit,
        name="project_expense_edit",
    ),
    path(
        "ergo/<int:project_pk>/exodo/<int:pk>/diagrafi/",
        views.project_expense_delete,
        name="project_expense_delete",
    ),
    path("exoda-ergou/prosthiiki/", views.add_project_expense, name="add_project_expense"),
    path("litourgika-exoda/", views.operational_expenses, name="operational_expenses"),
    path("imerologio/", views.work_calendar, name="work_calendar"),
    path("imerologio/neo/", views.work_schedule_create, name="work_schedule_create"),
    path("imerologio/<int:pk>/epexergasia/", views.work_schedule_edit, name="work_schedule_edit"),
    path("imerologio/<int:pk>/diagrafi/", views.work_schedule_delete, name="work_schedule_delete"),
    path("imerologio/<int:pk>/oloklirosi/", views.work_schedule_complete, name="work_schedule_complete"),
    path("anafores/", views.monthly_report, name="monthly_report"),
    path("prosfores/", views.quote_list, name="quote_list"),
    path("prosfores/neo/", views.quote_create, name="quote_create"),
    path("prosfores/epilogi-ergou/", views.quote_select_project, name="quote_select_project"),
    path("prosfores/<int:pk>/", views.quote_detail, name="quote_detail"),
    path("prosfores/<int:pk>/syndesi-ergou/", views.quote_link_project, name="quote_link_project"),
    path("prosfores/<int:pk>/epexergasia/", views.quote_edit, name="quote_edit"),
    path("prosfores/<int:pk>/dimiourgia-ergou/", views.quote_create_project, name="quote_create_project"),
    path("prosfores/<int:pk>/apodoxi/", views.quote_accept, name="quote_accept"),
    path("prosfores/<int:pk>/katastasi/", views.quote_update_status, name="quote_update_status"),
    path("prosfores/<int:pk>/diagrafi/", views.quote_delete, name="quote_delete"),
    path("rythmiseis/", views.user_settings, name="user_settings"),
    path(
        "allagi-kwdikou/",
        password_change_required,
        name="password_change_required",
    ),
]
