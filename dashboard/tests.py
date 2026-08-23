from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class RootRouteTests(TestCase):
    def test_root_route_returns_ok(self):
        response = self.client.get(reverse("root"))
        self.assertEqual(response.status_code, 200)


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
