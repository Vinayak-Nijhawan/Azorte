"""
MOIL-GeoSync — Login Page
=========================
Session-state based authentication with role-based access control.
Manual login + one-click role cards + guest demo access.
"""

import hashlib
import streamlit as st


def render_login(users: dict):
    """Render the login page UI and handle authentication."""

    # ── Hide sidebar completely on login page ──
    st.markdown("""<style>
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="stSidebarCollapsedControl"] { display: none !important; }
        .block-container { max-width: 100% !important; padding: 0 !important; }
    </style>""", unsafe_allow_html=True)

    # ── Login Page CSS ──
    st.html("""
    <style>
        .login-brand {
            text-align: center;
            margin-bottom: 28px;
        }
        .login-brand-icon { font-size: 2.2rem; margin-bottom: 8px; }
        .login-brand h1 {
            font-size: 1.6rem !important; font-weight: 700 !important;
            color: #111827 !important; margin: 0 0 4px 0 !important;
            letter-spacing: -0.5px;
        }
        .login-brand p {
            font-size: 0.82rem !important; color: #6B7280 !important;
            margin: 0 !important;
        }
        .login-divider {
            display: flex; align-items: center; gap: 12px;
            margin: 20px 0; font-size: 0.75rem; color: #9CA3AF;
        }
        .login-divider::before, .login-divider::after {
            content: ''; flex: 1; height: 1px; background: #E5E7EB;
        }
        .login-section-label {
            font-size: 0.72rem !important; color: #6B7280 !important;
            text-transform: uppercase; letter-spacing: 1px;
            font-weight: 600 !important; margin-bottom: 12px !important;
            text-align: center;
        }
        .login-footer {
            text-align: center; margin-top: 28px; padding-top: 20px;
            border-top: 1px solid #F3F4F6;
        }
        .login-footer p {
            font-size: 0.7rem !important; color: #9CA3AF !important;
            margin: 2px 0 !important;
        }
    </style>
    """)

    # ── Layout: centered login card ──
    col_l, col_c, col_r = st.columns([1, 1.3, 1])

    with col_c:
        # Branding
        st.html("""
        <div class="login-brand">
            <div class="login-brand-icon">🏗️</div>
            <h1>G-SYNC</h1>
            <p>MOIL-GeoSync Intelligence Platform</p>
            <p>AI-Powered Manganese Operations</p>
        </div>
        """)

        # ── Manual Login Form ──
        with st.form("login_form", clear_on_submit=False, border=False):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("🔐 Sign In", use_container_width=True, type="primary")

        if submitted:
            if username and password:
                input_hash = hashlib.sha256(password.encode()).hexdigest()
                user = users.get(username.lower().strip())
                if user and user["password_hash"] == input_hash:
                    _do_login(user["name"], user["role"], username.lower().strip())
                else:
                    st.error("❌ Invalid username or password")
            else:
                st.warning("Please enter both username and password")

        # ── Divider ──
        st.html('<div class="login-divider">or quick login as</div>')

        # ── One-Click Role Buttons (styled as cards via CSS) ──
        st.html("""
        <div class="login-section-label">Select a Demo Role</div>
        <style>
            /* Make role buttons look like cards */
            div[data-testid="stHorizontalBlock"] > div > div > div > div > button[kind="secondary"] {
                min-height: 90px !important;
                border-radius: 10px !important;
                border: 1px solid #E5E7EB !important;
                background: #F9FAFB !important;
                color: #111827 !important;
                font-weight: 600 !important;
                font-size: 0.82rem !important;
                transition: all 0.2s ease !important;
            }
            div[data-testid="stHorizontalBlock"] > div > div > div > div > button[kind="secondary"]:hover {
                border-color: #000080 !important;
                background: rgba(0,0,128,0.04) !important;
                transform: translateY(-2px) !important;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
            }
        </style>
        """)

        _ROLE_CARDS = [
            ("👑", "Admin", "admin"),
            ("⛏️", "Mine Mgr", "mine_mgr"),
            ("🔬", "Geologist", "geologist"),
            ("🔧", "Operator", "operator"),
            ("👁️", "Viewer", "viewer"),
        ]

        cols = st.columns(5)
        for idx, (icon, label, uname) in enumerate(_ROLE_CARDS):
            with cols[idx]:
                if st.button(f"{icon}\n{label}", key=f"role_{uname}",
                             use_container_width=True):
                    user = users[uname]
                    _do_login(user["name"], user["role"], uname)

        # ── Divider ──
        st.html('<div class="login-divider">or</div>')

        # ── Guest Demo Button ──
        if st.button("👤 Continue as Guest (Full Demo Access)", use_container_width=True):
            _do_login("Guest User", "Admin", "guest")

        # ── Footer ──
        st.html("""
        <div class="login-footer">
            <p>Team Azorte · SIH 2026 · PS 26009</p>
            <p>© 2026 MOIL Limited · Ministry of Steel, Govt. of India</p>
        </div>
        """)


def _do_login(name: str, role: str, username: str):
    """Set session state and rerun."""
    st.session_state.authenticated = True
    st.session_state.user_name = name
    st.session_state.user_role = role
    st.session_state.username = username
    st.rerun()
