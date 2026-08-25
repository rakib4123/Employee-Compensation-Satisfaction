"""Shared feature-column definitions for the compensation ML pipeline.

Kept separate from train_models.py so the Django app can import these
constants without pulling matplotlib/shap/sklearn into the web process.
Deliberately duplicated from train_models.py's own definitions rather
than cross-imported: train_models.py must remain runnable as a plain
script (`python3 ml/train_models.py`), and a script run that way only
has its own directory on sys.path, not the repo root, so it cannot
import `ml.features` reliably. Keep both definitions in sync by hand.
"""

CATEGORICAL_FEATURES = ["education_level", "language_proficiency", "job_role", "department"]
NUMERIC_FEATURES = [
    "age", "experience_years", "publications_count", "projects_led_count",
    "trainings_count", "skills_score", "boss_assessment_score",
]
CLASSIFICATION_EXTRA_NUMERIC = ["actual_salary", "expected_salary"]
