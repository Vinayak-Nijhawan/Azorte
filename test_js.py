import streamlit.components.v1 as components

components.html('''
<script>
    const parentDoc = window.parent.document;
    const inputElement = parentDoc.querySelector('.search-input-mock');
    
    if (inputElement) {
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
                // Navigate to the target URL
                window.parent.location.href = targetUrl;
            }
        });
    }
</script>
''', height=0)
