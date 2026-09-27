with open('src/pages/01_home.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    '.search-input-mock { background: transparent; border: none; color: #0F172A; width: 100%; outline: none; font-size: 0.9rem; padding: 4px; }',
    '.search-input-mock { background: transparent; border: none; color: white; font-weight: bold; width: 100%; outline: none; font-size: 0.9rem; padding: 4px; }'
)
content = content.replace(
    '.search-input-mock::placeholder { color: #94A3B8; }',
    '.search-input-mock::placeholder { color: rgba(255, 255, 255, 0.7); font-weight: normal; }'
)

with open('src/pages/01_home.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')
