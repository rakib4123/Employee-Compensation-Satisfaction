from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AuthFlowTests(TestCase):
    def test_root_redirects_anonymous_user_to_login(self):
        response = self.client.get(reverse("root"))
        self.assertRedirects(response, reverse("login"))

    def test_hr_login_redirects_to_dashboard_path(self):
        self.client.login(username="hr_admin", password="buscom-hr-2026")
        response = self.client.get(reverse("root"))
        self.assertRedirects(response, reverse("hr_dashboard"))

    def test_employee_login_redirects_to_self_service_path(self):
        self.client.login(username="amara_okafor", password="buscom-emp-2026")
        response = self.client.get(reverse("root"))
        self.assertRedirects(response, reverse("employee_self_service"))

    def test_login_page_renders(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/login.html")

    def test_wrong_password_shows_error(self):
        response = self.client.post(
            reverse("login"),
            {"username": "hr_admin", "password": "not-the-password"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username or password")

    def test_next_param_is_honored_over_role_default(self):
        get_user_model().objects.filter(username="amara_okafor").update(actual_salary=95000)
        target = reverse("payslip_detail", args=[1])
        response = self.client.post(
            f"{reverse('login')}?next={target}",
            {"username": "amara_okafor", "password": "buscom-emp-2026"},
        )
        self.assertRedirects(response, target)

    def test_login_without_next_falls_back_to_role_default(self):
        response = self.client.post(
            reverse("login"),
            {"username": "hr_admin", "password": "buscom-hr-2026"},
        )
        self.assertRedirects(response, reverse("hr_dashboard"))

    def test_authenticated_user_visiting_login_is_redirected(self):
        self.client.login(username="amara_okafor", password="buscom-emp-2026")
        response = self.client.get(reverse("login"))
        self.assertRedirects(response, reverse("employee_self_service"))


class UserRoleTests(TestCase):
    def test_user_has_role_field_defaulting_to_employee(self):
        User = get_user_model()
        user = User.objects.create_user(username="jdoe", password="x")
        self.assertEqual(user.role, User.Role.EMPLOYEE)

    def test_demo_users_are_seeded(self):
        User = get_user_model()
        hr = User.objects.get(username="hr_admin")
        employee = User.objects.get(username="amara_okafor")
        self.assertEqual(hr.role, User.Role.HR)
        self.assertEqual(employee.role, User.Role.EMPLOYEE)
        self.assertEqual(employee.email, "amara.okafor@buscom.test")


class HrDashboardTests(TestCase):
    def setUp(self):
        get_user_model().objects.filter(username="amara_okafor").update(
            first_name="Amara", last_name="Okafor", designation="Software Engineer",
            actual_salary=95000, experience_years=6,
        )

    def test_requires_login(self):
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 302)

    def test_hr_user_can_view_dashboard(self):
        self.client.login(username="hr_admin", password="buscom-hr-2026")
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/hr_dashboard.html")
        self.assertContains(response, "Amara Okafor")

    def test_employee_user_is_redirected_away_from_dashboard(self):
        self.client.login(username="amara_okafor", password="buscom-emp-2026")
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 302)

    def test_average_salary_ignores_employees_with_no_recorded_salary(self):
        # amara_okafor (from setUp) has actual_salary=95000. Add a second
        # employee with no salary on file at all; without the fix, the
        # `or 0` in the average divides by headcount and pulls the
        # average down toward zero instead of excluding them.
        get_user_model().objects.create_user(
            username="nosalary_hr_test", password="x",
            first_name="No", last_name="Salary", actual_salary=None,
        )
        self.client.login(username="hr_admin", password="buscom-hr-2026")
        response = self.client.get(reverse("hr_dashboard"))
        self.assertEqual(response.context["headcount"], 2)
        self.assertEqual(response.context["total_payroll"], 95000)
        self.assertEqual(response.context["avg_salary"], 95000)


class PayslipDerivationTests(TestCase):
    def make_employee(self, username="payee", salary=60000):
        User = get_user_model()
        return User.objects.create_user(
            username=username, password="x", first_name="Sadia", last_name="Akter",
            email=f"{username}@buscom.test", actual_salary=salary,
        )

    def test_payslip_is_derived_from_actual_salary(self):
        from dashboard.payslips import payslips_for

        slips = payslips_for(self.make_employee(), today=date(2026, 8, 25))
        self.assertEqual(len(slips), 3)
        current = slips[0]
        self.assertEqual(current["id"], 1)
        self.assertEqual(current["period"], "August 2026")
        self.assertEqual(current["gross"], 60000)
        self.assertEqual(current["deductions"], 7800)
        self.assertEqual(current["net"], 52200)

    def test_periods_run_backwards_across_a_year_boundary(self):
        from dashboard.payslips import payslips_for

        slips = payslips_for(self.make_employee(), today=date(2026, 1, 15))
        self.assertEqual([s["period"] for s in slips],
                         ["January 2026", "December 2025", "November 2025"])

    def test_employee_without_salary_has_no_payslips(self):
        from dashboard.payslips import payslips_for

        self.assertEqual(payslips_for(self.make_employee(salary=None)), [])

    def test_breakdown_sums_to_net(self):
        from dashboard.payslips import payslips_for

        slip = payslips_for(self.make_employee(), today=date(2026, 8, 25))[0]
        self.assertEqual(sum(item["amount"] for item in slip["breakdown"]), slip["net"])


class PayslipViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.employee = User.objects.create_user(
            username="viewer", password="x", first_name="Sadia", last_name="Akter",
            actual_salary=60000,
        )
        self.client.login(username="viewer", password="x")

    def test_detail_renders_for_own_payslip(self):
        response = self.client.get(reverse("payslip_detail", args=[1]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Base Salary")

    def test_unknown_payslip_id_returns_404(self):
        self.assertEqual(self.client.get(reverse("payslip_detail", args=[99])).status_code, 404)

    def test_employee_without_salary_gets_404(self):
        User = get_user_model()
        User.objects.create_user(username="nosalary", password="x")
        self.client.login(username="nosalary", password="x")
        self.assertEqual(self.client.get(reverse("payslip_detail", args=[1])).status_code, 404)

    def test_payslip_lookup_is_scoped_to_the_requesting_user(self):
        User = get_user_model()
        User.objects.create_user(username="other", password="x", actual_salary=120000)

        response = self.client.get(reverse("payslip_detail", args=[1]))
        self.assertContains(response, "60000")

        self.client.login(username="other", password="x")
        response = self.client.get(reverse("payslip_detail", args=[1]))
        self.assertContains(response, "120000")
        self.assertNotContains(response, "60000")


class EmployeeSelfServiceTests(TestCase):
    def test_requires_login(self):
        self.assertEqual(self.client.get("/me/").status_code, 302)

    def test_employee_sees_own_details(self):
        get_user_model().objects.filter(username="amara_okafor").update(
            designation="Software Engineer", actual_salary=95000, experience_years=6,
        )
        self.client.login(username="amara_okafor", password="buscom-emp-2026")
        response = self.client.get("/me/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/employee_self_service.html")
        self.assertContains(response, "Software Engineer")

    def test_hr_user_sees_empty_state(self):
        self.client.login(username="hr_admin", password="buscom-hr-2026")
        response = self.client.get(reverse("employee_self_service"))
        self.assertTemplateUsed(response, "dashboard/empty_state.html")
        self.assertContains(response, "No employee record is linked to your account yet.")


class DepartmentDerivationTests(TestCase):
    def test_department_is_derived_from_designation_on_save(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="derive1", password="x", designation="Accountant"
        )
        self.assertEqual(user.department, "Finance")

    def test_department_is_derived_for_engineering_roles(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="derive2", password="x", designation="Software Engineer"
        )
        self.assertEqual(user.department, "Engineering")

    def test_other_designation_keeps_the_supplied_department(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="derive3", password="x", designation="Other", department="Design"
        )
        self.assertEqual(user.department, "Design")

    def test_trainings_count_defaults_to_zero(self):
        User = get_user_model()
        user = User.objects.create_user(username="derive4", password="x")
        self.assertEqual(user.trainings_count, 0)

    def test_unrecognised_designation_keeps_the_supplied_department(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="derive5", password="x", designation="Astronaut", department="Engineering"
        )
        self.assertEqual(user.department, "Engineering")


class RegistrationTests(TestCase):
    def payload(self, **overrides):
        data = {
            "username": "newhire",
            "password1": "buscom-test-2026",
            "password2": "buscom-test-2026",
            "first_name": "Nusrat",
            "last_name": "Islam",
            "email": "nusrat@buscom.test",
            "age": 27,
            "designation": "Software Engineer",
            "language_proficiency": "Advanced",
            "experience_years": 4,
            "education_level": "BSc",
            "publications_count": 2,
            "projects_led_count": 3,
            "trainings_count": 4,
            "skills_score": 7,
            "actual_salary": 65000,
            "satisfaction_score": 4,
            "fairness_feedback": "",
        }
        data.update(overrides)
        return data

    def test_registration_persists_every_field(self):
        response = self.client.post(reverse("register"), self.payload())
        self.assertRedirects(response, reverse("employee_self_service"))
        User = get_user_model()
        user = User.objects.get(username="newhire")
        self.assertEqual(user.role, User.Role.EMPLOYEE)
        self.assertEqual(user.age, 27)
        self.assertEqual(user.designation, "Software Engineer")
        self.assertEqual(user.department, "Engineering")
        self.assertEqual(user.experience_years, 4)
        self.assertEqual(user.education_level, "BSc")
        self.assertEqual(user.language_proficiency, "Advanced")
        self.assertEqual(user.publications_count, 2)
        self.assertEqual(user.projects_led_count, 3)
        self.assertEqual(user.trainings_count, 4)
        self.assertEqual(user.skills_score, 7)
        self.assertEqual(user.actual_salary, 65000)
        self.assertEqual(user.satisfaction_score, 4)
        self.assertEqual(user.boss_assessment_score, 10)

    def test_other_designation_requires_a_department(self):
        response = self.client.post(
            reverse("register"), self.payload(designation="Other", job_role_other="AI Engineer")
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], "department", "Select a department for your role."
        )

    def test_other_designation_with_department_is_accepted(self):
        response = self.client.post(
            reverse("register"),
            self.payload(designation="Other", job_role_other="AI Engineer", department="Engineering"),
        )
        self.assertRedirects(response, reverse("employee_self_service"))
        user = get_user_model().objects.get(username="newhire")
        self.assertEqual(user.job_role_other, "AI Engineer")
        self.assertEqual(user.department, "Engineering")

    def test_validation_error_keeps_submitted_values(self):
        response = self.client.post(
            reverse("register"), self.payload(password2="does-not-match")
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="Nusrat"')
        self.assertContains(response, 'value="65000"')
        self.assertContains(response, 'value="27"')

    def test_malicious_designation_cannot_break_out_of_the_alpine_string(self):
        # designation is an invalid choice, so the form re-renders (200)
        # with form.designation.value() echoing the raw submitted text
        # into the x-data attribute. Django's autoescape turns the
        # payload's `'` into `&#x27;`, but browsers HTML-decode attribute
        # values BEFORE Alpine evaluates x-data as JS, so an unescaped
        # `&#x27;` still lets the payload break out of the Alpine string
        # and execute. A raw substring check on the response body can't
        # tell escaped from unescaped quotes apart (both render "+alert("
        # as plain text either way) so this decodes HTML entities first,
        # the way a browser would, before checking for the break-out.
        import html
        import re

        payload = self.payload(designation="Other', role: ''+alert(document.cookie)+'")
        response = self.client.post(reverse("register"), payload)
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        match = re.search(r'x-data="(\{ role: .*? \})"', body)
        self.assertIsNotNone(match, "could not find the Alpine x-data attribute on the register page")
        decoded = html.unescape(match.group(1))
        self.assertNotIn("''+alert(", decoded)


class RegistrationNumericBoundsTests(TestCase):
    """publications_count/projects_led_count/trainings_count/actual_salary
    had a min_value but no max_value, letting a public registration flood
    the model with an outlier (e.g. publications_count=999999 produced a
    predicted market salary over a billion BDT). These fields must be
    bounded the same way compensation/forms.py bounds the HR what-if form.
    """

    def payload(self, **overrides):
        data = {
            "username": "boundhire",
            "password1": "buscom-test-2026",
            "password2": "buscom-test-2026",
            "first_name": "Bound",
            "last_name": "Check",
            "email": "bound@buscom.test",
            "age": 27,
            "designation": "Software Engineer",
            "language_proficiency": "Advanced",
            "experience_years": 4,
            "education_level": "BSc",
            "publications_count": 2,
            "projects_led_count": 3,
            "trainings_count": 4,
            "skills_score": 7,
            "actual_salary": 65000,
            "satisfaction_score": 4,
            "fairness_feedback": "",
        }
        data.update(overrides)
        return data

    def test_publications_count_over_twenty_is_rejected(self):
        response = self.client.post(reverse("register"), self.payload(publications_count=999999))
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], "publications_count",
            "Ensure this value is less than or equal to 20.",
        )

    def test_projects_led_count_over_twenty_is_rejected(self):
        response = self.client.post(reverse("register"), self.payload(projects_led_count=999999))
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], "projects_led_count",
            "Ensure this value is less than or equal to 20.",
        )

    def test_trainings_count_over_twenty_is_rejected(self):
        response = self.client.post(reverse("register"), self.payload(trainings_count=999999))
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], "trainings_count",
            "Ensure this value is less than or equal to 20.",
        )

    def test_actual_salary_over_one_million_is_rejected(self):
        response = self.client.post(reverse("register"), self.payload(actual_salary=999999999))
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], "actual_salary",
            "Ensure this value is less than or equal to 1000000.",
        )

    def test_in_range_values_are_accepted(self):
        response = self.client.post(reverse("register"), self.payload(
            publications_count=20, projects_led_count=20, trainings_count=20, actual_salary=1000000,
        ))
        self.assertRedirects(response, reverse("employee_self_service"))


