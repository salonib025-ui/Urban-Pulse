
import subprocess
import sys
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable

SCRIPTS = {
    "1": ("Launch Streamlit Dashboard",
          ["-m", "streamlit", "run", "dashboard/app.py"]),

    "2": ("Preprocess Traffic Data",
          ["src/preprocess_data.py"]),

    "3": ("Train and Compare Models",
          ["src/train_models.py"]),

    "4": ("Traffic Forecasting",
          ["src/traffic_forecasting.py"]),

    "5": ("Evaluate Forecasting",
          ["src/evaluate_forecasting.py"]),

    "6": ("Traffic Analysis",
          ["src/traffic_analysis.py"]),

    "7": ("Feature Importance",
          ["src/feature_importance.py"]),

    "8": ("Traffic Explainability",
          ["src/traffic_explainability.py"]),

    "9": ("Interactive Route Optimizer",
          ["src/route_optimizer.py"]),

    "10": ("Validate Data",
           ["src/validate_data.py"]),

    "11": ("Inspect Data",
           ["src/inspect_data.py"]),
}


def run_script(choice):
    name, command = SCRIPTS[choice]

    print(f"\nRunning: {name}")
    print("-" * 50)

    try:
        result = subprocess.run(
            [PYTHON] + command,
            cwd=BASE_DIR,
            check=False
        )

        if result.returncode == 0:
            print(f"\n{name} finished.")
        else:
            print(
                f"\n{name} exited with code "
                f"{result.returncode}."
            )

    except FileNotFoundError as error:
        print(f"Unable to start: {error}")


def open_route_comparison():
    route_file = BASE_DIR / "outputs" / "route_comparison.html"

    if route_file.exists():
        webbrowser.open(route_file.resolve().as_uri())
        print("Opened saved route comparison.")
    else:
        print("Route comparison HTML was not found.")


def main():
    while True:
        print("\n" + "=" * 50)
        print("                 URBAN PULSE")
        print("            CENTRAL EXECUTION MENU")
        print("=" * 50)

        for key, (name, _) in SCRIPTS.items():
            print(f"{key}. {name}")

        print("12. Open Saved Route Comparison")
        print("0. Exit")

        choice = input("\nEnter your choice: ").strip()

        if choice == "0":
            print("Urban Pulse closed.")
            break
        elif choice in SCRIPTS:
            run_script(choice)
        elif choice == "12":
            open_route_comparison()
        else:
            print("Invalid choice. Try again.")


if __name__ == "__main__":
    main()
