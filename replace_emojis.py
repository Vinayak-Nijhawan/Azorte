import os

replacements = {
    "🏠": "<span class=\"material-symbols-rounded\">home</span>",
    "🗺️": "<span class=\"material-symbols-rounded\">explore</span>",
    "📈": "<span class=\"material-symbols-rounded\">monitoring</span>",
    "🚛": "<span class=\"material-symbols-rounded\">local_shipping</span>",
    "🎛️": "<span class=\"material-symbols-rounded\">tune</span>",
    "🧬": "<span class=\"material-symbols-rounded\">science</span>",
    "🤖": "<span class=\"material-symbols-rounded\">smart_toy</span>",
    "💰": "<span class=\"material-symbols-rounded\">attach_money</span>",
    "🔬": "<span class=\"material-symbols-rounded\">info</span>",
    "⛏️": "<span class=\"material-symbols-rounded\">architecture</span>",
    "🎯": "<span class=\"material-symbols-rounded\">my_location</span>",
    "✨": "<span class=\"material-symbols-rounded\">flare</span>",
    "⚠️": "<span class=\"material-symbols-rounded\">warning</span>",
    "🧭": "<span class=\"material-symbols-rounded\">explore</span>",
    "⏱️": "<span class=\"material-symbols-rounded\">timer</span>",
    "⚙️": "<span class=\"material-symbols-rounded\">settings</span>",
    "🌱": "<span class=\"material-symbols-rounded\">eco</span>",
    "🔍": "<span class=\"material-symbols-rounded\">search</span>",
    "🔴": "<span class=\"material-symbols-rounded\">circle</span>",
    "🟡": "<span class=\"material-symbols-rounded\">circle</span>",
    "🟢": "<span class=\"material-symbols-rounded\">circle</span>",
    "📋": "<span class=\"material-symbols-rounded\">content_paste</span>",
    "📊": "<span class=\"material-symbols-rounded\">bar_chart</span>",
    "🧮": "<span class=\"material-symbols-rounded\">calculate</span>",
    "🤝": "<span class=\"material-symbols-rounded\">handshake</span>",
    "₹": "<span class=\"material-symbols-rounded\">currency_rupee</span>",
    "💡": "<span class=\"material-symbols-rounded\">lightbulb</span>",
    "🚨": "<span class=\"material-symbols-rounded\">warning</span>",
    "🛡️": "<span class=\"material-symbols-rounded\">shield</span>",
    "👨‍🔧": "<span class=\"material-symbols-rounded\">engineering</span>",
    "🚚": "<span class=\"material-symbols-rounded\">local_shipping</span>",
    "🛣️": "<span class=\"material-symbols-rounded\">add_road</span>",
    "🛠️": "<span class=\"material-symbols-rounded\">build</span>",
    "🌧️": "<span class=\"material-symbols-rounded\">rainy</span>",
    "🏭": "<span class=\"material-symbols-rounded\">factory</span>",
    "💥": "<span class=\"material-symbols-rounded\">explosion</span>",
    "✅": "<span class=\"material-symbols-rounded\">check_circle</span>",
    "ℹ️": "<span class=\"material-symbols-rounded\">info</span>",
}

# Add Streamlit native versions for st.page_link, st.metric, etc.
# Actually, since st.metric and st.markdown support native Streamlit material syntax, 
# we could just use :material/icon: directly if it wasn't inside HTML.
# But inside HTML <span class="..."> works for both! 
# Let's check if the replacement will break anything.
# To be safe, we will just use the HTML spans. They work inside st.markdown.
# Wait, for st.markdown natively, `st.markdown("### <span...></span> Title")` works but might be ugly.
# Let's refine the dictionary to use native `:material/icon:` where possible, 
# but wait, `<span class="material-symbols-rounded">` is safest for the HTML strings we inject.
# Actually, replacing emojis in st.page_link with HTML span will BREAK st.page_link.
# But I already fixed app.py to use native :material: syntax.
# What about other files?

def replace_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    for emoji, icon in replacements.items():
        content = content.replace(emoji, icon)
        
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {filepath}")

for root, dirs, files in os.walk('src/pages'):
    for file in files:
        if file.endswith('.py'):
            replace_in_file(os.path.join(root, file))

print("Done!")
