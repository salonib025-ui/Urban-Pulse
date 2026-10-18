
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "processed" / "metro_traffic_modeling.csv"
OUTPUT_DIR = ROOT / "outputs"
MODEL_PATH = OUTPUT_DIR / "explainable_traffic_model.joblib"
IMPORTANCE_PATH = OUTPUT_DIR / "shap_global_importance.csv"
DETAILS_PATH = OUTPUT_DIR / "shap_prediction_explanations.csv"

NUMERIC_FEATURES = [
    "temp_celsius",
    "rain_1h",
    "snow_1h",
    "clouds_all",
    "hour",
    "day_of_week_num",
    "month",
    "is_weekend",
]

CATEGORICAL_FEATURES = ["weather_main"]

LAG_FEATURES = [
    "traffic_lag_1",
    "traffic_lag_24",
    "traffic_lag_168",
]

ALL_FEATURES = (
    NUMERIC_FEATURES + CATEGORICAL_FEATURES + LAG_FEATURES
)


def main():
    print("=" * 65)
    print("URBAN PULSE - SHAP EXPLAINABILITY")
    print("=" * 65)

    df = pd.read_csv(DATA_PATH, parse_dates=["date_time"])
    df = df.sort_values("date_time").reset_index(drop=True)

    if df["date_time"].duplicated().any():
        raise ValueError(
            "Duplicate timestamps found. Run preprocessing first."
        )

    # Match historical traffic observations by exact timestamp.
    traffic_by_time = df.set_index("date_time")["traffic_volume"]

    for lag_name, hours in [
        ("traffic_lag_1", 1),
        ("traffic_lag_24", 24),
        ("traffic_lag_168", 168),
    ]:
        previous_times = df["date_time"] - pd.Timedelta(hours=hours)
        df[lag_name] = previous_times.map(traffic_by_time)

    # Use the same chronological split as the fair comparison.
    split_index = int(len(df) * 0.8)
    train_all = df.iloc[:split_index].copy()
    test_all = df.iloc[split_index:].copy()

    train = train_all.dropna(subset=LAG_FEATURES).copy()
    test = test_all.dropna(subset=LAG_FEATURES).copy()

    if train.empty or test.empty:
        raise ValueError("Not enough records with valid traffic lags.")

    X_train = train[ALL_FEATURES]
    X_test = test[ALL_FEATURES]
    y_train = train["traffic_volume"]

    numeric_columns = NUMERIC_FEATURES + LAG_FEATURES

    preprocessor = ColumnTransformer([
        (
            "numeric",
            SimpleImputer(strategy="median"),
            numeric_columns,
        ),
        (
            "categorical",
            Pipeline([
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("encoder", OneHotEncoder(handle_unknown="ignore")),
            ]),
            CATEGORICAL_FEATURES,
        ),
    ])

    model = Pipeline([
        ("preprocessor", preprocessor),
        (
            "model",
            RandomForestRegressor(
                n_estimators=100,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1,
            ),
        ),
    ])

    print(f"\nTraining rows: {len(train):,}")
    print(f"Test rows: {len(test):,}")
    print("\nTraining Random Forest...")
    model.fit(X_train, y_train)

    # Save the fitted pipeline for later dashboard reuse.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    # SHAP explains the fitted forest using the transformed inputs.
    fitted_preprocessor = model.named_steps["preprocessor"]
    fitted_forest = model.named_steps["model"]

    X_test_transformed = fitted_preprocessor.transform(X_test)

    if hasattr(X_test_transformed, "toarray"):
        X_test_transformed = X_test_transformed.toarray()

    transformed_names = fitted_preprocessor.get_feature_names_out()
    transformed_names = [
        name.replace("numeric__", "").replace("categorical__", "")
        for name in transformed_names
    ]

    # Explain a manageable sample for faster execution.
    sample_size = min(200, len(X_test))
    sample_positions = np.linspace(
        0, len(X_test) - 1, num=sample_size, dtype=int
    )
    X_sample = X_test_transformed[sample_positions]

    print(f"Calculating SHAP values for {sample_size} test records...")
    explainer = shap.TreeExplainer(fitted_forest)
    shap_values = explainer.shap_values(X_sample)

    shap_array = np.asarray(shap_values)

    if shap_array.shape != (
    sample_size,
    len(transformed_names),
    ):
      raise ValueError(
        "SHAP output dimensions do not match the sampled records "
        "and transformed features."
    )

    # Global importance = mean absolute SHAP value per transformed feature.
    mean_abs_shap = np.abs(shap_array).mean(axis=0)

    importance = pd.DataFrame({
        "Feature": transformed_names,
        "Mean Absolute SHAP": mean_abs_shap,
    }).sort_values("Mean Absolute SHAP", ascending=False)

    importance.to_csv(IMPORTANCE_PATH, index=False)

    # Explain individual predictions with their feature contributions.
    predictions = model.predict(X_test.iloc[sample_positions])
    expected_value = float(np.asarray(explainer.expected_value).mean())


    detail_rows = []
    for sample_index, row_position in enumerate(sample_positions):
        record = X_test.iloc[row_position]
        contributions = shap_array[sample_index]

        positive_indices = np.where(contributions > 0)[0]
        negative_indices = np.where(contributions < 0)[0]

        top_positive_index = (
            int(positive_indices[np.argmax(contributions[positive_indices])])
            if len(positive_indices) else None
        )
        top_negative_index = (
            int(negative_indices[np.argmin(contributions[negative_indices])])
            if len(negative_indices) else None
        )

        row = {
            "date_time": test.iloc[row_position]["date_time"],
            "actual_traffic": float(test.iloc[row_position]["traffic_volume"]),
            "predicted_traffic": float(predictions[sample_index]),
            "expected_traffic": expected_value,
            "top_positive_feature": (
                transformed_names[top_positive_index]
                if top_positive_index is not None else "None"
            ),
            "top_positive_contribution": (
                float(contributions[top_positive_index])
                if top_positive_index is not None else 0.0
            ),
            "top_negative_feature": (
                transformed_names[top_negative_index]
                if top_negative_index is not None else "None"
            ),
            "top_negative_contribution": (
                float(contributions[top_negative_index])
                if top_negative_index is not None else 0.0
            ),
        }

        # Save each transformed feature's SHAP contribution.
        for feature_index, feature_name in enumerate(transformed_names):
            row[f"shap__{feature_name}"] = float(
                contributions[feature_index]
            )

        detail_rows.append(row)

    details = pd.DataFrame(detail_rows)
    details.to_csv(DETAILS_PATH, index=False)


    print("\nTOP GLOBAL SHAP FEATURES")
    print(importance.head(10).to_string(index=False))

    print("\nSAVED OUTPUTS")
    print(f"Model: {MODEL_PATH}")
    print(f"Global importance: {IMPORTANCE_PATH}")
    print(f"Individual explanations: {DETAILS_PATH}")

    print(
        "\nNote: SHAP values explain model predictions, not causal "
        "relationships. Individual explanations cover the sampled "
        "historical test records."
    )


if __name__ == "__main__":
    main()
