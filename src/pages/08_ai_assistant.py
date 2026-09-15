import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Setup paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

st.title("G-Sync AI Assistant 🤖")
st.markdown("Ask questions about mines, production, fleet, and prospectivity in natural language. Powered by **Groq Llama-3**.")

if not GROQ_API_KEY:
    st.error("GROQ_API_KEY not found in .env file. Please add it to use the AI Assistant.")
    st.stop()

# Initialize Groq Client
client = Groq(api_key=GROQ_API_KEY)

# Load context data
@st.cache_data
def load_csv(filename):
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()

df_prod = load_csv("production_dataset.csv")
df_prospect = load_csv("prospectivity_grid.csv")
df_forecast = load_csv("production_forecast.csv")

# Generate a smart context string based on the data
def get_system_context():
    context = "You are G-Sync AI, an expert mining analytics assistant for MOIL (Manganese Ore India Limited).\n"
    
    if not df_prod.empty:
        mines = df_prod['mine_id'].unique().tolist()
        avg_prod = df_prod['actual_production_tpd'].mean()
        context += f"- We are tracking {len(mines)} mines: {', '.join(mines)}.\n"
        context += f"- The average production across these mines is {avg_prod:.1f} Tonnes Per Day (TPD).\n"
        
    if not df_forecast.empty and 'shortfall_risk' in df_forecast.columns:
        high_risk = df_forecast[df_forecast['shortfall_risk'] == 'High']
        if not high_risk.empty:
            hr_mines = high_risk['mine_id'].unique().tolist()
            context += f"- ALERT: Currently facing 'High' shortfall risk in the forecast for: {', '.join(hr_mines)}.\n"
            
    if not df_prospect.empty and 'mn_probability' in df_prospect.columns:
        high_prob = len(df_prospect[df_prospect['mn_probability'] > 0.8])
        context += f"- AI Prospectivity model has identified {high_prob} high-probability (Prob > 0.8) target zones for new manganese drilling.\n"
        
    context += """
    Guidelines for answering:
    1. Be concise, professional, and helpful.
    2. Use the provided context to answer questions about the mines, risk, and prospectivity.
    3. If asked something outside this scope, gently remind the user that you are specialized in MOIL G-Sync operations.
    """
    return context

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "Hello! I am your G-Sync AI Assistant, powered by Groq. How can I help you with mine analytics today?"})

with st.expander("Example Queries"):
    st.markdown("""
    - 'Which mines are we tracking?'
    - 'Are there any high risk mines right now?'
    - 'How many drill targets has the AI found?'
    - 'What is the average production across our mines?'
    """)

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle user input
if prompt := st.chat_input("Ask a question about the G-Sync system..."):
    # Add user message to UI
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Call Groq API
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        # Build message history for the API
        api_messages = [{"role": "system", "content": get_system_context()}]
        
        # Add last 5 interactions to keep context window manageable
        for msg in st.session_state.messages[-5:]:
            api_messages.append({"role": msg["role"], "content": msg["content"]})
            
        try:
            response = client.chat.completions.create(
                model="qwen/qwen3.8-27b",
                messages=api_messages,
                temperature=0.3,
                max_tokens=500
            )
            full_response = response.choices[0].message.content
            message_placeholder.markdown(full_response)
            
            # Save assistant response
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"Error communicating with Groq API: {e}")
