with open('src/pages/02_prospectivity.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re

# Safely extract from <p style=... down to </style>
pattern = r'<p style=\"font-weight:600; color:var\(--text-color\); margin:8px 0 12px 0;\">Region-wise High Priority Targets:</p>.*?</style>'
# wait, there's no </style> at the end of the file. The file ends with """
pattern = r'<p style=\"font-weight:600; color:var\(--text-color\); margin:8px 0 12px 0;\">Region-wise High Priority Targets:</p>.*?\"\"\"'

new_html = '''<p style="font-weight:600; color:var(--text-color); margin:8px 0 12px 0;">Region-wise High Priority Targets:</p>
<div class="geo-kpi-grid">
    <div class="geo-kpi-card">
        <div class="geo-kpi-header">
            <div class="geo-kpi-title">Central India</div>
            <div class="geo-kpi-icon geo-icon-pink"><span class="material-symbols-rounded">landscape</span></div>
        </div>
        <div class="geo-kpi-value">{ci_high} targets</div>
        <div class="geo-kpi-footer">
            <span class="geo-trend-red">Nagpur Belt</span>
        </div>
    </div>
    <div class="geo-kpi-card">
        <div class="geo-kpi-header">
            <div class="geo-kpi-title">Madhya Pradesh</div>
            <div class="geo-kpi-icon geo-icon-blue"><span class="material-symbols-rounded">terrain</span></div>
        </div>
        <div class="geo-kpi-value">{mp_high} targets</div>
        <div class="geo-kpi-footer">
            <span class="geo-trend-amber">Balaghat Belt</span>
        </div>
    </div>
</div>
"""'''

content = re.sub(pattern, new_html, content, flags=re.DOTALL)

with open('src/pages/02_prospectivity.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')
