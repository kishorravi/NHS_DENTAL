import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="NHS Dental Contracts Dashboard", layout="wide")

st.title("NHS Dental Contracts Monthly Dashboard")
st.caption("Dynamic analysis interface for NHS-style contract data")

# Data loading & caching
@st.cache_data
def load_data(path):
    df = pd.read_csv(path)
    df['YEARMONTHSTR'] = df['YEARMONTH'].astype(str)
    df['YEARMONTHDATE'] = pd.to_datetime(df['YEARMONTHSTR'] + "-01", format="%Y-%m-%d")
    numeric_cols = [
        "TOTALFINVALUE", "CONTRACTEDUDA", "CONTRACTEDUOA", "GENERALDENTFINVALUE", "ORTHOFINVALUE"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

DEFAULT_PATH = "contractannual202506.csv"
uploaded = st.sidebar.file_uploader("Upload NHS Dental Contract CSV", type="csv")
if uploaded is not None:
    df = load_data(uploaded)
else:
    st.sidebar.info("Using default local file.")
    df = load_data(DEFAULT_PATH)

# Sidebar: Interactive Filters
commissioners = sorted(df["COMMISSIONERNAME"].dropna().unique())
selected_comm = st.sidebar.multiselect("Commissioner ICB", options=commissioners, default=commissioners)
if "PRISONIND" in df.columns:
    prison_vals = sorted(df["PRISONIND"].dropna().unique())
    selected_prison = st.sidebar.multiselect("Prison Indicator", options=prison_vals, default=prison_vals)
else:
    selected_prison = None

if "TOTALFINVALUE" in df.columns:
    min_value = float(df["TOTALFINVALUE"].min())
    max_value = float(df["TOTALFINVALUE"].max())
    value_range = st.sidebar.slider(
        "Total Financial Value", min_value, max_value, (min_value, max_value), step=1000.0
    )
else:
    value_range = None

df_filtered = df.copy()
if selected_comm:
    df_filtered = df_filtered[df_filtered["COMMISSIONERNAME"].isin(selected_comm)]
if selected_prison is not None:
    df_filtered = df_filtered[df_filtered["PRISONIND"].isin(selected_prison)]
if value_range and "TOTALFINVALUE" in df_filtered.columns:
    low, high = value_range
    df_filtered = df_filtered[
        (df_filtered["TOTALFINVALUE"] >= low) & (df_filtered["TOTALFINVALUE"] <= high)
    ]

st.write(f"Showing {len(df_filtered):,} contracts after filtering.")

# Top Metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Contracts", f"{len(df_filtered):,}")
col2.metric(
    "Total Contract Value",
    f"{df_filtered['TOTALFINVALUE'].sum():,.0f}" if "TOTALFINVALUE" in df_filtered.columns else "NA"
)
col3.metric(
    "Total Contracted UDA",
    f"{df_filtered['CONTRACTEDUDA'].sum():,.0f}" if "CONTRACTEDUDA" in df_filtered.columns else "NA"
)
col4.metric(
    "Total Contracted UOA",
    f"{df_filtered['CONTRACTEDUOA'].sum():,.0f}" if "CONTRACTEDUOA" in df_filtered.columns else "NA"
)

st.markdown("---")

# Dynamic Visualizations: Chart Tabs
st.subheader("Visualisations")

tab1, tab2, tab3, tab4 = st.tabs([
    "Total Contract Value by Commissioner",
    "UDA/UOA by Commissioner",
    "Top Providers by Value",
    "Custom Chart"
])

with tab1:
    if "TOTALFINVALUE" in df_filtered.columns:
        df_comm = (
            df_filtered.groupby("COMMISSIONERNAME")["TOTALFINVALUE"]
            .sum()
            .reset_index()
            .sort_values("TOTALFINVALUE", ascending=False)
        )
        fig_val = px.bar(
            df_comm, x="COMMISSIONERNAME", y="TOTALFINVALUE",
            title="Total Contract Value by Commissioner"
        )
        fig_val.update_layout(xaxis_title="Commissioner", yaxis_title="Total Value", xaxis_tickangle=-45)
        st.plotly_chart(fig_val, use_container_width=True)
    else:
        st.info("TOTALFINVALUE not available.")

with tab2:
    metric = st.selectbox("Select UDA/UOA Metric", ["CONTRACTEDUDA", "CONTRACTEDUOA"])
    if metric in df_filtered.columns:
        df_comm = (
            df_filtered.groupby("COMMISSIONERNAME")[metric]
            .sum()
            .reset_index()
            .sort_values(metric, ascending=False)
        )
        fig_uda = px.bar(
            df_comm, x="COMMISSIONERNAME", y=metric,
            title=f"{metric} by Commissioner"
        )
        fig_uda.update_layout(xaxis_title="Commissioner", yaxis_title=metric, xaxis_tickangle=-45)
        st.plotly_chart(fig_uda, use_container_width=True)
    else:
        st.info(f"{metric} not available.")

with tab3:
    if "TOTALFINVALUE" in df_filtered.columns and "PROVIDERNAME" in df_filtered.columns:
        df_prov = (
            df_filtered.groupby("PROVIDERNAME")["TOTALFINVALUE"]
            .sum()
            .reset_index()
            .sort_values("TOTALFINVALUE", ascending=False)
            .head(20)
        )
        st.write("Top 20 Providers by Total Contract Value")
        st.dataframe(df_prov, use_container_width=True)
        fig_prov = px.bar(
            df_prov, x="PROVIDERNAME", y="TOTALFINVALUE",
            title="Top 20 Providers by Contract Value"
        )
        fig_prov.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_prov, use_container_width=True)
    else:
        st.info("Cannot display provider ranking.")

with tab4:
    # Custom dynamic chart based on user selection
    group_col = st.selectbox(
        "Group By", options=[col for col in df_filtered.columns if df_filtered[col].dtype == 'O']
    )
    value_col = st.selectbox(
        "Value Metric", options=[col for col in df_filtered.columns if df_filtered[col].dtype != 'O']
    )
    chart_type = st.radio("Chart Type", ("Bar", "Line", "Scatter"))
    chart_df = (
        df_filtered.groupby(group_col)[value_col].sum()
        .reset_index()
        .sort_values(value_col, ascending=False)
    )
    if chart_type == "Bar":
        fig_custom = px.bar(chart_df, x=group_col, y=value_col, title=f"{value_col} by {group_col}")
    elif chart_type == "Line":
        fig_custom = px.line(chart_df, x=group_col, y=value_col, title=f"{value_col} by {group_col}")
    else:
        fig_custom = px.scatter(chart_df, x=group_col, y=value_col, title=f"{value_col} by {group_col}")
    st.plotly_chart(fig_custom, use_container_width=True)

# Expander: Raw Data View
with st.expander("View raw filtered data"):
    st.dataframe(df_filtered, use_container_width=True)
