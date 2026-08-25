# Real Data Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace BusCom's four disconnected employee data sources with one — employees register, their data lands in the `User` table, and every screen and both models read from there.

**Architecture:** `compensation/data.py` already isolates storage behind `get_roster()` / `get_employee_detail()` / `predict_profile()`, so swapping its loader from CSV to the ORM carries the whole feature over without touching templates, filters, sorting or pagination. The synthetic dataset stays as an immutable training base that never appears in the UI; real rows are appended at training time only, via separate generated CSVs.

**Tech Stack:** Django 5.2.17, SQLite, scikit-learn 1.9, pandas 3.0, joblib, Tailwind (standalone CLI), Alpine.js, GSAP.

**Spec:** `docs/superpowers/specs/2026-08-25-real-data-pipeline-design.md`

## Global Constraints

- Run everything through the project venv: `venv/bin/python`, never bare `python3`.
- Full test command: `venv/bin/python manage.py test`. It must pass at the end of every task.
- The 100-point scorecard: experience `min(20, years × 2)`, education PhD 20 / MSc 15 / BSc 10 / Diploma 5 / High School 0, publications `min(20, count × 2)`, projects `min(10, count × 2)`, training `min(10, count × 2)`, skills self-rated 0–10 as-is, boss assessment flat `10`. Total 100.
- Regression target is `actual_salary`. UI copy says "Predicted Market Salary", never "Fair".
- `boss_assessment_score` stays a model feature and stays `10` for every real employee. This is a decided trade-off — do not "fix" it.
- Currency is BDT (`৳`), monthly. No `$` anywhere in employee-facing copy.
- `ml/data/synthetic_employee_compensation.csv` is regenerated only by `ml/generate_dataset.py`. No other code writes to it.
- Never commit `db.sqlite3` (already gitignored).
- Commit after each task with the message given in its final step.

---

### Task 1: New marking logic

Redefine publications and training scoring in the generator, add `trainings_count` as the stored raw value, and update the scorecard that HR reads.

**Files:**
- Modify: `ml/generate_dataset.py`
- Modify: `compensation/data.py:32-40` (INT_FIELDS), `:106-130` (descriptions + `compute_scorecard`)
- Test: `compensation/tests.py:6-38` (`ScorecardTests`)

**Interfaces:**
- Consumes: nothing.
- Produces: `ml.generate_dataset.publication_score(count) -> int`, `ml.generate_dataset.training_score(count) -> int`. CSV column `trainings_count` (raw count) and `training_score` (derived mark). `compute_scorecard(row)` now reads `row["trainings_count"]`.

- [ ] **Step 1: Write the failing tests**

Replace the whole `ScorecardTests` class in `compensation/tests.py` with:

```python
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
```

Change the imports at the top of `compensation/tests.py` from:

```python
from compensation.data import compute_scorecard
```

to:

```python
from compensation.data import compute_scorecard
from ml.generate_dataset import publication_score, training_score
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `venv/bin/python manage.py test compensation.tests.ScorecardTests -v 2`
Expected: FAIL — `ImportError: cannot import name 'training_score'`.

- [ ] **Step 3: Update the scoring functions in `ml/generate_dataset.py`**

Replace:

```python
def publication_score(count):
    return 20 if count >= 4 else count * 5
```

with:

```python
def publication_score(count):
    return min(20, count * 2)


def training_score(count):
    return min(10, count * 2)
```

- [ ] **Step 4: Make training a count in `generate_row`**

In `ml/generate_dataset.py`, replace this line:

```python
    training_score = round(rng.betavariate(2, 2) * 10)
```

with:

```python
    trainings_count = rng.choices(
        [0, 1, 2, 3, 4, 5, 6, 7], weights=[12, 18, 20, 18, 14, 9, 6, 3], k=1
    )[0]
    train_score = training_score(trainings_count)
```

Then replace the two later uses of the old local. Change:

```python
    performance_signal = (training_score + skills_score) / 2
```

to:

```python
    performance_signal = (train_score + skills_score) / 2
```

and change:

```python
    compensation_score = (
        exp_score + edu_score + pub_score + proj_score
        + training_score + skills_score + boss_assessment_score
    )
```

to:

```python
    compensation_score = (
        exp_score + edu_score + pub_score + proj_score
        + train_score + skills_score + boss_assessment_score
    )
```

Finally, in the returned dict, replace `"training_score": training_score,` with:

```python
        "trainings_count": trainings_count,
        "training_score": train_score,
```

- [ ] **Step 5: Update `CSV_COLUMNS`**

In `ml/generate_dataset.py`, replace the whole `CSV_COLUMNS` list with:

```python
CSV_COLUMNS = [
    "employee_id", "name", "initials", "age", "job_role", "department",
    "experience_years", "education_level", "publications_count",
    "projects_led_count", "trainings_count", "skills_score",
    "boss_assessment_score", "language_proficiency",
    "experience_score", "education_score", "publication_score",
    "project_score", "training_score", "compensation_score",
    "market_min_salary", "market_max_salary",
    "expected_salary", "actual_salary", "compensation_ratio",
    "satisfaction_label",
]
```

- [ ] **Step 6: Update the scorecard in `compensation/data.py`**

Add `training_score` to the existing import block:

```python
from ml.generate_dataset import (
    EDUCATION_POINTS,
    JOB_ROLES,
    clip,
    experience_score,
    project_score,
    publication_score,
    training_score,
)
```

In `INT_FIELDS`, replace `"training_score",` with `"trainings_count", "training_score",`.

In `SCORECARD_DESCRIPTIONS`, replace the `publications`, `training` and `boss_assessment` entries:

```python
    "publications": "2 points per publication, capped at 20 (10+ publications)",
    "training": "2 points per training completed, capped at 10 (5+ trainings)",
    "boss_assessment": "Fixed at 10 for all employees",
```

In `compute_scorecard`, replace the training category line:

```python
        {"key": "training", "label": "Training", "score": training_score(row["trainings_count"]), "max": 10},
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `venv/bin/python manage.py test compensation.tests.ScorecardTests -v 2`
Expected: PASS, 5 tests.

- [ ] **Step 8: Commit**

```bash
git add ml/generate_dataset.py compensation/data.py compensation/tests.py
git commit -m "feat: redefine publications and training marking

Publications score 2 marks each capped at 20; training becomes a count
scoring 2 marks each capped at 10. trainings_count is now the stored
raw value, training_score the derived mark."
```

---

### Task 2: Regenerate the synthetic dataset

The marking change alters `compensation_score`, which drives `expected_salary` and `actual_salary`, so all 1000 rows change.

**Files:**
- Modify: `ml/data/synthetic_employee_compensation.csv` (regenerated)

**Interfaces:**
- Consumes: `CSV_COLUMNS`, `publication_score`, `training_score` from Task 1.
- Produces: a 1000-row CSV carrying `trainings_count`.

- [ ] **Step 1: Regenerate**

```bash
venv/bin/python ml/generate_dataset.py --rows 1000 --seed 42 --out ml/data/synthetic_employee_compensation.csv
```

Expected: `Wrote 1000 rows to ml/data/synthetic_employee_compensation.csv`

- [ ] **Step 2: Verify the header and a sane distribution**

```bash
head -1 ml/data/synthetic_employee_compensation.csv
venv/bin/python -c "
import pandas as pd
df = pd.read_csv('ml/data/synthetic_employee_compensation.csv')
print('rows', len(df))
print('trainings_count', df['trainings_count'].min(), '-', df['trainings_count'].max())
print('training_score', df['training_score'].min(), '-', df['training_score'].max())
print('compensation_score', df['compensation_score'].min(), '-', df['compensation_score'].max())
assert 'trainings_count' in df.columns
assert (df['training_score'] == df['trainings_count'].clip(upper=5) * 2).all()
assert df['compensation_score'].between(0, 100).all()
print('OK')
"
```

Expected: `trainings_count` spans 0–7, `training_score` 0–10, `compensation_score` within 0–100, then `OK`.

- [ ] **Step 3: Commit**

```bash
git add ml/data/synthetic_employee_compensation.csv
git commit -m "chore: regenerate synthetic dataset under the new marking rules"
```

---

### Task 3: Retarget the models and accept multiple data files

