
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "processed" / "metro_traffic_modeling.csv"
OUTPUT_PATH = ROOT / "outputs" / "lag_model_comparison.csv"

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


def main():
    print("=" * 60)
    print("URBAN PULSE - TRAFFIC FORECASTING")
    print("=" * 60)

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Modeling dataset not found: {DATA_PATH}"
        )

    df = pd.read_csv(DATA_PATH, parse_dates=["date_time"])
    df = df.sort_values("date_time").reset_index(drop=True)

    if df["date_time"].duplicated().any():
        raise ValueError(
            "Duplicate timestamps found. Run preprocessing first."
        )

    traffic_by_time = df.set_index("date_time")["traffic_volume"]

    for lag, hours in [
        ("traffic_lag_1", 1),
        ("traffic_lag_24", 24),
        ("traffic_lag_168", 168),
    ]:
        previous_times = df["date_time"] - pd.Timedelta(hours=hours)
        df[lag] = previous_times.map(traffic_by_time)

    # Split the full timeline before filtering missing lag values.
    split_index = int(len(df) * 0.8)
    train_all = df.iloc[:split_index].copy()
    test_all = df.iloc[split_index:].copy()

    train = train_all.dropna(subset=LAG_FEATURES).copy()
    test = test_all.dropna(subset=LAG_FEATURES).copy()

    if train.empty or test.empty:
        raise ValueError(
            "Not enough records with valid historical traffic lags."
        )

    features = (
        NUMERIC_FEATURES + CATEGORICAL_FEATURES + LAG_FEATURES
    )
    numeric_features = NUMERIC_FEATURES + LAG_FEATURES

    preprocessor = ColumnTransformer([
        (
            "numeric",
            SimpleImputer(strategy="median"),
            numeric_features,
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
        ("model", RandomForestRegressor(
            n_estimators=100,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )),
    ])

    print("\nCHRONOLOGICAL DATA SPLIT")
    print("-" * 40)
    print(f"All cleaned rows: {len(df)}")
    print(f"Training period rows: {len(train_all)}")
    print(f"Training rows with all lags: {len(train)}")
    print(f"Testing period rows: {len(test_all)}")
    print(f"Test rows with all lags: {len(test)}")
    print(
        f"Training period: {train_all['date_time'].min()} to "
        f"{train_all['date_time'].max()}"
    )
    print(
        f"Testing period: {test_all['date_time'].min()} to "
        f"{test_all['date_time'].max()}"
    )

    print("\nTraining Random Forest...")
    model.fit(train[features], train["traffic_volume"])
    predictions = model.predict(test[features])

    mae = mean_absolute_error(test["traffic_volume"], predictions)
    rmse = mean_squared_error(
        test["traffic_volume"], predictions
    ) ** 0.5
    r2 = r2_score(test["traffic_volume"], predictions)

    results = pd.DataFrame([{
        "Model": "Random Forest with Timestamp-Validated Lags",
        "MAE": mae,
        "RMSE": rmse,
        "R2": r2,
    }])

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUTPUT_PATH, index=False)

    print("\nFORECASTING RESULTS")
    print(results.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print(f"\nResults saved to:\n{OUTPUT_PATH}")

    print(
        "\nEvaluation note: this is a rolling one-step-ahead evaluation. "
        "Historical traffic observations and weather at the target "
        "timestamp are used as inputs. It does not establish "
        "multi-hour forecasting performance."
    )


if __name__ == "__main__":
    main()
