from pathlib import Path
import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs"
FIG = OUT / "figures"
DATA = ROOT / "data" / "processed"

st.set_page_config(page_title="Urban Pulse", page_icon="🚦", layout="wide")

# Keep styling simple until the dashboard is confirmed to render.
st.markdown("""

<style>
/* Main dashboard background and default text */
.stApp {
    background-color: #f5f7fb;
    color: #1e293b;
}

.stApp p,
.stApp h1,
.stApp h2,
.stApp h3,
.stApp h4,
.stApp label,
.stApp li,
.stApp .stMarkdown,
.stApp [data-testid="stCaptionContainer"] {
    color: #1e293b !important;
}

/* Keep sidebar dark with readable white text */
[data-testid="stSidebar"] {
    background-color: #14213d;
}

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #ffffff !important;
}

/* Hero banner */
.hero {
    background: linear-gradient(120deg, #14213d, #2457a7);
    color: #ffffff !important;
    padding: 22px 26px;
    border-radius: 16px;
    margin-bottom: 20px;
}

.hero h1,
.hero p {
    color: #ffffff !important;
}

/* Metrics */
[data-testid="stMetricLabel"],
[data-testid="stMetricValue"],
[data-testid="stMetricDelta"] {
    color: #1e293b !important;
}

/* Tables and dataframe text */
[data-testid="stDataFrame"],
[data-testid="stTable"] {
    color: #1e293b !important;
}

/* Buttons */
.stButton button,
.stDownloadButton button {
    color: #ffffff !important;
    background-color: #2457a7 !important;
    border: none;
    border-radius: 8px;
}

/* Input labels and select boxes */
.stSelectbox label,
.stTextInput label,
.stNumberInput label,
.stDateInput label {
    color: #1e293b !important;
}
</style>
""", unsafe_allow_html=True)

def read_csv(path):
    try:
        return pd.read_csv(path) if path.exists() else None
    except Exception as exc:
        st.warning(f"Could not load {path.name}: {exc}")
        return None


def chart(name, caption=None):
    path = FIG / name

    if not path.is_file():
        st.error(f"Chart file not found: {path}")
        return

    try:
        st.image(str(path), caption=caption, use_container_width=True)
    except Exception as exc:
        st.error(f"Could not display {name}: {exc}")


st.sidebar.title("🚦 URBAN PULSE")
st.sidebar.caption("Traffic intelligence & route planning")
page = st.sidebar.radio(
    "Navigate",
    ["Overview", "Traffic Analytics", "Traffic Forecasting",
     "Route Optimization", "Model Evaluation", "Data Explorer"]
)
st.sidebar.markdown("---")
st.sidebar.caption("Historical Metro Interstate Traffic Volume data")
st.markdown("""
<div class="hero">
  <h1>Urban Pulse</h1>
  <p>Understand traffic patterns. Explore forecasts. Compare routes.</p>
</div>
""", unsafe_allow_html=True)

if page == "Overview":
    st.header("Traffic intelligence at a glance")
    df = read_csv(DATA / "metro_traffic_cleaned.csv")
    if df is None:
        df = read_csv(DATA / "metro_traffic_modeling.csv")
    if df is not None:
        traffic_col = next((c for c in df.columns if c.lower().replace(" ", "_") == "traffic_volume"), None)
        date_col = next((c for c in df.columns if c.lower() in ("date_time", "datetime", "date")), None)
        c1, c2, c3 = st.columns(3)
        c1.metric("Historical records", f"{len(df):,}")
        c2.metric("Dataset columns", str(len(df.columns)))
        if traffic_col:
            c3.metric("Average traffic volume", f"{pd.to_numeric(df[traffic_col], errors='coerce').mean():,.0f}")
        elif date_col:
            c3.metric("Date field", date_col)
        else:
            c3.metric("Dataset", "Loaded")
    else:
        st.warning("Could not find the processed traffic dataset in data/processed/.")
    left, right = st.columns(2)
    with left:
        st.subheader("Traffic by hour")
        chart("01_hourly_traffic.png")
    with right:
        st.subheader("Forecast performance")
        chart("10_actual_vs_predicted.png")
    st.info("Route estimates use an OpenStreetMap road graph and estimated speeds, not live traffic.")