Switch the regression target to `actual_salary`, swap `training_score` for `trainings_count` in the feature list, feed the classifier the regressor's own prediction rather than the generator's `expected_salary`, and let `--data` take several files.

**Files:**
- Modify: `ml/features.py`
- Modify: `ml/train_models.py:43-50` (constants), `:75-108` (`run_regression`), `:111-158` (`run_classification`, `save_pipeline`), `:180-197` (`main`)
- Modify: `compensation/data.py:42-56` (`FEATURE_LABELS`), `:184-186`, `:226-230`, `:263-267`

**Interfaces:**
- Consumes: the regenerated CSV from Task 2.
- Produces: `NUMERIC_FEATURES` containing `trainings_count`; `CLASSIFICATION_EXTRA_NUMERIC == ["actual_salary", "predicted_market_salary"]`; `save_pipeline(...) -> Pipeline`; `run_regression(df, out_dir, artifacts_dir) -> (DataFrame, Pipeline)`.

- [ ] **Step 1: Update `ml/features.py`**

Replace the three constants at the bottom of the file:

```python
CATEGORICAL_FEATURES = ["education_level", "language_proficiency", "job_role", "department"]
NUMERIC_FEATURES = [
    "age", "experience_years", "publications_count", "projects_led_count",
    "trainings_count", "skills_score", "boss_assessment_score",
]
CLASSIFICATION_EXTRA_NUMERIC = ["actual_salary", "predicted_market_salary"]
```

- [ ] **Step 2: Mirror the constants in `ml/train_models.py`**

Replace lines 43–50 with:

```python
CATEGORICAL_FEATURES = ["education_level", "language_proficiency", "job_role", "department"]
NUMERIC_FEATURES = [
    "age", "experience_years", "publications_count", "projects_led_count",
    "trainings_count", "skills_score", "boss_assessment_score",
]
REGRESSION_TARGET = "actual_salary"
CLASSIFICATION_TARGET = "satisfaction_label"
CLASSIFICATION_EXTRA_NUMERIC = ["actual_salary", "predicted_market_salary"]
```

- [ ] **Step 3: Make `save_pipeline` return the pipeline**

In `ml/train_models.py`, replace `save_pipeline` with:

```python
def save_pipeline(preprocessor, estimator, artifacts_dir, filename):
    pipeline = Pipeline(steps=[("preprocessor", preprocessor), ("estimator", estimator)])
    path = os.path.join(artifacts_dir, filename)
    joblib.dump(pipeline, path)
    print(f"Saved {path}")
    return pipeline
```

- [ ] **Step 4: Return the fitted pipeline from `run_regression`**

Replace the last two lines of `run_regression`:

```python
    explain_model(fitted[best_name], X_train, X_test, feature_names, out_dir, prefix="regression")
    pipeline = save_pipeline(preprocessor, fitted[best_name], artifacts_dir, "regression_model.joblib")
    return results, pipeline
```

- [ ] **Step 5: Feed the classifier the regressor's prediction**

In `main()`, replace the body between `df = pd.read_csv(args.data)` and the comparison write with:

```python
    reg_results, reg_pipeline = run_regression(df, args.out, args.artifacts)

    # Train the classifier on the SAME signal it will be served at runtime:
    # the regression model's prediction, not the generator's expected_salary.
    # For the 80% of rows the regressor trained on this is in-sample, which
    # flatters the classifier slightly; acceptable for a prototype.
    df["predicted_market_salary"] = reg_pipeline.predict(
        df[CATEGORICAL_FEATURES + NUMERIC_FEATURES]
    )

    clf_results = run_classification(df, args.out, args.artifacts)
```

- [ ] **Step 6: Accept several data files**

In `main()`, replace the `--data` argument and the read:

```python
    parser.add_argument("--data", nargs="+", default=["ml/data/synthetic_employee_compensation.csv"])
```

and replace `df = pd.read_csv(args.data)` with:

```python
    frames = [pd.read_csv(path) for path in args.data]
    df = pd.concat(frames, ignore_index=True)
    print(f"Loaded {len(df)} rows from {len(frames)} file(s): {', '.join(args.data)}")
```

- [ ] **Step 7: Point `compensation/data.py` at the new classifier column**

Three call sites set the classifier's second numeric. In `_build_roster`, replace:

```python
    clf_input["expected_salary"] = predicted_salary
```

with:

```python
    clf_input["predicted_market_salary"] = predicted_salary
```

In `get_employee_detail`, replace `clf_row["expected_salary"] = employee["predicted_salary"]` with:

```python
    clf_row["predicted_market_salary"] = employee["predicted_salary"]
```

In `predict_profile`, replace `clf_row["expected_salary"] = predicted_salary` with:

```python
        clf_row["predicted_market_salary"] = predicted_salary
```

In `FEATURE_LABELS`, replace the `expected_salary` entry and add the two new keys:

```python
    "trainings_count": "Trainings completed",
    "actual_salary": "Actual salary",
    "predicted_market_salary": "Predicted market salary",
```

(Delete the old `"expected_salary": "Predicted fair salary",` line.)

- [ ] **Step 8: Retrain and regenerate the artifacts**

```bash
venv/bin/python ml/train_models.py --data ml/data/synthetic_employee_compensation.csv
```

Expected: both tables print, `Best model:` lines appear, and four files are written — `ml/artifacts/regression_model.joblib`, `ml/artifacts/classification_model.joblib`, and the SHAP PNGs in `ml/outputs/`. The regression R² will drop well below the old 0.982; that is the point of the change, not a regression.

- [ ] **Step 9: Confirm the saved pipelines expect the new feature list**

```bash
venv/bin/python -c "
import joblib, sys
sys.path.insert(0, '.')
from ml.features import CATEGORICAL_FEATURES, NUMERIC_FEATURES, CLASSIFICATION_EXTRA_NUMERIC
reg = joblib.load('ml/artifacts/regression_model.joblib')
clf = joblib.load('ml/artifacts/classification_model.joblib')
assert list(reg.named_steps['preprocessor'].feature_names_in_) == CATEGORICAL_FEATURES + NUMERIC_FEATURES
assert list(clf.named_steps['preprocessor'].feature_names_in_) == CATEGORICAL_FEATURES + NUMERIC_FEATURES + CLASSIFICATION_EXTRA_NUMERIC
print('feature lists OK')
"
```

Expected: `feature lists OK`.

- [ ] **Step 10: Run the full suite**

Run: `venv/bin/python manage.py test`
Expected: PASS, no exceptions. The UI still says "Predicted Fair Salary" and its assertions still pass — Task 11 renames both together. If anything fails here it is a real defect in this task; fix it before committing.

- [ ] **Step 11: Commit**

```bash
git add ml/features.py ml/train_models.py compensation/data.py ml/artifacts ml/outputs
git commit -m "feat: predict actual_salary and train on multiple data files

Regression target moves from the generator-invented expected_salary to
actual_salary, so real rows can train it. The classifier now receives
the regressor's own prediction, removing the train/serve skew. --data
accepts several CSVs so real and survey rows append to the synthetic
base without mutating it."
```

---

### Task 4: `trainings_count` on the User model and derived department

**Files:**
- Modify: `dashboard/models.py`
- Create: `dashboard/migrations/0005_*.py` (generated)
- Test: `dashboard/tests.py`

**Interfaces:**
- Consumes: `ml.generate_dataset.JOB_ROLES`.
- Produces: `User.trainings_count` (int, default 0); `dashboard.models.ROLE_DEPARTMENTS: dict[str, str]`; `dashboard.models.DEPARTMENT_CHOICES: list[tuple[str, str]]`; `User.save()` fills `department` from `designation`.

- [ ] **Step 1: Write the failing tests**

Append to `dashboard/tests.py`:

```python
class DepartmentDerivationTests(TestCase):
    def test_department_is_derived_from_designation_on_save(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="derive1", password="x", designation="Accountant"
        )
        self.assertEqual(user.department, "Finance")

    def test_department_is_derived_for_engineering_roles(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="derive2", password="x", designation="Software Engineer"
        )
        self.assertEqual(user.department, "Engineering")

    def test_other_designation_keeps_the_supplied_department(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="derive3", password="x", designation="Other", department="Design"
        )
        self.assertEqual(user.department, "Design")

    def test_trainings_count_defaults_to_zero(self):
        User = get_user_model()
        user = User.objects.create_user(username="derive4", password="x")
        self.assertEqual(user.trainings_count, 0)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `venv/bin/python manage.py test dashboard.tests.DepartmentDerivationTests -v 2`
Expected: FAIL — `department` is `None`, and `User` has no attribute `trainings_count`.

- [ ] **Step 3: Add the lookup tables and the field**

At the top of `dashboard/models.py`, below the existing imports:

```python
from ml.generate_dataset import JOB_ROLES

