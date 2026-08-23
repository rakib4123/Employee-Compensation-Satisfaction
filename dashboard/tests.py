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
        # /dashboard/ isn't routed until Task 7, so don't follow the redirect.
        self.assertRedirects(response, "/dashboard/", fetch_redirect_response=False)

    def test_employee_login_redirects_to_self_service_path(self):
        self.client.login(username="amara_okafor", password="buscom-emp-2026")
        response = self.client.get(reverse("root"))
        # /me/ isn't routed until Task 9, so don't follow the redirect.
        self.assertRedirects(response, "/me/", fetch_redirect_response=False)

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