elif page == "Traffic Analytics":
    st.success("Traffic Analytics page is running!")
    st.write("Chart folder:", str(FIG))
    st.write("Chart exists:", (FIG / "01_hourly_traffic.png").exists())
    st.header("Traffic Analytics")
    pairs = [
        ("01_hourly_traffic.png", "Hourly traffic"),
        ("02_weekday_traffic.png", "Weekday traffic"),
        ("03_traffic_distribution.png", "Traffic volume distribution"),
        ("04_traffic_heatmap.png", "Hourly and weekday heatmap"),
        ("05_weather_traffic.png", "Weather and traffic"),
        ("06_temperature_vs_traffic.png", "Temperature vs traffic"),
        ("07_monthly_traffic.png", "Monthly traffic"),
        ("08_correlation_heatmap.png", "Correlation heatmap"),
        ("09_feature_importance.png", "Feature importance"),
    ]
    
    
    for i in range(0, len(pairs), 2):
        col1, col2 = st.columns(2)

        with col1:
            st.subheader(pairs[i][1])
            chart(pairs[i][0])

        if i + 1 < len(pairs):
            with col2:
                st.subheader(pairs[i + 1][1])
                chart(pairs[i + 1][0])

    st.caption(
        "These charts show historical patterns and associations. "
        "They do not establish causation."
    )

elif page == "Traffic Forecasting":
    st.header("Traffic Forecasting")

    df = read_csv(OUT / "traffic_forecast_predictions.csv")

    if df is not None:
        st.metric("Saved forecast records", f"{len(df):,}")
        st.dataframe(df.head(100), use_container_width=True)
        st.download_button(
            "Download predictions",
            df.to_csv(index=False).encode("utf-8"),
            "traffic_forecast_predictions.csv",
            "text/csv",
        )
    else:
        st.warning("Forecast predictions CSV was not found.")

    chart("10_actual_vs_predicted.png", "Actual vs predicted")
    chart("11_traffic_forecast_timeline.png", "Forecast timeline")
    chart("12_prediction_error_distribution.png", "Prediction error distribution")
    chart("13_error_by_hour.png", "Error by hour")
    chart("14_error_by_weekday.png", "Error by weekday")

elif page == "Route Optimization":
    st.header("Route Optimization")
    st.write("Start your existing Flask route optimizer in a second terminal:")
    st.code("python src/route_optimizer.py", language="powershell")
    st.caption("Keep the Flask server running to use the embedded map.")
    components.iframe("http://127.0.0.1:5000", height=750, scrolling=True)

elif page == "Model Evaluation":
    st.header("Model Evaluation")

    for filename, title in [
        ("model_comparison.csv", "Model comparison"),
        ("lag_model_comparison.csv", "Lag forecasting comparison"),
        ("feature_importance.csv", "Feature importance"),
    ]:
        st.subheader(title)
        df = read_csv(OUT / filename)

        if df is not None:
            st.dataframe(df, use_container_width=True)
        else:
            st.warning(f"Missing file: {filename}")

    chart("10_actual_vs_predicted.png", "Actual vs predicted")
    chart("12_prediction_error_distribution.png", "Prediction error distribution")

elif page == "Data Explorer":
    st.header("Data Explorer")

    files = {
        "Cleaned traffic data": DATA / "metro_traffic_cleaned.csv",
        "Modeling data": DATA / "metro_traffic_modeling.csv",
        "Forecast predictions": OUT / "traffic_forecast_predictions.csv",
        "Traffic predictions": OUT / "traffic_predictions.csv",
        "Dataset summary": OUT / "dataset_summary.csv",
        "Missing values report": OUT / "missing_values_report.csv",
    }

    selected = st.selectbox("Choose a dataset", list(files))
    path = files[selected]
    df = read_csv(path)

    if df is not None:
        st.write(f"Rows: {len(df):,} | Columns: {len(df.columns)}")
        st.dataframe(df.head(2000), use_container_width=True)
        st.download_button(
            "Download CSV",
            df.to_csv(index=False).encode("utf-8"),
            path.name,
            "text/csv",
        )
    else:
        st.warning(f"File not found: {path}")
