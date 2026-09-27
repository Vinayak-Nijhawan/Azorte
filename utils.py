import os
import streamlit as st

def load_css():
    """Injects the global stylesheet on the current page."""
    # Find assets/style.css relative to the project root
    current_dir = os.path.dirname(os.path.abspath(__file__))
    css_path = os.path.join(current_dir, "assets", "style.css")
    
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()
            # Try st.html first, fallback to st.markdown
            if hasattr(st, "html"):
                st.html(f"<style>{css}</style>")
            else:
                st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

def inject_kpi_animations():
    """Injects JavaScript to animate .geo-kpi-value elements (count up effect)."""
    js = """
    <script>
        // Use a short timeout to ensure parent DOM is fully loaded
        setTimeout(() => {
            const parentDoc = window.parent.document;
            const counters = parentDoc.querySelectorAll('.geo-kpi-value');
            const duration = 1500;
            
            counters.forEach(counter => {
                // Ignore if already animated
                if(counter.getAttribute('data-animated') === 'true') return;
                
                // Extract target number from text (e.g., "1,500 <span...>TPD</span>")
                // Keep inner HTML (spans) separate from the number
                let rawHtml = counter.innerHTML;
                let textContent = counter.childNodes[0] ? counter.childNodes[0].textContent : "";
                
                // Parse number
                let cleanText = textContent.replace(/,/g, '').replace(/₹/g, '').trim();
                let target = parseFloat(cleanText);
                
                if(isNaN(target)) return;
                
                // Find if there are decimals
                let decimals = 0;
                if(cleanText.includes('.')) {
                    decimals = cleanText.split('.')[1].length;
                }
                
                let prefix = textContent.includes('₹') ? '₹' : '';
                
                // Extract any HTML suffix (spans)
                let suffixHtml = "";
                Array.from(counter.childNodes).forEach((node, i) => {
                    if(i > 0) suffixHtml += node.outerHTML || node.textContent;
                });
                
                counter.setAttribute('data-animated', 'true');
                
                const startTime = performance.now();
                const updateCounter = (currentTime) => {
                    const elapsedTime = currentTime - startTime;
                    const progress = Math.min(elapsedTime / duration, 1);
                    const easeOut = progress * (2 - progress);
                    const currentVal = target * easeOut;
                    
                    let formattedNum = currentVal.toLocaleString('en-IN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
                    counter.innerHTML = prefix + formattedNum + suffixHtml;

                    if (progress < 1) {
                        requestAnimationFrame(updateCounter);
                    } else {
                        let finalFormatted = target.toLocaleString('en-IN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
                        counter.innerHTML = prefix + finalFormatted + suffixHtml;
                    }
                };
                requestAnimationFrame(updateCounter);
            });
        }, 100);
    </script>
    """
    import streamlit.components.v1 as components
    components.html(js, height=0, width=0)

def inject_volcano_animations():
    """Injects CSS to animate Plotly bar charts like an erupting volcano."""
    css = """
    <style>
    @keyframes volcanoErupt {
        0% { transform: scaleY(0); opacity: 0; }
        70% { transform: scaleY(1.05); }
        100% { transform: scaleY(1); opacity: 1; }
    }
    [data-testid="stPlotlyChart"] svg .bars path,
    [data-testid="stPlotlyChart"] svg .point path {
        transform-origin: bottom !important;
        animation: volcanoErupt 1.2s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards !important;
    }
    </style>
    """
    if hasattr(st, "html"):
        st.html(css)
    else:
        st.markdown(css, unsafe_allow_html=True)
