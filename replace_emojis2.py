import os

filepaths = [os.path.join('src/pages', f) for f in os.listdir('src/pages') if f.endswith('.py')]
filepaths.append('app.py')

replacements = {
    '🟠': '<span class=\"material-symbols-rounded\">circle</span>',
    '📉': '<span class=\"material-symbols-rounded\">trending_down</span>',
    '💸': '<span class=\"material-symbols-rounded\">money_off</span>',
    '💹': '<span class=\"material-symbols-rounded\">trending_up</span>',
    '🚨': '<span class=\"material-symbols-rounded\">warning</span>',
    '⚠️': '<span class=\"material-symbols-rounded\">warning</span>',
    '🟢': '<span class=\"material-symbols-rounded\">circle</span>',
    '🔴': '<span class=\"material-symbols-rounded\">circle</span>',
    '🟡': '<span class=\"material-symbols-rounded\">circle</span>',
    '⛏️': '<span class=\"material-symbols-rounded\">architecture</span>',
    '🏭': '<span class=\"material-symbols-rounded\">factory</span>',
    '📈': '<span class=\"material-symbols-rounded\">monitoring</span>',
    '💡': '<span class=\"material-symbols-rounded\">lightbulb</span>',
}

for fp in filepaths:
    with open(fp, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for k, v in replacements.items():
        content = content.replace(k, v)
        
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(content)
