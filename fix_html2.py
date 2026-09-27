import os, glob, re

for file in glob.glob('src/pages/*.py') + ['app.py']:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    original = content
    # Replace any span that has currency_rupee inside it, regardless of quotes/backslashes
    pattern = r'<span[^>]*>currency_rupee</span>'
    content = re.sub(pattern, '?', content)
    
    if content != original:
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
