# Compensation Insights Design

Date: 2026-08-16

## Purpose

BusCom's frontend (see `2026-08-09-buscom-frontend-design.md`) explicitly
deferred salary business logic. This spec defines that logic as an
explainable ML framework and adds an HR-facing feature, **Compensation
Insights**, that surfaces it inside BusCom:

1. Predict an employee's expected ("fair") salary from demographic,
   educational, professional, and skill-related attributes.
2. Compare that prediction against the employee's actual salary and the
   market band for their role to find their relative compensation
   position.
3. Predict whether the employee is likely satisfied or dissatisfied with
   their compensation.
4. Explain, in plain language, which factors drove each prediction.

This spec covers the web app screens and how the already-built ML
pipeline (`ml/generate_dataset.py`, `ml/train_models.py`) is wired into
Django. It does not change the existing login/HR-dashboard/employee
self-service/payslip screens.

## Prior work this builds on

- `ml/generate_dataset.py` — generates the synthetic dataset, including
  the 100-point rule-based compensation scorecard (experience, education,
  publications, project management, training, skills, boss assessment).
- `ml/train_models.py` — trains and compares regression (expected salary)
  and classification (satisfaction) models, and produces SHAP
  explainability plots as static artifacts in `ml/outputs/`.
- `ml/data/synthetic_employee_compensation.csv` — 1,000-row synthetic
  dataset used as the demo roster for this feature.

## Additions to prior work

Two small changes to the already-built pieces, needed before the web app
can consume them:

1. **`ml/generate_dataset.py`** gains a `name` and `initials` column (a
   small synthetic first/last name pool), so the UI can display people
   rather than `Employee #482`. Regenerate the CSV after this change.
2. **`ml/train_models.py`** gains a step that serializes the winning
   regression and classification pipelines (preprocessor + fitted
   estimator, as single sklearn `Pipeline` objects) via `joblib.dump` to
   `ml/artifacts/regression_model.joblib` and
   `ml/artifacts/classification_model.joblib`. These are what the Django
   app loads at runtime — it never retrains.

## Stack

Same as the rest of BusCom: Django, server-rendered templates, Tailwind
CSS (standalone CLI), Alpine.js, GSAP. New Python dependency at runtime:
`joblib` (already installed transitively via scikit-learn) to load the
saved model artifacts. No new frontend dependencies.

## Architecture

A new Django app, `compensation`, added to `INSTALLED_APPS`, mounted at
`/compensation/`. All views require HR role (same `_is_hr` pattern used
in `dashboard/views.py`); an employee-role user is redirected the same
way `hr_dashboard` currently handles it.

Templates extend `dashboard/templates/dashboard/base.html` so the new
screens share the sidebar, topbar, and theme toggle. A new sidebar link
("Compensation Insights") is added to
`dashboard/templates/dashboard/partials/sidebar.html`, visible only to
HR.

**No new database models.** Consistent with BusCom's existing philosophy
("mocked data now, real persistence later" — see the frontend spec), the
1,000-row roster and its predictions are loaded once into an in-process
cache rather than migrated into SQLite. This keeps the data-layer swap to
real persistence a future, isolated step rather than something this
feature needs to solve now.

### Data loading (`compensation/data.py`)

