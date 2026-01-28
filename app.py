import streamlit as st
import os
import datetime
import json
import pandas as pd
import time
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv

import sys

# === CONFIGURACIÓN ESPAÑOL LATINOAMERICANO & TIMEZONE ===
from zoneinfo import ZoneInfo
try:
    CHILE_TZ = ZoneInfo("America/Santiago")
except:
    import pytz
    CHILE_TZ = pytz.timezone("America/Santiago")

import locale
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252')
    except:
        pass
os.environ['LANG'] = 'es_ES.UTF-8'
os.environ['LC_ALL'] = 'es_ES.UTF-8'
# ============================================

# --- FORCE RELOAD MODULES (Cloud Cache Fix) ---
try:
    for mods in ['modules.auth', 'modules.notifications', 'modules.google_services', 'modules.ai_core']:
        if mods in sys.modules:
            del sys.modules[mods]
except:
    pass

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

# --- APP CONFIG ---
APP_CONFIG = {
    "imagenes": {
        "LOGO_ALAIN": "logo_agent.png" 
    }
}

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

def get_time_period_color(hour):
    """Returns color based on time of day."""
    if 5 <= hour < 12:
        return "#10b981", "Mañana" # Green/Teal
    elif 12 <= hour < 18:
        return "#f59e0b", "Tarde" # Orange
    elif 18 <= hour < 22:
        return "#6366f1", "Noche" # Indigo
    else: # 22 - 5
        return "#64748b", "Madrugada" # Slate

