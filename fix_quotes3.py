import os
import re

filepaths = [os.path.join('src/pages', f) for f in os.listdir('src/pages') if f.endswith('.py')]
filepaths.append('app.py')

for fp in filepaths:
    with open(fp, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # First, let's fix the python syntax errors!
    # For strings like `'<span class='material-symbols-rounded'>...</span>'`, we change them to `'<span class=\"material-symbols-rounded\">...</span>'`
    content = content.replace(\"'<span class='material-symbols-rounded'>\", \"'<span class=\\\"material-symbols-rounded\\\">\")
    # If there's any remaining `\"<span class=\"material-symbols-rounded\">\"`, it needs to be `\"<span class='material-symbols-rounded'>\"`
    # But wait, my previous script did `content.replace('class=\"material-symbols-rounded\"', \"class='material-symbols-rounded'\")`
    # So now EVERYTHING has `class='material-symbols-rounded'`.
    # Let's just blindly escape it everywhere so it never conflicts with Python string quotes:
    # Wait, `class=\\'material-symbols-rounded\\'` is safe inside both ' and " python strings? No, inside " it becomes literal backslash.
    # The absolute safest is to just do `class=\"material-symbols-rounded\"` inside `'''` or `\"\"\"` but we don't know the context.
    pass

    # Actually, a better approach: 
    # Revert EVERYTHING back to unicode emojis using our dictionary, then apply fixes CAREFULLY.
    # Wait, the dictionary was one-way. We can reverse it!
