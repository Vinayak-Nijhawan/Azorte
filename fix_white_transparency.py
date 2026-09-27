import os
import re

for filename in os.listdir('src/pages'):
    if not filename.endswith('.py'): continue
    filepath = os.path.join('src/pages', filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace all transparent white backgrounds with adaptive secondary background
    content = re.sub(
        r'background:\s*rgba\(255,\s*255,\s*255,\s*0\.[0-9]+\)\s*;',
        'background: var(--secondary-background-color);',
        content
    )
    
    # Replace all transparent white borders with adaptive text-color mix
    content = re.sub(
        r'border(-bottom|-top|-left|-right)?:\s*1px\s*solid\s*rgba\(255,\s*255,\s*255,\s*0\.[0-9]+\)\s*;',
        r'border\1: 1px solid color-mix(in srgb, var(--text-color) 10%, transparent);',
        content
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
