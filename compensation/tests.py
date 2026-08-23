from django.test import TestCase
from django.urls import reverse

from compensation.data import compute_scorecard


class ScorecardTests(TestCase):
    def test_scorecard_matches_generator_formula_for_known_inputs(self):
        row = {
            "experience_years": 12,
            "education_level": "MSc",
            "publications_count": 5,
            "projects_led_count": 3,
            "training_score": 7,
            "skills_score": 8,
            "boss_assessment_score": 6,
        }
        scorecard = compute_scorecard(row)
        # experience: min(20, 12*2)=20, education: MSc=15, publications: 5>=4 -> 20,
        # projects: min(10, 3*2)=6, training=7, skills=8, boss_assessment=6
        self.assertEqual(scorecard["total"], 20 + 15 + 20 + 6 + 7 + 8 + 6)
        self.assertEqual(scorecard["max_total"], 100)

    def test_scorecard_zero_profile_scores_zero(self):
        row = {
            "experience_years": 0,
            "education_level": "High School",
            "publications_count": 0,
            "projects_led_count": 0,
            "training_score": 0,
            "skills_score": 0,
            "boss_assessment_score": 0,
        }
        scorecard = compute_scorecard(row)
        self.assertEqual(scorecard["total"], 0)


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


class AuditDashboardContentTests(TestCase):
    def setUp(self):
        self.client.login(username="hr_admin", password="buscom-hr-2026")

    def test_shows_stat_cards_and_table(self):
        response = self.client.get(reverse("compensation:audit_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Headcount")
        self.assertContains(response, "Average Pay Gap")

    def test_search_with_no_matches_shows_empty_state(self):
        response = self.client.get(reverse("compensation:audit_dashboard"), {"q": "zzzznonexistent"})
        self.assertContains(response, "No employees match these filters.")

    def test_department_filter_narrows_results(self):
        listing = self.client.get(reverse("compensation:audit_dashboard"))
        first_department = listing.context["departments"][0]
        filtered = self.client.get(reverse("compensation:audit_dashboard"), {"department": first_department})
        self.assertEqual(filtered.status_code, 200)
        for employee in filtered.context["page_obj"]:
            self.assertEqual(employee["department"], first_department)

    def test_pagination_defaults_to_25_per_page(self):
        response = self.client.get(reverse("compensation:audit_dashboard"))
        self.assertEqual(len(response.context["page_obj"]), 25)
