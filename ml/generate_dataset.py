#!/usr/bin/env python3
"""Synthetic employee compensation dataset generator for BusCom's salary
prediction / compensation-satisfaction ML prototype.

Usage:
    python ml/generate_dataset.py [--rows 1000] [--seed 42] [--out ml/data/synthetic_employee_compensation.csv]
"""

import argparse
import csv
import math
import random

# (job_role, department, market_min_salary, market_max_salary) in BDT/month
JOB_ROLES = [
    ("Software Engineer", "Engineering", 35000, 120000),
    ("Senior Software Engineer", "Engineering", 70000, 180000),
    ("Data Analyst", "Engineering", 30000, 90000),
    ("QA Engineer", "Engineering", 28000, 85000),
    ("HR Executive", "Human Resources", 25000, 70000),
    ("HR Manager", "Human Resources", 60000, 150000),
    ("Accountant", "Finance", 25000, 65000),
    ("Finance Manager", "Finance", 70000, 180000),
    ("Sales Executive", "Sales", 20000, 60000),
    ("Marketing Executive", "Marketing", 25000, 70000),
    ("Project Manager", "Operations", 80000, 200000),
    ("Customer Support Executive", "Customer Support", 18000, 45000),
    ("Graphic Designer", "Design", 22000, 60000),
    ("Business Analyst", "Strategy", 40000, 110000),
    ("Operations Manager", "Operations", 60000, 150000),
]

EDUCATION_POINTS = {
    "PhD": 20,
    "MSc": 15,
    "BSc": 10,
    "Diploma": 5,
    "High School": 0,
}
EDUCATION_WEIGHTS = [3, 22, 60, 12, 3]  # matches EDUCATION_POINTS key order

LANGUAGE_LEVELS = ["Basic", "Intermediate", "Advanced", "Fluent"]
LANGUAGE_WEIGHTS = [15, 35, 35, 15]

FIRST_NAMES = [
    "Abir", "Nusrat", "Rafiq", "Farhana", "Imran", "Sadia", "Tanvir", "Mim",
    "Shakil", "Ayesha", "Rahim", "Nabila", "Kamal", "Sultana", "Faisal",
    "Ruma", "Jahid", "Sabrina", "Mahmud", "Tania",
]
LAST_NAMES = [
    "Islam", "Rahman", "Hossain", "Akter", "Chowdhury", "Ahmed", "Khan",
    "Begum", "Uddin", "Sarker",
]

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


def clip(value, low, high):
    return max(low, min(high, value))


def experience_score(years):
    return min(20, years * 2)


def publication_score(count):
    return min(20, count * 2)


def training_score(count):
    return min(10, count * 2)


def project_score(count):
    return min(10, count * 2)


def sigmoid(x):
    return 1 / (1 + math.exp(-x))


def generate_row(employee_id, rng):
    name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
    initials = "".join(part[0] for part in name.split()).upper()

    job_role, department, market_min, market_max = rng.choice(JOB_ROLES)

    experience_years = round(rng.triangular(0, 15, 3))
    entry_age = rng.randint(21, 26)
    age = clip(entry_age + experience_years + rng.randint(0, 2), 21, 62)

    education_level = rng.choices(
        list(EDUCATION_POINTS.keys()), weights=EDUCATION_WEIGHTS, k=1
    )[0]
    publications_count = rng.choices(
        [0, 1, 2, 3, 4, 5, 6], weights=[40, 20, 15, 10, 8, 4, 3], k=1
    )[0]
    projects_led_count = rng.choices(
        [0, 1, 2, 3, 4, 5], weights=[15, 20, 20, 20, 15, 10], k=1
    )[0]
    trainings_count = rng.choices(
        [0, 1, 2, 3, 4, 5, 6, 7], weights=[12, 18, 20, 18, 14, 9, 6, 3], k=1
    )[0]
    train_score = training_score(trainings_count)
    skills_score = round(rng.betavariate(2.5, 2) * 10)

    # Boss assessment: loosely tracks demonstrated skill/training but carries
    # substantial independent noise, so it is not a flat 10 for everyone.
    performance_signal = (train_score + skills_score) / 2
    boss_assessment_score = clip(
        round(rng.gauss(0.5 * performance_signal + 3.0, 1.8)), 0, 10
    )

    language_proficiency = rng.choices(
        LANGUAGE_LEVELS, weights=LANGUAGE_WEIGHTS, k=1
    )[0]

    exp_score = experience_score(experience_years)
    edu_score = EDUCATION_POINTS[education_level]
    pub_score = publication_score(publications_count)
    proj_score = project_score(projects_led_count)

    compensation_score = (
        exp_score + edu_score + pub_score + proj_score
        + train_score + skills_score + boss_assessment_score
    )

    percentile = clip(compensation_score / 100 + rng.gauss(0, 0.03), 0, 1)
    expected_salary = market_min + percentile * (market_max - market_min)
    expected_salary *= rng.gauss(1.0, 0.03)
    expected_salary = round(clip(expected_salary, market_min * 0.9, market_max * 1.1) / 500) * 500

    actual_salary = expected_salary * rng.gauss(1.0, 0.12)
    actual_salary = round(clip(actual_salary, market_min * 0.6, market_max * 1.3) / 500) * 500

    compensation_ratio = round(actual_salary / expected_salary, 2)

    p_satisfied = sigmoid(8 * (compensation_ratio - 1) + 0.05 * (boss_assessment_score - 5))
    satisfaction_label = "Satisfied" if rng.random() < p_satisfied else "Dissatisfied"

    return {
        "employee_id": employee_id,
        "name": name,
        "initials": initials,
        "age": age,
        "job_role": job_role,
        "department": department,
        "experience_years": experience_years,
        "education_level": education_level,
        "publications_count": publications_count,
        "projects_led_count": projects_led_count,
        "trainings_count": trainings_count,
        "training_score": train_score,
        "skills_score": skills_score,
        "boss_assessment_score": boss_assessment_score,
        "language_proficiency": language_proficiency,
        "experience_score": exp_score,
        "education_score": edu_score,
        "publication_score": pub_score,
        "project_score": proj_score,
        "compensation_score": compensation_score,
        "market_min_salary": market_min,
        "market_max_salary": market_max,
        "expected_salary": int(expected_salary),
        "actual_salary": int(actual_salary),
        "compensation_ratio": compensation_ratio,
        "satisfaction_label": satisfaction_label,
    }


def generate_dataset(rows, seed):
    rng = random.Random(seed)
    return [generate_row(i + 1, rng) for i in range(rows)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="ml/data/synthetic_employee_compensation.csv")
    args = parser.parse_args()

    dataset = generate_dataset(args.rows, args.seed)

    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(dataset)

    print(f"Wrote {len(dataset)} rows to {args.out}")


if __name__ == "__main__":
    main()
