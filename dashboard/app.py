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
/* ===== URBAN PULSE: GLOBAL THEME ===== */
:root {
    --up-bg: #0b1120;
    --up-sidebar: #101a2d;
    --up-panel: #151f33;
    --up-panel-hover: #1b2940;
    --up-border: #293750;
    --up-text: #edf2f7;
    --up-muted: #a5b2c7;
    --up-lime: #c5f36b;
    --up-blue: #62a4ff;
    --up-teal: #42d6c2;
}

/* Main application */
.stApp {
    background: var(--up-bg);
    color: var(--up-text);
}

[data-testid="stAppViewContainer"] {
    background: var(--up-bg);
}

[data-testid="stHeader"] {
    background: rgba(11, 17, 32, 0.92);
}

/* Main content spacing */
.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    padding-left: clamp(1.5rem, 4vw, 4rem);
    padding-right: clamp(1.5rem, 4vw, 4rem);
    max-width: 100%;
}

/* Default text */
.stApp p,
.stApp li,
.stApp label,
.stApp .stMarkdown,
.stApp [data-testid="stCaptionContainer"] {
    color: var(--up-text);
}

.stApp h1,
.stApp h2,
.stApp h3,
.stApp h4 {
    color: #f5f8ff;
    letter-spacing: -0.3px;
}

.stApp [data-testid="stCaptionContainer"] {
    color: var(--up-muted);
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: var(--up-sidebar);
    border-right: 1px solid var(--up-border);
}

[data-testid="stSidebar"] > div:first-child {
    background: var(--up-sidebar);
}

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: var(--up-text);
}

[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
    color: var(--up-muted);
}

/* Sidebar navigation */
[data-testid="stSidebar"] [role="radiogroup"] {
    gap: 7px;
}

[data-testid="stSidebar"] [role="radio"] {
    padding: 10px 12px;
    border-radius: 10px;
    border: 1px solid transparent;
}

[data-testid="stSidebar"] [role="radio"]:hover {
    background: var(--up-panel-hover);
}

[data-testid="stSidebar"] [role="radio"][aria-checked="true"] {
    background: #24321f;
    border: 1px solid #617d36;
}

[data-testid="stSidebar"] [role="radio"][aria-checked="true"] p {
    color: var(--up-lime);
    font-weight: 700;
}

/* Hero banner */
.hero {
    background: linear-gradient(120deg, #151f33 0%, #203755 65%, #263e43 100%);
    color: #ffffff !important;
    padding: 28px 30px;
    border: 1px solid #34465d;
    border-left: 5px solid var(--up-lime);
    border-radius: 18px;
    margin-bottom: 26px;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.18);
}

.hero h1 {
    color: #ffffff !important;
    font-size: clamp(2rem, 4vw, 2.8rem);
    font-weight: 800;
    letter-spacing: -1.2px;
    margin-bottom: 8px;
}

.hero p {
    color: #c6d3e4 !important;
    font-size: 1rem;
    margin-bottom: 0;
}

/* Metric cards retain light surfaces for readability */
.metric-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 18px;
    margin: 18px 0 30px;
}

.metric-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 22px;
    min-height: 145px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.14);
    position: relative;
    overflow: hidden;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.metric-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 28px rgba(0, 0, 0, 0.22);
}

.metric-card::before {
    content: "";
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 5px;
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
    color: #526078;
    font-size: 0.88rem;
    font-weight: 650;
    line-height: 1.35;
}

.metric-value {
    color: #172b4d;
    font-size: clamp(1.45rem, 2.2vw, 2rem);
    font-weight: 800;
    line-height: 1.2;
    letter-spacing: -0.7px;
    overflow-wrap: anywhere;
}

.metric-note {
    color: #718096;
    font-size: 0.78rem;
    margin-top: 7px;
}

/* Section headings */
.section-heading {
    color: var(--up-lime);
    font-size: 1.2rem;
    font-weight: 750;
    margin: 12px 0 4px;
}

.section-description {
    color: var(--up-muted);
    font-size: 0.9rem;
    margin-bottom: 16px;
}