ROLE_DEPARTMENTS = {role: department for role, department, _min, _max in JOB_ROLES}
DEPARTMENT_CHOICES = [(name, name) for name in sorted(set(ROLE_DEPARTMENTS.values()))]
```

Inside `class User`, replace the `training_score` field with:

```python
    trainings_count = models.IntegerField(default=0, blank=True, null=True)
```

Then add the save override as the last method of `class User`:

```python
    def save(self, *args, **kwargs):
        if self.designation and self.designation != "Other":
            self.department = ROLE_DEPARTMENTS.get(self.designation, self.department)
        super().save(*args, **kwargs)
```

- [ ] **Step 4: Generate and apply the migration**

```bash
venv/bin/python manage.py makemigrations dashboard
venv/bin/python manage.py migrate
```

Expected: one migration adding `trainings_count`, removing `training_score`, and altering `designation` (the pending choices drift). Confirm no drift remains:

```bash
venv/bin/python manage.py makemigrations --check --dry-run
```

Expected: `No changes detected`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `venv/bin/python manage.py test dashboard.tests.DepartmentDerivationTests -v 2`
Expected: PASS, 4 tests.

- [ ] **Step 6: Commit**

```bash
git add dashboard/models.py dashboard/migrations/
git commit -m "feat: derive department from job role, store trainings_count

