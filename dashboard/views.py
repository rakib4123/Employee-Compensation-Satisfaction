from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import Http404
from django.shortcuts import redirect, render

from .mock_data import EMPLOYEES, PAYSLIPS
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


def _is_hr(user):
    return user.is_authenticated and user.role == User.Role.HR


@login_required
@user_passes_test(_is_hr, login_url="/me/")
def hr_dashboard(request):
    headcount = len(EMPLOYEES)
    total_payroll = sum(e["salary"] for e in EMPLOYEES)
    avg_salary = round(total_payroll / headcount, 2) if headcount else 0
    return render(request, "dashboard/hr_dashboard.html", {
        "employees": EMPLOYEES,
        "headcount": headcount,
        "total_payroll": total_payroll,
        "avg_salary": avg_salary,
    })


@login_required
def payslip_detail(request, payslip_id):
    payslip = next((p for p in PAYSLIPS if p["id"] == payslip_id), None)
    if payslip is None:
        raise Http404("Payslip not found.")
    return render(request, "dashboard/payslip_detail.html", {"payslip": payslip})


@login_required
def employee_self_service(request):
    employee = next(
        (e for e in EMPLOYEES if e["email"] == request.user.email),
        EMPLOYEES[0],
    )
    payslips = [p for p in PAYSLIPS if p["employee_id"] == employee["id"]]
    return render(request, "dashboard/employee_self_service.html", {
        "employee": employee,
        "payslips": payslips,
    })
