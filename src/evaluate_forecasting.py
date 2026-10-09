
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


ROOT = Path(__file__).resolve().parent.parent

DATA_PATH = ROOT / "data" / "processed" / "metro_traffic_modeling.csv"
FIGURES_DIR = ROOT / "outputs" / "figures"
PREDICTIONS_PATH = ROOT / "outputs" / "traffic_forecast_predictions.csv"

FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def main():
    print("=" * 60)
    print("URBAN PULSE - FORECAST EVALUATION")
    print("=" * 60)

    df = pd.read_csv(DATA_PATH, parse_dates=["date_time"])
    df = df.sort_values("date_time").reset_index(drop=True)

    numeric_features = [
        "temp_celsius", "rain_1h", "snow_1h", "clouds_all",
        "hour", "day_of_week_num", "month", "is_weekend",
    ]
    categorical_features = ["weather_main"]
    lag_features = ["traffic_lag_1", "traffic_lag_24", "traffic_lag_168"]

    df["traffic_lag_1"] = df["traffic_volume"].shift(1)
    df["traffic_lag_24"] = df["traffic_volume"].shift(24)
    df["traffic_lag_168"] = df["traffic_volume"].shift(168)

    df = df.dropna(subset=lag_features).reset_index(drop=True)

    features = numeric_features + categorical_features + lag_features

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
        ("model", RandomForestRegressor(
            n_estimators=100,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )),
    ])

    print("\nTraining model...")
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    results = pd.DataFrame({
        "date_time": df["date_time"].iloc[split_index:],
        "actual_traffic": y_test.to_numpy(),
        "predicted_traffic": predictions,
    })

    results["error"] = (
        results["actual_traffic"] - results["predicted_traffic"]
    )
    results["absolute_error"] = results["error"].abs()

    results.to_csv(PREDICTIONS_PATH, index=False)

    # 1. Actual vs predicted scatter plot
    plt.figure(figsize=(8, 7))
    sns.scatterplot(
        data=results,
        x="actual_traffic",
        y="predicted_traffic",
        alpha=0.35,
    )
    plt.plot([0, 7500], [0, 7500], linestyle="--")
    plt.title("Actual vs Predicted Traffic")
    plt.xlabel("Actual traffic volume")
    plt.ylabel("Predicted traffic volume")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "10_actual_vs_predicted.png", dpi=300)
    plt.close()

    # 2. Traffic over time: show a manageable seven-day sample
    sample = results.head(24 * 7)

    plt.figure(figsize=(14, 6))
    plt.plot(
        sample["date_time"],
        sample["actual_traffic"],
        label="Actual",
    )
    plt.plot(
        sample["date_time"],
        sample["predicted_traffic"],
        label="Predicted",
    )
    plt.title("Actual vs Predicted Traffic Over One Week")
    plt.xlabel("Date and time")
    plt.ylabel("Traffic volume")
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "11_traffic_forecast_timeline.png", dpi=300)
    plt.close()

    # 3. Distribution of prediction errors
    plt.figure(figsize=(9, 6))
    sns.histplot(results["error"], bins=50, kde=True)
    plt.axvline(0, linestyle="--")
    plt.title("Distribution of Traffic Prediction Errors")
    plt.xlabel("Actual - Predicted traffic")
    plt.ylabel("Number of observations")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "12_prediction_error_distribution.png", dpi=300)
    plt.close()

    print("\nEVALUATION SUMMARY")
    print(f"Test records: {len(results)}")
    print(f"Mean absolute error: {results['absolute_error'].mean():.2f}")
    print(f"Mean signed error: {results['error'].mean():.2f}")
    print(f"90th percentile absolute error: "
          f"{results['absolute_error'].quantile(0.90):.2f}")

    print("\nSaved predictions:", PREDICTIONS_PATH)
    print("Saved charts:")
    print(" - 10_actual_vs_predicted.png")
    print(" - 11_traffic_forecast_timeline.png")
    print(" - 12_prediction_error_distribution.png")


if __name__ == "__main__":
    main()