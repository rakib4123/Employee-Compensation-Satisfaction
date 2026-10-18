# Compensation Insights — Are Employees Satisfied With Their Pay?

A Django HR platform (**BUSCOM**) that estimates each employee's **market salary** and **compensation satisfaction**, explains every prediction, and comes with an IEEE-format research proposal on the question behind it.

## What it does

**For HR**
- **Dashboard** of all registered employees with their actual salary, predicted market salary and pay gap.
- **Compensation audit** (`/compensation/`) with the average pay gap and a filter for employees paid more than 10% below their predicted market salary.
- **Per-employee detail** showing the top factors behind each prediction (job role, experience, education, publications, skills and more).
- **What-if predictor** (`/compensation/predict/`) to estimate the market salary for any hypothetical profile.

**For employees**
- **Self-service page** with their own predicted market salary and pay gap.
- **Payslips**, a **profile** page, and a registration form that collects exactly the fields the models need.

## How the ML works

| Task | Target | Served model | Test performance |
| --- | --- | --- | --- |
| Regression | `actual_salary` (predicted market salary) | Linear Regression | R² 0.907 · RMSE 10,110 · MAE 7,421 |
| Classification | `satisfaction_label` | Logistic Regression | Accuracy 0.604 · F1 0.592 · ROC-AUC 0.668 |

- **Features:** education level, language proficiency, job role, department, age, years of experience, publications, projects led, trainings completed, skills score and manager assessment.
- **Why linear models:** each employee's explanation is computed exactly from the model coefficients. A Random Forest scored slightly better on RMSE (9,837), but it can't explain an *individual* prediction, so it isn't served.
- **SHAP** summary plots for both models are in [`ml/outputs/`](ml/outputs/).
- **Training data:** a 1,000-row synthetic base, plus cleaned real survey responses and the registered employees (exported from the app). Training happens offline; the web app only loads the saved artifacts.

### Honest caveats

The synthetic generator derives the satisfaction label from the same salary ratio the classifier can see, so on synthetic rows the classifier partly **rediscovers the generator's rule**. Without a salary feature it performs at chance. Real survey rows break this circularity, but there are only a handful so far. [`ml/README.md`](ml/README.md) documents this and every other known limitation.

## Research proposal

[`paper/`](paper/) contains an IEEE conference-format proposal, *"Are Employees Satisfied With Their Compensation?"*, available as LaTeX, PDF and Word, with exploratory analysis of the survey.

**Headline EDA finding:** across 11 usable responses, salary and satisfaction looked negatively correlated (r = −0.58). After removing three implausible salary entries the correlation disappears (r = −0.02). The strongest positive correlate of satisfaction was the **manager rating** (Spearman +0.70), not salary.

## Tech stack

Python · Django 5.2 · scikit-learn · pandas · NumPy · SHAP · matplotlib · Tailwind CSS · PostgreSQL / SQLite · Gunicorn · WhiteNoise

## Run it locally

```bash
python -m venv venv
venv/bin/pip install -r requirements.txt
./run_server.sh          # sets DJANGO_DEBUG=1, runs migrations, serves on http://127.0.0.1:8000
```

Or run `python start.py` to install, migrate and serve in one step.

Migrations seed two **local demo accounts**:

| Role | Username | Password |
| --- | --- | --- |
| HR | `hr_admin` | `buscom-hr-2026` |
| Employee | `amara_okafor` | `buscom-emp-2026` |

> `DEBUG` is off by default. In production, set `SECRET_KEY` and `DATABASE_URL`, and leave `DJANGO_DEBUG` unset. `build.sh` installs dependencies, collects static files and migrates for deployment (e.g. on Render).

### Retrain the models

```bash
venv/bin/python manage.py export_employees
venv/bin/python ml/data/survey_data_processor.py
venv/bin/python ml/train_models.py --data \
  ml/data/synthetic_employee_compensation.csv \
  ml/data/real_employees.csv \
  ml/data/survey_employees.csv
```

New artifacts are written to `ml/artifacts/`.

## Project structure

```
buscom/         Django project settings and URLs
dashboard/      auth, roles, registration, HR dashboard, self-service, payslips
compensation/   audit view, employee detail, what-if predictor
ml/             dataset generation, survey processing, training, artifacts, SHAP outputs
paper/          IEEE research proposal and EDA figures
docs/           design specs and implementation plans
```

## Author

**Md. Rakib Hossain** — CSE, American International University-Bangladesh (AIUB)
[LinkedIn](https://www.linkedin.com/in/md-rakib-hossain-519818263) · [Portfolio](https://rakib4123.github.io)
