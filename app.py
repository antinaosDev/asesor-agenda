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
    add_event_to_calendar, delete_event, optimize_event, update_event_calendar, COLOR_MAP
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
        
        # Use st.image for robust local file rendering
        c_img1, c_img2, c_img3 = st.columns([1, 1, 1])
        with c_img2:
             st.image("logo_agent.png", width=120)
        
        st.markdown("""
        <div class="login-box">
             <h1 style="font-size: 2rem; margin-bottom: 0.5rem;">Asistente Ejecutivo AI</h1>
             <p style="color: #9cb6ba; margin-bottom: 2rem;">Acceso Seguro</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Removed redundant st.image and markdown text below box to clean up UI as requested
        
        with st.form("login"):
            u = st.text_input("Usuario", placeholder="admin")
            p = st.text_input("Contraseña", type="password", placeholder="••••••")
            if st.form_submit_button("Autenticar", type="primary", width="stretch"):
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

    today_events = []
    
    # Calculate hours and Filter Today
    hours = 0
    try:
        # We need to filter events strictly for TODAY to make the "Agenda de Hoy" metric accurate
        # The list call above gets 00:00 to 23:59 so it should be correct for today's events.
        for e in events:
            # Check for All Day Events (date only) vs Timed Events (dateTime)
            start = e['start'].get('dateTime')
            end = e['end'].get('dateTime')
            
            if start and end: 
                # Timed Event
                try:
                    s_dt = datetime.datetime.fromisoformat(start)
                    e_dt = datetime.datetime.fromisoformat(end)
                    duration = (e_dt - s_dt).total_seconds() / 3600
                    hours += duration
                except: pass
            elif e['start'].get('date'):
                # All Day Event - Usually doesn't count towards "Meeting Hours" load in the same way, or count as 8h?
                # Let's count as 0 for "Meeting Hours" but keep in "Total Events" to avoid skewing "3000h" errors
                pass
            
            today_events.append(e) # Since query was time-boxed to today, all are today
    except Exception as e:
        print(f"Error calc: {e}")

    total_events = len(today_events)

    # --- REAL METRICS: TASKS & EMAILS ---
    pending_tasks_count = 0
    tasks_svc = get_tasks_service()
    if tasks_svc:
        try:
            tasks_list = get_existing_tasks_simple(tasks_svc)
            pending_tasks_count = len(tasks_list)
        except: pass

    # Fetch Unread Emails Count (Approx)
    unread_emails_count = 0
    creds = get_gmail_credentials()
    if creds:
        try:
            from googleapiclient.discovery import build
            svc_gmail = build('gmail', 'v1', credentials=creds)
            # Just get profile or messages label count for lighter query
            results = svc_gmail.users().messages().list(userId='me', q="is:unread -category:promotions -category:social", maxResults=50).execute()
            if 'messages' in results:
                unread_emails_count = len(results['messages']) # Capped at 50 for speed
                if unread_emails_count == 50: unread_emails_count = "50+"
        except: pass

    with c1: card_metric("Total Eventos", str(total_events), "event", "Agenda de Hoy")
    with c2: card_metric("Horas Reunión", f"{hours:.1f}h", "schedule", "Carga Total")
    with c3: card_metric("Tareas Pendientes", str(pending_tasks_count), "check_circle", "Google Tasks")
    with c4: card_metric("Bandeja Entrada", str(unread_emails_count), "mail", "No Leídos (Prioritarios)")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Split View: Morning Briefing UI & Timeline ---
    col_brief, col_timeline = st.columns([1, 1.5])
    

    with col_brief:
        # Recreating the HTML "Morning Briefing Card" - FIXED HTML Rendering
        # Completely flattened HTML string to prevent indentation issues
        advice_text = 'Tu tarde parece libre para trabajo profundo.' if hours < 4 else 'Es un día pesado de reuniones, planifica descansos.'
        
        st.markdown(f"""<div class="glass-panel" style="position: relative; overflow: hidden; height: 100%;"><div style="position: absolute; top: -50px; right: -50px; width: 200px; height: 200px; background: rgba(13,215,242,0.1); border-radius: 50%; filter: blur(60px);"></div><div style="display: flex; gap: 1rem; align-items: center; margin-bottom: 1.5rem;"><div style="width: 40px; height: 40px; border-radius: 50%; background: rgba(13,215,242,0.2); display: flex; align-items: center; justify-content: center;"><span class="material-symbols-outlined" style="color: #0dd7f2;">auto_awesome</span></div><h3 style="margin: 0; font-size: 1.25rem;">Informe Diario</h3></div><div style="background: rgba(17,23,24,0.5); padding: 1.25rem; border-left: 4px solid #0dd7f2; border-radius: 8px; margin-bottom: 1.5rem;"><p style="font-size: 1.1rem; line-height: 1.6; color: #e2e8f0;">Tienes <strong style="color: white;">{total_events} eventos</strong> agendados hoy, totalizando <strong style="color: #0dd7f2;">{hours:.1f} horas</strong> de reuniones. {advice_text}</p></div><div style="display: flex; flex-direction: column; gap: 0.8rem;"><div style="display: flex; gap: 10px; align-items: center; font-size: 0.9rem; color: #9cb6ba;"><span class="material-symbols-outlined" style="color: #eab308; font-size: 1.2rem;">warning</span><span>Revisar <strong>Google Tasks</strong> para pendientes urgentes.</span></div> <div style="display: flex; gap: 10px; align-items: center; font-size: 0.9rem; color: #9cb6ba;"><span class="material-symbols-outlined" style="color: #0dd7f2; font-size: 1.2rem;">mail</span><span>Revisar bandeja para nuevos <strong>correos prioritarios</strong>.</span></div></div><br></div>""", unsafe_allow_html=True)

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
                st.plotly_chart(fig, width="stretch")
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
                submitted = st.form_submit_button("Procesar", type="primary", width="stretch")
        
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
    
    mode = st.radio("Modo de Planificación", ["Semana Estándar (Manual + Calendario)", "Desglosar Proyecto (Eventos Largos)"], horizontal=True)
    
    calendar_context_str = ""
    calendar_id = st.session_state.get('connected_email', '')
    
    # Common Calendar Fetch (Optimized)
    if 'c_events_cache' not in st.session_state:
         st.session_state.c_events_cache = []
         
    # Always fetch if cache empty or requested (Only if email connected)
    if not st.session_state.c_events_cache and calendar_id:
        svc = get_calendar_service()
        if svc:
            try:
                today = datetime.date.today()
                t_min = datetime.datetime(today.year, 1, 1).isoformat() + 'Z'
                t_max = datetime.datetime(today.year, 12, 31, 23, 59, 59).isoformat() + 'Z'
                
                st.session_state.c_events_cache = svc.events().list(
                    calendarId=calendar_id, timeMin=t_min, timeMax=t_max, 
                    singleEvents=True, orderBy='startTime', maxResults=2000,
                    fields="items(summary,start,end,description)" 
                ).execute().get('items', [])
            except: pass
    # Simplified Logic from original app.py
    # ... (Logic for fetching calendar context would go here)
    
    if mode == "Semana Estándar (Manual + Calendario)":
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown("### 📥 Tareas de Entrada")
            
            use_calendar = st.checkbox("📥 Considerar eventos (Contexto)", value=True)
            
            # Context Logic
            if use_calendar and st.session_state.c_events_cache:
                 target_date = datetime.date.today()
                 s_week = target_date - datetime.timedelta(days=target_date.weekday())
                 e_week = s_week + datetime.timedelta(days=6)
                 
                 ctx_lines = []
                 for e in st.session_state.c_events_cache:
                     try:
                         start_str = e['start'].get('dateTime', e['start'].get('date'))
                         # Simple check if event is in current week
                         if start_str > s_week.isoformat() and start_str < e_week.isoformat():
                             summ = e.get('summary', 'Evento')
                             ctx_lines.append(f"- {start_str}: {summ}")
                     except: pass
                 calendar_context_str = "\\n".join(ctx_lines)

            tasks_text = st.text_area("Metas para la semana", height=150, placeholder="- Hacer X\\n- Terminar Y")
            if st.button("Generar Plan", type="primary"):
                 with st.spinner("Optimizando agenda..."):
                     plan = generate_work_plan_ai(tasks_text, calendar_context_str)
                     st.session_state.weekly_plan = plan
                     st.session_state.plan_type = 'weekly'

        with c2:
            st.markdown("### 🗓️ Vista Kanban")
            if 'weekly_plan' in st.session_state and st.session_state.get('plan_type') == 'weekly':
                cols = st.columns(5)
                days_map = {
                    "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles", "Thursday": "Jueves", "Friday": "Viernes"
                }
                days_en = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
                
                tasks_to_sync = []
                
                for i, day_en in enumerate(days_en):
                    day_es = days_map[day_en]
                    with cols[i]:
                        st.markdown(f"**{day_es}**")
                        tasks = st.session_state.weekly_plan.get(day_en, st.session_state.weekly_plan.get(day_es, []))
                        
                        for t in tasks:
                            st.markdown(f"""
                            <div style="background: #18282a; padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05); margin-bottom: 8px; font-size: 0.85rem;">
                                {t}
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Prepare for sync
                            tasks_to_sync.append({"title": t, "notes": f"Planificado para {day_es}", "due": None})
                
                st.divider()
                if st.button("🚀 Sincronizar con Google Tasks"):
                    tasks_svc = get_tasks_service()
                    if tasks_svc:
                        bar = st.progress(0)
                        for idx, t_item in enumerate(tasks_to_sync):
                            add_task_to_google(tasks_svc, "@default", t_item['title'], t_item['notes'])
                            bar.progress((idx+1)/len(tasks_to_sync))
                        st.success("¡Tareas sincronizadas!")
            else:
                st.info("Sin plan activo. Ingresa tareas para generar.")

    else: # PROJECT BREAKDOWN MODE
        st.markdown("### 🔨 Desglosar Proyecto Grande")
        st.info("Busca eventos largos (>3 días) para desglosarlos.")
        
        long_events_opts = []
        for e in st.session_state.c_events_cache:
            try:
                start = e['start'].get('dateTime', e['start'].get('date'))
                end = e['end'].get('dateTime', e['end'].get('date'))
                # Simple heuristic for long event (e.g. string compare or proper parsing if needed)
                # For now just show all to let user pick
                summ = e.get('summary', 'Sin Título')
                long_events_opts.append(f"{summ} | {start}")
            except: pass
            
        selected_proj = st.selectbox("Selecciona Proyecto/Evento:", long_events_opts)
        
        extra_context = st.text_area("📝 Contexto / Documentación (Opcional)", height=100, placeholder="Pega aquí correos, requerimientos o detalles específicos para que la IA los considere...")
        
        uploaded_file = st.file_uploader("📂 Subir Documentos (PDF/TXT)", type=["pdf", "txt"])
        if uploaded_file:
            try:
                file_text = ""
                if uploaded_file.type == "application/pdf":
                    import pypdf
                    reader = pypdf.PdfReader(uploaded_file)
                    for page in reader.pages:
                        file_text += page.extract_text() + "\n"
                else: # txt
                    file_text = uploaded_file.read().decode("utf-8")
                
                if file_text:
                    # OPTIMIZATION: Truncate for Qwen 32B Limit (6k TPM is tight)
                    # 15k chars is roughly 4-5k tokens, leaving room for prompt + output
                    MAX_CHARS = 15000
                    if len(file_text) > MAX_CHARS:
                        file_text = file_text[:MAX_CHARS] + "\n... [TRUNCADO POR LIMITE DE CREDITOS]"
                        st.warning(f"⚠️ Documento largo. Se ha truncado a {MAX_CHARS} caracteres para cuidar tus créditos de IA.")
                    
                    extra_context += f"\n\n--- DOCUMENTO ADJUNTO ({uploaded_file.name}) ---\n{file_text}"
                    st.toast(f"📄 Documento '{uploaded_file.name}' procesado.")
            except Exception as e:
                st.error(f"Error leyendo archivo: {e}")

        if st.button("Desglosar", type="primary", width="stretch"):
             if selected_proj:
                 with st.spinner("Generando Roadmap..."):
                     # Parse Title and Date from string "Title | Date"
                     parts = selected_proj.split("|")
                     p_title = parts[0].strip()
                     p_date = parts[1].strip() if len(parts) > 1 else str(datetime.date.today())
                     
                     breakdown = generate_project_breakdown_ai(p_title, "Proyecto extraído de calendario", p_date, "", extra_context=extra_context)
                     st.session_state.project_plan = breakdown
                     st.session_state.plan_type = 'project'
        
        if 'project_plan' in st.session_state and st.session_state.get('plan_type') == 'project':
             st.markdown("##### 📋 Roadmap Sugerido")
             
             # Parse and display items individually
             plan_data = st.session_state.project_plan
             
             # Handle list of dicts or raw list
             if isinstance(plan_data, list):
                 tasks_to_add = []
                 for i, item in enumerate(plan_data):
                     # Heuristic to handle string or dict items
                     if isinstance(item, dict):
                         title = item.get('title', 'Tarea')
                         date = item.get('date', '')
                         notes = item.get('notes', '')
                         label = f"**{title}** ({date}) - {notes}"
                     else:
                         label = str(item)
                         title = str(item)
                         date = ""
                         notes = ""
                         
                     if st.checkbox(label, key=f"pj_task_{i}", value=True):
                         tasks_to_add.append({"title": title, "notes": notes, "date": date})
                 
                 if st.button("🚀 Añadir Tareas Seleccionadas a Google Tasks", type="primary"):
                     tasks_svc = get_tasks_service()
                     if tasks_svc:
                         # 1. Create Parent Task
                         proj_title = selected_proj.split("|")[0].strip() if selected_proj else "Proyecto Nuevo"
                         with st.spinner(f"Creando tarea principal '{proj_title}'..."):
                             parent_task = add_task_to_google(tasks_svc, "@default", proj_title, f"Proyecto generado por AI: {len(tasks_to_add)} tareas.")
                         
                         if parent_task:
                             parent_id = parent_task['id']
                             st.toast(f"📂 Carpeta creada: {proj_title}")
                             
                             # 2. Add Subtasks
                             bar = st.progress(0)
                             for idx, t in enumerate(tasks_to_add):
                                 # Parse Date
                                 d_obj = None
                                 if t.get('date'):
                                     try: 
                                         # Try ISO format or simply YYYY-MM-DD
                                         d_str = t['date'].strip()
                                         d_obj = datetime.datetime.fromisoformat(d_str)
                                     except:
                                         pass # Fail gracefully, no date
                                 
                                 add_task_to_google(tasks_svc, "@default", t['title'], t['notes'], due_date=d_obj, parent=parent_id)
                                 bar.progress((idx+1)/len(tasks_to_add))
                                 # time.sleep(0.1) # Optional rate limit
                                 
                             st.success(f"¡Proyecto '{proj_title}' creado con {len(tasks_to_add)} subtareas!")
                             time.sleep(2)
                             st.rerun()
                         else:
                             st.error("Error creando tarea principal (Parent Task).")
                     else:
                         st.error("No se pudo conectar con Google Tasks.")
             else:
                 st.write(plan_data)

    # --- UNIFIED MANAGER UI (TASKS + CALENDAR) ---
    st.divider()
    st.subheader("🎛️ Gestor de Agenda (Eventos y Tareas)")
    
    # 1. Controls
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([1.5, 1.5, 1])
    with col_ctrl1:
        m_start_date = st.date_input("Desde", datetime.date.today(), key="man_start")
    with col_ctrl2:
        m_end_date = st.date_input("Hasta", datetime.date.today() + datetime.timedelta(days=7), key="man_end")
    with col_ctrl3:
        st.write("") # Spacer
        if st.button("🔎 Buscar Eventos"):
            st.session_state.trigger_manager_search = True

        st.session_state.trigger_manager_search = True

    # 2. Logic (Connection Status)
    if 'connected_email' not in st.session_state or not st.session_state.connected_email or st.session_state.connected_email == 'Desconocido':
        is_robot = True
        account_label = "🤖 Cuenta de Robot (Servicio)"
        status_color = "orange"
    else:
        is_robot = False
        account_label = f"👤 {st.session_state.connected_email}"
        status_color = "green"

    msg_warn = f'<span style="color: orange; font-size: 0.8rem;">⚠️ Tus tareas personales NO se verán aquí.</span>' if is_robot else ''
    
    st.markdown(f'''
    <div style="background: rgba(255,255,255,0.05); padding: 10px 15px; border-radius: 8px; border: 1px solid {status_color}; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">
        <div>
            <span style="color: #9cb6ba; font-size: 0.8rem;">Viendo datos de:</span>
            <div style="font-weight: bold; color: {status_color};">{account_label}</div>
        </div>
        <div>{msg_warn}</div>
    </div>
    ''', unsafe_allow_html=True)
    
    if is_robot:
        if st.button("🔄 Conectar mi Cuenta Personal (Gmail)", key="btn_connect_manager"):
            st.session_state.trigger_mail_analysis = True # Hack to trigger auth flow in view_inbox or similar?
            # Better: Reset token and rerun to force auth on next call
            if 'google_token' in st.session_state: del st.session_state['google_token']
            st.rerun()

    if st.session_state.get('trigger_manager_search') or True: # Always show or trigger
        cal_svc = get_calendar_service()
        tasks_svc = get_tasks_service()
        cal_id = st.session_state.get('connected_email', 'primary')
        
        st.markdown("#### 📅 Eventos de Calendario")
        if cal_svc:
            try:
                t_min = datetime.datetime.combine(m_start_date, datetime.time.min).isoformat() + 'Z'
                t_max = datetime.datetime.combine(m_end_date, datetime.time.max).isoformat() + 'Z'
                
                # Retry logic for Broken Pipe / Connection Issues
                retries = 3
                for i in range(retries):
                    try:
                        events_res = cal_svc.events().list(
                            calendarId=cal_id, timeMin=t_min, timeMax=t_max, singleEvents=True, orderBy='startTime'
                        ).execute()
                        break # Success
                    except Exception as e:
                        if i < retries - 1 and ("broken pipe" in str(e).lower() or "connection" in str(e).lower()):
                            time.sleep(1)
                            continue
                        else:
                            raise e # Re-raise if retries exhausted
                
                events_list = events_res.get('items', [])
                
                if not events_list:
                    st.caption("No se encontraron eventos en este rango.")
                else:
                    for ev in events_list:
                        with st.expander(f"🗓️ {ev.get('summary', '(Sin Título)')} | {ev['start'].get('dateTime', ev['start'].get('date'))[:16]}"):
                             # Edit Form
                             u_summ = st.text_input("Título", ev.get('summary', ''), key=f"ev_ti_{ev['id']}")
                             u_desc = st.text_area("Descripción", ev.get('description', ''), key=f"ev_de_{ev['id']}")
                             
                             # Simple Date Edit (Keeping it simple for now, separating Date and Time could be better but complex UI)
                             # Just offering Delete and Text updates for v1 safety, or basic delete
                             c_u1, c_u2 = st.columns(2)
                             with c_u1:
                                 if st.button("💾 Guardar Cambios", key=f"btn_sav_ev_{ev['id']}"):
                                     ok, msg = update_event_calendar(cal_svc, cal_id, ev['id'], summary=u_summ, description=u_desc)
                                     if ok: st.success("Guardado!"); st.session_state.trigger_manager_search = True; st.rerun()
                                     else: st.error(msg)
                             with c_u2:
                                 if st.button("🗑️ Eliminar Evento", key=f"btn_del_ev_{ev['id']}"):
                                     if delete_event(cal_svc, ev['id']):
                                         st.success("Eliminado")
                                         st.session_state.trigger_manager_search = True
                                         st.rerun()
            except Exception as e:
                st.error(f"Error leyendo calendario: {e}")

        st.divider()
        st.markdown("#### ✅ Tareas de Google Tasks")
        if tasks_svc:
            # Reusing the simple getter, technically fetches all active tasks. Filtering by date is done client side if 'due' exists
            # We add a spinner to indicate loading
            # with st.spinner("Cargando tareas..."):
            all_tasks = get_existing_tasks_simple(tasks_svc)
            
            # Allow creating new task here
            # Fix: Use a form or callback to avoid infinite loop on rerun
            with st.form("quick_task_form", clear_on_submit=True):
                c_form1, c_form2 = st.columns([4, 1])
                with c_form1:
                    new_t = st.text_input("➕ Nueva Tarea", placeholder="Escribir...", label_visibility="collapsed")
                with c_form2:
                    submitted = st.form_submit_button("Agregar")
                
                if submitted and new_t:
                     res = add_task_to_google(tasks_svc, "@default", new_t)
                     if res: 
                         st.success("Tarea añadida")
                         time.sleep(1) # Give API a moment
                         st.rerun()

            # --- MASS ACTIONS ---
            with st.expander("⚙️ Acciones Avanzadas (Zona de Peligro)"):
                 st.warning("Estas acciones afectan a la cuenta conectada.")
                 if st.button("🗑️ ELIMINAR TODAS LAS TAREAS VISIBLES", type="primary"):
                     if not all_tasks:
                         st.info("No hay tareas para borrar.")
                     else:
                         st.session_state.confirm_delete_all = True
                 
                 if st.session_state.get('confirm_delete_all'):
                     st.error(f"¿Estás seguro? Se eliminarán {len(all_tasks)} tareas permanentemente.")
                     c_d1, c_d2 = st.columns(2)
                     with c_d1:
                         if st.button("✅ SÍ, BORRAR TODO"):
                             progress_bar = st.progress(0)
                             deleted_count = 0
                             for idx, t in enumerate(all_tasks):
                                 delete_task_google(tasks_svc, t['list_id'], t['id'])
                                 deleted_count += 1
                                 progress_bar.progress((idx + 1) / len(all_tasks))
                                 time.sleep(0.1) # Avoid rate limits
                             
                             st.success(f"Se eliminaron {deleted_count} tareas.")
                             st.session_state.confirm_delete_all = False
                             time.sleep(1)
                             st.rerun()
                     with c_d2:
                         if st.button("Cancelar"):
                             st.session_state.confirm_delete_all = False
                             st.rerun()

            # --- DEBUG: SHOW LISTS ---
            with st.expander("📂 Ver Listas de Tareas Detectadas"):
                task_lists = get_task_lists(tasks_svc)
                for tl in task_lists:
                    st.write(f"- **{tl['title']}** (ID: `{tl['id']}`)")

            if not all_tasks:
                st.caption("No hay tareas pendientes (o no se pudieron cargar).")
            else:
                for t in all_tasks:
                     # Filter visually if due date is in range? Or just show all? User asked for control, showing all is safer
                     list_tag = f"[{t['list_title']}]" if t.get('list_title') else ""
                     
                     with st.expander(f"☑️ {t['title']} {list_tag}"):
                          st.caption(f"📍 Lista: {t.get('list_title', 'Desconocida')}")
                          ed_ti = st.text_input("Título", t['title'], key=f"t_ti_{t['id']}")
                          ed_no = st.text_area("Notas", t.get('notes', ''), key=f"t_no_{t['id']}")
                          
                          d_val = datetime.date.today()
                          if t.get('due'):
                             try: d_val = datetime.datetime.fromisoformat(t['due'].replace('Z','')).date()
                             except: pass
                          ed_du = st.date_input("Vencimiento", d_val, key=f"t_du_{t['id']}")
                          
                          c_t1, c_t2 = st.columns(2)
                          with c_t1:
                             if st.button("💾 Guardar Tarea", key=f"u_t_{t['id']}"):
                                 update_task_google(tasks_svc, t['list_id'], t['id'], title=ed_ti, notes=ed_no, due=ed_du)
                                 st.success("Guardado")
                                 st.rerun()
                          with c_t2:
                             if st.button("🗑️ Borrar Tarea", key=f"d_t_{t['id']}"):
                                 delete_task_google(tasks_svc, t['list_id'], t['id'])
                                 st.rerun()


def view_inbox():
    render_header("Inteligencia de Bandeja", "Filtrado de Correo con IA")
    st.markdown("Filtra y extrae eventos de tu correo automáticamente.")
    
    col_g1, col_g2 = st.columns([1, 2])
    
    with col_g1:
        # --- VISUALIZAR CUENTA ACTUAL ---
        if 'connected_email' in st.session_state:
            st.success(f"📧 Conectado: **{st.session_state.connected_email}**")
            if st.button("♻️ Cambiar Cuenta / Salir", key="btn_logout_gmail"):
                st.session_state.logout_google = True
                st.rerun()
        # --------------------------------

        c_d1, c_d2 = st.columns(2)
        with c_d1:
            start_date = st.date_input("Fecha Inicio", datetime.date.today() - datetime.timedelta(days=7))
        with c_d2:
            end_date = st.date_input("Fecha Fin", datetime.date.today())
        
        # Global Limit check
        global_limit = st.session_state.get('admin_max_emails', 50)
        max_fetch = st.slider(f"Max Correos a Leer (Límite Admin: {global_limit}):", 5, global_limit, min(50, global_limit), help="Mayor cantidad consume más tokens.")

        # Logic to handle auto-continue after auth reload
        if 'trigger_mail_analysis' not in st.session_state:
            st.session_state.trigger_mail_analysis = False

        if st.button("🔄 Conectar y Analizar Buzón"):
             st.session_state.trigger_mail_analysis = True
        
        # Execute if triggered
        if st.session_state.trigger_mail_analysis:
             from googleapiclient.discovery import build
             creds = get_gmail_credentials() # This might stop/rerun
             
             if creds:
                 # Only proceed if we have valid creds (auth flow done)
                 try:
                     service_gmail = build('gmail', 'v1', credentials=creds)
                     with st.spinner(f"📩 Leyendo desde {start_date} hasta {end_date} (Max {max_fetch})..."):
                         emails = fetch_emails_batch(service_gmail, start_date=start_date, end_date=end_date, max_results=max_fetch)
                     
                     if not emails:
                         st.warning("No se encontraron correos nuevos relevantes.")
                     else:
                         st.session_state.fetched_emails = emails
                         with st.spinner(f"🧠 La IA está analizando {len(emails)} correos..."):
                             events = analyze_emails_ai(emails)
                             st.session_state.ai_gmail_events = events
                             if not events:
                                 st.warning('La IA leyó los correos pero no encontró eventos agendables.')
                 except Exception as e:
                     st.error(f"Error procesando correos: {e}")
                 finally:
                     # Reset trigger so it doesn't loop forever
                     st.session_state.trigger_mail_analysis = False
             else:
                 pass

    with col_g2:
         if 'ai_gmail_events' in st.session_state and st.session_state.ai_gmail_events:
             st.success(f"✅ ¡He detectado {len(st.session_state.ai_gmail_events)} posibles eventos!")
             
             for i, ev in enumerate(st.session_state.ai_gmail_events):
                 with st.expander(f"📅 {ev.get('summary', 'Evento Detectado')}", expanded=True):
                     c1, c2 = st.columns([3, 1])
                     with c1:
                         st.write(f"**Detalles:** {ev.get('description', '-')}")
                         st.caption(f"🕒 {ev.get('start_time')} ➡ {ev.get('end_time')}")
                     with c2:
                         if st.button(f"Agendar 📌", key=f"btn_gm_{i}"):
                             cal_id = st.session_state.get('connected_email', 'primary')
                             service_cal = get_calendar_service()
                             if service_cal:
                                  res, msg = add_event_to_calendar(service_cal, ev, cal_id)
                                  if res: st.success(f"¡Agendado!")
                                  else: st.error(f"Error: {msg}")
         elif 'fetched_emails' in st.session_state:
              st.info(f"📨 Se leyeron {len(st.session_state.fetched_emails)} correos. Esperando análisis...")

def view_optimize():
    render_header("Optimizador de Agenda", "Auditoría de Tiempo")
    
    calendar_id = st.session_state.get('connected_email', '')
    if not calendar_id:
        st.warning("⚠️  Configura tu ID de Calendario en la barra lateral.")
        return

    col_opt_1, col_opt_2 = st.columns(2)
    with col_opt_1:
        today = datetime.date.today()
        start_date = st.date_input("Fecha Inicio", today)
    with col_opt_2:
        end_date = st.date_input("Fecha Fin", today + datetime.timedelta(days=30))
        
    if st.button("📥 Importar Período Seleccionado"):
        service = get_calendar_service()
        if service:
            t_min = datetime.datetime.combine(start_date, datetime.time.min).isoformat() + 'Z'
            t_max = datetime.datetime.combine(end_date, datetime.time.max).isoformat() + 'Z'
            
            try:
                res = service.events().list(
                    calendarId=calendar_id, 
                    timeMin=t_min, 
                    timeMax=t_max, 
                    singleEvents=True, 
                    orderBy='startTime',
                    maxResults=250
                ).execute()
                st.session_state.opt_events = res.get('items', [])
                if len(st.session_state.opt_events) == 250:
                    st.warning("⚠️ Se alcanzó el límite de 250 eventos. Intenta reducir el rango si faltan datos.")
                else:
                    st.success(f"Cargados {len(st.session_state.opt_events)} eventos.")
            except Exception as e:
                st.error(f"Error cargando calendario: {e}")
    
    if 'opt_events' in st.session_state and st.session_state.opt_events:
        events = st.session_state.opt_events
        st.write(f"📅 Se leyeron {len(events)} eventos en el periodo seleccionado.")
        
        if st.button("🧠 AI: Analizar Historial y Tendencias"):
            with st.spinner("Analizando patrones anuales, mensuales y semanales..."):
                result = analyze_existing_events_ai(events)
                st.session_state.opt_plan = result.get('optimization_plan', {})
                st.session_state.advisor_note = result.get('advisor_note', "Sin comentarios.")
        
        if 'opt_plan' in st.session_state:
            st.markdown("### 💡 Informe Estratégico:")
            st.info(st.session_state.advisor_note)
            
            st.subheader("Mejoras Propuestas:")
            
            with st.form("exec_optimization"):
                c1, c2, c3 = st.columns([2, 2, 1])
                c1.markdown("**Original**")
                c2.markdown("**Propuesta**")
                c3.markdown("**Estado**")
                
                for ev in events: 
                    pid = ev['id']
                    if pid in st.session_state.opt_plan:
                        proposal = st.session_state.opt_plan[pid]
                        c1, c2, c3 = st.columns([2, 2, 1])
                        c1.text(ev.get('summary', ''))
                        c2.markdown(f"**{proposal['new_summary']}**")
                        c3.caption("Mejorable")
                        st.divider()
                
                if st.form_submit_button("✨ Ejecutar Transformación"):
                    service = get_calendar_service()
                    if service:
                        bar = st.progress(0)
                        done = 0
                        plan = st.session_state.opt_plan
                        for i, ev in enumerate(events):
                            if ev['id'] in plan:
                                p = plan[ev['id']]
                                optimize_event(service, calendar_id, ev['id'], p['new_summary'], p['colorId'])
                                done += 1
                            bar.progress((i+1)/len(events))
                        st.success(f"¡Agenda Transformada! {done} eventos optimizados.")

# --- NAVIGATION CONTROLLER ---

def main_app():
    # Sidebar Navigation mimicking the "Rail"
    with st.sidebar:
        st.markdown("<div style='text-align: center; margin-bottom: 20px;'>", unsafe_allow_html=True)
        st.image("logo_agent.png", width=90)
        st.markdown("</div>", unsafe_allow_html=True)
             
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

        # --- ADMIN PANEL ---
        user_role = "User"
        if 'user_data_full' in st.session_state:
            # Robust extraction: try 'rol', 'role', 'ROL', etc.
            ud = st.session_state.user_data_full
            # The keys are lowercased in auth.py, but let's be safe
            raw_role = ud.get('rol', ud.get('role', ud.get('ROL', 'User')))
            user_role = str(raw_role).strip()
            
        # --- FALLBACK / OVERRIDE FOR SPECIFIC ADMIN ---
        if st.session_state.get('license_key') == 'adm_alain':
            user_role = 'ADMIN'
            
        if user_role.upper() == 'ADMIN':
            with st.expander("🛠️ Panel Admin"):
                st.write(f"Rol Activo: {user_role}") # Debug confirmation
                st.markdown("**Control de Límites**")
                current_limit = st.session_state.get('admin_max_emails', 50)
                new_limit = st.number_input("Max Correos (Global)", value=current_limit, step=10)
                if new_limit != current_limit:
                    st.session_state.admin_max_emails = new_limit
                    
                st.markdown("**Simulación de Rol**")
                # This affects specific UI elements if implemented, currently mostly placeholder for future role-based views
                sim_role = st.selectbox("Ver como:", ["Admin", "User", "Manager"])
                st.session_state.simulated_role = sim_role
        # -------------------

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
