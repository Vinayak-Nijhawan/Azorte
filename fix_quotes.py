import os

filepaths = [os.path.join('src/pages', f) for f in os.listdir('src/pages') if f.endswith('.py')]
filepaths.append('app.py')

for fp in filepaths:
    with open(fp, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace double-quote class names with single-quote to prevent breaking Python strings
    content = content.replace('class="material-symbols-rounded"', "class='material-symbols-rounded'")
    
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(content)
