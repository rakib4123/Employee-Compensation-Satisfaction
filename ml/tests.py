from django.test import SimpleTestCase

from ml.data.survey_data_processor import (
    parse_salary,
    resolve_department,
    resolve_role,
    salary_in_band,
)


class SalaryParsingTests(SimpleTestCase):
    def test_plain_and_comma_separated_numbers(self):
        self.assertEqual(parse_salary("30000"), 30000)
        self.assertEqual(parse_salary("50,000"), 50000)

    def test_lakh_notation(self):
        self.assertEqual(parse_salary("3 lakh"), 300000)

    def test_zero_and_junk_are_none(self):
        self.assertIsNone(parse_salary("0"))
        self.assertIsNone(parse_salary("0000"))
        self.assertIsNone(parse_salary("n/a"))
        self.assertIsNone(parse_salary(""))


class RoleResolutionTests(SimpleTestCase):
    def test_known_role_resolves_exactly(self):
        self.assertEqual(resolve_role("Software Engineer", ""), "Software Engineer")

    def test_senior_role_is_not_matched_as_the_junior_one(self):
        self.assertEqual(resolve_role("Senior Software Engineer", ""), "Senior Software Engineer")

    def test_unknown_role_is_none(self):
        self.assertIsNone(resolve_role("Other", "AI Engineer"))
        self.assertIsNone(resolve_role("Other", "Student"))


class DepartmentResolutionTests(SimpleTestCase):
    def test_academic_department_falls_back_to_the_role_department(self):
        self.assertEqual(resolve_department("CSE", "Software Engineer"), "Engineering")
        self.assertEqual(resolve_department("Cse", "Data Analyst"), "Engineering")

    def test_known_department_is_kept(self):
        self.assertEqual(resolve_department("Finance", "Accountant"), "Finance")


class SalaryBandTests(SimpleTestCase):
    def test_in_band_salary_is_accepted(self):
        self.assertTrue(salary_in_band(70000, "Software Engineer"))

    def test_out_of_band_salary_is_rejected(self):
        self.assertFalse(salary_in_band(500000, "Data Analyst"))
        self.assertFalse(salary_in_band(300000, "Graphic Designer"))
