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


/* Overview metric cards */
.metric-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 18px;
    margin: 14px 0 28px 0;
}

.metric-card {
    background: #ffffff;
    border: 1px solid #e5eaf3;
    border-radius: 16px;
    padding: 22px 22px 20px;
    min-height: 145px;
    box-shadow: 0 4px 14px rgba(30, 55, 90, 0.045);
    position: relative;
    overflow: hidden;
}

.metric-card::before {
    content: "";
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 4px;
    background: var(--accent);
}

.metric-card.blue {
    --accent: #4385f5;
    --tint: #eaf2ff;
}

.metric-card.teal {
    --accent: #12a594;
    --tint: #e5f8f4;
}

.metric-card.purple {
    --accent: #8b6ce8;
    --tint: #f0ebff;
}

.metric-top {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 17px;
}

.metric-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 42px;
    height: 42px;
    border-radius: 12px;
    background: var(--tint);
    font-size: 22px;
}

.metric-label {
    color: #667085;
    font-size: 0.88rem;
    font-weight: 600;
    line-height: 1.35;
}

.metric-value {
    color: #172b4d;
    font-size: clamp(1.45rem, 2.2vw, 2rem);
    font-weight: 750;
    line-height: 1.2;
    letter-spacing: -0.7px;
    overflow-wrap: anywhere;
}

.metric-note {
    color: #8490a5;
    font-size: 0.78rem;
    margin-top: 7px;
}

.section-heading {
    color: #172b4d;
    font-size: 1.2rem;
    font-weight: 700;
    margin: 12px 0 4px 0;
}

.section-description {
    color: #748198;
    font-size: 0.9rem;
    margin-bottom: 16px;
}

.chart-panel {
    background: #ffffff;
    border: 1px solid #e5eaf3;
    border-radius: 15px;
    padding: 16px 18px 8px;
    margin-bottom: 20px;
    box-shadow: 0 3px 12px rgba(30, 55, 90, 0.035);
}

@media (max-width: 700px) {
    .metric-grid {
        grid-template-columns: 1fr;
    }
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
        st.info(
<<<<<<< HEAD
            "Insight: Traffic volume varies throughout the day, "
                "with higher average traffic during peak commuting hours. "
                "This pattern can help identify periods when traffic "
                "management and route planning are most important."
            )
    
=======
            "Key Insight: Average traffic volume is highest around "
            "4 PM (16:00) and lowest around 3 AM (03:00). "
            "This indicates a strong daily traffic pattern that "
            "can help identify peak and off-peak periods."
            )
>>>>>>> 7a03768d5757792332a169fb82a1e056c90933c4
    except Exception as exc:
        st.error(f"Could not display {name}: {exc}")


st.sidebar.title("🚦 URBAN PULSE")
st.sidebar.caption("Traffic intelligence & route planning")


def open_route_optimizer():
    st.session_state["page"] = "Route Optimization"



pages = [
    "Overview",
    "Traffic Analytics",
    "Traffic Forecasting",
    "Route Optimization",
    "Model Evaluation",
    "Data Explorer",
]

if "page" not in st.session_state:
    st.session_state["page"] = "Overview"

