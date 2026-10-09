
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

ROOT = Path(__file__).resolve().parent.parent

DATA_PATH = ROOT / "outputs" / "traffic_forecast_predictions.csv"
FIGURES_DIR = ROOT / "outputs" / "figures"

FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def main():
    df = pd.read_csv(DATA_PATH, parse_dates=["date_time"])

    df["hour"] = df["date_time"].dt.hour
    df["day_of_week"] = df["date_time"].dt.day_name()

    # Average absolute error by hour
    hourly_error = (
        df.groupby("hour")["absolute_error"]
        .mean()
        .reset_index()
        .sort_values("hour")
    )

    print("\nAVERAGE ABSOLUTE ERROR BY HOUR")
    print(hourly_error.to_string(index=False))

    # Plot hourly error
    plt.figure(figsize=(11, 5))
    sns.barplot(data=hourly_error, x="hour", y="absolute_error")
    plt.title("Traffic Forecast Error by Hour of Day")
    plt.xlabel("Hour of day")
    plt.ylabel("Mean absolute error")
    plt.tight_layout()
    plt.savefig(
        FIGURES_DIR / "13_error_by_hour.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close()

    # Average absolute error by day of week
    weekday_order = [
        "Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday",
    ]

    weekday_error = (
        df.groupby("day_of_week")["absolute_error"]
        .mean()
        .reindex(weekday_order)
        .dropna()
        .reset_index()
    )

    print("\nAVERAGE ABSOLUTE ERROR BY DAY OF WEEK")
    print(weekday_error.to_string(index=False))

    plt.figure(figsize=(11, 5))
    sns.barplot(
        data=weekday_error,
        x="day_of_week",
        y="absolute_error",
    )
    plt.title("Traffic Forecast Error by Day of Week")
    plt.xlabel("Day")
    plt.ylabel("Mean absolute error")
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.savefig(
        FIGURES_DIR / "14_error_by_weekday.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close()

    # Inspect the 20 largest absolute errors
    largest_errors = df.nlargest(20, "absolute_error")[
        ["date_time", "actual_traffic", "predicted_traffic", "error",
         "absolute_error"]
    ]

    print("\n20 LARGEST PREDICTION ERRORS")
    print(largest_errors.to_string(index=False))

    print("\nCharts saved:")
    print(" - outputs/figures/13_error_by_hour.png")
    print(" - outputs/figures/14_error_by_weekday.png")


if __name__ == "__main__":
    main()