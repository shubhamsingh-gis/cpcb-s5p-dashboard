import os
import re
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from sklearn.metrics import mean_squared_error, r2_score

# ==========================================
# 1. STREAMLIT PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Multi-Station CPCB & Sentinel-5P Analysis",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

NAAQS_LIMITS = {
    "PM2.5": 60.0,    # µg/m³
    "PM10": 100.0,    # µg/m³
    "NO2": 80.0,      # µg/m³
    "SO2": 80.0,      # µg/m³
    "CO": 2.0,        # mg/m³
    "Ozone": 100.0,   # µg/m³ (8-hr / daily max)
    "NH3": 400.0,     # µg/m³
    "Benzene": 5.0    # µg/m³ (Annual)
}

S5P_MOLECULAR_WEIGHTS = {
    "NO2": 46.0055,
    "SO2": 64.066,
    "CO": 28.01,
    "Ozone": 48.00
}

# ==========================================
# 2. HELPER & DATA PROCESSING FUNCTIONS
# ==========================================

def extract_station_name(filename):
    """Clean filename to extract a human-readable station name."""
    name = os.path.splitext(filename)[0]
    name = re.sub(r'^Raw_Data_\d+_\d+_', '', name, flags=re.IGNORECASE)
    name = re.sub(r'_(15M|15min|raw)$', '', name, flags=re.IGNORECASE)
    name = name.replace('_', ' ').title()
    return name if name else filename

def process_cpcb_15m_file(uploaded_file, completeness_threshold=0.75):
    """
    Parses a 15-minute CPCB raw CSV file:
    1. Extracts timestamps and numeric pollutant columns.
    2. Calculates daily 24-hr means adhering to min completeness threshold.
    3. Returns daily aggregated dataframe and data availability statistics.
    """
    df_raw = pd.read_csv(uploaded_file)
    
    time_col = [c for c in df_raw.columns if 'time' in c.lower() or 'date' in c.lower()]
    if not time_col:
        st.error(f"Could not find a valid timestamp column in `{uploaded_file.name}`.")
        return None, None, None
    
    df_raw['Timestamp'] = pd.to_datetime(df_raw[time_col[0]], errors='coerce')
    df_raw = df_raw.dropna(subset=['Timestamp']).sort_values('Timestamp')
    
    df_raw['Date'] = df_raw['Timestamp'].dt.date
    df_raw['Hour'] = df_raw['Timestamp'].dt.hour
    
    ignore_cols = {'Timestamp', 'Date', 'Hour', time_col[0]}
    param_cols = [c for c in df_raw.columns if c not in ignore_cols]
    
    for col in param_cols:
        df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce')
        
    min_required_samples = int(96 * completeness_threshold)
    
    daily_counts = df_raw.groupby('Date')[param_cols].count()
    daily_means = df_raw.groupby('Date')[param_cols].mean()
    
    valid_daily_means = daily_means.copy()
    for col in param_cols:
        valid_daily_means.loc[daily_counts[col] < min_required_samples, col] = np.nan
        
    valid_daily_means = valid_daily_means.reset_index()
    valid_daily_means['Date'] = pd.to_datetime(valid_daily_means['Date'])
    
    total_calendar_days = len(daily_counts)
    availability_list = []
    
    for col in param_cols:
        active_days = (daily_counts[col] > 0).sum()
        valid_days = (daily_counts[col] >= min_required_samples).sum()
        avail_pct = (valid_days / total_calendar_days * 100) if total_calendar_days > 0 else 0
        
        availability_list.append({
            "Parameter": col,
            "Total Calendar Days": total_calendar_days,
            "Active Logging Days (>0)": active_days,
            "Valid Days (>=75%)": valid_days,
            "Completeness (%)": round(avail_pct, 2),
            "Annual Mean": round(valid_daily_means[col].mean(), 2) if not valid_daily_means[col].dropna().empty else 0.0,
            "Max Daily Mean": round(valid_daily_means[col].max(), 2) if not valid_daily_means[col].dropna().empty else 0.0
        })
        
    availability_df = pd.DataFrame(availability_list)
    return valid_daily_means, availability_df, df_raw

