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
  the old formula-derived one. That is why R2 stays high (~0.91) rather
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
- The classifier has the same circularity problem as the regressor
  above, and it is worse there because the classifier's only working
  input is a proxy for the regressor's own output:
  - `ml/generate_dataset.py` derives `satisfaction_label` from
    `compensation_ratio = actual_salary / expected_salary`. The
    classifier's inputs include `actual_salary` and
    `predicted_market_salary` (the served regressor's own prediction),
    whose ratio is a near-exact stand-in for `compensation_ratio` on the
    993 of 1,007 training rows that came from the synthetic generator.
    The classifier is largely rediscovering the generator's own rule.
    Without a salary feature it performs at chance (ROC-AUC 0.485). Its
    "Predicted Satisfaction" output is close to a restatement of the
    `gap_pct` already shown on the same card, not independent evidence.
  - `predicted_market_salary` is provably redundant as a feature:
    regressing it on the classifier's other inputs gives R² = 1.0,
    because the served regressor is linear over those same columns. The
    ~0.028 AUC it appears to add over `actual_salary` alone is an L2
    regularisation artifact spread across two collinear columns, not
    signal.
  - ROC-AUC 0.668 is nonetheless an honest number for what the task
    allows: scoring synthetic rows with the generator's own probability
    (rather than the thresholded label) gives 0.7222, the Bayes ceiling
    for this generator. The served model achieves roughly 93% of what is
    achievable.
  - `satisfaction_label` itself means two different things depending on
    where the row came from: a coin flip weighted by
    `compensation_ratio` in synthetic rows, versus a real 1–5 self-report
    thresholded at `>= 4` in survey/registration rows. Two different
    measurement instruments are pooled into one training target column.