class ExportEmployeesTests(TestCase):
    def test_export_writes_csv_columns_for_complete_employees(self):
        import csv
        import tempfile
        from pathlib import Path

        from django.core.management import call_command

        from ml.generate_dataset import CSV_COLUMNS

        get_user_model().objects.create_user(
            username="exportme", password="x", first_name="Tanvir", last_name="Uddin",
            age=31, designation="Data Analyst", language_proficiency="Fluent",
            experience_years=7, education_level="MSc", publications_count=2,
            projects_led_count=3, trainings_count=4, skills_score=8,
            boss_assessment_score=10, actual_salary=80000, satisfaction_score=5,
        )
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "real_employees.csv"
            call_command("export_employees", "--out", str(out))
            rows = list(csv.DictReader(out.open()))

        self.assertEqual(len(rows), 1)
        self.assertEqual(list(rows[0].keys()), CSV_COLUMNS)
        self.assertEqual(rows[0]["job_role"], "Data Analyst")
        self.assertEqual(rows[0]["department"], "Engineering")
        self.assertEqual(rows[0]["actual_salary"], "80000")
        self.assertEqual(rows[0]["trainings_count"], "4")
        self.assertEqual(rows[0]["training_score"], "8")
        self.assertEqual(rows[0]["satisfaction_label"], "Satisfied")
        self.assertEqual(rows[0]["expected_salary"], "")
        self.assertEqual(rows[0]["compensation_ratio"], "")

    def test_incomplete_employees_are_skipped(self):
        import csv
        import tempfile
        from pathlib import Path

        from django.core.management import call_command

        get_user_model().objects.create_user(
            username="partial2", password="x", first_name="Mim", last_name="Begum",
            actual_salary=None,
        )
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "real_employees.csv"
            call_command("export_employees", "--out", str(out))
            self.assertEqual(list(csv.DictReader(out.open())), [])
