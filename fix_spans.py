import os
def replace_in(fp, old, new):
    with open(fp, 'r', encoding='utf-8') as f:
        c = f.read()
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(c.replace(old, new))

replace_in('src/pages/08_ai_assistant.py', '<span class=\"material-symbols-rounded\">check_circle</span>', ':material/check_circle:')
replace_in('src/pages/09_financial.py', '<span class=\"material-symbols-rounded\">currency_rupee</span>', ':material/currency_rupee:')
