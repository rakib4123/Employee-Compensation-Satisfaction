# Real Data Pipeline Design

Date: 2026-08-25

## Purpose

BusCom currently has four disconnected notions of "employee". This spec
collapses them into one: employees register, their data lands in the
database, and every screen and every model reads from there.

Today:

1. `dashboard/mock_data.py` holds five hardcoded employees, joined to
   real accounts by email string match. It drives the HR dashboard and
   payslips.
2. `ml/data/synthetic_employee_compensation.csv` holds 1,000 synthetic
   rows. It is the only source Compensation Insights reads.
3. The `User` table carries fifteen compensation fields added by
   migrations 0003/0004. No view queries them.
4. `ml/data/survey_raw.tsv` holds thirteen real survey responses,
   appended into (2) by a script.

After this change:

- Registration collects everything the roster and the models need.
- The HR dashboard and Compensation Insights both read the `User` table.
- `dashboard/mock_data.py` is deleted.
- The synthetic dataset becomes an immutable training base that never
  appears in the UI; real rows are appended at training time only.

## Prior work this builds on

- `2026-08-16-compensation-insights-design.md` — defines the roster row
  shape, the 100-point scorecard, and the model-serving approach. That
  design is kept intact; only the data source behind it changes.
- `ml/generate_dataset.py` — `JOB_ROLES` (role → department → market
  band) and the scorecard component functions are reused directly.
- `compensation/data.py` — `get_roster()`, `get_employee_detail()` and
  `predict_profile()` keep their signatures and return shapes.

## The seam

`compensation/data.py` already isolates storage. Everything downstream —
templates, filters, sorting, pagination, views — consumes plain dicts,
and only `_load_dataset()` touches the CSV. Replacing that one function
carries the whole feature over to the database.

`User` can supply every field the roster needs. Fifteen are stored
directly. The rest are derived:

| Roster field | Source |
|---|---|
| `employee_id` | `user.id` |
| `name` | `first_name` + `last_name` |
| `initials` | first letter of each name part |
| `job_role` | `designation`, or `job_role_other` when designation is `Other` |
| `department` | derived at save time from `JOB_ROLES` |
| `market_min_salary`, `market_max_salary` | `JOB_ROLES` lookup |
| `experience_score` … `compensation_score` | `compute_scorecard()` |
| `expected_salary` | regression model prediction |
| `compensation_ratio` | `actual_salary / expected_salary` |
| `satisfaction_label` | `Satisfied` when `satisfaction_score >= 4` |

Nothing is missing, so no new model and no data migration are required.
Two schema migrations are still needed: one for the pending
`designation` choices drift that `makemigrations --check` already
reports, and one changing the `boss_assessment_score` default from `10`
to null.

## Storage

Compensation fields stay on `dashboard.User`, where migrations 0003 and
0004 already put them. A separate `EmployeeProfile` model would separate
the auth and HR domains more cleanly, and remains a contained refactor
later precisely because `data.py` hides storage from every consumer. It
is not worth a fifteen-field data migration now.

## Registration

The form keeps its current fields with three changes.

**Department is removed as a question.** It is derived from the selected
job role via `JOB_ROLES`, so it is always a category the models were
trained on. The current free-text field is the direct cause of the
survey's unusable department data, where all thirteen respondents
entered their academic department (`CSE`, `Cse`, `cse`, `CS`, `Bsc`).

When the job role is `Other`, a department dropdown of the eight known
values appears instead, reusing the Alpine `x-model="role"` toggle
already present in `register.html` for the `job_role_other` field.

**Every input gets a `value=` binding.** The template hand-rolls all
inputs with no value binding and hardcodes `selected` on the placeholder
`<option>`, so any validation error clears the entire seventeen-field
form. Selects must mark the submitted value as selected.

**`boss_assessment_score` is not on the form.** See below.

## Boss assessment rating

`boss_assessment_score` is a model feature. Its model default changes
from `10` to null, and HR sets it from the HR dashboard. Employees do
not self-report the rating their manager gave them.

An employee with no rating **receives no prediction**. The roster shows
them with a "Set rating" action in place of a gap and a risk level, and
they are excluded from the aggregate statistics, which display their
coverage (for example, "12 of 15 rated"). A provisional prediction that
silently changes once HR fills in a rating is worse than no prediction
in a tool whose purpose is auditing fairness.

The thirteen existing survey rows keep their **self-reported** ratings,
which are real values with genuine spread (`9, 6, 7, 1, 6, 8, 7, 8, 10,
5, 6, 5, 8`) and are far better training signal than the hardcoded `10`
that the current processor substitutes. This does mean the feature mixes
self-reported and HR-set values across sources; that caveat belongs in
any write-up of model results.

## Roster

`_load_dataset()` becomes `_load_employees()`, reading
`User.objects.filter(role=User.Role.EMPLOYEE)` and mapping each row to
the dict shape above. `get_roster()`, `get_employee_detail()`,
`predict_profile()`, and every template and view are unchanged.

**The `_roster_cache` module-level global is removed.** Building the
roster once per process is correct for a static CSV and a stale-data bug
the moment the roster is live — a newly registered employee would appear
for some workers and not others. The roster is built per request.
`_pipeline_cache` stays: model artifacts do not change mid-process.

Employees missing any required field are surfaced as unrated rather than
silently dropped, so HR can see who needs completing.

## HR dashboard and payslips

