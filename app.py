import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
import io
from pathlib import Path

from src.emissions_calculator.models import ActivityInput
from src.emissions_calculator.factors import load_emission_factors, FactorLoadError
from src.emissions_calculator.calculator import (
    calculate_inventory,
    summarize_by_scope,
    UnknownActivityError
)
from src.emissions_calculator.egrid_factors import (
    EgridFactorLoadError,
    build_factor_file_map,
    load_egrid_subregion_factors,
    normalize_egrid_subregion,
    with_egrid_electricity_factor,
)
from src.emissions_calculator.scope3_factors import load_scope3_factors, Scope3FactorLoadError
from src.emissions_calculator.scope3_calculator import calculate_scope3_inventory

# Page Setup
st.set_page_config(
    page_title="CarbonAware | Framework-Aligned Emissions Calculator",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Injected CSS for custom premium styling (glassmorphism cards, Google Fonts, and smooth layouts)
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    /* Global Styles */
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    /* Title and Header Gradients */
    .app-title {
        font-size: 2.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #10B981 0%, #3B82F6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    
    .app-subtitle {
        font-size: 1.1rem;
        color: #6B7280;
        margin-bottom: 2rem;
        font-weight: 400;
    }
    
    /* Glassmorphism Metric Cards */
    .metric-container {
        display: flex;
        gap: 1.5rem;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        flex: 1;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 1.5rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-4px);
        border-color: rgba(16, 185, 129, 0.3);
    }
    
    .metric-label {
        font-size: 0.85rem;
        color: #9CA3AF;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        margin-bottom: 0.5rem;
    }
    
    .metric-value-s1 {
        font-size: 2.4rem;
        font-weight: 700;
        background: linear-gradient(135deg, #F59E0B 0%, #EF4444 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .metric-value-s2 {
        font-size: 2.4rem;
        font-weight: 700;
        background: linear-gradient(135deg, #3B82F6 0%, #06B6D4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .metric-value-total {
        font-size: 2.4rem;
        font-weight: 700;
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .metric-meta {
        font-size: 0.85rem;
        font-weight: 500;
        margin-top: 0.4rem;
    }
    
    /* Disclaimer and educational info container */
    .disclaimer-container {
        background-color: rgba(239, 68, 68, 0.08);
        border-left: 4px solid #EF4444;
        padding: 1.2rem;
        border-radius: 8px;
        margin-bottom: 2rem;
    }
    
    .disclaimer-title {
        font-weight: 600;
        color: #F87171;
        margin-bottom: 0.3rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .disclaimer-text {
        font-size: 0.9rem;
        color: #E5E7EB;
        line-height: 1.5;
    }
    
    .info-container {
        background-color: rgba(59, 130, 246, 0.08);
        border-left: 4px solid #3B82F6;
        padding: 1.2rem;
        border-radius: 8px;
        margin-bottom: 2rem;
    }
    
    .info-title {
        font-weight: 600;
        color: #60A5FA;
        margin-bottom: 0.3rem;
    }
    
    .info-text {
        font-size: 0.9rem;
        color: #E5E7EB;
        line-height: 1.5;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Load factors
FACTORS_PATH = os.path.join(os.path.dirname(__file__), "data", "emission_factors.json")
EGRID_FACTORS_PATH = os.path.join(os.path.dirname(__file__), "data", "egrid2023_subregion_factors.json")
SCOPE3_FACTORS_PATH = os.path.join(os.path.dirname(__file__), "data", "scope3_supply_chain_factors.json")

try:
    factors = load_emission_factors(FACTORS_PATH)
except FactorLoadError as e:
    st.error(f"Error loading emission factors database: {str(e)}")
    st.stop()

try:
    scope3_factors = load_scope3_factors(SCOPE3_FACTORS_PATH)
except Scope3FactorLoadError as e:
    st.error(f"Error loading Scope 3 emission factors database: {str(e)}")
    st.stop()

try:
    egrid_factors = load_egrid_subregion_factors(EGRID_FACTORS_PATH)
except EgridFactorLoadError as e:
    st.error(f"Error loading eGRID subregion factors database: {str(e)}")
    st.stop()


def egrid_option_label(code: str) -> str:
    """Build a compact label for the eGRID subregion select boxes."""
    factor = egrid_factors[code]
    display_name = factor.source_name.split(f"{code} ", 1)[-1]
    return f"{code} - {display_name} ({factor.factor_value:.6f} MT CO2e/kWh)"


egrid_options = sorted(egrid_factors.keys(), key=lambda code: (code != "US", code))
egrid_label_to_code = {egrid_option_label(code): code for code in egrid_options}
default_egrid_index = egrid_options.index("US") if "US" in egrid_options else 0
egrid_factor_filename = os.path.basename(EGRID_FACTORS_PATH)

# Sidebar - Parameters and Information
st.sidebar.image("https://img.icons8.com/color/96/co2.png", width=70)
st.sidebar.markdown("### **CarbonAware v1.0**")
st.sidebar.markdown(
    "A framework-aligned emissions calculator aligned with the Greenhouse Gas (GHG) Protocol corporate standard."
)
st.sidebar.markdown("---")

st.sidebar.subheader("⚙️ Custom Emission Factors")
uploaded_factor_file = st.sidebar.file_uploader("Upload custom factors (CSV or JSON)", type=["csv", "json"])

if uploaded_factor_file is not None:
    import tempfile
    ext = os.path.splitext(uploaded_factor_file.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(uploaded_factor_file.getvalue())
        tmp_path = tmp.name
    try:
        factors = load_emission_factors(tmp_path)
        base_factor_filename = uploaded_factor_file.name
        st.sidebar.success(f"Loaded custom factors: {base_factor_filename}")
    except FactorLoadError as e:
        st.sidebar.error(f"Error loading custom factors: {str(e)}")
        base_factor_filename = os.path.basename(FACTORS_PATH)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
else:
    base_factor_filename = os.path.basename(FACTORS_PATH)

scope12_factor_file_map = build_factor_file_map(base_factor_filename, egrid_factor_filename)

st.sidebar.markdown("---")

st.sidebar.subheader("🌱 About Scopes")
st.sidebar.markdown(
    """
    **Scope 1 (Direct Emissions)**
    Direct greenhouse gas emissions from sources owned or controlled by the reporting company, e.g., natural gas for heating or diesel fuel for company-owned fleets.
    
    **Scope 2 (Indirect Emissions)**
    Indirect emissions associated with the generation of electricity, steam, heating, or cooling purchased and consumed by the reporting company.
    """
)

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    💡 *Tip: Download the sample template CSV under the "Bulk Upload" tab to test calculations on multiple facilities simultaneously.*
    """
)

# Main Application Layout
st.markdown('<div class="app-title">CarbonAware</div>', unsafe_allow_html=True)
st.markdown('<div class="app-subtitle">Framework-Aligned Greenhouse Gas Accounting MVP</div>', unsafe_allow_html=True)

# Tabs
tab_single, tab_bulk, tab_scope3, tab_factors, tab_limitations = st.tabs([
    "📊 Single Facility Calculator", 
    "📁 Bulk CSV Processing", 
    "🚚 Scope 3 Supply Chain",
    "📚 Emission Factors Library", 
    "⚠️ Scope & Limitations"
])

# ================= TAB 1: SINGLE FACILITY CALCULATOR =================
with tab_single:
    st.markdown("### **Interactive Activity Input**")
    st.write("Enter the annual activity data for a single facility to compute its scope-separated carbon footprint.")

    # Form/Inputs
    col_meta1, col_meta2 = st.columns(2)
    with col_meta1:
        facility_name = st.text_input("Facility Name", value="Springfield Assembly Plant")
    with col_meta2:
        reporting_year = st.number_input("Reporting Calendar Year", min_value=2000, max_value=2100, value=2025, step=1)

    st.markdown("#### **Activity Data**")
    col_input1, col_input2, col_input3 = st.columns(3)

    with col_input1:
        st.markdown("**Scope 1: Direct Fuels**")
        ng_val = st.number_input(
            "Natural Gas (therms)", 
            min_value=0.0, 
            value=12500.0, 
            step=100.0,
            help="Typically sourced from monthly utility gas bills."
        )
    with col_input2:
        st.markdown("**Scope 1: Fleet/Onsite Fuel**")
        diesel_val = st.number_input(
            "Diesel Fuel (gallons)", 
            min_value=0.0, 
            value=1400.0, 
            step=50.0,
            help="Sourced from fuel purchasing logs or generator runtime tracking."
        )
    with col_input3:
        st.markdown("**Scope 2: Purchased Utility**")
        elec_val = st.number_input(
            "Purchased Electricity (kWh)", 
            min_value=0.0, 
            value=245000.0, 
            step=1000.0,
            help="Sourced from monthly commercial electricity bills."
        )
        selected_egrid_label = st.selectbox(
            "Electricity eGRID subregion",
            options=list(egrid_label_to_code.keys()),
            index=default_egrid_index,
            help=(
                "Select the EPA eGRID subregion for location-based Scope 2 "
                "electricity estimates. Use US average when the facility region is unknown."
            ),
        )
        selected_egrid_code = egrid_label_to_code[selected_egrid_label]
        selected_egrid_factor = egrid_factors[selected_egrid_code]
        st.caption(
            f"Using {selected_egrid_code}: {selected_egrid_factor.factor_value:.6f} "
            "MT CO2e/kWh from EPA eGRID2023 Revision 2."
        )

    # Perform calculation
    activity_dict = {
        "natural_gas": ng_val,
        "diesel_fuel": diesel_val,
        "electricity": elec_val
    }

    try:
        selected_factors = with_egrid_electricity_factor(
            factors, egrid_factors, selected_egrid_code
        )
        results = calculate_inventory(
            activity_dict,
            selected_factors,
            factor_file=scope12_factor_file_map,
        )
        summary = summarize_by_scope(facility_name, reporting_year, results)
        
        # Display Premium Metrics Dashboard
        st.markdown("---")
        st.markdown("### **Calculated Emissions Inventory**")
        
        # Injected Custom Metrics (HTML/CSS)
        st.markdown(
            f"""
            <div class="metric-container">
                <div class="metric-card">
                    <div class="metric-label">Scope 1 (Direct)</div>
                    <div class="metric-value-s1">{summary.scope_1_total:,.3f}</div>
                    <div class="metric-meta" style="color: #F59E0B;">
                        MT CO₂e • <b>{summary.scope_1_percentage}%</b> of total
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Scope 2 (Indirect)</div>
                    <div class="metric-value-s2">{summary.scope_2_total:,.3f}</div>
                    <div class="metric-meta" style="color: #3B82F6;">
                        MT CO₂e • <b>{summary.scope_2_percentage}%</b> of total
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Grand Total Carbon Footprint</div>
                    <div class="metric-value-total">{summary.grand_total:,.3f}</div>
                    <div class="metric-meta" style="color: #10B981;">
                        Metric Tons CO₂e
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Split Details & Charts
        col_table, col_chart = st.columns([3, 2])
        
        with col_table:
            st.markdown("#### **Emissions Breakdown Table**")
            
            # Format results into a beautiful DataFrame
            results_data = []
            for r in results:
                name_formatted = r.activity_type.replace('_', ' ').title()
                results_data.append({
                    "Emission Source": name_formatted,
                    "Scope": f"Scope {r.scope}",
                    "Activity Amount": f"{r.activity_value:,.1f}",
                    "Activity Unit": r.input_unit,
                    "Emissions (MT CO₂e)": round(r.emissions_mt_co2e, 4),
                    "Emission Factor": f"{r.factor_value:.6f}",
                    "Factor Unit": r.factor_unit,
                    "Factor Source": r.source_name
                })
            
            df_results = pd.DataFrame(results_data)
            st.dataframe(df_results, width="stretch", hide_index=True)

            # Export individual results to CSV
            csv_buffer = io.StringIO()
            # Construct a complete, downloadable report format carrying full factor provenance
            report_df = pd.DataFrame({
                "facility_name": [summary.facility_name] * len(results),
                "reporting_year": [summary.reporting_year] * len(results),
                "activity_type": [r.activity_type for r in results],
                "scope": [r.scope for r in results],
                "activity_value": [r.activity_value for r in results],
                "input_unit": [r.input_unit for r in results],
                "factor_value": [r.factor_value for r in results],
                "factor_unit": [r.factor_unit for r in results],
                "factor_source": [r.source_name for r in results],
                "factor_year": [r.factor_year for r in results],
                "factor_file": [r.factor_file for r in results],
                "emissions_mt_co2e": [r.emissions_mt_co2e for r in results]
            })
            report_df.to_csv(csv_buffer, index=False)
            
            st.download_button(
                label="📥 Download Detailed CSV Report",
                data=csv_buffer.getvalue(),
                file_name=f"{summary.facility_name.lower().replace(' ', '_')}_emissions_report_{summary.reporting_year}.csv",
                mime="text/csv"
            )
            
        with col_chart:
            st.markdown("#### **Scope Share Visualization**")
            
            if summary.grand_total > 0:
                # 1. Donut Chart for Scope 1 vs Scope 2
                labels = ['Scope 1 (Direct)', 'Scope 2 (Indirect)']
                values = [summary.scope_1_total, summary.scope_2_total]
                colors = ['#EF4444', '#3B82F6']
                
                fig_donut = go.Figure(data=[go.Pie(
                    labels=labels, 
                    values=values, 
                    hole=.4,
                    marker=dict(colors=colors, line=dict(color='#0e1117', width=2))
                )])
                
                fig_donut.update_layout(
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5),
                    margin=dict(t=10, b=10, l=10, r=10),
                    height=240,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)"
                )
                st.plotly_chart(fig_donut, width="stretch")

                # 2. Source breakdown bar chart
                source_names = [r.activity_type.replace('_', ' ').title() for r in results]
                source_emissions = [r.emissions_mt_co2e for r in results]
                source_scopes = [f"Scope {r.scope}" for r in results]
                
                fig_bar = px.bar(
                    x=source_emissions,
                    y=source_names,
                    color=source_scopes,
                    orientation='h',
                    labels={'x': 'Emissions (MT CO₂e)', 'y': 'Source', 'color': 'Boundary'},
                    color_discrete_map={'Scope 1': '#F59E0B', 'Scope 2': '#3B82F6'}
                )
                fig_bar.update_layout(
                    margin=dict(t=20, b=10, l=10, r=10),
                    height=200,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
                    yaxis=dict(showgrid=False)
                )
                st.plotly_chart(fig_bar, width="stretch")
            else:
                st.info("Enter positive values above to generate interactive emissions visualizations.")

    except ValueError as e:
        st.error(f"⚠️ Calculation Input Error: {str(e)}")

# ================= TAB 2: BULK CSV PROCESSING =================
with tab_bulk:
    st.markdown("### **Bulk Emissions Processing & Multi-Facility Reporting**")
    st.write("Upload a CSV file containing activity data for multiple facilities to run calculations in batch mode.")

    # 1. Download Template Utility
    st.markdown("#### **Step 1: Download Activity Template**")
    st.write("Format your facility activity data according to this schema:")
    
    # Render an example table for reference
    template_example = pd.DataFrame({
        "facility_name": ["Springfield Manufacturing", "Shelbyville Logistics"],
        "reporting_year": [2025, 2025],
        "natural_gas_therms": [12450.5, 4820.0],
        "diesel_fuel_gallons": [1420.0, 18500.2],
        "electricity_kwh": [245800.0, 112500.0],
        "egrid_subregion": ["US", "CAMX"]
    })
    st.dataframe(template_example, width="stretch", hide_index=True)
    st.caption(
        "`egrid_subregion` is optional. If omitted, the default selected below is used."
    )
    
    # Download button for actual template
    csv_template_buffer = io.StringIO()
    template_example.to_csv(csv_template_buffer, index=False)
    st.download_button(
        label="📥 Download Template CSV",
        data=csv_template_buffer.getvalue(),
        file_name="facility_emissions_template.csv",
        mime="text/csv"
    )

    st.markdown("---")
    st.markdown("#### **Step 2: Upload Completed Activity Data**")
    bulk_default_egrid_label = st.selectbox(
        "Default eGRID subregion for bulk rows",
        options=list(egrid_label_to_code.keys()),
        index=default_egrid_index,
        help="Used when an uploaded CSV does not include egrid_subregion or leaves it blank.",
        key="bulk_egrid_subregion",
    )
    bulk_default_egrid_code = egrid_label_to_code[bulk_default_egrid_label]
    
    uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])
    
    if uploaded_file is not None:
        try:
            df_upload = pd.read_csv(uploaded_file)
            
            # Simple column verification
            required_cols = {"facility_name", "reporting_year", "natural_gas_therms", "diesel_fuel_gallons", "electricity_kwh"}
            missing_cols = required_cols - set(df_upload.columns)
            
            if missing_cols:
                st.error(f"❌ Uploaded CSV is missing required columns: {', '.join(missing_cols)}")
            else:
                st.success("CSV uploaded and required columns validated.")
                
                # Perform batch calculation
                processed_rows = []
                detailed_ledger_rows = []
                comparison_data = []
                bulk_warnings = []
                
                for idx, row in df_upload.iterrows():
                    facility = str(row["facility_name"])
                    year = int(row["reporting_year"])
                    raw_subregion = (
                        row["egrid_subregion"]
                        if "egrid_subregion" in df_upload.columns
                        and not pd.isna(row["egrid_subregion"])
                        else bulk_default_egrid_code
                    )
                    row_egrid_code = normalize_egrid_subregion(raw_subregion)
                    if row_egrid_code not in egrid_factors:
                        bulk_warnings.append(
                            f"Row {idx + 1} facility '{facility}' used unknown eGRID "
                            f"subregion '{raw_subregion}'. Falling back to {bulk_default_egrid_code}."
                        )
                        row_egrid_code = bulk_default_egrid_code
                    
                    try:
                        row_activities = {
                            "natural_gas": float(row["natural_gas_therms"]) if not pd.isna(row["natural_gas_therms"]) else 0.0,
                            "diesel_fuel": float(row["diesel_fuel_gallons"]) if not pd.isna(row["diesel_fuel_gallons"]) else 0.0,
                            "electricity": float(row["electricity_kwh"]) if not pd.isna(row["electricity_kwh"]) else 0.0
                        }
                    except ValueError as ve:
                        st.error(f"❌ Row {idx + 1} for '{facility}' has invalid numeric data: {ve}")
                        continue
                    
                    try:
                        row_factors = with_egrid_electricity_factor(
                            factors, egrid_factors, row_egrid_code
                        )
                        res_list = calculate_inventory(
                            row_activities,
                            row_factors,
                            factor_file=scope12_factor_file_map,
                        )
                        sum_res = summarize_by_scope(facility, year, res_list)
                    except Exception as calc_err:
                        st.error(f"❌ Row {idx + 1} for '{facility}' calculation error: {calc_err}")
                        continue
                    
                    processed_rows.append({
                        "Facility Name": sum_res.facility_name,
                        "Reporting Year": sum_res.reporting_year,
                        "Natural Gas (therms)": row_activities["natural_gas"],
                        "Diesel (gallons)": row_activities["diesel_fuel"],
                        "Electricity (kWh)": row_activities["electricity"],
                        "eGRID Subregion": row_egrid_code,
                        "Scope 1 (MT CO₂e)": sum_res.scope_1_total,
                        "Scope 2 (MT CO₂e)": sum_res.scope_2_total,
                        "Total (MT CO₂e)": sum_res.grand_total,
                        "Scope 1 %": sum_res.scope_1_percentage,
                        "Scope 2 %": sum_res.scope_2_percentage
                    })
                    
                    # Generate row-by-row provenance details for every activity in this facility
                    for r in res_list:
                        detailed_ledger_rows.append({
                            "facility_name": sum_res.facility_name,
                            "reporting_year": sum_res.reporting_year,
                            "activity_type": r.activity_type,
                            "scope": r.scope,
                            "egrid_subregion": row_egrid_code if r.activity_type == "electricity" else "",
                            "activity_value": r.activity_value,
                            "input_unit": r.input_unit,
                            "factor_value": r.factor_value,
                            "factor_unit": r.factor_unit,
                            "factor_source": r.source_name,
                            "factor_year": r.factor_year,
                            "factor_file": r.factor_file,
                            "emissions_mt_co2e": r.emissions_mt_co2e
                        })
                    
                    # Chart structuring
                    comparison_data.append({
                        "Facility": sum_res.facility_name,
                        "Emissions": sum_res.scope_1_total,
                        "Scope": "Scope 1 (Direct)"
                    })
                    comparison_data.append({
                        "Facility": sum_res.facility_name,
                        "Emissions": sum_res.scope_2_total,
                        "Scope": "Scope 2 (Indirect)"
                    })
                
                df_processed = pd.DataFrame(processed_rows)
                df_ledger = pd.DataFrame(detailed_ledger_rows)
                df_comparison = pd.DataFrame(comparison_data)
                
                st.markdown("#### **Calculated Batch Inventories**")
                if bulk_warnings:
                    st.warning("Some rows used fallback eGRID subregions.")
                    for warning in bulk_warnings:
                        st.write(f"- {warning}")
                st.dataframe(df_processed, width="stretch", hide_index=True)
                
                # Dual download options using Streamlit grid
                col_dl1, col_dl2 = st.columns(2)
                with col_dl1:
                    csv_batch_buffer = io.StringIO()
                    df_processed.to_csv(csv_batch_buffer, index=False)
                    st.download_button(
                        label="📥 Download Facility Summaries CSV",
                        data=csv_batch_buffer.getvalue(),
                        file_name="batch_calculated_facility_summaries.csv",
                        mime="text/csv",
                        key="dl_summary"
                    )
                with col_dl2:
                    csv_ledger_buffer = io.StringIO()
                    df_ledger.to_csv(csv_ledger_buffer, index=False)
                    st.download_button(
                        label="📥 Download Detailed Master Ledger CSV",
                        data=csv_ledger_buffer.getvalue(),
                        file_name="batch_calculated_detailed_ledger.csv",
                        mime="text/csv",
                        key="dl_ledger"
                    )
                
                # Multi-facility comparison chart
                st.markdown("---")
                st.markdown("#### **Multi-Facility Comparison Chart**")
                
                fig_comp = px.bar(
                    df_comparison,
                    x="Facility",
                    y="Emissions",
                    color="Scope",
                    title="Emissions Comparison by Boundary & Facility",
                    labels={"Emissions": "Metric Tons CO₂e", "Facility": "Facility Name"},
                    color_discrete_map={"Scope 1 (Direct)": "#EF4444", "Scope 2 (Indirect)": "#3B82F6"},
                    barmode="stack"
                )
                fig_comp.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    xaxis=dict(showgrid=False),
                    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)")
                )
                st.plotly_chart(fig_comp, width="stretch")

        except Exception as e:
            st.error(f"❌ Failed to process uploaded CSV: {str(e)}. Please check columns and formatting.")

# ================= TAB 3: SCOPE 3 SUPPLY CHAIN =================
with tab_scope3:
    st.markdown("### **Scope 3 Category 1: Purchased Goods & Services**")
    st.markdown(
        """
        <div class="info-container">
            <div class="info-title">💡 Spend-Based Screening Methodology</div>
            <div class="info-text">
                This module implements a spend-based greenhouse gas estimation model utilizing emission factors from the 
                <b>EPA Supply Chain GHG Emission Factors v1.2</b> (published 2023, based on 2019 environmental data). 
                Calculations utilize standard <b>SEF+MEF</b> (Supply Chain Emission Factor + Margins Emission Factor) coefficients 
                in terms of <i>kg CO2e per 2021 USD</i>. Spend values represent <b>provenance-friendly screening estimates</b> 
                for prioritization, not supplier-specific primary-data accounting.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("#### **Step 1: Download Purchase Ledger Template**")
    st.write("Format your organizational procurement spend registers using this structure:")
    
    # Render sample DataFrame
    scope3_template_df = pd.DataFrame({
        "facility_name": ["Clear Lake Lab", "Clear Lake Lab", "Clear Lake Lab", "Clear Lake Lab"],
        "reporting_year": [2026, 2026, 2026, 2026],
        "supplier_name": ["Lab Supplier A", "Office Vendor B", "Cloud Provider C", "Furniture Depot"],
        "purchase_category": ["laboratory_supplies", "office_supplies", "software_services", "office_furniture"],
        "amount_spent_usd": [2500.0, 800.0, 1200.0, 1500.0],
        "factor_key": ["laboratory_supplies", "office_supplies", "software_services", "office_furniture"]
    })
    st.dataframe(scope3_template_df, width="stretch", hide_index=True)

    # Download template button
    csv_s3_template_buffer = io.StringIO()
    scope3_template_df.to_csv(csv_s3_template_buffer, index=False)
    st.download_button(
        label="📥 Download Scope 3 Purchases Template CSV",
        data=csv_s3_template_buffer.getvalue(),
        file_name="scope3_purchases_template.csv",
        mime="text/csv",
        key="s3_template_dl"
    )

    st.markdown("---")
    st.markdown("#### **Step 2: Upload Procurement Registers**")
    s3_uploaded_file = st.file_uploader("Upload purchases CSV file", type=["csv"], key="s3_uploader")

    if s3_uploaded_file is not None:
        try:
            df_s3 = pd.read_csv(s3_uploaded_file)
            
            required_s3_cols = {"facility_name", "reporting_year", "supplier_name", "purchase_category", "amount_spent_usd", "factor_key"}
            missing_s3_cols = required_s3_cols - set(df_s3.columns)
            
            if missing_s3_cols:
                st.error(f"❌ Uploaded CSV is missing required columns: {', '.join(missing_s3_cols)}")
            else:
                st.success("Scope 3 ledger uploaded. Mapping status is summarized below.")
                
                # Parse rows and calculate
                purchase_records = []
                for idx, row in df_s3.iterrows():
                    purchase_records.append({
                        "facility_name": str(row["facility_name"]),
                        "reporting_year": int(row["reporting_year"]),
                        "supplier_name": str(row["supplier_name"]),
                        "purchase_category": str(row["purchase_category"]),
                        "amount_spent_usd": float(row["amount_spent_usd"]) if not pd.isna(row["amount_spent_usd"]) else 0.0,
                        "factor_key": str(row["factor_key"]) if not pd.isna(row["factor_key"]) else ""
                    })
                
                s3_filename = os.path.basename(SCOPE3_FACTORS_PATH)
                s3_summary = calculate_scope3_inventory(purchase_records, scope3_factors, factor_file=s3_filename)
                
                # Dashboard Metrics (HTML/CSS)
                st.markdown("---")
                st.markdown("### **Calculated Scope 3 Emissions & Mapping Metrics**")
                
                st.markdown(
                    f"""
                    <div class="metric-container">
                        <div class="metric-card">
                            <div class="metric-label">Grand Total Scope 3</div>
                            <div class="metric-value-total">{s3_summary.grand_total_emissions:,.3f}</div>
                            <div class="metric-meta" style="color: #10B981;">
                                Metric Tons CO₂e (Category 1)
                            </div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Mapped Spend (SEF+MEF Mapped)</div>
                            <div class="metric-value-s2">${s3_summary.mapped_spend:,.2f}</div>
                            <div class="metric-meta" style="color: #3B82F6;">
                                <b>{s3_summary.percent_spend_mapped}%</b> of total spend mapped
                            </div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-label">Unmapped Spend (Screening Warnings)</div>
                            <div class="metric-value-s1" style="background: linear-gradient(135deg, #EF4444 0%, #F59E0B 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                                ${s3_summary.unmapped_spend:,.2f}
                            </div>
                            <div class="metric-meta" style="color: #F59E0B;">
                                Excluded from total emissions
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # Warnings Block
                if s3_summary.warnings:
                    st.warning("⚠️ **Mapping & Validation Warnings Detected**")
                    for warn in s3_summary.warnings:
                        st.write(f"- {warn}")

                # Splits Table & Charts
                col_s3_table, col_s3_charts = st.columns([3, 2])
                
                with col_s3_table:
                    st.markdown("#### **Purchase Ledger Calculation View**")
                    s3_display_rows = []
                    for r in s3_summary.results:
                        s3_display_rows.append({
                            "Supplier": r.supplier_name,
                            "Purchase Category": r.purchase_category.replace('_', ' ').title(),
                            "Spend (USD)": f"${r.amount_spent_usd:,.2f}",
                            "Calculation Status": r.calculation_status.replace('_', ' ').title(),
                            "Emissions (MT CO₂e)": round(r.emissions_mt_co2e, 4),
                            "Factor Value (kg CO₂e/$)": f"{r.factor_value:.4f}",
                            "Model Version": r.factor_source
                        })
                    st.dataframe(pd.DataFrame(s3_display_rows), width="stretch", hide_index=True)
                    
                    # Download full ledger
                    csv_s3_ledger_buffer = io.StringIO()
                    s3_ledger_export_rows = []
                    for r in s3_summary.results:
                        s3_ledger_export_rows.append({
                            "facility_name": r.facility_name,
                            "reporting_year": r.reporting_year,
                            "supplier_name": r.supplier_name,
                            "purchase_category": r.purchase_category,
                            "amount_spent_usd": r.amount_spent_usd,
                            "factor_key": r.factor_key,
                            "emissions_mt_co2e": r.emissions_mt_co2e,
                            "calculation_status": r.calculation_status,
                            "included_in_total": r.included_in_total,
                            "warning": r.warning,
                            "factor_value": r.factor_value,
                            "factor_unit": r.factor_unit,
                            "factor_source": r.factor_source,
                            "factor_year": r.factor_year,
                            "factor_file": r.factor_file
                        })
                    pd.DataFrame(s3_ledger_export_rows).to_csv(csv_s3_ledger_buffer, index=False)
                    st.download_button(
                        label="📥 Download Detailed Scope 3 Ledger CSV",
                        data=csv_s3_ledger_buffer.getvalue(),
                        file_name=f"scope3_detailed_calculations_ledger.csv",
                        mime="text/csv",
                        key="s3_ledger_dl"
                    )

                with col_s3_charts:
                    st.markdown("#### **Scope 3 Category Share Analysis**")
                    
                    if s3_summary.grand_total_emissions > 0:
                        # Category chart
                        cat_names = list(s3_summary.total_by_category.keys())
                        cat_emissions = list(s3_summary.total_by_category.values())
                        fig_cat = px.bar(
                            x=cat_emissions,
                            y=[c.replace('_', ' ').title() for c in cat_names],
                            orientation='h',
                            labels={'x': 'Emissions (MT CO₂e)', 'y': 'Category'},
                            title="Scope 3 Emissions by Commodity Category",
                            color_discrete_sequence=['#10B981']
                        )
                        fig_cat.update_layout(
                            height=220,
                            margin=dict(t=30, b=10, l=10, r=10),
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
                        )
                        st.plotly_chart(fig_cat, width="stretch")

                        # Supplier chart
                        sup_names = list(s3_summary.total_by_supplier.keys())
                        sup_emissions = list(s3_summary.total_by_supplier.values())
                        fig_sup = px.bar(
                            x=sup_emissions,
                            y=sup_names,
                            orientation='h',
                            labels={'x': 'Emissions (MT CO₂e)', 'y': 'Supplier'},
                            title="Scope 3 Emissions by Supplier",
                            color_discrete_sequence=['#3B82F6']
                        )
                        fig_sup.update_layout(
                            height=220,
                            margin=dict(t=30, b=10, l=10, r=10),
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
                        )
                        st.plotly_chart(fig_sup, width="stretch")
                    else:
                        st.info("Ensure positive mapped purchase spend is uploaded to generate Scope 3 charts.")
                        
        except Exception as e:
            st.error(f"❌ Failed to process purchases CSV: {str(e)}. Please check structure.")

# ================= TAB 4: EMISSION FACTORS LIBRARY =================
with tab_factors:
    st.markdown("### **Active Emission Factors Library**")
    st.write(
        "Greenhouse gas emissions are computed dynamically using local JSON factor libraries with source notes. "
        "Each conversion factor includes source notes and metadata to help reviewers trace calculation assumptions."
    )

    for act_name, fact in factors.items():
        scope_lbl = "Scope 1 (Direct)" if fact.scope == 1 else "Scope 2 (Purchased Utilities)"
        card_color = "#F59E0B" if fact.scope == 1 else "#3B82F6"
        
        with st.container():
            st.markdown(
                f"""
                <div style="border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 1.2rem; margin-bottom: 1.2rem; background-color: rgba(255,255,255,0.02)">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <span style="font-size: 1.2rem; font-weight: 600; text-transform: capitalize;">{act_name.replace('_', ' ')}</span>
                        <span style="background-color: {card_color}22; color: {card_color}; font-size: 0.8rem; font-weight: 600; padding: 4px 10px; border-radius: 20px; border: 1px solid {card_color}44;">
                            {scope_lbl}
                        </span>
                    </div>
                    <div style="display: flex; gap: 2rem; margin: 0.8rem 0;">
                        <div>
                            <div style="font-size: 0.75rem; color: #888888; text-transform: uppercase;">Emission Factor</div>
                            <div style="font-size: 1.3rem; font-weight: 700; color: #FFFFFF;">{fact.factor_value:.6f}</div>
                            <div style="font-size: 0.75rem; color: #888888;">{fact.factor_unit}</div>
                        </div>
                        <div>
                            <div style="font-size: 0.75rem; color: #888888; text-transform: uppercase;">Reporting Gas Basis</div>
                            <div style="font-size: 1.3rem; font-weight: 700; color: #10B981;">{fact.gas_basis}</div>
                            <div style="font-size: 0.75rem; color: #888888;">Global Warming Potential</div>
                        </div>
                    </div>
                    <div style="font-size: 0.85rem; color: #E5E7EB; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 0.8rem; margin-top: 0.8rem;">
                        <b>Source Reference:</b> {fact.source_reference} ({fact.source_year})<br>
                        <b>Accounting Logic / Notes:</b> {fact.notes}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    with st.expander("EPA eGRID2023 Revision 2 Subregion Electricity Factors"):
        st.write(
            "These factors replace the generic electricity factor when a user selects an "
            "eGRID subregion. EPA publishes the source rates in lb CO2e/MWh; the app "
            "converts them to metric tons CO2e/kWh for consistency with the rest of the inventory."
        )
        egrid_rows = []
        for code in egrid_options:
            fact = egrid_factors[code]
            display_name = fact.source_name.split(f"{code} ", 1)[-1]
            egrid_rows.append({
                "Subregion": code,
                "Name": display_name,
                "Factor (MT CO2e/kWh)": round(fact.factor_value, 9),
                "Source Year": fact.source_year,
                "Factor File": egrid_factor_filename,
            })
        st.dataframe(pd.DataFrame(egrid_rows), width="stretch", hide_index=True)

# ================= TAB 4: SCOPE & LIMITATIONS =================
with tab_limitations:
    st.markdown("### **Greenhouse Gas Protocol Accounting Boundary & Limitations**")
    
    # GHG Boundary Diagram
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/e/e6/Greenhouse_Gas_Protocol_Scopes.jpg", 
        caption="GHG Protocol standard scopes defining direct (Scope 1) and indirect (Scope 2) boundaries.",
        width="stretch"
    )
    
    # 1. Mandatory Disclaimer Block (Rich Aesthetic Styling)
    st.markdown(
        """
        <div class="disclaimer-container">
            <div class="disclaimer-title">
                <span>⚠️</span> IMPORTANT PROTOCOL & COMPLIANCE DISCLAIMER
            </div>
            <div class="disclaimer-text">
                “This prototype is intended for learning, portfolio demonstration, and early facility screening. 
                It is not a certified greenhouse gas inventory tool. Emission factors, organizational boundaries, 
                market-based Scope 2 claims, renewable energy certificates, and reporting requirements must be reviewed 
                against current guidance before formal reporting.”
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 2. Accounting Formula & Boundary Explanation
    st.markdown(
        """
        #### **Greenhouse Gas Accounting Formulation**
        Emissions calculations are based on the standard accounting guidelines published by the Greenhouse Gas Protocol:
        
        $$\\text{Activity Data} \\times \\text{Emission Factor} = \\text{Greenhouse Gas Emissions (MT } CO_2e)$$
        
        Where:
        - **Activity Data**: Quantified consumption metrics representing facility operations (e.g., utility invoices, fuel logs, purchase records).
        - **Emission Factor**: Standard coefficient converting activity volumes to equivalent metric tons of carbon dioxide ($CO_2$), methane ($CH_4$), and nitrous oxide ($N_2O$) emissions using Global Warming Potentials (GWPs).
        
        #### **MVP Assumptions and Defaults**
        1. **Scope 1 Stationary Combustion (Natural Gas & Diesel)**: Factored assuming stationary boiler, furnace, or generator usage. Grid-losses, supply-chain leakage, or upstream extraction boundaries (Scope 3) are excluded.
        2. **Scope 2 Purchased Electricity**: Calculated using the **Location-based method** representing physical grid emissions. Renewable energy certificates (RECs), power purchase agreements (PPAs), or supplier-specific fuel mixes (**Market-based method**) are not reflected.
        3. **Equivalency GWPs**: Uses the Intergovernmental Panel on Climate Change (IPCC) Fifth Assessment Report (AR5) 100-year Global Warming Potentials to represent methane and nitrous oxide impacts in terms of $CO_2$ equivalence ($CO_2e$).
        """
    )