with st.sidebar:
    st.markdown("## 🏙️ Urban Pulse")
    st.caption("Traffic Intelligence Dashboard")
    st.divider()

    page = st.radio(
        "NAVIGATION",
        pages,
        key="page",
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
        
        traffic_col = next(
            (
                c for c in df.columns
                if c.lower().replace(" ", "_") == "traffic_volume"
            ),
            None,
        )

        avg_traffic = (
            pd.to_numeric(df[traffic_col], errors="coerce").mean()
            if traffic_col else None
        )

        average_text = (
            f"{avg_traffic:,.0f}"
            if avg_traffic is not None and pd.notna(avg_traffic)
            else "N/A"
        )

        st.markdown(
            f"""
<div class="metric-grid">
<div class="metric-card blue">
<div class="metric-top">
<div class="metric-icon">📊</div>
<div class="metric-label">Historical records</div>
</div>
<div class="metric-value">{len(df):,}</div>
<div class="metric-note">Records in the loaded dataset</div>
</div>
<div class="metric-card teal">
<div class="metric-top">
<div class="metric-icon">🧩</div>
<div class="metric-label">Dataset columns</div>
</div>
<div class="metric-value">{len(df.columns)}</div>
<div class="metric-note">Available data fields</div>
</div>
<div class="metric-card purple">
<div class="metric-top">
<div class="metric-icon">🚦</div>
<div class="metric-label">Average traffic volume</div>
</div>
<div class="metric-value">{average_text}</div>
<div class="metric-note">Mean across available records</div>
</div>
</div>
            """,
            unsafe_allow_html=True,
        )


    else:
        st.warning("Could not find the processed traffic dataset in data/processed/.")
    left, right = st.columns(2)
    with left:
        st.subheader("Traffic by hour")
        chart("01_hourly_traffic.png")
    with right:
        st.subheader("Forecast performance")
        chart("10_actual_vs_predicted.png")
    
    st.divider()
    st.subheader("🧭 Smart Route Recommendations")
    st.caption(
        "Explore alternative routes based on distance, estimated "
        "travel time, and traffic signals."
    )

    route_col, info_col = st.columns([1.4, 1], gap="large")

    with route_col:
        st.markdown("#### Compare your route options")

        st.markdown(
            """
            <div style="background:white; border:1px solid #e4eaf3;
                        border-radius:14px; padding:16px; margin-bottom:12px;">
                <div style="font-size:17px; font-weight:650; color:#2457a7;">
                    🔵 Shortest Route
                </div>
                <div style="color:#53627a; font-size:14px;">
                    Prioritizes the total road distance.
                </div>
            </div>
            <div style="background:white; border:1px solid #e4eaf3;
                        border-radius:14px; padding:16px; margin-bottom:12px;">
                <div style="font-size:17px; font-weight:650; color:#16804a;">
                    🟢 Fastest Route
                </div>
                <div style="color:#53627a; font-size:14px;">
                    Prioritizes estimated journey time.
                </div>
            </div>
            <div style="background:white; border:1px solid #e4eaf3;
                        border-radius:14px; padding:16px;">
                <div style="font-size:17px; font-weight:650; color:#805ad5;">
                    🟣 Custom Route
                </div>
                <div style="color:#53627a; font-size:14px;">
                    Balances route preferences using your chosen priorities.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with info_col:
        st.markdown(
            """
            <div style="
                background:linear-gradient(145deg,#14213d,#2457a7);
                border-radius:16px; padding:22px; color:white;
                min-height:235px;">
                <div style="font-size:36px;">🗺️</div>
                <div style="font-size:21px; font-weight:700; margin:10px 0;">
                    Plan a smarter journey
                </div>
                <div style="font-size:14px; color:#e4efff;">
                    Select your starting point and destination, view routes
                    on the map, and compare estimated travel metrics.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.write("")
        
        if st.button(
         "Open Route Optimizer →",
         type="primary",
        use_container_width=True,
        key="overview_route_button",
        on_click=open_route_optimizer,
        ):
         pass
 

    st.caption(
        "Route estimates use an OpenStreetMap road network and estimated "
        "speeds; they do not represent live traffic conditions."
    )



elif page == "Traffic Analytics":
    st.header("Traffic Analytics")
    st.markdown(
        '<p class="section-description">'
        'Explore historical traffic patterns, weather associations, '
        'and model insights.</p>',
        unsafe_allow_html=True,
    )

    # Section 1: Traffic patterns
    st.markdown(
        '<div class="section-heading">🕒 Traffic patterns</div>'
        '<div class="section-description">'
        'Identify peak hours and recurring weekly or monthly trends.'
        '</div>',
        unsafe_allow_html=True,
    )

    a, b = st.columns(2, gap="large")
    with a:
        with st.container(border=True):
            st.markdown("**Hourly traffic**")
            chart("01_hourly_traffic.png")
    with b:
        with st.container(border=True):
            st.markdown("**Weekday traffic**")
            chart("02_weekday_traffic.png")

    with st.container(border=True):
        st.markdown("**Monthly traffic patterns**")
        chart("07_monthly_traffic.png")

    st.divider()

    # Section 2: Traffic and external factors
    st.markdown(
        '<div class="section-heading">🌦️ Traffic and external factors</div>'
        '<div class="section-description">'
        'Explore traffic distribution and historical associations '
        'with weather and temperature.'
        '</div>',
        unsafe_allow_html=True,
    )

    a, b = st.columns(2, gap="large")
    with a:
        with st.container(border=True):
            st.markdown("**Traffic volume distribution**")
            chart("03_traffic_distribution.png")
    with b:
        with st.container(border=True):
            st.markdown("**Hour and weekday heatmap**")
            chart("04_traffic_heatmap.png")

    a, b = st.columns(2, gap="large")
    with a:
        with st.container(border=True):
            st.markdown("**Weather and traffic**")
            chart("05_weather_traffic.png")
    with b:
        with st.container(border=True):
            st.markdown("**Temperature vs traffic**")
            chart("06_temperature_vs_traffic.png")

    st.divider()

    # Section 3: Model insights
    st.markdown(
        '<div class="section-heading">🧠 Model insights</div>'
        '<div class="section-description">'
        'Examine feature importance and relationships between variables.'
        '</div>',
        unsafe_allow_html=True,
    )

    a, b = st.columns(2, gap="large")
    with a:
        with st.container(border=True):
            st.markdown("**Feature importance**")
            chart("09_feature_importance.png")
    with b:
        with st.container(border=True):
            st.markdown("**Feature correlation heatmap**")
            chart("08_correlation_heatmap.png")

    st.caption(
        "These charts show historical patterns and associations; "
        "they do not establish that one variable causes another."
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

elif page == "Congestion Risk Map":
    st.header("Congestion Risk Forecast Map")
    st.caption(
        "Historical traffic-based risk estimates for the I-94 monitoring "
        "station near Minneapolis–St. Paul. This is not live or citywide "
        "road-level congestion data."
    )

    import pandas as pd
    import streamlit as st

    from pathlib import Path

    project_root = Path(__file__).resolve().parent.parent
    traffic_path = project_root / "data" / "processed" / "metro_traffic_cleaned.csv"
    forecast_path = project_root / "outputs" / "traffic_forecast_predictions.csv"

    if not traffic_path.exists() or not forecast_path.exists():
        st.error(
            "Required traffic data was not found. Check that the cleaned "
            "dataset and forecast predictions exist in the project folders."
        )
    else:
        traffic = pd.read_csv(traffic_path, parse_dates=["date_time"])
        forecasts = pd.read_csv(forecast_path, parse_dates=["date_time"])

        # Use the historical distribution to define transparent thresholds.
        q25, q50, q75, q90 = traffic["traffic_volume"].quantile(
            [0.25, 0.50, 0.75, 0.90]
        ).tolist()

        def classify_risk(value):
            if value <= q25:
                return "Low", "🟢"
            elif value <= q50:
                return "Moderate", "🟡"
            elif value <= q75:
                return "High", "🟠"
            return "Critical", "🔴"

        st.subheader("Risk categories")
        legend_cols = st.columns(4)
        categories = [
            ("🟢 Low", f"Up to {q25:,.0f} vehicles/hour"),
            ("🟡 Moderate", f"{q25:,.0f}–{q50:,.0f}"),
            ("🟠 High", f"{q50:,.0f}–{q75:,.0f}"),
            ("🔴 Critical", f"Above {q75:,.0f}"),
        ]

        for col, (label, threshold) in zip(legend_cols, categories):
            col.metric(label, threshold)

        st.caption(
            "Thresholds are based on the 25th, 50th, and 75th percentiles "
            "of historical traffic volume. These are relative traffic-volume "
            "categories, not official congestion or safety classifications."
        )

        st.divider()
        st.subheader("Explore a historical forecast")

        forecasts = forecasts.sort_values("date_time").dropna(
            subset=["date_time", "actual_traffic", "predicted_traffic"]
        )

        if forecasts.empty:
            st.warning("No valid forecast records are available.")
        else:
            selected_date = st.selectbox(
                "Select a date",
                options=sorted(forecasts["date_time"].dt.date.unique()),
                format_func=lambda d: d.strftime("%d %b %Y"),
            )

            day_data = forecasts[
                forecasts["date_time"].dt.date == selected_date
            ].copy()

            selected_time = st.selectbox(
                "Select an hour",
                options=day_data["date_time"].tolist(),
                format_func=lambda t: t.strftime("%H:%M"),
            )

            record = day_data.loc[
                day_data["date_time"] == selected_time
            ].iloc[0]

            actual = float(record["actual_traffic"])
            predicted = float(record["predicted_traffic"])
            risk, emoji = classify_risk(predicted)

            c1, c2, c3 = st.columns(3)
            c1.metric("Predicted traffic", f"{predicted:,.0f} vehicles/hour")
            c2.metric("Actual traffic", f"{actual:,.0f} vehicles/hour")
            c3.metric("Estimated risk", f"{emoji} {risk}")

            st.info(
                f"For {selected_time:%d %b %Y, %H:%M}, the model predicted "
                f"approximately {predicted:,.0f} vehicles/hour. This falls "
                f"within the **{risk.lower()} relative traffic-volume category** "
                f"under the thresholds derived from the historical dataset."
            )

            st.subheader("Traffic monitoring station")

                
            st.warning(
    "Exact monitoring station coordinates have not been verified. "
    "A geographically precise map is therefore not displayed."
)

            st.markdown("### 📍 Monitoring Station Information")

            col1, col2 = st.columns(2)

            with col1:
                   st.metric("Road", "Westbound I-94")

            with col2:
                   st.metric("Monitoring Station", "MnDOT ATR 301")

            st.info(
                   f"The model predicts **{predicted:,.0f} vehicles per hour**, "
                   f"classified as **{risk} risk** using historical traffic-volume "
                   "percentiles. This is a station-level estimate, not a live "
                  "or citywide congestion measurement."
            )
 

            st.subheader("Actual vs predicted traffic throughout the day")
            chart_data = day_data.set_index("date_time")[
                ["actual_traffic", "predicted_traffic"]
            ]
            st.line_chart(chart_data)

            st.caption(
                "These are historical test-set predictions. Selecting a date "
                "does not generate a forecast for a new future date."
            )

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
