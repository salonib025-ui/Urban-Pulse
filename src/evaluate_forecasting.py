
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
    print("=" * 65)
    print("URBAN PULSE - FAIR FORECAST EVALUATION")
    print("=" * 65)

    df = pd.read_csv(DATA_PATH, parse_dates=["date_time"])
    df = df.sort_values("date_time").reset_index(drop=True)

    if df["date_time"].duplicated().any():
        raise ValueError(
            "Duplicate timestamps found. Run preprocessing first."
        )

    # Create lags from actual observations at exact previous timestamps.
    traffic_by_time = df.set_index("date_time")["traffic_volume"]

    for lag, hours in [
        ("traffic_lag_1", 1),
        ("traffic_lag_24", 24),
        ("traffic_lag_168", 168),
    ]:
        previous_times = df["date_time"] - pd.Timedelta(hours=hours)
        df[lag] = previous_times.map(traffic_by_time)

    # Split the complete timeline first, matching the fair comparison.
    split_index = int(len(df) * 0.8)
    train_all = df.iloc[:split_index].copy()
    test_all = df.iloc[split_index:].copy()

    # Only retain test timestamps with all three real historical lags.
    test = test_all.dropna(subset=LAG_FEATURES).copy()
    train = train_all.dropna(subset=LAG_FEATURES).copy()

    if test.empty:
        raise ValueError("No test rows have all required historical lags.")

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

    print("\nDATA SPLIT")
    print("-" * 45)
    print(f"All cleaned rows: {len(df)}")
    print(f"Training period rows: {len(train_all)}")
    print(f"Training rows with all lags: {len(train)}")
    print(f"Common test rows: {len(test)}")
    print(f"Test period: {test_all['date_time'].min()} to "
          f"{test_all['date_time'].max()}")
    print(f"Evaluated test period: {test['date_time'].min()} to "
          f"{test['date_time'].max()}")

    print("\nTraining Random Forest with timestamp-validated lags...")
    model.fit(train[features], train["traffic_volume"])

    predictions = model.predict(test[features])

    results = pd.DataFrame({
        "date_time": test["date_time"].to_numpy(),
        "actual_traffic": test["traffic_volume"].to_numpy(),
        "predicted_traffic": predictions,
    })

    results["error"] = (
        results["actual_traffic"] - results["predicted_traffic"]
    )
    results["absolute_error"] = results["error"].abs()

    PREDICTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
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

    # 2. Actual vs predicted traffic over one week
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
    plt.savefig(
        FIGURES_DIR / "11_traffic_forecast_timeline.png", dpi=300
    )
    plt.close()

    # 3. Distribution of prediction errors
    plt.figure(figsize=(9, 6))
    sns.histplot(results["error"], bins=50, kde=True)
    plt.axvline(0, linestyle="--")
    plt.title("Distribution of Traffic Prediction Errors")
    plt.xlabel("Actual - Predicted traffic")
    plt.ylabel("Number of observations")
    plt.tight_layout()
    plt.savefig(
        FIGURES_DIR / "12_prediction_error_distribution.png", dpi=300
    )
    plt.close()

    print("\nEVALUATION SUMMARY")
    print("-" * 45)
    print(f"Test records: {len(results)}")
    print(f"Mean absolute error: {results['absolute_error'].mean():.2f}")
    print(f"Mean signed error: {results['error'].mean():.2f}")
    print(
        "90th percentile absolute error: "
        f"{results['absolute_error'].quantile(0.90):.2f}"
    )

    print("\nSaved predictions:", PREDICTIONS_PATH)
    print("Saved charts:")
    print(" - 10_actual_vs_predicted.png")
    print(" - 11_traffic_forecast_timeline.png")
    print(" - 12_prediction_error_distribution.png")

    print(
        "\nEvaluation note: This is a rolling one-step-ahead evaluation. "
        "Historical traffic observations and weather at the target "
        "timestamp are used as inputs. It does not demonstrate "
        "multi-hour forecasting made entirely in advance."
    )


if __name__ == "__main__":
    main()
