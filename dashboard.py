# =============================================================================
# dashboard.py  —  RAPA Engine Local Visualization Dashboard
# =============================================================================
#
# Run:
#   $env:PYTHONUTF8 = "1"
#   streamlit run dashboard.py
#
# Opens automatically at http://localhost:8501
# =============================================================================

import os
import sqlite3
from datetime import datetime, timezone

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Page configuration  (must be the FIRST streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="RAPA Engine — Flight Analytics",
    page_icon="airplane",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flight_quotes.db")

LEAD_TIME_BUCKETS = {
    "1_day":   (0,  2),
    "7_days":  (2,  10),
    "30_days": (10, 45),
    "60_days": (45, 999),
}
BUCKET_LABELS = {
    "1_day":   "Last Minute\n(0-2 days)",
    "7_days":  "Short Lead\n(2-10 days)",
    "30_days": "Medium Lead\n(10-45 days)",
    "60_days": "Advance\n(45+ days)",
}

# ---------------------------------------------------------------------------
# Custom CSS — premium dark theme
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* Dark background */
    .stApp { background-color: #0f1117; }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1d2e 0%, #161827 100%);
        border-right: 1px solid #2d3561;
    }

    /* Metric cards */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #1e2140 0%, #252847 100%);
        border: 1px solid #3d4278;
        border-radius: 12px;
        padding: 16px;
    }
    div[data-testid="metric-container"] label { color: #8892b0 !important; }
    div[data-testid="metric-container"] div[data-testid="metric-value"] {
        color: #64ffda !important; font-size: 1.8rem !important;
    }

    /* Headers */
    h1 { color: #ccd6f6 !important; }
    h2 { color: #8892b0 !important; border-bottom: 1px solid #2d3561; padding-bottom: 8px; }
    h3 { color: #64ffda !important; }

    /* Streamlit default text */
    .stMarkdown p { color: #a8b2d8; }

    /* Section dividers */
    hr { border-color: #2d3561; }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# Data Loading (cached so it only re-reads DB when the file changes)
# =============================================================================

@st.cache_data(ttl=30)  # refresh every 30 seconds
def load_data() -> pd.DataFrame:
    """Load flight_quotes table into a DataFrame with computed columns."""
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM flight_quotes", conn)
    conn.close()

    # Computed columns
    df["route"] = df["origin_sector"] + " -> " + df["destination_sector"]
    df["departure_dt"] = pd.to_datetime(df["departure_timestamp"], errors="coerce")
    today = datetime.now(timezone.utc).replace(tzinfo=None)
    df["days_to_departure"] = (df["departure_dt"] - today).dt.days
    df["is_math_valid"] = df["is_math_valid"].astype(bool)
    df["is_price_outlier"] = df["is_price_outlier"].astype(bool)

    return df


# =============================================================================
# Header
# =============================================================================

st.markdown("""
<h1 style="text-align:center; font-size:2.5rem; margin-bottom:0;">
    RAPA Engine
</h1>
<p style="text-align:center; color:#64ffda; font-size:1.1rem; margin-top:4px;">
    Flight Quote Analytics Dashboard — Powered by Gemini 3.6 Flash
</p>
<hr>
""", unsafe_allow_html=True)


# =============================================================================
# Load data
# =============================================================================

df_full = load_data()

if df_full.empty:
    st.error(
        "**Database not found or empty.**\n\n"
        "Please run the pipeline first:\n"
        "```powershell\n"
        "python db_setup.py\n"
        "python processor.py\n"
        "```"
    )
    st.stop()


# =============================================================================
# Sidebar — Filters
# =============================================================================

st.sidebar.markdown("## Filters")

# Airline filter
all_airlines = sorted(df_full["airline"].unique().tolist())
selected_airlines = st.sidebar.multiselect(
    "Airlines", options=all_airlines, default=all_airlines
)

# Route filter
all_routes = sorted(df_full["route"].unique().tolist())
selected_routes = st.sidebar.multiselect(
    "Routes", options=all_routes, default=all_routes
)

# Seat status filter
all_statuses = sorted(df_full["seat_status"].unique().tolist())
selected_statuses = st.sidebar.multiselect(
    "Seat Status", options=all_statuses, default=all_statuses
)

# Fare range slider
fare_min = float(df_full["total_fare"].min())
fare_max = float(df_full["total_fare"].max())
fare_range = st.sidebar.slider(
    "Total Fare Range (INR)",
    min_value=fare_min,
    max_value=fare_max,
    value=(fare_min, fare_max),
    step=100.0,
)

# Outlier toggle
exclude_outliers = st.sidebar.checkbox("Exclude Price Outliers", value=True)

st.sidebar.divider()
st.sidebar.markdown(
    f"**Database:** `flight_quotes.db`  \n"
    f"**Total records:** {len(df_full)}  \n"
    f"**Last refreshed:** {datetime.now().strftime('%H:%M:%S')}"
)


# =============================================================================
# Apply filters
# =============================================================================

df = df_full.copy()
if selected_airlines:
    df = df[df["airline"].isin(selected_airlines)]
if selected_routes:
    df = df[df["route"].isin(selected_routes)]
if selected_statuses:
    df = df[df["seat_status"].isin(selected_statuses)]
df = df[df["total_fare"].between(fare_range[0], fare_range[1])]
if exclude_outliers:
    df = df[~df["is_price_outlier"]]


# =============================================================================
# KPI Metric Cards
# =============================================================================

st.markdown("## Key Metrics")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Total Quotes", len(df))
with col2:
    st.metric("Avg Fare", f"Rs.{df['total_fare'].mean():,.0f}" if not df.empty else "N/A")
with col3:
    st.metric("Min Fare", f"Rs.{df['total_fare'].min():,.0f}" if not df.empty else "N/A")
with col4:
    st.metric("Max Fare", f"Rs.{df['total_fare'].max():,.0f}" if not df.empty else "N/A")
with col5:
    math_pct = df["is_math_valid"].sum() / len(df) * 100 if not df.empty else 0
    st.metric("Math Valid", f"{math_pct:.0f}%")

@st.cache_data(ttl=30)
def load_index_series(frequency: str = "daily") -> pd.DataFrame:
    """Load index_values table for given frequency, auto-aggregating if not computed."""
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    try:
        query = "SELECT calculation_date, jevons_index, naive_index, inflation_mom FROM index_values WHERE LOWER(frequency) = ? ORDER BY calculation_date ASC"
        idf = pd.read_sql_query(query, conn, params=(frequency.lower(),))
        if idf.empty and frequency.lower() in ("weekly", "monthly"):
            from index.calculator import recompute_all_frequencies
            recompute_all_frequencies(DB_PATH)
            idf = pd.read_sql_query(query, conn, params=(frequency.lower(),))
        return idf
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()


# =============================================================================
# CHART 0: Airfare Price Index (APIx) Trends & Frequency Aggregation
# =============================================================================

st.markdown("## Airfare Price Index (APIx) Trends")
st.caption(
    "Matched-model Jevons index across time. Choose aggregation frequency to inspect "
    "high-frequency daily signals or smoothed weekly / monthly series for NSO & RBI macro integration."
)

freq_col, _ = st.columns([2, 3])
with freq_col:
    freq_choice = st.radio(
        "Index Frequency:",
        ["Daily", "Weekly", "Monthly"],
        horizontal=True,
        index=0,
        key="index_freq_toggle"
    )

idf = load_index_series(freq_choice.lower())
if not idf.empty:
    fig_index = px.line(
        idf,
        x="calculation_date",
        y="jevons_index",
        markers=True,
        title=f"APIx Airfare Price Index ({freq_choice}) — Base: Dec 2025 = 100.0",
        labels={"calculation_date": "Period", "jevons_index": "Jevons Index"}
    )
    fig_index.update_traces(line_color="#64ffda", marker=dict(size=8, color="#64ffda"))
    fig_index.update_layout(
        paper_bgcolor="#0f1117",
        plot_bgcolor="#1a1d2e",
        font_color="#ccd6f6",
        height=360,
        margin={"t": 40, "b": 40, "l": 40, "r": 20},
    )
    st.plotly_chart(fig_index, use_container_width=True)
else:
    st.info(f"No {freq_choice.lower()} index records available yet.")

st.markdown("---")


# =============================================================================
# CHART 1: Sector Pricing Heatmap
# =============================================================================

st.markdown("## Sector-wise Fare Heatmap")
st.caption(
    "Average total fare (INR) for each origin -> destination route. "
    "Darker = more expensive."
)

if df.empty:
    st.warning("No data after applying filters.")
else:
    # Build pivot: rows = origin, cols = destination, values = avg fare
    heatmap_data = (
        df.groupby(["origin_sector", "destination_sector"])["total_fare"]
        .mean()
        .reset_index()
    )
    pivot = heatmap_data.pivot(
        index="origin_sector", columns="destination_sector", values="total_fare"
    )

    fig_heatmap = px.imshow(
        pivot,
        labels={"x": "Destination", "y": "Origin", "color": "Avg Fare (INR)"},
        color_continuous_scale="Blues",
        text_auto=".0f",
        aspect="auto",
    )
    fig_heatmap.update_layout(
        paper_bgcolor="#0f1117",
        plot_bgcolor="#0f1117",
        font_color="#ccd6f6",
        title={
            "text": "Average Fare Heatmap by Sector (INR)",
            "font": {"size": 18, "color": "#64ffda"},
        },
        coloraxis_colorbar={"tickfont": {"color": "#a8b2d8"}},
        height=400,
        margin={"t": 60, "b": 40, "l": 40, "r": 40},
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

st.markdown("---")


# =============================================================================
# CHART 2: Airline Fare Comparison Bar Chart
# =============================================================================

st.markdown("## Airline Fare Breakdown")

col_left, col_right = st.columns(2)

with col_left:
    st.caption("Average fare components per airline (stacked bar)")
    if df.empty:
        st.warning("No data.")
    else:
        airline_breakdown = (
            df.groupby("airline")[["base_fare", "taxes", "user_development_fee", "convenience_charge"]]
            .mean()
            .reset_index()
        )
        fig_bar = px.bar(
            airline_breakdown,
            x="airline",
            y=["base_fare", "taxes", "user_development_fee", "convenience_charge"],
            barmode="stack",
            color_discrete_map={
                "base_fare": "#64ffda",
                "taxes": "#4a9eff",
                "user_development_fee": "#bc6ff1",
                "convenience_charge": "#ff6b6b",
            },
            labels={"value": "Avg Amount (INR)", "airline": "Airline", "variable": "Component"},
        )
        fig_bar.update_layout(
            paper_bgcolor="#0f1117",
            plot_bgcolor="#1a1d2e",
            font_color="#ccd6f6",
            legend={"font": {"color": "#a8b2d8"}},
            height=380,
            margin={"t": 20, "b": 40, "l": 40, "r": 20},
        )
        st.plotly_chart(fig_bar, use_container_width=True)

with col_right:
    st.caption("Seat availability distribution")
    if df_full.empty:
        st.warning("No data.")
    else:
        status_counts = df_full["seat_status"].value_counts().reset_index()
        status_counts.columns = ["Status", "Count"]
        fig_pie = px.pie(
            status_counts,
            names="Status",
            values="Count",
            color="Status",
            color_discrete_map={
                "available": "#64ffda",
                "sold-out": "#ff6b6b",
                "cancelled": "#f0a500",
            },
            hole=0.4,
        )
        fig_pie.update_layout(
            paper_bgcolor="#0f1117",
            font_color="#ccd6f6",
            legend={"font": {"color": "#a8b2d8"}},
            height=380,
            margin={"t": 20, "b": 40, "l": 40, "r": 20},
        )
        st.plotly_chart(fig_pie, use_container_width=True)

st.markdown("---")


# =============================================================================
# CHART 3: Lead-Time Price Elasticity Curve
# =============================================================================

st.markdown("## Lead-Time Price Elasticity")
st.caption(
    "How does fare change depending on how many days before departure you look? "
    "Each dot = average fare for that booking lead-time window."
)

elasticity_rows = []
for bucket_key, (low, high) in LEAD_TIME_BUCKETS.items():
    mask = (df_full["days_to_departure"] >= low) & (df_full["days_to_departure"] < high)
    bucket_df = df_full[mask]
    if not bucket_df.empty:
        elasticity_rows.append({
            "Bucket": BUCKET_LABELS[bucket_key],
            "Avg Fare": round(bucket_df["total_fare"].mean(), 2),
            "Min Fare": round(bucket_df["total_fare"].min(), 2),
            "Max Fare": round(bucket_df["total_fare"].max(), 2),
            "Count": len(bucket_df),
            "Sort": low,
        })

if elasticity_rows:
    elast_df = pd.DataFrame(elasticity_rows).sort_values("Sort")

    fig_elast = go.Figure()

    # Shaded area between min and max
    fig_elast.add_trace(
        go.Scatter(
            x=elast_df["Bucket"].tolist() + elast_df["Bucket"].tolist()[::-1],
            y=elast_df["Max Fare"].tolist() + elast_df["Min Fare"].tolist()[::-1],
            fill="toself",
            fillcolor="rgba(100,255,218,0.08)",
            line={"color": "rgba(0,0,0,0)"},
            name="Fare Range",
            hoverinfo="skip",
        )
    )

    # Average fare line
    fig_elast.add_trace(
        go.Scatter(
            x=elast_df["Bucket"],
            y=elast_df["Avg Fare"],
            mode="lines+markers+text",
            name="Avg Fare",
            line={"color": "#64ffda", "width": 3},
            marker={"size": 12, "color": "#64ffda", "symbol": "circle"},
            text=[f"Rs.{v:,.0f}" for v in elast_df["Avg Fare"]],
            textposition="top center",
            textfont={"color": "#ccd6f6", "size": 13},
        )
    )

    fig_elast.update_layout(
        paper_bgcolor="#0f1117",
        plot_bgcolor="#1a1d2e",
        font_color="#ccd6f6",
        xaxis={"title": "Booking Lead Time", "tickfont": {"color": "#a8b2d8"}},
        yaxis={"title": "Avg Total Fare (INR)", "tickfont": {"color": "#a8b2d8"},
               "tickprefix": "Rs."},
        legend={"font": {"color": "#a8b2d8"}},
        height=420,
        margin={"t": 20, "b": 60, "l": 60, "r": 20},
    )
    st.plotly_chart(fig_elast, use_container_width=True)

    # Elasticity table
    display_df = elast_df[["Bucket", "Count", "Min Fare", "Avg Fare", "Max Fare"]].rename(
        columns={"Min Fare": "Min (INR)", "Avg Fare": "Avg (INR)", "Max Fare": "Max (INR)"}
    )
    st.dataframe(display_df.set_index("Bucket"), use_container_width=True)
else:
    st.info(
        "Not enough departure date data for elasticity analysis. "
        "Add more dumps with varied departure dates and re-run the pipeline."
    )

st.markdown("---")


# =============================================================================
# Raw Data Table
# =============================================================================

st.markdown("## Raw Data Explorer")

show_cols = [
    "flight_number", "airline", "route", "departure_timestamp",
    "base_fare", "taxes", "user_development_fee", "convenience_charge",
    "total_fare", "seat_status", "is_math_valid", "is_price_outlier", "source_file",
]
available_cols = [c for c in show_cols if c in df.columns]

if df.empty:
    st.warning("No records match the current filters.")
else:
    st.dataframe(
        df[available_cols].reset_index(drop=True),
        use_container_width=True,
        height=300,
    )

    # CSV download
    csv = df[available_cols].to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download filtered data as CSV",
        data=csv,
        file_name="flight_quotes_filtered.csv",
        mime="text/csv",
    )
