from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("ergo/<int:pk>/pdf/", views.export_project_pdf, name="project_pdf"),
    path("anafores/excel/", views.export_monthly_excel, name="monthly_excel"),
    path("anafores/pdf/", views.export_monthly_pdf, name="monthly_pdf"),
    path("prosfora/<int:pk>/pdf/", views.export_quote_pdf, name="quote_pdf"),
]
