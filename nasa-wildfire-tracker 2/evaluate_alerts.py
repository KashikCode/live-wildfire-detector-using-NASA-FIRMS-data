"""Optional: evaluate an independently scored fire alert model against labels.

Input CSV must have independent ground-truth labels (`y_true` = 0 or 1)
and model-produced predicted probabilities (`y_score` in [0,1]).
NASA VIIRS l/n/h confidence codes are NOT calibrated model probabilities.

Usage: python evaluate_alerts.py labeled_predictions.csv --threshold 0.4
"""
import argparse
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, precision_score, recall_score, average_precision_score


def evaluate(path, threshold):
    df = pd.read_csv(path)
    required = {"y_true", "y_score"}
    if not required.issubset(df.columns):
        raise ValueError("CSV must have y_true and y_score columns")
    if not df["y_true"].isin([0, 1]).all():
        raise ValueError("y_true must contain only 0 or 1")
    if not df["y_score"].between(0, 1).all():
        raise ValueError("y_score must contain predicted probabilities in [0,1]")
    if df["y_true"].nunique() != 2:
        raise ValueError("Both ground-truth classes must be represented")

    labels = df["y_true"].astype(int)
    predicted = (df["y_score"] >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(labels, predicted, labels=[0, 1]).ravel()
    print(f"Threshold: {threshold:.2f}")
    print(f"True positives: {tp}; False positives: {fp}")
    print(f"True negatives: {tn}; False negatives: {fn}")
    print(f"Accuracy:           {accuracy_score(labels, predicted):.3f}")
    print(f"Precision:          {precision_score(labels, predicted, zero_division=0):.3f}")
    print(f"Recall:             {recall_score(labels, predicted, zero_division=0):.3f}")
    print(f"Average precision:  {average_precision_score(labels, df['y_score']):.3f}")
    print("A valid fire detector evaluation must include missed fires in ground truth.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", help="CSV with y_true and y_score")
    parser.add_argument("--threshold", type=float, default=0.5)
    args = parser.parse_args()
    if not 0 <= args.threshold <= 1:
        parser.error("--threshold must be between 0 and 1")
    evaluate(args.csv, args.threshold)
