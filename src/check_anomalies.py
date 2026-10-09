
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "processed" / "metro_traffic_cleaned.csv"


def main():
    df = pd.read_csv(DATA_PATH, parse_dates=["date_time"])

    print("=" * 60)
    print("URBAN PULSE - WEATHER ANOMALY INVESTIGATION")
    print("=" * 60)

    # Temperature records that need investigation
    print("\n1. ZERO-KELVIN TEMPERATURE RECORDS")
    bad_temp = df[df["temp"] <= 0]

    print("Count:", len(bad_temp))
    print(
        bad_temp[
            ["date_time", "temp", "temp_celsius", "traffic_volume",
             "weather_main"]
        ].to_string(index=False)
    )

    # Extreme rainfall records
    print("\n2. EXTREME RAINFALL RECORDS")
    extreme_rain = df[df["rain_1h"] > 100]

    print(
        extreme_rain[
            ["date_time", "rain_1h", "traffic_volume",
             "weather_main", "weather_description"]
        ].to_string(index=False)
    )

    # Rainfall distribution
    print("\n3. RAINFALL PERCENTILES")
    print(
        df["rain_1h"]
        .quantile([0, 0.5, 0.9, 0.95, 0.99, 1])
        .to_string()
    )

    print("\nInvestigation completed.")


if __name__ == "__main__":
    main()