On first access (module-level lazy singleton — simpler than wiring
`AppConfig.ready()`, and avoids doing model-loading work during
`manage.py migrate`/tests that don't need it):

1. Load `ml/data/synthetic_employee_compensation.csv` into a list of
   dicts (`csv.DictReader`, matching the stdlib-only style already used
   in `generate_dataset.py` — no need to introduce pandas as a Django
   runtime dependency for this).
2. Load the two joblib pipelines.
3. For each row, run the regression pipeline to get `predicted_salary`
   (the model's own prediction, not the CSV's ground-truth
   `expected_salary` column, so the UI reflects what the trained model
   actually says). Then run the classification pipeline, substituting
   this `predicted_salary` value in place of the CSV's `expected_salary`
   column (the classifier was trained on a column named
   `expected_salary`; at inference time the app's own regression output
   is what fills that slot, not the synthetic ground truth) to get
   `satisfaction_probability`/`predicted_satisfaction`.
4. Compute `gap_pct = (actual_salary - predicted_salary) / predicted_salary`.
5. Compute the rule-based scorecard by importing the same scoring
   functions used in `generate_dataset.py`
   (`experience_score`, `EDUCATION_POINTS`, `publication_score`,
   `project_score`) rather than reimplementing them, so the UI scorecard
   and the dataset generator can't drift apart.
6. Compute top-3 contributing factors per employee as closed-form
   `coefficient × standardized feature value` terms from the linear
   models (both winning models — `LinearRegression`,
   `LogisticRegression` — support this directly; no SHAP dependency
   needed at request time). Map raw feature names (e.g.
   `cat__job_role_Finance Manager`) to plain-language labels (e.g. "Job
   role: Finance Manager") via a small lookup table.

The resulting list of enriched employee dicts is cached in a module-level
variable for the process lifetime (fine for a prototype; a dev-server
reload recomputes it, which takes well under a second per the earlier
timing).

## Screens

### 1. Compensation Audit Dashboard — `/compensation/`

- Stat cards (animated count-up, matching the existing HR dashboard
  pattern): headcount, average gap %, count underpaid (gap < -10%), count
  at satisfaction risk (probability of "Satisfied" < 0.5).
- Table: name, job role, department, actual salary, predicted salary,
  gap %, satisfaction-risk chip (color-coded: green/amber/red). Search by
  name/role, filter by department and risk level, sortable columns,
  paginated (Django `Paginator`, 25/page — 1,000 rows needs pagination
  where the existing 5-row employee directory didn't).
- Row click → detail view.

### 2. Employee Compensation Detail — `/compensation/<id>/`

- Profile card: age, experience, education, publications, projects,
  training/skills/boss-assessment scores, language proficiency, job
  role/department.
- Rule-based scorecard: the 7 categories from your point rules, each
  shown against its max, summing to /100 — the transparent,
  human-auditable half of the explanation.
- ML prediction card: predicted fair salary vs. actual salary, gap %, and
  where they sit within their role's market band (min–max bar with a
  marker).
- Satisfaction card: predicted label + probability, top 3 factors in
  plain language with direction (e.g. "Actual salary 12% below predicted
  fair salary (–)", "Strong boss assessment (+)").

### 3. Predict for a Profile — `/compensation/predict/`

- Form fields matching the model's inputs: job role (select, drives
  department + market band display), age, experience years, education
  level, publications count, projects led, training score, skills score,
  boss assessment score, language proficiency, and an optional "proposed
  salary" field.
- On submit (POST, not saved anywhere — purely computed and rendered):
  shows the same prediction/market-band card as the detail view. If a
  proposed salary was given, also shows the satisfaction card. This is a
  what-if tool for offer decisions, not a record-creating form.

## Error handling

- Empty state when filters match nothing ("No employees match these
  filters"), consistent with the existing `empty_state.html` pattern.
- Predict-for-profile form: inline validation matching the existing
  add/edit employee modal's pattern (e.g. experience 0–40, scores 0–10).
- Missing CSV or joblib artifact at data-load time is a hard failure
  (raise, don't silently fall back) — this is a prototype; a broken data
  pipeline should be obvious immediately, not masked.

## Testing

- Django smoke tests: each new route returns 200 for an HR-role user and
  redirects for an employee-role user, matching the existing test style
  for `hr_dashboard`.
- Unit test asserting `compensation/data.py`'s scorecard computation
  matches `generate_dataset.py`'s formula for a handful of known inputs,
  so the two can't silently drift apart.
- Manual in-browser check of the three screens (motion, search/filter,
  form validation) — no automated visual testing, consistent with the
  rest of BusCom.

## Out of scope (for this pass)

- Editing employee records or persisting predictions to a database.
- Employee self-service view of their own compensation position (HR-only
  for now, per your answer).
- Retraining models from the UI — retraining stays a manual
  `python ml/train_models.py` step.
