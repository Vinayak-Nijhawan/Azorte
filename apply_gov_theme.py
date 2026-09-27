import os
import re

with open('assets/style.css', 'r', encoding='utf-8') as f:
    css = f.read()

# 1. Fix the fd-header gradient that is hardcoded dark
css = css.replace(
    'background: linear-gradient(135deg, rgba(59,130,246,0.08) 0%, rgba(13,17,23,0.7) 60%) !important;',
    'background: linear-gradient(135deg, color-mix(in srgb, var(--primary-color) 8%, transparent) 0%, var(--secondary-background-color) 100%) !important;'
)

# 2. Add an Indian Govt specific aesthetic using a media query for light mode
# This will inject saffron and green accents in light mode to make it feel like a Gov portal.
# We will add a decorative top border to the whole app in light mode:
gov_theme_css = """
/* ================================================================
   INDIAN GOVERNMENT THEME (LIGHT MODE)
   ================================================================ */
@media (prefers-color-scheme: light) {
    /* Tricolor Top Bar */
    header[data-testid="stHeader"] {
        border-top: 4px solid #FF9933;
        box-shadow: inset 0 4px 0 0 #FFFFFF, inset 0 8px 0 0 #138808;
        background: rgba(255, 255, 255, 0.9) !important;
    }
    
    /* Elegant Sidebar Logo for Gov */
    .sb-logo-icon {
        background: linear-gradient(135deg, #FF9933 0%, #138808 100%) !important;
        box-shadow: 0 4px 14px rgba(19, 136, 8, 0.2) !important;
    }
    
    .sb-logo-title {
        color: #000080 !important; /* Navy Blue Ashoka Chakra */
    }
    
    /* Tweak primary buttons in light mode to look more official */
    .stButton > button {
        background: #000080 !important;
        color: white !important;
    }
    .stButton > button:hover {
        background: #FF9933 !important;
        color: white !important;
    }
    
    /* Make metric cards pop out on white background */
    [data-testid="stMetric"] {
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
        border: 1px solid rgba(0, 0, 0, 0.1) !important;
        background: #FFFFFF !important;
    }
    
    .fd-header {
        border-left: 4px solid #FF9933 !important;
    }
}
"""

if "INDIAN GOVERNMENT THEME" not in css:
    css += "\n" + gov_theme_css

with open('assets/style.css', 'w', encoding='utf-8') as f:
    f.write(css)

# Also update config.toml to force the base light theme to be navy blue/professional
config_path = '.streamlit/config.toml'
if os.path.exists(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = f.read()
    
    if '[theme]' not in config:
        config += """
[theme]
base="light"
primaryColor="#000080"
backgroundColor="#F9FAFB"
secondaryBackgroundColor="#FFFFFF"
textColor="#111827"
font="sans serif"
"""
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config)
