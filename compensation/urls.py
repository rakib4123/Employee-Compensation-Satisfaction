from django.urls import path

from . import views

app_name = "compensation"

urlpatterns = [
    path("", views.audit_dashboard, name="audit_dashboard"),
]
