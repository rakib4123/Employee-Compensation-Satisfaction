from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from dashboard.mock_data import PAYSLIPS


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


class PayslipDetailTests(TestCase):
    def test_requires_login(self):
        response = self.client.get("/me/payslips/1/")
        self.assertEqual(response.status_code, 302)

    def test_shows_itemized_breakdown(self):
        self.client.login(username="amara_okafor", password="buscom-emp-2026")
        response = self.client.get("/me/payslips/1/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/payslip_detail.html")
        self.assertContains(response, "Base Salary")

    def test_missing_payslip_returns_404(self):
        self.client.login(username="amara_okafor", password="buscom-emp-2026")
        response = self.client.get("/me/payslips/999/")
        self.assertEqual(response.status_code, 404)

    def test_other_employees_payslip_returns_404(self):
        other_payslip = {
            "id": 9001,
            "employee_id": 2,
            "period": "July 2026",
            "gross": 6000.00,
            "deductions": 900.00,
            "net": 5100.00,
            "breakdown": [{"label": "Base Salary", "amount": 6000.00}],
        }
        PAYSLIPS.append(other_payslip)
        try:
            self.client.login(username="amara_okafor", password="buscom-emp-2026")
            response = self.client.get(reverse("payslip_detail", args=[other_payslip["id"]]))
            self.assertEqual(response.status_code, 404)
        finally:
            PAYSLIPS.remove(other_payslip)


class EmployeeSelfServiceTests(TestCase):
    def test_requires_login(self):
        response = self.client.get("/me/")
        self.assertEqual(response.status_code, 302)

    def test_employee_sees_own_profile_and_payslips(self):
        self.client.login(username="amara_okafor", password="buscom-emp-2026")
        response = self.client.get("/me/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/employee_self_service.html")
        self.assertContains(response, "Senior Backend Engineer")
        self.assertContains(response, "June 2026")

    def test_user_with_no_matching_employee_sees_empty_state(self):
        self.client.login(username="hr_admin", password="buscom-hr-2026")
        response = self.client.get(reverse("employee_self_service"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/empty_state.html")
        self.assertNotContains(response, "Amara Okafor")
        self.assertNotContains(response, "95000")
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