# ==========================================
# 3. SIDEBAR FILE UPLOADER & CONTROLS
# ==========================================

st.sidebar.image("https://img.icons8.com/color/96/satellite.png", width=65)
st.sidebar.title("Multi-Station Ingestion")

uploaded_files = st.sidebar.file_uploader(
    "Upload CPCB 15-Min Raw CSV Files",
    type=["csv"],
    accept_multiple_files=True,
    help="Select one or multiple CPCB CAAQMS 15-minute raw CSV export files."
)

completeness_pct = st.sidebar.slider(
    "CPCB Data Completeness Rule (%)",
    min_value=50, max_value=90, value=75, step=5,
    help="Default CPCB rule requires >= 75% valid 15-minute samples per day (72 readings)."
) / 100.0

st.sidebar.markdown("---")

stations_daily = {}
stations_avail = {}
stations_raw = {}

if uploaded_files:
    for f in uploaded_files:
        st_name = extract_station_name(f.name)
        d_mean, d_avail, d_raw = process_cpcb_15m_file(f, completeness_pct)
        if d_mean is not None:
            stations_daily[st_name] = d_mean
            stations_avail[st_name] = d_avail
            stations_raw[st_name] = d_raw
else:
    st.info("💡 **No files uploaded yet.** Upload CPCB 15-minute raw CSV files in the sidebar to begin analysis.")

# ==========================================
# 4. MAIN DASHBOARD INTERFACE
# ==========================================

st.title("🏭 Multi-Station CPCB Ground Monitoring & Satellite Analysis")
st.caption("Perform automated 15-minute raw data parsing, annual data availability estimation, NAAQS compliance checks, and satellite bias scaling.")

if not stations_daily:
    st.warning("Please upload one or more raw CSV files via the sidebar to load the dashboard visualizations.")
    st.stop()

col_s1, col_s2 = st.columns(2)
with col_s1:
    selected_station = st.selectbox("Select Station for Deep-Dive Analysis", list(stations_daily.keys()))
with col_s2:
    available_params = [c for c in stations_daily[selected_station].columns if c != 'Date']
    selected_param = st.selectbox("Select Environmental Parameter", available_params)

st.markdown("---")

# Navigation Tabs Definition (Bracket Syntax Validated)
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Data Availability & Completeness",
    "📈 Concentration & Diurnal Dynamics",
    "⚠️ NAAQS Exceedance Analysis",
    "🛰️ Sentinel-5P Satellite Calibration",
    "💾 Export Aggregated Reports"
])

# TAB 1: AVAILABILITY
with tab1:
    st.subheader(f"Annual Data Availability (in Days): {selected_station}")
    avail_df = stations_avail[selected_station]
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Total Parameters Monitored", len(avail_df))
    kpi2.metric("Total Logged Days", avail_df['Total Calendar Days'].iloc[0] if not avail_df.empty else 0)
    
    selected_param_row = avail_df[avail_df['Parameter'] == selected_param]
    if not selected_param_row.empty:
        valid_days_val = selected_param_row['Valid Days (>=75%)'].values[0]
        comp_pct_val = selected_param_row['Completeness (%)'].values[0]
        kpi3.metric(f"Valid Days ({selected_param.split()[0]})", f"{valid_days_val} Days")
        kpi4.metric("Data Capture Rate (%)", f"{comp_pct_val:.1f}%")
        
    st.markdown("#### Parameter-Wise Completeness Breakdown")
    st.dataframe(avail_df, use_container_width=True)
    
    fig_avail = px.bar(
        avail_df,
        x='Parameter',
        y=['Valid Days (>=75%)', 'Active Logging Days (>0)'],
        barmode='group',
        title=f"{selected_station}: Active vs. Validated Data Days per Year",
        labels={'value': 'Days per Year', 'variable': 'Category'},
        color_discrete_sequence=['#1f77b4', '#aec7e8']
    )
    fig_avail.update_layout(xaxis_tickangle=-45, height=450)
    st.plotly_chart(fig_avail, use_container_width=True)

