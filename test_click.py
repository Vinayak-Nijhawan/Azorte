import streamlit as st
import streamlit.components.v1 as components

st.page_link('src/pages/02_prospectivity.py', label='hidden', key='hidden_link')

components.html('''
<script>
    setTimeout(() => {
        try {
            const parentDoc = window.parent.document;
            const link = parentDoc.querySelector('a[href$=\"02_prospectivity\"]');
            if (link) {
                link.click();
            } else {
                console.log(\"Link not found\");
            }
        } catch (e) {
            console.error(e);
        }
    }, 1000);
</script>
''', height=0)
