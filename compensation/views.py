from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render

from dashboard.views import _is_hr


@login_required
@user_passes_test(_is_hr, login_url="employee_self_service")
def audit_dashboard(request):
    return render(request, "compensation/dashboard.html", {})
