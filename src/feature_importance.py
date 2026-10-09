
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
FIGURES_DIR.mkdir(parents=True, exist_ok=True)


def main():
    df = pd.read_csv(DATA_PATH, parse_dates=["date_time"])
    df = df.sort_values("date_time").reset_index(drop=True)

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

    # Use the same chronological split as the first experiment.
    split_index = int(len(df) * 0.8)
    X_train = df[features].iloc[:split_index]
    y_train = df["traffic_volume"].iloc[:split_index]

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

    model.fit(X_train, y_train)

    transformed_names = (
        model.named_steps["preprocessor"].get_feature_names_out()
    )
    importances = model.named_steps["model"].feature_importances_

    importance_df = pd.DataFrame({
        "feature": transformed_names,
        "importance": importances,
    }).sort_values("importance", ascending=False)

    # Group encoded weather categories under one readable feature.
    importance_df["feature_group"] = (
        importance_df["feature"]
        .str.replace("numeric__", "", regex=False)
        .str.replace("categorical__weather_main_", "weather: ", regex=False)
    )

    importance_df.to_csv(
        ROOT / "outputs" / "feature_importance.csv",
        index=False,
    )

    top_features = importance_df.head(15).sort_values("importance")

    plt.figure(figsize=(10, 7))
    sns.barplot(
        data=top_features,
        x="importance",
        y="feature_group",
    )
    plt.title("Random Forest Feature Importance", fontsize=15)
    plt.xlabel("Importance")
    plt.ylabel("Feature")
    plt.tight_layout()

    plt.savefig(
        FIGURES_DIR / "09_feature_importance.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close()

    print("\nTOP 15 MODEL FEATURES")
    print(importance_df.head(15).to_string(index=False))
    print("\nChart saved to outputs/figures/09_feature_importance.png")


if __name__ == "__main__":
    main()