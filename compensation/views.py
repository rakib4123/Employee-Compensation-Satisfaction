from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render

from dashboard.views import _is_hr

from . import data
from .forms import PredictProfileForm

SORT_FIELDS = {
    "name": lambda row: row["name"],
    "gap_pct": lambda row: row["gap_pct"],
    "predicted_salary": lambda row: row["predicted_salary"],
    "satisfaction_probability": lambda row: row["satisfaction_probability"],
}


@login_required
@user_passes_test(_is_hr, login_url="employee_self_service")
def audit_dashboard(request):
    roster = data.get_roster()

    query = request.GET.get("q", "").strip()
    department = request.GET.get("department", "all")
    risk = request.GET.get("risk", "all")
    sort = request.GET.get("sort", "name")

    filtered = roster
    if query:
        needle = query.lower()
        filtered = [r for r in filtered if needle in r["name"].lower() or needle in r["job_role"].lower()]
    if department != "all":
        filtered = [r for r in filtered if r["department"] == department]
    if risk != "all":
        filtered = [r for r in filtered if r["risk_level"] == risk]
    filtered = sorted(filtered, key=SORT_FIELDS.get(sort, SORT_FIELDS["name"]))

    paginator = Paginator(filtered, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    headcount = len(roster)
    avg_gap_pct = round(sum(r["gap_pct"] for r in roster) / headcount, 1) if headcount else 0
    underpaid_count = sum(1 for r in roster if r["gap_pct"] < -10)
    at_risk_count = sum(1 for r in roster if r["risk_level"] == "high")

    base_params = request.GET.copy()
    base_params.pop("page", None)

    return render(request, "compensation/dashboard.html", {
        "page_obj": page_obj,
        "query": query,
        "department": department,
        "risk": risk,
        "sort": sort,
        "departments": sorted({r["department"] for r in roster}),
        "headcount": headcount,
        "avg_gap_pct": avg_gap_pct,
        "underpaid_count": underpaid_count,
        "at_risk_count": at_risk_count,
        "base_query": base_params.urlencode(),
    })


@login_required
@user_passes_test(_is_hr, login_url="employee_self_service")
def employee_detail(request, employee_id):
    employee = data.get_employee_detail(employee_id)
    if employee is None:
        raise Http404("Employee not found.")
    return render(request, "compensation/detail.html", {
        "employee": employee,
        "card": employee,
        "salary_label": "Actual salary",
    })


@login_required
@user_passes_test(_is_hr, login_url="employee_self_service")
def predict_profile(request):
    result = None
    if request.method == "POST":
        form = PredictProfileForm(request.POST)
        if form.is_valid():
            result = data.predict_profile(form.cleaned_data)
            if result.get("proposed_salary") is not None:
                result["actual_salary"] = result["proposed_salary"]
    else:
        form = PredictProfileForm()

    return render(request, "compensation/predict.html", {
        "form": form,
        "result": result,
        "card": result,
        "salary_label": "Proposed salary",
    })
