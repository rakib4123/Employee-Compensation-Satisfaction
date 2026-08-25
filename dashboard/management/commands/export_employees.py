"""Export registered employees in the ML training CSV shape.

expected_salary and compensation_ratio are left blank: they exist only
in the synthetic dataset, where the generator invents a "fair" salary.
Real employees have no such label, and neither column is a model
feature or target, so blanks are harmless when the files are
concatenated at training time.
"""

import csv

from django.core.management.base import BaseCommand

from compensation.data import compute_scorecard, get_complete_employees
from ml.generate_dataset import CSV_COLUMNS

DEFAULT_OUT = "ml/data/real_employees.csv"


class Command(BaseCommand):
    help = "Export complete employee records to a training CSV."

    def add_arguments(self, parser):
        parser.add_argument("--out", default=DEFAULT_OUT)

    def handle(self, *args, **options):
        rows = []
        for row in get_complete_employees():
            scorecard = compute_scorecard(row)
            by_key = {category["key"]: category["score"] for category in scorecard["categories"]}
            rows.append({
                **row,
                "experience_score": by_key["experience"],
                "education_score": by_key["education"],
                "publication_score": by_key["publications"],
                "project_score": by_key["projects"],
                "compensation_score": scorecard["total"],
                "expected_salary": "",
                "compensation_ratio": "",
            })

        with open(options["out"], "w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

        self.stdout.write(f"Wrote {len(rows)} employee rows to {options['out']}")
