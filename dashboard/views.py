from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse

from django.contrib.auth import login
from .forms import EmployeeRegistrationForm
from .mock_data import EMPLOYEES, PAYSLIPS
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
    employee = next((e for e in EMPLOYEES if e["email"] == request.user.email), None)
    payslip = next((p for p in PAYSLIPS if p["id"] == payslip_id), None)
    if payslip is None or employee is None or payslip["employee_id"] != employee["id"]:
        raise Http404("Payslip not found.")
    return render(request, "dashboard/payslip_detail.html", {"payslip": payslip})


@login_required
def employee_self_service(request):
    employee = next((e for e in EMPLOYEES if e["email"] == request.user.email), None)
    if employee is None:
        return render(request, "dashboard/empty_state.html", {
            "message": "No employee record is linked to your account yet.",
        })
    payslips = [p for p in PAYSLIPS if p["employee_id"] == employee["id"]]
    return render(request, "dashboard/employee_self_service.html", {
        "employee": employee,
        "payslips": payslips,
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
            
            # Append to mock data
            new_id = max(e["id"] for e in EMPLOYEES) + 1 if EMPLOYEES else 1
            EMPLOYEES.append({
                "id": new_id,
                "name": f"{user.first_name} {user.last_name}",
                "email": user.email,
                "designation": form.cleaned_data.get("designation"),
                "department": form.cleaned_data.get("department"),
                "experience_years": 0,
                "salary": 50000,
                "initials": "".join(part[0] for part in [user.first_name, user.last_name] if part).upper()
            })
            
            login(request, user)
            return redirect("employee_self_service")
    else:
        form = EmployeeRegistrationForm()
        
    return render(request, "dashboard/register.html", {"form": form})
