"""Data layer for Compensation Insights.

Queries the registered employees (User rows with role=employee) fresh on
every call and enriches them with each trained model's own predictions and
a human-readable explanation of what drove them.

Both winning models are linear (LinearRegression, LogisticRegression),
so top_factors() below computes exact closed-form contributions from
model coefficients. If a future retrain picks a non-linear model this
will break — that's a known, accepted limitation for this prototype.
"""

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

FEATURE_LABELS = {
    "job_role": "Job role",
    "department": "Department",
    "education_level": "Education",
    "language_proficiency": "Language proficiency",
    "age": "Age",
    "experience_years": "Experience",
    "publications_count": "Publications",
    "projects_led_count": "Projects led",
    "trainings_count": "Trainings completed",
    "skills_score": "Skills score",
    "boss_assessment_score": "Boss assessment",
    "actual_salary": "Actual salary",
    "predicted_market_salary": "Predicted market salary",
}

_pipeline_cache = None

REQUIRED_EMPLOYEE_FIELDS = (
    "designation", "department", "education_level", "language_proficiency",
    "age", "experience_years", "publications_count", "projects_led_count",
    "trainings_count", "skills_score", "boss_assessment_score",
    "actual_salary", "satisfaction_score",
)

MARKET_BANDS = {role: (low, high) for role, _department, low, high in JOB_ROLES}

# Every real employee carries this value; the what-if predictor uses it too so
# its output is comparable with roster rows. See ml/README.md for the caveat.
BOSS_ASSESSMENT_SCORE = 10


def _artifacts_dir():
    return settings.BASE_DIR / "ml" / "artifacts"


def _get_pipelines():
    global _pipeline_cache
    if _pipeline_cache is None:
        artifacts_dir = _artifacts_dir()
        regression_pipeline = joblib.load(artifacts_dir / "regression_model.joblib")
        classification_pipeline = joblib.load(artifacts_dir / "classification_model.joblib")
        _pipeline_cache = (regression_pipeline, classification_pipeline)
    return _pipeline_cache


def _employee_role(user):
    if user.designation == "Other":
        return user.job_role_other or "Other"
    return user.designation


def _missing_fields(user):
    missing = [name for name in REQUIRED_EMPLOYEE_FIELDS if getattr(user, name) in (None, "")]
    # "designation" already covers the case where no job title was chosen at
    # all; this catches the case where one was chosen (including a
    # free-text "Other" role) but it doesn't match any known market band.
    # An unrecognised role has no market band to compare against and no
    # model coefficients to react to it (the one-hot encoder zeroes it
    # out), so treating it as incomplete keeps it out of the roster, the
    # models, and the export rather than showing a fabricated number.
    if "designation" not in missing and _employee_role(user) not in MARKET_BANDS:
        missing.append("recognised job role")
    return missing


def _display_name(user):
    name = f"{user.first_name} {user.last_name}".strip()
    return name or user.username


def _employee_row(user):
    role = _employee_role(user)
    # _missing_fields() already excludes any user whose resolved role isn't
    # a recognised market band, so every caller of _employee_row() (via
    # _load_employees()) has a guaranteed hit here.
    market_min, market_max = MARKET_BANDS[role]
    name = _display_name(user)
    return {
        "employee_id": user.id,
        "name": name,
        "initials": "".join(part[0] for part in name.split()[:2]).upper(),
        "age": user.age,
        "job_role": role,
        "department": user.department or "",
        "experience_years": user.experience_years,
        "education_level": user.education_level,
        "publications_count": user.publications_count,
        "projects_led_count": user.projects_led_count,
        "trainings_count": user.trainings_count,
        "skills_score": user.skills_score,
        "boss_assessment_score": user.boss_assessment_score,
        "language_proficiency": user.language_proficiency,
        "market_min_salary": market_min,
        "market_max_salary": market_max,
        "actual_salary": user.actual_salary,
        "satisfaction_score": user.satisfaction_score,
        "satisfaction_label": "Satisfied" if user.satisfaction_score >= 4 else "Dissatisfied",
        # Collected at registration and, until now, read by nobody. The
        # detail page shows both so HR sees what the employee actually
        # reported next to what the model predicts.
        "fairness_feedback": (user.fairness_feedback or "").strip(),
    }


def _employees():
    from dashboard.models import User

    return User.objects.filter(role=User.Role.EMPLOYEE).order_by("id")


def get_incomplete_employees():
    incomplete = []
    for user in _employees():
        missing = _missing_fields(user)
        if missing:
            incomplete.append({"id": user.id, "name": _display_name(user), "missing": missing})
    return incomplete


def _load_employees():
    return [_employee_row(user) for user in _employees() if not _missing_fields(user)]


def get_complete_employees():
    """Employee rows with every model input present, in CSV_COLUMNS-compatible shape."""
    return _load_employees()


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
    rows = _load_employees()
    if not rows:
        return []
    regression_pipeline, classification_pipeline = _get_pipelines()
    df = pd.DataFrame(rows)

    predicted_salary = _predict_salary(regression_pipeline, df)

    clf_input = df.copy()
    clf_input["predicted_market_salary"] = predicted_salary
    satisfaction_probability = _predict_satisfaction(classification_pipeline, clf_input)

    return [
        _enrich(row, salary, probability)
        for row, salary, probability in zip(rows, predicted_salary, satisfaction_probability)
    ]


def _enrich(row, salary, probability):
    """Attach the model outputs to one roster row."""
    predicted = round(float(salary))
    probability = round(float(probability), 2)
    level = risk_level(probability)
    return {
        **row,
        "predicted_salary": predicted,
        "gap_pct": round((row["actual_salary"] - predicted) / predicted * 100, 1),
        "market_position_pct": market_position_pct(predicted, row["market_min_salary"], row["market_max_salary"]),
        "satisfaction_probability": probability,
        "predicted_satisfaction": satisfaction_label(level),
        "risk_level": level,
        "scorecard": compute_scorecard(row),
    }


def predict_for_user(user):
    """Prediction for a single employee, or None when their record is
    incomplete. Used by employee self-service, which needs one row and should
    not pay for building and scoring the whole roster to get it.
    """
    if _missing_fields(user):
        return None
    row = _employee_row(user)
    regression_pipeline, classification_pipeline = _get_pipelines()
    df = pd.DataFrame([row])
    predicted_salary = _predict_salary(regression_pipeline, df)

    clf_input = df.copy()
    clf_input["predicted_market_salary"] = predicted_salary
    probability = _predict_satisfaction(classification_pipeline, clf_input)

    return _enrich(row, predicted_salary[0], probability[0])


def get_roster():
    return _build_roster()


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
    clf_row["predicted_market_salary"] = employee["predicted_salary"]
    classification_factors = top_factors(
        classification_pipeline, clf_row[CATEGORICAL_FEATURES + NUMERIC_FEATURES + CLASSIFICATION_EXTRA_NUMERIC]
    )

    return {
        **employee,
        "regression_top_factors": regression_factors,
        "classification_top_factors": classification_factors,
    }


def predict_profile(profile):
    profile = {**profile, "boss_assessment_score": BOSS_ASSESSMENT_SCORE}
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
        clf_row["predicted_market_salary"] = predicted_salary
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