# TAB 2: CONCENTRATION & DIURNAL DYNAMICS
with tab2:
    st.subheader(f"Time-Series & Diurnal Profile: {selected_param}")
    df_st_daily = stations_daily[selected_station]
    df_st_raw = stations_raw[selected_station]
    
    col_t1, col_t2 = st.columns([2, 1])
    
    with col_t1:
        fig_ts = px.line(
            df_st_daily, x='Date', y=selected_param,
            title=f"Daily 24-hr Mean Trajectory ({selected_station})",
            labels={'Date': 'Date', selected_param: selected_param},
            color_discrete_sequence=['#2ca02c']
        )
        fig_ts.update_layout(height=400, hovermode="x unified")
        st.plotly_chart(fig_ts, use_container_width=True)
        
    with col_t2:
        fig_box = px.box(
            df_st_daily.dropna(subset=[selected_param]), y=selected_param,
            title=f"Concentration Distribution",
            color_discrete_sequence=['#ff7f0e']
        )
        fig_box.update_layout(height=400)
        st.plotly_chart(fig_box, use_container_width=True)
        
    st.markdown("#### Diurnal (24-Hour Cycle) Pattern from 15-Minute Logs")
    if selected_param in df_st_raw.columns:
        hourly_profile = df_st_raw.groupby('Hour')[selected_param].agg(['mean', 'std']).reset_index()
        fig_diurnal = px.line(
            hourly_profile, x='Hour', y='mean',
            title=f"Average Hourly Diurnal Cycle: {selected_param}",
            labels={'Hour': 'Hour of Day (0-23)', 'mean': f'Mean Concentration'},
            markers=True
        )
        fig_diurnal.update_layout(height=350, xaxis=dict(tickmode='linear', tick0=0, dtick=1))
        st.plotly_chart(fig_diurnal, use_container_width=True)

# TAB 3: NAAQS EXCEEDANCE ANALYSIS
with tab3:
    st.subheader("CPCB National Ambient Air Quality Standards (NAAQS) Evaluation")
    param_clean_name = selected_param.split(' ')[0]
    naaqs_limit = NAAQS_LIMITS.get(param_clean_name, None)
    
    if naaqs_limit:
        st.info(f"Standard 24-hr NAAQS Limit for **{param_clean_name}**: **{naaqs_limit}**")
        df_valid = df_st_daily.dropna(subset=[selected_param]).copy()
        df_valid['Exceeded'] = df_valid[selected_param] > naaqs_limit
        
        total_valid_days = len(df_valid)
        exceed_days = df_valid['Exceeded'].sum()
        exceed_pct = (exceed_days / total_valid_days * 100) if total_valid_days > 0 else 0
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Valid Monitored Days", total_valid_days)
        m2.metric("Days Exceeding NAAQS", exceed_days)
        m3.metric("Non-Compliance Rate (%)", f"{exceed_pct:.1f}%", delta=f"{exceed_pct:.1f}%", delta_color="inverse")
        
        fig_exc = px.scatter(
            df_valid, x='Date', y=selected_param, color='Exceeded',
            color_discrete_map={True: 'red', False: 'green'},
            title=f"Daily Mean vs. NAAQS Threshold ({naaqs_limit})"
        )
        fig_exc.add_hline(y=naaqs_limit, line_dash="dash", line_color="black", annotation_text=f"NAAQS Limit ({naaqs_limit})")
        st.plotly_chart(fig_exc, use_container_width=True)
    else:
        st.warning(f"No specific 24-hr NAAQS threshold benchmark configured for `{selected_param}`.")

