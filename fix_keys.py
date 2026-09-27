import re

with open('src/pages/01_home.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r', key=\"[^\"]+\"', '', content)

with open('src/pages/01_home.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed keys')
