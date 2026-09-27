import glob
import os

pages = glob.glob(r"c:\Users\Ayush\Desktop\sih\Azorte\src\pages\*.py")

for page in pages:
    if '09_financial.py' in page:
        continue
        
    with open(page, 'r', encoding='utf-8') as f:
        content = f.read()
        
    if 'inject_kpi_animations' not in content:
        content = content.replace('from utils import load_css', 'from utils import load_css, inject_kpi_animations, inject_volcano_animations')
        
        # Append calls to the end of the file
        content += "\n\n# --- Animations ---\n"
        content += "inject_kpi_animations()\n"
        content += "inject_volcano_animations()\n"
        
        with open(page, 'w', encoding='utf-8') as f:
            f.write(content)
            
print("Done injecting animations!")
