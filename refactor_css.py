import os
import re

with open('assets/style.css', 'r', encoding='utf-8') as f:
    css = f.read()

# Remove the aggressive body background override
css = re.sub(r'html, body, \[data-testid="stApp"\], \[data-testid="stAppViewContainer"\],\s*\n\s*\.main \.block-container\s*\{[^}]+\}', 
             r'.main .block-container {\n    padding: 2rem 2.5rem 4rem !important;\n    max-width: 1400px !important;\n}', css)

# Replace hardcoded colors with CSS variables
replacements = {
    '#0F172A': 'var(--secondary-background-color)',
    '#090D16': 'var(--background-color)',
    '#1E293B': 'color-mix(in srgb, var(--text-color) 12%, transparent)',
    '#334155': 'color-mix(in srgb, var(--text-color) 20%, transparent)',
    '#111827': 'var(--background-color)',
    '#e2e8f0': 'var(--text-color)',
    '#f1f5f9': 'var(--text-color)',
    '#cbd5e1': 'color-mix(in srgb, var(--text-color) 85%, transparent)',
    '#94a3b8': 'color-mix(in srgb, var(--text-color) 60%, transparent)',
    '#94A3B8': 'color-mix(in srgb, var(--text-color) 60%, transparent)',
    '#475569': 'color-mix(in srgb, var(--text-color) 50%, transparent)',
    '#64748b': 'color-mix(in srgb, var(--text-color) 60%, transparent)',
    '#3B82F6': 'var(--primary-color)',
    '#2563EB': 'var(--primary-color)',
    'rgba(17, 24, 39, 0.7)': 'var(--secondary-background-color)',
    'rgba(17,24,39,0.8)': 'var(--secondary-background-color)',
    'rgba(30, 41, 59, 0.8)': 'color-mix(in srgb, var(--text-color) 15%, transparent)',
    'rgba(255,255,255,0.04)': 'color-mix(in srgb, var(--text-color) 5%, transparent)',
}

for k, v in replacements.items():
    css = css.replace(k, v)
    if k.startswith('#'):
        css = css.replace(k.lower(), v)

# For #fff, we want it to stay #fff for text on primary buttons, but if it's used as a background it should maybe adapt. 
# It's safest to leave #fff as #fff or use #ffffff. Let's just leave it.

with open('assets/style.css', 'w', encoding='utf-8') as f:
    f.write(css)
