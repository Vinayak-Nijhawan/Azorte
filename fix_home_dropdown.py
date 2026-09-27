import re

with open('src/pages/01_home.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_html = r'''# 1. Header Area
st.markdown\(\"\"\"
<div class=\"glass-panel modern-header\">
    <div class=\"header-titles\">
        <h1>MOIL-GeoSync \(G-Sync\)</h1>
        <p>AI-Powered Manganese Exploration & Production Optimization</p>
    </div>
    <div class=\"header-actions\">
        <div class=\"search-bar\">
            <span class=\\\"material-symbols-rounded\\\" style=\"vertical-align: middle; font-size: 1.2rem;\">search</span> Search modules or reports...
        </div>
        <div class=\"profile-action\">
            <div class=\"profile-avatar\">VN</div>
            <div class=\"profile-name\">Vinayak Nijhawan</div>
            <span style=\"color: color-mix\(in srgb, var\(--text-color\) 50%, transparent\); font-size: 0.8rem; margin-left: 4px;\">▼</span>
        </div>
    </div>
</div>
\"\"\", unsafe_allow_html=True\)'''

new_html = '''# Combine Header and KPI into ONE block to fix z-index clipping of the dropdown
st.markdown(f\"\"\"
<style>
details {{ position: relative; display: inline-block; }}
summary {{ list-style: none; cursor: pointer; display: flex; align-items: center; gap: 10px; outline: none; }}
summary::-webkit-details-marker {{ display: none; }}
.profile-dropdown-menu {{
    position: absolute; right: 0; top: 100%; margin-top: 10px;
    background: rgba(255, 255, 255, 0.98); backdrop-filter: blur(12px);
    border: 1px solid rgba(0, 0, 0, 0.1); border-radius: 12px;
    box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1); z-index: 99999; min-width: 240px;
    overflow: hidden;
}}
.dropdown-item {{ padding: 12px 16px; color: #334155; font-size: 0.9rem; transition: all 0.2s; display: flex; align-items: center; gap: 10px; cursor: pointer; }}
.dropdown-item:hover {{ background: #F1F5F9; color: #0F172A; }}
.dropdown-header {{ padding: 16px; color: #0F172A; font-weight: 600; border-bottom: 1px solid rgba(0, 0, 0, 0.05); display: flex; align-items: center; gap: 12px; }}
.dropdown-header .small-avatar {{ background: linear-gradient(135deg, #FF9933, #FF7700); width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.85rem; font-weight: bold; color: white; }}
.search-input-mock {{ background: transparent; border: none; color: #0F172A; width: 100%; outline: none; font-size: 0.9rem; padding: 4px; }}
.search-input-mock::placeholder {{ color: #94A3B8; }}
</style>

<div class="glass-panel modern-header">
    <div class="header-titles">
        <h1>MOIL-GeoSync (G-Sync)</h1>
        <p>AI-Powered Manganese Exploration & Production Optimization</p>
    </div>
    <div class="header-actions">
        <div class="search-bar" style="display: flex; align-items: center; padding: 8px 16px;">
            <span class="material-symbols-rounded" style="margin-right: 8px; font-size: 1.2rem; color: #64748B;">search</span> 
            <input type="text" list="search-options" class="search-input-mock" placeholder="Search modules or reports..." />
            <datalist id="search-options">
                <option value="Prospectivity Map"></option>
                <option value="Production Forecast"></option>
                <option value="Fleet Optimization"></option>
                <option value="What-If Simulator"></option>
                <option value="Financial ROI"></option>
                <option value="Explainability"></option>
                <option value="AI Assistant"></option>
            </datalist>
        </div>
        <details>
            <summary class="profile-action">
                <div class="profile-avatar">VN</div>
                <div class="profile-name">Vinayak Nijhawan</div>
                <span style="color: #64748B; font-size: 0.8rem; margin-left: 4px;">▼</span>
            </summary>
            <div class="profile-dropdown-menu">
                <div class="dropdown-header">
                    <div class="small-avatar">VN</div>
                    <div>
                        <div style="font-size: 0.95rem;">Vinayak Nijhawan</div>
                        <div style="font-size: 0.75rem; color: #64748b; font-weight: 400;">Admin Account</div>
                    </div>
                </div>
                <div class="dropdown-item"><span class="material-symbols-rounded" style="font-size:1.1rem; margin-right:4px;">settings</span> Settings</div>
                <div class="dropdown-item"><span class="material-symbols-rounded" style="font-size:1.1rem; margin-right:4px;">person_add</span> Add other account</div>
                <div class="dropdown-item" style="color: #ef4444; border-top: 1px solid rgba(0, 0, 0, 0.05);"><span class="material-symbols-rounded" style="font-size:1.1rem; margin-right:4px;">logout</span> Logout</div>
            </div>
        </details>
    </div>
</div>
\"\"\", unsafe_allow_html=True)'''

content = re.sub(old_html, new_html, content)

# Check if z-index is set in .modern-header inside style.css or inline.
# I will make sure the inline style has it in the CSS block at the top if needed.

with open('src/pages/01_home.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')
