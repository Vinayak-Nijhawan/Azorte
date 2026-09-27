import os, glob

for file in glob.glob('src/pages/*.py') + ['app.py']:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    original = content
    content = content.replace('<span class=\"material-symbols-rounded\">currency_rupee</span>', '?')
    content = content.replace('<span class=\'material-symbols-rounded\'>currency_rupee</span>', '?')
    
    if content != original:
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
