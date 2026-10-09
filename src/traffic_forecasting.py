
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
OUTPUT_PATH = ROOT / "outputs" / "lag_model_comparison.csv"

def main():
    print("=" * 60)
    print("URBAN PULSE - TRAFFIC FORECASTING")
    print("=" * 60)

    df = pd.read_csv(DATA_PATH, parse_dates=["date_time"])
    df = df.sort_values("date_time").reset_index(drop=True)

    # Features available from the current record
    numeric_features = [
        "temp_celsius",
        "rain_1h",
        "snow_1h",
        "clouds_all",
        "hour",
        "day_of_week_num",
        "month",
        "is_weekend",
    ]

    categorical_features = ["weather_main"]

    # Previous traffic observations
    df["traffic_lag_1"] = df["traffic_volume"].shift(1)
    df["traffic_lag_24"] = df["traffic_volume"].shift(24)
    df["traffic_lag_168"] = df["traffic_volume"].shift(168)

    lag_features = [
        "traffic_lag_1",
        "traffic_lag_24",
        "traffic_lag_168",
    ]

    features = (
        numeric_features
        + categorical_features
        + lag_features
    )

    # Remove rows without enough historical traffic
    df = df.dropna(subset=lag_features).reset_index(drop=True)

    # Chronological split: earlier records train, later records test
    split_index = int(len(df) * 0.8)

    X_train = df[features].iloc[:split_index]
    X_test = df[features].iloc[split_index:]

    y_train = df["traffic_volume"].iloc[:split_index]
    y_test = df["traffic_volume"].iloc[split_index:]

    preprocessor = ColumnTransformer([
        (
            "numeric",
            SimpleImputer(strategy="median"),
            numeric_features + lag_features,
        ),
        (
            "categorical",
            Pipeline([
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("encoder", OneHotEncoder(handle_unknown="ignore")),
            ]),
            categorical_features,
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

    print("\nTraining the forecasting model...")
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    mae = mean_absolute_error(y_test, predictions)
    rmse = mean_squared_error(y_test, predictions) ** 0.5
    r2 = r2_score(y_test, predictions)

    results = pd.DataFrame([{
        "Model": "Random Forest with Lag Features",
        "MAE": mae,
        "RMSE": rmse,
        "R2": r2,
    }])

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUTPUT_PATH, index=False)

    print("\nFORECASTING RESULTS")
    print(results.to_string(index=False))

    print("\nResults saved to:")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()