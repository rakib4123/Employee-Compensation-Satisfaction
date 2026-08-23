from django.test import TestCase
from django.urls import reverse


class AuditDashboardAccessTests(TestCase):
    def test_requires_login(self):
        response = self.client.get(reverse("compensation:audit_dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_hr_user_can_view_dashboard(self):
        self.client.login(username="hr_admin", password="buscom-hr-2026")
        response = self.client.get(reverse("compensation:audit_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "compensation/dashboard.html")

    def test_employee_user_is_redirected(self):
        self.client.login(username="amara_okafor", password="buscom-emp-2026")
        response = self.client.get(reverse("compensation:audit_dashboard"))
        self.assertEqual(response.status_code, 302)
