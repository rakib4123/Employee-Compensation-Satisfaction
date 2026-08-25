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

Nothing is missing, so no new model is required. Two schema migrations
are needed: one for the pending `designation` choices drift that
`makemigrations --check` already reports, and one replacing
`training_score` with `trainings_count` (see Marking logic).

## Storage

Compensation fields stay on `dashboard.User`, where migrations 0003 and
0004 already put them. A separate `EmployeeProfile` model would separate
the auth and HR domains more cleanly, and remains a contained refactor
later precisely because `data.py` hides storage from every consumer. It
is not worth a fifteen-field data migration now.

## Marking logic

The 100-point scorecard is redefined. Counted components score two
marks per item up to their cap; rated components score their rating
directly.

| Component | Rule | Max | Maxes out at |
|---|---|---|---|
| Experience | `min(20, years × 2)` | 20 | 10 years |
| Education | PhD 20 · MSc 15 · BSc 10 · Diploma 5 · High School 0 | 20 | — |
| Publications | `min(20, count × 2)` | 20 | 10 publications |
| Projects led | `min(10, count × 2)` | 10 | 5 projects |
| Training | `min(10, count × 2)` | 10 | 5 trainings |
| Skills | self-rated 0–10, used as-is | 10 | — |
| Boss assessment | flat `10` for everyone | 10 | — |
| **Total** | | **100** | |

Three changes from the current implementation:

**Publications** move from `20 if count >= 4 else count × 5` to
`min(20, count × 2)`. Reaching the cap now takes ten publications rather
than four.

**Training becomes a count, not a rating.** Today `training_score` is a
0–10 self-assessment of development received. It becomes
`trainings_count` — how many trainings or courses the employee has
completed — scored at two marks each. The stored field changes name and
meaning, and the registration question changes with it.

`trainings_count` replaces `training_score` in `NUMERIC_FEATURES`, so
the model consumes the raw count alongside `publications_count` and
`projects_led_count`, and the derived score stays a display concern.
This makes every counted component consistent: raw count stored and fed
to the model, score derived for the scorecard.

**Boss assessment is a flat 10 for everyone.** See below.

Because `publication_score` and the training component feed
`compensation_score`, which drives `expected_salary` and therefore
`actual_salary`, **the synthetic dataset must be regenerated** and both
models retrained. `generate_dataset.py` gains a `trainings_count` column
drawn from a plausible distribution, with `training_score` derived from
it.

`SCORECARD_DESCRIPTIONS` and `compute_scorecard()` in
`compensation/data.py` are updated to match, so the explanation HR reads
on the detail page states the real rule.

## Registration

The form keeps its current fields with four changes.

**Training asks for a count.** "Rate the training/professional
development you have received" becomes "How many trainings or courses
have you completed?", storing `trainings_count`.

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

**`boss_assessment_score` is not on the form.** It is a flat 10.

## Boss assessment rating

Every employee scores a flat `10`. The field keeps its default of `10`,
nothing sets it, and it contributes a constant ten marks to every
scorecard. No HR rating screen, no unrated state, no gate on
predictions.

It stays in `NUMERIC_FEATURES` and is still fed to both models.

**Known caveat, deliberately accepted.** The synthetic dataset generates
boss assessments across a realistic 0–10 spread, so the models learn a
positive association between the rating and pay. Every real employee
then arrives holding the maximum value, which biases their predictions
upward relative to the synthetic rows the models mostly learned from.
The size of the effect is whatever coefficient training assigns the
feature.

This is a conscious trade for not asking employees to self-report their
manager's rating and not building an HR screen to enter it. When real
ratings become available the fix is to store them and retrain; nothing
else in the design has to change. Any write-up of model results should
state that boss assessment is constant in real data.

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

Every registered employee gets a prediction, since registration makes
all model inputs required and boss assessment is constant. An employee
whose record predates this change, or is otherwise incomplete, is shown
in the roster flagged as incomplete rather than silently dropped, so HR
can see who needs attention.

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
`survey_employees.csv` from scratch, with three correctness fixes:

1. **Department** mapped to a known category; rows whose department
   cannot be resolved fall back to the department implied by their job
   role.
2. **Job-role matching** by exact match. The current
   `if jr.lower() in job_role.lower()` substring test matches
   `Senior Software Engineer` against `Software Engineer` first,
   assigning the junior market band (35k–120k instead of 70k–180k).
3. **Salary sanity bounds**, relative to the role's own market band: a
   row is kept when `actual_salary` falls within
   `[0.3 × market_min, 3 × market_max]`. A role-relative rule is used
   rather than one global range because the bands span 18k to 200k.

Rows whose job role is not in `JOB_ROLES` are dropped. The models
one-hot encode `job_role` with `handle_unknown="ignore"`, so an
unrecognised role silently becomes an all-zero vector and contributes
nothing; keeping such rows adds noise without signal.

An `Other` education level maps to unknown rather than being silently
downgraded to `High School`, which currently scores it zero points.

Boss assessment stays hardcoded at `10`, matching the rule applied to
registered employees. The survey's real self-reported ratings (`9, 6, 7,
1, 6, 8, 7, 8, 10, 5, 6, 5, 8`) are therefore discarded. They are kept
in `survey_raw.tsv` should the decision be revisited.

The survey's training answers were collected as 0–10 ratings, before
training became a count. They are read as counts, which is
approximately but not exactly what respondents meant. With seven usable
rows against a 1,000-row synthetic base the distortion is immaterial;
future surveys should ask for a count.

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

- Each scorecard component scores by its new rule, at zero, mid-range,
  at its cap, and beyond its cap; the seven components total 100.
- Registration persists every collected field to `User`.
- Department is derived from job role, including the `Other` path.
- A validation error re-renders the form with submitted values intact.
- The roster reflects the database, including newly registered users.
- An incomplete employee record is flagged, not silently dropped.
- Payslips derive from `actual_salary`; one user cannot fetch another's.
- `export_employees` output matches `CSV_COLUMNS`.
- The survey processor is idempotent, resolves departments, matches
  roles exactly, and drops out-of-range salaries and unknown roles.

`compensation/tests.py` already asserts the old scorecard formula in
`test_scorecard_matches_generator_formula_for_known_inputs`. That test
is rewritten against the new rules, not deleted.

## Out of scope

- Any `EmployeeProfile` extraction.
- Real payroll integration.
- Authentication changes; the demo seed users in migration 0002 stay.
- The non-functional controls on `dashboard/templates/dashboard/profile.html`.
- Deployment and settings hardening (`SECRET_KEY` fallback, `DEBUG`
  default, missing `psycopg2-binary`, SQLite on ephemeral disk). These
  are real problems, tracked separately.