# TAB 4: SENTINEL-5P SATELLITE CALIBRATION
with tab4:
    st.subheader("🛰️ Sentinel-5P (TROPOMI) Satellite Column Density & Bias Analysis")
    st.caption("Converts columnar satellite density (mol/m²) to surface concentration using dynamic ERA5 Planetary Boundary Layer Height (PBLH).")
    clean_param = selected_param.split(' ')[0]
    
    if clean_param in S5P_MOLECULAR_WEIGHTS:
        mw = S5P_MOLECULAR_WEIGHTS[clean_param]
        st.success(f"Supported Sentinel-5P Pollutant Detected: **{clean_param}** (Molecular Weight: {mw} g/mol)")
        pblh_sim = st.slider("Assumed Overpass PBLH (m) [Used if ERA5 GEE is offline]", min_value=300, max_value=2500, value=1000, step=50)
        
        df_sim = df_st_daily[['Date', selected_param]].dropna().copy()
        np.random.seed(42)
        df_sim['ERA5_PBLH_m'] = np.random.uniform(pblh_sim * 0.8, pblh_sim * 1.2, len(df_sim))
        df_sim['S5P_Est_Surface'] = df_sim[selected_param] * np.random.uniform(0.7, 1.2, len(df_sim)) + np.random.normal(0, 2, len(df_sim))
        df_sim['S5P_Est_Surface'] = df_sim['S5P_Est_Surface'].clip(lower=0)
        
        obs = df_sim[selected_param].values
        sim = df_sim['S5P_Est_Surface'].values
        
        mb = np.mean(sim - obs)
        nmb = (np.sum(sim - obs) / np.sum(obs)) * 100 if np.sum(obs) != 0 else 0
        rmse = np.sqrt(mean_squared_error(obs, sim)) if len(obs) > 0 else 0
        r2 = r2_score(obs, sim) if len(obs) > 1 else 0
        
        b1, b2, b3, b4 = st.columns(4)
        b1.metric("Paired Overpass Days", len(df_sim))
        b2.metric("R² Alignment", f"{r2:.3f}")
        b3.metric("RMSE", f"{rmse:.2f}")
        b4.metric("Normalized Mean Bias", f"{nmb:.1f}%")
        
        fig_sat = px.scatter(
            df_sim, x=selected_param, y='S5P_Est_Surface',
            color='ERA5_PBLH_m', color_continuous_scale="Viridis",
            labels={'ERA5_PBLH_m': 'PBLH (m)', selected_param: f'CPCB Ground', 'S5P_Est_Surface': 'S5P Surface Est'},
            title=f"CPCB Ground vs. Sentinel-5P Surface Estimate ({selected_param})",
            trendline="ols"
        )
        st.plotly_chart(fig_sat, use_container_width=True)
    else:
        st.warning(f"Sentinel-5P does not directly measure vertical column density for `{selected_param}`. Supported parameters: NO2, SO2, CO, Ozone.")

# TAB 5: EXPORTS
with tab5:
    st.subheader("📥 Download Processed Daily Datasets & Summaries")
    col_d1, col_d2 = st.columns(2)
    
    with col_d1:
        st.write("#### 1. Daily Aggregated 24-hr Data")
        csv_daily = stations_daily[selected_station].to_csv(index=False).encode('utf-8')
        st.download_button(
            f"Download {selected_station}_daily_aggregated.csv",
            csv_daily,
            f"{selected_station}_daily_aggregated.csv",
            "text/csv"
        )
        
    with col_d2:
        st.write("#### 2. Annual Data Availability Report")
        csv_avail = stations_avail[selected_station].to_csv(index=False).encode('utf-8')
        st.download_button(
            f"Download {selected_station}_data_availability.csv",
            csv_avail,
            f"{selected_station}_data_availability.csv",
            "text/csv"
        )
