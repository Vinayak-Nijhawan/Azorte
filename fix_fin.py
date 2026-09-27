import os

with open('src/pages/09_financial.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_func = '''def render_animated_kpi_row(kpi_list):
    cards_html = \"\"\"<div class=\"geo-kpi-grid\">\"\"\"
    
    for kpi in kpi_list:
        val = kpi[\"value\"]
        prefix = kpi.get(\"prefix\", \"\")
        suffix = kpi.get(\"suffix\", \"\")
        decimals = kpi.get(\"decimals\", 2)
        
        if kpi.get(\"is_money\", False):
            prefix = \"?\"
            if val >= 1e7:
                val = val / 1e7
                suffix = \" Cr\"
            elif val >= 1e5:
                val = val / 1e5
                suffix = \" Lakh\"
            else:
                decimals = 0
        
        formatted_val = f\"{val:,.{decimals}f}\" if decimals > 0 else f\"{val:,.0f}\"
        
        badge_html = \"\"
        if kpi.get(\"badge\"):
            b_color = kpi.get(\"badge_color\", \"badge-green\")
            trend_class = \"geo-trend-up\" if \"green\" in b_color else (\"geo-trend-down\" if \"red\" in b_color else \"geo-trend-neutral\")
            badge_html = f\"\"\"<div class=\"geo-kpi-footer\"><span class=\"{trend_class}\">{kpi['badge']}</span></div>\"\"\"
            
        cards_html += f\"\"\"
        <div class=\"geo-kpi-card\">
            <div class=\"geo-kpi-title\">{kpi['title']}</div>
            <div class=\"geo-kpi-value\">{prefix}{formatted_val}{suffix}</div>
            {badge_html}
        </div>
        \"\"\"
        
    cards_html += \"</div>\"
    import streamlit as st
    st.markdown(cards_html, unsafe_allow_html=True)
'''

with open('src/pages/09_financial.py', 'w', encoding='utf-8') as f:
    f.writelines(lines[:122])
    f.write(new_func + '\n')
    f.writelines(lines[216:])