def render_date_badge(start_str, end_str=None):
    """Renders a stylish time badge."""
    try:
        if 'T' in start_str:
             d = datetime.datetime.fromisoformat(start_str.replace('Z', ''))
             color, period = get_time_period_color(d.hour)
             
             # Manual Spanish Localization
             months_es = {1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun", 
                          7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"}
             fmt_date = f"{d.day} {months_es[d.month]}"
             
             fmt_time = d.strftime("%H:%M")
             
             return f"""<div style="display: inline-flex; flex-direction: column; align-items: center; background: rgba(0,0,0,0.3); border: 1px solid {color}; border-radius: 8px; padding: 5px 10px; min-width: 80px;"><span style="color: {color}; font-weight: bold; font-size: 0.8rem; text-transform: uppercase;">{period}</span><span style="color: white; font-weight: 700; font-size: 1.1rem;">{fmt_time}</span><span style="color: #9cb6ba; font-size: 0.75rem;">{fmt_date}</span></div>"""
        else:
             # All day
             return f"""<div style="display: inline-flex; flex-direction: column; align-items: center; background: rgba(0,0,0,0.3); border: 1px solid #0dd7f2; border-radius: 8px; padding: 5px 10px; min-width: 80px;"><span style="color: #0dd7f2; font-weight: bold; font-size: 0.8rem; text-transform: uppercase;">DÍA</span><span style="color: white; font-weight: 700; font-size: 1.1rem;">Todo</span><span style="color: #9cb6ba; font-size: 0.75rem;">{start_str}</span></div>"""
    except:
        return f"<span>{start_str}</span>"

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
        st.markdown('<br>', unsafe_allow_html=True)
        
        # Centered logo with optimized size
        c_img1, c_img2, c_img3 = st.columns([1, 1, 1])
        with c_img2:
             st.image("logo_agent.png", width=150)  # Increased for better visibility
        
        st.markdown("""
        <div class="login-box" style="text-align: center;">
             <h1 style="font-size: 2.2rem; margin-bottom: 0.3rem; font-weight: 600;">Asistente Ejecutivo AI</h1>
             <p style="color: #0dd7f2; margin-bottom: 2rem; font-size: 0.95rem;">🔐 Acceso Seguro</p>
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


    # === RESUMEN MATUTINO CON VOZ (OPTIMIZADO CON CACHE) ===
    st.markdown("""
    <div style='background: linear-gradient(135deg, rgba(13,215,242,0.1) 0%, rgba(9,168,196,0.05) 100%); 
                padding: 20px; border-radius: 15px; border-left: 4px solid #0DD7F2; margin-bottom: 25px;'>
        <h3 style='margin: 0; color: #0DD7F2; font-size: 1.4rem;'>
            🎙️ Resumen Matutino con Voz
        </h3>
        <p style='margin: 5px 0 0 0; color: #9CB6BA; font-size: 0.9rem;'>
            Tu asistente personal te informa sobre el día
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col_b1, col_b2, col_b3 = st.columns([3, 1, 1])
    
    with col_b1:
        # Verificar si ya existe un briefing de hoy en cache
        today_key = datetime.datetime.now().strftime('%Y-%m-%d')
        cache_key = f'briefing_{today_key}'
        
        # Obtener eventos actuales para comparar
        cal_svc = get_calendar_service()
        today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0)
        today_end = today_start + datetime.timedelta(days=1)
        
        try:
            events_result = cal_svc.events().list(
                calendarId=calendar_id,
                timeMin=today_start.isoformat() + 'Z',
                timeMax=today_end.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            current_events = events_result.get('items', [])
            events_hash = hash(str([e.get('id') for e in current_events]))
        except:
            current_events = []
            events_hash = 0
        
        # Verificar cache
        cache_valid = False
        if cache_key in st.session_state:
            cached_data = st.session_state[cache_key]
            if cached_data.get('events_hash') == events_hash:
                cache_valid = True
        
        # Mostrar estado del cache
        if cache_valid:
            st.success("✅ Resumen del día ya generado (usando versión guardada)")
        else:
            st.info("💡 Genera tu resumen personalizado del día")
        
        # Botón con estado dinámico
        button_label = "🔄 Regenerar Resumen" if cache_valid else "🎧 Generar Resumen de Voz"
        
        if st.button(button_label, width="stretch", type="primary", key="btn_briefing"):
            with st.spinner("🧠 Creando tu resumen personalizado..."):
                from modules.ai_core import generate_daily_briefing
                from modules.tts_service import text_to_speech
                
                # Top 3 tareas
                try:
                    tasks_svc = get_tasks_service()
                    task_lists = tasks_svc.tasklists().list().execute().get('items', [])
                    all_tasks = []
                    for tlist in task_lists[:1]:
                        tasks = tasks_svc.tasks().list(tasklist=tlist['id']).execute().get('items', [])
                        all_tasks.extend(tasks)
                    top_tasks = all_tasks[:3]
                except:
                    top_tasks = []
                
                unread_count = 0
                
                # Generar con IA (SOLO si no hay cache válido o se fuerza)
                briefing_text = generate_daily_briefing(current_events, top_tasks, unread_count)
                
                # Convertir a audio
                audio_bytes = text_to_speech(briefing_text)
                
                # Guardar en cache
                st.session_state[cache_key] = {
                    'text': briefing_text,
                    'audio': audio_bytes,
                    'events_hash': events_hash,
                    'timestamp': datetime.datetime.now().isoformat()
                }
                
                st.success("✅ Resumen generado y guardado")
                st.rerun()
    
    with col_b2:
        st.metric("Eventos Hoy", len(current_events))
    
    with col_b3:
        if cache_valid:
            cache_time = datetime.datetime.fromisoformat(st.session_state[cache_key]['timestamp'])
            hours_ago = int((datetime.datetime.now() - cache_time).total_seconds() / 3600)
            st.metric("Actualizado", f"Hace {hours_ago}h" if hours_ago > 0 else "Ahora")
    
    # Mostrar audio y transcripción si existe cache
    if cache_valid or cache_key in st.session_state:
        cached_data = st.session_state.get(cache_key, {})
        
        if cached_data.get('audio'):
            st.markdown("---")
            
            # Player de audio con diseño moderno
            st.markdown("""
            <div style='background: rgba(13,215,242,0.05); padding: 15px; border-radius: 10px; margin: 10px 0;'>
                <p style='margin: 0 0 10px 0; color: #0DD7F2; font-weight: 600;'>
                    🔊 Reproducir Audio
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            st.audio(cached_data['audio'], format='audio/mp3')
            
            # Transcripción expandible con diseño
            with st.expander("📄 Ver Transcripción Completa", expanded=False):
                st.markdown(f"""
                <div style='background: rgba(250,250,250,0.05); padding: 15px; border-radius: 8px; 
                            line-height: 1.6; color: #FAFAFA;'>
                    {cached_data.get('text', '')}
                </div>
                """, unsafe_allow_html=True)

    st.divider()

    # --- MÉTRICAS PRINCIPALES (Diseño Moderno) ---
    st.markdown("""
    <h3 style='color: #0DD7F2; font-size: 1.3rem; margin-bottom: 15px;'>
        📊 Resumen del Día
    </h3>
    """, unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns(4)
    
    # Fetch Data (Cached)
    events = []
    try:
        svc = get_calendar_service()
        if svc:
            now = datetime.datetime.now(CHILE_TZ)
            # Safe bet: Get local start/end, convert to RFC3339 format expected by Google
            # Use astimezone() to include the local system offset (e.g., -03:00)
            t_min = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            t_max = now.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
            events = svc.events().list(
                calendarId=calendar_id, timeMin=t_min, timeMax=t_max, singleEvents=True, orderBy='startTime'
            ).execute().get('items', [])
    except Exception as e:
        # Fallback: If 404 (Not Found) or 403 (Forbidden), it might be that User doesn't have access but Robot does.
        error_str = str(e)
        if "404" in error_str or "notFound" in error_str or "403" in error_str:
            try:
                # Retry with Robot (Service Account)
                svc_sa = get_calendar_service(force_service_account=True)
                if svc_sa:
                    events = svc_sa.events().list(
                         calendarId=calendar_id, timeMin=t_min, timeMax=t_max, singleEvents=True, orderBy='startTime'
                    ).execute().get('items', [])
                    # If success, maybe show a small toast?
                    # st.toast("🔄 Usando cuenta robot para este calendario.")
            except: pass # If fails again, nothing to do
        else:
            print(f"Calendar Error: {e}")

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
                    s_dt = datetime.datetime.fromisoformat(start)
                    e_dt = datetime.datetime.fromisoformat(end)
                    
                    # Fix: Calculate intersection with TODAY only
                    # Assuming 'now' is defined above for timezone naiveness check or similar
                    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
                    
                    # Make offsets compatible if needed (assuming ISO from Google is offset-aware)
                    if s_dt.tzinfo and not today_start.tzinfo:
                        today_start = today_start.astimezone(s_dt.tzinfo)
                        today_end = today_end.astimezone(s_dt.tzinfo)

                    # Max of starts, Min of ends
                    overlap_start = max(s_dt, today_start)
                    overlap_end = min(e_dt, today_end)
                    
                    if overlap_start < overlap_end:
                        duration = (overlap_end - overlap_start).total_seconds() / 3600
                        hours += duration
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
                    showlegend=False,
                    margin=dict(l=10, r=10, t=10, b=10),
                    height=300
                )
                st.plotly_chart(fig, width="stretch", key="timeline_chart")
            else:
                st.info("No hay eventos en la línea de tiempo.")

    # --- ADVANCED ANALYTICS ---
    with st.expander("📊 Análisis Avanzado", expanded=True):
        ac1, ac2 = st.columns(2)
        
        with ac1:
            st.markdown("###### 🎨 Distribución de Tiempo (Eventos)")
            if today_events:
                # Group by Color (Category proxy)
                df_ev = pd.DataFrame([{'Color': e.get('colorId', 'Default'), 'Count': 1} for e in today_events])
                if not df_ev.empty:
                    df_ev_counts = df_ev.groupby('Color').count().reset_index()
                    fig_pie = px.pie(df_ev_counts, values='Count', names='Color', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                    fig_pie.update_layout(height=250, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_pie, width="stretch", key="events_pie")
            else:
                st.caption("Sin datos de eventos.")
                
        with ac2:
            st.markdown("###### ✅ Estado de Tareas")
            # If tasks_list exists (fetched above)
            if 'tasks_list' in locals() and tasks_list:
                # Mock status based on notes or title (Tasks API simple doesn't give much)
                # Or just count by "List" if we had that info. 
                # Let's count properly.
                total_t = len(tasks_list)
                # Visual bar
                st.progress(max(0.1, min(1.0, 0.5)), text=f"{total_t} Tareas Pendientes") # Dummy progress for now
                
                # Simple Bar Chart
                df_tasks = pd.DataFrame([{'Type': 'Pendientes', 'Count': total_t}, {'Type': 'Completadas (Hoy)', 'Count': 0}]) # API limitation
                fig_bar = px.bar(df_tasks, x='Type', y='Count', color='Type', color_discrete_sequence=['#ef4444', '#22c55e'])
                fig_bar.update_layout(height=250, margin=dict(l=0, r=0, t=20, b=0), paper_bgcolor='rgba(0,0,0,0)', showlegend=False)
                st.plotly_chart(fig_bar, width="stretch", key="tasks_bar")
            else:
                 st.caption("Sin datos de tareas.")
        
        st.divider()
        
        # --- NEW: DETAILED TABLE & UTILIZATION ---
        ac3, ac4 = st.columns([1.5, 1])
        
        with ac3:
            st.markdown("###### 📋 Detalle de Agenda")
            if today_events:
                # Build nice dataframe
                table_data = []
                for e in today_events:
                    summ = e.get('summary', 'Sin Título')
                    start_raw = e['start'].get('dateTime', e['start'].get('date'))
                    
                    # Format Time
                    try:
                        dt_s = datetime.datetime.fromisoformat(start_raw)
                        time_str = dt_s.strftime("%H:%M")
                    except:
                        time_str = "Todo el día"
                        
                    # Recalculate duration for table context
                    dur_str = "-"
                    if e['start'].get('dateTime') and e['end'].get('dateTime'):
                        try:
                            s = datetime.datetime.fromisoformat(e['start'].get('dateTime'))
                            en = datetime.datetime.fromisoformat(e['end'].get('dateTime'))
                            dur_min = (en - s).total_seconds() / 60
                            dur_str = f"{int(dur_min)} min"
                        except: pass
                        
                    table_data.append({"Hora": time_str, "Evento": summ, "Duración": dur_str})
                
                df_detail = pd.DataFrame(table_data)
                st.dataframe(df_detail, width="stretch", hide_index=True)
            else:
                st.info("Agenda libre.")

        with ac4:
            st.markdown("###### ⏳ Carga Laboral (Base 9h)")
            # Work Day Analysis
            work_day_hours = 9.0
            used_hours = min(hours, work_day_hours)
            overtime = max(0, hours - work_day_hours)
            free_hours = max(0, work_day_hours - hours)
            
            df_load = pd.DataFrame([
                {"Tipo": "Reuniones", "Horas": used_hours, "Color": "Ocupado"},
                {"Tipo": "Libre", "Horas": free_hours, "Color": "Libre"},
                {"Tipo": "Extra", "Horas": overtime, "Color": "Extra"}
            ])
            
            # Simple Stacked Bar only if there is data
            if hours > 0 or free_hours > 0:
                fig_load = px.bar(df_load, x="Horas", y="Color", orientation='h', color="Color", 
                                color_discrete_map={"Ocupado": "#0dd7f2", "Libre": "#334155", "Extra": "#ef4444"}, text="Horas")
                fig_load.update_layout(height=200, margin=dict(l=0, r=0, t=0, b=0), 
                                     paper_bgcolor='rgba(0,0,0,0)', showlegend=False,
                                     xaxis=dict(showgrid=False), yaxis=dict(showticklabels=False))
                st.plotly_chart(fig_load, width="stretch", key="load_chart")
            else:
                st.caption("Sin datos de carga.")

    # --- ENRIQUECIMIENTO CON CONTEXTO EXTERNO (GRATIS) ---
    if today_events:
        st.markdown("---")
        st.markdown("""
        <h3 style='color: #0DD7F2; font-size: 1.3rem; margin-bottom: 10px;'>
            🕵️ Contexto Inteligente
        </h3>
        <p style='color: #9CB6BA; font-size: 0.9rem; margin-bottom: 15px;'>
            Enriquece tus eventos con información actualizada de la web
        </p>
        """, unsafe_allow_html=True)
        
        for idx, event in enumerate(today_events[:5]):  # Limitar a 5 eventos
            event_title = event.get('summary', 'Sin título')
            event_id = event.get('id')
            event_desc = event.get('description', '')
            
            with st.expander(f"📅 {event_title}", expanded=False):
                col_evt1, col_evt2 = st.columns([3, 1])
                
                with col_evt1:
                    if event_desc and '🕵️ CONTEXTO AUTOMÁTICO' not in event_desc:
                        st.markdown(f"**Descripción actual:**\n{event_desc[:200]}...")
                    elif '🕵️ CONTEXTO AUTOMÁTICO' in event_desc:
                        st.success("✅ Este evento ya tiene contexto enriquecido")
                        # Mostrar solo el contexto
                        context_part = event_desc.split('🕵️ CONTEXTO AUTOMÁTICO:')[1] if '🕵️ CONTEXTO AUTOMÁTICO:' in event_desc else event_desc
                        st.markdown(f"**Contexto:**\n{context_part[:300]}...")
                    else:
                        st.info("Sin descripción. Agrega contexto automático →")
                
                with col_evt2:
                    button_key = f"enrich_{event_id}_{idx}"
                    button_label = "🔄 Actualizar" if '🕵️ CONTEXTO' in event_desc else "🔍 Buscar Contexto"
                    
                    if st.button(button_label, key=button_key, width="stretch"):
                        with st.spinner("🌐 Buscando información en la web..."):
                            from modules.web_search import enrich_event_with_free_context
                            
                            # Buscar contexto (título + descripción)
                            context = enrich_event_with_free_context(event_title, event_desc)
                            
                            if context:
                                # Actualizar descripción del evento
                                current_desc = event_desc.split('---\n🕵️ CONTEXTO')[0] if '🕵️ CONTEXTO' in event_desc else event_desc
                                
                                new_desc = f"""{current_desc}

---
🕵️ CONTEXTO AUTOMÁTICO ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}):

{context}

[Fuente: Búsqueda web automática con DuckDuckGo + Groq AI]
"""
                                
                                # Actualizar en Google Calendar
                                try:
                                    cal_svc = get_calendar_service()
                                    event['description'] = new_desc
                                    
                                    updated_event = cal_svc.events().update(
                                        calendarId=calendar_id,
                                        eventId=event_id,
                                        body=event
                                    ).execute()
                                    
                                    st.success("✅ Contexto agregado exitosamente")
                                    st.markdown(f"**Información encontrada:**\n{context}")
                                    st.rerun()
                                    
                                except Exception as e:
                                    st.error(f"Error al actualizar evento: {e}")
                            else:
                                st.warning("⚠️ No se encontró información relevante para este evento")


def view_create():
    # Modern header with glassmorphism
    st.markdown("""
    <div style='background: linear-gradient(135deg, rgba(13,215,242,0.1) 0%, rgba(9,168,196,0.05) 100%); 
                padding: 25px; border-radius: 15px; border-left: 4px solid #0DD7F2; margin-bottom: 25px;'>
        <h2 style='margin: 0; color: #0DD7F2; font-size: 1.8rem;'>
            🚀 Centro de Comandos
        </h2>
        <p style='margin: 8px 0 0 0; color: #9CB6BA; font-size: 1rem;'>
            Creación de eventos con IA y lenguaje natural
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col_input, col_viz = st.columns([1, 1])

    with col_input:
        st.markdown("### 🗣️ Entrada de Lenguaje Natural")
        with st.form("create_event"):
            prompt = st.text_area("¿Qué deseas agendar?", height=200, 
                                placeholder="Ejemplo: Reunión el próximo martes a las 14:00 sobre el presupuesto Q3...")
            
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
            
            # Custom Badge Rendering
            start_iso = ev.get('start_time', '2025-01-01')
            badge_html = render_date_badge(start_iso)
            
            st.markdown(f"""
            <div class="glass-panel" style="border-left: 4px solid #0dd7f2;">
                <div style="display: flex; gap: 15px; align-items: start;">
                    {badge_html}
                    <div style="flex-grow: 1;">
                        <h3 style="margin: 0; color: white;">{summary}</h3>
                        <p style="color: #9cb6ba; font-size: 0.9rem; margin-top: 5px;">{desc}</p>
                    </div>
                    <div>
                         <span class="material-symbols-outlined" style="color: #0dd7f2;">event</span>
                    </div>
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
                    
                    # Check for duplicates BEFORE creating
                    from modules.google_services import check_event_exists
                    if check_event_exists(svc, cal_id, ev):
                        st.warning(f"✅ Ya agendado: '{summary}'")
                        st.info("Este evento ya existe en tu calendario con datos similares.")
                    else:
                        ok, msg = add_event_to_calendar(svc, ev, cal_id)
                        if ok: st.success("¡Evento Creado!")
                        else: st.error(msg)


def view_planner():
    # Modern header with glassmorphism
    st.markdown("""
    <div style='background: linear-gradient(135deg, rgba(13,215,242,0.1) 0%, rgba(9,168,196,0.05) 100%); 
                padding: 25px; border-radius: 15px; border-left: 4px solid #0DD7F2; margin-bottom: 25px;'>
        <h2 style='margin: 0; color: #0DD7F2; font-size: 1.8rem;'>
            📅 Planificador Inteligente
        </h2>
        <p style='margin: 8px 0 0 0; color: #9CB6BA; font-size: 1rem;'>
            Orquestación semanal de tareas y compromisos
        </p>
    </div>
    """, unsafe_allow_html=True)
    
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
            except Exception as e:
                err_msg = str(e)
                fallback_success = False
                
                # --- FALLBACK: TRY SERVICE ACCOUNT (ROBOT) ---
                if "404" in err_msg or "Not Found" in err_msg:
                    # Maybe the user doesn't have permission, but the Robot (SA) does?
                    try:
                        svc_sa = get_calendar_service(force_service_account=True)
                        if svc_sa:
                            st.session_state.c_events_cache = svc_sa.events().list(
                                calendarId=calendar_id, timeMin=t_min, timeMax=t_max, 
                                singleEvents=True, orderBy='startTime', maxResults=2000,
                                fields="items(summary,start,end,description)" 
                            ).execute().get('items', [])
                            fallback_success = True
                            st.toast(f"🤖 Usando cuenta Robot para ver {calendar_id}")
                    except:
                        pass
                
                if not fallback_success:
                    if "404" in err_msg or "Not Found" in err_msg:
                         st.warning(f"⚠️ No se encontró el calendario **{calendar_id}**.")
                         st.info("💡 Tu usuario NO tiene permiso, y la cuenta Robot tampoco. Comparte el calendario con tu email o con la cuenta de servicio.")
                    else:
                        st.error(f"Error cargando calendario: {e}")
                    st.session_state.c_events_cache = []
    
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
                
                # --- DEFENSIVE CHECK FOR STALE STATE ---
                if 'weekly_plan' in st.session_state:
                     if isinstance(st.session_state.weekly_plan, list):
                         if len(st.session_state.weekly_plan) > 0 and isinstance(st.session_state.weekly_plan[0], dict):
                             st.session_state.weekly_plan = st.session_state.weekly_plan[0]
                         else:
                             st.session_state.weekly_plan = {}
                     elif not isinstance(st.session_state.weekly_plan, dict):
                         st.session_state.weekly_plan = {}
                
                tasks_to_sync = []
                
                for i, day_en in enumerate(days_en):
                    day_es = days_map[day_en]
                    with cols[i]:
                        st.markdown(f"**{day_es}**")
                        
                        # FAIL-SAFE ACCESS
                        plan_data = st.session_state.weekly_plan
                        tasks = []
                        
                        if isinstance(plan_data, dict):
                            tasks = plan_data.get(day_en, plan_data.get(day_es, []))
                        elif isinstance(plan_data, list) and len(plan_data) > 0 and isinstance(plan_data[0], dict):
                             # Fail-safe for stale list state
                             tasks = plan_data[0].get(day_en, plan_data[0].get(day_es, []))
                        
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
        
        extra_context = st.text_area("📝 Contexto (Opcional)", height=100, placeholder="Pega aquí correos, requerimientos o detalles específicos para que la IA los considere...")
        
        # uploaded_file = st.file_uploader("📂 Subir Documentos (PDF/TXT)", type=["pdf", "txt"])
        # if uploaded_file:
        #     try:
        #         file_text = ""
        #         if uploaded_file.type == "application/pdf":
        #             import pypdf
        #             reader = pypdf.PdfReader(uploaded_file)
        #             for page in reader.pages:
        #                 file_text += page.extract_text() + "\n"
        #         else: # txt
        #             file_text = uploaded_file.read().decode("utf-8")
        #         
        #         if file_text:
        #             # OPTIMIZATION: Truncate for Qwen 32B Limit (6k TPM is tight)
        #             # 15k chars is roughly 4-5k tokens, leaving room for prompt + output
        #             MAX_CHARS = 15000
        #             if len(file_text) > MAX_CHARS:
        #                 file_text = file_text[:MAX_CHARS] + "\n... [TRUNCADO POR LIMITE DE CREDITOS]"
        #                 st.warning(f"⚠️ Documento largo. Se ha truncado a {MAX_CHARS} caracteres para cuidar tus créditos de IA.")
        #             
        #             extra_context += f"\n\n--- DOCUMENTO ADJUNTO ({uploaded_file.name}) ---\n{file_text}"
        #             st.toast(f"📄 Documento '{uploaded_file.name}' procesado.")
        #     except Exception as e:
        #         st.error(f"Error leyendo archivo: {e}")

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
                err_msg = str(e)
                fallback_success = False
                
                # --- FALLBACK: TRY SERVICE ACCOUNT (ROBOT) ---
                if "404" in err_msg or "Not Found" in err_msg:
                    try:
                        cal_svc_sa = get_calendar_service(force_service_account=True)
                        if cal_svc_sa:
                             events_res = cal_svc_sa.events().list(
                                calendarId=cal_id, timeMin=t_min, timeMax=t_max, 
                                singleEvents=True, orderBy='startTime', maxResults=50
                             ).execute()
                             events_list = events_res.get('items', [])
                             
                             # Render Events WITH FULL CONTROLS (Same as main block)
                             if not events_list:
                                 st.caption("No se encontraron eventos en este rango (vía Robot).")
                             else:
                                 st.caption("ℹ️ Mostrando eventos con permiso de Robot")
                                 for ev in events_list:
                                     with st.expander(f"🗓️ {ev.get('summary', '(Sin Título)')} | {ev['start'].get('dateTime', ev['start'].get('date'))[:16]}"):
                                          # Edit Form
                                          u_summ = st.text_input("Título", ev.get('summary', ''), key=f"ev_ti_sa_{ev['id']}")
                                          u_desc = st.text_area("Descripción", ev.get('description', ''), key=f"ev_de_sa_{ev['id']}")
                                          
                                          c_u1, c_u2 = st.columns(2)
                                          with c_u1:
                                              if st.button("💾 Guardar Cambios", key=f"btn_sav_ev_sa_{ev['id']}"):
                                                  ok, msg = update_event_calendar(cal_svc_sa, cal_id, ev['id'], summary=u_summ, description=u_desc)
                                                  if ok: st.success("Guardado!"); st.session_state.trigger_manager_search = True; st.rerun()
                                                  else: st.error(msg)
                                          with c_u2:
                                              if st.button("🗑️ Eliminar Evento", key=f"btn_del_ev_sa_{ev['id']}"):
                                                  if delete_event(cal_svc_sa, ev['id']):
                                                      st.success("Eliminado")
                                                      st.session_state.trigger_manager_search = True
                                                      st.rerun()
                             fallback_success = True
                    except: pass
                
                if not fallback_success:
                    if "404" in err_msg or "Not Found" in err_msg:
                         st.error(f"Error 404: No tienes permiso para ver el calendario {cal_id}.")
                    else:
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
    # Modern header with glassmorphism
    st.markdown("""
    <div style='background: linear-gradient(135deg, rgba(13,215,242,0.1) 0%, rgba(9,168,196,0.05) 100%); 
                padding: 25px; border-radius: 15px; border-left: 4px solid #0DD7F2; margin-bottom: 20px;'>
        <h2 style='margin: 0; color: #0DD7F2; font-size: 1.8rem;'>
            📧 Inteligencia de Bandeja
        </h2>
        <p style='margin: 8px 0 0 0; color: #9CB6BA; font-size: 1rem;'>
            Filtrado de correo con IA - Extrae eventos automáticamente
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col_g1, col_g2 = st.columns([1, 2])
    
    with col_g1:
        # --- VISUALIZAR CUENTA ACTUAL (DINÁMICO - DETECTA CUENTA REAL) ---
        try:
            from googleapiclient.discovery import build
            creds = get_gmail_credentials()
            if creds:
                gmail_svc = build('gmail', 'v1', credentials=creds)
                profile = gmail_svc.users().getProfile(userId='me').execute()
                current_email = profile.get('emailAddress', 'Desconocido')
                st.success(f"📧 Conectado: **{current_email}**")
            else:
                st.info("📧 No conectado a Gmail")
        except Exception as e:
            st.warning(f"📧 Error detectando cuenta: {e}")
        
        # --- BOTÓN LOGOUT (SIEMPRE VISIBLE) ---
        if st.button("♻️ Cambiar Cuenta / Salir", key="btn_logout_gmail"):
            # 1. Clear from Sheet (Cloud)
            if 'license_key' in st.session_state:
                 user = st.session_state.license_key
                 st.toast("Desvinculando cuenta de Google...")
                 auth.update_user_field(user, 'COD_VAL', '')
            
            # 2. Clear Local Session State (UI Reset)
            keys_to_clear = ['connected_email', 'google_token', 'calendar_service', 'tasks_service', 'sheets_service', 'user_data_full']
            for k in keys_to_clear:
                if k in st.session_state:
                    del st.session_state[k]
            
            # 3. Clear Caches (Force Fresh Data)
            st.cache_data.clear()

            # 4. Delete Local Token File (Force Auth Flow)
            if os.path.exists('token.pickle'):
                try: os.remove('token.pickle')
                except: pass

            # 5. Trigger Rerun
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
        
        # User Specific Limit (from Sheet)
        user_limit = 50 # Default
        if 'user_data_full' in st.session_state:
            try:
                raw_lim = st.session_state.user_data_full.get('cant_corr', '')
                if raw_lim and str(raw_lim).strip():
                    user_limit = int(float(str(raw_lim).strip()))
            except:
                pass
        
        # Enforce strict minimum of the two limits
        effective_limit = min(global_limit, user_limit)
        
        if effective_limit < 5: effective_limit = 5 # Minimum sanity check
        
        st.caption(f"Límite de lectura asignado: **{effective_limit} emails**")
        
        # Display Quota Info
        if 'license_key' in st.session_state:
             _, rem, use, lim = auth.check_and_update_daily_quota(st.session_state.license_key)
             st.progress(min(1.0, use/lim) if lim > 0 else 0, text=f"Cuota Diaria: {use}/{lim} analizados")

        max_fetch = st.slider(f"Max Correos a Leer:", 5, effective_limit, effective_limit, help="Definido por Admin.")

        # Logic to handle auto-continue after auth reload
        if 'trigger_mail_analysis' not in st.session_state:
            st.session_state.trigger_mail_analysis = False

        if st.button("🔄 Conectar y Analizar Buzón"):
             # 1. Pre-Check Quota UI
             if 'license_key' in st.session_state:
                 allowed, remaining, usage, limit = auth.check_and_update_daily_quota(st.session_state.license_key)
                 if not allowed:
                     st.error(f"⚠️ Cuota diaria excedida ({usage}/{limit}).")
                 else:
                     st.session_state.trigger_mail_analysis = True
             else:
                  st.session_state.trigger_mail_analysis = True
        
        # Execute if triggered
        if st.session_state.trigger_mail_analysis:
             from googleapiclient.discovery import build
             creds = get_gmail_credentials() # This might stop/rerun
             
             if creds:
                 # Only proceed if we have valid creds (auth flow done)
                 try:
                     # 2. Check Quota (Double Check before burning API)
                     allowed, remaining, usage, limit = True, 100, 0, 100
                     if 'license_key' in st.session_state:
                         allowed, remaining, usage, limit = auth.check_and_update_daily_quota(st.session_state.license_key)
                     
                     if not allowed:
                         st.error(f"❌ Has superado tu cuota diaria ({limit} correos).")
                         st.info(f"Usados hoy: {usage}. Intenta mañana o contacta al admin.")
                         st.session_state.trigger_mail_analysis = False
                         st.stop()

                     service_gmail = build('gmail', 'v1', credentials=creds)
                     with st.spinner(f"📩 Leyendo desde {start_date} hasta {end_date} (Max {max_fetch})..."):
                         emails = fetch_emails_batch(service_gmail, start_date=start_date, end_date=end_date, max_results=max_fetch)
                     
                     if not emails:
                         st.warning("No se encontraron correos nuevos relevantes.")
                     else:
                         st.session_state.fetched_emails = emails
                         with st.spinner(f"🧠 La IA está analizando y categorizando {len(emails)} correos..."):
                             analyzed_items = analyze_emails_ai(emails)
                             st.session_state.ai_gmail_events = analyzed_items 
                             
                             # 3. Update Quota Consumption
                             if 'license_key' in st.session_state:
                                  auth.check_and_update_daily_quota(st.session_state.license_key, requested_amount=len(emails))
                            
                             # Auto-labeling REMOVED. Now handled manually in UI.

                             if not analyzed_items:
                                 st.warning('La IA leyó los correos pero no encontró nada accionable.')
                 except Exception as e:
                     st.error(f"Error procesando correos: {e}")
                 finally:
                     # Reset trigger so it doesn't loop forever
                     st.session_state.trigger_mail_analysis = False
             else:
                 pass

    with col_g2:
         # Check if analysis has run (ignoring if empty)
         if 'ai_gmail_events' in st.session_state:
             items = st.session_state.ai_gmail_events
             if not items:
                 st.info("🤷‍♂️ La IA analizó los correos pero no detectó eventos ni tareas importantes.")
             else:
                 st.success(f"✅ ¡Procesado! {len(items)} elementos detectados.")
                 
                 # Tabs for Events vs Tasks vs Labeling
                 tab_ev, tab_info, tab_labels = st.tabs(["📅 Eventos", "📝 Tareas / Info", "🏷️ Revisión Etiquetas"])
                 
                 # --- TAB LABELS (MANUAL REVIEW) ---
                 with tab_labels:
                     st.info("Revisa y confirma las etiquetas antes de aplicarlas en Gmail.")
                     
                     # Prepare data for display
                     label_preview = []
                     for x in items:
                         lbl = f"Agente A2/{x.get('urgency', 'Media')}"
                         label_preview.append({
                             "Asunto": x.get('summary', 'Sin Asunto'),
                             "Etiqueta Propuesta": lbl,
                             "Categoría": x.get('category', '-')
                         })
                     
                     if label_preview:
                         st.table(label_preview)
                         
                         if st.button("✅ Confirmar y Aplicar Etiquetas"):
                             with st.spinner("Aplicando etiquetas en Gmail..."):
                                 from modules.google_services import ensure_label, add_label_to_email
                                 from googleapiclient.discovery import build
                                 
                                 # Re-auth specifically for this action
                                 creds_lbl = get_gmail_credentials()
                                 if creds_lbl:
                                     svc_lbl = build('gmail', 'v1', credentials=creds_lbl)
                                     count_ok = 0
                                     
                                     # Ensure Parent
                                     try: ensure_label(svc_lbl, "Agente A2")
                                     except: pass

                                     for item in items:
                                         if item.get('id'):
                                             lbl_name = f"Agente A2/{item.get('urgency', 'Media')}"
                                             try:
                                                 lid = ensure_label(svc_lbl, lbl_name)
                                                 if lid:
                                                     add_label_to_email(svc_lbl, item['id'], lid)
                                                     count_ok += 1
                                             except: pass
                                     
                                     if count_ok > 0:
                                         st.success(f"¡Listo! {count_ok} correos etiquetados.")
                                         time.sleep(2)
                                         st.rerun()
                                     else:
                                         st.warning("No se pudo etiquetar nada.")
                     else:
                         st.write("No hay correos para etiquetar.")

                 with tab_ev:
                     events = [x for x in items if x.get('is_event') or x.get('start_time')]
                     if not events: st.info("No hay eventos de calendario estrictos.")
                     
                     for i, ev in enumerate(events):
                         with st.expander(f"🗓️ {ev.get('summary', 'Evento')} ({ev.get('urgency','?')})", expanded=True):
                             c1, c2 = st.columns([3, 1])
                             with c1:
                                 # Badge Logic
                                 s_time = ev.get('start_time', '')
                                 badge = render_date_badge(s_time)
                                 
                                 # Layout with Badge
                                 st.markdown(f"""
                                 <div style="display: flex; gap: 15px; align-items: start;">
                                     {badge}
                                     <div>
                                         <div style="font-weight: bold; color: white;">{ev.get('category','-')}</div>
                                         <div style="color: #ccc; font-size: 0.9rem;">{ev.get('description', '-')}</div>
                                     </div>
                                 </div>
                                 """, unsafe_allow_html=True)
                                 if ev.get('id'):
                                      # Valid Link Logic: Use authuser for multi-account support
                                      t_id = ev.get('threadId', ev['id'])
                                      user_email = st.session_state.get('connected_email', '0') # defaults to 0 if unknown
                                      link = f"https://mail.google.com/mail/u/?authuser={user_email}#inbox/{t_id}"
                                      st.markdown(f"🔗 [Ver Correo Original]({link})")
                             with c2:
                                 from modules.google_services import check_event_exists
                                 cal_id = st.session_state.get('connected_email', 'primary')
                                 service_cal = get_calendar_service()
                                 
                                 is_scheduled = False
                                 if service_cal:
                                     is_scheduled = check_event_exists(service_cal, cal_id, ev)
                                 
                                 if is_scheduled:
                                     st.success("✅ Agendado")
                                     if st.button(f"Regenerar", key=f"btn_ev_re_{i}"):
                                         res, msg = add_event_to_calendar(service_cal, ev, cal_id)
                                         if res: 
                                             st.success("¡Agendado!")
                                             st.rerun()
                                         else: st.error(f"Error: {msg}")
                                 else:
                                     if st.button(f"Agendar", key=f"btn_ev_{i}"):
                                          if service_cal:
                                               # Append Link to Description
                                               final_desc = ev.get('description', '-')
                                               if ev.get('id'):
                                                   t_id = ev.get('threadId', ev['id'])
                                                   user_email = st.session_state.get('connected_email', '0')
                                                   link = f"https://mail.google.com/mail/u/?authuser={user_email}#inbox/{t_id}"
                                                   if link not in final_desc:
                                                       final_desc += f"\n\n🔗 Correo: {link}"
                                               
                                               # Create copy to avoid mutating session state permanently if failed
                                               ev_to_add = ev.copy()
                                               ev_to_add['description'] = final_desc

                                               res, msg = add_event_to_calendar(service_cal, ev_to_add, cal_id)
                                               if res: 
                                                   st.success("¡Agendado!")
                                                   st.rerun()
                                               else: st.error(f"Error: {msg}")
                 
                 with tab_info:
                     tasks = [x for x in items if not x.get('is_event') and not x.get('start_time')]
                     if not tasks: st.info("No hay información suelta o tareas sin fecha.")
                     
                     for i, t in enumerate(tasks):
                         with st.expander(f"📌 {t.get('summary', 'Nota')} ({t.get('urgency','?')})", expanded=True):
                             st.markdown(f"**Categoría**: {t.get('category','Otro')}")
                             st.write(t.get('description', ''))
                             
                             # Display Link if ID exists
                             email_link = None
                             if t.get('id'):
                                 t_id = t.get('threadId', t['id'])
                                 user_email = st.session_state.get('connected_email', '0')
                                 email_link = f"https://mail.google.com/mail/u/?authuser={user_email}#inbox/{t_id}"
                                 st.markdown(f"🔗 [Ver Correo Original]({email_link})")
                             
                             # Action: Save as Task for TODAY (Catch-all)
                             if st.button("Guardar como Tarea (Para Hoy)", key=f"btn_tk_{i}"):
                                 svc_tasks = get_tasks_service()
                                 if svc_tasks:
                                     # Append Link to Notes
                                     final_notes = t.get('description', '')
                                     if email_link:
                                         final_notes += f"\n\n🔗 Correo: {email_link}"
                                     
                                     # Current date for due date
                                     due_today = datetime.datetime.now(datetime.timezone.utc)
                                     add_task_to_google(svc_tasks, "@default", t.get('summary'), final_notes, due_date=due_today)
                                     st.success("✅ Guardada en Google Tasks para hoy.")
         
         elif 'fetched_emails' in st.session_state:
              st.info(f"📨 Se leyeron {len(st.session_state.fetched_emails)} correos. Esperando análisis...")

def view_optimize():
    # Modern header with glassmorphism
    st.markdown("""
    <div style='background: linear-gradient(135deg, rgba(13,215,242,0.1) 0%, rgba(9,168,196,0.05) 100%); 
                padding: 25px; border-radius: 15px; border-left: 4px solid #0DD7F2; margin-bottom: 25px;'>
        <h2 style='margin: 0; color: #0DD7F2; font-size: 1.8rem;'>
            ⚡ Optimizador de Agenda
        </h2>
        <p style='margin: 8px 0 0 0; color: #9CB6BA; font-size: 1rem;'>
            Auditoría de tiempo y sugerencias estratégicas con IA
        </p>
    </div>
    """, unsafe_allow_html=True)
    
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
                # Safety check: AI might return list or dict
                if isinstance(result, dict):
                    st.session_state.opt_plan = result.get('optimization_plan', {})
                    st.session_state.advisor_note = result.get('advisor_note', "Sin comentarios.")
                else:
                    st.warning("⚠️ Respuesta inesperada de la IA. Intenta nuevamente.")
                    st.session_state.opt_plan = {}
                    st.session_state.advisor_note = "Error al procesar análisis."
        
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

def view_account():
    """Vista de configuración de cuenta del usuario"""
    # Modern header with glassmorphism
    st.markdown("""
    <div style='background: linear-gradient(135deg, rgba(13,215,242,0.1) 0%, rgba(9,168,196,0.05) 100%); 
                padding: 25px; border-radius: 15px; border-left: 4px solid #0DD7F2; margin-bottom: 25px;'>
        <h2 style='margin: 0; color: #0DD7F2; font-size: 1.8rem;'>
            ⚙️ Mi Cuenta
        </h2>
        <p style='margin: 8px 0 0 0; color: #9CB6BA; font-size: 1rem;'>
            Configuración personal, seguridad y estado de licencias
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    if 'license_key' not in st.session_state or 'user_data_full' not in st.session_state:
        st.error("No hay sesión activa.")
        return
    
    user = st.session_state.license_key
    user_data = st.session_state.user_data_full
    
    # --- USER INFORMATION ---
    st.subheader("📋 Información de Usuario")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("👤 Usuario", user)
        st.metric("📧 Email de Envío", user_data.get('email_send', 'No configurado'))
    
    with col2:
        st.metric("📬 Límite de Correos", user_data.get('cant_corr', '50'))
        st.metric("✅ Estado", user_data.get('ESTADO', 'ACTIVO'))
    
    st.divider()
    
    # --- PASSWORD CHANGE ---
    st.subheader("🔐 Cambiar Contraseña")
    
    with st.form("change_password_form"):
        st.markdown("🔒 **Seguridad:** Tu contraseña debe tener al menos 6 caracteres.")
        
        old_pass = st.text_input("Contraseña Actual", type="password", placeholder="••••••")
        new_pass = st.text_input("Nueva Contraseña", type="password", placeholder="Mínimo 6 caracteres")
        confirm_pass = st.text_input("Confirmar Nueva Contraseña", type="password", placeholder="••••••")
        
        submitted = st.form_submit_button("Cambiar Contraseña", type="primary", width="stretch")
        
        if submitted:
            # Validations
            if not old_pass or not new_pass or not confirm_pass:
                st.error("❌ Todos los campos son obligatorios.")
            elif new_pass != confirm_pass:
                st.error("❌ Las contraseñas nuevas no coinciden.")
            else:
                from modules.auth import change_password
                success, message = change_password(user, old_pass, new_pass)
                
                if success:
                    st.success(message)
                    st.balloons()
                    st.info("ℹ️ Por seguridad, se recomienda cerrar sesión y volver a iniciar sesión con la nueva contraseña.")
                else:
                    st.error(message)
    
    st.divider()
    
    # --- USEFUL TIPS ---
    st.subheader("💡 Consejos de Seguridad")
    st.markdown("""
    - 🔑 Usa una contraseña única y segura
    - 🔄 Cambia tu contraseña periódicamente
    - 🚫 No compartas tus credenciales
    - ✅ Cierra sesión al terminar de usar la app
    """)

def view_time_insights():
    """Vista de Análisis de Fuga de Tiempo"""
    # Modern header with glassmorphism
    st.markdown("""
    <div style='background: linear-gradient(135deg, rgba(13,215,242,0.1) 0%, rgba(9,168,196,0.05) 100%); 
                padding: 25px; border-radius: 15px; border-left: 4px solid #0DD7F2; margin-bottom: 25px;'>
        <h2 style='margin: 0; color: #0DD7F2; font-size: 1.8rem;'>
            📉 Insights de Tiempo
        </h2>
        <p style='margin: 8px 0 0 0; color: #9CB6BA; font-size: 1rem;'>
            Análisis de distribución y oportunidades de optimización semanal
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    from modules.ai_core import analyze_time_leaks_weekly
    from datetime import datetime, timedelta
    import plotly.graph_objects as go
    
    st.markdown("🕵️ Analizamos los últimos 7 días de tu calendario para identificar oportunidades de optimización.")
    st.divider()
    
    if st.button("🔍 Analizar Última Semana", width="stretch", type="primary"):
        with st.spinner("📊 Analizando 7 días de calendario..."):
            # Obtener eventos de últimos 7 días
            cal_svc = get_calendar_service()
            calendar_id = st.session_state.get('connected_email', 'primary')
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            try:
                events_result = cal_svc.events().list(
                    calendarId=calendar_id,
                    timeMin=start_date.isoformat() + 'Z',
                    timeMax=end_date.isoformat() + 'Z',
                    singleEvents=True
                ).execute()
                
                events = events_result.get('items', [])
            except Exception as e:
                st.error(f"Error obteniendo eventos: {e}")
                return
            
            if len(events) < 3:
                st.warning("⚠️ Muy pocos eventos para análisis significativo (mínimo 3 requeridos)")
                return
            
            # Analizar con IA
            analysis = analyze_time_leaks_weekly(events)
            
            # --- VISUALIZACIÓN ---
            st.markdown("### 📊 Distribución del Tiempo")
            
            # Métricas superiores
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Horas", f"{analysis['total_hours']}h", help="Tiempo total en eventos")
            with col2:
                st.metric("Eventos", len(events), help="Cantidad de eventos analizados")
            with col3:
                top_cat = max(analysis['stats'].items(), key=lambda x: x[1]['hours'])
                st.metric("Mayor Consumo", top_cat[0].replace('_', ' ').title(), help=f"{top_cat[1]['hours']}h")
            with col4:
                avg_per_day = round(analysis['total_hours'] / 7, 1)
                st.metric("Promedio/Día", f"{avg_per_day}h", help="Horas promedio por día")
            
            st.divider()
            
            # Gráficos
            col_pie, col_bar = st.columns(2)
            
            with col_pie:
                st.markdown("**Por Categoría**")
                labels = [cat.replace('_', ' ').title() for cat in analysis['stats'].keys()]
                values = [data['hours'] for data in analysis['stats'].values()]
                
                fig_pie = go.Figure(data=[go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.4,
                    marker=dict(colors=['#0DD7F2', '#09A8C4', '#21C354', '#FF4B4B', '#9CB6BA'])
                )])
                fig_pie.update_layout(
                    title="Distribución por Tipo",
                    height=350,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#FAFAFA')
                )
                st.plotly_chart(fig_pie, width="stretch")
            
            with col_bar:
                st.markdown("**Comparativa**")
                cats = [cat.replace('_', ' ').title() for cat in analysis['stats'].keys()]
                hours = [data['hours'] for data in analysis['stats'].values()]
                
                fig_bar = go.Figure(data=[go.Bar(
                    x=cats,
                    y=hours,
                    marker_color='#0DD7F2'
                )])
                fig_bar.update_layout(
                    title="Horas por Categoría",
                    xaxis_title="Categoría",
                    yaxis_title="Horas",
                    height=350,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#FAFAFA')
                )
                st.plotly_chart(fig_bar, width="stretch")
            
            st.divider()
            
            # Insights de IA
            st.markdown("### 💡 Recomendaciones Estratégicas (IA)")
            st.markdown(analysis['insights'])
            
            st.divider()
            
            # Desglose detallado
            with st.expander("📋 Ver Desglose Completo de Eventos"):
                for cat_name, events_list in analysis['categories'].items():
                    if events_list:
                        cat_display = cat_name.replace('_', ' ').title()
                        st.markdown(f"**{cat_display}** ({len(events_list)} eventos)")
                        
                        for ev in events_list[:10]:
                            dur_val = ev['duration']
                            # DEBUG: Show raw value to understand why 3.0 < 1.0 is seemingly True
                            # st.caption(f"DEBUG: val={dur_val} type={type(dur_val)}")
                            
                            try:
                                val_float = float(dur_val)
                                if val_float < 1.0:
                                    dur_str = f"{int(round(val_float * 60))} min"
                                else:
                                    dur_str = f"{val_float:.1f}h"
                            except:
                                dur_str = f"{dur_val} (?)"
                                
                            st.text(f"  • {ev['title']} ({dur_str})")
                        
                        st.markdown("")

# --- NAVIGATION CONTROLLER ---

def main_app():
    # Sidebar Navigation mimicking the "Rail"
    with st.sidebar:
        st.markdown("<div style='text-align: center; margin-bottom: 25px; padding-top: 10px;'>", unsafe_allow_html=True)
        st.image("logo_agent.png", width=100)  # Slightly larger for better sidebar presence
        st.markdown("<p style='color: #0dd7f2; font-size: 0.75rem; margin-top: 5px;'>Asistente IA</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
             
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- SUBSCRIPTION STATUS BOX ---
        if 'user_data_full' in st.session_state:
            ud = st.session_state.user_data_full
            sys_type = str(ud.get('sistema', '')).strip()
            
            if sys_type in ['Suscripción', 'Pago Anual']:
                reno_date = ud.get('proxima_renovacion', 'Pendiente')
                if str(reno_date).lower() == 'nan': reno_date = "Pendiente..."
                
                if sys_type == 'Suscripción':
                    price_text = "Monto: $5.500 / mes"
                else:
                    price_text = "Monto: $60.000 / año"
                
                st.markdown(f"""
                <div style="background-color: #1e293b; padding: 12px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #0dd7f2;">
                    <p style="color: #94a3b8; font-size: 0.75rem; margin: 0; text-transform: uppercase; letter-spacing: 0.5px;">Próxima Renovación</p>
                    <p style="color: white; font-weight: bold; font-size: 1rem; margin: 4px 0;">{reno_date}</p>
                    <p style="color: #0dd7f2; font-size: 0.85rem; margin: 0;">{price_text}</p>
                </div>
                """, unsafe_allow_html=True)
                
                with st.expander("💳 Datos Transferencia"):
                    st.caption(" Banco: Tenpo (Vista)\nNro: 111118581575\nRUT: 18.581.575-7\nMail: alain.antinao.s@gmail.com")
        
        # Navigation Buttons with icons and emojis for visual appeal
        nav_options = {
            "Dashboard": "📊 Panel Principal",
            "Create": "➕ Crear Evento",
            "Planner": "📅 Planificador",
            "Inbox": "📧 Bandeja IA",
            "Optimize": "⚡ Optimizar",
            "Insights": "📉 Insights",
            "Account": "⚙️ Mi Cuenta"
        }
        
        selection = st.radio("Navegación", list(nav_options.keys()), format_func=lambda x: nav_options[x], label_visibility="collapsed")
        
        st.divider()
        st.caption("Configuración")
        st.text_input("ID Calendario", value=st.session_state.get('connected_email', ''), key='connected_email_input')
        if st.session_state.connected_email_input != st.session_state.get('connected_email', ''):
             st.session_state.connected_email = st.session_state.connected_email_input

        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("🔐 Cerrar Sesión App", key="btn_logout_sidebar", width="stretch"):
            # IMPORTANTE: NO borrar COD_VAL (token Google OAuth)
            # El token debe persistir en Google Sheets para evitar re-autenticación
            # Solo se borra si el usuario hace clic en "Cambiar Cuenta / Salir"
            
            # Clear Local Session State ONLY (UI Reset)
            keys_to_clear = ['connected_email', 'google_token', 'calendar_service', 'tasks_service', 'sheets_service', 'authenticated', 'user_data_full', 'license_key']
            for k in keys_to_clear:
                if k in st.session_state:
                    del st.session_state[k]
            
            # Clear Caches
            st.cache_data.clear()
            
            # 4. Delete Local Token File (Force Auth Flow)
            if os.path.exists('token.pickle'):
                try: os.remove('token.pickle')
                except: pass
            
            if os.path.exists('.license_key'):
                 try: os.remove('.license_key')
                 except: pass

            # 5. Trigger Rerun
            st.session_state.logout_google = True
            st.rerun()

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
                st.write(f"Rol Activo: {user_role}") 
                
                # --- USER MANAGEMENT ---
                st.markdown("### Gestión de Usuarios")
                if st.button("🔄 Cargar Usuarios"):
                    users = auth.get_all_users()
                    if users:
                        df_users = pd.DataFrame(users)
                        # Filter relevant columns for display
                        cols_to_show = ['user', 'rol', 'estado', 'cant_corr', 'modelo_ia']
                        # Ensure columns exist
                        for c in cols_to_show:
                            if c not in df_users.columns: df_users[c] = ""
                            
                        st.session_state.admin_users_df = df_users[cols_to_show].copy()
                    else:
                        st.error("No se pudieron cargar usuarios.")

                if 'admin_users_df' in st.session_state:
                    # Make DataFrame editable but keep tracking IDs
                    edited_df = st.data_editor(
                        st.session_state.admin_users_df,
                        key="user_editor",
                        disabled=["user", "rol"],
                        column_config={
                            "estado": st.column_config.SelectboxColumn("Estado", options=["ACTIVO", "SUSPENDIDO", "INACTIVO"], required=True),
                            "cant_corr": st.column_config.NumberColumn("Límite Correos", min_value=0, max_value=200, format="%d"),
                            "modelo_ia": st.column_config.SelectboxColumn(
                                "Modelo IA Predefinido",
                                options=[
                                    "llama-3.3-70b-versatile",
                                    "llama-3.1-8b-instant",
                                    "mixtral-8x7b-32768"
                                ],
                                required=False,
                                width="medium"
                            )
                        }
                    )
                    
                    c_act1, c_act2 = st.columns(2)
                    
                    with c_act1:
                        if st.button("💾 Guardar Cambios"):
                            with st.spinner("Guardando cambios masivos..."):
                                 ok, msg = auth.update_users_batch(edited_df)
                                 if ok:
                                     st.success(f"✅ {msg}")
                                     time.sleep(1)
                                 else: st.error(f"Error: {msg}")

                    with c_act2:
                        # Reset Quota Action
                        user_to_reset = st.selectbox("Seleccionar Usuario para Reiniciar Cuota:", edited_df['user'].unique(), key="sel_rst_usr")
                        if st.button("🔄 Reiniciar Uso (0)", key="btn_rst_quota"):
                            ok, msg = auth.update_user_field(user_to_reset, "USO_HOY", 0)
                            if ok:
                                st.success(f"✅ Contador reiniciado para {user_to_reset}")
                                time.sleep(1)
                            else: st.error(f"Error: {msg}")
                        
                st.divider()
                st.markdown("**Simulación**")
                sim_role = st.selectbox("Ver como:", ["Admin", "User", "Manager"])
                st.session_state.simulated_role = sim_role
        # -------------------

    # Main Router
    if selection == "Dashboard": view_dashboard()
    elif selection == "Create": view_create()
    elif selection == "Planner": view_planner()
    elif selection == "Inbox": view_inbox()
    elif selection == "Optimize": view_optimize()
    elif selection == "Insights": view_time_insights()
    elif selection == "Account": view_account()
    
    # --- FOOTER ---
    st.markdown("---")
    with st.container():
        col_f1, col_f2, col_f3, col_f4 = st.columns([3, 1, 5, 1])
        
        with col_f2:
            # LOGO EMPRESA (LOGO_ALAIN)
            if APP_CONFIG['imagenes'].get('LOGO_ALAIN'):
                st.image(APP_CONFIG['imagenes']['LOGO_ALAIN'], width=150)
            else:
                st.info("Logo Dev")
                
        with col_f3:
            st.markdown("""
                <div style='text-align: left; color: #888888; font-size: 16px; padding-bottom: 20px;'>
                    💼 Aplicación desarrollada por <strong>Alain Antinao Sepúlveda</strong> <br>
                    📧 Contacto: <a href="mailto:alain.antinao.s@gmail.com" style="color: #006DB6;">alain.antinao.s@gmail.com</a> <br>
                    🌐 Más información en: <a href="https://alain-antinao-s.notion.site/Alain-C-sar-Antinao-Sep-lveda-1d20a081d9a980ca9d43e283a278053e" target="_blank" style="color: #006DB6;">Mi página personal</a>
                </div>
            """, unsafe_allow_html=True)

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
