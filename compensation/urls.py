from django.urls import path

from . import views

app_name = "compensation"

urlpatterns = [
    path("", views.audit_dashboard, name="audit_dashboard"),
    path("<int:employee_id>/", views.employee_detail, name="employee_detail"),
]
