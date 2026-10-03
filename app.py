"""
MOIL-GeoSync (G-Sync) Dashboard
================================
AI-Powered Manganese Exploration & Production Optimization
Team Azorte | SIH 2026 | PS 26009

Run with: streamlit run app.py
"""

import streamlit as st

st.set_page_config(
    layout="wide",
    page_title="MOIL-GeoSync",
    page_icon=":material/architecture:",
    initial_sidebar_state="expanded",
)


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO CREDENTIALS (pre-computed SHA-256 hashes)
# At login: hashlib.sha256(user_input.encode()).hexdigest() is compared
# against these stored hashes. No plaintext passwords in code.
# ═══════════════════════════════════════════════════════════════════════════════
DEFAULT_USERS = {
    "admin": {
        "name": "Vinayak Nijhawan",
        "role": "Admin",
        "password_hash": "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9",  # admin123
    },
    "mine_mgr": {
        "name": "Rajesh Kumar",
        "role": "Mine Manager",
        "password_hash": "a71ddaee076561c3008fec3b4ab4280f32160071cfcf21ae9d781d4aee360767",  # mine2026
    },
    "geologist": {
        "name": "Priya Sharma",
        "role": "Geologist",
        "password_hash": "9fadd87faadc366f07df367daf1d17a40f3de628c2318954b7ccd6c9f7616f46",  # geo2026
    },
    "operator": {
        "name": "Suresh Yadav",
        "role": "Operator",
        "password_hash": "ab72db25169030b9049e4ed98609dfc9f0331f4042de154461332f853bc36794",  # ops2026
    },
    "viewer": {
        "name": "MOIL Auditor",
        "role": "Viewer",
        "password_hash": "d5202e6904b89534425e3e52d9173445bf493805ad2c40edddd1529d497cde18",  # view2026
    },
}

# Initialize session-state user store (mutable — account management can add users)
if "app_users" not in st.session_state:
    st.session_state.app_users = dict(DEFAULT_USERS)


# ═══════════════════════════════════════════════════════════════════════════════
# ROLE → ALLOWED PAGES
# ═══════════════════════════════════════════════════════════════════════════════
ROLE_PAGES = {
    "Admin":        ["Overview", "GeoProspect AI", "Production Forecast",
                     "Fleet Dispatch", "Underground Dispatch", "What-If Simulator",
                     "AI Explainability", "G-Sync AI", "Financial ROI",
                     "Data & Model Info", "Account Management"],
    "Mine Manager": ["Overview", "Production Forecast", "Fleet Dispatch",
                     "Underground Dispatch", "What-If Simulator", "G-Sync AI",
                     "Financial ROI", "Data & Model Info", "Account Management"],
    "Geologist":    ["Overview", "GeoProspect AI", "What-If Simulator",
                     "AI Explainability", "G-Sync AI", "Data & Model Info"],
    "Operator":     ["Overview", "Fleet Dispatch", "Underground Dispatch",
                     "G-Sync AI"],
    "Viewer":       ["Overview", "Production Forecast", "Financial ROI",
                     "Data & Model Info"],
}

# Page icons mapping (for sidebar links)
PAGE_ICONS = {
    "Overview": ":material/home:",
    "GeoProspect AI": ":material/explore:",
    "Production Forecast": ":material/monitoring:",
    "Fleet Dispatch": ":material/local_shipping:",
    "Underground Dispatch": ":material/elevator:",
    "What-If Simulator": ":material/tune:",
    "AI Explainability": ":material/science:",
    "G-Sync AI": ":material/smart_toy:",
    "Financial ROI": ":material/attach_money:",
    "Data & Model Info": ":material/info:",
    "Account Management": ":material/manage_accounts:",
}

# Navigation sections (for sidebar grouping)
COMMAND_CENTER = ["Overview", "GeoProspect AI", "Production Forecast",
                  "Fleet Dispatch", "Underground Dispatch", "What-If Simulator"]
INTELLIGENCE = ["AI Explainability", "G-Sync AI", "Financial ROI", "Data & Model Info"]
ADMIN_SECTION = ["Account Management"]


