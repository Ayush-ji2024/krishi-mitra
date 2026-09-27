"""
Train the crop recommendation model on the Kaggle Crop Recommendation dataset.

Dataset : https://www.kaggle.com/datasets/atharvaingle/crop-recommendation-dataset
          data/Crop_recommendation.csv  (N, P, K, temperature, humidity, ph, rainfall, label)

What this script does:
  1. Loads and validates the CSV (columns, missing values, duplicate rows).
  2. Splits it once into train (80%) and test (20%), stratified by crop.
  3. Compares three models with 5-fold cross-validation on the TRAIN part only:
       - Logistic Regression (simple baseline)
       - Random Forest
       - MLP (a small neural network, like the original project used)
  4. Retrains the best model on the full train part and evaluates it ONCE on test.
  5. Saves one file with everything the app needs: models/crop_recommender.joblib
     (the scaler lives INSIDE the pipeline, so it can never get out of sync).
  6. Writes reports to reports/crop/.

Usage:
  python scripts/train_crop_recommender.py
"""

import argparse
import json
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (ConfusionMatrixDisplay, accuracy_score,
                             classification_report, confusion_matrix, f1_score,
                             top_k_accuracy_score)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
TARGET = "label"


# ----------------------------------------------------------------------------- data
def load_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(f"Dataset not found: {path}")
    df = pd.read_csv(path)

    missing_cols = [c for c in FEATURES + [TARGET] if c not in df.columns]
    if missing_cols:
        raise SystemExit(f"CSV is missing columns: {missing_cols}")
    df = df[FEATURES + [TARGET]]

    n_missing = int(df.isna().any(axis=1).sum())
    n_dupes = int(df.duplicated().sum())
    df = df.dropna().drop_duplicates().reset_index(drop=True)

    print(f"Rows after cleaning   : {len(df)}  (dropped {n_missing} with missing values, "
          f"{n_dupes} exact duplicates)")
    counts = df[TARGET].value_counts()
    print(f"Crops                 : {df[TARGET].nunique()}  "
          f"(rows per crop: min {counts.min()}, max {counts.max()})")
    return df


def build_candidates(seed: int):
    """
    Each model is a Pipeline: preprocessing + classifier in ONE object.
    Scaling matters for Logistic Regression and MLP (they compare distances /
    use gradients); Random Forest splits on thresholds, so it doesn't need it.
    """
    return {
        "logistic_regression": Pipeline([
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(max_iter=5000)),
        ]),
        "random_forest": Pipeline([
            ("clf", RandomForestClassifier(n_estimators=300, random_state=seed, n_jobs=-1)),
        ]),
        "mlp": Pipeline([
            ("scale", StandardScaler()),
            # early_stopping is left off on purpose: in some scikit-learn versions it
            # crashes when the labels are text ("rice", "maize"...).
            ("clf", MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=2000,
                                  random_state=seed)),
        ]),
    }


