# ML pipeline

## Data files

| File | Written by | Notes |
|---|---|---|
| `data/synthetic_employee_compensation.csv` | `generate_dataset.py` | Immutable training base. Never appears in the UI. |
| `data/real_employees.csv` | `manage.py export_employees` | Registered employees. Rewritten each run. |
| `data/survey_employees.csv` | `data/survey_data_processor.py` | Cleaned survey responses. Rewritten each run. |

Nothing appends to the synthetic base. Each generated file is rewritten
from scratch, so reruns cannot duplicate rows.

Survey rows number their `employee_id` starting from 1, so those ids
collide with synthetic `employee_id` 1–7 once the files are concatenated
for training. This is harmless — `employee_id` is not in
`CATEGORICAL_FEATURES` or `NUMERIC_FEATURES`, so no model ever sees it —
but anyone reading the combined file should know the column is not a
unique key.

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
- Switching the regression target to `actual_salary` does **not** fully
  break the circularity on synthetic data. `ml/generate_dataset.py`
  defines `actual_salary = expected_salary * gauss(1.0, 0.12)`, so on
  synthetic rows the new target is still only about 12% noise away from
  the old formula-derived one. That is why R2 stays high (~0.92) rather
  than collapsing. The circularity is genuinely broken only for real
  rows, where `actual_salary` is an observed fact rather than a derived
  number. Any write-up of model results must say this — the target
  switch alone did not solve the problem.
- Model selection for the served artifacts is constrained to linear
  models (`LinearRegression`, `LogisticRegression`), because the
  per-employee explanation reads `estimator.coef_`. On the current data
  a RandomForest scores marginally better on RMSE (9837 vs 10110); it is
  deliberately not served, because tree models expose only global
  feature importances, which cannot explain an individual prediction.
  Revisit if the gap ever becomes large — that would mean switching the
  explanation method too, not just the model.