# ═══════════════════════════════════════════════════════════════════════════════
# ALL PAGES REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════
ALL_PAGES = {
    "Overview": st.Page("src/pages/01_home.py", title="Overview", icon=":material/home:"),
    "GeoProspect AI": st.Page("src/pages/02_prospectivity.py", title="GeoProspect AI", icon=":material/explore:"),
    "Production Forecast": st.Page("src/pages/03_production.py", title="Production Forecast", icon=":material/monitoring:"),
    "Fleet Dispatch": st.Page("src/pages/04_fleet_dispatch.py", title="Fleet Dispatch", icon=":material/local_shipping:"),
    "Underground Dispatch": st.Page("src/pages/05_underground_dispatch.py", title="Underground Dispatch", icon=":material/elevator:"),
    "What-If Simulator": st.Page("src/pages/06_what_if.py", title="What-If Simulator", icon=":material/tune:"),
    "AI Explainability": st.Page("src/pages/07_explainability.py", title="AI Explainability", icon=":material/science:"),
    "G-Sync AI": st.Page("src/pages/08_ai_assistant.py", title="G-Sync AI", icon=":material/smart_toy:"),
    "Financial ROI": st.Page("src/pages/09_financial.py", title="Financial ROI", icon=":material/attach_money:"),
    "Data & Model Info": st.Page("src/pages/05_methodology.py", title="Data & Model Info", icon=":material/info:"),
    "Account Management": st.Page("src/pages/10_account.py", title="Account Management", icon=":material/manage_accounts:"),
}


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH GATE
# ═══════════════════════════════════════════════════════════════════════════════
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    # ── NOT LOGGED IN → Show login page only (no sidebar) ──
    from src.pages.login import render_login
    render_login(st.session_state.app_users)

else:
    # ── LOGGED IN → Show dashboard with role-filtered sidebar ──
    role = st.session_state.get("user_role", "Viewer")
    user_name = st.session_state.get("user_name", "User")
    allowed = ROLE_PAGES.get(role, ["Overview"])

    # Filter pages by role — always set Overview as default
    nav_pages = []
    for name in allowed:
        if name in ALL_PAGES:
            page = ALL_PAGES[name]
            if name == "Overview":
                page = st.Page("src/pages/01_home.py", title="Overview",
                               icon=":material/home:", default=True)
            nav_pages.append(page)

    pg = st.navigation(nav_pages, position="hidden")

    # ── Custom Sidebar Construction ───────────────────────────────────────
    with st.sidebar:
        # 1. BRANDING & WORKSPACE
        st.markdown("### :material/architecture: G-SYNC")
        st.caption("Intelligence Platform")

        with st.container(border=True):
            st.markdown(f"**Workspace:** {user_name}")

        # 2. NAVIGATION — COMMAND CENTER (role-filtered)
        st.caption("COMMAND CENTER")
        for page_name in COMMAND_CENTER:
            if page_name in allowed and page_name in ALL_PAGES:
                st.page_link(ALL_PAGES[page_name], label=page_name,
                             icon=PAGE_ICONS.get(page_name, ":material/circle:"))

        # 3. NAVIGATION — INTELLIGENCE (role-filtered)
        has_intel = any(p in allowed for p in INTELLIGENCE)
        if has_intel:
            st.write("")  # Spacer
            st.caption("INTELLIGENCE")
            for page_name in INTELLIGENCE:
                if page_name in allowed and page_name in ALL_PAGES:
                    st.page_link(ALL_PAGES[page_name], label=page_name,
                                 icon=PAGE_ICONS.get(page_name, ":material/circle:"))

        # 4. NAVIGATION — ADMIN (role-filtered)
        has_admin = any(p in allowed for p in ADMIN_SECTION)
        if has_admin:
            st.write("")  # Spacer
            st.caption("ADMIN")
            for page_name in ADMIN_SECTION:
                if page_name in allowed and page_name in ALL_PAGES:
                    st.page_link(ALL_PAGES[page_name], label=page_name,
                                 icon=PAGE_ICONS.get(page_name, ":material/circle:"))

        # 5. FOOTER — STATUS & PROFILE
        st.divider()
        st.markdown("🟢 **All systems operational**")
        st.caption("Last sync 2 min ago")
        st.markdown(f"**{user_name}** · *{role}*")

        # 6. LOGOUT BUTTON
        if st.button("🚪 Logout", use_container_width=True):
            for key in ["authenticated", "user_name", "user_role", "username"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    pg.run()
