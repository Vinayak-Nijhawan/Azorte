import streamlit as st
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
        <h1>🤖 G-Sync AI Assistant</h1>
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
        return pd.read_csv(path)
    return None

df_prod = load_csv("production_dataset.csv")
df_prospect = load_csv("prospectivity_grid.csv")
df_forecast = load_csv("production_forecast.csv")
df_dispatch = load_csv("dispatch_plan.csv")
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
</style>
""", unsafe_allow_html=True)

if GROQ_AVAILABLE:
    env_key = os.environ.get("GROQ_API_KEY", "")
    if env_key and env_key != "your_api_key_here":
        st.sidebar.success("✅ Secure API Key loaded from environment.")
        api_key = env_key
    else:
        api_key = st.sidebar.text_input("Enter Groq API Key", type="password", help="Enter your Groq key to enable real LLM responses.")
else:
    st.sidebar.warning("Groq package not installed. Using rule-based fallback.")
    api_key = ""

# Helper for handling user input
def process_query(prompt):
    query = prompt.lower()
    
    # Context building
    ctx_mines = df_prod['mine_id'].nunique() if df_prod is not None else 0
    ctx_prospect = len(df_prospect[df_prospect['prospectivity_class'] == 'High']) if df_prospect is not None and 'prospectivity_class' in df_prospect.columns else 0
    
    if api_key:
        try:
            client = Groq(api_key=api_key)
            system_prompt = f"""You are G-Sync AI, an expert mining analytics assistant for MOIL-GeoSync.
            Current System Context:
            - Tracking {ctx_mines} active mines.
            - Identified {ctx_prospect} high prospectivity zones.
            Answer the user's query concisely and professionally based on this context and general mining knowledge.
            """
            
            # Format chat history for Groq
            messages = [{"role": "system", "content": system_prompt}]
            for msg in st.session_state.messages[-5:]: # Keep last 5 messages for context
                if msg["role"] in ["user", "assistant"]:
                    messages.append({"role": msg["role"], "content": msg["content"]})
                    
            messages.append({"role": "user", "content": prompt})
            
            chat_completion = client.chat.completions.create(
                messages=messages,
                model="openai/gpt-oss-20b",
            )
            return chat_completion.choices[0].message.content, None
        except Exception as e:
            return f"Error communicating with Groq API: {e}. Falling back to rule-based responses.", None
    
    # --- Fallback Rule-Based Engine ---
    # 1. Risk/Shortfall
    if any(k in query for k in ['risk', 'shortfall', 'danger', 'problem']):
        data_to_use = df_forecast if df_forecast is not None else df_prod
        if data_to_use is not None and 'shortfall_risk' in data_to_use.columns:
            high_risk = data_to_use[data_to_use['shortfall_risk'] == 'High']
            if not high_risk.empty:
                mines = high_risk['mine_id'].unique()
                response = f"Based on our MineFlow analysis, the following mines face high shortfall risk: {', '.join(mines)}."
                return response, high_risk[['mine_id', 'month', 'year', 'shortfall_risk']]
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
            summary = df_prod.groupby('mine_id')['actual_production_tpd'].mean().reset_index()
            summary = summary.sort_values(by='actual_production_tpd', ascending=False)
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
            heavy_rain = df_show[df_show['rainfall_mm'] > df_show['rainfall_mm'].mean()]
            return f"Weather impact analysis{' for ' + mine_filter if mine_filter else ''}: Heavy rainfall months show notable dips in equipment availability and production.", heavy_rain[['mine_id', 'month', 'rainfall_mm', 'actual_production_tpd']]
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
