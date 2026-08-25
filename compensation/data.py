"""In-memory data layer for Compensation Insights.

Loads the synthetic roster once per process and enriches it with each
trained model's own predictions and a human-readable explanation of what
drove them. Mirrors dashboard/mock_data.py's "plain Python data, no
database yet" approach — see
docs/superpowers/specs/2026-08-16-compensation-insights-design.md.

Both winning models are linear (LinearRegression, LogisticRegression),
so top_factors() below computes exact closed-form contributions from
model coefficients. If a future retrain picks a non-linear model this
will break — that's a known, accepted limitation for this prototype.
"""

import csv

import joblib
import numpy as np
import pandas as pd
from django.conf import settings

from ml.generate_dataset import (
    EDUCATION_POINTS,
    JOB_ROLES,
    clip,
    experience_score,
    project_score,
    publication_score,
    training_score,
)
from ml.features import CATEGORICAL_FEATURES, CLASSIFICATION_EXTRA_NUMERIC, NUMERIC_FEATURES

INT_FIELDS = [
    "employee_id", "age", "experience_years", "publications_count",
    "projects_led_count", "trainings_count", "training_score", "skills_score",
    "boss_assessment_score", "experience_score", "education_score",
    "publication_score", "project_score", "compensation_score",
    "market_min_salary", "market_max_salary", "expected_salary",
    "actual_salary",
]
FLOAT_FIELDS = ["compensation_ratio"]

FEATURE_LABELS = {
    "job_role": "Job role",
    "department": "Department",
    "education_level": "Education",
    "language_proficiency": "Language proficiency",
    "age": "Age",
    "experience_years": "Experience",
    "publications_count": "Publications",
    "projects_led_count": "Projects led",
    "training_score": "Training score",
    "skills_score": "Skills score",
    "boss_assessment_score": "Boss assessment",
    "actual_salary": "Actual salary",
    "expected_salary": "Predicted fair salary",
}

_roster_cache = None
_pipeline_cache = None


def _dataset_path():
    return settings.BASE_DIR / "ml" / "data" / "synthetic_employee_compensation.csv"


def _artifacts_dir():
    return settings.BASE_DIR / "ml" / "artifacts"


