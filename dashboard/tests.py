from django.test import TestCase
from django.urls import reverse


class RootRouteTests(TestCase):
    def test_root_route_returns_ok(self):
        response = self.client.get(reverse("root"))
        self.assertEqual(response.status_code, 200)
