import streamlit as st
import streamlit.components.v1 as components

st.page_link('src/pages/02_prospectivity.py', label='TargetLink')

components.html('''
<script>
    setTimeout(() => {
        const link = window.parent.document.querySelector('[data-testid=\"stPageLink\"]');
        if (link) {
            console.log("HTML: " + link.outerHTML);
        }
    }, 1000);
</script>
''', height=0)
