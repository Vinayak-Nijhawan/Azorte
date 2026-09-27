import os

files_to_fix = [
    'src/pages/03_production.py',
    'src/pages/04_fleet_dispatch.py',
    'src/pages/08_ai_assistant.py',
    'src/pages/01_home.py'
]

for file in files_to_fix:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace all instances of 'shortfall_risk' with 'shortfall_risk__DERIVED'
    content = content.replace("'shortfall_risk'", "'shortfall_risk__DERIVED'")
    content = content.replace('"shortfall_risk"', '"shortfall_risk__DERIVED"')
    
    # In 01_home.py, replace the mean() calculation
    content = content.replace(
        "kpi_data['avg_shortfall_risk'] = f\"{df_prod['shortfall_risk__DERIVED'].mean():.1f}\"",
        "high_count = (df_prod['shortfall_risk__DERIVED'] == 'High').sum()\n                kpi_data['avg_shortfall_risk'] = f\"{high_count} High Risk\""
    )
    
    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)
