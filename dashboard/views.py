from django.contrib.auth import views as auth_views
from django.shortcuts import redirect

from .models import User


class RoleLoginView(auth_views.LoginView):
    template_name = "dashboard/login.html"

    def get_success_url(self):
        if self.request.user.role == User.Role.HR:
            return "/dashboard/"
        return "/me/"


def root_redirect(request):
    if not request.user.is_authenticated:
        return redirect("login")
    if request.user.role == User.Role.HR:
        return redirect("/dashboard/")
    return redirect("/me/")
