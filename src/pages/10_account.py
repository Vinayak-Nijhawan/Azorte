"""
MOIL-GeoSync — Account Management
===================================
Admin: create accounts for ANY role.
Mine Manager: create accounts ONLY for Operator role.
Accounts exist in-memory only — reset on app restart.
"""

import os
import sys
import hashlib
import streamlit as st
import pandas as pd

# Load global CSS
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from utils import load_css
load_css()


# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════

st.html("""
<div class="fd-header">
    <div class="fd-header-left">
        <h1>👥 Account Management</h1>
        <div class="fd-subtitle">Create & Manage User Accounts · MOIL-GeoSync</div>
    </div>
    <div class="fd-header-right">
        <span class="fd-tag">🔐 Admin Panel</span>
        <span class="fd-live"><span class="fd-live-dot"></span> OPERATIONAL</span>
    </div>
</div>
""")


# ═══════════════════════════════════════════════════════════════════════════════
# ACCESS CONTROL
# ═══════════════════════════════════════════════════════════════════════════════

current_role = st.session_state.get("user_role", "Viewer")
current_user = st.session_state.get("user_name", "Unknown")

if current_role not in ("Admin", "Mine Manager"):
    st.error("🚫 Access denied. Only Admin and Mine Manager can access this page.")
    st.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION INFO
# ═══════════════════════════════════════════════════════════════════════════════

st.info(
    "ℹ️ **Session-Only Storage:** Accounts created here exist only for this session "
    "and reset if the app restarts. A persistent database will be added before any "
    "offline/production deployment."
)


# ═══════════════════════════════════════════════════════════════════════════════
# ROLE OPTIONS BASED ON CURRENT USER
# ═══════════════════════════════════════════════════════════════════════════════

ALL_ROLES = ["Admin", "Mine Manager", "Geologist", "Operator", "Viewer"]

if current_role == "Admin":
    allowed_roles = ALL_ROLES
    st.caption(f"👑 Logged in as **{current_user}** (Admin) — can create accounts for any role")
elif current_role == "Mine Manager":
    allowed_roles = ["Operator"]
    st.caption(f"⛏️ Logged in as **{current_user}** (Mine Manager) — can create Operator accounts only")


# ═══════════════════════════════════════════════════════════════════════════════
# CREATE ACCOUNT FORM
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("### ➕ Create New Account")

with st.form("create_account_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        new_username = st.text_input("Username", placeholder="e.g. john_doe")
        new_password = st.text_input("Password", type="password", placeholder="Set a password")
    with col2:
        new_display_name = st.text_input("Display Name", placeholder="e.g. John Doe")
        if len(allowed_roles) == 1:
            new_role = allowed_roles[0]
            st.text_input("Role", value="Operator", disabled=True)
        else:
            new_role = st.selectbox("Role", allowed_roles)

    create_submitted = st.form_submit_button("✅ Create Account", use_container_width=True, type="primary")

if create_submitted:
    # Validation
    if not new_username or not new_display_name or not new_password:
        st.error("❌ All fields are required.")
    elif len(new_username.strip()) < 3:
        st.error("❌ Username must be at least 3 characters.")
    elif len(new_password) < 4:
        st.error("❌ Password must be at least 4 characters.")
    elif new_username.lower().strip() in st.session_state.get("app_users", {}):
        st.error(f"❌ Username `{new_username}` already exists.")
    else:
        # Hash password and create account
        password_hash = hashlib.sha256(new_password.encode()).hexdigest()
        clean_username = new_username.lower().strip()

        # Add to session-state users dict
        if "app_users" in st.session_state:
            st.session_state.app_users[clean_username] = {
                "name": new_display_name.strip(),
                "role": new_role,
                "password_hash": password_hash,
            }
            st.success(f"✅ Account created: **{new_display_name}** ({new_role}) — username: `{clean_username}`")
            st.toast(f"👤 New {new_role} account created: {new_display_name}", icon="✅")
        else:
            st.error("⚠️ User store not initialized. Please restart the app.")


# ═══════════════════════════════════════════════════════════════════════════════
# CURRENT ACCOUNTS TABLE
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown("### 📋 Current Accounts")

users_dict = st.session_state.get("app_users", {})

if users_dict:
    rows = []
    for uname, udata in users_dict.items():
        role = udata["role"]
        role_icons = {
            "Admin": "👑", "Mine Manager": "⛏️", "Geologist": "🔬",
            "Operator": "🔧", "Viewer": "👁️"
        }
        rows.append({
            "Username": uname,
            "Display Name": udata["name"],
            "Role": f"{role_icons.get(role, '👤')} {role}",
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"Total accounts: **{len(rows)}**")
else:
    st.info("No accounts found.")
