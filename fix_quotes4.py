import os
import re

filepaths = [os.path.join('src/pages', f) for f in os.listdir('src/pages') if f.endswith('.py')]
filepaths.append('app.py')

reverse_map = {
    "<span class='material-symbols-rounded'>home</span>": "🏠",
    "<span class='material-symbols-rounded'>explore</span>": "🗺️",
    "<span class='material-symbols-rounded'>monitoring</span>": "📈",
    "<span class='material-symbols-rounded'>local_shipping</span>": "🚛",
    "<span class='material-symbols-rounded'>tune</span>": "🎛️",
    "<span class='material-symbols-rounded'>science</span>": "🧬",
    "<span class='material-symbols-rounded'>smart_toy</span>": "🤖",
    "<span class='material-symbols-rounded'>attach_money</span>": "💰",
    "<span class='material-symbols-rounded'>info</span>": "🔬",
    "<span class='material-symbols-rounded'>architecture</span>": "⛏️",
    "<span class='material-symbols-rounded'>my_location</span>": "🎯",
    "<span class='material-symbols-rounded'>flare</span>": "✨",
    "<span class='material-symbols-rounded'>warning</span>": "⚠️",
    "<span class='material-symbols-rounded'>timer</span>": "⏱️",
    "<span class='material-symbols-rounded'>settings</span>": "⚙️",
    "<span class='material-symbols-rounded'>eco</span>": "🌱",
    "<span class='material-symbols-rounded'>search</span>": "🔍",
    "<span class='material-symbols-rounded'>circle</span>": "🔴",
    "<span class='material-symbols-rounded'>content_paste</span>": "📋",
    "<span class='material-symbols-rounded'>bar_chart</span>": "📊",
    "<span class='material-symbols-rounded'>calculate</span>": "🧮",
    "<span class='material-symbols-rounded'>handshake</span>": "🤝",
    "<span class='material-symbols-rounded'>currency_rupee</span>": "₹",
    "<span class='material-symbols-rounded'>lightbulb</span>": "💡",
    "<span class='material-symbols-rounded'>shield</span>": "🛡️",
    "<span class='material-symbols-rounded'>engineering</span>": "👨‍🔧",
    "<span class='material-symbols-rounded'>add_road</span>": "🛣️",
    "<span class='material-symbols-rounded'>build</span>": "🛠️",
    "<span class='material-symbols-rounded'>rainy</span>": "🌧️",
    "<span class='material-symbols-rounded'>factory</span>": "🏭",
    "<span class='material-symbols-rounded'>explosion</span>": "💥",
    "<span class='material-symbols-rounded'>check_circle</span>": "✅"
}

for fp in filepaths:
    with open(fp, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Let's fix the python syntax errors first by converting ALL html spans to use \" (escaped quotes)
    # This prevents them from breaking any enclosing single or double quotes!
    # The current state in the files is `class='material-symbols-rounded'` due to my previous fix script.
    
    # First, let's fix the specific Plotly issues and f-string issues:
    # 02_prospectivity.py line 199: name='<span class='material-symbols-rounded'>architecture</span> Known Mines'
    # We will just replace ALL `<span class='material-symbols-rounded'>...</span>` inside `name='...'` with the emoji!
    def repl_name(match):
        inner = match.group(1)
        for span, emoji in reverse_map.items():
            inner = inner.replace(span, emoji)
        return f"name='{inner}'"
    content = re.sub(r"name='([^']*)'", repl_name, content)
    
    def repl_name_double(match):
        inner = match.group(1)
        for span, emoji in reverse_map.items():
            inner = inner.replace(span, emoji)
        return f'name="{inner}"'
    content = re.sub(r'name="([^"]*)"', repl_name_double, content)

    # 09_financial.py line 107: return f'<span class='material-symbols-rounded'>currency_rupee</span>{amount/1e7:.2f} Cr'
    # If the span is inside an f-string starting with f', we should escape the quote in the span!
    # Instead of complex regex, let's just globally replace `class='material-symbols-rounded'` 
    # with `class=\"material-symbols-rounded\"` EVERYWHERE.
    content = content.replace("class='material-symbols-rounded'", 'class=\\"material-symbols-rounded\\"')
    
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(content)