/* Chart panels */
.chart-panel {
    background: var(--up-panel);
    border: 1px solid var(--up-border);
    border-radius: 15px;
    padding: 16px 18px 8px;
    margin-bottom: 20px;
    box-shadow: 0 5px 18px rgba(0, 0, 0, 0.12);
}


/* Streamlit chart panels */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(145deg, #151f33, #111b2d);
    border: 1px solid #293750;
    border-radius: 16px;
    padding: 8px 10px;
    box-shadow: 0 5px 18px rgba(0, 0, 0, 0.12);
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: #465b75;
    box-shadow: 0 8px 22px rgba(0, 0, 0, 0.2);
}


/* Metrics and data */
[data-testid="stMetricLabel"],
[data-testid="stMetricValue"],
[data-testid="stMetricDelta"] {
    color: var(--up-text);
}

[data-testid="stDataFrame"],
[data-testid="stTable"] {
    color: var(--up-text);
}

/* Inputs */
.stSelectbox label,
.stTextInput label,
.stNumberInput label,
.stDateInput label {
    color: var(--up-text);
}

[data-baseweb="select"] > div,
[data-baseweb="input"] > div,
[data-baseweb="textarea"] {
    background: var(--up-panel);
    border-color: var(--up-border);
    color: var(--up-text);
}

/* Buttons */
.stButton button,
.stDownloadButton button {
    color: #000000 !important;
    background: var(--up-lime) !important;
    border: 1px solid var(--up-lime);
    border-radius: 10px;
    font-weight: 700;
    padding: 0.55rem 1rem;
    transition: all 0.2s ease;
}

.stButton button p,
.stDownloadButton button p {
    color: #000000 !important;
}

.stButton button:hover,
.stDownloadButton button:hover {
    color: #000000 !important;
    background: #d8ff8c !important;
    border-color: #d8ff8c;
    box-shadow: 0 4px 16px rgba(197, 243, 107, 0.18);
}

/* Links and separators */
.stApp a {
    color: var(--up-lime);
}

.stApp hr {
    border-color: var(--up-border);
}

/* Alerts */
[data-testid="stAlert"] {
    border-radius: 12px;
}

