import streamlit as st

import sys
import os
# Add the project root to sys.path so we can import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from utils import load_css, inject_kpi_animations, inject_volcano_animations
load_css()

import pandas as pd
import os

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

# Setup paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJECT_ROOT, '.env'), override=True)
except ImportError:
    pass

st.markdown("""
<div class="fd-header">
    <div class="fd-header-left">
        <h1><span class=\"material-symbols-rounded\">smart_toy</span> G-Sync AI Assistant</h1>
        <div class="fd-subtitle">Natural Language Analytics · Powered by Groq Llama-3</div>
    </div>
    <div class="fd-header-right">
        <div class="fd-tag">💬 Conversational AI</div>
        <div class="fd-live"><div class="fd-live-dot"></div> ONLINE</div>
    </div>
</div>
""", unsafe_allow_html=True)
st.markdown("Ask questions about mines, production, fleet, and prospectivity in natural language")

with st.expander("Example Queries"):
    st.markdown("""
    - 'Which mine has the highest shortfall risk?'
    - 'Show fleet alerts for Mine A'
    - 'How many high prospectivity zones are there?'
    - 'Compare production across all mines'
    - 'What is the system status?'
    - 'Show top 5 drill targets'
    - 'What is the weather impact on Mine B?'
    """)

# Load data
@st.cache_data
def load_csv(filename):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        return pd.read_csv(path, comment='#')
    return None

df_prod = load_csv("production_dataset_real.csv")
df_prospect = load_csv("prospectivity_final_real.csv")
if df_prospect is None:
    df_prospect = load_csv("prospectivity_grid.csv")
df_forecast = load_csv("production_forecast_real.csv")
df_dispatch = load_csv("dispatch_plan_real.csv")
if df_dispatch is None:
    df_dispatch = load_csv("dispatch_plan.csv")
df_alerts = load_csv("fleet_alerts_real.csv")
if df_alerts is None:
    df_alerts = load_csv("fleet_alerts.csv")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "Hello! I am your G-Sync AI Assistant. How can I help you with mine analytics today?"})

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "dataframe" in message:
            st.dataframe(message["dataframe"], use_container_width=True)

# Sidebar for API Key
st.sidebar.markdown("### 🧠 Smart AI Upgrade")

# CSS to forcibly hide the password reveal (eye) icon and prevent copying
st.sidebar.markdown("""
<style>
    /* Hide the Streamlit password visibility toggle */
    div[data-testid="stTextInput"] button,
    button[title="Show password text"],
    button[aria-label="Show password text"] {
        display: none !important;
        pointer-events: none !important;
        visibility: hidden !important;
    }
    /* Prevent selection of the input text */
    input[type="password"] {
        user-select: none !important;
        -webkit-user-select: none !important;
    }

        @media (prefers-color-scheme: light) {
            .kpi-card { background: #F3F4F6 !important; border-color: #E5E7EB !important; color: #111827 !important; }
            .kpi-card.highlight { background: linear-gradient(180deg, #F3F4F6 0%, #E5E7EB 100%) !important; }
            .kpi-title { color: #6B7280 !important; }
            .kpi-value { color: #111827 !important; }
            body { color: #111827; }
        }
        </style>

""", unsafe_allow_html=True)

if GROQ_AVAILABLE:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    env_key = os.environ.get("GROQ_API_KEY", "")
    if env_key and env_key != "your_api_key_here":
        st.sidebar.success("✅ Secure API Key loaded.")
        api_key = env_key
    else:
        api_key = st.sidebar.text_input("Enter Groq API Key", type="password", help="Enter your Groq key to enable real LLM responses.")
else:
    st.sidebar.warning("Groq package not installed. Using rule-based fallback.")
    api_key = ""

