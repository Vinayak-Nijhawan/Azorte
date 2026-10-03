"""
MOIL-GeoSync — Login Page
=========================
Session-state based authentication with role-based access control.
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
        .login-wrapper {
            min-height: 90vh;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        .login-card {
            background: #FFFFFF;
            border: 1px solid rgba(17, 24, 39, 0.1);
            border-radius: 16px;
            padding: 48px 40px 36px;
            width: 100%;
            max-width: 420px;
            box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
        }
        .login-brand {
            text-align: center;
            margin-bottom: 32px;
        }
        .login-brand-icon {
            font-size: 2.2rem;
            margin-bottom: 8px;
        }
        .login-brand h1 {
            font-size: 1.6rem !important;
            font-weight: 700 !important;
            color: #111827 !important;
            margin: 0 0 4px 0 !important;
            letter-spacing: -0.5px;
        }
        .login-brand p {
            font-size: 0.82rem !important;
            color: #6B7280 !important;
            margin: 0 !important;
        }
        .login-divider {
            display: flex;
            align-items: center;
            gap: 12px;
            margin: 16px 0;
            font-size: 0.75rem;
            color: #9CA3AF;
        }
        .login-divider::before, .login-divider::after {
            content: '';
            flex: 1;
            height: 1px;
            background: #E5E7EB;
        }
        .login-footer {
            text-align: center;
            margin-top: 28px;
            padding-top: 20px;
            border-top: 1px solid #F3F4F6;
        }
        .login-footer p {
            font-size: 0.7rem !important;
            color: #9CA3AF !important;
            margin: 2px 0 !important;
        }
        .login-roles {
            background: #F9FAFB;
            border: 1px solid #E5E7EB;
            border-radius: 8px;
            padding: 12px 16px;
            margin-top: 16px;
        }
        .login-roles summary {
            font-size: 0.72rem;
            color: #6B7280;
            cursor: pointer;
            font-weight: 500;
        }
        .login-roles table {
            width: 100%;
            font-size: 0.7rem;
            color: #374151;
            margin-top: 8px;
            border-collapse: collapse;
        }
        .login-roles td {
            padding: 3px 8px;
            border-bottom: 1px solid #F3F4F6;
        }
        .login-roles td:first-child {
            font-family: 'SF Mono', 'Fira Code', monospace;
            font-weight: 500;
            color: #111827;
        }
    </style>
    """)

    # ── Layout: centered login card ──
    col_l, col_c, col_r = st.columns([1, 1.2, 1])

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

        # Login form
        with st.form("login_form", clear_on_submit=False, border=False):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("🔐 Sign In", use_container_width=True, type="primary")

        if submitted:
            if username and password:
                input_hash = hashlib.sha256(password.encode()).hexdigest()
                user = users.get(username.lower().strip())
                if user and user["password_hash"] == input_hash:
                    st.session_state.authenticated = True
                    st.session_state.user_name = user["name"]
                    st.session_state.user_role = user["role"]
                    st.session_state.username = username.lower().strip()
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password")
            else:
                st.warning("Please enter both username and password")

        # Divider
        st.html('<div class="login-divider">or</div>')

        # Guest Demo button
        if st.button("👤 Continue as Guest (Full Demo Access)", use_container_width=True):
            st.session_state.authenticated = True
            st.session_state.user_name = "Guest User"
            st.session_state.user_role = "Admin"
            st.session_state.username = "guest"
            st.rerun()

        # Footer
        st.html("""
        <div class="login-footer">
            <p>Team Azorte · SIH 2026 · PS 26009</p>
            <p>© 2026 MOIL Limited · Ministry of Steel, Govt. of India</p>
        </div>
        """)

        # Demo credentials hint
        st.html("""
        <details class="login-roles">
            <summary>📋 Demo Credentials</summary>
            <table>
                <tr><td>admin</td><td>admin123</td><td>👑 Full Access</td></tr>
                <tr><td>mine_mgr</td><td>mine2026</td><td>⛏️ Mine Manager</td></tr>
                <tr><td>geologist</td><td>geo2026</td><td>🔬 Geologist</td></tr>
                <tr><td>operator</td><td>ops2026</td><td>🔧 Operator</td></tr>
                <tr><td>viewer</td><td>view2026</td><td>👁️ Viewer</td></tr>
            </table>
        </details>
        """)
