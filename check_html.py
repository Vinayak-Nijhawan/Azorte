import os, glob

def check_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    for i, line in enumerate(lines):
        if ('st.markdown' in line or 'st.write' in line or 'st.info' in line or 'st.success' in line or 'st.warning' in line or 'st.error' in line or 'st.caption' in line):
            if '<span' in line or '<div' in line or '<br' in line or '<b>' in line:
                if 'unsafe_allow_html' not in line:
                    print(f'{filepath}:{i+1}: {line.strip()}')

for file in glob.glob('src/pages/*.py') + ['app.py']:
    check_file(file)