`hr_dashboard` reads the `User` table; headcount, total payroll and
average salary come from database aggregates rather than summing a
Python list.

The `EMPLOYEES.append(...)` block in `register_employee` is deleted. It
mutates a module-level list, so registrations are lost on restart and
are invisible to other gunicorn workers.

`dashboard/mock_data.py` is deleted.

A new `dashboard/payslips.py` derives the last three months from
`actual_salary`: gross, then tax and insurance deductions, then net, in
BDT. Payslips are labeled **"Estimated — derived from recorded salary,
not payroll"**, because no payroll system stands behind them.

Payslips are looked up within the requesting user's own derived list, so
one employee cannot address another's payslip by id. The ownership check
the current view performs becomes structurally unnecessary.

## Training data

The synthetic CSV becomes an immutable base. Three separate inputs
replace one file that gets appended to:

```
ml/data/synthetic_employee_compensation.csv   base, never written
ml/data/real_employees.csv                    manage.py export_employees
ml/data/survey_employees.csv                  survey processor output
```

`train_models.py` takes `--data` with `nargs="+"` and concatenates. Each
generated file is rewritten from scratch on every run, so re-running a
processor cannot duplicate rows — the current `max_id + idx + 1` scheme
appends thirteen more rows every time it runs.

`manage.py export_employees` writes database employees in `CSV_COLUMNS`
shape, including only those with a boss rating set.

Because generated files are separate from the base, the survey processor
no longer writes model predictions into its own training input. Under
the current design it fills `expected_salary` from
`regression_model.joblib` and appends the result to the training CSV, so
a retrain would train the model partly on its own output.

### Regression target

The regression target changes from `expected_salary` to `actual_salary`.

`expected_salary` is invented by `generate_dataset.py` as a
deterministic function of the same features the model receives. Real
employees have no such label — nobody knows what a given person *should*
earn — so under the current target, real data can only ever train the
satisfaction classifier. It also explains the reported R² of 0.982: the
model is rediscovering the generator's formula, not predicting anything.

With `actual_salary` as the target, the model predicts what someone with
a given profile actually earns, and underpayment is being paid below
that prediction. Real registrations and survey rows can train it, and
the result is defensible in a way the current number is not.

Consequences:

- Both models must be retrained and the artifacts regenerated.
- UI labels change from "Predicted Fair Salary" to "Predicted Market
  Salary"; `salary_label` strings and templates follow.
- The classifier's `expected_salary` feature now refers to the market
  prediction. This also removes an existing train/serve skew, where the
  classifier was trained on the CSV's ground-truth `expected_salary` but
  served the regression model's prediction.

## Survey processor

`ml/data/survey_data_processor.py` is rewritten to emit
`survey_employees.csv` from scratch, with four correctness fixes:

1. **Manager rating** read from column 12 instead of hardcoded to `10`.
2. **Department** mapped to a known category; rows whose department
   cannot be resolved fall back to the department implied by their job
   role.
3. **Job-role matching** by exact match. The current
   `if jr.lower() in job_role.lower()` substring test matches
   `Senior Software Engineer` against `Software Engineer` first,
   assigning the junior market band (35k–120k instead of 70k–180k).
4. **Salary sanity bounds**, relative to the role's own market band: a
   row is kept when `actual_salary` falls within
   `[0.3 × market_min, 3 × market_max]`. A role-relative rule is used
   rather than one global range because the bands span 18k to 200k.

Rows whose job role is not in `JOB_ROLES` are dropped. The models
one-hot encode `job_role` with `handle_unknown="ignore"`, so an
unrecognised role silently becomes an all-zero vector and contributes
nothing; keeping such rows adds noise without signal.

An `Other` education level maps to unknown rather than being silently
downgraded to `High School`, which currently scores it zero points.

Applying these rules to the thirteen responses keeps **seven**: two are
dropped for unrecognised roles (`Student`, `AI Engineer`) and four for
out-of-band salaries (`400000` and `500000` against a 30k–90k Data
Analyst band, `3 lakh` against a 22k–60k Graphic Designer band, and a
`0`). The survivors cover two job roles — Software Engineer and Data
Analyst.

This batch is a smoke test for the pipeline, not a training set. The
value of this work is the retrain path, not this data.

## Testing

Test-driven throughout.

The existing thirty-nine tests assert on mock data — `Amara Okafor`,
`Senior Backend Engineer`, `June 2026`. They are reworked to create real
`User` rows in fixtures. Behaviour under test is preserved: role-based
redirects, HR-only access, payslip ownership, empty states.

New coverage:

- Registration persists every collected field to `User`.
- Department is derived from job role, including the `Other` path.
- A validation error re-renders the form with submitted values intact.
- The roster reflects the database, including newly registered users.
- Unrated employees get no prediction and are excluded from aggregates.
- Payslips derive from `actual_salary`; one user cannot fetch another's.
- `export_employees` output matches `CSV_COLUMNS` and excludes unrated
  employees.
- The survey processor is idempotent, reads real ratings, resolves
  departments, matches roles exactly, and drops out-of-range salaries.

## Out of scope

- Any `EmployeeProfile` extraction.
- Real payroll integration.
- Authentication changes; the demo seed users in migration 0002 stay.
- The non-functional controls on `dashboard/templates/dashboard/profile.html`.
- Deployment and settings hardening (`SECRET_KEY` fallback, `DEBUG`
  default, missing `psycopg2-binary`, SQLite on ephemeral disk). These
  are real problems, tracked separately.
