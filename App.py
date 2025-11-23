import pandas as pd
import streamlit as st
import plotly.express as px

# -------------------------
# Page config
# -------------------------
st.set_page_config(
    page_title="NHS Dental Contracts Dashboard",
    page_icon="🦷",
    layout="wide"
)

st.title("🦷 NHS Dental Contracts – Monthly Contractual Dashboard")
st.caption(
    "English Contractor Monthly General Dental and Orthodontic Contractual Dataset "
    "(example: 202506 extract). Built for NHS-style information analysis."
)

# -------------------------
# Load data
# -------------------------
@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    # Create a proper date from YEAR_MONTH (e.g. 202506 -> 2025-06-01)
    df["YEAR_MONTH_STR"] = df["YEAR_MONTH"].astype(str)
    df["YEAR_MONTH_DATE"] = pd.to_datetime(df["YEAR_MONTH_STR"] + "01", format="%Y%m%d")

    # Ensure key numeric columns are numeric
    numeric_cols = [
        "TOTAL_FIN_VALUE",
        "CONTRACTED_UDA",
        "CONTRACTED_UOA",
        "GENERAL_DENT_FIN_VALUE",
        "ORTHO_FIN_VALUE",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


# Default file path (your local file)
DEFAULT_PATH = "contract_annual_202506.csv"

uploaded = st.sidebar.file_uploader("📁 Upload NHS Dental Contract CSV", type=["csv"])

if uploaded is not None:
    df = load_data(uploaded)
else:
    st.sidebar.info("Using default file: `contract_annual_202506.csv` in this folder.")
    df = load_data(DEFAULT_PATH)

# -------------------------
# Sidebar filters
# -------------------------
st.sidebar.header("🔎 Filters")

# Commissioner filter
commissioners = sorted(df["COMMISSIONER_NAME"].dropna().unique())
selected_commissioners = st.sidebar.multiselect(
    "Commissioner (ICB)",
    options=commissioners,
    default=commissioners,   # all selected by default
)

# Prison / non-prison contracts
if "PRISON_IND" in df.columns:
    prison_values = sorted(df["PRISON_IND"].dropna().unique())
    selected_prison = st.sidebar.multiselect(
        "Prison Indicator",
        options=prison_values,
        default=prison_values,
    )
else:
    selected_prison = None

# Minimum total contract value filter
if "TOTAL_FIN_VALUE" in df.columns:
    min_value = float(df["TOTAL_FIN_VALUE"].min())
    max_value = float(df["TOTAL_FIN_VALUE"].max())
    value_range = st.sidebar.slider(
        "Total Financial Value (£) – contract filter",
        min_value=round(min_value, 0),
        max_value=round(max_value, 0),
        value=(round(min_value, 0), round(max_value, 0)),
        step=1000.0,
    )
else:
    value_range = None

# Apply filters
df_filtered = df.copy()

if selected_commissioners:
    df_filtered = df_filtered[df_filtered["COMMISSIONER_NAME"].isin(selected_commissioners)]

if selected_prison is not None:
    df_filtered = df_filtered[df_filtered["PRISON_IND"].isin(selected_prison)]

if value_range is not None and "TOTAL_FIN_VALUE" in df_filtered.columns:
    low, high = value_range
    df_filtered = df_filtered[
        (df_filtered["TOTAL_FIN_VALUE"] >= low) &
        (df_filtered["TOTAL_FIN_VALUE"] <= high)
    ]

st.write(f"Showing **{len(df_filtered):,}** contracts after filtering.")

# -------------------------
# KPIs
# -------------------------
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Contracts", f"{len(df_filtered):,}")

with col2:
    if "TOTAL_FIN_VALUE" in df_filtered.columns:
        total_value = df_filtered["TOTAL_FIN_VALUE"].sum()
        st.metric("Total Contract Value (£)", f"{total_value:,.0f}")
    else:
        st.metric("Total Contract Value (£)", "N/A")

with col3:
    if "CONTRACTED_UDA" in df_filtered.columns:
        total_uda = df_filtered["CONTRACTED_UDA"].sum()
        st.metric("Total Contracted UDA", f"{total_uda:,.0f}")
    else:
        st.metric("Total Contracted UDA", "N/A")

with col4:
    if "CONTRACTED_UOA" in df_filtered.columns:
        total_uoa = df_filtered["CONTRACTED_UOA"].sum()
        st.metric("Total Contracted UOA", f"{total_uoa:,.0f}")
    else:
        st.metric("Total Contracted UOA", "N/A")

st.markdown("---")

# -------------------------
# Aggregations by Commissioner
# -------------------------
st.subheader("📍 Commissioner-level Summary")

group_cols = ["COMMISSIONER_NAME"]

agg_dict = {}
if "TOTAL_FIN_VALUE" in df_filtered.columns:
    agg_dict["TOTAL_FIN_VALUE"] = "sum"
if "CONTRACTED_UDA" in df_filtered.columns:
    agg_dict["CONTRACTED_UDA"] = "sum"
if "CONTRACTED_UOA" in df_filtered.columns:
    agg_dict["CONTRACTED_UOA"] = "sum"

df_comm = df_filtered.groupby(group_cols).agg(agg_dict).reset_index()

st.dataframe(df_comm.sort_values("TOTAL_FIN_VALUE", ascending=False), use_container_width=True)

# -------------------------
# Charts
# -------------------------
st.subheader("📊 Visualisations")

tab1, tab2, tab3 = st.tabs([
    "💰 Total Contract Value by Commissioner",
    "🦷 UDA / UOA by Commissioner",
    "🏥 Top Providers by Contract Value",
])

# --- Tab 1: Total contract value ---
with tab1:
    if "TOTAL_FIN_VALUE" in df_comm.columns and not df_comm.empty:
        fig_val = px.bar(
            df_comm.sort_values("TOTAL_FIN_VALUE", ascending=False),
            x="COMMISSIONER_NAME",
            y="TOTAL_FIN_VALUE",
            title="Total Contract Value (£) by Commissioner",
        )
        fig_val.update_layout(xaxis_title="Commissioner (ICB)", yaxis_title="Total £", xaxis_tickangle=-45)
        st.plotly_chart(fig_val, use_container_width=True)
    else:
        st.info("TOTAL_FIN_VALUE not available in this extract.")

# --- Tab 2: Contracted UDA / UOA ---
with tab2:
    if ("CONTRACTED_UDA" in df_comm.columns or "CONTRACTED_UOA" in df_comm.columns) and not df_comm.empty:
        df_long = df_comm.melt(
            id_vars="COMMISSIONER_NAME",
            value_vars=[c for c in ["CONTRACTED_UDA", "CONTRACTED_UOA"] if c in df_comm.columns],
            var_name="Measure",
            value_name="Value"
        )
        fig_uda = px.bar(
            df_long.sort_values("Value", ascending=False),
            x="COMMISSIONER_NAME",
            y="Value",
            color="Measure",
            barmode="group",
            title="Contracted UDA / UOA by Commissioner",
        )
        fig_uda.update_layout(xaxis_title="Commissioner (ICB)", xaxis_tickangle=-45)
        st.plotly_chart(fig_uda, use_container_width=True)
    else:
        st.info("No CONTRACTED_UDA / CONTRACTED_UOA columns available.")

# --- Tab 3: Top providers ---
with tab3:
    if "TOTAL_FIN_VALUE" in df_filtered.columns:
        df_prov = (
            df_filtered.groupby("PROVIDER_NAME", as_index=False)["TOTAL_FIN_VALUE"]
            .sum()
            .sort_values("TOTAL_FIN_VALUE", ascending=False)
            .head(20)
        )
        st.write("Top 20 Providers by Total Contract Value")
        st.dataframe(df_prov, use_container_width=True)

        fig_prov = px.bar(
            df_prov,
            x="PROVIDER_NAME",
            y="TOTAL_FIN_VALUE",
            title="Top 20 Providers by Contract Value (£)",
        )
        fig_prov.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_prov, use_container_width=True)
    else:
        st.info("TOTAL_FIN_VALUE not available to rank providers.")

# -------------------------
# Raw data expander
# -------------------------
with st.expander("📄 View raw filtered data"):
    st.dataframe(df_filtered, use_container_width=True)
