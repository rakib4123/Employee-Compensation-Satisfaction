#!/usr/bin/env python3
"""Train and compare salary-regression and satisfaction-classification
models on the synthetic BusCom compensation dataset, with SHAP-based
explainability for the best model in each task.

Usage:
    python ml/train_models.py [--data ml/data/synthetic_employee_compensation.csv] [--out ml/outputs]
"""

import argparse
import os

import matplotlib

matplotlib.use("Agg")
import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    precision_score,
    recall_score,
    roc_auc_score,
    root_mean_squared_error,
    r2_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

CATEGORICAL_FEATURES = ["education_level", "language_proficiency", "job_role", "department"]
NUMERIC_FEATURES = [
    "age", "experience_years", "publications_count", "projects_led_count",
    "trainings_count", "skills_score", "boss_assessment_score",
]
REGRESSION_TARGET = "expected_salary"
CLASSIFICATION_TARGET = "satisfaction_label"
CLASSIFICATION_EXTRA_NUMERIC = ["actual_salary", "expected_salary"]

RANDOM_STATE = 42


def build_preprocessor(numeric_features):
    return ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
        ("num", StandardScaler(), numeric_features),
    ])


def fit_transform_split(df, numeric_features, target, test_size=0.2):
    X = df[CATEGORICAL_FEATURES + numeric_features]
    y = df[target]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=RANDOM_STATE
    )
    preprocessor = build_preprocessor(numeric_features)
    X_train_t = preprocessor.fit_transform(X_train)
    X_test_t = preprocessor.transform(X_test)
    feature_names = preprocessor.get_feature_names_out()
    return X_train_t, X_test_t, y_train.to_numpy(), y_test.to_numpy(), feature_names, preprocessor


def run_regression(df, out_dir, artifacts_dir):
    X_train, X_test, y_train, y_test, feature_names, preprocessor = fit_transform_split(
        df, NUMERIC_FEATURES, REGRESSION_TARGET
    )

    models = {
        "LinearRegression": LinearRegression(),
        "RandomForest": RandomForestRegressor(n_estimators=300, random_state=RANDOM_STATE),
        "GradientBoosting": GradientBoostingRegressor(random_state=RANDOM_STATE),
    }

    rows = []
    fitted = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        rows.append({
            "task": "regression",
            "model": name,
            "MAE": mean_absolute_error(y_test, preds),
            "RMSE": root_mean_squared_error(y_test, preds),
            "R2": r2_score(y_test, preds),
        })
        fitted[name] = model

    results = pd.DataFrame(rows).sort_values("RMSE")
    best_name = results.iloc[0]["model"]
    print("\n=== Regression: predicting expected_salary ===")
    print(results.to_string(index=False))
    print(f"Best model: {best_name}")

    explain_model(fitted[best_name], X_train, X_test, feature_names, out_dir, prefix="regression")
    save_pipeline(preprocessor, fitted[best_name], artifacts_dir, "regression_model.joblib")
    return results


def run_classification(df, out_dir, artifacts_dir):
    numeric_features = NUMERIC_FEATURES + CLASSIFICATION_EXTRA_NUMERIC
    df = df.copy()
    df["satisfaction_binary"] = (df[CLASSIFICATION_TARGET] == "Satisfied").astype(int)

    X_train, X_test, y_train, y_test, feature_names, preprocessor = fit_transform_split(
        df, numeric_features, "satisfaction_binary"
    )

    models = {
        "LogisticRegression": LogisticRegression(max_iter=1000),
        "RandomForest": RandomForestClassifier(n_estimators=300, random_state=RANDOM_STATE),
        "GradientBoosting": GradientBoostingClassifier(random_state=RANDOM_STATE),
    }

    rows = []
    fitted = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        probs = model.predict_proba(X_test)[:, 1]
        rows.append({
            "task": "classification",
            "model": name,
            "Accuracy": accuracy_score(y_test, preds),
            "Precision": precision_score(y_test, preds),
            "Recall": recall_score(y_test, preds),
            "F1": f1_score(y_test, preds),
            "ROC_AUC": roc_auc_score(y_test, probs),
        })
        fitted[name] = model

    results = pd.DataFrame(rows).sort_values("ROC_AUC", ascending=False)
    best_name = results.iloc[0]["model"]
    print("\n=== Classification: predicting satisfaction_label ===")
    print(results.to_string(index=False))
    print(f"Best model: {best_name}")

    explain_model(fitted[best_name], X_train, X_test, feature_names, out_dir, prefix="classification")
    save_pipeline(preprocessor, fitted[best_name], artifacts_dir, "classification_model.joblib")
    return results


def save_pipeline(preprocessor, estimator, artifacts_dir, filename):
    pipeline = Pipeline(steps=[("preprocessor", preprocessor), ("estimator", estimator)])
    path = os.path.join(artifacts_dir, filename)
    joblib.dump(pipeline, path)
    print(f"Saved {path}")


def explain_model(model, X_train, X_test, feature_names, out_dir, prefix):
    background = X_train[np.random.default_rng(RANDOM_STATE).choice(X_train.shape[0], size=min(100, X_train.shape[0]), replace=False)]
    explainer = shap.Explainer(model.predict, background, feature_names=feature_names)
    sample = X_test[:200] if X_test.shape[0] > 200 else X_test
    shap_values = explainer(sample)

    plt.figure()
    shap.plots.bar(shap_values, show=False)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, f"{prefix}_shap_bar.png"), dpi=150)
    plt.close()

    plt.figure()
    shap.plots.beeswarm(shap_values, show=False)
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, f"{prefix}_shap_beeswarm.png"), dpi=150)
    plt.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="ml/data/synthetic_employee_compensation.csv")
    parser.add_argument("--out", default="ml/outputs")
    parser.add_argument("--artifacts", default="ml/artifacts")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    os.makedirs(args.artifacts, exist_ok=True)
    df = pd.read_csv(args.data)

    reg_results = run_regression(df, args.out, args.artifacts)
    clf_results = run_classification(df, args.out, args.artifacts)

    comparison_path = os.path.join(args.out, "model_comparison.csv")
    pd.concat([reg_results, clf_results], ignore_index=True).to_csv(comparison_path, index=False)
    print(f"\nSaved comparison table to {comparison_path}")
    print(f"Saved SHAP plots to {args.out}/")


if __name__ == "__main__":
    main()