Department is filled from the JOB_ROLES table on save, so it is always
a category the models were trained on. training_score is replaced by
trainings_count to match the new marking rules."
```

---

### Task 5: Registration collects the right fields

Drop the free-text department, ask for a training count, show a department dropdown only for "Other", and stop the form wiping itself on a validation error.

**Files:**
- Modify: `dashboard/forms.py`
- Modify: `dashboard/templates/dashboard/register.html`
- Modify: `dashboard/views.py:79-108` (`register_employee`)
- Test: `dashboard/tests.py`

**Interfaces:**
- Consumes: `DEPARTMENT_CHOICES`, `User.trainings_count` from Task 4.
- Produces: `EmployeeRegistrationForm` with `trainings_count`, no free-text `department`, and a `clean()` that requires `department` only when `designation == "Other"`.

- [ ] **Step 1: Write the failing tests**

Append to `dashboard/tests.py`:

```python
class RegistrationTests(TestCase):
    def payload(self, **overrides):
        data = {
            "username": "newhire",
            "password1": "buscom-test-2026",
            "password2": "buscom-test-2026",
            "first_name": "Nusrat",
            "last_name": "Islam",
            "email": "nusrat@buscom.test",
            "age": 27,
            "designation": "Software Engineer",
            "language_proficiency": "Advanced",
            "experience_years": 4,
            "education_level": "BSc",
            "publications_count": 2,
            "projects_led_count": 3,
            "trainings_count": 4,
            "skills_score": 7,
            "actual_salary": 65000,
            "satisfaction_score": 4,
            "fairness_feedback": "",
        }
        data.update(overrides)
        return data

    def test_registration_persists_every_field(self):
        response = self.client.post(reverse("register"), self.payload())
        self.assertRedirects(response, reverse("employee_self_service"))
        User = get_user_model()
        user = User.objects.get(username="newhire")
        self.assertEqual(user.role, User.Role.EMPLOYEE)
        self.assertEqual(user.age, 27)
        self.assertEqual(user.designation, "Software Engineer")
        self.assertEqual(user.department, "Engineering")
        self.assertEqual(user.experience_years, 4)
        self.assertEqual(user.education_level, "BSc")
        self.assertEqual(user.language_proficiency, "Advanced")
        self.assertEqual(user.publications_count, 2)
        self.assertEqual(user.projects_led_count, 3)
        self.assertEqual(user.trainings_count, 4)
        self.assertEqual(user.skills_score, 7)
        self.assertEqual(user.actual_salary, 65000)
        self.assertEqual(user.satisfaction_score, 4)
        self.assertEqual(user.boss_assessment_score, 10)

    def test_other_designation_requires_a_department(self):
        response = self.client.post(
            reverse("register"), self.payload(designation="Other", job_role_other="AI Engineer")
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"], "department", "Select a department for your role."
        )

    def test_other_designation_with_department_is_accepted(self):
        response = self.client.post(
            reverse("register"),
            self.payload(designation="Other", job_role_other="AI Engineer", department="Engineering"),
        )
        self.assertRedirects(response, reverse("employee_self_service"))
        user = get_user_model().objects.get(username="newhire")
        self.assertEqual(user.job_role_other, "AI Engineer")
        self.assertEqual(user.department, "Engineering")

    def test_validation_error_keeps_submitted_values(self):
        response = self.client.post(
            reverse("register"), self.payload(password2="does-not-match")
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="Nusrat"')
        self.assertContains(response, 'value="65000"')
        self.assertContains(response, 'value="27"')
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `venv/bin/python manage.py test dashboard.tests.RegistrationTests -v 2`
Expected: FAIL — the form still has a required free-text `department` and no `trainings_count`.

- [ ] **Step 3: Update the form**

In `dashboard/forms.py`, change the import line to:

```python
from .models import DEPARTMENT_CHOICES, User
```

Replace the `department` field declaration with:

```python
    department = forms.ChoiceField(
        choices=[("", "Select department")] + DEPARTMENT_CHOICES,
        required=False,
        label="Department",
    )
```

Replace the `training_score` field declaration with:

```python
    trainings_count = forms.IntegerField(min_value=0, required=True, label="How many trainings or courses have you completed?")
```

In `Meta.fields`, replace `'training_score'` with `'trainings_count'`.

Add this method to the class, after the `Meta` class:

```python
    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("designation") == "Other" and not cleaned_data.get("department"):
            self.add_error("department", "Select a department for your role.")
        return cleaned_data
```

- [ ] **Step 4: Simplify the view**

In `dashboard/views.py`, replace the whole body of the `if form.is_valid():` block with:

```python
        if form.is_valid():
            user = form.save(commit=False)
            user.role = User.Role.EMPLOYEE
            user.save()
            login(request, user)
            return redirect("employee_self_service")
```

Leave `from .mock_data import EMPLOYEES, PAYSLIPS` exactly as it is. The other three views still use it; Task 7 removes the import and the module together.

This deletes the `EMPLOYEES.append(...)` block, which mutated a module-level list — registrations were lost on restart and invisible to other gunicorn workers.

- [ ] **Step 5: Bind values in the template**

In `dashboard/templates/dashboard/register.html`, every text and number `<input>` needs its submitted value echoed back. Apply this pattern to each field — `first_name`, `last_name`, `email`, `username`, `job_role_other`, `age`, `experience_years`, `publications_count`, `projects_led_count`, `trainings_count`, `skills_score`, `actual_salary`, `satisfaction_score`:

```html
<input ... name="first_name" id="id_first_name" value="{{ form.first_name.value|default:'' }}" required>
```

Do **not** add a value to `password1` or `password2`.

For the textarea, put the value between the tags:

```html
<textarea class="w-full rounded-xl border border-white/40 dark:border-slate-600/50 bg-white/50 dark:bg-slate-800/50 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-sm"
          name="fairness_feedback" id="id_fairness_feedback" rows="3">{{ form.fairness_feedback.value|default:'' }}</textarea>
```

For every `<select>` (`designation`, `language_proficiency`, `education_level`), replace the placeholder option and loop with this pattern:

```html
<option value="" disabled {% if not form.designation.value %}selected{% endif %}>Select title</option>
{% for value, name in form.designation.field.choices %}
  <option value="{{ value }}" {% if form.designation.value|stringformat:"s" == value|stringformat:"s" %}selected{% endif %}>{{ name }}</option>
{% endfor %}
```

- [ ] **Step 6: Swap the department input for a conditional dropdown**

Replace the whole `<div>` containing `id_department` with:

```html
        <div x-show="role === 'Other'" x-transition style="display: none;">
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1" for="id_department">{{ form.department.label }}</label>
          <select class="w-full rounded-xl border border-white/40 dark:border-slate-600/50 bg-white/50 dark:bg-slate-800/50 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-sm"
                  name="department" id="id_department">
            {% for value, name in form.department.field.choices %}
              <option value="{{ value }}" {% if form.department.value|stringformat:"s" == value|stringformat:"s" %}selected{% endif %}>{{ name }}</option>
            {% endfor %}
          </select>
          {% if form.department.errors %}<p class="text-red-500 text-xs mt-1">{{ form.department.errors.0 }}</p>{% endif %}
          <p class="text-xs text-slate-500 mt-1">Only needed when your job title is "Other" — otherwise we set it from your role.</p>
        </div>
```

- [ ] **Step 7: Rename the training input**

Replace the `training_score` field block with:

```html
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1" for="id_trainings_count">{{ form.trainings_count.label }}</label>
          <input class="w-full rounded-xl border border-white/40 dark:border-slate-600/50 bg-white/50 dark:bg-slate-800/50 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-sm"
                 type="number" name="trainings_count" id="id_trainings_count" min="0" value="{{ form.trainings_count.value|default:'' }}" required>
          {% if form.trainings_count.errors %}<p class="text-red-500 text-xs mt-1">{{ form.trainings_count.errors.0 }}</p>{% endif %}
        </div>
```

Change the section heading `Performance & Self-Assessment (Out of 10)` to `Training & Self-Assessment`.

- [ ] **Step 8: Run the tests to verify they pass**

Run: `venv/bin/python manage.py test dashboard.tests.RegistrationTests -v 2`
Expected: PASS, 4 tests.

- [ ] **Step 9: Commit**

```bash
git add dashboard/forms.py dashboard/views.py dashboard/templates/dashboard/register.html dashboard/tests.py
git commit -m "feat: registration collects model-ready fields

Department becomes a dropdown shown only for 'Other' roles and is
otherwise derived. Training asks for a count. Every input echoes its
submitted value, so a validation error no longer clears the form."
```

---

### Task 6: DB-backed roster

**Files:**
- Modify: `compensation/data.py:58-88` (caches, loaders), `:177-215` (`_build_roster`, `get_roster`)
- Test: `compensation/tests.py`

**Interfaces:**
- Consumes: `User` fields from Tasks 4–5; the retrained artifacts from Task 3.
- Produces: `get_roster() -> list[dict]` (complete employees only, freshly queried each call); `get_incomplete_employees() -> list[dict]` with keys `id`, `name`, `missing`; `REQUIRED_EMPLOYEE_FIELDS: tuple[str, ...]`.

- [ ] **Step 1: Write the failing tests**

Add to `compensation/tests.py`:

```python
class RosterFromDatabaseTests(TestCase):
    def create_employee(self, username, **overrides):
        User = get_user_model()
        fields = {
            "first_name": "Rafiq",
            "last_name": "Hossain",
            "age": 30,
            "designation": "Software Engineer",
            "language_proficiency": "Advanced",
            "experience_years": 6,
            "education_level": "BSc",
            "publications_count": 1,
            "projects_led_count": 2,
            "trainings_count": 3,
            "skills_score": 7,
            "boss_assessment_score": 10,
            "actual_salary": 70000,
            "satisfaction_score": 4,
        }
        fields.update(overrides)
        return User.objects.create_user(username=username, password="x", **fields)

    def test_roster_contains_registered_employees(self):
        self.create_employee("rafiq")
        roster = data.get_roster()
        self.assertEqual([row["name"] for row in roster], ["Rafiq Hossain"])
        row = roster[0]
        self.assertEqual(row["job_role"], "Software Engineer")
        self.assertEqual(row["department"], "Engineering")
        self.assertEqual(row["initials"], "RH")
        self.assertEqual(row["actual_salary"], 70000)
        self.assertEqual(row["satisfaction_label"], "Satisfied")
        self.assertIn("predicted_salary", row)
        self.assertIn("gap_pct", row)
        self.assertIn("scorecard", row)

    def test_roster_reflects_a_newly_created_employee(self):
        self.create_employee("rafiq")
        self.assertEqual(len(data.get_roster()), 1)
        self.create_employee("nabila", first_name="Nabila", last_name="Khan")
        self.assertEqual(len(data.get_roster()), 2)

    def test_hr_users_are_not_in_the_roster(self):
        User = get_user_model()
        User.objects.create_user(username="hr2", password="x", role=User.Role.HR)
        self.assertEqual(data.get_roster(), [])

    def test_other_designation_uses_the_free_text_role(self):
        self.create_employee("ai", designation="Other", job_role_other="AI Engineer",
                             department="Engineering")
        self.assertEqual(data.get_roster()[0]["job_role"], "AI Engineer")

    def test_incomplete_employee_is_flagged_not_dropped(self):
        # migration 0002 seeds amara_okafor with no ML fields, so she is
        # always incomplete. Remove her so this test counts only its own row.
        get_user_model().objects.filter(username="amara_okafor").delete()
        self.create_employee("partial", actual_salary=None)
        self.assertEqual(data.get_roster(), [])
        incomplete = data.get_incomplete_employees()
        self.assertEqual(len(incomplete), 1)
        self.assertEqual(incomplete[0]["name"], "Rafiq Hossain")
        self.assertIn("actual_salary", incomplete[0]["missing"])

    def test_satisfaction_label_is_dissatisfied_below_four(self):
        self.create_employee("low", satisfaction_score=2)
        self.assertEqual(data.get_roster()[0]["satisfaction_label"], "Dissatisfied")
```

Add to the imports at the top of `compensation/tests.py`:

```python
from django.contrib.auth import get_user_model
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `venv/bin/python manage.py test compensation.tests.RosterFromDatabaseTests -v 2`
Expected: FAIL — the roster still comes from the CSV, so it holds 1000 synthetic rows.

- [ ] **Step 3: Replace the loader**

In `compensation/data.py`, delete `INT_FIELDS`, `FLOAT_FIELDS`, `_dataset_path()`, `_load_dataset()` and the `import csv` line. Replace `_roster_cache = None` and `_pipeline_cache = None` with:

```python
_pipeline_cache = None

REQUIRED_EMPLOYEE_FIELDS = (
    "designation", "education_level", "language_proficiency", "age",
    "experience_years", "publications_count", "projects_led_count",
    "trainings_count", "skills_score", "boss_assessment_score",
    "actual_salary", "satisfaction_score",
)

MARKET_BANDS = {role: (low, high) for role, _department, low, high in JOB_ROLES}
```

Then add these functions in their place:

```python
def _employee_role(user):
    if user.designation == "Other":
        return user.job_role_other or "Other"
    return user.designation


def _missing_fields(user):
    return [name for name in REQUIRED_EMPLOYEE_FIELDS if getattr(user, name) in (None, "")]


def _display_name(user):
    name = f"{user.first_name} {user.last_name}".strip()
    return name or user.username


def _employee_row(user):
    role = _employee_role(user)
    market_min, market_max = MARKET_BANDS.get(role, (30000, 100000))
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
```

- [ ] **Step 4: Rebuild the roster per request**

Replace `_build_roster()`'s first two lines:

```python
def _build_roster():
    rows = _load_employees()
    if not rows:
        return []
    regression_pipeline, classification_pipeline = _get_pipelines()
    df = pd.DataFrame(rows)
```

Replace `get_roster()` entirely — the module-level cache goes:

```python
def get_roster():
    return _build_roster()
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `venv/bin/python manage.py test compensation.tests.RosterFromDatabaseTests -v 2`
Expected: PASS, 6 tests.

- [ ] **Step 6: Surface incomplete records in the audit dashboard**

The spec requires HR to see who needs attention rather than have records vanish. Add the failing test to `compensation/tests.py`:

```python
class IncompleteEmployeeBannerTests(TestCase):
    def setUp(self):
        # migration 0002's amara_okafor has no ML fields and is therefore
        # always incomplete; drop her so the count below is unambiguous.
        get_user_model().objects.filter(username="amara_okafor").delete()
        get_user_model().objects.create_user(
            username="halfdone", password="x", first_name="Mim", last_name="Begum",
            designation="QA Engineer",
        )
        self.client.login(username="hr_admin", password="buscom-hr-2026")

    def test_dashboard_warns_about_incomplete_records(self):
        response = self.client.get(reverse("compensation:audit_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1 employee record is incomplete")

    def test_no_banner_when_every_record_is_complete(self):
        get_user_model().objects.filter(username="halfdone").delete()
        response = self.client.get(reverse("compensation:audit_dashboard"))
        self.assertNotContains(response, "incomplete")
```

Run it: `venv/bin/python manage.py test compensation.tests.IncompleteEmployeeBannerTests -v 2` — expect FAIL.

In `compensation/views.py`, inside `audit_dashboard`, add after `roster = data.get_roster()`:

```python
    incomplete = data.get_incomplete_employees()
```

and add to the render context dict:

```python
        "incomplete": incomplete,
        "incomplete_count": len(incomplete),
```

In `compensation/templates/compensation/dashboard.html`, immediately after the opening `{% block content %}` tag, add:

```html
{% if incomplete_count %}
<div class="rounded-xl border border-amber-300 bg-amber-50 dark:border-amber-700/50 dark:bg-amber-900/20 text-amber-800 dark:text-amber-200 px-4 py-3 mb-6 text-sm">
  <p class="font-medium">{{ incomplete_count }} employee record{{ incomplete_count|pluralize }} {{ incomplete_count|pluralize:"is,are" }} incomplete and excluded from these figures.</p>
  <ul class="mt-1 list-disc list-inside text-xs">
    {% for employee in incomplete %}
    <li>{{ employee.name }} — missing {{ employee.missing|join:", " }}</li>
    {% endfor %}
  </ul>
</div>
{% endif %}
```

Run it again: expect PASS, 2 tests.

- [ ] **Step 7: Fix the pre-existing compensation tests**

`AuditDashboardContentTests` and `EmployeeDetailTests` assume a 1000-row CSV roster. Add a `setUp` to each that creates employees. For `AuditDashboardContentTests`, replace its `setUp` with:

```python
    def setUp(self):
        User = get_user_model()
        for index in range(30):
            User.objects.create_user(
                username=f"emp{index}", password="x",
                first_name="Emp", last_name=f"Number{index}",
                age=30, designation="Software Engineer", language_proficiency="Advanced",
                experience_years=5, education_level="BSc", publications_count=1,
                projects_led_count=2, trainings_count=3, skills_score=7,
                boss_assessment_score=10, actual_salary=70000, satisfaction_score=4,
            )
        self.client.login(username="hr_admin", password="buscom-hr-2026")
```

Delete `test_pagination_defaults_to_25_per_page`'s reliance on 1000 rows — with 30 employees a full first page is still 25, so the assertion stands unchanged.

For `EmployeeDetailTests`, add the same employee-creating `setUp` (three employees is enough) before the login line.

- [ ] **Step 8: Run the full compensation suite**

Run: `venv/bin/python manage.py test compensation -v 2`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add compensation/data.py compensation/tests.py compensation/views.py compensation/templates/compensation/dashboard.html
git commit -m "feat: build the compensation roster from the User table

Only the loader changes; get_roster/get_employee_detail/predict_profile
keep their shapes, so templates, filters, sorting and pagination are
untouched. The module-level roster cache is removed — correct for a
static CSV, a stale-data bug against a live table."
```

---

### Task 7: DB-backed HR dashboard, derived payslips, mock data deleted

**Files:**
- Create: `dashboard/payslips.py`
- Delete: `dashboard/mock_data.py`, `dashboard/templates/dashboard/partials/employee_modal.html`
- Modify: `dashboard/views.py`, `dashboard/static/dashboard/js/app.js`, `dashboard/templates/dashboard/hr_dashboard.html`, `dashboard/templates/dashboard/employee_self_service.html`
- Test: `dashboard/tests.py`

**Interfaces:**
- Consumes: `User` fields from Task 4.
- Produces: `dashboard.payslips.payslips_for(user, count=3, today=None) -> list[dict]` with keys `id`, `period`, `gross`, `deductions`, `net`, `breakdown`; `dashboard.payslips.find_payslip(user, payslip_id) -> dict | None`.

- [ ] **Step 1: Write the failing tests**

Add to `dashboard/tests.py`:

```python
class PayslipDerivationTests(TestCase):
    def make_employee(self, username="payee", salary=60000):
        User = get_user_model()
        return User.objects.create_user(
            username=username, password="x", first_name="Sadia", last_name="Akter",
            email=f"{username}@buscom.test", actual_salary=salary,
        )

    def test_payslip_is_derived_from_actual_salary(self):
        from dashboard.payslips import payslips_for

        slips = payslips_for(self.make_employee(), today=date(2026, 8, 25))
        self.assertEqual(len(slips), 3)
        current = slips[0]
        self.assertEqual(current["id"], 1)
        self.assertEqual(current["period"], "August 2026")
        self.assertEqual(current["gross"], 60000)
        self.assertEqual(current["deductions"], 7800)
        self.assertEqual(current["net"], 52200)

    def test_periods_run_backwards_across_a_year_boundary(self):
        from dashboard.payslips import payslips_for

        slips = payslips_for(self.make_employee(), today=date(2026, 1, 15))
        self.assertEqual([s["period"] for s in slips],
                         ["January 2026", "December 2025", "November 2025"])

    def test_employee_without_salary_has_no_payslips(self):
        from dashboard.payslips import payslips_for

        self.assertEqual(payslips_for(self.make_employee(salary=None)), [])

    def test_breakdown_sums_to_net(self):
        from dashboard.payslips import payslips_for

        slip = payslips_for(self.make_employee(), today=date(2026, 8, 25))[0]
        self.assertEqual(sum(item["amount"] for item in slip["breakdown"]), slip["net"])


class PayslipViewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.employee = User.objects.create_user(
            username="viewer", password="x", first_name="Sadia", last_name="Akter",
            actual_salary=60000,
        )
        self.client.login(username="viewer", password="x")

    def test_detail_renders_for_own_payslip(self):
        response = self.client.get(reverse("payslip_detail", args=[1]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Base Salary")

    def test_unknown_payslip_id_returns_404(self):
        self.assertEqual(self.client.get(reverse("payslip_detail", args=[99])).status_code, 404)

    def test_employee_without_salary_gets_404(self):
        User = get_user_model()
        User.objects.create_user(username="nosalary", password="x")
        self.client.login(username="nosalary", password="x")
        self.assertEqual(self.client.get(reverse("payslip_detail", args=[1])).status_code, 404)
```

Add `from datetime import date` to the imports at the top of `dashboard/tests.py`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `venv/bin/python manage.py test dashboard.tests.PayslipDerivationTests -v 2`
Expected: FAIL — `ModuleNotFoundError: No module named 'dashboard.payslips'`.

- [ ] **Step 3: Write the payslip module**

Create `dashboard/payslips.py`:

```python
"""Payslips derived from an employee's recorded salary.

There is no payroll system behind BusCom. These are estimates computed
from User.actual_salary so employee self-service has something real to
show, and they are labeled as estimates everywhere they appear.
"""

from datetime import date

TAX_RATE = 0.10
INSURANCE_RATE = 0.03
MONTHS_SHOWN = 3


def _shift_month(today, months_back):
    month_index = today.month - 1 - months_back
    year = today.year + month_index // 12
    return date(year, month_index % 12 + 1, 1)


def _payslip(salary, period_start, payslip_id):
    tax = round(salary * TAX_RATE)
    insurance = round(salary * INSURANCE_RATE)
    net = salary - tax - insurance
    return {
        "id": payslip_id,
        "period": period_start.strftime("%B %Y"),
        "gross": salary,
        "deductions": tax + insurance,
        "net": net,
        "breakdown": [
            {"label": "Base Salary", "amount": salary},
            {"label": "Tax", "amount": -tax},
            {"label": "Insurance", "amount": -insurance},
        ],
    }


def payslips_for(user, count=MONTHS_SHOWN, today=None):
    salary = user.actual_salary
    if not salary:
        return []
    today = today or date.today()
    return [
        _payslip(salary, _shift_month(today, offset), offset + 1)
        for offset in range(count)
    ]


def find_payslip(user, payslip_id):
    return next((slip for slip in payslips_for(user) if slip["id"] == payslip_id), None)
```

- [ ] **Step 4: Rewrite the dashboard views**

In `dashboard/views.py`, replace the `from .mock_data import EMPLOYEES, PAYSLIPS` line with:

```python
from .payslips import find_payslip, payslips_for
```

Replace `hr_dashboard`, `payslip_detail` and `employee_self_service` with:

```python
@login_required
@user_passes_test(_is_hr, login_url="employee_self_service")
def hr_dashboard(request):
    employees = [
        {
            "id": user.id,
            "name": f"{user.first_name} {user.last_name}".strip() or user.username,
            "initials": "".join(
                part[0] for part in f"{user.first_name} {user.last_name}".split()[:2]
            ).upper(),
            "designation": user.job_role_other if user.designation == "Other" else (user.designation or "—"),
            "department": user.department or "—",
            "experience_years": user.experience_years or 0,
            "salary": user.actual_salary or 0,
        }
        for user in User.objects.filter(role=User.Role.EMPLOYEE).order_by("id")
    ]
    headcount = len(employees)
    total_payroll = sum(e["salary"] for e in employees)
    avg_salary = round(total_payroll / headcount, 2) if headcount else 0
    return render(request, "dashboard/hr_dashboard.html", {
        "employees": employees,
        "headcount": headcount,
        "total_payroll": total_payroll,
        "avg_salary": avg_salary,
    })


@login_required
def payslip_detail(request, payslip_id):
    payslip = find_payslip(request.user, payslip_id)
    if payslip is None:
        raise Http404("Payslip not found.")
    return render(request, "dashboard/payslip_detail.html", {"payslip": payslip})


@login_required
def employee_self_service(request):
    user = request.user
    if user.role != User.Role.EMPLOYEE:
        return render(request, "dashboard/empty_state.html", {
            "message": "No employee record is linked to your account yet.",
        })
    employee = {
        "name": f"{user.first_name} {user.last_name}".strip() or user.username,
        "initials": "".join(
            part[0] for part in f"{user.first_name} {user.last_name}".split()[:2]
        ).upper(),
        "designation": user.job_role_other if user.designation == "Other" else (user.designation or "—"),
        "department": user.department or "—",
        "experience_years": user.experience_years or 0,
        "email": user.email,
        "salary": user.actual_salary or 0,
    }
    return render(request, "dashboard/employee_self_service.html", {
        "employee": employee,
        "payslips": payslips_for(user),
    })
```

- [ ] **Step 5: Delete the mock data and the phantom "Add Employee" flow**

```bash
git rm dashboard/mock_data.py dashboard/templates/dashboard/partials/employee_modal.html
```

In `dashboard/templates/dashboard/hr_dashboard.html`, delete the `{% include "dashboard/partials/employee_modal.html" %}` line and the whole `<button @click="openModal()" ...>Add Employee</button>` element. The modal only pushed rows into a JavaScript array — they vanished on refresh and would now sit alongside real records. Registration is the real path.

In `dashboard/static/dashboard/js/app.js`, delete the `formError`, `showModal` properties and the `openModal`, `closeModal` and `addEmployee` methods from `employeeDirectory`.

- [ ] **Step 6: Switch the currency to BDT**

In `dashboard/templates/dashboard/hr_dashboard.html`, replace all three `{ prefix: '$' }` occurrences with `{ prefix: '৳' }`, both `>$0<` stat placeholders with `>৳0<`, and the table cell:

```html
            <td class="py-2 text-right" x-text="'৳' + employee.salary.toLocaleString()"></td>
```

In `dashboard/templates/dashboard/employee_self_service.html`, change `{ prefix: '$' }` to `{ prefix: '৳' }`, `>$0<` to `>৳0<`, `Current Annual Salary` to `Current Monthly Salary`, and `${{ payslip.net }}` to `৳{{ payslip.net }}`. Add an estimate note under the Payslips heading:

```html
  <h2 class="font-semibold mb-1">Payslips</h2>
  <p class="text-xs text-slate-500 mb-4">Estimated — derived from your recorded salary, not payroll.</p>
```

- [ ] **Step 7: Rework the mock-data-dependent tests**

In `dashboard/tests.py`, delete the `from dashboard.mock_data import PAYSLIPS` import and the `PayslipDetailTests` and `EmployeeSelfServiceTests` classes — the new `PayslipDerivationTests` and `PayslipViewTests` replace them.

`HrDashboardTests.test_hr_user_can_view_dashboard` asserts on `"Amara Okafor"`. That assertion **stays as it is** — she is a real seeded `User` with `role=employee`, so she now appears in the DB-backed roster legitimately, and her name is rendered into the `json_script` payload. Give her the fields the dashboard displays by adding to that class:

```python
    def setUp(self):
        get_user_model().objects.filter(username="amara_okafor").update(
            first_name="Amara", last_name="Okafor", designation="Software Engineer",
            actual_salary=95000, experience_years=6,
        )
```

Note that `.update()` bypasses `save()`, so `department` is not derived and renders as `—`. That is correct here: this test only checks that the HR dashboard lists real employees.

Add a self-service test to replace the deleted class:

```python
class EmployeeSelfServiceTests(TestCase):
    def test_requires_login(self):
        self.assertEqual(self.client.get("/me/").status_code, 302)

    def test_employee_sees_own_details(self):
        get_user_model().objects.filter(username="amara_okafor").update(
            designation="Software Engineer", actual_salary=95000, experience_years=6,
        )
        self.client.login(username="amara_okafor", password="buscom-emp-2026")
        response = self.client.get("/me/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/employee_self_service.html")
        self.assertContains(response, "Software Engineer")

    def test_hr_user_sees_empty_state(self):
        self.client.login(username="hr_admin", password="buscom-hr-2026")
        response = self.client.get(reverse("employee_self_service"))
        self.assertTemplateUsed(response, "dashboard/empty_state.html")
        self.assertContains(response, "No employee record is linked to your account yet.")
```

- [ ] **Step 8: Run the full suite**

Run: `venv/bin/python manage.py test`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add -A dashboard/
git commit -m "feat: HR dashboard and payslips read the database

mock_data.py is deleted. The HR roster comes from the User table, and
payslips are derived from actual_salary and labeled as estimates. The
client-only Add Employee modal is removed — it created rows that
vanished on refresh. Currency is BDT throughout."
```

---

### Task 8: Export employees for training

**Files:**
- Create: `dashboard/management/__init__.py`, `dashboard/management/commands/__init__.py`, `dashboard/management/commands/export_employees.py`
- Test: `dashboard/tests.py`

**Interfaces:**
- Consumes: `compensation.data` row helpers from Task 6; `CSV_COLUMNS` from Task 1.
- Produces: `manage.py export_employees [--out PATH]` writing `CSV_COLUMNS`-shaped rows. `expected_salary` and `compensation_ratio` are left blank — real employees have no fair-salary label, and neither column is a feature or a target.

- [ ] **Step 1: Write the failing test**

Add to `dashboard/tests.py`:

```python
class ExportEmployeesTests(TestCase):
    def test_export_writes_csv_columns_for_complete_employees(self):
        import csv
        import tempfile
        from pathlib import Path

        from django.core.management import call_command

        from ml.generate_dataset import CSV_COLUMNS

        get_user_model().objects.create_user(
            username="exportme", password="x", first_name="Tanvir", last_name="Uddin",
            age=31, designation="Data Analyst", language_proficiency="Fluent",
            experience_years=7, education_level="MSc", publications_count=2,
            projects_led_count=3, trainings_count=4, skills_score=8,
            boss_assessment_score=10, actual_salary=80000, satisfaction_score=5,
        )
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "real_employees.csv"
            call_command("export_employees", "--out", str(out))
            rows = list(csv.DictReader(out.open()))

        self.assertEqual(len(rows), 1)
        self.assertEqual(list(rows[0].keys()), CSV_COLUMNS)
        self.assertEqual(rows[0]["job_role"], "Data Analyst")
        self.assertEqual(rows[0]["department"], "Engineering")
        self.assertEqual(rows[0]["actual_salary"], "80000")
        self.assertEqual(rows[0]["trainings_count"], "4")
        self.assertEqual(rows[0]["training_score"], "8")
        self.assertEqual(rows[0]["satisfaction_label"], "Satisfied")
        self.assertEqual(rows[0]["expected_salary"], "")
        self.assertEqual(rows[0]["compensation_ratio"], "")

    def test_incomplete_employees_are_skipped(self):
        import csv
        import tempfile
        from pathlib import Path

        from django.core.management import call_command

        get_user_model().objects.create_user(
            username="partial2", password="x", first_name="Mim", last_name="Begum",
            actual_salary=None,
        )
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "real_employees.csv"
            call_command("export_employees", "--out", str(out))
            self.assertEqual(list(csv.DictReader(out.open())), [])
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `venv/bin/python manage.py test dashboard.tests.ExportEmployeesTests -v 2`
Expected: FAIL — `CommandError: Unknown command: 'export_employees'`.

- [ ] **Step 3: Create the package files**

```bash
mkdir -p dashboard/management/commands
touch dashboard/management/__init__.py dashboard/management/commands/__init__.py
```

- [ ] **Step 4: Write the command**

Create `dashboard/management/commands/export_employees.py`:

```python
"""Export registered employees in the ML training CSV shape.

expected_salary and compensation_ratio are left blank: they exist only
in the synthetic dataset, where the generator invents a "fair" salary.
Real employees have no such label, and neither column is a model
feature or target, so blanks are harmless when the files are
concatenated at training time.
"""

import csv

from django.core.management.base import BaseCommand

from compensation.data import compute_scorecard
from compensation import data as compensation_data
from ml.generate_dataset import CSV_COLUMNS

DEFAULT_OUT = "ml/data/real_employees.csv"


class Command(BaseCommand):
    help = "Export complete employee records to a training CSV."

    def add_arguments(self, parser):
        parser.add_argument("--out", default=DEFAULT_OUT)

    def handle(self, *args, **options):
        rows = []
        for row in compensation_data._load_employees():
            scorecard = compute_scorecard(row)
            by_key = {category["key"]: category["score"] for category in scorecard["categories"]}
            rows.append({
                **row,
                "experience_score": by_key["experience"],
                "education_score": by_key["education"],
                "publication_score": by_key["publications"],
                "project_score": by_key["projects"],
                "training_score": by_key["training"],
                "compensation_score": scorecard["total"],
                "expected_salary": "",
                "compensation_ratio": "",
            })

        with open(options["out"], "w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

        self.stdout.write(f"Wrote {len(rows)} employee rows to {options['out']}")
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `venv/bin/python manage.py test dashboard.tests.ExportEmployeesTests -v 2`
Expected: PASS, 2 tests.

- [ ] **Step 6: Commit**

```bash
git add dashboard/management dashboard/tests.py
git commit -m "feat: export_employees management command

Writes registered employees in the training CSV shape so real rows can
be appended to the synthetic base at training time without ever
mutating that base."
```

---

### Task 9: Rewrite the survey processor

**Files:**
- Modify: `ml/data/survey_data_processor.py` (full rewrite)
- Create: `ml/tests.py`

Verified beforehand: Django's test runner already discovers `ml/tests.py`
without `ml` being in `INSTALLED_APPS`, and `ml.data.survey_data_processor`
imports fine as a namespace subpackage — no `ml/data/__init__.py` needed.
Do not add either.

**Interfaces:**
- Consumes: `JOB_ROLES`, `EDUCATION_POINTS`, `CSV_COLUMNS` and the score functions from Task 1.
- Produces: `ml/data/survey_employees.csv`, rewritten from scratch on every run. Public helpers: `parse_salary(value) -> int | None`, `resolve_role(title, other) -> str | None`, `resolve_department(raw, role) -> str`, `salary_in_band(salary, role) -> bool`.

- [ ] **Step 1: Write the failing tests**

Create `ml/tests.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `venv/bin/python manage.py test ml -v 2`
Expected: FAIL — `ImportError: cannot import name 'resolve_role'`.

- [ ] **Step 3: Rewrite the processor**

Replace the entire contents of `ml/data/survey_data_processor.py`:

```python
#!/usr/bin/env python3
"""Turn raw survey responses into a training-ready CSV.

Writes ml/data/survey_employees.csv from scratch on every run, so
re-running never duplicates rows. It never touches the synthetic
dataset: that file is an immutable training base, and appending model
predictions back into it would train the model on its own output.

Rows are dropped when the job role is not one the models know (the
encoder would silently zero it out) or when the reported salary falls
outside a plausible range for that role.
"""

import csv
import sys
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from ml.generate_dataset import (  # noqa: E402
    CSV_COLUMNS,
    EDUCATION_POINTS,
    JOB_ROLES,
    experience_score,
    project_score,
    publication_score,
    training_score,
)

ROLE_DEPARTMENTS = {role: department for role, department, _min, _max in JOB_ROLES}
MARKET_BANDS = {role: (low, high) for role, _department, low, high in JOB_ROLES}
KNOWN_DEPARTMENTS = set(ROLE_DEPARTMENTS.values())

BOSS_ASSESSMENT_SCORE = 10  # flat for every employee, by design
SALARY_BAND_LOW = 0.3
SALARY_BAND_HIGH = 3.0


def parse_salary(value):
    text = str(value).lower().replace(",", "").strip()
    if not text or text == "nan":
        return None
    multiplier = 1
    if "lakh" in text:
        multiplier = 100000
        text = text.replace("lakh", "").strip()
    try:
        amount = int(float(text) * multiplier)
    except ValueError:
        return None
    return amount or None


def parse_int(value, default=0):
    text = str(value).strip()
    if not text or text.lower() in {"n/a", "nan"}:
        return default
    if "-" in text:
        low, _, high = text.partition("-")
        try:
            return (int(low.strip()) + int(high.strip())) // 2
        except ValueError:
            return default
    try:
        return int(float(text))
    except ValueError:
        return default


def resolve_role(title, other):
    title = str(title).strip()
    if title == "Other":
        title = str(other).strip()
    return title if title in MARKET_BANDS else None


def resolve_department(raw, role):
    raw = str(raw).strip()
    if raw in KNOWN_DEPARTMENTS:
        return raw
    return ROLE_DEPARTMENTS[role]


def resolve_education(raw):
    raw = str(raw).strip()
    return raw if raw in EDUCATION_POINTS else None


def salary_in_band(salary, role):
    low, high = MARKET_BANDS[role]
    return low * SALARY_BAND_LOW <= salary <= high * SALARY_BAND_HIGH


def build_row(employee_id, record):
    role = resolve_role(record.iloc[2], record.iloc[3])
    if role is None:
        return None

    salary = parse_salary(record.iloc[13])
    if salary is None or not salary_in_band(salary, role):
        return None

    education = resolve_education(record.iloc[7])
    if education is None:
        return None

    publications = parse_int(record.iloc[8])
    projects = parse_int(record.iloc[9])
    trainings = parse_int(record.iloc[10])
    skills = parse_int(record.iloc[11])
    experience = parse_int(record.iloc[6])
    satisfaction = parse_int(record.iloc[14])

    scores = {
        "experience_score": experience_score(experience),
        "education_score": EDUCATION_POINTS[education],
        "publication_score": publication_score(publications),
        "project_score": project_score(projects),
        "training_score": training_score(trainings),
    }
    market_min, market_max = MARKET_BANDS[role]

    return {
        "employee_id": employee_id,
        "name": f"Survey Participant {employee_id}",
        "initials": "SP",
        "age": parse_int(record.iloc[1], 25),
        "job_role": role,
        "department": resolve_department(record.iloc[4], role),
        "experience_years": experience,
        "education_level": education,
        "publications_count": publications,
        "projects_led_count": projects,
        "trainings_count": trainings,
        "skills_score": skills,
        "boss_assessment_score": BOSS_ASSESSMENT_SCORE,
        "language_proficiency": str(record.iloc[5]).strip(),
        **scores,
        "compensation_score": sum(scores.values()) + skills + BOSS_ASSESSMENT_SCORE,
        "market_min_salary": market_min,
        "market_max_salary": market_max,
        "expected_salary": "",
        "actual_salary": salary,
        "compensation_ratio": "",
        "satisfaction_label": "Satisfied" if satisfaction >= 4 else "Dissatisfied",
    }


def main():
    raw_file = BASE_DIR / "ml" / "data" / "survey_raw.tsv"
    out_file = BASE_DIR / "ml" / "data" / "survey_employees.csv"

    responses = pd.read_csv(raw_file, sep="\t")
    rows = []
    for position in range(len(responses)):
        row = build_row(len(rows) + 1, responses.iloc[position])
        if row is not None:
            rows.append(row)

    with open(out_file, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    dropped = len(responses) - len(rows)
    print(f"Wrote {len(rows)} usable rows to {out_file} ({dropped} of {len(responses)} dropped)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `venv/bin/python manage.py test ml -v 2`
Expected: PASS, 9 tests.

- [ ] **Step 5: Generate the survey CSV and confirm it is idempotent**

```bash
venv/bin/python ml/data/survey_data_processor.py
venv/bin/python ml/data/survey_data_processor.py
wc -l ml/data/survey_employees.csv
```

Expected: both runs print `Wrote 7 usable rows ... (6 of 13 dropped)`, and the file has 8 lines (header + 7). Running twice must not change the count — that is the idempotency fix.

- [ ] **Step 6: Confirm the synthetic base is untouched**

```bash
git status --short ml/data/synthetic_employee_compensation.csv
```

Expected: no output. The processor must never modify that file.

- [ ] **Step 7: Commit**

```bash
git add ml/data/survey_data_processor.py ml/tests.py ml/data/survey_employees.csv
git commit -m "fix: rewrite the survey processor

Writes its own CSV from scratch, so reruns cannot duplicate rows and
model predictions are never fed back into training data. Departments
resolve to known categories, roles match exactly instead of by
substring, and out-of-band salaries are dropped."
```

---

### Task 10: Retrain on real and survey data

**Files:**
- Modify: `ml/artifacts/*.joblib`, `ml/outputs/*` (regenerated)
- Create: `ml/README.md`

**Interfaces:**
- Consumes: everything above.
- Produces: artifacts trained on the synthetic base plus survey rows, and a documented retrain path.

- [ ] **Step 1: Retrain across both files**

```bash
venv/bin/python ml/train_models.py \
  --data ml/data/synthetic_employee_compensation.csv ml/data/survey_employees.csv
```

Expected: `Loaded 1007 rows from 2 file(s)`, both comparison tables, and four regenerated artifact files.

- [ ] **Step 2: Verify the app still serves predictions**

Run: `venv/bin/python manage.py test`
Expected: PASS.

- [ ] **Step 3: Document the retrain path**

Create `ml/README.md`:

```markdown
# ML pipeline

## Data files

| File | Written by | Notes |
|---|---|---|
| `data/synthetic_employee_compensation.csv` | `generate_dataset.py` | Immutable training base. Never appears in the UI. |
| `data/real_employees.csv` | `manage.py export_employees` | Registered employees. Rewritten each run. |
| `data/survey_employees.csv` | `data/survey_data_processor.py` | Cleaned survey responses. Rewritten each run. |

Nothing appends to the synthetic base. Each generated file is rewritten
from scratch, so reruns cannot duplicate rows.

## Retraining

```bash
venv/bin/python manage.py export_employees
venv/bin/python ml/data/survey_data_processor.py
venv/bin/python ml/train_models.py --data \
  ml/data/synthetic_employee_compensation.csv \
  ml/data/real_employees.csv \
  ml/data/survey_employees.csv
```

Artifacts land in `artifacts/`; the Django app loads them and never trains.

## Known caveats

- The regression target is `actual_salary` — what someone with a given
  profile actually earns. Being paid below the prediction is the
  underpayment signal. It is **not** a "fair salary": no such label
  exists for real people.
- `boss_assessment_score` is a flat 10 for every real employee, while
  synthetic rows vary across 0–10. The models learn a positive
  association from the synthetic data and then see the maximum for
  everyone real, which biases real predictions upward. Fix by storing
  real ratings and retraining; nothing else has to change.
- Survey training answers were collected as 0–10 ratings before
  training became a count, and are read as counts. Immaterial at seven
  rows against a 1,000-row base. Future surveys should ask for a count.
- The classifier is trained on the regression model's predictions,
  which are in-sample for the 80% of rows the regressor trained on.
```

- [ ] **Step 4: Commit**

```bash
git add ml/artifacts ml/outputs ml/README.md
git commit -m "chore: retrain on synthetic base plus survey rows

Documents the retrain path and the known caveats: flat boss assessment,
survey training answers read as counts, and in-sample classifier input."
```

---

### Task 11: Rename the prediction in the UI

The model no longer predicts a "fair" salary. Every user-facing string must say so.

**Files:**
- Modify: `compensation/templates/compensation/partials/prediction_cards.html:28`
- Modify: `compensation/templates/compensation/dashboard.html:121`
- Modify: `compensation/templates/compensation/detail.html:22`
- Modify: `compensation/views.py:94`, `:115`
- Test: `compensation/tests.py:92`, `:129`, `:134`

**Interfaces:**
- Consumes: nothing.
- Produces: the string `Predicted Market Salary` wherever the prediction is shown.

- [ ] **Step 1: Update the failing assertions first**

In `compensation/tests.py`, replace all three occurrences of `"Predicted Fair Salary"` with `"Predicted Market Salary"`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `venv/bin/python manage.py test compensation -v 2`
Expected: FAIL — the templates still render "Predicted Fair Salary".

- [ ] **Step 3: Update the copy**

In `compensation/templates/compensation/partials/prediction_cards.html`, replace line 28:

```html
    <h2 class="font-semibold mb-4">Predicted Market Salary</h2>
```

Add a one-line explanation directly under the market band paragraph:

```html
    <p class="text-xs text-slate-500 mb-4">What someone with this profile typically earns. Being paid below it is the underpayment signal.</p>
```

In `compensation/templates/compensation/dashboard.html`, replace the `Predicted Fair` column heading text with `Predicted Market`.

In `compensation/templates/compensation/detail.html`, replace the training line:

```html
      <div><dt class="text-slate-500">Trainings</dt><dd>{{ employee.trainings_count }}</dd></div>
```

- [ ] **Step 4: Run the full suite**

Run: `venv/bin/python manage.py test`
Expected: PASS.

- [ ] **Step 5: Verify no stale copy remains**

```bash
grep -rn "Fair Salary\|fair salary\|Predicted Fair\|training_score" --include=*.html --include=*.py . | grep -v "^./venv" | grep -v "^./docs" | grep -v migrations
```

Expected matches for `training_score` only in: `ml/generate_dataset.py`, `ml/data/survey_data_processor.py`, `ml/tests.py`, `dashboard/management/commands/export_employees.py`, `compensation/data.py` and `compensation/tests.py` — all referring to the derived `training_score` mark, which is correct and stays. Zero matches for any "Fair Salary" variant, and zero `training_score` matches in `.html` files.

- [ ] **Step 6: Commit**

```bash
git add compensation/
git commit -m "feat: rename the prediction to Predicted Market Salary

The regression target is actual_salary, so the number is what a profile
typically earns, not an invented fair salary. The detail page shows the
training count rather than the old 0-10 rating."
```

---

### Task 12: Full verification

**Files:** none modified.

- [ ] **Step 1: Full test suite**

Run: `venv/bin/python manage.py test`
Expected: PASS, zero failures.

- [ ] **Step 2: No migration drift**

Run: `venv/bin/python manage.py makemigrations --check --dry-run`
Expected: `No changes detected`.

- [ ] **Step 3: System check**

Run: `venv/bin/python manage.py check`
Expected: `System check identified no issues`.

- [ ] **Step 4: No mock data survives**

```bash
test ! -f dashboard/mock_data.py && echo "mock_data.py gone"
grep -rn "mock_data\|EMPLOYEES\|PAYSLIPS" --include=*.py --include=*.html . | grep -v "^./venv" | grep -v "^./docs" || echo "no references"
```

Expected: `mock_data.py gone`, then `no references`.

- [ ] **Step 5: Manual smoke test**

```bash
venv/bin/python manage.py runserver 8000
```

Walk through: register a new employee at `/register/` (confirm department is not asked, and that submitting a mismatched password keeps every value); log in as `hr_admin` / `buscom-hr-2026`; confirm the new employee appears on `/dashboard/` in BDT and on `/compensation/` with a predicted market salary and a gap; open their detail page; check `/compensation/predict/`; log in as the new employee and confirm `/me/` shows derived payslips marked as estimates.

- [ ] **Step 6: Commit any fixes and push the branch**

```bash
git status
git push -u origin real-data-pipeline
```
