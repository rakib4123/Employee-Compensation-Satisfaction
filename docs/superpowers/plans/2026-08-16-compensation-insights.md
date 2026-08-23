# Compensation Insights Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an HR-only "Compensation Insights" feature to BusCom that predicts each employee's fair salary and satisfaction risk from the already-built ML models, with a plain-language explanation of what drove each prediction.

**Architecture:** A new Django app `compensation`, with no database models — it loads the synthetic CSV and two trained scikit-learn pipelines into an in-process cache (mirroring `dashboard/mock_data.py`'s "plain Python data, no persistence yet" approach), and serves three server-rendered screens: an audit dashboard, a per-employee detail page, and a what-if prediction form.

**Tech Stack:** Django (existing), Tailwind CSS (standalone CLI, existing), Alpine.js/GSAP (existing, reused via already-defined `motion.js` helpers — no new JS), scikit-learn + joblib (already installed in the venv from prior ML work).

**Spec:** `docs/superpowers/specs/2026-08-16-compensation-insights-design.md`

## Global Constraints

- HR-only: every view uses the same `_is_hr` / `user_passes_test(..., login_url="employee_self_service")` pattern already used by `dashboard.views.hr_dashboard` — import it rather than redefining it.
- No new database models or migrations for `compensation` — data is loaded once per process from `ml/data/synthetic_employee_compensation.csv` and `ml/artifacts/*.joblib` and cached in module-level variables.
- Currency is BDT, displayed with the `৳` prefix (per the approved spec — this differs from the rest of BusCom's `$`-denominated mock data; that inconsistency is expected and out of scope to fix).
- The two winning models (`LinearRegression`, `LogisticRegression`) are linear — per-instance explanations use exact closed-form `coefficient × transformed value` contributions, not SHAP. If a future retrain picks a non-linear model, `top_factors()` will break; this is a known, documented limitation, not something to defensively code around now.
- All Python commands run inside the project venv. In this worktree, invoke the venv's binaries directly (`./venv/bin/python`, `./venv/bin/python manage.py ...`) rather than `source venv/bin/activate && ...` — the sandbox cannot verify a sourced shell stays inside the worktree and will refuse the command. Every command below that shows `python3 ...` or `python manage.py ...` means `./venv/bin/python3 ...` / `./venv/bin/python manage.py ...` in this worktree.
- The predict-for-a-profile form uses server-side Django form validation with inline per-field error rendering, not the existing add/edit employee modal's client-only Alpine validation — that pattern can't run a trained sklearn model in the browser, so this is a deliberate, necessary deviation from the spec's literal wording. Visual style (input classes, inline error placement) still matches.
- Every task that adds or changes template markup ends by rebuilding CSS: `./tailwindcss -i ./dashboard/static/dashboard/css/input.css -o ./dashboard/static/dashboard/css/output.css --minify` (the input file gets one new `@source` line in Task 3 so Tailwind's v4 content scanner also covers `compensation/templates`).
- Match existing Tailwind conventions exactly: cards are `rounded-xl bg-white dark:bg-slate-800 shadow p-5` (or `p-6`), primary buttons are `rounded-lg bg-indigo-600 hover:bg-indigo-500 active:scale-[0.98] transition text-white text-sm font-medium px-4 py-1.5`, inputs are `rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500`, table rows are `border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition`.

---

## Task 1: Add employee names to the synthetic dataset generator

**Files:**
- Modify: `ml/generate_dataset.py`
- Create: `ml/__init__.py`
- Regenerate: `ml/data/synthetic_employee_compensation.csv`

**Interfaces:**
- Produces: `generate_row()` now includes `"name"` (str) and `"initials"` (str, 2 uppercase letters) keys in its returned dict, and `CSV_COLUMNS` includes them.

- [ ] **Step 1: Add name pools and generate name/initials in `generate_row`**

In `ml/generate_dataset.py`, add after the `LANGUAGE_WEIGHTS = [15, 35, 35, 15]` line:

```python
FIRST_NAMES = [
    "Abir", "Nusrat", "Rafiq", "Farhana", "Imran", "Sadia", "Tanvir", "Mim",
    "Shakil", "Ayesha", "Rahim", "Nabila", "Kamal", "Sultana", "Faisal",
    "Ruma", "Jahid", "Sabrina", "Mahmud", "Tania",
]
LAST_NAMES = [
    "Islam", "Rahman", "Hossain", "Akter", "Chowdhury", "Ahmed", "Khan",
    "Begum", "Uddin", "Sarker",
]
```

Change `CSV_COLUMNS` from:

```python
CSV_COLUMNS = [
    "employee_id", "age", "job_role", "department",
```

to:

```python
CSV_COLUMNS = [
    "employee_id", "name", "initials", "age", "job_role", "department",
```

Change the start of `generate_row` from:

```python
def generate_row(employee_id, rng):
    job_role, department, market_min, market_max = rng.choice(JOB_ROLES)
```

to:

```python
def generate_row(employee_id, rng):
    name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
    initials = "".join(part[0] for part in name.split()).upper()

    job_role, department, market_min, market_max = rng.choice(JOB_ROLES)
```

Change the returned dict from:

```python
    return {
        "employee_id": employee_id,
        "age": age,
```

to:

```python
    return {
        "employee_id": employee_id,
        "name": name,
        "initials": initials,
        "age": age,
```

- [ ] **Step 2: Make `ml` an importable package**

Create empty `ml/__init__.py` (Django's `compensation` app will need `import ml.generate_dataset` later).

- [ ] **Step 3: Regenerate the dataset and verify**

```bash
source venv/bin/activate && python3 ml/generate_dataset.py --rows 1000 --seed 42 --out ml/data/synthetic_employee_compensation.csv
```

Then verify names landed correctly:

```bash
source venv/bin/activate && python3 -c "
import csv
with open('ml/data/synthetic_employee_compensation.csv') as f:
    rows = list(csv.DictReader(f))
print(len(rows), 'rows')
print(rows[0]['name'], rows[0]['initials'])
assert all(row['name'] and row['initials'] for row in rows)
print('OK')
"
```

Expected: `1000 rows`, a plausible name/initials pair, then `OK`.

- [ ] **Step 4: Commit**

This also picks up `ml/generate_dataset.py`'s and the dataset's earlier uncommitted state from prior work in this session.

```bash
git add ml/__init__.py ml/generate_dataset.py ml/data/synthetic_employee_compensation.csv
git commit -m "$(cat <<'EOF'
feat: add employee names to synthetic compensation dataset

Compensation Insights needs a name to display per employee; adds a
small first/last name pool to generate_dataset.py and makes ml/ an
importable package for the Django app to consume.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Save trained model pipelines as loadable artifacts

**Files:**
- Modify: `ml/train_models.py`
- Modify: `requirements.txt` (already edited in prior session work — committed here)
- Regenerate: `ml/outputs/*.png`, `ml/outputs/model_comparison.csv`
- Create (generated): `ml/artifacts/regression_model.joblib`, `ml/artifacts/classification_model.joblib`

**Interfaces:**
- Produces: `ml/artifacts/regression_model.joblib` and `ml/artifacts/classification_model.joblib`, each a fitted `sklearn.pipeline.Pipeline` with steps named `"preprocessor"` and `"estimator"` — `compensation/data.py` (Task 4) loads these by exactly these step names.

- [ ] **Step 1: Add joblib/Pipeline imports**

Change:

```python
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
```

to:

```python
import matplotlib

matplotlib.use("Agg")
import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
```

Change:

```python
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
```

to:

```python
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
```

- [ ] **Step 2: Return the fitted preprocessor from `fit_transform_split`**

Change:

```python
    feature_names = preprocessor.get_feature_names_out()
    return X_train_t, X_test_t, y_train.to_numpy(), y_test.to_numpy(), feature_names
```

to:

```python
    feature_names = preprocessor.get_feature_names_out()
    return X_train_t, X_test_t, y_train.to_numpy(), y_test.to_numpy(), feature_names, preprocessor
```

- [ ] **Step 3: Thread `artifacts_dir` through `run_regression` and save the winning pipeline**

Change:

```python
def run_regression(df, out_dir):
    X_train, X_test, y_train, y_test, feature_names = fit_transform_split(
        df, NUMERIC_FEATURES, REGRESSION_TARGET
    )
```

to:

```python
def run_regression(df, out_dir, artifacts_dir):
    X_train, X_test, y_train, y_test, feature_names, preprocessor = fit_transform_split(
        df, NUMERIC_FEATURES, REGRESSION_TARGET
    )
```

Change:

```python
    explain_model(fitted[best_name], X_train, X_test, feature_names, out_dir, prefix="regression")
    return results


def run_classification(df, out_dir):
    numeric_features = NUMERIC_FEATURES + CLASSIFICATION_EXTRA_NUMERIC
    df = df.copy()
    df["satisfaction_binary"] = (df[CLASSIFICATION_TARGET] == "Satisfied").astype(int)

    X_train, X_test, y_train, y_test, feature_names = fit_transform_split(
        df, numeric_features, "satisfaction_binary"
    )
```

to:

```python
    explain_model(fitted[best_name], X_train, X_test, feature_names, out_dir, prefix="regression")
    save_pipeline(preprocessor, fitted[best_name], artifacts_dir, "regression_model.joblib")
    return results


def run_classification(df, out_dir, artifacts_dir):
    numeric_features = NUMERIC_FEATURES + CLASSIFICATION_EXTRA_NUMERIC
    df = df.copy()
    df["satisfaction_binary"] = (df[CLASSIFICATION_TARGET] == "Satisfied").astype(int)

    X_train, X_test, y_train, y_test, feature_names, preprocessor = fit_transform_split(
        df, numeric_features, "satisfaction_binary"
    )
```

- [ ] **Step 4: Save the classification pipeline and add `save_pipeline`**

Change:

```python
    explain_model(fitted[best_name], X_train, X_test, feature_names, out_dir, prefix="classification")
    return results


def explain_model(model, X_train, X_test, feature_names, out_dir, prefix):
```

to:

```python
    explain_model(fitted[best_name], X_train, X_test, feature_names, out_dir, prefix="classification")
    save_pipeline(preprocessor, fitted[best_name], artifacts_dir, "classification_model.joblib")
    return results


def save_pipeline(preprocessor, estimator, artifacts_dir, filename):
    pipeline = Pipeline(steps=[("preprocessor", preprocessor), ("estimator", estimator)])
    path = os.path.join(artifacts_dir, filename)
    joblib.dump(pipeline, path)
    print(f"Saved {path}")


def explain_model(model, X_train, X_test, feature_names, out_dir, prefix):
```

- [ ] **Step 5: Wire `--artifacts` through `main()`**

Change:

```python
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="ml/data/synthetic_employee_compensation.csv")
    parser.add_argument("--out", default="ml/outputs")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    df = pd.read_csv(args.data)

    reg_results = run_regression(df, args.out)
    clf_results = run_classification(df, args.out)
```

to:

```python
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="ml/data/synthetic_employee_compensation.csv")
    parser.add_argument("--out", default="ml/outputs")
    parser.add_argument("--artifacts", default="ml/artifacts")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    os.makedirs(args.artifacts, exist_ok=True)
    df = pd.read_csv(args.data)

    reg_results = run_regression(df, args.out, args.artifacts)
    clf_results = run_classification(df, args.out, args.artifacts)
```

- [ ] **Step 6: Run and verify artifacts load and predict**

```bash
source venv/bin/activate && python3 ml/train_models.py
```

Expected: same metrics table as before, plus two `Saved ml/artifacts/....joblib` lines.

```bash
source venv/bin/activate && python3 -c "
import joblib, pandas as pd
reg = joblib.load('ml/artifacts/regression_model.joblib')
clf = joblib.load('ml/artifacts/classification_model.joblib')
row = pd.read_csv('ml/data/synthetic_employee_compensation.csv').iloc[[0]]
print('regression predict_ok:', reg.predict(row[['education_level','language_proficiency','job_role','department','age','experience_years','publications_count','projects_led_count','training_score','skills_score','boss_assessment_score']])[0])
row = row.copy()
row['expected_salary'] = row['expected_salary']
print('classification predict_proba_ok:', clf.predict_proba(row[['education_level','language_proficiency','job_role','department','age','experience_years','publications_count','projects_led_count','training_score','skills_score','boss_assessment_score','actual_salary','expected_salary']])[0])
"
```

Expected: both print a numeric prediction with no traceback.

- [ ] **Step 7: Commit**

```bash
git add ml/train_models.py ml/outputs ml/artifacts requirements.txt
git commit -m "$(cat <<'EOF'
feat: save trained model pipelines as loadable joblib artifacts

Compensation Insights needs to run inference without retraining;
train_models.py now saves the winning regression and classification
pipelines (preprocessor + estimator bundled as one sklearn Pipeline)
to ml/artifacts/ after each run. Also commits the ML prototype's
dependencies (pandas/numpy/scikit-learn/matplotlib/shap) to
requirements.txt from prior session work.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Scaffold the `compensation` Django app

**Files:**
- Create: `compensation/__init__.py`, `compensation/apps.py`, `compensation/urls.py`, `compensation/views.py`, `compensation/tests.py`, `compensation/templates/compensation/dashboard.html`
- Modify: `buscom/settings.py`, `buscom/urls.py`, `dashboard/static/dashboard/css/input.css`

**Interfaces:**
- Consumes: `dashboard.views._is_hr(user)` (existing).
- Produces: URL `compensation:audit_dashboard` resolving to `/compensation/`, returning 200 for HR and redirecting employees — later tasks build on this view and its template.

- [ ] **Step 1: Create the app package**

Create `compensation/__init__.py` (empty).

Create `compensation/apps.py`:

```python
from django.apps import AppConfig


class CompensationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "compensation"
```

- [ ] **Step 2: Register the app and mount its URLs**

In `buscom/settings.py`, change:

```python
    "django.contrib.staticfiles",
    "dashboard",
]
```

to:

```python
    "django.contrib.staticfiles",
    "dashboard",
    "compensation",
]
```

In `buscom/urls.py`, change:

```python
urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("dashboard.urls")),
]
```

to:

```python
urlpatterns = [
    path("admin/", admin.site.urls),
    path("compensation/", include("compensation.urls")),
    path("", include("dashboard.urls")),
]
```

- [ ] **Step 3: Extend the Tailwind content scanner to the new app**

In `dashboard/static/dashboard/css/input.css`, change:

```css
@import "tailwindcss" source(none);
@source "../../../templates";
@custom-variant dark (&:where(.dark, .dark *));
```

to:

```css
@import "tailwindcss" source(none);
@source "../../../templates";
@source "../../../../compensation/templates";
@custom-variant dark (&:where(.dark, .dark *));
```

- [ ] **Step 4: Write the failing test**

Create `compensation/tests.py`:

```python
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
```

- [ ] **Step 5: Run test to verify it fails**

```bash
source venv/bin/activate && python manage.py test compensation -v 2
```

Expected: FAIL — `NoReverseMatch` (no `compensation` app registered/no urls yet).

- [ ] **Step 6: Implement the view, urls, and placeholder template**

Create `compensation/views.py`:

```python
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render

from dashboard.views import _is_hr


@login_required
@user_passes_test(_is_hr, login_url="employee_self_service")
def audit_dashboard(request):
    return render(request, "compensation/dashboard.html", {})
```

Create `compensation/urls.py`:

```python
from django.urls import path

from . import views

app_name = "compensation"

urlpatterns = [
    path("", views.audit_dashboard, name="audit_dashboard"),
]
```

Create `compensation/templates/compensation/dashboard.html`:

```html
{% extends "dashboard/base.html" %}
{% block title %}Compensation Insights — BusCom{% endblock %}
{% block content %}
<p class="text-slate-500">Compensation Insights coming soon.</p>
{% endblock %}
```

- [ ] **Step 7: Run test to verify it passes, and check for regressions**

```bash
source venv/bin/activate && python manage.py test compensation dashboard -v 2
```

Expected: all PASS (the `dashboard` app's existing suite must still pass — this step touched shared `settings.py`/`urls.py`).

- [ ] **Step 8: Rebuild CSS**

```bash
./tailwindcss -i ./dashboard/static/dashboard/css/input.css -o ./dashboard/static/dashboard/css/output.css --minify
```

- [ ] **Step 9: Commit**

```bash
git add compensation buscom/settings.py buscom/urls.py dashboard/static/dashboard/css/input.css dashboard/static/dashboard/css/output.css
git commit -m "$(cat <<'EOF'
feat: scaffold compensation Django app

Adds a new HR-only compensation app with a placeholder dashboard
route, wired into buscom's URLs/settings and the Tailwind content
scanner. No database models — this app is data-layer-free by design.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Data layer — roster loading, scorecard, and predictions

**Files:**
- Create: `compensation/data.py`
- Modify: `compensation/tests.py`

**Interfaces:**
- Consumes: `ml.generate_dataset.{EDUCATION_POINTS, JOB_ROLES, clip, experience_score, project_score, publication_score}`, `ml.train_models.{CATEGORICAL_FEATURES, CLASSIFICATION_EXTRA_NUMERIC, NUMERIC_FEATURES}`.
- Produces: `get_roster() -> list[dict]` (1,000 rows, each with `predicted_salary`, `gap_pct`, `market_position_pct`, `satisfaction_probability`, `predicted_satisfaction`, `risk_level`, `scorecard`), `get_employee(employee_id) -> dict | None`, `compute_scorecard(row) -> dict`. Later tasks add `get_employee_detail()` (Task 6) and `predict_profile()` (Task 7) to this same file.

- [ ] **Step 1: Write the failing test**

Add to `compensation/tests.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
source venv/bin/activate && python manage.py test compensation.tests.ScorecardTests -v 2
```

Expected: FAIL — `ModuleNotFoundError: No module named 'compensation.data'`.

- [ ] **Step 3: Implement `compensation/data.py`**

```python
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
)
from ml.train_models import CATEGORICAL_FEATURES, CLASSIFICATION_EXTRA_NUMERIC, NUMERIC_FEATURES

INT_FIELDS = [
    "employee_id", "age", "experience_years", "publications_count",
    "projects_led_count", "training_score", "skills_score",
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


def compute_scorecard(row):
    categories = [
        {"key": "experience", "label": "Experience", "score": experience_score(row["experience_years"]), "max": 20},
        {"key": "education", "label": "Education", "score": EDUCATION_POINTS[row["education_level"]], "max": 20},
        {"key": "publications", "label": "Publications", "score": publication_score(row["publications_count"]), "max": 20},
        {"key": "projects", "label": "Project management", "score": project_score(row["projects_led_count"]), "max": 10},
        {"key": "training", "label": "Training", "score": row["training_score"], "max": 10},
        {"key": "skills", "label": "Skills", "score": row["skills_score"], "max": 10},
        {"key": "boss_assessment", "label": "Boss assessment", "score": row["boss_assessment_score"], "max": 10},
    ]
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
        roster.append({
            **row,
            "predicted_salary": predicted,
            "gap_pct": round((row["actual_salary"] - predicted) / predicted * 100, 1),
            "market_position_pct": market_position_pct(predicted, row["market_min_salary"], row["market_max_salary"]),
            "satisfaction_probability": probability,
            "predicted_satisfaction": "Satisfied" if probability >= 0.5 else "Dissatisfied",
            "risk_level": risk_level(probability),
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
```

- [ ] **Step 4: Run test to verify it passes**

```bash
source venv/bin/activate && python manage.py test compensation.tests.ScorecardTests -v 2
```

Expected: PASS.

- [ ] **Step 5: Sanity-check the roster loads end-to-end**

```bash
source venv/bin/activate && python manage.py shell -c "
from compensation.data import get_roster
roster = get_roster()
print(len(roster), 'employees')
print(roster[0]['name'], roster[0]['predicted_salary'], roster[0]['risk_level'])
"
```

Expected: `1000 employees` and a sensible sample row with no traceback.

- [ ] **Step 6: Commit**

```bash
git add compensation/data.py compensation/tests.py
git commit -m "$(cat <<'EOF'
feat: add compensation data layer (roster, scorecard, predictions)

compensation/data.py loads the synthetic roster and the two trained
model pipelines once per process, runs both models to get each
employee's predicted fair salary and satisfaction risk, and exposes a
scorecard reusing generate_dataset.py's exact point-rule formulas so
the two can't silently drift apart.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Compensation Audit Dashboard screen

**Files:**
- Modify: `compensation/views.py`, `compensation/templates/compensation/dashboard.html`, `compensation/tests.py`

**Interfaces:**
- Consumes: `compensation.data.get_roster()` (Task 4).
- Produces: `/compensation/` renders stat cards + a searchable/filterable/sortable/paginated table. No row links yet (added in Task 6) and no "Predict for a profile" link yet (added in Task 7).

- [ ] **Step 1: Write the failing tests**

Add to `compensation/tests.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
source venv/bin/activate && python manage.py test compensation.tests.AuditDashboardContentTests -v 2
```

Expected: FAIL — placeholder template doesn't contain "Headcount"/"Average Pay Gap", and the view provides no `departments`/`page_obj` context.

- [ ] **Step 3: Implement the view**

Replace `compensation/views.py` with:

```python
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.shortcuts import render

from dashboard.views import _is_hr

from . import data

SORT_FIELDS = {
    "name": lambda row: row["name"],
    "gap_pct": lambda row: row["gap_pct"],
    "predicted_salary": lambda row: row["predicted_salary"],
    "satisfaction_probability": lambda row: row["satisfaction_probability"],
}


@login_required
@user_passes_test(_is_hr, login_url="employee_self_service")
def audit_dashboard(request):
    roster = data.get_roster()

    query = request.GET.get("q", "").strip()
    department = request.GET.get("department", "all")
    risk = request.GET.get("risk", "all")
    sort = request.GET.get("sort", "name")

    filtered = roster
    if query:
        needle = query.lower()
        filtered = [r for r in filtered if needle in r["name"].lower() or needle in r["job_role"].lower()]
    if department != "all":
        filtered = [r for r in filtered if r["department"] == department]
    if risk != "all":
        filtered = [r for r in filtered if r["risk_level"] == risk]
    filtered = sorted(filtered, key=SORT_FIELDS.get(sort, SORT_FIELDS["name"]))

    paginator = Paginator(filtered, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    headcount = len(roster)
    avg_gap_pct = round(sum(r["gap_pct"] for r in roster) / headcount, 1) if headcount else 0
    underpaid_count = sum(1 for r in roster if r["gap_pct"] < -10)
    at_risk_count = sum(1 for r in roster if r["risk_level"] == "high")

    base_params = request.GET.copy()
    base_params.pop("page", None)

    return render(request, "compensation/dashboard.html", {
        "page_obj": page_obj,
        "query": query,
        "department": department,
        "risk": risk,
        "sort": sort,
        "departments": sorted({r["department"] for r in roster}),
        "headcount": headcount,
        "avg_gap_pct": avg_gap_pct,
        "underpaid_count": underpaid_count,
        "at_risk_count": at_risk_count,
        "base_query": base_params.urlencode(),
    })
```

- [ ] **Step 4: Implement the template**

Replace `compensation/templates/compensation/dashboard.html` with:

```html
{% extends "dashboard/base.html" %}
{% block title %}Compensation Insights — BusCom{% endblock %}
{% block content %}
<div x-data x-init="$nextTick(() => staggerRows($refs.tbody))">
  <div class="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-8">
    <div class="rounded-xl bg-white dark:bg-slate-800 shadow p-5" x-data x-init="animateCountUp($el.querySelector('.stat-value'), {{ headcount }})">
      <p class="text-sm text-slate-500">Headcount</p>
      <p class="stat-value text-3xl font-semibold mt-1">0</p>
    </div>
    <div class="rounded-xl bg-white dark:bg-slate-800 shadow p-5" x-data x-init="animateCountUp($el.querySelector('.stat-value'), {{ avg_gap_pct }}, { decimals: 1 })">
      <p class="text-sm text-slate-500">Average Pay Gap</p>
      <p class="mt-1"><span class="stat-value text-3xl font-semibold">0</span><span class="text-3xl font-semibold">%</span></p>
    </div>
    <div class="rounded-xl bg-white dark:bg-slate-800 shadow p-5" x-data x-init="animateCountUp($el.querySelector('.stat-value'), {{ underpaid_count }})">
      <p class="text-sm text-slate-500">Underpaid (&gt;10% below fair)</p>
      <p class="stat-value text-3xl font-semibold mt-1">0</p>
    </div>
    <div class="rounded-xl bg-white dark:bg-slate-800 shadow p-5" x-data x-init="animateCountUp($el.querySelector('.stat-value'), {{ at_risk_count }})">
      <p class="text-sm text-slate-500">Satisfaction Risk</p>
      <p class="stat-value text-3xl font-semibold mt-1">0</p>
    </div>
  </div>

  <div class="rounded-xl bg-white dark:bg-slate-800 shadow p-5">
    <form method="get" class="flex flex-wrap items-center gap-3 mb-4">
      <input type="text" name="q" value="{{ query }}" placeholder="Search name or role..."
             class="w-64 rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
      <select name="department" onchange="this.form.submit()"
              class="rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
        <option value="all" {% if department == "all" %}selected{% endif %}>All departments</option>
        {% for dept in departments %}
        <option value="{{ dept }}" {% if department == dept %}selected{% endif %}>{{ dept }}</option>
        {% endfor %}
      </select>
      <select name="risk" onchange="this.form.submit()"
              class="rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
        <option value="all" {% if risk == "all" %}selected{% endif %}>All risk levels</option>
        <option value="low" {% if risk == "low" %}selected{% endif %}>Likely satisfied</option>
        <option value="medium" {% if risk == "medium" %}selected{% endif %}>Uncertain</option>
        <option value="high" {% if risk == "high" %}selected{% endif %}>At risk</option>
      </select>
      <select name="sort" onchange="this.form.submit()"
              class="rounded-lg border border-slate-300 dark:border-slate-600 bg-transparent px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
        <option value="name" {% if sort == "name" %}selected{% endif %}>Sort: Name</option>
        <option value="gap_pct" {% if sort == "gap_pct" %}selected{% endif %}>Sort: Pay gap</option>
        <option value="predicted_salary" {% if sort == "predicted_salary" %}selected{% endif %}>Sort: Predicted salary</option>
        <option value="satisfaction_probability" {% if sort == "satisfaction_probability" %}selected{% endif %}>Sort: Satisfaction</option>
      </select>
      <button type="submit"
              class="rounded-lg bg-indigo-600 hover:bg-indigo-500 active:scale-[0.98] transition text-white text-sm font-medium px-4 py-1.5">
        Filter
      </button>
    </form>

    {% if page_obj.paginator.count == 0 %}
    <p class="text-slate-500 text-sm py-8 text-center">No employees match these filters.</p>
    {% else %}
    <table class="w-full text-sm">
      <thead>
        <tr class="text-left text-slate-500 border-b border-slate-200 dark:border-slate-700">
          <th class="py-2">Name</th>
          <th class="py-2">Role</th>
          <th class="py-2">Department</th>
          <th class="py-2 text-right">Actual</th>
          <th class="py-2 text-right">Predicted Fair</th>
          <th class="py-2 text-right">Gap</th>
          <th class="py-2">Satisfaction</th>
        </tr>
      </thead>
      <tbody x-ref="tbody">
        {% for employee in page_obj %}
        <tr class="border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition">
          <td class="py-2 flex items-center gap-2">
            <span class="w-7 h-7 rounded-full bg-indigo-100 dark:bg-indigo-900 text-indigo-600 dark:text-indigo-300 text-xs flex items-center justify-center font-medium">{{ employee.initials }}</span>
            <span>{{ employee.name }}</span>
          </td>
          <td class="py-2">{{ employee.job_role }}</td>
          <td class="py-2">{{ employee.department }}</td>
          <td class="py-2 text-right">৳{{ employee.actual_salary }}</td>
          <td class="py-2 text-right">৳{{ employee.predicted_salary }}</td>
          <td class="py-2 text-right {% if employee.gap_pct < 0 %}text-red-500{% else %}text-emerald-600{% endif %}">{{ employee.gap_pct }}%</td>
          <td class="py-2">
            {% if employee.risk_level == "low" %}
            <span class="rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300 text-xs px-2 py-0.5">Likely satisfied</span>
            {% elif employee.risk_level == "medium" %}
            <span class="rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300 text-xs px-2 py-0.5">Uncertain</span>
            {% else %}
            <span class="rounded-full bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300 text-xs px-2 py-0.5">At risk</span>
            {% endif %}
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>

    <div class="flex items-center justify-between mt-4 text-sm text-slate-500">
      <span>Page {{ page_obj.number }} of {{ page_obj.paginator.num_pages }} &middot; {{ page_obj.paginator.count }} employees</span>
      <div class="flex gap-2">
        {% if page_obj.has_previous %}
        <a href="?{{ base_query }}&page={{ page_obj.previous_page_number }}"
           class="rounded-lg border border-slate-300 dark:border-slate-600 px-3 py-1.5 hover:bg-slate-100 dark:hover:bg-slate-700 transition">Previous</a>
        {% endif %}
        {% if page_obj.has_next %}
        <a href="?{{ base_query }}&page={{ page_obj.next_page_number }}"
           class="rounded-lg border border-slate-300 dark:border-slate-600 px-3 py-1.5 hover:bg-slate-100 dark:hover:bg-slate-700 transition">Next</a>
        {% endif %}
      </div>
    </div>
    {% endif %}
  </div>
</div>
{% endblock %}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
source venv/bin/activate && python manage.py test compensation -v 2
```

Expected: all PASS.

- [ ] **Step 6: Rebuild CSS**

```bash
./tailwindcss -i ./dashboard/static/dashboard/css/input.css -o ./dashboard/static/dashboard/css/output.css --minify
```

- [ ] **Step 7: Commit**

```bash
git add compensation/views.py compensation/templates/compensation/dashboard.html compensation/tests.py dashboard/static/dashboard/css/output.css
git commit -m "$(cat <<'EOF'
feat: build compensation audit dashboard screen

Stat cards (headcount, avg pay gap, underpaid count, satisfaction-risk
count) plus a searchable/filterable/sortable/paginated table over the
1,000-row synthetic roster.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Employee Compensation Detail screen

**Files:**
- Modify: `compensation/data.py`, `compensation/views.py`, `compensation/urls.py`, `compensation/templates/compensation/dashboard.html`, `compensation/tests.py`
- Create: `compensation/templates/compensation/detail.html`, `compensation/templates/compensation/partials/prediction_cards.html`

**Interfaces:**
- Consumes: `compensation.data.{get_employee, top_factors, CATEGORICAL_FEATURES, NUMERIC_FEATURES, CLASSIFICATION_EXTRA_NUMERIC}`.
- Produces: `compensation.data.get_employee_detail(employee_id) -> dict | None` (adds `regression_top_factors`/`classification_top_factors` to a roster row). URL `compensation:employee_detail`. The `compensation/partials/prediction_cards.html` partial, reused by Task 7's predict screen, renders from context variables `card` (a dict with `scorecard`, `predicted_salary`, `market_min_salary`, `market_max_salary`, `market_position_pct`, and optionally `actual_salary`, `gap_pct`, `regression_top_factors`, `satisfaction_probability`, `predicted_satisfaction`, `risk_level`, `classification_top_factors`) and `salary_label` (str).

- [ ] **Step 1: Write the failing tests**

Add to `compensation/tests.py`:

```python
from compensation import data


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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
source venv/bin/activate && python manage.py test compensation.tests.EmployeeDetailTests -v 2
```

Expected: FAIL — `NoReverseMatch` (route doesn't exist yet).

- [ ] **Step 3: Add `get_employee_detail` to `compensation/data.py`**

Append to `compensation/data.py`:

```python
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
```

- [ ] **Step 4: Add the view and route**

In `compensation/views.py`, add the import and view:

```python
from django.http import Http404
```

(add alongside the existing `django.contrib.auth.decorators`/`django.core.paginator`/`django.shortcuts` imports)

```python
@login_required
@user_passes_test(_is_hr, login_url="employee_self_service")
def employee_detail(request, employee_id):
    employee = data.get_employee_detail(employee_id)
    if employee is None:
        raise Http404("Employee not found.")
    return render(request, "compensation/detail.html", {
        "employee": employee,
        "card": employee,
        "salary_label": "Actual salary",
    })
```

In `compensation/urls.py`, change:

```python
urlpatterns = [
    path("", views.audit_dashboard, name="audit_dashboard"),
]
```

to:

```python
urlpatterns = [
    path("", views.audit_dashboard, name="audit_dashboard"),
    path("<int:employee_id>/", views.employee_detail, name="employee_detail"),
]
```

- [ ] **Step 5: Create the shared prediction-cards partial**

Create `compensation/templates/compensation/partials/prediction_cards.html`:

```html
<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
  <div class="rounded-xl bg-white dark:bg-slate-800 shadow p-6">
    <h2 class="font-semibold mb-4">Compensation Scorecard</h2>
    <div class="space-y-2 text-sm">
      {% for category in card.scorecard.categories %}
      <div>
        <div class="flex justify-between mb-1">
          <span class="text-slate-500">{{ category.label }}</span>
          <span>{{ category.score }} / {{ category.max }}</span>
        </div>
        <div class="h-1.5 rounded-full bg-slate-100 dark:bg-slate-700">
          <div class="h-1.5 rounded-full bg-indigo-500" style="width: {% widthratio category.score category.max 100 %}%"></div>
        </div>
      </div>
      {% endfor %}
    </div>
    <div class="flex justify-between text-sm font-semibold border-t border-slate-200 dark:border-slate-700 pt-3 mt-3">
      <span>Total</span>
      <span>{{ card.scorecard.total }} / {{ card.scorecard.max_total }}</span>
    </div>
  </div>

  <div class="rounded-xl bg-white dark:bg-slate-800 shadow p-6">
    <h2 class="font-semibold mb-4">Predicted Fair Salary</h2>
    <p class="text-3xl font-semibold mb-1">৳{{ card.predicted_salary }}</p>
    <p class="text-sm text-slate-500 mb-4">Market band: ৳{{ card.market_min_salary }} – ৳{{ card.market_max_salary }}</p>
    <div class="relative h-2 rounded-full bg-slate-100 dark:bg-slate-700 mb-4">
      <div class="absolute top-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-slate-400" style="left: {{ card.market_position_pct }}%"></div>
    </div>
    {% if card.actual_salary %}
    <div class="flex justify-between text-sm">
      <span class="text-slate-500">{{ salary_label }}</span>
      <span>৳{{ card.actual_salary }}</span>
    </div>
    <div class="flex justify-between text-sm">
      <span class="text-slate-500">Gap</span>
      <span class="{% if card.gap_pct < 0 %}text-red-500{% else %}text-emerald-600{% endif %}">{{ card.gap_pct }}%</span>
    </div>
    {% endif %}
    {% if card.regression_top_factors %}
    <div class="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
      <p class="text-sm text-slate-500 mb-2">Top factors</p>
      <ul class="text-sm space-y-1">
        {% for factor in card.regression_top_factors %}
        <li>{{ factor.label }} <span class="{% if factor.direction == '+' %}text-emerald-600{% else %}text-red-500{% endif %}">({{ factor.direction }})</span></li>
        {% endfor %}
      </ul>
    </div>
    {% endif %}
  </div>
</div>

{% if card.satisfaction_probability %}
<div class="rounded-xl bg-white dark:bg-slate-800 shadow p-6 mb-6">
  <h2 class="font-semibold mb-4">Predicted Satisfaction</h2>
  <div class="flex items-center gap-3 mb-4">
    {% if card.risk_level == "low" %}
    <span class="rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300 text-xs px-2 py-0.5">Likely satisfied</span>
    {% elif card.risk_level == "medium" %}
    <span class="rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300 text-xs px-2 py-0.5">Uncertain</span>
    {% else %}
    <span class="rounded-full bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300 text-xs px-2 py-0.5">At risk</span>
    {% endif %}
    <span class="text-sm text-slate-500">{{ card.predicted_satisfaction }} ({{ card.satisfaction_probability }} probability)</span>
  </div>
  <ul class="text-sm space-y-1">
    {% for factor in card.classification_top_factors %}
    <li>{{ factor.label }} <span class="{% if factor.direction == '+' %}text-emerald-600{% else %}text-red-500{% endif %}">({{ factor.direction }})</span></li>
    {% endfor %}
  </ul>
</div>
{% endif %}
```

- [ ] **Step 6: Create the detail template**

Create `compensation/templates/compensation/detail.html`:

```html
{% extends "dashboard/base.html" %}
{% block title %}{{ employee.name }} — Compensation — BusCom{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto" x-data x-init="fadeInPage($el)">
  <div class="rounded-xl bg-white dark:bg-slate-800 shadow p-6 mb-6">
    <div class="flex items-center gap-3 mb-4">
      <span class="w-12 h-12 rounded-full bg-indigo-100 dark:bg-indigo-900 text-indigo-600 dark:text-indigo-300 flex items-center justify-center font-medium">
        {{ employee.initials }}
      </span>
      <div>
        <p class="font-semibold">{{ employee.name }}</p>
        <p class="text-sm text-slate-500">{{ employee.job_role }} &middot; {{ employee.department }}</p>
      </div>
    </div>
    <dl class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
      <div><dt class="text-slate-500">Age</dt><dd>{{ employee.age }}</dd></div>
      <div><dt class="text-slate-500">Experience</dt><dd>{{ employee.experience_years }} yrs</dd></div>
      <div><dt class="text-slate-500">Education</dt><dd>{{ employee.education_level }}</dd></div>
      <div><dt class="text-slate-500">Language</dt><dd>{{ employee.language_proficiency }}</dd></div>
      <div><dt class="text-slate-500">Publications</dt><dd>{{ employee.publications_count }}</dd></div>
      <div><dt class="text-slate-500">Projects led</dt><dd>{{ employee.projects_led_count }}</dd></div>
      <div><dt class="text-slate-500">Training score</dt><dd>{{ employee.training_score }} / 10</dd></div>
      <div><dt class="text-slate-500">Skills score</dt><dd>{{ employee.skills_score }} / 10</dd></div>
    </dl>
  </div>

  {% include "compensation/partials/prediction_cards.html" %}
</div>
{% endblock %}
```

- [ ] **Step 7: Make dashboard rows clickable**

In `compensation/templates/compensation/dashboard.html`, change:

```html
        {% for employee in page_obj %}
        <tr class="border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition">
```

to:

```html
        {% for employee in page_obj %}
        <tr class="border-b border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition cursor-pointer"
            onclick="window.location='{% url 'compensation:employee_detail' employee.employee_id %}'">
```

- [ ] **Step 8: Run tests to verify they pass**

```bash
source venv/bin/activate && python manage.py test compensation -v 2
```

Expected: all PASS.

- [ ] **Step 9: Rebuild CSS**

```bash
./tailwindcss -i ./dashboard/static/dashboard/css/input.css -o ./dashboard/static/dashboard/css/output.css --minify
```

- [ ] **Step 10: Commit**

```bash
git add compensation dashboard/static/dashboard/css/output.css
git commit -m "$(cat <<'EOF'
feat: build employee compensation detail screen

Adds get_employee_detail() (per-instance top-factor explanations for
both models), the detail route/template, a shared prediction-cards
partial (also used by the predict-for-a-profile screen), and makes
audit dashboard rows clickable through to it.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Predict for a Profile screen

**Files:**
- Modify: `compensation/data.py`, `compensation/views.py`, `compensation/urls.py`, `compensation/templates/compensation/dashboard.html`, `compensation/tests.py`
- Create: `compensation/forms.py`, `compensation/templates/compensation/predict.html`

**Interfaces:**
- Consumes: `ml.generate_dataset.{EDUCATION_POINTS, JOB_ROLES, LANGUAGE_LEVELS}`.
- Produces: `compensation.data.predict_profile(profile: dict) -> dict` (ad-hoc, not persisted). URL `compensation:predict_profile`.

- [ ] **Step 1: Write the failing tests**

Add to `compensation/tests.py`:

```python
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
            "training_score": 7,
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

    def test_invalid_profile_shows_errors(self):
        response = self.client.post(reverse("compensation:predict_profile"), {"job_role": "Software Engineer"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please correct the errors below.")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
source venv/bin/activate && python manage.py test compensation.tests.PredictProfileTests -v 2
```

Expected: FAIL — `NoReverseMatch` (route doesn't exist yet).

- [ ] **Step 3: Add `predict_profile` to `compensation/data.py`**

Append to `compensation/data.py`:

```python
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

    if profile.get("proposed_salary"):
        clf_row = row_df.copy()
        clf_row["actual_salary"] = profile["proposed_salary"]
        clf_row["expected_salary"] = predicted_salary
        probability = round(float(_predict_satisfaction(classification_pipeline, clf_row)[0]), 2)
        result["satisfaction_probability"] = probability
        result["predicted_satisfaction"] = "Satisfied" if probability >= 0.5 else "Dissatisfied"
        result["risk_level"] = risk_level(probability)
        result["gap_pct"] = round((profile["proposed_salary"] - predicted_salary) / predicted_salary * 100, 1)
        result["classification_top_factors"] = top_factors(
            classification_pipeline, clf_row[CATEGORICAL_FEATURES + NUMERIC_FEATURES + CLASSIFICATION_EXTRA_NUMERIC]
        )

    return result
```

- [ ] **Step 4: Create the form**

Create `compensation/forms.py`:

```python
from django import forms

from ml.generate_dataset import EDUCATION_POINTS, JOB_ROLES, LANGUAGE_LEVELS

JOB_ROLE_CHOICES = [(role, role) for role, *_ in JOB_ROLES]
EDUCATION_CHOICES = [(level, level) for level in EDUCATION_POINTS]
LANGUAGE_CHOICES = [(level, level) for level in LANGUAGE_LEVELS]

INPUT_CLASS = (
    "w-full rounded-lg border border-slate-300 dark:border-slate-600 "
    "bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-2 "
    "focus:ring-indigo-500"
)


class PredictProfileForm(forms.Form):
    job_role = forms.ChoiceField(choices=JOB_ROLE_CHOICES)
    age = forms.IntegerField(min_value=18, max_value=70)
    experience_years = forms.IntegerField(min_value=0, max_value=40)
    education_level = forms.ChoiceField(choices=EDUCATION_CHOICES)
    publications_count = forms.IntegerField(min_value=0, max_value=20)
    projects_led_count = forms.IntegerField(min_value=0, max_value=20)
    training_score = forms.IntegerField(min_value=0, max_value=10)
    skills_score = forms.IntegerField(min_value=0, max_value=10)
    boss_assessment_score = forms.IntegerField(min_value=0, max_value=10)
    language_proficiency = forms.ChoiceField(choices=LANGUAGE_CHOICES)
    proposed_salary = forms.IntegerField(min_value=0, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = INPUT_CLASS
```

- [ ] **Step 5: Add the view and route**

In `compensation/views.py`, add the import:

```python
from .forms import PredictProfileForm
```

Add the view:

```python
@login_required
@user_passes_test(_is_hr, login_url="employee_self_service")
def predict_profile(request):
    result = None
    if request.method == "POST":
        form = PredictProfileForm(request.POST)
        if form.is_valid():
            result = data.predict_profile(form.cleaned_data)
            if result.get("proposed_salary"):
                result["actual_salary"] = result["proposed_salary"]
    else:
        form = PredictProfileForm()

    return render(request, "compensation/predict.html", {
        "form": form,
        "result": result,
        "card": result,
        "salary_label": "Proposed salary",
    })
```

In `compensation/urls.py`, change:

```python
urlpatterns = [
    path("", views.audit_dashboard, name="audit_dashboard"),
    path("<int:employee_id>/", views.employee_detail, name="employee_detail"),
]
```

to:

```python
urlpatterns = [
    path("", views.audit_dashboard, name="audit_dashboard"),
    path("predict/", views.predict_profile, name="predict_profile"),
    path("<int:employee_id>/", views.employee_detail, name="employee_detail"),
]
```

(the `predict/` route must be listed before `<int:employee_id>/` — otherwise Django would try to parse `"predict"` as an integer employee id and 404.)

- [ ] **Step 6: Create the predict template**

Create `compensation/templates/compensation/predict.html`:

```html
{% extends "dashboard/base.html" %}
{% block title %}Predict for a Profile — Compensation — BusCom{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto" x-data x-init="fadeInPage($el)">
  <div class="rounded-xl bg-white dark:bg-slate-800 shadow p-6 mb-6">
    <h1 class="font-semibold mb-4">Predict for a Profile</h1>
    {% if form.errors %}
    <p class="text-red-500 text-sm mb-3">Please correct the errors below.</p>
    {% endif %}
    <form method="post" class="grid grid-cols-1 sm:grid-cols-2 gap-3">
      {% csrf_token %}
      {% for field in form %}
      <div>
        <label class="block text-sm text-slate-500 mb-1">{{ field.label }}</label>
        {{ field }}
        {% if field.errors %}<p class="text-red-500 text-xs mt-1">{{ field.errors.0 }}</p>{% endif %}
      </div>
      {% endfor %}
      <div class="sm:col-span-2 flex justify-end">
        <button type="submit"
                class="rounded-lg bg-indigo-600 hover:bg-indigo-500 active:scale-[0.98] transition text-white text-sm font-medium px-4 py-1.5">
          Predict
        </button>
      </div>
    </form>
  </div>

  {% if result %}
  {% include "compensation/partials/prediction_cards.html" %}
  {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 7: Add the dashboard link to this screen**

In `compensation/templates/compensation/dashboard.html`, change:

```html
      <button type="submit"
              class="rounded-lg bg-indigo-600 hover:bg-indigo-500 active:scale-[0.98] transition text-white text-sm font-medium px-4 py-1.5">
        Filter
      </button>
    </form>
```

to:

```html
      <button type="submit"
              class="rounded-lg bg-indigo-600 hover:bg-indigo-500 active:scale-[0.98] transition text-white text-sm font-medium px-4 py-1.5">
        Filter
      </button>
      <a href="{% url 'compensation:predict_profile' %}"
         class="ml-auto rounded-lg border border-slate-300 dark:border-slate-600 px-4 py-1.5 text-sm hover:bg-slate-100 dark:hover:bg-slate-700 transition">
        Predict for a profile
      </a>
    </form>
```

- [ ] **Step 8: Run tests to verify they pass**

```bash
source venv/bin/activate && python manage.py test compensation -v 2
```

Expected: all PASS.

- [ ] **Step 9: Rebuild CSS**

```bash
./tailwindcss -i ./dashboard/static/dashboard/css/input.css -o ./dashboard/static/dashboard/css/output.css --minify
```

- [ ] **Step 10: Commit**

```bash
git add compensation dashboard/static/dashboard/css/output.css
git commit -m "$(cat <<'EOF'
feat: build predict-for-a-profile screen

A what-if form (not persisted) that runs the same trained pipelines
used by the audit dashboard against a hand-entered candidate profile,
optionally showing satisfaction risk when a proposed salary is given.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Sidebar link and final verification pass

**Files:**
- Modify: `dashboard/templates/dashboard/partials/sidebar.html`, `compensation/tests.py`

**Interfaces:**
- Consumes: everything from Tasks 3–7.
- Produces: HR users see a "Compensation Insights" sidebar link; the full test suite passes together.

- [ ] **Step 1: Write the failing test**

Add to `compensation/tests.py`:

```python
class SidebarLinkTests(TestCase):
    def test_hr_sees_compensation_link(self):
        self.client.login(username="hr_admin", password="buscom-hr-2026")
        response = self.client.get(reverse("hr_dashboard"))
        self.assertContains(response, "Compensation Insights")

    def test_employee_does_not_see_compensation_link(self):
        self.client.login(username="amara_okafor", password="buscom-emp-2026")
        response = self.client.get(reverse("employee_self_service"))
        self.assertNotContains(response, "Compensation Insights")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
source venv/bin/activate && python manage.py test compensation.tests.SidebarLinkTests -v 2
```

Expected: FAIL — link not present yet.

- [ ] **Step 3: Add the sidebar link**

In `dashboard/templates/dashboard/partials/sidebar.html`, change:

```html
    {% if user.role == "hr" %}
      <a href="{% url 'hr_dashboard' %}" class="block rounded-lg px-3 py-2 text-sm font-medium hover:bg-slate-100 dark:hover:bg-slate-700 transition">Dashboard</a>
    {% else %}
```

to:

```html
    {% if user.role == "hr" %}
      <a href="{% url 'hr_dashboard' %}" class="block rounded-lg px-3 py-2 text-sm font-medium hover:bg-slate-100 dark:hover:bg-slate-700 transition">Dashboard</a>
      <a href="{% url 'compensation:audit_dashboard' %}" class="block rounded-lg px-3 py-2 text-sm font-medium hover:bg-slate-100 dark:hover:bg-slate-700 transition">Compensation Insights</a>
    {% else %}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
source venv/bin/activate && python manage.py test compensation.tests.SidebarLinkTests -v 2
```

Expected: PASS.

- [ ] **Step 5: Rebuild CSS**

```bash
./tailwindcss -i ./dashboard/static/dashboard/css/input.css -o ./dashboard/static/dashboard/css/output.css --minify
```

- [ ] **Step 6: Run the full test suite**

```bash
source venv/bin/activate && python manage.py test -v 2
```

Expected: every test in both `dashboard` and `compensation` PASSES.

- [ ] **Step 7: Manual in-browser verification**

Start the dev server (`python manage.py runserver`), log in as `hr_admin` / `buscom-hr-2026`, and check:
- Sidebar shows "Compensation Insights" and it navigates to `/compensation/`.
- Stat cards animate in; search, department filter, risk filter, and sort all work; pagination moves between pages.
- Clicking a row opens its detail page with a correct scorecard (totals to 100), predicted-vs-actual salary, and top factors.
- "Predict for a profile" form validates (try submitting empty), then produces a prediction; adding a proposed salary also produces a satisfaction card.
- Toggle dark mode and confirm all three screens still read correctly.

- [ ] **Step 8: Commit**

```bash
git add dashboard/templates/dashboard/partials/sidebar.html compensation/tests.py dashboard/static/dashboard/css/output.css
git commit -m "$(cat <<'EOF'
feat: link Compensation Insights from the HR sidebar

Final integration step — HR users can now reach the audit dashboard,
employee detail, and predict-for-a-profile screens from navigation.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```