/* Responsive layout */
@media (max-width: 700px) {
    .metric-grid {
        grid-template-columns: 1fr;
    }

    .hero {
        padding: 22px;
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
        st.image(str(path), caption=caption, width="stretch")

        if name == "01_hourly_traffic.png":
          st.info(
            "Key Insight: Average traffic volume peaks around "
            "4 PM (16:00) and is lowest around 3 AM (03:00), "
            "revealing a clear daily traffic pattern."
           )
        elif name == "10_actual_vs_predicted.png":
          st.info(
            "Key Insight: Most predictions cluster near the "
            "ideal diagonal, indicating that predicted traffic "
            "generally aligns well with actual traffic."
           )
    except Exception as exc:
        st.error(f"Could not display {name}: {exc}")


def analytics_insight(name):
    insights = {
        "01_hourly_traffic.png": (
            "Peak-hour insight",
            "Traffic peaks around 4 PM (16:00), while the lowest "
            "average occurs around 3 AM (03:00)."
        ),
        "02_weekday_traffic.png": (
            "Weekly pattern",
            "Weekday traffic is generally higher than weekend traffic. "
            "Friday has the highest average among the weekdays in this dataset."
        ),
        "03_traffic_distribution.png": (
            "Traffic distribution",
            "The distribution helps reveal how frequently different "
            "traffic-volume levels occur, including unusually quiet periods."
        ),
        "04_traffic_heatmap.png": (
            "Peak-period pattern",
            "The hour-and-weekday heatmap helps identify recurring "
            "busy periods that may be hidden in daily averages."
        ),
        "05_weather_traffic.png": (
            "Weather association",
            "Compare traffic levels across weather categories. "
            "These are historical associations, not proof that weather caused a change."
        ),
        "06_temperature_vs_traffic.png": (
            "Temperature relationship",
            "Look for patterns between temperature and traffic volume, "
            "while remembering that time of day and other factors may also matter."
        ),
        "07_monthly_traffic.png": (
            "Monthly variation",
            "Monthly averages help reveal longer-term variation and "
            "potential seasonal patterns in traffic."
        ),
        "08_correlation_heatmap.png": (
            "Feature relationships",
            "Correlation measures linear association between variables; "
            "it does not establish causation."
        ),
        "09_feature_importance.png": (
            "Model drivers",
            "Feature importance indicates which inputs the model relies "
            "on most, but does not prove that they cause traffic changes."
        ),
    }

    if name in insights:
        title, message = insights[name]
        st.markdown(
            f"""
            <div style="
                background:#19283a;
                border-left:3px solid #c5f36b;
                border-radius:9px;
                padding:12px 14px;
                margin:8px 0 14px;
            ">
                <div style="
                    color:#c5f36b;
                    font-size:0.82rem;
                    font-weight:700;
                    margin-bottom:4px;
                ">{title}</div>
                <div style="
                    color:#d4deeb;
                    font-size:0.86rem;
                    line-height:1.5;
                ">{message}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


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
            <div style="
                background:linear-gradient(110deg,#17263d,#1b2c43);
                border:1px solid #344a63;
                border-left:4px solid #62a4ff;
                border-radius:14px;
                padding:18px 20px;
                margin-bottom:12px;
                transition:transform 0.2s ease;">
                <div style="font-size:17px;font-weight:750;color:#82b5ff;">
                    🔵 Shortest Route
                </div>
                <div style="color:#c0ccdc;font-size:14px;margin-top:7px;">
                    Prioritizes the total road distance.
                </div>
                <div style="color:#8295ae;font-size:12px;margin-top:10px;">
                    BEST FOR DISTANCE
                </div>
            </div>

            <div style="
                background:linear-gradient(110deg,#172b31,#1b3438);
                border:1px solid #31534e;
                border-left:4px solid #42d6a0;
                border-radius:14px;
                padding:18px 20px;
                margin-bottom:12px;">
                <div style="font-size:17px;font-weight:750;color:#66e0b5;">
                    🟢 Fastest Route
                </div>
                <div style="color:#c0d8d3;font-size:14px;margin-top:7px;">
                    Prioritizes estimated journey time.
                </div>
                <div style="color:#8cb5ab;font-size:12px;margin-top:10px;">
                    BEST FOR TRAVEL TIME
                </div>
            </div>

            <div style="
                background:linear-gradient(110deg,#28213c,#302644);
                border:1px solid #514269;
                border-left:4px solid #b69aff;
                border-radius:14px;
                padding:18px 20px;">
                <div style="font-size:17px;font-weight:750;color:#c6adff;">
                    🟣 Custom Route
                </div>
                <div style="color:#d1c8df;font-size:14px;margin-top:7px;">
                    Balances route preferences using your chosen priorities.
                </div>
                <div style="color:#b4a3ce;font-size:12px;margin-top:10px;">
                    FLEXIBLE ROUTE PREFERENCE
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
        width="stretch",
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
           analytics_insight("01_hourly_traffic.png")
    with b:
        with st.container(border=True):
            st.markdown("**Weekday traffic**")
            chart("02_weekday_traffic.png")
            analytics_insight("02_weekday_traffic.png")

    with st.container(border=True):
        st.markdown("**Monthly traffic patterns**")
        chart("07_monthly_traffic.png")
        analytics_insight("07_monthly_traffic.png")

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
            analytics_insight("03_traffic_distribution.png")
    with b:
        with st.container(border=True):
            st.markdown("**Hour and weekday heatmap**")
            chart("04_traffic_heatmap.png")
            analytics_insight("04_traffic_heatmap.png")

    a, b = st.columns(2, gap="large")
    with a:
        with st.container(border=True):
            st.markdown("**Weather and traffic**")
            chart("05_weather_traffic.png")
            analytics_insight("05_weather_traffic.png")
    with b:
        with st.container(border=True):
            st.markdown("**Temperature vs traffic**")
            chart("06_temperature_vs_traffic.png")
            analytics_insight("06_temperature_vs_traffic.png")

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
            analytics_insight("09_feature_importance.png")
    with b:
        with st.container(border=True):
            st.markdown("**Feature correlation heatmap**")
            chart("08_correlation_heatmap.png")
            analytics_insight("08_correlation_heatmap.png")

    st.caption(
        "These charts show historical patterns and associations; "
        "they do not establish that one variable causes another."
    )



elif page == "Traffic Forecasting":
    st.markdown(
        """
        <div class="hero">
            <h1>Traffic Forecasting</h1>
            <p>
                Explore predicted traffic, evaluate model behaviour,
                and understand which features influence predictions.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-heading">FORECAST OVERVIEW</div>'
        '<div class="section-description">'
        'Review saved predictions and examine how closely the model '
        'tracks actual traffic patterns.'
        '</div>',
        unsafe_allow_html=True,
    )

    df = read_csv(OUT / "traffic_forecast_predictions.csv")

    if df is not None:
        total_records = len(df)
        avg_predicted = df["predicted_traffic"].mean()
        avg_actual = df["actual_traffic"].mean()

        c1, c2, c3 = st.columns(3, gap="large")

        with c1:
            with st.container(border=True):
                st.metric(
                    "Forecast Records",
                    f"{total_records:,}",
                )
                st.caption("Saved prediction records")

        with c2:
            with st.container(border=True):
                 st.metric(
                     "Average Predicted Traffic",
                     f"{avg_predicted:,.0f}",
                  )
            st.caption("Mean predicted traffic volume")

        with c3:
            with st.container(border=True):
                 st.metric(
                    "Average Actual Traffic",
                    f"{avg_actual:,.0f}",
                )
            st.caption("Mean observed traffic volume")

        st.dataframe(df.head(100), width="stretch")

        st.download_button(
            "Download predictions",
            df.to_csv(index=False).encode("utf-8"),
            "traffic_forecast_predictions.csv",
            "text/csv",
        )
    else:
        st.warning("Forecast predictions CSV was not found.")


    st.markdown(
        '<div class="section-heading">FORECAST PERFORMANCE</div>'
        '<div class="section-description">'
        'Compare predicted and observed traffic, then explore where '
        'prediction errors are more common.'
        '</div>',
        unsafe_allow_html=True,
    )

    # Actual versus predicted traffic
    with st.container(border=True):
        st.markdown("**Actual vs Predicted Traffic**")
        st.caption(
            "Compare the model's estimates with observed traffic. "
            "Closer agreement indicates better predictions."
        )
        chart("10_actual_vs_predicted.png")

    # Forecast timeline
    with st.container(border=True):
        st.markdown("**Traffic Forecast Timeline**")
        st.caption(
            "Follow predicted and observed traffic over time to see "
            "how well the model tracks changing traffic patterns."
        )
        chart("11_traffic_forecast_timeline.png")

    # Prediction errors
    st.markdown("### Understanding prediction errors")

    c1, c2 = st.columns(2, gap="large")

    with c1:
        with st.container(border=True):
            st.markdown("**Prediction Error Distribution**")
            st.caption(
                "Shows how prediction errors are distributed. "
                "Errors closer to zero generally indicate better estimates."
            )
            chart("12_prediction_error_distribution.png")

    with c2:
        with st.container(border=True):
            st.markdown("**Prediction Error by Hour**")
            st.caption(
                "Compare errors across hours to identify when the "
                "model's predictions tend to be less accurate."
            )
            chart("13_error_by_hour.png")

    with st.container(border=True):
        st.markdown("**Prediction Error by Weekday**")
        st.caption(
            "Compare model errors across weekdays to identify "
            "differences in prediction performance."
        )
        chart("14_error_by_weekday.png")


    st.divider()
    st.subheader("Why did the model make this prediction?")
    st.caption(
        "SHAP explains how the model's input features contribute to "
        "its predictions. These explanations describe model behaviour, "
        "not cause-and-effect relationships."
    )

    # Global feature importance
    shap_importance = read_csv(OUT / "shap_global_importance.csv")

    if shap_importance is not None and not shap_importance.empty:
        st.markdown("### What influences traffic predictions most?")
        st.caption(
            "Features with larger mean absolute SHAP values have a "
            "greater influence on the model's predictions overall. "
            "This measures influence, not whether traffic increases or decreases."
        )

        top_features = shap_importance.head(10).sort_values(
            "Mean Absolute SHAP", ascending=True
        )

        with st.container(border=True):
            st.markdown("**Top 10 influential features**")
            st.bar_chart(
               top_features.set_index("Feature")["Mean Absolute SHAP"],
               horizontal=True,
            )

        with st.expander("View all SHAP feature importance values"):
            st.dataframe(
               shap_importance,
               width="stretch",
               hide_index=True,
            )
    else:
       st.info("SHAP global importance data was not found.")


    # Individual prediction explanations
    shap_details = read_csv(
        OUT / "shap_prediction_explanations.csv"
    )

    if shap_details is not None and not shap_details.empty:
        st.markdown("### Why did this prediction happen?")
        st.caption(
            "Each bar shows how a feature moves the prediction away "
            "from the model's baseline. Positive values push the "
            "prediction higher; negative values push it lower."
        )

        shap_details["date_time"] = pd.to_datetime(
            shap_details["date_time"], errors="coerce"
        )
        shap_details = shap_details.dropna(
            subset=["date_time"]
        ).sort_values("date_time")

        shap_columns = [
            column for column in shap_details.columns
            if column.startswith("shap__")
        ]

        if shap_columns and not shap_details.empty:
            selected_time = st.selectbox(
                "Select a historical test record",
                shap_details["date_time"].dt.strftime(
                    "%Y-%m-%d %H:%M"
                ).tolist(),
                key="shap_prediction_time",
            )

            selected_record = shap_details.loc[
                shap_details["date_time"].dt.strftime(
                    "%Y-%m-%d %H:%M"
                ) == selected_time
            ].iloc[0]

            col1, col2, col3 = st.columns(3, gap="large")

            with col1:
               with st.container(border=True):
                st.metric(
                    "Actual Traffic",
                    f"{selected_record['actual_traffic']:,.0f}",
                )
                st.caption("Observed traffic volume")

            with col2:
              with st.container(border=True):
                st.metric(
                    "Predicted Traffic",
                    f"{selected_record['predicted_traffic']:,.0f}",
                )
                st.caption("Model-estimated traffic volume")

            with col3:
               with st.container(border=True):
                 st.metric(
                    "Model Baseline",
                    f"{selected_record['expected_traffic']:,.0f}",
                 )
                 st.caption("Expected prediction before feature contributions")


            # Build the local contribution chart.
            contributions = pd.DataFrame({
                "Feature": [
                    column.replace("shap__", "")
                    for column in shap_columns
                ],
                "SHAP contribution": [
                    float(selected_record[column])
                    for column in shap_columns
                ],
            })

            contributions["Absolute contribution"] = (
                contributions["SHAP contribution"].abs()
            )
            contributions = contributions.nlargest(
                12, "Absolute contribution"
            ).sort_values("SHAP contribution")

            with st.container(border=True):
               st.markdown("**Feature Contributions**")
               st.caption(
                 "Each bar shows how a feature shifts this prediction "
                 "relative to the model baseline. Positive values push "
                 "the prediction higher; negative values push it lower. "
                 "Larger absolute values indicate stronger contributions."
                )

            st.bar_chart(
                 contributions.set_index("Feature")[
                     "SHAP contribution"
                 ],
                horizontal=True,
                )


            positive = contributions[
                contributions["SHAP contribution"] > 0
            ].sort_values("SHAP contribution", ascending=False)

            negative = contributions[
                contributions["SHAP contribution"] < 0
            ].sort_values("SHAP contribution")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Pushing traffic higher**")
                if not positive.empty:
                    for _, item in positive.head(3).iterrows():
                        st.write(
                            f"↑ {item['Feature']}: "
                            f"+{item['SHAP contribution']:,.2f}"
                        )
                else:
                    st.write("No positive contributions among the top features.")

            with col2:
                st.markdown("**Pushing traffic lower**")
                if not negative.empty:
                    for _, item in negative.head(3).iterrows():
                        st.write(
                            f"↓ {item['Feature']}: "
                            f"{item['SHAP contribution']:,.2f}"
                        )
                else:
                    st.write("No negative contributions among the top features.")

            st.caption(
                "The baseline is the model's expected prediction. "
                "The sum of all SHAP contributions plus the baseline "
                "approximately reconstructs the model prediction; "
                "rounding may cause small differences."
            )
        else:
            st.warning(
                "No individual SHAP contribution columns were found. "
                "Run src/traffic_explainability.py again."
            )
    else:
        st.info("Individual SHAP explanations were not found.")



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
    st.markdown(
        "Compare traffic prediction models using the same chronological "
        "test period and the same test timestamps."
    )

    # Fair comparison: all models evaluated on common test timestamps
    fair_df = read_csv(OUT / "fair_model_comparison.csv")

    if fair_df is not None and not fair_df.empty:
        st.subheader("Fair Model Comparison")

        st.caption(
            "The comparison uses a chronological train-test split. "
            "Results represent rolling one-step-ahead predictions using "
            "historical traffic lags and observed weather at the target "
            "timestamp; they are not multi-hour forecasts generated "
            "entirely in advance."
        )

        st.dataframe(fair_df, width="stretch")

        # Identify metric columns without assuming their capitalization.
        column_lookup = {
            str(column).strip().lower().replace(" ", "_"): column
            for column in fair_df.columns
        }

        model_col = next(
            (
                column_lookup[name]
                for name in ["model", "model_name", "approach"]
                if name in column_lookup
            ),
            None,
        )

        mae_col = next(
            (
                column_lookup[name]
                for name in ["mae", "mean_absolute_error"]
                if name in column_lookup
            ),
            None,
        )

        rmse_col = next(
            (
                column_lookup[name]
                for name in ["rmse", "root_mean_squared_error"]
                if name in column_lookup
            ),
            None,
        )

        r2_col = next(
            (
                column_lookup[name]
                for name in ["r2", "r_squared", "r2_score"]
                if name in column_lookup
            ),
            None,
        )

        test_rows_col = next(
            (
                column_lookup[name]
                for name in ["test_rows", "testing_rows", "n_test"]
                if name in column_lookup
            ),
            None,
        )

        if mae_col and rmse_col and r2_col:
            metrics_df = fair_df.copy()

            for column in [mae_col, rmse_col, r2_col]:
                metrics_df[column] = pd.to_numeric(
                    metrics_df[column], errors="coerce"
                )

            valid_metrics = metrics_df.dropna(
                subset=[mae_col, rmse_col, r2_col]
            )

            if not valid_metrics.empty:
                best_index = valid_metrics[mae_col].idxmin()
                best_model = (
                    str(valid_metrics.loc[best_index, model_col])
                    if model_col
                    else "Lowest-MAE model"
                )

                best = valid_metrics.loc[best_index]

                st.subheader("Best-performing model")

                c1, c2, c3 = st.columns(3, gap="large")

                with c1:
                  with st.container(border=True):
                     st.metric("Best Model", best_model)
                     st.caption("Lowest mean absolute error")

                with c2:
                  with st.container(border=True):
                    st.metric("MAE", f"{best[mae_col]:,.2f}")
                    st.caption("Lower is generally better")

                with c3:
                  with st.container(border=True):
                     st.metric("RMSE", f"{best[rmse_col]:,.2f}")
                     st.caption("Penalizes larger errors more strongly")

                with st.container(border=True):
                 st.metric("R² Score", f"{best[r2_col]:.4f}")
                 st.caption(
                    "Measures how well the model explains variation in traffic. "
                    "Higher values are generally better."
                 )

                st.subheader("Metric comparison")
                st.caption(
                    "Compare all models evaluated on the same test timestamps. "
                    "Lower MAE and RMSE indicate smaller prediction errors."
                )

                chart_df = (
                  valid_metrics.set_index(model_col)[[mae_col, rmse_col]]
                  if model_col
                  else valid_metrics[[mae_col, rmse_col]]
                )

                r2_chart_df = (
                  valid_metrics.set_index(model_col)[[r2_col]]
                  if model_col
                  else valid_metrics[[r2_col]]
                )


                with st.container(border=True):
                   st.markdown("**MAE and RMSE by model**")
                   st.bar_chart(chart_df)

                with st.container(border=True):
                  st.markdown("**R² score by model**")
                  st.caption(
                   "R² measures how well predictions explain variation in traffic. "
                   "Higher values generally indicate a better fit; negative values "
                   "can occur when a model performs worse than predicting the mean."
                  )
                  st.bar_chart(r2_chart_df)

                if test_rows_col:
                    st.caption(
                        "Test rows per model: "
                        + ", ".join(
                            f"{row[model_col] if model_col else index}: "
                            f"{int(row[test_rows_col]):,}"
                            for index, row in valid_metrics.iterrows()
                        )
                    )
        else:
            st.info(
                "The comparison file was loaded, but its metric column "
                "names could not be identified automatically."
            )

        st.download_button(
            "Download fair comparison CSV",
            fair_df.to_csv(index=False).encode("utf-8"),
            "fair_model_comparison.csv",
            "text/csv",
        )

    else:
        st.warning(
            "Fair comparison results were not found. Run "
            "`python src\\compare_models_fair.py` in PowerShell first."
        )



        st.divider()

        st.markdown(
            '<div class="section-heading">ADDITIONAL MODEL INSIGHTS</div>'
            '<div class="section-description">'
            'Explore the original model results and the features used to '
            'understand traffic predictions.'
            '</div>',
            unsafe_allow_html=True,
        )

        for filename, title in [
            ("model_comparison.csv", "Original Model Comparison"),
            ("feature_importance.csv", "Feature Importance"),
        ]:
            df = read_csv(OUT / filename)

            with st.container(border=True):
                st.markdown(f"**{title}**")

                if filename == "model_comparison.csv":
                    st.caption(
                        "Review the previously generated model comparison results."
                    )
                else:
                    st.caption(
                        "Inspect the saved feature-importance values to see "
                        "which inputs contribute most to the model."
                    )

                if df is not None:
                    st.dataframe(
                        df,
                        width="stretch",
                        hide_index=True,
                    )
                else:
                    st.warning(f"Missing file: {filename}")

        chart("10_actual_vs_predicted.png", "Actual vs predicted")
        chart(
            "12_prediction_error_distribution.png",
            "Prediction error distribution",
        )



elif page == "Data Explorer":
    st.markdown(
        """
        <div class="hero">
            <h1>Data Explorer</h1>
            <p>
                Browse, inspect, and download the datasets that power
                Urban Pulse's traffic analysis and prediction workflows.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-heading">DATA WORKSPACE</div>'
        '<div class="section-description">'
        'Choose a dataset to inspect its structure and preview its records.'
        '</div>',
        unsafe_allow_html=True,
    )

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
        # Dataset summary cards
        col1, col2 = st.columns(2, gap="large")

        with col1:
            with st.container(border=True):
                st.metric("Total Records", f"{len(df):,}")
                st.caption("Number of rows in the selected dataset")

        with col2:
            with st.container(border=True):
                st.metric("Total Columns", f"{len(df.columns):,}")
                st.caption("Number of variables available")

        # Dataset preview
        st.markdown(
            '<div class="section-heading">DATASET PREVIEW</div>'
            '<div class="section-description">'
            'Inspect the first 2,000 records from the selected dataset.'
            '</div>',
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            st.dataframe(
                df.head(2000),
                width="stretch",
                hide_index=True,
            )

        # Download button
        st.download_button(
            "Download CSV",
            df.to_csv(index=False).encode("utf-8"),
            path.name,
            "text/csv",
        )

    else:
        st.warning(f"File not found: {path}")
