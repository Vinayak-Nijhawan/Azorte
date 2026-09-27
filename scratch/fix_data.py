import os

generate_path = r"c:\Users\Bansal\Desktop\sih\Azorte\src\generate_data.py"
prospectivity_path = r"c:\Users\Bansal\Desktop\sih\Azorte\src\pages\02_prospectivity.py"

with open(generate_path, "r", encoding="utf-8") as f:
    gen = f.read()

# Modify generate_data.py
gen = gen.replace("Expands data to 3 regions: Central India, Odisha, and Karnataka.", "Expands data to Central India and Madhya Pradesh.")
gen = gen.replace("""    # Region 2: Eastern (Joda-Barbil, Odisha)
    lat_east = np.random.uniform(21.8, 22.3, 750)
    lon_east = np.random.uniform(85.0, 85.7, 750)
    
    # Region 3: Southern (Sandur-Bellary, Karnataka)
    lat_south = np.random.uniform(14.8, 15.4, 750)
    lon_south = np.random.uniform(76.2, 76.8, 750)
    
    lats = np.concatenate([lat_cen, lat_east, lat_south])
    lons = np.concatenate([lon_cen, lon_east, lon_south])""", 
"""    # Region 2: Madhya Pradesh (Balaghat)
    lat_east = np.random.uniform(21.9, 22.1, 1500)
    lon_east = np.random.uniform(80.2, 80.6, 1500)
    
    lats = np.concatenate([lat_cen, lat_east])
    lons = np.concatenate([lon_cen, lon_east])""")

gen = gen.replace("""    def assign_rock_type(lat, lon):
        if lat < 16.0: return 'Dharwar_Schist' # Karnataka
        if lon > 84.0: return 'Iron_Ore_Group' # Odisha
        
        # Central India - Mapped to Sausar Group Stratigraphy (from G4 Report)""",
"""    def assign_rock_type(lat, lon):
        # Central India & MP - Mapped to Sausar Group Stratigraphy (from G4 Report)""")

gen = gen.replace("""    # Regional Rainfall adjustment
    base_rain = np.where(df_prospectivity['longitude'] > 84.0, 1400, # High rain in Odisha
                  np.where(df_prospectivity['latitude'] < 16.0, 600, # Low rain in Karnataka
                           1000)) # Medium in Central""",
"""    # Regional Rainfall adjustment
    base_rain = np.where(df_prospectivity['longitude'] > 80.2, 1600, # MP
                           1000) # Medium in Central""")

gen = gen.replace("""        'Mine_G_Joda_East', 'Mine_H_Bamebari', # Odisha
        'Mine_I_Sandur', 'Mine_J_Hospet' # Karnataka""",
"""        'Mine_G_Lugma', 'Mine_H_Ukwa' # Madhya Pradesh""")

gen = gen.replace("""        # Determine regional characteristics
        is_odisha = mine in ['Mine_G_Joda_East', 'Mine_H_Bamebari']
        is_karnataka = mine in ['Mine_I_Sandur', 'Mine_J_Hospet']""",
"""        # Determine regional characteristics
        is_mp = mine in ['Mine_G_Lugma', 'Mine_H_Ukwa']""")

gen = gen.replace("""            planned_tpd = np.random.uniform(800, 2000) if is_odisha else np.random.uniform(500, 1500)
            
            # Different monsoon impact
            if is_odisha: monsoon_months = [6, 7, 8, 9, 10]
            elif is_karnataka: monsoon_months = [7, 8, 9]
            else: monsoon_months = [6, 7, 8, 9]
            
            is_monsoon = month in monsoon_months
            
            equipment_availability = np.random.uniform(0.6, 0.8) if is_monsoon else np.random.uniform(0.8, 1.0)
            
            # Rainfall logic based on region
            if is_odisha: base_rain_monsoon = np.random.uniform(300, 600)
            elif is_karnataka: base_rain_monsoon = np.random.uniform(100, 250)
            else: base_rain_monsoon = np.random.uniform(200, 500)""",
"""            planned_tpd = np.random.uniform(300, 350) if is_mp else np.random.uniform(500, 1500)
            
            # Different monsoon impact
            monsoon_months = [6, 7, 8, 9]
            is_monsoon = month in monsoon_months
            
            equipment_availability = np.random.uniform(0.6, 0.8) if is_monsoon else np.random.uniform(0.8, 1.0)
            
            # Rainfall logic based on region
            if is_mp: base_rain_monsoon = np.random.uniform(300, 600)
            else: base_rain_monsoon = np.random.uniform(200, 500)""")

gen = gen.replace("""        is_odisha = mine in ['Mine_G_Joda_East', 'Mine_H_Bamebari']
        is_karnataka = mine in ['Mine_I_Sandur', 'Mine_J_Hospet']""",
"""        is_mp = mine in ['Mine_G_Lugma', 'Mine_H_Ukwa']""")

