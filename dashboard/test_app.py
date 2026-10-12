
import streamlit as st

st.set_page_config(page_title="Urban Pulse Test", layout="wide")

st.title("🚦 Urban Pulse")
st.subheader("Traffic Intelligence Dashboard")
st.success("The dashboard is rendering correctly!")

col1, col2, col3 = st.columns(3)
col1.metric("Traffic Records", "48,187")
col2.metric("Forecast MAE", "162.90")
col3.metric("Forecast R²", "0.9804")

st.write("If you can see this, Streamlit can render our dashboard components.")
