
import os

target_file = r"D:\PROYECTOS PROGRAMACIÓN\ANTIGRAVITY_PROJECTS\Plataformas\herramientas_gest\app.py"

with open(target_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Locate def view_dashboard(): to insert before it if possible
insert_idx = -1
for i, line in enumerate(lines):
    if "def view_dashboard" in line:
        insert_idx = i
        break

# The function code to insert
fn_code = [
    "\n",
    "# === FORCED INSERTION OF MISSING FUNCTION ===\n",
    "def render_login_page():\n",
    "    # Minimal Login Page\n",
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
    "        try:\n",
    "            st.image(\"logo_agent.png\", width=150)\n",
    "        except:\n",
    "            st.markdown(\"<h1 style='text-align: center;'>🗓️</h1>\", unsafe_allow_html=True)\n",
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
    "                    try:\n",
    "                        saved = auth.load_calendar_session(u)\n",
    "                        if saved:\n",
    "                            st.session_state.conf_calendar_id = saved\n",
    "                    except: pass\n",
    "                    st.rerun()\n",
    "                else:\n",
    "                    st.error(\"Acceso Denegado\")\n",
    "\n"
]

# We need to act on the list
if insert_idx != -1:
    print(f"Inserting at line {insert_idx}")
    # Insert before view_dashboard
    # Use standard list insertion
    # We must insert lines one by one or splice
    lines[insert_idx:insert_idx] = fn_code
else:
    print("Could not find view_dashboard, appending to end before main block")
    # Finding main block
    main_idx = -1
    for i, line in enumerate(lines):
        if "if __name__ == \"__main__\":" in line:
            main_idx = i
            break
    
    if main_idx != -1:
         lines[main_idx:main_idx] = fn_code
    else:
         lines.extend(fn_code)

with open(target_file, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Forced insertion complete.")
