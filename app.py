import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTwdoXryOVIFA7r2xx0M7utizRKLS009t0XRleTls6bGXI0xaP78oiCzAS0Q08B2O7SZmi9OaD0_HgD/pub?output=csv"
st.set_page_config(layout="wide", page_title="Mobile Data Dashboard")

# Custom CSS for cards
st.markdown("""
<style>
    .card {
        background-color: white;
        border-radius: 12px;
        padding: 20px 24px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border: 1px solid #e5e7eb;
    }
    .card-left { display: flex; align-items: center; }
    .card-header { display: flex; align-items: center; }
    .card-icon { width: 50px; height: 50px; border-radius: 12px; display: flex; align-items: center; justify-content: center; margin-right: 16px; }
    .icon-blue { background-color: #DBEAFE; }
    .icon-purple { background-color: #EDE9FE; }
    .db-icon { width: 28px; height: 28px; }
    .card-title { font-size: 19px; font-weight: 600; color: #1F2937; margin: 0; }
    .status-row { display: flex; align-items: center; gap: 14px; padding: 0; }
    .status-item { text-align: center; padding: 12px 18px; background-color: #F9FAFB; border-radius: 10px; border: 1px solid #e5e7eb; }
    .status-label { font-size: 12px; color: #6B7280; margin-bottom: 5px; font-weight: 500; }
    .status-value { font-size: 19px; font-weight: 700; }
    .value-green { color: #10B981; }
    .value-orange { color: #F59E0B; }
    .value-gray { color: #6B7280; }
    .main-title { font-size: 28px; font-weight: 700; margin-bottom: 18px; margin-top: -20px; color: #1F2937; }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_and_clean(url):
    df = pd.read_csv(url)
    # normalize column names
    df.columns = [c.strip() for c in df.columns]

    # ensure expected columns exist
    for col in ["State Name", "Voter Count", "Voter Status", "Adhar Count", "Adhar Status"]:
        if col not in df.columns:
            df[col] = ""

    def to_int(x):
        if pd.isna(x) or str(x).strip() == "":
            return 0
        s = str(x).strip().replace(",", "").replace(" ", "")
        digits = "".join([c for c in s if c.isdigit()])
        return int(digits) if digits else 0

    df["Voter_Count_Num"] = df["Voter Count"].apply(to_int)
    df["Adhar_Count_Num"] = df["Adhar Count"].apply(to_int)

    def clean(raw, count):
        """
        Priority:
        1. If numeric count > 0 -> Uploaded
        2. If raw contains 'pending' -> Pending upload
        3. If raw contains 'upload' or 'uploaded' -> Uploaded
        4. If raw indicates 'no' or 'no data' -> No Data
        5. Default -> No Data
        """
        s = "" if pd.isna(raw) else str(raw).lower().strip()
        if count > 0:
            return "Uploaded"
        # check 'pending' first because 'pending upload' contains 'upload'
        if "pending" in s:
            return "Pending upload"
        # check upload words next
        if "uploaded" in s or "upload" in s:
            return "Uploaded"
        if "no data" in s or s == "no" or s == "na" or s == "n/a" or s == "":
            return "No Data"
        # fallback
        return "No Data"

    df["Voter_Status_Clean"] = df.apply(lambda r: clean(r["Voter Status"], r["Voter_Count_Num"]), axis=1)
    df["Adhar_Status_Clean"] = df.apply(lambda r: clean(r["Adhar Status"], r["Adhar_Count_Num"]), axis=1)

    df["State"] = df["State Name"].astype(str).str.strip()
    return df

def to_csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8")

# Load data
df = load_and_clean(CSV_URL)

# Sidebar: only state filter
st.sidebar.header("Filters")
state_filter = st.sidebar.selectbox("State", ["All"] + sorted(df["State"].unique().tolist()))

# Apply only the state filter
df_filtered = df.copy()
if state_filter != "All":
    df_filtered = df_filtered[df_filtered["State"] == state_filter]

# Title
st.markdown('<div class="main-title" style="text-align:center;">Mobile Data Status</div>', unsafe_allow_html=True)

# Statistics (based on full df)
aadhaar_uploaded = (df['Adhar_Status_Clean'] == 'Uploaded').sum()
aadhaar_pending = (df['Adhar_Status_Clean'] == 'Pending upload').sum()
aadhaar_no_data = (df['Adhar_Status_Clean'] == 'No Data').sum()

voter_uploaded = (df['Voter_Status_Clean'] == 'Uploaded').sum()
voter_pending = (df['Voter_Status_Clean'] == 'Pending upload').sum()
voter_no_data = (df['Voter_Status_Clean'] == 'No Data').sum()

# Aadhaar Card
st.markdown(f"""
<div class="card">
    <div class="card-left">
        <div class="card-icon icon-blue">
            <svg class="db-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M4 7C4 5.89543 4.89543 5 6 5H18C19.1046 5 20 5.89543 20 7V9H4V7Z" fill="#3B82F6"/>
                <path d="M4 11H20V17C20 18.1046 19.1046 19 18 19H6C4.89543 19 4 18.1046 4 17V11Z" fill="#3B82F6"/>
                <path d="M4 13H20V15H4V13Z" fill="#DBEAFE"/>
            </svg>
        </div>
        <div class="card-title">Aadhaar Data</div>
    </div>
    <div class="status-row">
        <div class="status-item">
            <div class="status-label">Uploaded</div>
            <div class="status-value value-green">{aadhaar_uploaded} <span style="font-size:12px; font-weight:400; color:#6B7280;">states</span></div>
        </div>
        <div class="status-item">
            <div class="status-label">Pending Upload</div>
            <div class="status-value value-orange">{aadhaar_pending} <span style="font-size:12px; font-weight:400; color:#6B7280;">states</span></div>
        </div>
        <div class="status-item">
            <div class="status-label">No Data</div>
            <div class="status-value value-gray">{aadhaar_no_data} <span style="font-size:12px; font-weight:400; color:#6B7280;">states</span></div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Voter Card
st.markdown(f"""
<div class="card">
    <div class="card-left">
        <div class="card-icon icon-purple">
            <svg class="db-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M4 7C4 5.89543 4.89543 5 6 5H18C19.1046 5 20 5.89543 20 7V9H4V7Z" fill="#8B5CF6"/>
                <path d="M4 11H20V17C20 18.1046 19.1046 19 18 19H6C4.89543 19 4 18.1046 4 17V11Z" fill="#8B5CF6"/>
                <path d="M4 13H20V15H4V13Z" fill="#EDE9FE"/>
            </svg>
        </div>
        <div class="card-title">Voter Data</div>
    </div>
    <div class="status-row">
        <div class="status-item">
            <div class="status-label">Uploaded</div>
            <div class="status-value value-green">{voter_uploaded} <span style="font-size:12px; font-weight:400; color:#6B7280;">states</span></div>
        </div>
        <div class="status-item">
            <div class="status-label">Pending Upload</div>
            <div class="status-value value-orange">{voter_pending} <span style="font-size:12px; font-weight:400; color:#6B7280;">states</span></div>
        </div>
        <div class="status-item">
            <div class="status-label">No Data</div>
            <div class="status-value value-gray">{voter_no_data} <span style="font-size:12px; font-weight:400; color:#6B7280;">states</span></div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# -------------------------
# Grouped bar chart (UNLINKED from filters) - always shows full dataset
# X-axis: State, Y-axis: Mobile Count (compact), hover shows exact value
df_bar = df.sort_values("Voter_Count_Num", ascending=False)
if not df_bar.empty:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_bar["State"],
        y=df_bar["Voter_Count_Num"],
        name="Voter Mobile Count",
        marker_color="#1E3A8A",  # NAVY BLUE
        hovertemplate="%{y:,}<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=df_bar["State"],
        y=df_bar["Adhar_Count_Num"],
        name="Aadhaar Mobile Count",
        marker_color="#38BDF8",  # SKY BLUE
        hovertemplate="%{y:,}<extra></extra>"
    ))
    fig.update_layout(
        barmode="group",
        xaxis=dict(title="State", tickangle=-45),
        yaxis=dict(title="Mobile Count", tickformat=".2s"),
        height=360,
        # margin=dict(t=10, b=80, l=60, r=10),
        margin=dict(t=5, b=10, l=60, r=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
# -------------------------

# Table with new format (based on df_filtered)
st.subheader("State Level Details")

display = df_filtered.copy()
display["Voter Mobile Count/Status"] = display.apply(
    lambda r: f"{r['Voter_Count_Num']:,}" if r['Voter_Count_Num'] > 0 else r['Voter_Status_Clean'],
    axis=1
)
display["Aadhaar Mobile Count/Status"] = display.apply(
    lambda r: f"{r['Adhar_Count_Num']:,}" if r['Adhar_Count_Num'] > 0 else r['Adhar_Status_Clean'],
    axis=1
)

display = display[["State", "Voter Mobile Count/Status", "Aadhaar Mobile Count/Status"]]

# Show index from 1 instead of 0
display.index = display.index + 1

st.dataframe(display, use_container_width=True)

# Download filtered CSV
st.download_button(
    "Download filtered CSV",
    to_csv_bytes(display),
    "filtered_states.csv",
    "text/csv"
)
