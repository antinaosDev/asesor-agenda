
import os

target_file = r"D:\PROYECTOS PROGRAMACIÓN\ANTIGRAVITY_PROJECTS\Plataformas\herramientas_gest\app.py"

with open(target_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the start of the corrupted block (around 350-400)
# We look for the previous function end or the specific corrupted signature
start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if "def view_dashboard" in line:
        end_idx = i
        break
    if "def render_login_p" in line or "def render_login_pa" in line:
        start_idx = i

# If we can't find start_idx cleanly, let's look for "st.dataframe(df_u[safe_cols], hide_index=True)"
if start_idx == -1:
    for i, line in enumerate(lines):
        if "st.dataframe(df_u[safe_cols]" in line:
            start_idx = i + 1 # Start inserting after this
            break

if start_idx != -1 and end_idx != -1:
    print(f"Repairing lines {start_idx} to {end_idx}")
    
    # Keep lines before start
    new_lines = lines[:start_idx]
    
    # Insert clean render_login_page
    clean_code = [
        "\n",
        "def render_login_page():\n",
        "    # Similar to previous version but refined styling\n",
        "    st.markdown(\"\"\"\n",
        "    <style>\n",
        "        [data-testid=\"stSidebar\"] {display: none;}\n",
        "        .login-box {\n",
        "            background: rgba(24, 40, 42, 0.6);\n",
        "            backdrop-filter: blur(20px);\n",
        "            border: 1px solid rgba(13, 215, 242, 0.2);\n",
        "            border-radius: 16px;\n",
        "            padding: 3rem;\n",
        "            box-shadow: 0 0 40px rgba(0,0,0,0.5);\n",
        "            text-align: center;\n",
        "        }\n",
        "    </style>\n",
        "    \"\"\", unsafe_allow_html=True)\n",
        "\n",
        "    c1, c2, c3 = st.columns([1, 1.2, 1])\n",
        "    with c2:\n",
        "        st.markdown('<br>', unsafe_allow_html=True)\n",
        "\n",
        "        # Centered logo with optimized size\n",
        "        c_img1, c_img2, c_img3 = st.columns([1, 1, 1])\n",
        "        with c_img2:\n",
        "            try:\n",
        "                st.image(\"logo_agent.png\", width=150)\n",
        "            except:\n",
        "                st.markdown(\"<h1 style='text-align: center;'>🗓️</h1>\", unsafe_allow_html=True)\n",
        "\n",
        "        st.markdown(\"\"\"\n",
        "        <div class=\"login-box\" style=\"text-align: center;\">\n",
        "             <h1 style=\"font-size: 2.2rem; margin-bottom: 0.3rem; font-weight: 600;\">Asistente Ejecutivo AI</h1>\n",
        "             <p style=\"color: #0dd7f2; margin-bottom: 2rem; font-size: 0.95rem;\">🔐 Acceso Seguro</p>\n",
        "        </div>\n",
        "        \"\"\", unsafe_allow_html=True)\n",
        "\n",
        "        with st.form(\"login\"):\n",
        "            u = st.text_input(\"Usuario\", placeholder=\"admin\")\n",
        "            p = st.text_input(\"Contraseña\", type=\"password\", placeholder=\"••••••\")\n",
        "            if st.form_submit_button(\"Autenticar\", type=\"primary\", width=\"stretch\"):\n",
        "                valid, data = auth.login_user(u, p)\n",
        "                if valid:\n",
        "                    st.session_state.authenticated = True\n",
        "                    st.session_state.user_data_full = data\n",
        "                    st.session_state.license_key = u\n",
        "                    \n",
        "                    # AUTO-LOAD CALENDAR SESSION\n",
        "                    saved_calendar = auth.load_calendar_session(u)\n",
        "                    if saved_calendar:\n",
        "                        st.session_state.conf_calendar_id = saved_calendar\n",
        "                        st.session_state.connected_email = saved_calendar # Initial state\n",
        "                        st.toast(f\"📅 Calendario cargado: {saved_calendar[:30]}...\")\n",
        "                    \n",
        "                    st.rerun()\n",
        "                else:\n",
        "                    st.error(\"Acceso Denegado\")\n",
        "\n",
        "# --- MAIN VIEWS ---\n",
        "\n"
    ]
    
    new_lines.extend(clean_code)
    
    # Append lines from view_dashboard onwards
    new_lines.extend(lines[end_idx:])
    
    with open(target_file, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
        
    print("SUCCESS: File scheduled for repair.")
else:
    print(f"FAILED: Could not locate blocks. Start: {start_idx}, End: {end_idx}")

