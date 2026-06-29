import streamlit as st
from streamlit_folium import st_folium
import hackathon

# -----------------------------
# Page configuration (FIRST)
# -----------------------------
st.set_page_config(
    page_title="Climate Dashboard",
    page_icon="🌍",
    layout="wide"
)

st.title("🌍 Climate & Air Quality Monitoring Dashboard")

# -----------------------------
# Sidebar (SECOND)
# -----------------------------
st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Choose Page",
    [
        "Dashboard",
        "AQI Map",
        "Alerts",
        "Dataset"
    ]
)

# -----------------------------
# Cached functions
# -----------------------------
@st.cache_data
def load_data():
    return hackathon.task1()

# Load data first
df = load_data()

# Create map only once
if "aqi_map" not in st.session_state:
    st.session_state.aqi_map = hackathon.task4(df)


# Load data once
df = load_data()
st.success("ETL Completed Successfully!")

# -----------------------------
# Pages
# -----------------------------
if page == "Dataset":

    st.subheader("Cleaned Dataset")
    st.dataframe(df)

elif page == "Dashboard":

    hackathon.task3(df)

    st.image(
        "climate_dashboard.png",
        use_container_width=True
    )

elif page == "AQI Map":

    st.subheader("AQI Risk Map")

    st_folium(
        st.session_state.aqi_map,
        width=1000,
        height=600,
        returned_objects=[]
    )

elif page == "Alerts":

    alerts_df, critical_df = hackathon.task2(df)

    # ----------------------------
    # Summary Cards
    # ----------------------------

    col1, col2 = st.columns(2)

    col1.metric(
        "🚨 Critical Alerts",
        len(alerts_df)
    )

    col2.metric(
        "⚠️ Critical Cities",
        len(critical_df)
    )

    st.divider()

    # ----------------------------
    # Top Alerts Table
    # ----------------------------

    st.subheader("🚨 Top 10 Critical Pollution Alerts")

    st.dataframe(
        alerts_df,
        use_container_width=True
    )

    st.divider()

    # ----------------------------
    # Critical Cities Table
    # ----------------------------

    st.subheader("⚠️ Cities with 3-Hour Critical Windows")

    st.dataframe(
        critical_df,
        use_container_width=True
    )