def _load_dataset():
    with open(_dataset_path(), newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        for field in INT_FIELDS:
            row[field] = int(row[field])
        for field in FLOAT_FIELDS:
            row[field] = float(row[field])
    return rows


def _get_pipelines():
    global _pipeline_cache
    if _pipeline_cache is None:
        artifacts_dir = _artifacts_dir()
        regression_pipeline = joblib.load(artifacts_dir / "regression_model.joblib")
        classification_pipeline = joblib.load(artifacts_dir / "classification_model.joblib")
        _pipeline_cache = (regression_pipeline, classification_pipeline)
    return _pipeline_cache


def risk_level(probability):
    if probability >= 0.6:
        return "low"
    if probability >= 0.4:
        return "medium"
    return "high"


SATISFACTION_LABELS = {"low": "Satisfied", "medium": "Uncertain", "high": "Dissatisfied"}


def satisfaction_label(level):
    return SATISFACTION_LABELS[level]


SCORECARD_DESCRIPTIONS = {
    "experience": "2 points per year of experience, capped at 20 (10+ years)",
    "education": "PhD = 20, MSc = 15, BSc = 10, Diploma = 5, High School = 0",
    "publications": "2 points per publication, capped at 20 (10+ publications)",
    "projects": "2 points per project led, capped at 10 (5+ projects)",
    "training": "2 points per training completed, capped at 10 (5+ trainings)",
    "skills": "Current skill-level score out of 10",
    "boss_assessment": "Fixed at 10 for all employees",
}


def compute_scorecard(row):
    categories = [
        {"key": "experience", "label": "Experience", "score": experience_score(row["experience_years"]), "max": 20},
        {"key": "education", "label": "Education", "score": EDUCATION_POINTS[row["education_level"]], "max": 20},
        {"key": "publications", "label": "Publications", "score": publication_score(row["publications_count"]), "max": 20},
        {"key": "projects", "label": "Project management", "score": project_score(row["projects_led_count"]), "max": 10},
        {"key": "training", "label": "Training", "score": training_score(row["trainings_count"]), "max": 10},
        {"key": "skills", "label": "Skills", "score": row["skills_score"], "max": 10},
        {"key": "boss_assessment", "label": "Boss assessment", "score": row["boss_assessment_score"], "max": 10},
    ]
    for category in categories:
        category["description"] = SCORECARD_DESCRIPTIONS[category["key"]]
    total = sum(category["score"] for category in categories)
    return {"categories": categories, "total": total, "max_total": 100}


def humanize_feature_name(raw_name):
    prefix, _, rest = raw_name.partition("__")
    if prefix == "cat":
        for column in CATEGORICAL_FEATURES:
            marker = column + "_"
            if rest.startswith(marker):
                value = rest[len(marker):]
                return f"{FEATURE_LABELS[column]}: {value}"
        return rest
    if prefix == "num":
        return FEATURE_LABELS.get(rest, rest)
    return raw_name


def top_factors(pipeline, row_df, limit=3):
    preprocessor = pipeline.named_steps["preprocessor"]
    estimator = pipeline.named_steps["estimator"]
    transformed = preprocessor.transform(row_df)[0]
    coefficients = np.ravel(estimator.coef_)
    feature_names = preprocessor.get_feature_names_out()
    contributions = transformed * coefficients
    order = np.argsort(-np.abs(contributions))[:limit]
    return [
        {
            "label": humanize_feature_name(feature_names[i]),
            "direction": "+" if contributions[i] > 0 else "-",
        }
        for i in order
    ]


def market_position_pct(predicted_salary, market_min, market_max):
    return round(clip((predicted_salary - market_min) / (market_max - market_min) * 100, 0, 100))


def _predict_salary(pipeline, df):
    return pipeline.predict(df[CATEGORICAL_FEATURES + NUMERIC_FEATURES])


def _predict_satisfaction(pipeline, df):
    columns = CATEGORICAL_FEATURES + NUMERIC_FEATURES + CLASSIFICATION_EXTRA_NUMERIC
    return pipeline.predict_proba(df[columns])[:, 1]


def _build_roster():
    rows = _load_dataset()
    regression_pipeline, classification_pipeline = _get_pipelines()
    df = pd.DataFrame(rows)

    predicted_salary = _predict_salary(regression_pipeline, df)

    clf_input = df.copy()
    clf_input["expected_salary"] = predicted_salary
    satisfaction_probability = _predict_satisfaction(classification_pipeline, clf_input)

    roster = []
    for row, salary, probability in zip(rows, predicted_salary, satisfaction_probability):
        predicted = round(float(salary))
        probability = round(float(probability), 2)
        level = risk_level(probability)
        roster.append({
            **row,
            "predicted_salary": predicted,
            "gap_pct": round((row["actual_salary"] - predicted) / predicted * 100, 1),
            "market_position_pct": market_position_pct(predicted, row["market_min_salary"], row["market_max_salary"]),
            "satisfaction_probability": probability,
            "predicted_satisfaction": satisfaction_label(level),
            "risk_level": level,
            "scorecard": compute_scorecard(row),
        })
    return roster


def get_roster():
    global _roster_cache
    if _roster_cache is None:
        _roster_cache = _build_roster()
    return _roster_cache


def get_employee(employee_id):
    return next((row for row in get_roster() if row["employee_id"] == employee_id), None)


def get_employee_detail(employee_id):
    employee = get_employee(employee_id)
    if employee is None:
        return None
    regression_pipeline, classification_pipeline = _get_pipelines()
    row_df = pd.DataFrame([employee])

    regression_factors = top_factors(regression_pipeline, row_df[CATEGORICAL_FEATURES + NUMERIC_FEATURES])

    clf_row = row_df.copy()
    clf_row["expected_salary"] = employee["predicted_salary"]
    classification_factors = top_factors(
        classification_pipeline, clf_row[CATEGORICAL_FEATURES + NUMERIC_FEATURES + CLASSIFICATION_EXTRA_NUMERIC]
    )

    return {
        **employee,
        "regression_top_factors": regression_factors,
        "classification_top_factors": classification_factors,
    }


def predict_profile(profile):
    job_role = profile["job_role"]
    department, market_min, market_max = next(
        (dept, mn, mx) for role, dept, mn, mx in JOB_ROLES if role == job_role
    )
    row = {**profile, "department": department}
    row_df = pd.DataFrame([row])

    regression_pipeline, classification_pipeline = _get_pipelines()
    predicted_salary = round(float(_predict_salary(regression_pipeline, row_df)[0]))
    regression_factors = top_factors(regression_pipeline, row_df[CATEGORICAL_FEATURES + NUMERIC_FEATURES])

    result = {
        "job_role": job_role,
        "department": department,
        "market_min_salary": market_min,
        "market_max_salary": market_max,
        "predicted_salary": predicted_salary,
        "market_position_pct": market_position_pct(predicted_salary, market_min, market_max),
        "scorecard": compute_scorecard(row),
        "regression_top_factors": regression_factors,
        "proposed_salary": profile.get("proposed_salary"),
    }

    if profile.get("proposed_salary") is not None:
        clf_row = row_df.copy()
        clf_row["actual_salary"] = profile["proposed_salary"]
        clf_row["expected_salary"] = predicted_salary
        probability = round(float(_predict_satisfaction(classification_pipeline, clf_row)[0]), 2)
        result["satisfaction_probability"] = probability
        level = risk_level(probability)
        result["predicted_satisfaction"] = satisfaction_label(level)
        result["risk_level"] = level
        result["gap_pct"] = round((profile["proposed_salary"] - predicted_salary) / predicted_salary * 100, 1)
        result["classification_top_factors"] = top_factors(
            classification_pipeline, clf_row[CATEGORICAL_FEATURES + NUMERIC_FEATURES + CLASSIFICATION_EXTRA_NUMERIC]
        )

    return result
