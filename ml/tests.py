import pandas as pd
from django.test import SimpleTestCase

from ml.data.survey_data_processor import (
    build_row,
    parse_salary,
    parse_satisfaction,
    resolve_department,
    resolve_language,
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


class LanguageResolutionTests(SimpleTestCase):
    def test_known_language_resolves_exactly(self):
        self.assertEqual(resolve_language("Advanced"), "Advanced")

    def test_unknown_language_is_none(self):
        self.assertIsNone(resolve_language("Bengali"))
        self.assertIsNone(resolve_language(""))


class SatisfactionParsingTests(SimpleTestCase):
    def test_valid_rating_parses_to_int(self):
        self.assertEqual(parse_satisfaction("4"), 4)
        self.assertEqual(parse_satisfaction(2), 2)

    def test_blank_or_unparseable_answer_is_none(self):
        # A missing answer must drop the row, not silently become 0 (which
        # reads as "Dissatisfied" since 0 >= 4 is False) and fabricate a
        # training label for a question nobody answered.
        self.assertIsNone(parse_satisfaction(""))
        self.assertIsNone(parse_satisfaction("n/a"))
        self.assertIsNone(parse_satisfaction("nan"))
        self.assertIsNone(parse_satisfaction("not a number"))


class BuildRowDropConditionsTests(SimpleTestCase):
    """End-to-end check that build_row() actually drops the row (rather
    than just the helper functions returning None in isolation) for the
    two conditions fixed here: a blank satisfaction answer, and an
    unrecognised language proficiency answer.
    """

    def record(self, overrides=None):
        # Positional columns match survey_raw.tsv: Timestamp, Age, Job
        # title, Other job title, Department, Language, Experience,
        # Education, Publications, Projects, Trainings, Skills, Manager
        # rating, Salary, Satisfaction, Feedback.
        values = [
            "2026-01-01", 30, "Software Engineer", "", "Engineering",
            "Advanced", 5, "BSc", 2, 2, 3, 7, 8, "70000", 4, "",
        ]
        series = pd.Series(values)
        for index, value in (overrides or {}).items():
            series.iloc[index] = value
        return series

    def test_row_is_built_when_everything_is_valid(self):
        row = build_row(1, self.record())
        self.assertIsNotNone(row)
        self.assertEqual(row["satisfaction_label"], "Satisfied")
        self.assertEqual(row["language_proficiency"], "Advanced")

    def test_blank_satisfaction_drops_the_row(self):
        self.assertIsNone(build_row(1, self.record({14: ""})))

    def test_unrecognised_language_drops_the_row(self):
        self.assertIsNone(build_row(1, self.record({5: "Bengali"})))
