import os
import re

filepaths = [os.path.join('src/pages', f) for f in os.listdir('src/pages') if f.endswith('.py')]

for fp in filepaths:
    with open(fp, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Safely remove font=dict(color='...') by replacing only font color
    content = re.sub(r'font=dict\([^)]*color=[\'"][^\'"]*[\'"][^)]*\)', 
                     lambda m: re.sub(r'color=[\'"][^\'"]*[\'"]\s*,?', '', m.group(0)), 
                     content)
    
    # Remove gridcolor='...' and zerolinecolor='...'
    content = re.sub(r'gridcolor=[\'"][^\'"]*[\'"]\s*,?', '', content)
    content = re.sub(r'zerolinecolor=[\'"][^\'"]*[\'"]\s*,?', '', content)
    
    # Clean up empty commas
    content = content.replace('font=dict( ', 'font=dict(')
    content = content.replace('(,', '(')
    content = content.replace(', )', ')')
    
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(content)
