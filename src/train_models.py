
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


ROOT = Path(__file__).resolve().parent.parent

DATA_PATH = (
    ROOT / "data" / "processed" / "metro_traffic_modeling.csv"
)

OUTPUT_DIR = ROOT / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    print("=" * 65)
    print("       URBAN PULSE - TRAFFIC PREDICTION MODELS")
    print("=" * 65)

    # 1. Load data
    df = pd.read_csv(DATA_PATH, parse_dates=["date_time"])
    df = df.sort_values("date_time").reset_index(drop=True)

    # 2. Define prediction target and input features
    target = "traffic_volume"

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

    features = numeric_features + categorical_features

    X = df[features]
    y = df[target]

    # 3. Chronological 80/20 split
    split_index = int(len(df) * 0.8)

    X_train = X.iloc[:split_index]
    X_test = X.iloc[split_index:]

    y_train = y.iloc[:split_index]
    y_test = y.iloc[split_index:]

    print(f"\nTraining records: {len(X_train)}")
    print(f"Testing records:  {len(X_test)}")
    print(f"Training period:  {df['date_time'].iloc[0]} to "
          f"{df['date_time'].iloc[split_index - 1]}")
    print(f"Testing period:   {df['date_time'].iloc[split_index]} to "
          f"{df['date_time'].iloc[-1]}")

    # 4. Preprocessing is learned from training data only
    numeric_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

    categorical_transformer = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore")),
    ])

    preprocessor = ColumnTransformer([
        ("numeric", numeric_transformer, numeric_features),
        ("categorical", categorical_transformer, categorical_features),
    ])

    # 5. Define models
    models = {
        "Linear Regression": LinearRegression(),
        "Random Forest": RandomForestRegressor(
            n_estimators=100,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        ),
    }

    results = []
    predictions = pd.DataFrame({
        "date_time": df["date_time"].iloc[split_index:].values,
        "actual_traffic": y_test.values,
    })

    # 6. Historical baseline: mean traffic by hour
    training_hour_means = (
        pd.DataFrame({
            "hour": X_train["hour"],
            "traffic": y_train,
        })
        .groupby("hour")["traffic"]
        .mean()
    )

    baseline_predictions = (
        X_test["hour"]
        .map(training_hour_means)
        .fillna(y_train.mean())
        .to_numpy()
    )

    model_predictions = {
        "Historical Hourly Baseline": baseline_predictions
    }

    # 7. Train and evaluate machine-learning models
    for name, model in models.items():
        pipeline = Pipeline([
            ("preprocessor", preprocessor),
            ("model", model),
        ])

        print(f"\nTraining {name}...")
        pipeline.fit(X_train, y_train)

        pred = pipeline.predict(X_test)
        model_predictions[name] = pred

    # 8. Calculate evaluation metrics
    for name, pred in model_predictions.items():
        mae = mean_absolute_error(y_test, pred)
        rmse = np.sqrt(mean_squared_error(y_test, pred))
        r2 = r2_score(y_test, pred)

        results.append({
            "Model": name,
            "MAE": mae,
            "RMSE": rmse,
            "R2": r2,
        })

        predictions[name] = pred

    results_df = pd.DataFrame(results).sort_values("MAE")
    results_path = OUTPUT_DIR / "model_comparison.csv"
    predictions_path = OUTPUT_DIR / "traffic_predictions.csv"

    results_df.to_csv(results_path, index=False)
    predictions.to_csv(predictions_path, index=False)

    print("\n" + "=" * 65)
    print("MODEL EVALUATION RESULTS")
    print("=" * 65)
    print(results_df.round(3).to_string(index=False))

    print(f"\nMetrics saved to: {results_path}")
    print(f"Predictions saved to: {predictions_path}")
    print("\nModel training and evaluation completed.")


if __name__ == "__main__":
    main()