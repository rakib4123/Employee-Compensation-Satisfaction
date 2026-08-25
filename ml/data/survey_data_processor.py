import csv
import re
import pandas as pd
import joblib

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from ml.generate_dataset import (
    CSV_COLUMNS,
    EDUCATION_POINTS,
    experience_score,
    publication_score,
    project_score,
    JOB_ROLES,
)

def parse_salary(val):
    val = str(val).lower().replace(",", "").strip()
    if "lakh" in val:
        val = val.replace("lakh", "").strip()
        try:
            return int(float(val) * 100000)
        except:
            return 0
    try:
        return int(float(val))
    except:
        return 0

def parse_int(val, default=0):
    val = str(val).strip()
    if val.lower() == "n/a" or val == "":
        return default
    if "-" in val:
        parts = val.split("-")
        try:
            return (int(parts[0].strip()) + int(parts[1].strip())) // 2
        except:
            return default
    try:
        return int(float(val))
    except:
        return default

def main():
    raw_file = BASE_DIR / "ml" / "data" / "survey_raw.tsv"
    dataset_file = BASE_DIR / "ml" / "data" / "synthetic_employee_compensation.csv"
    model_file = BASE_DIR / "ml" / "artifacts" / "regression_model.joblib"
    
    # Load model
    try:
        pipeline = joblib.load(model_file)
    except Exception as e:
        print(f"Error loading model: {e}")
        pipeline = None

    df = pd.read_csv(raw_file, sep="\t")
    
    try:
        df_existing = pd.read_csv(dataset_file)
        max_id = df_existing["employee_id"].max()
        if pd.isna(max_id):
            max_id = 0
    except Exception:
        df_existing = pd.DataFrame()
        max_id = 0
        
    rows = []
    
    for idx, row in df.iterrows():
        emp_id = max_id + idx + 1
        name = f"Survey Participant {emp_id}"
        initials = "SP"
        
        age = parse_int(row.iloc[1], 25)
        
        job_role = str(row.iloc[2]).strip()
        if job_role.lower() == "other":
            other_role = str(row.iloc[3]).strip()
            if other_role and other_role.lower() != "nan":
                job_role = other_role
        
        dept = str(row.iloc[4]).strip()
        lang = str(row.iloc[5]).strip()
        
        exp_years = parse_int(row.iloc[6])
        
        edu = str(row.iloc[7]).strip()
        if edu not in EDUCATION_POINTS:
            edu = "High School"
            
        pub = parse_int(row.iloc[8])
        proj = parse_int(row.iloc[9])
        train_score = parse_int(row.iloc[10])
        skill_score = parse_int(row.iloc[11])
        boss_score = 10  # Hardcoded as requested
        
        actual_sal = parse_salary(row.iloc[13])
        
        sat_val = parse_int(row.iloc[14])
        sat_label = "Satisfied" if sat_val >= 4 else "Dissatisfied"
        
        exp_score = experience_score(exp_years)
        edu_score = EDUCATION_POINTS[edu]
        pub_score = publication_score(pub)
        proj_score = project_score(proj)
        comp_score = exp_score + edu_score + pub_score + proj_score + train_score + skill_score + boss_score
        
        # Market min/max
        market_min = 30000
        market_max = 100000
        for jr, d, mmin, mmax in JOB_ROLES:
            if jr.lower() in job_role.lower():
                market_min = mmin
                market_max = mmax
                break
                
        out_row = {
            "employee_id": emp_id,
            "name": name,
            "initials": initials,
            "age": age,
            "job_role": job_role,
            "department": dept,
            "experience_years": exp_years,
            "education_level": edu,
            "publications_count": pub,
            "projects_led_count": proj,
            "training_score": train_score,
            "skills_score": skill_score,
            "boss_assessment_score": boss_score,
            "language_proficiency": lang,
            "experience_score": exp_score,
            "education_score": edu_score,
            "publication_score": pub_score,
            "project_score": proj_score,
            "compensation_score": comp_score,
            "market_min_salary": market_min,
            "market_max_salary": market_max,
            "actual_salary": actual_sal,
            "satisfaction_label": sat_label,
        }
        rows.append(out_row)
        
    out_df = pd.DataFrame(rows)
    
    if pipeline:
        from ml.features import CATEGORICAL_FEATURES, NUMERIC_FEATURES
        expected_salary_preds = pipeline.predict(out_df[CATEGORICAL_FEATURES + NUMERIC_FEATURES])
        out_df["expected_salary"] = [int(round(x)) for x in expected_salary_preds]
    else:
        out_df["expected_salary"] = out_df["actual_salary"]
        
    out_df["compensation_ratio"] = out_df.apply(lambda r: round(r["actual_salary"] / r["expected_salary"], 2) if r["expected_salary"] > 0 else 0, axis=1)
    
    # Reorder columns to match original exactly
    out_df = out_df[CSV_COLUMNS]
    
    if not df_existing.empty:
        combined_df = pd.concat([df_existing, out_df], ignore_index=True)
    else:
        combined_df = out_df
        
    combined_df.to_csv(dataset_file, index=False)
    print(f"Successfully processed {len(out_df)} survey rows and appended to {dataset_file}. Total rows: {len(combined_df)}")

if __name__ == "__main__":
    main()
