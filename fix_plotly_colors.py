import os
import re

filepaths = [os.path.join('src/pages', f) for f in os.listdir('src/pages') if f.endswith('.py')]

for fp in filepaths:
    with open(fp, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove font=dict(color='...')
    # It might have other arguments like size=11, we should keep those if possible, 
    # but removing the whole dict and replacing with font=dict(size=11) is tricky.
    # Actually, removing color='...' is enough.
    content = re.sub(r'color=[\'"][^\'"]*[\'"]\s*,?', '', content)
    
    # Remove gridcolor='...' and zerolinecolor='...'
    content = re.sub(r'gridcolor=[\'"][^\'"]*[\'"]\s*,?', '', content)
    content = re.sub(r'zerolinecolor=[\'"][^\'"]*[\'"]\s*,?', '', content)
    
    # Clean up empty commas like `font=dict( size=11)`
    content = content.replace('font=dict( ', 'font=dict(')
    content = content.replace('(,', '(')
    content = content.replace(', )', ')')
    
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(content)
