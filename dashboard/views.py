from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse

from django.contrib.auth import login
from .forms import EmployeeRegistrationForm
from .payslips import find_payslip, payslips_for
from .models import User


class RoleLoginView(auth_views.LoginView):
    template_name = "dashboard/login.html"
    redirect_authenticated_user = True

    def get_default_redirect_url(self):
        if self.request.user.role == User.Role.HR:
            return reverse("hr_dashboard")
        return reverse("employee_self_service")


def root_redirect(request):
    if not request.user.is_authenticated:
        return redirect("login")
    if request.user.role == User.Role.HR:
        return redirect("hr_dashboard")
    return redirect("employee_self_service")


def _is_hr(user):
    return user.is_authenticated and user.role == User.Role.HR


@login_required
@user_passes_test(_is_hr, login_url="employee_self_service")
def hr_dashboard(request):
    users = list(User.objects.filter(role=User.Role.EMPLOYEE).order_by("id"))
    employees = [
        {
            "id": user.id,
            "name": f"{user.first_name} {user.last_name}".strip() or user.username,
            "initials": "".join(
                part[0] for part in f"{user.first_name} {user.last_name}".split()[:2]
            ).upper(),
            "designation": user.job_role_other if user.designation == "Other" else (user.designation or "—"),
            "department": user.department or "—",
            "experience_years": user.experience_years or 0,
            "salary": user.actual_salary or 0,
        }
        for user in users
    ]
    headcount = len(employees)
    total_payroll = sum(e["salary"] for e in employees)
    # Average only over employees who actually have a recorded salary, so
    # one with no salary on file (e.g. a freshly seeded/incomplete record)
    # doesn't silently drag the average toward zero. total_payroll and
    # headcount stay true totals across every employee.
    salaried_count = sum(1 for user in users if user.actual_salary is not None)
    avg_salary = round(total_payroll / salaried_count, 2) if salaried_count else 0
    return render(request, "dashboard/hr_dashboard.html", {
        "employees": employees,
        "headcount": headcount,
        "total_payroll": total_payroll,
        "avg_salary": avg_salary,
    })


@login_required
def payslip_detail(request, payslip_id):
    payslip = find_payslip(request.user, payslip_id)
    if payslip is None:
        raise Http404("Payslip not found.")
    return render(request, "dashboard/payslip_detail.html", {"payslip": payslip})


@login_required
def employee_self_service(request):
    user = request.user
    if user.role != User.Role.EMPLOYEE:
        return render(request, "dashboard/empty_state.html", {
            "message": "No employee record is linked to your account yet.",
        })
    employee = {
        "name": f"{user.first_name} {user.last_name}".strip() or user.username,
        "initials": "".join(
            part[0] for part in f"{user.first_name} {user.last_name}".split()[:2]
        ).upper(),
        "designation": user.job_role_other if user.designation == "Other" else (user.designation or "—"),
        "department": user.department or "—",
        "experience_years": user.experience_years or 0,
        "email": user.email,
        "salary": user.actual_salary or 0,
    }
    # Imported here rather than at module scope: dashboard is loaded during
    # app registry setup and compensation.data pulls in pandas and the model
    # artifacts, which self-service is the only view in this app to need.
    from compensation.data import predict_for_user

    return render(request, "dashboard/employee_self_service.html", {
        "employee": employee,
        "payslips": payslips_for(user),
        "prediction": predict_for_user(user),
    })


@login_required
def user_profile(request):
    return render(request, "dashboard/profile.html", {
        "user": request.user,
    })


def register_employee(request):
    if request.user.is_authenticated:
        return redirect("root")
        
    if request.method == "POST":
        form = EmployeeRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = User.Role.EMPLOYEE
            user.save()
            login(request, user)
            return redirect("employee_self_service")
    else:
        form = EmployeeRegistrationForm()
        
    return render(request, "dashboard/register.html", {"form": form})
