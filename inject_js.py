with open('src/pages/01_home.py', 'r', encoding='utf-8') as f:
    content = f.read()

injection = '''
# --- JavaScript Injection for Search Navigation ---
import streamlit.components.v1 as components
components.html(\"\"\"
<script>
    // Execute after a short delay to ensure DOM is fully mounted
    setTimeout(function() {
        const parentDoc = window.parent.document;
        const inputElement = parentDoc.querySelector('.search-input-mock');
        
        if (inputElement) {
            // Prevent multiple listeners if re-run
            if (inputElement.hasAttribute('data-listener-attached')) return;
            inputElement.setAttribute('data-listener-attached', 'true');
            
            inputElement.addEventListener('change', function(e) {
                const val = e.target.value;
                let targetUrl = '';
                
                if (val === 'Prospectivity Map') targetUrl = 'prospectivity';
                else if (val === 'Production Forecast') targetUrl = 'production';
                else if (val === 'Fleet Optimization') targetUrl = 'fleet';
                else if (val === 'What-If Simulator') targetUrl = 'what_if';
                else if (val === 'Financial ROI') targetUrl = 'financial';
                else if (val === 'Explainability') targetUrl = 'explainability';
                
                if (targetUrl !== '') {
                    window.parent.location.href = targetUrl;
                }
            });
        }
    }, 500);
</script>
\"\"\", height=0)
# ------------------------------------------------
'''

# We will inject this right before # 3. Outcomes Section
content = content.replace('# 3. Outcomes Section', injection + '\n# 3. Outcomes Section')

with open('src/pages/01_home.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Injected Javascript')