# ----------------------------------------------------------------------------- reports
def save_reports(report_dir: Path, cv_rows, best_name, pipe, X_test, y_test, seed, extra):
    report_dir.mkdir(parents=True, exist_ok=True)
    classes = list(pipe.classes_)
    y_pred = pipe.predict(X_test)
    proba = pipe.predict_proba(X_test)

    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average="macro")
    # The app shows the top 3 crops, so "is the right crop in the top 3?" matters too.
    top3 = top_k_accuracy_score(y_test, proba, k=3, labels=classes)

    pd.DataFrame(cv_rows).to_csv(report_dir / "cv_results.csv", index=False)

    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
    metrics = {
        "model": best_name,
        "test_accuracy": round(acc, 4),
        "test_macro_f1": round(f1, 4),
        "test_top3_accuracy": round(top3, 4),
        "cv_results": cv_rows,
        "per_class": report,
        **extra,
    }
    with open(report_dir / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    # Confusion matrix (22 x 22)
    cm = confusion_matrix(y_test, y_pred, labels=classes)
    fig, ax = plt.subplots(figsize=(11, 11))
    ConfusionMatrixDisplay(cm, display_labels=classes).plot(
        ax=ax, cmap="Greens", colorbar=False, xticks_rotation=90)
    ax.set_title(f"Crop recommender ({best_name}) - test set\n"
                 f"accuracy {acc:.1%}, macro-F1 {f1:.3f}, top-3 {top3:.1%}")
    fig.tight_layout()
    fig.savefig(report_dir / "confusion_matrix.png", dpi=130)
    plt.close(fig)

    # Which inputs matter most? Permutation importance: shuffle one column at a
    # time and see how much the score drops. Works for any model.
    imp = permutation_importance(pipe, X_test, y_test, n_repeats=10,
                                 random_state=seed, scoring="f1_macro")
    order = np.argsort(imp.importances_mean)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.barh(np.array(FEATURES)[order], imp.importances_mean[order],
            xerr=imp.importances_std[order], color="#3a7d44")
    ax.set_xlabel("drop in macro-F1 when the feature is shuffled")
    ax.set_title("Feature importance (permutation, test set)")
    fig.tight_layout()
    fig.savefig(report_dir / "feature_importance.png", dpi=150)
    plt.close(fig)

    print("\n========== TEST SET RESULTS ==========")
    print(f"Model           : {best_name}")
    print(f"Accuracy        : {acc:.3f}")
    print(f"Macro-F1        : {f1:.3f}")
    print(f"Top-3 accuracy  : {top3:.3f}")
    wrong = [(t, p) for t, p in zip(y_test, y_pred) if t != p]
    print(f"Mistakes        : {len(wrong)} of {len(y_test)}")
    for t, p in wrong:
        print(f"    true {t:<12} -> predicted {p}")
    print("\nFeature importance (drop in macro-F1 when shuffled):")
    for i in order[::-1]:
        print(f"    {FEATURES[i]:<12} {imp.importances_mean[i]:.3f}")
    print("======================================")


# ----------------------------------------------------------------------------- main
def main():
    parser = argparse.ArgumentParser(description="Train the crop recommendation model.")
    parser.add_argument("--data_path", default="data/Crop_recommendation.csv")
    parser.add_argument("--model_out", default="models/crop_recommender.joblib")
    parser.add_argument("--report_dir", default="reports/crop")
    parser.add_argument("--test_size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    df = load_data(Path(args.data_path))
    X, y = df[FEATURES], df[TARGET]

    # Split ONCE. The test part is not touched until the very end.
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, stratify=y, random_state=args.seed)
    print(f"Train rows: {len(X_train)} | Test rows: {len(X_test)}")

    # Compare models with 5-fold cross-validation on the train part:
    # train is cut into 5 pieces; each piece takes a turn as the validation set.
    # 5 scores per model -> the mean says how good it is, the std how stable.
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=args.seed)
    cv_rows = []
    print("\n5-fold cross-validation on train (macro-F1):")
    for name, pipe in build_candidates(args.seed).items():
        scores = cross_val_score(pipe, X_train, y_train, cv=cv, scoring="f1_macro", n_jobs=1)
        cv_rows.append({"model": name, "cv_f1_mean": round(scores.mean(), 4),
                        "cv_f1_std": round(scores.std(), 4)})
        print(f"    {name:<20} {scores.mean():.4f} +/- {scores.std():.4f}")

    best = max(cv_rows, key=lambda r: r["cv_f1_mean"])
    best_name = best["model"]
    print(f"\nBest model by cross-validation: {best_name}")

    # Retrain the winner on ALL train rows, then test once.
    pipe = build_candidates(args.seed)[best_name]
    pipe.fit(X_train, y_train)

    out = Path(args.model_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # Save the pipeline plus the info the app needs to validate user input.
    joblib.dump({
        "pipeline": pipe,
        "model_name": best_name,
        "features": FEATURES,
        "classes": list(pipe.classes_),
        "feature_ranges": {f: [float(X_train[f].min()), float(X_train[f].max())] for f in FEATURES},
        "sklearn_version": sklearn.__version__,
    }, out)
    print(f"Model saved to {out}")

    save_reports(Path(args.report_dir), cv_rows, best_name, pipe, X_test, y_test, args.seed, {
        "train_rows": len(X_train), "test_rows": len(X_test), "seed": args.seed,
    })
    print(f"Reports saved to {args.report_dir}/")


if __name__ == "__main__":
    main()