gen = gen.replace("""            if is_odisha: monsoon_months = [6, 7, 8, 9, 10]
            elif is_karnataka: monsoon_months = [7, 8, 9]
            else: monsoon_months = [6, 7, 8, 9]
            
            is_monsoon = month in monsoon_months
            
            planned_tpd = np.random.uniform(800, 2000) if is_odisha else np.random.uniform(500, 1500)
            equipment_availability = 0.7 if is_monsoon else 0.9
            
            if is_odisha: base_rain_monsoon = 450
            elif is_karnataka: base_rain_monsoon = 150
            else: base_rain_monsoon = 300""",
"""            monsoon_months = [6, 7, 8, 9]
            is_monsoon = month in monsoon_months
            
            planned_tpd = 330 if is_mp else np.random.uniform(500, 1500)
            equipment_availability = 0.7 if is_monsoon else 0.9
            
            if is_mp: base_rain_monsoon = 450
            else: base_rain_monsoon = 300""")

gen = gen.replace("Generated {len(df_prospectivity)} prospectivity records (3 Regions).", "Generated {len(df_prospectivity)} prospectivity records (2 Regions).")


with open(generate_path, "w", encoding="utf-8") as f:
    f.write(gen)


# Modify 02_prospectivity.py
with open(prospectivity_path, "r", encoding="utf-8") as f:
    pros = f.read()

pros = pros.replace(
    'region = st.selectbox("🌍 Region", ["Central India (Nagpur)", "Eastern India (Odisha)", "Southern India (Karnataka)"])',
    'region = st.selectbox("🌍 Region", ["Central India (Nagpur)", "Madhya Pradesh (Balaghat)"])'
)

pros = pros.replace("""    if "Central" in region:
        map_center = dict(lat=21.45, lon=79.65)
    elif "Eastern" in region:
        map_center = dict(lat=22.05, lon=85.25)
    else:
        map_center = dict(lat=15.15, lon=76.55)""",
"""    if "Central" in region:
        map_center = dict(lat=21.45, lon=79.65)
    elif "Madhya" in region:
        map_center = dict(lat=21.98, lon=80.42)
    else:
        map_center = dict(lat=21.45, lon=79.65)""")

pros = pros.replace("""            # Odisha (Joda-Barbil belt)
            (22.010, 85.437, "Joda East Mine", "Odisha"),
            (22.100, 85.250, "Bamebari Mine", "Odisha"),
            # Karnataka (Sandur schist belt)
            (15.083, 76.550, "Sandur Mine", "Karnataka"),
            (15.250, 76.350, "Hospet Mine", "Karnataka"),""",
"""            # Madhya Pradesh (Balaghat belt)
            (21.974, 80.385, "Lugma Mine", "Madhya Pradesh"),
            (21.986, 80.457, "Ukwa Mine", "Madhya Pradesh"),""")

pros = pros.replace(
    "m_colors = ['red' if r == 'Central' else 'cyan' if r == 'Odisha' else 'lime' for r in m_regions]",
    "m_colors = ['red' if r == 'Central' else 'cyan' if r == 'Madhya Pradesh' else 'lime' for r in m_regions]"
)

pros = pros.replace("""    if lat >= 21.0 and lat <= 22.0 and lon >= 78.5 and lon <= 80.5:
        return "Central India"
    elif lat >= 21.5 and lon >= 84.5:
        return "Odisha"
    elif lat < 16.0:
        return "Karnataka"
    return "Other\"""",
"""    if lat >= 21.0 and lat <= 22.0 and lon >= 78.5 and lon <= 80.2:
        return "Central India"
    elif lat >= 21.8 and lon >= 80.2 and lon <= 80.6:
        return "Madhya Pradesh"
    return "Other\"""")

pros = pros.replace("""    od_high  = int((df[df['region'] == 'Odisha']['mn_probability'] > 0.45).sum())        if len(df[df['region'] == 'Odisha']) > 0       else 0
    kar_high = int((df[df['region'] == 'Karnataka']['mn_probability'] > 0.45).sum())     if len(df[df['region'] == 'Karnataka']) > 0    else 0""",
"""    mp_high  = int((df[df['region'] == 'Madhya Pradesh']['mn_probability'] > 0.45).sum())        if len(df[df['region'] == 'Madhya Pradesh']) > 0       else 0""")

html_to_replace = """    <div class="geo-kpi-card">
        <div class="geo-kpi-header">
            <div class="geo-kpi-title">Odisha</div>
            <div class="geo-kpi-icon geo-icon-blue">🟦</div>
        </div>
        <div class="geo-kpi-value">{od_high} targets</div>
        <div class="geo-kpi-footer">
            <span class="geo-trend-amber">Joda-Barbil Belt</span>
        </div>
    </div>
    <div class="geo-kpi-card">
        <div class="geo-kpi-header">
            <div class="geo-kpi-title">Karnataka</div>
            <div class="geo-kpi-icon geo-icon-lime">🟩</div>
        </div>
        <div class="geo-kpi-value">{kar_high} targets</div>
        <div class="geo-kpi-footer">
            <span class="geo-trend-green">Sandur Schist Belt</span>
        </div>
    </div>"""

html_replacement = """    <div class="geo-kpi-card">
        <div class="geo-kpi-header">
            <div class="geo-kpi-title">Madhya Pradesh</div>
            <div class="geo-kpi-icon geo-icon-blue">🟦</div>
        </div>
        <div class="geo-kpi-value">{mp_high} targets</div>
        <div class="geo-kpi-footer">
            <span class="geo-trend-amber">Balaghat Belt</span>
        </div>
    </div>"""
    
pros = pros.replace(html_to_replace, html_replacement)

with open(prospectivity_path, "w", encoding="utf-8") as f:
    f.write(pros)
