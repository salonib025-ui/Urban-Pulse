
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "processed" / "metro_traffic_cleaned.csv"


def main():
    df = pd.read_csv(DATA_PATH, parse_dates=["date_time"])

    print("=" * 50)
    print("URBAN PULSE - CLEANED DATA VALIDATION")
    print("=" * 50)

    print("\n1. Dataset shape:", df.shape)
    print("\n2. Missing values:")
    print(df.isna().sum().to_string())

    print("\n3. Duplicate rows:", df.duplicated().sum())

    print("\n4. Date range:")
    print("Start:", df["date_time"].min())
    print("End:  ", df["date_time"].max())

    print("\n5. Traffic volume:")
    print(df["traffic_volume"].describe().round(2).to_string())

    print("\n6. Temperature checks:")
    print("Raw zero-Kelvin values:", (df["temp"] == 0).sum())
    print("Celsius range:",
          round(df["temp_celsius"].min(), 2),
          "to",
          round(df["temp_celsius"].max(), 2))

    print("\n7. Rainfall checks:")
    print("Maximum rain_1h:", df["rain_1h"].max())
    print("Rows with rain_1h > 100:",
          (df["rain_1h"] > 100).sum())

    print("\n8. Time features:")
    print("Hours:", sorted(df["hour"].unique()))
    print("Weekdays:", sorted(df["day_of_week"].unique()))
    print("Weekend counts:")
    print(df["is_weekend"].value_counts().sort_index().to_string())

    print("\n9. Holiday labels:")
    print(df["holiday"].value_counts().head(15).to_string())

    print("\nValidation completed.")


if __name__ == "__main__":
    main()