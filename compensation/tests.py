from django.test import TestCase
from django.urls import reverse

from compensation import data
from compensation.data import compute_scorecard
from ml.generate_dataset import publication_score, training_score


class ScorecardTests(TestCase):
    def test_scorecard_matches_generator_formula_for_known_inputs(self):
        row = {
            "experience_years": 12,
            "education_level": "MSc",
            "publications_count": 5,
            "projects_led_count": 3,
            "trainings_count": 7,
            "skills_score": 8,
            "boss_assessment_score": 6,
        }
        scorecard = compute_scorecard(row)
        # experience: min(20, 12*2)=20, education: MSc=15,
        # publications: min(20, 5*2)=10, projects: min(10, 3*2)=6,
        # training: min(10, 7*2)=10, skills=8, boss_assessment=6
        self.assertEqual(scorecard["total"], 20 + 15 + 10 + 6 + 10 + 8 + 6)
        self.assertEqual(scorecard["max_total"], 100)

    def test_scorecard_zero_profile_scores_zero(self):
        row = {
            "experience_years": 0,
            "education_level": "High School",
            "publications_count": 0,
            "projects_led_count": 0,
            "trainings_count": 0,
            "skills_score": 0,
            "boss_assessment_score": 0,
        }
        self.assertEqual(compute_scorecard(row)["total"], 0)

    def test_scorecard_components_cap_at_their_maximum(self):
        row = {
            "experience_years": 40,
            "education_level": "PhD",
            "publications_count": 50,
            "projects_led_count": 50,
            "trainings_count": 50,
            "skills_score": 10,
            "boss_assessment_score": 10,
        }
        scorecard = compute_scorecard(row)
        self.assertEqual(scorecard["total"], 100)
        for category in scorecard["categories"]:
            self.assertEqual(category["score"], category["max"])

    def test_publication_score_is_two_marks_each_capped_at_twenty(self):
        self.assertEqual(publication_score(0), 0)
        self.assertEqual(publication_score(3), 6)
        self.assertEqual(publication_score(10), 20)
        self.assertEqual(publication_score(11), 20)

    def test_training_score_is_two_marks_each_capped_at_ten(self):
        self.assertEqual(training_score(0), 0)
        self.assertEqual(training_score(3), 6)
        self.assertEqual(training_score(5), 10)
        self.assertEqual(training_score(6), 10)


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


class EmployeeDetailTests(TestCase):
    def setUp(self):
        self.client.login(username="hr_admin", password="buscom-hr-2026")

    def test_shows_employee_profile_and_prediction(self):
        target = data.get_roster()[0]
        response = self.client.get(reverse("compensation:employee_detail", args=[target["employee_id"]]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, target["name"])
        self.assertContains(response, "Predicted Fair Salary")

    def test_unknown_employee_returns_404(self):
        response = self.client.get(reverse("compensation:employee_detail", args=[999999]))
        self.assertEqual(response.status_code, 404)

    def test_employee_role_is_redirected(self):
        self.client.logout()
        self.client.login(username="amara_okafor", password="buscom-emp-2026")
        target = data.get_roster()[0]
        response = self.client.get(reverse("compensation:employee_detail", args=[target["employee_id"]]))
        self.assertEqual(response.status_code, 302)


class PredictProfileTests(TestCase):
    def setUp(self):
        self.client.login(username="hr_admin", password="buscom-hr-2026")

    def valid_payload(self, **overrides):
        payload = {
            "job_role": "Software Engineer",
            "age": 28,
            "experience_years": 5,
            "education_level": "BSc",
            "publications_count": 0,
            "projects_led_count": 2,
            "trainings_count": 3,
            "skills_score": 7,
            "boss_assessment_score": 6,
            "language_proficiency": "Advanced",
        }
        payload.update(overrides)
        return payload

    def test_get_shows_empty_form(self):
        response = self.client.get(reverse("compensation:predict_profile"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Predicted Fair Salary")

    def test_post_valid_profile_shows_prediction_without_satisfaction(self):
        response = self.client.post(reverse("compensation:predict_profile"), self.valid_payload())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Predicted Fair Salary")
        self.assertNotContains(response, "Predicted Satisfaction")

    def test_post_with_proposed_salary_shows_satisfaction(self):
        response = self.client.post(
            reverse("compensation:predict_profile"),
            self.valid_payload(proposed_salary=60000),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Predicted Satisfaction")

    def test_post_with_zero_proposed_salary_shows_satisfaction(self):
        response = self.client.post(
            reverse("compensation:predict_profile"),
            self.valid_payload(proposed_salary=0),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Predicted Satisfaction")

    def test_invalid_profile_shows_errors(self):
        response = self.client.post(reverse("compensation:predict_profile"), {"job_role": "Software Engineer"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please correct the errors below.")


class SidebarLinkTests(TestCase):
    def test_hr_sees_compensation_link(self):
        self.client.login(username="hr_admin", password="buscom-hr-2026")
        response = self.client.get(reverse("hr_dashboard"))
        self.assertContains(response, "Compensation Insights")

    def test_employee_does_not_see_compensation_link(self):
        self.client.login(username="amara_okafor", password="buscom-emp-2026")
        response = self.client.get(reverse("employee_self_service"))
        self.assertNotContains(response, "Compensation Insights")
