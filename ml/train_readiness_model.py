# Small offline script to train a logistic regression model
# on the exported check-ins CSV

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, precision_score, recall_score
import joblib
from pathlib import Path


def main() -> None:
    """
    Load the exported CSV, train a simple logistic regression model,
    print evaluation metrics, and save the model + scaler.
    """
    # path to the CSV exported by the Django management command
    csv_path = Path("checkins_dataset.csv")

    # load the CSV into a pandas DataFrame
    df = pd.read_csv(csv_path)

    if df.empty:
        print("Dataset is empty. Add some check-ins before training.")
        return

    # --- CLEAN & IMPUTE FEATURES ---

    # 1) make sure mood and hrv_rmssd are numeric
    #    errors='coerce' turns non-numeric values into NaN
    df["mood"] = pd.to_numeric(df["mood"], errors="coerce")
    df["hrv_rmssd"] = pd.to_numeric(df["hrv_rmssd"], errors="coerce")

    # 2) handle missing mood values: use median mood as fallback
    if df["mood"].notna().any():
        mood_median = df["mood"].median()
        df["mood"] = df["mood"].fillna(mood_median)
    else:
        # if *all* mood values are missing (very unlikely), just drop those rows
        print("All mood values are missing. Cannot train a model.")
        return

    # 3) handle missing HRV values
    #    If we have at least one real HRV value, use the median
    if df["hrv_rmssd"].notna().any():
        hrv_median = df["hrv_rmssd"].median()
        df["hrv_rmssd"] = df["hrv_rmssd"].fillna(hrv_median)
    else:
        # if there are no HRV values at all, set them to 0 as a neutral default
        df["hrv_rmssd"] = 0.0

    # 4) make sure label is present and numeric
    df["completed"] = pd.to_numeric(df["completed"], errors="coerce")
    df = df.dropna(subset=["completed"])  # drop rows where label is missing
    df["completed"] = df["completed"].astype(int)

    # if after cleaning we have too few rows, warn & exit
    if len(df) < 5:
        print(f"Not enough samples after cleaning (n={len(df)}).")
        print("Add more check-ins and export again.")
        return

    # --- FEATURE MATRIX & LABEL VECTOR ---

    X = df[["mood", "hrv_rmssd"]]
    y = df["completed"]

    # split data into training and test sets
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # scale the features for better model performance
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # initialize and fit a simple logistic regression model
    model = LogisticRegression()
    model.fit(X_train_scaled, y_train)

    # predict probabilities on the test set
    y_proba = model.predict_proba(X_test_scaled)[:, 1]

    # convert probabilities to class predictions using 0.5 threshold
    y_pred = (y_proba >= 0.5).astype(int)

    # calculate evaluation metrics
    auc = roc_auc_score(y_test, y_proba)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)

    # print metrics for your paper
    print(f"AUC:       {auc:.3f}")
    print(f"Precision: {precision:.3f}")
    print(f"Recall:    {recall:.3f}")

    # save model and scaler so they could be used in Django later if desired
    joblib.dump(model, "readiness_model.joblib")
    joblib.dump(scaler, "readiness_scaler.joblib")
    print("Saved model to readiness_model.joblib and readiness_scaler.joblib")


if __name__ == "__main__":
    main()
