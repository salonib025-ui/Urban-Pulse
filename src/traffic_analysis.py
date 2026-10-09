
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Project paths
ROOT = Path(__file__).resolve().parent.parent

DATA_PATH = ROOT / "data" / "processed" / "metro_traffic_cleaned.csv"
FIGURES_DIR = ROOT / "outputs" / "figures"

FIGURES_DIR.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", context="notebook")


def main():
    print("=" * 60)
    print("       URBAN PULSE - TRAFFIC ANALYSIS")
    print("=" * 60)

    # Load the cleaned dataset
    df = pd.read_csv(DATA_PATH, parse_dates=["date_time"])

    # --------------------------------------------------
    # CHART 1: Average traffic volume by hour
    # --------------------------------------------------
    hourly_traffic = (
        df.groupby("hour")["traffic_volume"]
        .mean()
        .reindex(range(24))
    )

    plt.figure(figsize=(11, 5))
    plt.plot(
        hourly_traffic.index,
        hourly_traffic.values,
        marker="o",
        linewidth=2
    )

    plt.title("Average Traffic Volume by Hour", fontsize=15)
    plt.xlabel("Hour of Day (0–23)")
    plt.ylabel("Average Traffic Volume")
    plt.xticks(range(24))
    plt.tight_layout()

    plt.savefig(
        FIGURES_DIR / "01_hourly_traffic.png",
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()

    print("\n1. HOURLY TRAFFIC")
    print(f"Highest average traffic hour: {hourly_traffic.idxmax()}:00")
    print(f"Lowest average traffic hour: {hourly_traffic.idxmin()}:00")

    # --------------------------------------------------
    # CHART 2: Average traffic by day of the week
    # --------------------------------------------------
    weekdays = [
        "Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday"
    ]

    daily_traffic = (
        df.groupby("day_of_week")["traffic_volume"]
        .mean()
        .reindex(weekdays)
    )

    plt.figure(figsize=(10, 5))
    sns.barplot(
        x=daily_traffic.index,
        y=daily_traffic.values
    )

    plt.title("Average Traffic Volume by Day of the Week", fontsize=15)
    plt.xlabel("Day of the Week")
    plt.ylabel("Average Traffic Volume")
    plt.xticks(rotation=25)
    plt.tight_layout()

    plt.savefig(
        FIGURES_DIR / "02_weekday_traffic.png",
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()

    print("\n2. DAILY TRAFFIC")
    print(daily_traffic.round(2).to_string())

    # --------------------------------------------------
    # CHART 3: Distribution of traffic volume
    # --------------------------------------------------
    plt.figure(figsize=(10, 5))
    sns.histplot(
        data=df,
        x="traffic_volume",
        bins=40,
        kde=True
    )

    plt.title("Distribution of Traffic Volume", fontsize=15)
    plt.xlabel("Traffic Volume")
    plt.ylabel("Number of Observations")
    plt.tight_layout()

    plt.savefig(
        FIGURES_DIR / "03_traffic_distribution.png",
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()
    
    
    # --------------------------------------------------
    # CHART 4: Traffic volume by day and hour
    # --------------------------------------------------
    weekdays = [
        "Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday"
    ]

    heatmap_data = df.pivot_table(
        index="day_of_week",
        columns="hour",
        values="traffic_volume",
        aggfunc="mean"
    )

    # Keep weekdays and hours in the correct order
    heatmap_data = heatmap_data.reindex(weekdays)
    heatmap_data = heatmap_data.reindex(columns=range(24))

    plt.figure(figsize=(16, 6))

    sns.heatmap(
        heatmap_data,
        cmap="YlOrRd",
        linewidths=0.2,
        cbar_kws={"label": "Average Traffic Volume"}
    )

    plt.title(
        "Average Traffic Volume by Day of Week and Hour",
        fontsize=15
    )
    plt.xlabel("Hour of Day")
    plt.ylabel("Day of Week")
    plt.tight_layout()

    plt.savefig(
        FIGURES_DIR / "04_traffic_heatmap.png",
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()

    print("\n4. DAY-OF-WEEK VS HOUR HEATMAP")
    print("Heatmap saved as 04_traffic_heatmap.png")
    
    
    # --------------------------------------------------
    # CHART 5: Average traffic by weather condition
    # --------------------------------------------------
    weather_traffic = (
        df.groupby("weather_main")["traffic_volume"]
        .agg(["mean", "count"])
        .sort_values("mean", ascending=False)
    )

    plt.figure(figsize=(11, 6))

    sns.barplot(
        data=weather_traffic.reset_index(),
        x="mean",
        y="weather_main"
    )

    plt.title(
        "Average Traffic Volume by Weather Condition",
        fontsize=15
    )
    plt.xlabel("Average Traffic Volume")
    plt.ylabel("Weather Condition")
    plt.tight_layout()

    plt.savefig(
        FIGURES_DIR / "05_weather_traffic.png",
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()

    weather_traffic.to_csv(
        FIGURES_DIR / "weather_traffic_summary.csv"
    )

    print("\n5. AVERAGE TRAFFIC BY WEATHER")
    print(weather_traffic.round(2).to_string())
    print("Chart saved as 05_weather_traffic.png")
    
    
    # --------------------------------------------------
    # CHART 6: Temperature versus traffic volume
    # --------------------------------------------------

    # Exclude physically implausible zero-Kelvin readings
    # from this chart only; preserve the records elsewhere.
    temperature_data = df[df["temp"] > 0].copy()

    plt.figure(figsize=(10, 6))

    sns.scatterplot(
        data=temperature_data,
        x="temp_celsius",
        y="traffic_volume",
        alpha=0.25,
        s=12
    )

    plt.title(
        "Temperature vs Traffic Volume",
        fontsize=15
    )
    plt.xlabel("Temperature (°C)")
    plt.ylabel("Traffic Volume")
    plt.tight_layout()

    plt.savefig(
        FIGURES_DIR / "06_temperature_vs_traffic.png",
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()

    print("\n6. TEMPERATURE VS TRAFFIC")
    print(
        "Records plotted:",
        len(temperature_data)
    )
    print(
        "Chart saved as 06_temperature_vs_traffic.png"
    )
    
    
    # --------------------------------------------------
    # CHART 7: Average traffic volume by month
    # --------------------------------------------------
    month_names = [
        "January", "February", "March", "April",
        "May", "June", "July", "August",
        "September", "October", "November", "December"
    ]

    monthly_traffic = (
        df.groupby("month")["traffic_volume"]
        .mean()
        .reindex(range(1, 13))
    )

    plt.figure(figsize=(12, 5))

    sns.lineplot(
        x=range(1, 13),
        y=monthly_traffic.values,
        marker="o",
        linewidth=2
    )

    plt.title(
        "Average Traffic Volume by Month",
        fontsize=15
    )
    plt.xlabel("Month")
    plt.ylabel("Average Traffic Volume")
    plt.xticks(
        range(1, 13),
        month_names,
        rotation=35,
        ha="right"
    )
    plt.tight_layout()

    plt.savefig(
        FIGURES_DIR / "07_monthly_traffic.png",
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()

    monthly_summary = pd.DataFrame({
        "month": month_names,
        "average_traffic_volume": monthly_traffic.values
    })

    monthly_summary.to_csv(
        FIGURES_DIR / "monthly_traffic_summary.csv",
        index=False
    )

    print("\n7. AVERAGE TRAFFIC BY MONTH")
    print(monthly_summary.round(2).to_string(index=False))
    print("Chart saved as 07_monthly_traffic.png")
    
    
    # --------------------------------------------------
    # CHART 8: Correlation heatmap
    # --------------------------------------------------

    numeric_columns = [
        "temp_celsius",
        "rain_1h",
        "snow_1h",
        "clouds_all",
        "traffic_volume",
        "hour",
        "month",
        "year"
    ]

    correlation_data = df[numeric_columns].copy()

    # Exclude physically implausible temperature values
    # from this correlation calculation only.
    correlation_data.loc[
        df["temp"] <= 0, "temp_celsius"
    ] = float("nan")

    correlation_matrix = correlation_data.corr(
        numeric_only=True
    )

    plt.figure(figsize=(11, 8))

    sns.heatmap(
        correlation_matrix,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        center=0,
        vmin=-1,
        vmax=1,
        square=True
    )

    plt.title(
        "Correlation Heatmap of Traffic and Weather Features",
        fontsize=15
    )
    plt.tight_layout()

    plt.savefig(
        FIGURES_DIR / "08_correlation_heatmap.png",
        dpi=300,
        bbox_inches="tight"
    )
    plt.close()

    correlation_matrix.to_csv(
        FIGURES_DIR / "correlation_matrix.csv"
    )

    print("\n8. CORRELATION WITH TRAFFIC VOLUME")
    print(
        correlation_matrix["traffic_volume"]
        .sort_values(ascending=False)
        .round(3)
        .to_string()
    )
    print("Chart saved as 08_correlation_heatmap.png")

    print("\n3. TRAFFIC DISTRIBUTION")
    print(df["traffic_volume"].describe().round(2).to_string())

    # Save numerical summaries for the report
    hourly_traffic.rename("average_traffic_volume").to_csv(
        FIGURES_DIR / "hourly_traffic_summary.csv"
    )

    daily_traffic.rename("average_traffic_volume").to_csv(
        FIGURES_DIR / "daily_traffic_summary.csv"
    )

    print("\n" + "=" * 60)
    print("TRAFFIC ANALYSIS COMPLETED")
    print(f"Charts saved to: {FIGURES_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()