# Helper for handling user input
def process_query(prompt):
    query = prompt.lower()
    
    # ---- Build rich context from actual data ----
    ctx_mines = df_prod['mine_id'].nunique() if df_prod is not None else 0
    mine_list = ', '.join(df_prod['mine_id'].unique().tolist()) if df_prod is not None else 'N/A'

    # Per-mine avg production
    mine_stats = ""
    if df_prod is not None and 'derived_actual_production_tpd__DERIVED' in df_prod.columns:
        avg_tpd = df_prod.groupby('mine_id')['derived_actual_production_tpd__DERIVED'].mean()
        mine_stats = "\n".join([f"  - {m}: {v:.0f} TPD avg" for m, v in avg_tpd.items()])
    elif df_prod is not None and 'actual_production_tpd' in df_prod.columns:
        avg_tpd = df_prod.groupby('mine_id')['actual_production_tpd'].mean()
        mine_stats = "\n".join([f"  - {m}: {v:.0f} TPD avg" for m, v in avg_tpd.items()])

    # Prospectivity summary
    prosp_summary = ""
    if df_prospect is not None and 'prospectivity_class' in df_prospect.columns:
        counts = df_prospect['prospectivity_class'].value_counts()
        high_c = int(counts.get('High', 0))
        med_c = int(counts.get('Medium', 0))
        low_c = int(counts.get('Low', 0))
        prosp_summary = f"High: {high_c}, Medium: {med_c}, Low: {low_c} (Total: {len(df_prospect)} grid points)"

    # Forecast risk summary
    risk_summary = ""
    if df_forecast is not None and 'shortfall_risk' in df_forecast.columns:
        high_risk_mines = df_forecast[df_forecast['shortfall_risk'] == 'High']['mine_id'].unique().tolist()
        risk_summary = f"Mines with High shortfall risk in 2026 forecast: {', '.join(high_risk_mines) if high_risk_mines else 'None'}"

    if api_key:
        try:
            client = Groq(api_key=api_key)
            system_prompt = f"""You are G-Sync AI, the intelligent assistant for MOIL-GeoSync (G-Sync) - an AI-powered manganese mining intelligence platform built for MOIL Limited, India's largest manganese producer.

PROJECT CONTEXT:
- Built for Smart India Hackathon (SIH) 2026, Problem Statement 26009
- Team Azorte, led by Vinayak Nijhawan
- Platform modules: GeoProspect AI (mineral exploration), MineFlow Optimizer (production forecasting + fleet dispatch), Financial ROI Analysis

MOIL MINES TRACKED ({ctx_mines} mines, real data 2016-2025):
{mine_stats}

Mines: {mine_list}
- Balaghat (MP): Largest opencast mine, ~1028 TPD avg
- Dongri_Buzurg (MH): Largest underground mine, ~433 TPD avg
- Chikla, Munsar, Kandri, Gumgaon (MH): Nagpur-Bhandara belt
- Tirodi, Ukwa, Sitapatore, Beldongri (MP/MH): Smaller operations

GEOPROSPECT AI (Manganese Prospectivity Mapping):
- Study area: Nagpur-Bhandara-Balaghat manganese belt + MP regions
- {prosp_summary}
- Features: Sentinel-2 spectral indices (NDVI, Iron Oxide, Clay), GSI geology (rock_type, fault_distance_km), elevation, rainfall
- Model: PU Bagging Random Forest with Spatial Block Cross-Validation

MINEFLOW OPTIMIZER (Production Forecasting):
- Model: Gradient Boosting Regressor, R2 = 0.978, MAE = 18.13 TPD
- Forecasts 2026 production under 3 weather scenarios (Normal, High Rainfall, Low Rainfall)
- {risk_summary}
- Monsoon months (Jun-Sep) cause 15-30% production dips due to equipment availability and haul road degradation

FLEET DISPATCH:
- MILP (Mixed Integer Linear Programming) optimizer using Google OR-Tools
- Optimizes dumper-to-shovel assignment per mine per month
- Considers weather penalties, equipment availability, crusher capacity constraints

FINANCIAL ROI:
- Exploration savings: AI-guided drilling reduces 85 unnecessary boreholes (saves ~12.75 Cr)
- Production revenue protection via shortfall prediction
- Fleet optimization reduces idle costs and diesel consumption
- ESG: CO2 reduction from optimized routes, reduced deforestation from targeted exploration

INSTRUCTIONS:
- Answer in clean, professional language. Use proper paragraphs.
- NEVER output HTML tags like <br>, <p>, <div> etc. Use newlines for line breaks.
- Use markdown formatting (bold, bullet points, headers) for readability.
- When discussing specific mines, use their actual names from the data.
- Base answers on the real data context above. If asked something outside your data, say so clearly.
- Keep responses focused and concise (3-5 paragraphs max).
- All production numbers are in TPD (Tonnes Per Day).
"""
            
            # Format chat history for Groq
            messages = [{"role": "system", "content": system_prompt}]
            for msg in st.session_state.messages[-5:]:
                if msg["role"] in ["user", "assistant"]:
                    messages.append({"role": msg["role"], "content": msg["content"]})
                    
            messages.append({"role": "user", "content": prompt})
            
            chat_completion = client.chat.completions.create(
                messages=messages,
                model="openai/gpt-oss-20b",
            )
            response = chat_completion.choices[0].message.content
            # Clean any HTML tags that the LLM might generate
            response = response.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
            response = response.replace('<p>', '\n').replace('</p>', '\n')
            response = response.replace('<b>', '**').replace('</b>', '**')
            response = response.replace('<i>', '*').replace('</i>', '*')
            return response, None
        except Exception as e:
            return f"Error communicating with Groq API: {e}. Falling back to rule-based responses.", None
    
    # --- Fallback Rule-Based Engine ---
    # 1. Risk/Shortfall
    if any(k in query for k in ['risk', 'shortfall', 'danger', 'problem']):
        data_to_use = df_forecast if df_forecast is not None else df_prod
        if data_to_use is not None and 'shortfall_risk__DERIVED' in data_to_use.columns:
            high_risk = data_to_use[data_to_use['shortfall_risk__DERIVED'] == 'High']
            if not high_risk.empty:
                mines = high_risk['mine_id'].unique()
                response = f"Based on our MineFlow analysis, the following mines face high shortfall risk: {', '.join(mines)}."
                return response, high_risk[['mine_id', 'month', 'year', 'shortfall_risk__DERIVED']]
            else:
                return "Good news! Currently, no mines are flagged with high shortfall risk.", None
        return "I couldn't find risk forecast data.", None

    # 2. Fleet/Dumper/Shovel
    elif any(k in query for k in ['fleet', 'dumper', 'shovel', 'dispatch', 'assign']):
        if df_dispatch is not None:
            mine_filter = next((m for m in ['Mine_A', 'Mine_B', 'Mine_C'] if m.lower() in query), None)
            df_show = df_dispatch[df_dispatch['mine_id'] == mine_filter] if mine_filter else df_dispatch
            
            t_dumpers = df_show['assigned_dumpers'].sum() if 'assigned_dumpers' in df_show.columns else "N/A"
            t_shovels = df_show['assigned_shovels'].sum() if 'assigned_shovels' in df_show.columns else "N/A"
            
            response = f"Fleet Summary{' for ' + mine_filter if mine_filter else ''}: {t_dumpers} Dumpers, {t_shovels} Shovels assigned."
            return response, df_show
        elif df_prod is not None:
            t_dumpers = df_prod['num_dumpers'].sum()
            t_shovels = df_prod['num_shovels'].sum()
            return f"Total active fleet recorded: {t_dumpers} Dumpers, {t_shovels} Shovels.", None
        return "Fleet dispatch data is currently unavailable.", None

    # 3. Alert/Warning
    elif any(k in query for k in ['alert', 'warning', 'critical']):
        if df_alerts is not None:
            mine_filter = next((m for m in ['Mine_A', 'Mine_B', 'Mine_C'] if m.lower() in query), None)
            df_show = df_alerts[df_alerts['mine_id'] == mine_filter] if mine_filter else df_alerts
            if not df_show.empty:
                return f"Here are the latest fleet alerts{' for ' + mine_filter if mine_filter else ''}:", df_show
            return "No active alerts found.", None
        return "Alert data is currently unavailable.", None

    # 4. Prospectivity/Exploration
    elif any(k in query for k in ['prospect', 'explor', 'where', 'target', 'drill', 'manganese']):
        if df_prospect is not None:
            high_count = len(df_prospect[df_prospect['prospectivity_class'] == 'High'])
            targets = df_prospect.nlargest(5, 'mn_probability')[['latitude', 'longitude', 'mn_probability', 'prospectivity_class']]
            return f"There are {high_count} High Prospectivity zones identified. Here are the top 5 drill targets based on probability:", targets
        return "Prospectivity data is unavailable.", None
        
    # 5. Compare/Best/Worst
    elif any(k in query for k in ['compare', 'best', 'worst', 'rank']):
        if df_prod is not None:
            summary = df_prod.groupby('mine_id')['derived_actual_production_tpd__DERIVED'].mean().reset_index()
            summary = summary.sort_values(by='derived_actual_production_tpd__DERIVED', ascending=False)
            best_mine = summary.iloc[0]['mine_id']
            worst_mine = summary.iloc[-1]['mine_id']
            return f"Comparing production across mines: **{best_mine}** has the highest average production, while **{worst_mine}** has the lowest.", summary
        return "Production data unavailable for comparison.", None

    # 6. Summary/Overview/Status
    elif any(k in query for k in ['summary', 'overview', 'status', 'hello', 'hi']):
        total_pts = len(df_prospect) if df_prospect is not None else 0
        high_pts = len(df_prospect[df_prospect['prospectivity_class'] == 'High']) if df_prospect is not None else 0
        mines_count = df_prod['mine_id'].nunique() if df_prod is not None else 0
        return f"**System Status Overview:**\n- Tracking {mines_count} active mines.\n- Analyzed {total_pts} geographic coordinates.\n- Found {high_pts} High Prospectivity targets.\n\nAll modules are operational. What would you like to know?", None

    # 7. Weather/Rain/Monsoon
    elif any(k in query for k in ['weather', 'rain', 'monsoon']):
        if df_prod is not None:
            mine_filter = next((m for m in ['Mine_A', 'Mine_B', 'Mine_C'] if m.lower() in query), None)
            df_show = df_prod[df_prod['mine_id'] == mine_filter] if mine_filter else df_prod
            heavy_rain = df_show[df_show['rainfall_mm__REAL'] > df_show['rainfall_mm__REAL'].mean()]
            return f"Weather impact analysis{' for ' + mine_filter if mine_filter else ''}: Heavy rainfall months show notable dips in equipment availability and production.", heavy_rain[['mine_id', 'month', 'rainfall_mm__REAL', 'derived_actual_production_tpd__DERIVED']]
        return "Weather data unavailable.", None

    # 8. Help
    elif any(k in query for k in ['help', 'what can you do']):
        return "I can help with prospectivity analysis, production forecasting, fleet dispatch, and alerts. Try asking:\n- 'Which mine has the highest risk?'\n- 'Show top 5 drill targets'\n- 'Compare production across all mines'", None

    # Default
    return "I can help with prospectivity analysis, production forecasting, fleet dispatch, and alerts. Try asking: 'Which mine has the highest risk?' or type 'help' for more examples. Alternatively, enter a Groq API Key in the sidebar for true AI responses!", None


# Accept user input
if prompt := st.chat_input("Ask a question about the G-Sync system..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)

    response_text, response_df = process_query(prompt)
    
    msg_data = {"role": "assistant", "content": response_text}
    if response_df is not None:
        msg_data["dataframe"] = response_df
    
    st.session_state.messages.append(msg_data)
    
    with st.chat_message("assistant"):
        st.markdown(response_text)
        if response_df is not None:
            st.dataframe(response_df, use_container_width=True)


# --- Animations ---
inject_kpi_animations()
inject_volcano_animations()
