"""Payslips derived from an employee's recorded salary.

There is no payroll system behind BusCom. These are estimates computed
from User.actual_salary so employee self-service has something real to
show, and they are labeled as estimates everywhere they appear.
"""

from datetime import date

TAX_RATE = 0.10
INSURANCE_RATE = 0.03
MONTHS_SHOWN = 3


def _shift_month(today, months_back):
    month_index = today.month - 1 - months_back
    year = today.year + month_index // 12
    return date(year, month_index % 12 + 1, 1)


def _payslip(salary, period_start, payslip_id):
    tax = round(salary * TAX_RATE)
    insurance = round(salary * INSURANCE_RATE)
    net = salary - tax - insurance
    return {
        "id": payslip_id,
        "period": period_start.strftime("%B %Y"),
        "gross": salary,
        "deductions": tax + insurance,
        "net": net,
        "breakdown": [
            {"label": "Base Salary", "amount": salary},
            {"label": "Tax", "amount": -tax},
            {"label": "Insurance", "amount": -insurance},
        ],
    }


def payslips_for(user, count=MONTHS_SHOWN, today=None):
    salary = user.actual_salary
    if not salary:
        return []
    today = today or date.today()
    return [
        _payslip(salary, _shift_month(today, offset), offset + 1)
        for offset in range(count)
    ]


def find_payslip(user, payslip_id):
    return next((slip for slip in payslips_for(user) if slip["id"] == payslip_id), None)
