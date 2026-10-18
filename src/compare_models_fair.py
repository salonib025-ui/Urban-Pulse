
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "processed" / "metro_traffic_modeling.csv"
OUTPUT_PATH = ROOT / "outputs" / "fair_model_comparison.csv"

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
LAG_FEATURES = ["traffic_lag_1", "traffic_lag_24", "traffic_lag_168"]


def make_random_forest(features):
    """Create a preprocessing and Random Forest pipeline."""
    numeric = [c for c in features if c in NUMERIC_FEATURES + LAG_FEATURES]
    categorical = [c for c in features if c in CATEGORICAL_FEATURES]

    transformers = []

    if numeric:
        transformers.append((
            "numeric",
            SimpleImputer(strategy="median"),
            numeric,
        ))

    if categorical:
        transformers.append((
            "categorical",
            Pipeline([
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("encoder", OneHotEncoder(handle_unknown="ignore")),
            ]),
            categorical,
        ))

    return Pipeline([
        ("preprocessor", ColumnTransformer(transformers)),
        ("model", RandomForestRegressor(
            n_estimators=100,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )),
    ])


def calculate_metrics(name, actual, predicted):
    return {
        "Model": name,
        "Test Rows": len(actual),
        "MAE": mean_absolute_error(actual, predicted),
        "RMSE": mean_squared_error(actual, predicted) ** 0.5,
        "R2": r2_score(actual, predicted),
    }


def main():
    print("=" * 65)
    print("URBAN PULSE - FAIR MODEL COMPARISON")
    print("=" * 65)

    df = pd.read_csv(DATA_PATH, parse_dates=["date_time"])
    df = df.sort_values("date_time").reset_index(drop=True)

    if df["date_time"].duplicated().any():
        raise ValueError(
            "Duplicate timestamps found. Run preprocessing first."
        )

    # Construct lags using exact timestamps, not row offsets.
    traffic_by_time = df.set_index("date_time")["traffic_volume"]

    for lag, hours in [
        ("traffic_lag_1", 1),
        ("traffic_lag_24", 24),
        ("traffic_lag_168", 168),
    ]:
        previous_times = df["date_time"] - pd.Timedelta(hours=hours)
        df[lag] = previous_times.map(traffic_by_time)

    # Define one chronological split on the complete cleaned timeline.
    split_index = int(len(df) * 0.8)
    train_all = df.iloc[:split_index].copy()
    test_all = df.iloc[split_index:].copy()

    # All models are evaluated on the same test timestamps.
    # This common test set requires all three genuine lag observations.
    test_common = test_all.dropna(subset=LAG_FEATURES).copy()

    # Lag model training also requires all three historical observations.
    train_lag = train_all.dropna(subset=LAG_FEATURES).copy()

    # Matched training set: all models use the same timestamps.
    train_common = train_lag.copy()

    if test_common.empty:
        raise ValueError("No common test rows have all required lags.")

    base_features = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    all_features = base_features + LAG_FEATURES

    X_train_base = train_all[base_features]
    X_test_base = test_common[base_features]

    X_train_lag = train_lag[all_features]
    X_test_lag = test_common[all_features]

    y_train_base = train_all["traffic_volume"]
    y_train_lag = train_lag["traffic_volume"]
    y_test = test_common["traffic_volume"]

    print("\nDATA SPLIT")
    print("-" * 45)
    print(f"All cleaned rows: {len(df)}")
    print(f"Training period rows: {len(train_all)}")
    print(f"Training period: {train_all['date_time'].min()} to "
          f"{train_all['date_time'].max()}")
    print(f"Testing period: {test_all['date_time'].min()} to "
          f"{test_all['date_time'].max()}")
    print(f"Common test rows used by all models: {len(test_common)}")
    print(f"Training rows available to baseline/RF: {len(train_all)}")
    print(f"Training rows available to lag RF: {len(train_lag)}")

    # Model 1: historical hourly mean learned from training data only.
    hourly_means = train_all.groupby("hour")["traffic_volume"].mean()
    overall_mean = train_all["traffic_volume"].mean()
    baseline_predictions = (
        test_common["hour"].map(hourly_means).fillna(overall_mean)
    )

    # Model 2: Random Forest without traffic lags.
    print("\nTraining Random Forest without lag features...")
    base_model = make_random_forest(base_features)
    base_model.fit(X_train_base, y_train_base)
    base_predictions = base_model.predict(X_test_base)

    # Model 3: Random Forest with timestamp-validated traffic lags.
    print("Training Random Forest with lag features...")
    lag_model = make_random_forest(all_features)
    lag_model.fit(X_train_lag, y_train_lag)
    lag_predictions = lag_model.predict(X_test_lag)


    # Matched-training experiment: all models use identical training rows.
    print("\nRunning matched-training-sample comparison...")

    matched_features = base_features
    X_train_matched_base = train_lag[matched_features]
    y_train_matched = train_lag["traffic_volume"]

    # Matched historical hourly baseline
    matched_hourly_means = (
        train_lag.groupby("hour")["traffic_volume"].mean()
    )
    matched_overall_mean = train_lag["traffic_volume"].mean()
    matched_baseline_predictions = (
        test_common["hour"]
        .map(matched_hourly_means)
        .fillna(matched_overall_mean)
    )

    # Matched Random Forest without lags
    matched_base_model = make_random_forest(matched_features)
    matched_base_model.fit(
        X_train_matched_base,
        y_train_matched,
    )
    matched_base_predictions = matched_base_model.predict(
        test_common[matched_features]
    )

    # Matched Random Forest with lags
    matched_all_features = base_features + LAG_FEATURES
    matched_lag_model = make_random_forest(matched_all_features)
    matched_lag_model.fit(
        train_lag[matched_all_features],
        y_train_matched,
    )
    matched_lag_predictions = matched_lag_model.predict(
        test_common[matched_all_features]
    )


    # All metrics use precisely the same test timestamps and target values.

    results = pd.DataFrame([
        # Original experiment
        calculate_metrics(
            "Historical Hourly Baseline",
            y_test,
            baseline_predictions,
        ),
        calculate_metrics(
            "Random Forest without Lags",
            y_test,
            base_predictions,
        ),
        calculate_metrics(
            "Random Forest with Timestamp-Validated Lags",
            y_test,
            lag_predictions,
        ),

        # Matched-training experiment
        calculate_metrics(
            "Matched - Historical Hourly Baseline",
            y_test,
            matched_baseline_predictions,
        ),
        calculate_metrics(
            "Matched - Random Forest without Lags",
            y_test,
            matched_base_predictions,
        ),
        calculate_metrics(
            "Matched - Random Forest with Lags",
            y_test,
            matched_lag_predictions,
        ),
    ])


    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUTPUT_PATH, index=False)

    print("\nFAIR MODEL COMPARISON")
    print("-" * 65)
    print(results.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    print(f"\nSaved comparison to:\n{OUTPUT_PATH}")
    print(
        "\nEvaluation note: test predictions use observed weather at "
        "the target timestamp. Lag predictions also use historical "
        "traffic observations available at each test timestamp. "
        "This is a rolling one-step-ahead evaluation, not a multi-hour "
        "forecast made entirely in advance."
    )


if __name__ == "__main__":
    main()
