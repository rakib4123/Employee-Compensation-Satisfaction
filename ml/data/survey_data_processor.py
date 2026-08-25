#!/usr/bin/env python3
"""Turn raw survey responses into a training-ready CSV.

Writes ml/data/survey_employees.csv from scratch on every run, so
re-running never duplicates rows. It never touches the synthetic
dataset: that file is an immutable training base, and appending model
predictions back into it would train the model on its own output.

Rows are dropped when the job role is not one the models know (the
encoder would silently zero it out), when the reported salary falls
outside a plausible range for that role, when the language proficiency
answer is not one the models know (same silent-zero problem as an
unknown role), or when the satisfaction answer is missing or
unparseable (a blank answer is not evidence of dissatisfaction, and
must not silently become the "Dissatisfied" training label).
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
    LANGUAGE_LEVELS,
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


def resolve_language(raw):
    raw = str(raw).strip()
    return raw if raw in LANGUAGE_LEVELS else None


def parse_satisfaction(value):
    """Unlike parse_int(), this has no default: a missing or unparseable
    answer must drop the row rather than silently becoming a rating of 0,
    which reads as "Dissatisfied" (0 >= 4 is False) and fabricates a
    training label for a question nobody answered.
    """
    text = str(value).strip()
    if not text or text.lower() in {"n/a", "nan"}:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def salary_in_band(salary, role):
    low, high = MARKET_BANDS[role]
    return low * SALARY_BAND_LOW <= salary <= high * SALARY_BAND_HIGH


def build_row(employee_id, record):
    role = resolve_role(record.iloc[1], record.iloc[2])
    if role is None:
        return None

    salary = parse_salary(record.iloc[12])
    if salary is None or not salary_in_band(salary, role):
        return None

    education = resolve_education(record.iloc[6])
    if education is None:
        return None

    language = resolve_language(record.iloc[4])
    if language is None:
        return None

    satisfaction = parse_satisfaction(record.iloc[13])
    if satisfaction is None:
        return None

    publications = parse_int(record.iloc[7])
    projects = parse_int(record.iloc[8])
    trainings = parse_int(record.iloc[9])
    skills = parse_int(record.iloc[10])
    experience = parse_int(record.iloc[5])

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
        "age": parse_int(record.iloc[0], 25),
        "job_role": role,
        "department": resolve_department(record.iloc[3], role),
        "experience_years": experience,
        "education_level": education,
        "publications_count": publications,
        "projects_led_count": projects,
        "trainings_count": trainings,
        "skills_score": skills,
        "boss_assessment_score": BOSS_ASSESSMENT_SCORE,
        "language_proficiency": language,
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
