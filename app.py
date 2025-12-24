import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import BytesIO

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTwdoXryOVIFA7r2xx0M7utizRKLS009t0XRleTls6bGXI0xaP78oiCzAS0Q08B2O7SZmi9OaD0_HgD/pub?output=csv"
st.set_page_config(layout="wide", page_title="Mobile Data Dashboard")

# Custom CSS
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
    .card-icon { width: 50px; height: 50px; border-radius: 12px; display: flex; align-items: center; justify-content: center; margin-right: 16px; }
    .icon-blue { background-color: #DBEAFE; }
    .icon-purple { background-color: #EDE9FE; }
    .icon-green { background-color: #D1FAE5; }
    .db-icon { width: 28px; height: 28px; }
    .card-title { font-size: 19px; font-weight: 600; color: #1F2937; margin: 0; }
    .status-row { display: flex; align-items: center; gap: 14px; padding: 0; }
    .status-item { text-align: center; padding: 12px 18px; background-color: #F9FAFB; border-radius: 10px; border: 1px solid #e5e7eb; min-width: 120px; flex: 1; }
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
    import time
    import requests
    from io import StringIO

    max_retries = 3

    for attempt in range(max_retries):
        try:
            # Use requests library instead of pandas direct URL reading
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # Raise an error for bad status codes

            # Read CSV from the response text
            df = pd.read_csv(StringIO(response.text))
            break
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                st.warning(f"Connection attempt {attempt + 1} failed. Retrying in 2 seconds...")
                time.sleep(2)
            else:
                st.error(f"Failed to load data after {max_retries} attempts.")
                st.error(f"Error: {str(e)}")
                st.info("Please check: 1) Internet connection, 2) Google Sheets is published to web, 3) URL is correct")
                st.stop()
        except Exception as e:
            st.error(f"Unexpected error: {str(e)}")
            st.stop()

    df.columns = [c.strip() for c in df.columns]

    # Ensure all required columns exist
    for col in ["State Name", "Population", "Voter Count", "Voter Status", "Adhar Count", "Adhar Status",
                "Cadre Count", "Cadre Status", "Overall Unique Mobile Count (Within State)"]:
        if col not in df.columns:
            df[col] = "" if col in ["State Name", "Voter Status", "Adhar Status", "Cadre Status"] else 0

    # Rename Voter to Eroll for display
    df["Eroll Count"] = df["Voter Count"]
    df["Eroll Status"] = df["Voter Status"]

    def to_int(x):
        if pd.isna(x) or str(x).strip() == "":
            return 0
        s = str(x).strip().replace(",", "").replace(" ", "")
        # Check for "Data Not Available" or similar text
        if any(word in s.lower() for word in ["data", "not", "available", "na", "n/a"]):
            return 0
        digits = "".join([c for c in s if c.isdigit()])
        return int(digits) if digits else 0

    def to_float(x):
        if pd.isna(x) or str(x).strip() == "":
            return 0.0
        try:
            return float(str(x).strip().replace(",", ""))
        except:
            return 0.0

    df["Population_Num"] = df["Population"].apply(to_float)
    df["Adhar_Count_Num"] = df["Adhar Count"].apply(to_int)
    df["Cadre_Count_Num"] = df["Cadre Count"].apply(to_int)
    df["Eroll_Count_Num"] = df["Voter Count"].apply(to_int)
    df["Overall_Mobile_Count_Num"] = df["Overall Unique Mobile Count (Within State)"].apply(to_int)

    def clean(raw, count):
        s = "" if pd.isna(raw) else str(raw).lower().strip()
        if count > 0:
            return "Uploaded"
        # Check for various "data not available" formats
        if any(word in s for word in ["data not available", "not available", "na", "n/a"]):
            return "No Data"
        if "pending" in s:
            return "Pending upload"
        if "uploaded" in s or "upload" in s or "uploded" in s:  # Handle typo "uploded"
            return "Uploaded"
        return "No Data"

    df["Adhar_Status_Clean"] = df.apply(lambda r: clean(r["Adhar Status"], r["Adhar_Count_Num"]), axis=1)
    df["Cadre_Status_Clean"] = df.apply(lambda r: clean(r["Cadre Status"], r["Cadre_Count_Num"]), axis=1)
    df["Eroll_Status_Clean"] = df.apply(lambda r: clean(r["Voter Status"], r["Eroll_Count_Num"]), axis=1)

    # Calculate percentages in order: Aadhaar, Cadre, Eroll
    df["Adhar_Percent"] = df.apply(
        lambda r: (r["Adhar_Count_Num"] / r["Population_Num"] * 100) if r["Population_Num"] > 0 else 0,
        axis=1
    )
    df["Cadre_Percent"] = df.apply(
        lambda r: (r["Cadre_Count_Num"] / r["Population_Num"] * 100) if r["Population_Num"] > 0 else 0,
        axis=1
    )
    df["Eroll_Percent"] = df.apply(
        lambda r: (r["Eroll_Count_Num"] / r["Population_Num"] * 100) if r["Population_Num"] > 0 else 0,
        axis=1
    )
    df["Overall_Mobile_Percent"] = df.apply(
        lambda r: (r["Overall_Mobile_Count_Num"] / r["Population_Num"] * 100) if r["Population_Num"] > 0 else 0,
        axis=1
    )

    df["State"] = df["State Name"].astype(str).str.strip()
    return df


def format_number(n):
    if n > 0:
        return f"{int(n):,}"
    else:
        return "0"


def create_progress_bar(count, percentage):
    """Create HTML for a progress bar - always green"""
    pct = min(percentage, 100)

    return f"""
    <div class="data-content">
        <div class="data-header">
            <span class="count-text">{format_number(count)}</span>
            <span class="percent-badge">{pct:.1f}%</span>
        </div>
        <div class="progress-bar">
            <div class="progress-fill progress-green" style="width: {pct}%;"></div>
        </div>
    </div>
    """


def create_status_badge(status):
    """Create HTML for status badge"""
    if status == "Pending upload":
        return f'<span class="status-badge badge-pending">{status}</span>'
    else:
        return f'<span class="status-badge badge-nodata">{status}</span>'


def to_csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8")


# Load data
df = load_and_clean(CSV_URL)

# Sidebar
st.sidebar.header("Filters")
state_filter = st.sidebar.selectbox("State", ["All"] + sorted(df["State"].unique().tolist()))

# Apply filter
df_filtered = df.copy()
if state_filter != "All":
    df_filtered = df_filtered[df_filtered["State"] == state_filter]

# Title
st.markdown('<div class="main-title" style="text-align:center;">Mobile Data Status</div>', unsafe_allow_html=True)

# Statistics - Order: Aadhaar, Cadre, Eroll
aadhaar_uploaded = (df['Adhar_Status_Clean'] == 'Uploaded').sum()
aadhaar_pending = (df['Adhar_Status_Clean'] == 'Pending upload').sum()
aadhaar_no_data = (df['Adhar_Status_Clean'] == 'No Data').sum()

cadre_uploaded = (df['Cadre_Status_Clean'] == 'Uploaded').sum()
cadre_pending = (df['Cadre_Status_Clean'] == 'Pending upload').sum()
cadre_no_data = (df['Cadre_Status_Clean'] == 'No Data').sum()

eroll_uploaded = (df['Eroll_Status_Clean'] == 'Uploaded').sum()
eroll_pending = (df['Eroll_Status_Clean'] == 'Pending upload').sum()
eroll_no_data = (df['Eroll_Status_Clean'] == 'No Data').sum()

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

# Cadre Card
st.markdown(f"""
<div class="card">
    <div class="card-left">
        <div class="card-icon icon-green">
            <svg class="db-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M4 7C4 5.89543 4.89543 5 6 5H18C19.1046 5 20 5.89543 20 7V9H4V7Z" fill="#10B981"/>
                <path d="M4 11H20V17C20 18.1046 19.1046 19 18 19H6C4.89543 19 4 18.1046 4 17V11Z" fill="#10B981"/>
                <path d="M4 13H20V15H4V13Z" fill="#D1FAE5"/>
            </svg>
        </div>
        <div class="card-title">Cadre Data</div>
    </div>
    <div class="status-row">
        <div class="status-item">
            <div class="status-label">Uploaded</div>
            <div class="status-value value-green">{cadre_uploaded} <span style="font-size:12px; font-weight:400; color:#6B7280;">states</span></div>
        </div>
        <div class="status-item">
            <div class="status-label">Pending Upload</div>
            <div class="status-value value-orange">{cadre_pending} <span style="font-size:12px; font-weight:400; color:#6B7280;">states</span></div>
        </div>
        <div class="status-item">
            <div class="status-label">No Data</div>
            <div class="status-value value-gray">{cadre_no_data} <span style="font-size:12px; font-weight:400; color:#6B7280;">states</span></div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Eroll Card
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
        <div class="card-title">Eroll Data</div>
    </div>
    <div class="status-row">
        <div class="status-item">
            <div class="status-label">Uploaded</div>
            <div class="status-value value-green">{eroll_uploaded} <span style="font-size:12px; font-weight:400; color:#6B7280;">states</span></div>
        </div>
        <div class="status-item">
            <div class="status-label">Pending Upload</div>
            <div class="status-value value-orange">{eroll_pending} <span style="font-size:12px; font-weight:400; color:#6B7280;">states</span></div>
        </div>
        <div class="status-item">
            <div class="status-label">No Data</div>
            <div class="status-value value-gray">{eroll_no_data} <span style="font-size:12px; font-weight:400; color:#6B7280;">states</span></div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Bar chart - Order: Aadhaar, Cadre, Eroll (removed Overall Unique Mobile)
df_bar = df.sort_values("Adhar_Count_Num", ascending=False)
if not df_bar.empty:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_bar["State"],
        y=df_bar["Adhar_Count_Num"],
        name="Aadhaar",
        marker_color="#38BDF8",
        hovertemplate="%{y:,}<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=df_bar["State"],
        y=df_bar["Cadre_Count_Num"],
        name="Cadre",
        marker_color="#10B981",
        hovertemplate="%{y:,}<extra></extra>"
    ))
    fig.add_trace(go.Bar(
        x=df_bar["State"],
        y=df_bar["Eroll_Count_Num"],
        name="Eroll",
        marker_color="#8B5CF6",
        hovertemplate="%{y:,}<extra></extra>"
    ))
    fig.update_layout(
        barmode="group",
        xaxis=dict(title="State", tickangle=-45),
        yaxis=dict(title="Mobile Count", tickformat=","),
        height=400,
        margin=dict(t=5, b=10, l=60, r=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, config={"displayModeBar": False})

# Enhanced Table Section
st.subheader("State Level Details")

# Build HTML table with full styling
html_table = """
<style>
    .table-wrapper {
        background: white;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border: 1px solid #E5E7EB;
    }
    .enhanced-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
    }
    .enhanced-table thead {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        position: sticky;
        top: 0;
        z-index: 10;
    }
    .enhanced-table th {
        padding: 18px 16px;
        text-align: left;
        font-weight: 600;
        font-size: 15px;
    }
    .enhanced-table tbody tr {
        border-bottom: 1px solid #E5E7EB;
        transition: background 0.2s;
    }
    .enhanced-table tbody tr:nth-child(even) {
        background: #F9FAFB;
    }
    .enhanced-table tbody tr:hover {
        background: #EEF2FF;
    }
    .enhanced-table td {
        padding: 18px 16px;
        vertical-align: middle;
    }
    .state-name {
        font-weight: 600;
        color: #1F2937;
        font-size: 16px;
    }
    .population-cell {
        color: #1F2937;
        font-weight: 700;
        font-size: 16px;
    }
    .data-content {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    .data-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .count-text {
        font-weight: 700;
        color: #1F2937;
        font-size: 16px;
    }
    .percent-badge {
        font-size: 15px;
        font-weight: 600;
        padding: 6px 14px;
        border-radius: 12px;
        background: #DBEAFE;
        color: #1E40AF;
    }
    .progress-bar {
        width: 100%;
        height: 10px;
        background: #E5E7EB;
        border-radius: 10px;
        overflow: hidden;
    }
    .progress-fill {
        height: 100%;
        border-radius: 10px;
        transition: width 0.5s ease;
    }
    .progress-green { background: linear-gradient(90deg, #10B981, #059669); }
    .status-badge {
        display: inline-block;
        padding: 8px 16px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
    }
    .badge-pending {
        background: #FEF3C7;
        color: #92400E;
    }
    .badge-nodata {
        background: #F3F4F6;
        color: #4B5563;
    }
</style>

<div class="table-wrapper">
<table class="enhanced-table">
    <thead>
        <tr>
            <th>State</th>
            <th>Population</th>
            <th>Aadhaar</th>
            <th>Cadre</th>
            <th>Eroll</th>
            <th>Overall Unique Mobile</th>
        </tr>
    </thead>
    <tbody>
"""

display = df_filtered.sort_values("State")

for _, row in display.iterrows():
    html_table += f"""
        <tr>
            <td class="state-name">{row['State']}</td>
            <td class="population-cell">{format_number(row['Population_Num'])}</td>
            <td>
    """

    # Aadhaar column (first)
    if row['Adhar_Count_Num'] > 0:
        html_table += create_progress_bar(row['Adhar_Count_Num'], row['Adhar_Percent'])
    else:
        html_table += create_status_badge(row['Adhar_Status_Clean'])

    html_table += "</td><td>"

    # Cadre column (second)
    if row['Cadre_Count_Num'] > 0:
        html_table += create_progress_bar(row['Cadre_Count_Num'], row['Cadre_Percent'])
    else:
        html_table += create_status_badge(row['Cadre_Status_Clean'])

    html_table += "</td><td>"

    # Eroll column (third)
    if row['Eroll_Count_Num'] > 0:
        html_table += create_progress_bar(row['Eroll_Count_Num'], row['Eroll_Percent'])
    else:
        html_table += create_status_badge(row['Eroll_Status_Clean'])

    html_table += "</td><td>"

    # Overall Unique Mobile column (fourth)
    if row['Overall_Mobile_Count_Num'] > 0:
        html_table += create_progress_bar(row['Overall_Mobile_Count_Num'], row['Overall_Mobile_Percent'])
    else:
        html_table += '<span class="status-badge badge-nodata">No Data</span>'

    html_table += "</td></tr>"

html_table += """
    </tbody>
</table>
</div>
"""

# Display the HTML table
st.components.v1.html(html_table, height=600, scrolling=True)

# Download button
st.markdown("<br>", unsafe_allow_html=True)
display_df = df_filtered[["State", "Population_Num", "Adhar_Count_Num", "Adhar_Percent", "Adhar_Status_Clean",
                          "Cadre_Count_Num", "Cadre_Percent", "Cadre_Status_Clean",
                          "Eroll_Count_Num", "Eroll_Percent", "Eroll_Status_Clean",
                          "Overall_Mobile_Count_Num", "Overall_Mobile_Percent"]].copy()
display_df.columns = ["State", "Population", "Aadhaar Count", "Aadhaar %", "Aadhaar Status",
                      "Cadre Count", "Cadre %", "Cadre Status",
                      "Eroll Count", "Eroll %", "Eroll Status",
                      "Overall Mobile Count", "Overall Mobile %"]

st.download_button(
    "📥 Download Filtered Data as CSV",
    to_csv_bytes(display_df),
    "mobile_data_filtered.csv",
    "text/csv"
)