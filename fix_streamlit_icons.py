import os
import re

filepaths = [os.path.join('src/pages', f) for f in os.listdir('src/pages') if f.endswith('.py')]
filepaths.append('app.py')

pattern = re.compile(r'<span class=\\?"material-symbols-rounded\\?">(\w+)</span>')

for fp in filepaths:
    with open(fp, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    new_lines = []
    for line in lines:
        # If the line contains typical Streamlit widgets or headers, replace span with native material syntax
        if any(x in line for x in ['st.toggle', 'st.tabs', 'st.button', 'st.slider', 'st.radio', 
                                   'st.checkbox', 'st.selectbox', 'st.metric', 'st.title', 
                                   'st.subheader', 'st.header', 'st.caption', 'st.info', 
                                   'st.warning', 'st.error', 'st.success']):
            line = pattern.sub(r':material/\1:', line)
            
        # Also do this for f-strings and format strings that are not part of HTML blocks
        # A simple heuristic: if it doesn't have <div or </h1> or other HTML tags, we convert it
        elif '<div' not in line and '</h1>' not in line and '</h' not in line:
            # Let's be careful. Let's just convert any span that isn't inside a multi-line HTML string.
            # If the line has 'st.markdown' without 'unsafe_allow_html=True', we can safely convert.
            pass
            
        new_lines.append(line)
        
    with open(fp, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
