
from pathlib import Path

import pandas as pd

# Find the UrbanPulse project folder automatically
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "metro_interstate_traffic_volume.csv"
)

OUTPUT_DIR = PROJECT_ROOT / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    print("=" * 60)
    print("       URBAN PULSE - DATASET INSPECTION")
    print("=" * 60)

    # Check whether the dataset exists
    if not DATA_PATH.exists():
        print("\nERROR: Dataset file not found.")
        print(f"Expected location: {DATA_PATH}")
        print("Check the CSV filename and folder.")
        return

    # Load the original CSV
    df = pd.read_csv(DATA_PATH)

    # Treat whitespace-only cells as missing values for inspection
    df.replace(r"^\s*$", pd.NA, regex=True, inplace=True)

    print("\n1. DATASET DIMENSIONS")
    print(f"Rows: {df.shape[0]}")
    print(f"Columns: {df.shape[1]}")

    print("\n2. COLUMN NAMES")
    for column in df.columns:
        print(f"- {column}")

    print("\n3. DATA TYPES")
    print(df.dtypes.to_string())

    print("\n4. MISSING VALUES")
    missing = df.isna().sum()
    missing_report = pd.DataFrame({
        "Missing_Count": missing,
        "Missing_Percentage": (
            missing / len(df) * 100 if len(df) else 0
        ).round(2)
    })
    print(missing_report.to_string())

    print("\n5. DUPLICATE ROWS")
    print(f"Exact duplicate rows: {df.duplicated().sum()}")

    print("\n6. FIRST FIVE ROWS")
    print(df.head().to_string(index=False))

    print("\n7. NUMERICAL SUMMARY")
    print(df.describe(include="number").round(2).to_string())

    print("\n8. CATEGORICAL SUMMARY")
    print(
         df[["holiday", "weather_main", "weather_description"]]
         .describe()
         .to_string()
    )

    # Check the date column if it exists
    if "date_time" in df.columns:
        dates = pd.to_datetime(
             df["date_time"],
             format="%d-%m-%Y %H:%M",
             errors="coerce"
        )
        print("\n9. DATE RANGE")
        print(f"Earliest date: {dates.min()}")
        print(f"Latest date:   {dates.max()}")
        print(f"Invalid dates: {dates.isna().sum()}")

    # Save inspection reports for later reference
    missing_report.to_csv(
        OUTPUT_DIR / "missing_values_report.csv"
    )

    df.describe(include="all").transpose().to_csv(
        OUTPUT_DIR / "dataset_summary.csv"
    )

    print("\n" + "=" * 60)
    print("INSPECTION COMPLETED")
    print(f"Reports saved in: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()