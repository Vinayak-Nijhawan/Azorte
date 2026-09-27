import streamlit as st
import streamlit.components.v1 as components

st.page_link('src/pages/02_prospectivity.py', label='TargetLink')

components.html('''
<script>
    setTimeout(() => {
        try {
            const parentDoc = window.parent.document;
            const link = parentDoc.querySelector('[data-testid=\"stPageLink\"]');
            if (link) {
                console.log("Tag Name: " + link.tagName);
            }
        } catch (e) {}
    }, 1000);
</script>
''', height=0)
