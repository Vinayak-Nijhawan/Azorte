import streamlit as st
import streamlit.components.v1 as components

st.markdown("""
<div class="geo-kpi-value" data-target="1500" data-decimals="0">0</div>
""", unsafe_allow_html=True)

components.html("""
<script>
    const parentDoc = window.parent.document;
    const counters = parentDoc.querySelectorAll('.geo-kpi-value');
    counters.forEach(c => {
        c.innerHTML = "JS WORKED: " + c.getAttribute('data-target');
    });
</script>
""", height=0, width=0)
