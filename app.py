import streamlit as st
import os
import datetime
import json
import pandas as pd
import time
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv

# --- MODULE IMPORTS ---
import modules.auth as auth
import modules.notifications as notif

from modules.google_services import (
    get_calendar_service, get_tasks_service, get_sheets_service, get_gmail_credentials,
    fetch_emails_batch, clean_email_body, 
    get_task_lists, create_task_list, add_task_to_google, 
    delete_task_google, update_task_google, get_existing_tasks_simple,
    add_event_to_calendar, delete_event, optimize_event, COLOR_MAP
)
from modules.ai_core import (
    analyze_emails_ai, parse_events_ai, analyze_existing_events_ai,
    generate_work_plan_ai, generate_project_breakdown_ai
)

# Load environment variables
load_dotenv()

# --- Page Config ---
st.set_page_config(
    page_title="Panel Ejecutivo AI",
    page_icon="logo_agent.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- GLOBAL STYLES (THEME INJECTION) ---
def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Noto+Sans:wght@400;500;700&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');

        :root {
            --primary-neon: #0dd7f2;
            --bg-dark: #102022;
            --card-dark: #18282a;
            --text-white: #ffffff;
            --text-gray: #9cb6ba;
            --glass-border: rgba(255, 255, 255, 0.08);
        }

        /* Base Streamlit Overrides */
        .stApp {
            background-color: var(--bg-dark);
            color: var(--text-white);
            font-family: 'Space Grotesk', sans-serif;
        }

        h1, h2, h3, h4, .stMarkdown, div[data-testid="stMetricLabel"] {
            font-family: 'Space Grotesk', sans-serif !important;
        }

        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            background-color: #0e1c1e;
            border-right: 1px solid var(--glass-border);
        }
        
        /* Buttons */
        .stButton > button {
            background-color: transparent;
            border: 1px solid var(--glass-border);
            color: var(--primary-neon);
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        .stButton > button:hover {
            background-color: rgba(13, 215, 242, 0.1);
            border-color: var(--primary-neon);
            box-shadow: 0 0 15px rgba(13, 215, 242, 0.2);
            color: white;
        }

        /* Primary Action Buttons (Custom Class) */
        .primary-action-btn > button {
            background-color: var(--primary-neon) !important;
            color: #102022 !important;
            border: none;
            box-shadow: 0 0 15px rgba(13, 215, 242, 0.4);
        }
        .primary-action-btn > button:hover {
            box-shadow: 0 0 25px rgba(13, 215, 242, 0.6);
            transform: scale(1.02);
        }

        /* Inputs */
        .stTextInput > div > div > input, .stTextArea > div > div > textarea, .stDateInput > div > div > input {
            background-color: #161b1c;
            border: 1px solid var(--glass-border);
            color: white;
            border-radius: 8px;
        }
        .stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus {
            border-color: var(--primary-neon);
            box-shadow: 0 0 0 1px var(--primary-neon);
        }

        /* Glass Cards */
        .glass-panel {
            background: rgba(24, 40, 42, 0.4);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--glass-border);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
        }

        /* Metrics */
        div[data-testid="stMetricValue"] {
            color: var(--primary-neon);
            font-size: 2rem !important;
            text-shadow: 0 0 10px rgba(13, 215, 242, 0.3);
        }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 1rem;
            background-color: transparent;
            border-bottom: 1px solid var(--glass-border);
        }
        .stTabs [data-baseweb="tab"] {
            color: var(--text-gray);
            border-radius: 4px 4px 0 0;
        }
        .stTabs [aria-selected="true"] {
            background-color: rgba(13, 215, 242, 0.1);
            color: var(--primary-neon) !important;
            border-bottom: 2px solid var(--primary-neon);
        }

        /* Custom Scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        ::-webkit-scrollbar-track { background: #102022; }
        ::-webkit-scrollbar-thumb { background: #283739; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #3a4e51; }

    </style>
    """, unsafe_allow_html=True)

# --- HELPER UI FUNCTIONS ---

def render_header(title, subtitle=None):
    sub = f'<p style="color: #9cb6ba; font-size: 0.9rem; margin-top: -10px;">{subtitle}</p>' if subtitle else ''
    st.markdown(f"""
    <div style="border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 1rem; margin-bottom: 2rem;">
        <div style="display: flex; align-items: center; gap: 10px;">
            <span class="material-symbols-outlined" style="font-size: 32px; color: #0dd7f2;">auto_awesome</span>
            <h1 style="margin: 0; font-size: 2.5rem; font-weight: 700; background: linear-gradient(90deg, #fff, #9cb6ba); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{title}</h1>
        </div>
        {sub}
    </div>
    """, unsafe_allow_html=True)

def card_metric(label, value, icon, subtext=""):
    st.markdown(f"""
    <div class="glass-panel" style="padding: 1.2rem; display: flex; flex-direction: column; justify-content: space-between; height: 100%;">
        <div style="display: flex; justify-content: space-between; align-items: start;">
            <span style="color: #9cb6ba; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">{label}</span>
            <span class="material-symbols-outlined" style="color: #0dd7f2;">{icon}</span>
        </div>
        <div style="margin-top: 1rem;">
            <div style="color: white; font-size: 2rem; font-weight: 700; text-shadow: 0 0 15px rgba(13,215,242,0.2);">{value}</div>
            <div style="color: #6b7280; font-size: 0.75rem; margin-top: 4px;">{subtext}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_login_page():
    # Similar to previous version but refined styling
    st.markdown("""
    <style>
        [data-testid="stSidebar"] {display: none;}
        .login-box {
            background: rgba(24, 40, 42, 0.6);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(13, 215, 242, 0.2);
            border-radius: 16px;
            padding: 3rem;
            box-shadow: 0 0 40px rgba(0,0,0,0.5);
            text-align: center;
        }
    </style>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown('<br><br>', unsafe_allow_html=True)
        st.markdown("""
        <div class="login-box">
             <img src="app/logo_agent.png" style="width: 100px; margin-bottom: 1rem;">
             <!-- Fallback if image fails local load without helper, usually streamlit handles local files in root or static -->
             <!-- For simple local file usage in markdown html, we often need a helper or st.image. Let's use st.image for reliability in columns -->
        </div>
        """, unsafe_allow_html=True)
        
        st.image("logo_agent.png", width=120)
        
        st.markdown("""
        <div style="text-align: center;">
            <h1 style="font-size: 2rem; margin-bottom: 0.5rem; margin-top: 0;">Asistente Ejecutivo AI</h1>
            <p style="color: #9cb6ba; margin-bottom: 2rem;">Acceso Seguro</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login"):
            u = st.text_input("Usuario", placeholder="admin")
            p = st.text_input("Contraseña", type="password", placeholder="••••••")
            if st.form_submit_button("Autenticar", type="primary", use_container_width=True):
                valid, data = auth.login_user(u, p)
                if valid:
                    st.session_state.authenticated = True
                    st.session_state.user_data_full = data
                    st.session_state.license_key = u
                    st.rerun()
                else:
                    st.error("Acceso Denegado")

# --- MAIN VIEWS ---

def view_dashboard():
    render_header("Panel Ejecutivo", "Resumen Matutino y Estado Diario")
    
    # Context Loading
    calendar_id = st.session_state.get('connected_email', '')
    if not calendar_id:
        st.info("⚠️ Por favor conecta tu Google Calendar en configuración para ver tu panel.")
        return

    # --- Top Row: Stats ---
    c1, c2, c3, c4 = st.columns(4)
    
    # Fetch Data (Cached)
    events = []
    try:
        svc = get_calendar_service()
        if svc:
            now = datetime.datetime.now()
            t_min = now.replace(hour=0, minute=0, second=0).isoformat() + 'Z'
            t_max = now.replace(hour=23, minute=59, second=59).isoformat() + 'Z'
            events = svc.events().list(
                calendarId=calendar_id, timeMin=t_min, timeMax=t_max, singleEvents=True, orderBy='startTime'
            ).execute().get('items', [])
    except: pass

    total_events = len(events)
    # Calculate hours
    hours = 0
    for e in events:
        try:
            start = e['start'].get('dateTime')
            end = e['end'].get('dateTime')
            if start and end:
                s_dt = datetime.datetime.fromisoformat(start)
                e_dt = datetime.datetime.fromisoformat(end)
                hours += (e_dt - s_dt).total_seconds() / 3600
        except: pass

    with c1: card_metric("Total Eventos", str(total_events), "event", "Agenda de Hoy")
    with c2: card_metric("Horas Reunión", f"{hours:.1f}h", "schedule", "Carga Total")
    with c3: card_metric("Tareas Pendientes", "5", "check_circle", "Alta Prioridad") # Placeholder
    with c4: card_metric("Bandeja Entrada", "12", "mail", "No Leídos Importantes") # Placeholder

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Split View: Morning Briefing UI & Timeline ---
    col_brief, col_timeline = st.columns([1, 1.5])
    
    with col_brief:
        # Recreating the HTML "Morning Briefing Card"
        st.markdown(f"""
        <div class="glass-panel" style="position: relative; overflow: hidden; height: 100%;">
            <div style="position: absolute; top: -50px; right: -50px; width: 200px; height: 200px; background: rgba(13,215,242,0.1); border-radius: 50%; filter: blur(60px);"></div>
            <div style="display: flex; gap: 1rem; align-items: center; margin-bottom: 1.5rem;">
                 <div style="width: 40px; height: 40px; border-radius: 50%; background: rgba(13,215,242,0.2); display: flex; align-items: center; justify-content: center;">
                    <span class="material-symbols-outlined" style="color: #0dd7f2;">auto_awesome</span>
                 </div>
                 <h3 style="margin: 0; font-size: 1.25rem;">Informe Diario</h3>
            </div>
            
            <div style="background: rgba(17,23,24,0.5); padding: 1.25rem; border-left: 4px solid #0dd7f2; border-radius: 8px; margin-bottom: 1.5rem;">
                <p style="font-size: 1.1rem; line-height: 1.6; color: #e2e8f0;">
                    Tienes <strong style="color: white;">{total_events} eventos</strong> agendados hoy, totalizando <strong style="color: #0dd7f2;">{hours:.1f} horas</strong> de reuniones. 
                    {'Tu tarde parece libre para trabajo profundo.' if hours < 4 else 'Es un día pesado de reuniones, planifica descansos.'}
                </p>
            </div>

            <div style="display: flex; flex-direction: column; gap: 0.8rem;">
                <div style="display: flex; gap: 10px; align-items: center; font-size: 0.9rem; color: #9cb6ba;">
                    <span class="material-symbols-outlined" style="color: #eab308; font-size: 1.2rem;">warning</span>
                    <span>Prioridad: Revisar <strong>Reportes Q3</strong> antes de las 14:00.</span>
                </div>
                 <div style="display: flex; gap: 10px; align-items: center; font-size: 0.9rem; color: #9cb6ba;">
                    <span class="material-symbols-outlined" style="color: #0dd7f2; font-size: 1.2rem;">mail</span>
                    <span>Remitente Top: <strong>Director General</strong> (Urgente)</span>
                </div>
            </div>
            <br>
        </div>
        """, unsafe_allow_html=True)

    with col_timeline:
        st.markdown("### 🗓️ Línea de Tiempo")
        # Visual Timeline using Plotly (Gantt style)
        if events:
            # Prepare DF
            data = []
            for e in events:
                start = e['start'].get('dateTime')
                end = e['end'].get('dateTime')
                if start and end:
                    data.append(dict(Task=e.get('summary', 'Ocupado'), Start=start, Finish=end, Color=e.get('colorId', '1')))
            
            if data:
                df = pd.DataFrame(data)
                fig = px.timeline(df, x_start="Start", x_end="Finish", y="Task", color="Color", height=350)
                fig.update_yaxes(autorange="reversed")
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white', family="Space Grotesk"),
                    xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)'),
                    margin=dict(l=10, r=10, t=10, b=10)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay eventos agendados para hoy.")
        else:
             st.info("No se encontraron eventos.")

def view_create():
    render_header("Centro de Comandos", "Creación de Eventos con IA")
    
    col_input, col_viz = st.columns([1, 1])

    with col_input:
        st.markdown("### 🗣️ Entrada de Lenguaje Natural")
        with st.form("create_event"):
            prompt = st.text_area("¿Qué deseas agendar?", height=200, 
                                placeholder="Ejemplo: Reunión con Sara el próximo martes a las 14:00 sobre el presupuesto Q3...")
            
            c_btn1, c_btn2 = st.columns([1, 4])
            with c_btn1:
                submitted = st.form_submit_button("Procesar", type="primary", use_container_width=True)
        
        if submitted and prompt:
            with st.spinner("🧠 Analizando patrones y extrayendo datos..."):
                events = parse_events_ai(prompt)
                st.session_state.draft_events = events

    with col_viz:
        st.markdown("### 🧠 Procesador Semántico")
        # Visual decoration
        st.markdown(f"""
        <div class="glass-panel" style="height: 250px; display: flex; align-items: center; justify-content: center; position: relative; overflow: hidden;">
            <div style="position: absolute; width: 100%; height: 100%; background-image: radial-gradient(rgba(13, 215, 242, 0.1) 1px, transparent 1px); background-size: 20px 20px; opacity: 0.3;"></div>
            <div style="text-align: center;">
                <span class="material-symbols-outlined" style="font-size: 64px; color: #0dd7f2; opacity: 0.8; animation: pulse 2s infinite;">memory</span>
                <p style="color: #9cb6ba; margin-top: 1rem; font-family: monospace;">ESPERANDO NUEVA ENTRADA</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    if 'draft_events' in st.session_state and st.session_state.draft_events:
        st.divider()
        st.markdown("### 📝 Eventos Propuestos")
        
        for i, ev in enumerate(st.session_state.draft_events):
            # Styling specific to the event card in user's example
            bg_accent = "#18282a"
            summary = ev.get('summary', 'Sin Título')
            time_str = f"{ev.get('start_time')} -> {ev.get('end_time')}"
            desc = ev.get('description', 'Sin detalles.')
            
            st.markdown(f"""
            <div class="glass-panel" style="border-left: 4px solid #0dd7f2;">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <h3 style="margin: 0; color: white;">{summary}</h3>
                        <p style="color: #9cb6ba; font-size: 0.9rem; margin-top: 5px;">{time_str}</p>
                    </div>
                     <span class="material-symbols-outlined" style="color: #0dd7f2;">event</span>
                </div>
                <div style="background: rgba(0,0,0,0.2); padding: 10px; border-radius: 6px; margin-top: 10px;">
                    <p style="color: #ccc; font-size: 0.9rem;">{desc}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"Confirmar y Agendar '{summary}'", key=f"btn_add_{i}"):
                cal_id = st.session_state.get('connected_email')
                if not cal_id: st.error("Por favor conecta tu email primero.")
                else:
                    svc = get_calendar_service()
                    ok, msg = add_event_to_calendar(svc, ev, cal_id)
                    if ok: st.success("¡Evento Creado!")
                    else: st.error(msg)


def view_planner():
    render_header("Planificador Inteligente", "Orquestación Semanal de Tareas")
    
    calendar_context_str = ""
    # Simplified Logic from original app.py
    # ... (Logic for fetching calendar context would go here)
    
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown("### 📥 Tareas de Entrada")
        tasks_text = st.text_area("Metas para la semana", height=150, placeholder="- Hacer X\n- Terminar Y")
        if st.button("Generar Plan", type="primary"):
             with st.spinner("Optimizando agenda..."):
                 plan = generate_work_plan_ai(tasks_text, "")
                 st.session_state.weekly_plan = plan

    with c2:
        st.markdown("### 🗓️ Vista Kanban")
        if 'weekly_plan' in st.session_state:
            cols = st.columns(5)
            # Translate keys if they come back in English or enforce Spanish prompts later
            days_map = {
                "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles", "Thursday": "Jueves", "Friday": "Viernes"
            }
            # Fallback days list if keys are missing
            days_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            
            for i, day_en in enumerate(days_en):
                day_es = days_map[day_en]
                with cols[i]:
                    st.markdown(f"**{day_es}**")
                    # Try fetch by English or Spanish Key
                    tasks = st.session_state.weekly_plan.get(day_en, st.session_state.weekly_plan.get(day_es, []))
                    
                    for t in tasks:
                        st.markdown(f"""
                        <div style="background: #18282a; padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); margin-bottom: 8px; font-size: 0.85rem;">
                            {t}
                        </div>
                        """, unsafe_allow_html=True)
        else:
            st.info("Sin plan activo. Ingresa tareas para generar.")


def view_inbox():
    render_header("Inteligencia de Bandeja", "Filtrado de Correo con IA")
    # Porting functionality...
    if st.button("🔄 Conectar y Escanear Inbox"):
        creds = get_gmail_credentials()
        if creds:
             # Logic to fetch
             pass
    st.info("Módulo en Construcción en la nueva UI.")

def view_optimize():
    render_header("Optimizador de Agenda", "Auditoría de Tiempo")
    st.info("Módulo en Construcción en la nueva UI.")

# --- NAVIGATION CONTROLLER ---

def main_app():
    # Sidebar Navigation mimicking the "Rail"
    with st.sidebar:
        col_logo, col_text = st.columns([1, 2])
        with col_logo:
             st.image("logo_agent.png", width=70)
        with col_text:
             st.markdown("""
             <div style="padding-top: 10px;">
                <h3 style="margin: 0; font-size: 1.1rem;">Asistente</h3>
                <p style="font-size: 0.8rem; color: #9cb6ba; margin: 0;">Premium AI</p>
             </div>
             """, unsafe_allow_html=True)
             
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Navigation Buttons (using radio for state)
        # Using icons in radio labels not supported natively well without hacking CSS, keeping text simple
        nav_options = {
            "Dashboard": "Panel Principal",
            "Create": "Crear Evento",
            "Planner": "Planificador",
            "Inbox": "Bandeja IA",
            "Optimize": "Optimizar"
        }
        
        selection = st.radio("Navegación", list(nav_options.keys()), format_func=lambda x: nav_options[x], label_visibility="collapsed")
        
        st.divider()
        st.caption("Configuración")
        st.text_input("ID Calendario", value=st.session_state.get('connected_email', ''), key='connected_email_input')
        if st.session_state.connected_email_input != st.session_state.get('connected_email', ''):
             st.session_state.connected_email = st.session_state.connected_email_input

    # Main Router
    if selection == "Dashboard": view_dashboard()
    elif selection == "Create": view_create()
    elif selection == "Planner": view_planner()
    elif selection == "Inbox": view_inbox()
    elif selection == "Optimize": view_optimize()

# --- ENTRY POINT ---

if __name__ == "__main__":
    inject_custom_css()
    
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    # Debug Bypass
    # st.session_state.authenticated = True

    if not st.session_state.authenticated:
        render_login_page()
    else:
        main_app()
