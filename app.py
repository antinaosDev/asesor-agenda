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
import os
# Ensure root directory is in sys.path for Streamlit Cloud
root_path = os.path.dirname(os.path.abspath(__file__))
if root_path not in sys.path:
    sys.path.append(root_path)

# Workaround for 'KeyError: modules' in some environments
try:
    import modules
except ImportError:
    pass

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

# --- MODULE IMPORTS ---

# --- MODULE IMPORTS ---
import modules.auth as auth
import modules.notifications as notif
import modules.chat_view as chat_view # NEW CHAT MODULE
import modules.notes_view as notes_view # NEW NOTES MODULE

from modules.google_services import (
    get_calendar_service, get_tasks_service, get_sheets_service, get_gmail_credentials,
    fetch_emails_batch, clean_email_body, 
    get_task_lists, create_task_list, add_task_to_google, 
    delete_task_google, update_task_google, get_existing_tasks_simple,
    add_event_to_calendar, delete_event, optimize_event, update_event_calendar, COLOR_MAP
)
from modules.ai_core import (
    analyze_emails_ai, parse_events_ai, analyze_agenda_ai,
    generate_work_plan_ai, generate_project_breakdown_ai, analyze_document_vision
)
from modules.auth import check_and_update_doc_analysis_quota
import modules.ui_components as ui # Global import for UI helpers

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
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Noto+Sans:wght@400;500;700&display=swap">
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" />
    <style>

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
            try:
                st.image("logo_agent.png", width=150)
            except:
                st.markdown("<h1 style='text-align: center;'>🗓️</h1>", unsafe_allow_html=True)

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
                    
                    # AUTO-LOAD CALENDAR SESSION
                    saved_calendar = auth.load_calendar_session(u)
                    if saved_calendar:
                        st.session_state.connected_email = saved_calendar
                        st.toast(f"📅 Calendario cargado: {saved_calendar[:30]}...")
                    
                    st.rerun()
                else:
                    st.error("Acceso Denegado")

# --- MAIN VIEWS ---

def view_dashboard():
    # --- WEATHER & CONTEXT ---
    # --- WEATHER & CONTEXT REMOVED AS REQUESTED ---
    # import modules.weather_service as ws (Removed)
    import modules.ui_components as ui
    
    weather_ctx = None # Disabled

    
    # Get User Name (First Name)
    user_name = "Ejecutivo"
    if 'user_data_full' in st.session_state:
        ud = st.session_state.user_data_full
        # Try multiple keys for name
        full_n = ud.get('nombre_completo') or ud.get('nombre') or ud.get('user') or 'Ejecutivo'
        user_name = str(full_n).split(' ')[0]
        
    st.markdown(ui.render_smart_header(user_name, "Resumen Matutino y Estado Diario", weather_ctx), unsafe_allow_html=True)

    # --- UX GUIDE: DASHBOARD ---
    with st.expander("📚 Guía Rápida: Tu Panel de Control", expanded=False):
        st.markdown(ui.render_guide_card_html(
            "Este es tu centro de mando. Revisa tu carga laboral, métricas de productividad y el estado de tu agenda en tiempo real.",
            "Visualiza la 'Línea de Tiempo' para detectar huecos libres y optimizar tu día."
        ), unsafe_allow_html=True)

    # --- VISUAL COLOR LEGEND ---
    with st.expander("🎨 Leyenda de Colores (Guía Visual)", expanded=False):
        # Hex mapping for Google Calendar Colors
        HEX_MAP = {
            "1": "#7986CB", "2": "#33B679", "3": "#8E24AA", "4": "#E67C73", 
            "5": "#F09300", "6": "#F4511E", "7": "#039BE5", "8": "#616161",
            "9": "#3F51B5", "10": "#0B8043", "11": "#D50000"
        }
        
        cols = st.columns(4)
        for i, (cid, name) in enumerate(COLOR_MAP.items()):
            c_hex = HEX_MAP.get(cid, "#9E9E9E")
            label = name.split('(')[1].replace(')', '') if '(' in name else name
            
            with cols[i % 4]:
                st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px; background: rgba(255,255,255,0.05); padding: 5px; border-radius: 4px;">
                    <div style="width: 12px; height: 12px; background-color: {c_hex}; border-radius: 50%; box-shadow: 0 0 5px {c_hex};"></div>
                    <span style="font-size: 0.8rem; color: #eee; font-weight: 500;">{label}</span>
                </div>
                """, unsafe_allow_html=True)

    
    # --- CONTEXT WIDGET ---
    import modules.context_services as ctx
    with st.container(border=True):
        ctx.render_context_widget()
    # ----------------------

    # Context Loading
    calendar_id = 'primary' # FORCE PRIMARY to match OAuth Token User
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
        except Exception as e:
            # 404 Handling: If calendar not found/authorized, treat as empty or try primary
            err_str = str(e)
            if "404" in err_str or "notFound" in err_str:
                print(f"DEBUG: Dashboard 404 for {calendar_id}. Trying fallback.")
                try:
                     # Try primary as fallback
                     events_result = cal_svc.events().list(
                        calendarId='primary',
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
            else:
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
             # Silently swallow 404 for dashboard to prevent huge error blocks
             pass
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
        
        # --- UX GUIDE: CREATE ---
        with st.expander("📚 Guía Rápida: Agendamiento IA", expanded=False):
            st.markdown(ui.render_guide_card_html(
                "Simplemente escribe o dicta lo que necesitas hacer. La IA detectará fechas, horas, participantes y contextos automáticamente.",
                "Para eventos repetitivos complejos (ej. 'Todos los martes'), usa el 'Asistente de Bloques' abajo."
            ), unsafe_allow_html=True)

        # --- RECURRENCE ASSISTANT ---
        with st.expander("⏱️ Asistente de Horarios y Bloques (Beta)", expanded=False):
            st.info("Genera frases precisas para bloques repetitivos o atención de público.")
            
            c_gen1, c_gen2 = st.columns(2)
            with c_gen1:
                r_title = st.text_input("Título del Bloque", "Atención de usuarios")
                r_days = st.multiselect("Días", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"], ["Lunes"])
            with c_gen2:
                r_start = st.time_input("Inicio", datetime.time(15, 0))
                r_end = st.time_input("Fin", datetime.time(17, 0))
            
            if st.button("✨ Generar Frase"):
                days_str = " y ".join(r_days) if len(r_days) < 2 else (", ".join(r_days[:-1]) + " y " + r_days[-1])
                # Construct Natural Language phrase
                phrase = f"{r_title} todos los {days_str} de {r_start.strftime('%H:%M')} a {r_end.strftime('%H:%M')}"
                st.session_state.create_prompt = phrase
                st.rerun()
        # ----------------------------

        # --- AVAILABILITY MANAGER (Approved Feature) ---
        with st.expander("📅 Gestor de Disponibilidad & Citas", expanded=False):
            st.info("Define tus bloques 'Disponibles'. Esto crea eventos transparentes (no ocupan espacio) y genera textos para correos.")
            
            c_av1, c_av2 = st.columns(2)
            with c_av1:
                av_days = st.multiselect("Días Disponibles", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"], ["Martes", "Jueves"])
                av_start = st.time_input("Desde", datetime.time(10, 0), key="av_start")
            with c_av2:
                av_title = st.text_input("Etiqueta", "🟢 Disponible")
                av_end = st.time_input("Hasta", datetime.time(12, 0), key="av_end")

            c_act1, c_act2 = st.columns(2)
            
            # Action 1: Create in Calendar
            if c_act1.button("📅 Crear en Calendario"):
                if not av_days:
                    st.error("Selecciona al menos un día.")
                else:
                    try:
                        service = get_calendar_service()
                        if service:
                            # Create RRULE
                            # Map days to RRULE format (MO, TU, WE, TH, FR)
                            day_map = {"Lunes": "MO", "Martes": "TU", "Miércoles": "WE", "Jueves": "TH", "Viernes": "FR"}
                            rrule_days = ",".join([day_map[d] for d in av_days])
                            
                            # Calculate Start DT (Next occurrence of first day?) 
                            # Simplification: Today + Time, let google handle recurrence start or specific logic
                            # Better: Start 'Tomorrow' to avoid past issues, or 'Today' if time hasn't passed.
                            today = datetime.date.today()
                            start_dt = datetime.datetime.combine(today, av_start)
                            end_dt = datetime.datetime.combine(today, av_end)
                             
                            event_data = {
                                "summary": av_title,
                                "start_time": start_dt.isoformat(),
                                "end_time": end_dt.isoformat(),
                                "description": "Bloque de disponibilidad generado por Asistente IA.",
                                "colorId": "2", # Sage (Green/Planning)
                                "transparency": "transparent", # KEY FEATURE
                                "recurrence": [f"RRULE:FREQ=WEEKLY;BYDAY={rrule_days}"]
                            }
                            
                            success, msg = add_event_to_calendar(service, event_data)
                            if success:
                                st.success(f"✅ Disponibilidad creada: {msg}")
                                time.sleep(2)
                                st.rerun()
                            else:
                                st.error(f"Error: {msg}")
                    except Exception as e:
                        st.error(f"Error conectando: {e}")

            # Action 2: Copy Text
            if c_act2.button("📋 Copiar Texto Email"):
                days_txt = ", ".join(av_days)
                text_block = f"""Hola,
                
Para nuestra reunión, mis horarios disponibles son:
📅 {days_txt} de {av_start.strftime('%H:%M')} a {av_end.strftime('%H:%M')} hrs.

Quedo atento a tu confirmación.
Saludos."""
                st.code(text_block, language="text")

        # --- QUICK ADD: Create events from simple text ---
        with st.expander("⚡ Crear Evento Rápido (QuickAdd)", expanded=False):
            st.markdown("""
            Crea eventos al instante con texto simple. Ejemplos:
            - `Reunión mañana 3pm`
            - `Almuerzo viernes 1pm`
            - `Call lunes 9am`
            """)
            
            with st.form("quick_add_form"):
                quick_text = st.text_input("Descripción del evento:", placeholder="Reunión mañana 3pm")
                quick_submit = st.form_submit_button("⚡ Crear", type="primary")
            
            if quick_submit and quick_text:
                cal_svc = get_calendar_service()
                if not cal_svc:
                    st.error("Conecta tu calendario primero.")
                else:
                    from modules.google_services import quick_add_event
                    with st.spinner("Creando evento rápido..."):
                        event = quick_add_event(cal_svc, quick_text)
                        if event:
                            st.success(f"✅ Evento creado: **{event.get('summary', 'Evento')}**")
                            st.caption(f"📅 {event.get('start', {}).get('dateTime', 'Fecha no disponible')}")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("No se pudo crear el evento. Verifica el texto.")

        # --- MAIN AI PROCESSING FORM ---
        with st.form("create_event"):
            # Use 'create_prompt' key to bind with the generator above
            prompt = st.text_area("¿Qué deseas agendar?", height=150, 
                                key="create_prompt",
                                placeholder="Ejemplo: Reunión el próximo martes a las 14:00 sobre el presupuesto Q3...")
            
             # Removed subtle tip since we have the full assistant now

            c_btn1, c_btn2 = st.columns([1, 4])
            with c_btn1:
                submitted = st.form_submit_button("Procesar", type="primary", use_container_width=True)

        if submitted and prompt:
            with st.spinner("🧠 Analizando patrones y extrayendo datos..."):
                try:
                    events = parse_events_ai(prompt)
                    st.session_state.draft_events = events
                    
                    if not events:
                        st.warning("La IA analizó el contenido pero no encontró eventos claros.")
                except Exception as e:
                    st.error(f"Error en análisis IA: {e}")

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

            # Determine Type
            item_type = ev.get('type', 'event')
            
            st.markdown(f"""
            <div class="glass-panel" style="border-left: 4px solid #0dd7f2;">
                <div style="display: flex; gap: 15px; align-items: start;">
                    {badge_html}
                    <div style="flex-grow: 1;">
                        <div style="display: flex; gap: 8px; align-items: center;">
                             <span style="background: {'#1aa' if item_type=='task' else '#0dd'}; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; color: black; font-weight: bold;">{item_type.upper()}</span>
                             <h3 style="margin: 0; color: white;">{summary}</h3>
                        </div>
                        <p style="color: #9cb6ba; font-size: 0.9rem; margin-top: 5px;">{desc}</p>
                    </div>
                    <div>
                         <span class="material-symbols-outlined" style="color: #0dd7f2;">{'check_circle' if item_type=='task' else 'event'}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            c_act1, c_act2 = st.columns([1, 4])
            with c_act2:
                if item_type == 'task':
                     c_t1, c_t2 = st.columns([1, 1])
                     
                     with c_t1:
                         if st.button(f"✅ Guardar Tarea '{summary}'", key=f"btn_add_{i}", use_container_width=True):
                            svc_task = get_tasks_service()
                            if not svc_task: st.error("Conecta Google Tasks primero.")
                            else:
                                 # Parse Start and Due Dates from AI-detected task
                                 start_dt = None
                                 due_dt = None
                                 
                                 if ev.get('start_time'):
                                     try: 
                                         start_dt = datetime.datetime.fromisoformat(ev['start_time'])
                                     except: pass
                                 
                                 if ev.get('end_time'):
                                     try: 
                                         due_dt = datetime.datetime.fromisoformat(ev['end_time'])
                                     except: pass
                                 
                                 res = add_task_to_google(svc_task, "@default", summary, desc, 
                                                         due_date=due_dt, start_date=start_dt)
                                 if res: st.success("¡Tarea Guardada!"); time.sleep(1); st.rerun()
                                 else: st.error("Error al guardar tarea.")
                     
                     with c_t2:
                         if st.button(f"⏱️ Bloquear Tiempo (Focus)", key=f"btn_block_{i}", use_container_width=True):
                             cal_id = st.session_state.get('connected_email')
                             if not cal_id: st.error("Conecta tu email.")
                             else:
                                 # Create Event Wrapper
                                 blk_ev = ev.copy()
                                 blk_ev['summary'] = f"Focus: {ev.get('summary')}"
                                 blk_ev['colorId'] = "7" # Peacock (Work)
                                 
                                 # Ensure we have a start time for the block. 
                                 # If task start_time is a date (YYYY-MM-DD), add convenient time
                                 s_raw = blk_ev.get('start_time')
                                 if s_raw and 'T' not in s_raw:
                                      blk_ev['start_time'] = f"{s_raw}T10:00:00"
                                 
                                 svc = get_calendar_service()
                                 ok, msg = add_event_to_calendar(svc, blk_ev, cal_id)
                                 if ok: st.success("¡Tiempo Bloqueado!")
                                 else: st.error(msg)

                else:
                    if st.button(f"📅 Confirmar y Agendar '{summary}'", key=f"btn_add_{i}"):
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
    from modules.google_services import get_calendar_service, get_tasks_service, add_task_to_google, delete_event, update_event_calendar, delete_task_google, update_task_google, get_existing_tasks_simple, get_task_lists, delete_events_bulk, delete_tasks_bulk
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

    # --- UX GUIDE: PLANNER ---
    with st.expander("📚 Guía Rápida: Planificador Estratégico", expanded=False):
         st.markdown(ui.render_guide_card_html(
             "Convierte tus grandes metas en una agenda accionable. Genera un plan semanal estructurado basado en tus tareas y disponibilidad real.",
             "Usa el modo 'Desglosar Proyecto' para que la IA divida objetivos grandes en subtareas manejables automáticamente."
         ), unsafe_allow_html=True)

    calendar_context_str = ""
    calendar_id = st.session_state.get('connected_email', '')

    # Common Calendar Fetch (Optimized with TTL)
    if 'c_events_cache' not in st.session_state:
        st.session_state.c_events_cache = []
        st.session_state.c_events_cache_time = None

    # Check if cache needs refresh (TTL: 5 minutes)
    cache_expired = False
    if st.session_state.c_events_cache_time:
        import datetime as dt
        time_since_cache = (dt.datetime.now() - st.session_state.c_events_cache_time).total_seconds()
        if time_since_cache > 300:  # 5 minutes = 300 seconds
            cache_expired = True
            st.session_state.c_events_cache = []  # Clear expired cache

    # Always fetch if cache empty, expired, or requested (Only if email connected)
    if (not st.session_state.c_events_cache or cache_expired) and calendar_id:
        svc = get_calendar_service()
        if svc:
            try:
                today = datetime.date.today()
                t_min = datetime.datetime(today.year, 1, 1).isoformat() + 'Z'
                t_max = datetime.datetime(today.year, 12, 31, 23, 59, 59).isoformat() + 'Z'

                st.session_state.c_events_cache = svc.events().list(
                    calendarId=calendar_id, timeMin=t_min, timeMax=t_max, 
                    singleEvents=True, orderBy='startTime', maxResults=2000,
                    fields="items(summary,start,end,description,id,colorId)" 
                ).execute().get('items', [])
                
                # Update timestamp
                import datetime as dt
                st.session_state.c_events_cache_time = dt.datetime.now()
                
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
                                fields="items(summary,start,end,description,id,colorId)" 
                            ).execute().get('items', [])
                            fallback_success = True
                            st.toast(f"🤖 Usando cuenta Robot para ver {calendar_id}")
                            
                            # Update timestamp
                            import datetime as dt
                            st.session_state.c_events_cache_time = dt.datetime.now()
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

                # import modules.ui_interactive as ui_v2 (REMOVED due to SegFault risk)

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
                            tasks = plan_data[0].get(day_en, plan_data[0].get(day_es, []))

                        # Build Items for V2
                        day_items = []
                        for idx, t in enumerate(tasks):
                            day_items.append({
                                "id": f"{day_en}_{idx}",
                                "title": t[:50] + ("..." if len(t)>50 else ""),
                                "content": t,
                                "actions": [
                                    {"id": "delete", "label": "Borrar", "icon": "🗑️", "type": "danger", "autoHide": True},
                                    # {"id": "sync", "label": "Sync", "icon": "🚀", "type": "primary", "autoHide": False} # Individual sync optional
                                ]
                            })
                        
                        # Render Interactive List (Native)
                        for idx, t in enumerate(tasks):
                            with st.container():
                                st.markdown(f"""
                                <div style="background: rgba(24, 40, 42, 0.4); border: 1px solid rgba(255, 255, 255, 0.08); 
                                            border-radius: 8px; padding: 12px; margin-bottom: 8px; font-size: 0.9rem;">
                                    {t[:100]}...
                                </div>
                                """, unsafe_allow_html=True)
                                
                                c_act = st.columns([1, 4])
                                with c_act[0]:
                                    btn_k_key = f"btn_del_kb_{day_en}_{idx}"
                                    if st.button("🗑️", key=btn_k_key, help="Borrar"):
                                        st.session_state['triggered_kb_del'] = {'day': day_en, 'idx': idx, 'day_es': day_es}

                        # Handle Deletion State (Post-Loop)
                        if 'triggered_kb_del' in st.session_state:
                             trig = st.session_state.triggered_kb_del
                             # Validate it matches current loop context if needed or just execute
                             # Since we rerun immediately, global state is fine
                             d_key = trig['day']
                             d_idx = trig['idx']
                             d_es = trig['day_es']
                             
                             del st.session_state['triggered_kb_del'] # Reset
                             
                             try:
                                 # Update Session State
                                 current_list = None
                                 if isinstance(st.session_state.weekly_plan, dict):
                                     if d_key in st.session_state.weekly_plan:
                                         st.session_state.weekly_plan[d_key].pop(d_idx)
                                     elif d_es in st.session_state.weekly_plan:
                                         st.session_state.weekly_plan[d_es].pop(d_idx)
                                 
                                 st.toast("🗑️ Tarea eliminada del plan")
                                 time.sleep(0.3)
                                 st.rerun()
                             except Exception as e:
                                 st.error(f"Error borrando: {e}")

                        # Prepare for sync (Global button still useful)
                        for t in tasks:
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

    # --- BULK MANAGEMENT (DELETE) - COPIED FROM OPTIMIZE ---
    with st.expander("🗑️ Gestión Masiva (Eliminación)", expanded=False):
        st.warning("⚠️ ZONA DE PELIGRO: Las acciones aquí no se pueden deshacer.")
        
        tab_del_ev, tab_del_tk = st.tabs(["📅 Eliminar Eventos", "📝 Eliminar Tareas"])
        
        # TAB 1: EVENTS
        with tab_del_ev:
            c_de1, c_de2 = st.columns(2)
            with c_de1:
                de_start = st.date_input("Desde", datetime.date.today().replace(day=1), key="de_start_pl")
            with c_de2:
                de_end = st.date_input("Hasta", datetime.date.today().replace(day=28) + datetime.timedelta(days=4), key="de_end_pl")
            
            st.info(f"Se eliminarán TODOS los eventos entre {de_start} y {de_end} del calendario seleccionado.")
            
            confirm_ev = st.checkbox("Entiendo que esto es irreversible", key="chk_del_ev_pl")
            if st.button("🗑️ Eliminar Eventos en Rango", disabled=not confirm_ev, type="primary", key="btn_del_bulk_pl"):
                with st.spinner("Eliminando eventos..."):
                    cal_id_target = st.session_state.get('connected_email', 'primary')
                    svc = get_calendar_service()
                    if svc:
                        count = delete_events_bulk(svc, cal_id_target, de_start, de_end)
                        if isinstance(count, int):
                            st.success(f"✅ Se eliminaron {count} eventos.")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"Error: {count}")

        # TAB 2: TASKS
        with tab_del_tk:
            st.write("Selecciona Lista:")
            task_svc = get_tasks_service()
            if task_svc:
                lists = get_task_lists(task_svc)
                list_opts = {l['title']: l['id'] for l in lists}
                sel_list_name = st.selectbox("Lista de Tareas", list(list_opts.keys()), key="sel_list_pl")
                sel_list_id = list_opts.get(sel_list_name)
                
                del_mode = st.radio("Modo de Eliminación", ["Por Fecha de Vencimiento", "TODO (Vaciar Lista)"], key="radio_del_tk_pl")
                
                dt_start, dt_end = None, None
                if "Fecha" in del_mode:
                    c_dt1, c_dt2 = st.columns(2)
                    with c_dt1: dt_start = st.date_input("Vencimiento Desde", datetime.date.today(), key="tk_start_pl")
                    with c_dt2: dt_end = st.date_input("Vencimiento Hasta", datetime.date.today(), key="tk_end_pl")
                
                confirm_tk = st.checkbox("Confirmar eliminación permanente de tareas", key="chk_del_tk_pl")
                
                if st.button("🗑️ Eliminar Tareas", disabled=not confirm_tk, type="primary", key="btn_del_tk_pl"):
                    with st.spinner("Eliminando tareas..."):
                        delete_all = "TODO" in del_mode
                        count = delete_tasks_bulk(task_svc, sel_list_id, dt_start, dt_end, delete_all=delete_all)
                         
                        if isinstance(count, int):
                            st.success(f"✅ Se eliminaron {count} tareas.")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"Error: {count}")
    # --------------------------------

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
        cal_id = 'primary' # FORCE PRIMARY

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

            # --- SMART LISTS SETUP ---
            # Fetch lists once
            tl_cache = get_task_lists(tasks_svc)
            # Define Smart Lists we want
            smart_target = ["Inbox", "Hoy", "Proyectos"]
            
            # Allow creating new task here
            with st.form("quick_task_form", clear_on_submit=True):
                c_form1, c_form2, c_form3 = st.columns([3, 1.5, 1])
                with c_form1:
                    new_t = st.text_input("➕ Nueva Tarea", placeholder="Escribir...", label_visibility="collapsed")
                with c_form2:
                    # Map names to IDs
                    list_opts = {l['title']: l['id'] for l in tl_cache}
                    # Default to @default or first one
                    sel_list_name = st.selectbox("Lista", options=list_opts.keys(), label_visibility="collapsed")
                with c_form3:
                    submitted = st.form_submit_button("Agregar 🚀", use_container_width=True)

                if submitted and new_t:
                    target_id = list_opts.get(sel_list_name, '@default')
                    res = add_task_to_google(tasks_svc, target_id, new_t)
                    if res: 
                        st.success(f"Tarea añadida a '{sel_list_name}'")
                        time.sleep(1) # Give API a moment
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
                                st.toast(f"🗑️ Intentando borrar tarea {t['id']}...", icon="🛑")
                                delete_task_google(tasks_svc, t['list_id'], t['id'])
                                st.rerun()


def view_inbox():
    from modules.google_services import get_gmail_credentials, archive_old_emails, get_calendar_service, add_event_to_calendar, get_tasks_service, add_task_to_google


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
            keys_to_clear = ['connected_email', 'google_token', 'calendar_service', 'tasks_service', 'sheets_service', 'user_data_full', 'inbox_target_calendar_id']
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

        # --- CALENDAR SELECTOR (NEW) ---
        c_cal_sel, _ = st.columns([2, 1])
        with c_cal_sel:
            # Fetch calendars
            try:
                cal_service = get_calendar_service()
                if cal_service:
                    from modules.google_services import get_calendar_list
                    cals = get_calendar_list(cal_service)
                    if cals:
                        # Format for display
                        cal_opts = {f"{c['summary']} ({c['id']})": c['id'] for c in cals}
                        # Default to primary or previous selection
                        def_idx = 0
                        
                        sel_cal_name = st.selectbox("📅 Calendario Destino:", options=list(cal_opts.keys()), index=def_idx, help="Elige en qué calendario guardar los eventos.")
                        st.session_state.inbox_target_calendar_id = cal_opts[sel_cal_name]
                    else:
                        st.session_state.inbox_target_calendar_id = 'primary'
            except:
                st.session_state.inbox_target_calendar_id = 'primary'
        # -------------------------------

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

        # --- UX GUIDE: INBOX ---
        with st.expander("📚 Guía Rápida: Análisis de Buzón", expanded=False):
             st.markdown(ui.render_guide_card_html(
                 "No dejes que los compromisos se pierdan en tu correo. La IA escanea tu bandeja de entrada, extrae fechas clave y sugiere acciones.",
                 "Usa el botón 'Bloquear Tiempo' en las tareas detectadas para asegurar tu espacio de trabajo antes de que se llene la agenda."
             ), unsafe_allow_html=True)

        # Display Quota Info
        if 'license_key' in st.session_state:
            _, rem, use, lim = auth.check_and_update_daily_quota(st.session_state.license_key)
            st.progress(min(1.0, use/lim) if lim > 0 else 0, text=f"Cuota Diaria: {use}/{lim} analizados")

        max_fetch = st.slider(f"Max Correos a Leer:", 5, effective_limit, effective_limit, help="Definido por Admin.")

        # Logic to handle auto-continue after auth reload
        if 'trigger_mail_analysis' not in st.session_state:
            st.session_state.trigger_mail_analysis = False

        # Check Quota BEFORE Rendering Button
        quota_allowed = True
        if 'license_key' in st.session_state:
            # Check without updating usage (just read)
            # Since check_and_update_daily_quota updates usage only if requested_amount > 0 or default 0? 
            # Looking at auth.py signature: check_and_update_daily_quota(key, requested_amount=0) -> returns status
            allowed, remaining, usage, limit = auth.check_and_update_daily_quota(st.session_state.license_key, requested_amount=0)
            if usage >= limit:
                quota_allowed = False
                st.error(f"❌ Has alcanzado tu límite diario de análisis ({usage}/{limit}).")
                st.info("🕒 Podrás analizar más correos mañana.")

        if quota_allowed:
            c_act_a, c_act_b = st.columns([2, 1])
            with c_act_a:
                if st.button("🔄 Conectar y Analizar Buzón", use_container_width=True):
                    st.session_state.trigger_mail_analysis = True
            with c_act_b:
                if st.button("☢️ Limpieza (Promociones > 30d)", help="Opción Nuclear: Archiva promociones antiguas.", use_container_width=True):
                    with st.spinner("Ejecutando limpieza masiva..."):
                        from modules.google_services import archive_old_emails, get_gmail_credentials
                        from googleapiclient.discovery import build
                        # Ensure creds
                        creds = get_gmail_credentials()
                        if creds:
                            svc = build('gmail', 'v1', credentials=creds)
                            count = archive_old_emails(svc, hours_old=720) # 30 days
                            if count >= 0:
                                st.success(f"✅ Se archivaron {count} correos antiguos.")
                                time.sleep(2)
                                st.rerun()
                            else:
                                st.error("Error en limpieza.")
                        else:
                            st.error("No conectado.")

        else:
            # Ensure analysis doesn't run if quota exceeded even if triggered somehow
            st.session_state.trigger_mail_analysis = False

        # --- HISTORIAL GLOBAL INTERACTIVO (Moved Outside Conditional) ---
        all_ids = set()
        if 'user_data_full' in st.session_state:
            history = auth.get_user_history(st.session_state.user_data_full)

            # Extract IDs for filtering later
            processed_mail = {x['id'] for x in history['mail'] if x.get('id')}
            processed_tasks = {x['id'] for x in history['tasks'] if x.get('id')} 
            processed_labels = {x['id'] for x in history['labels'] if x.get('id')}
            all_ids = processed_mail | processed_tasks | processed_labels

            # Display Global History
            total_hist = len(history['mail']) + len(history['tasks'])
            
            if total_hist > 0:
                with st.expander(f"📜 Historial Interactivo ({total_hist} ítems)", expanded=False):
                    st.info("Aquí puedes ver elementos capturados anteriormente y procesarlos si olvidaste hacerlo.")
                    
                    tab_hm, tab_ht = st.tabs(["📧 Correos Leídos", "📝 Tareas Guardadas"])
                    
                    with tab_hm:
                        try:
                            # Re-fetch users might be needed if state is weird, but using session_state is best
                            mail_items = sorted(history['mail'], key=lambda x: x.get('d', ''), reverse=True)
                        except:
                            mail_items = history['mail']
                            
                        for idx, h_item in enumerate(mail_items[:50]):
                            c_h1, c_h2 = st.columns([3, 1])
                            with c_h1:
                                st.markdown(f"**{h_item.get('d','?')}** - {h_item.get('s','Unknown')}")
                                if h_item.get('id'):
                                    t_id = h_item.get('id')
                                    clean_id = t_id.replace('msg-', '')
                                    u_email = st.session_state.get('connected_email', '0')
                                    lnk = f"https://mail.google.com/mail/u/?authuser={u_email}#inbox/{clean_id}"
                                    st.caption(f"[Ver Correo]({lnk})")
                            
                            with c_h2:
                                if st.button("📅 Agendar", key=f"hist_btn_ev_{idx}"):
                                    st.session_state[f"show_hist_cal_{idx}"] = True
                            
                            if st.session_state.get(f"show_hist_cal_{idx}", False):
                                with st.form(f"hist_form_cal_{idx}"):
                                    st.write("Agendar Evento")
                                    new_sum = st.text_input("Título", value=h_item.get('s', 'Evento'))
                                    d_val = datetime.date.today()
                                    try: d_val = datetime.datetime.strptime(h_item.get('d'), '%Y-%m-%d').date()
                                    except: pass
                                    
                                    new_date = st.date_input("Fecha", value=d_val)
                                    new_time = st.time_input("Hora", value=datetime.time(9,0))
                                    
                                    if st.form_submit_button("Confirmar Agendar"):
                                        svc_cal = get_calendar_service()
                                        cid = st.session_state.get('inbox_target_calendar_id', 'primary') # Use Selected
                                        if svc_cal:
                                            start_dt = datetime.datetime.combine(new_date, new_time)
                                            end_dt = start_dt + datetime.timedelta(hours=1)
                                            body = {
                                                'summary': new_sum,
                                                'description': f"Recuperado del historial. ID: {h_item.get('id')}",
                                                'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'America/Santiago'},
                                                'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'America/Santiago'},
                                            }
                                            try:
                                                svc_cal.events().insert(calendarId=cid, body=body).execute()
                                                st.toast("✅ Evento creado exitosamente.")
                                                st.session_state[f"show_hist_cal_{idx}"] = False
                                                # Optional: Don't rerun immediately if not needed, or rerun to close form
                                                time.sleep(1)
                                                st.rerun()
                                            except Exception as e:
                                                st.error(f"Error: {e}")

                    with tab_ht:
                        try:
                            task_items = sorted(history['tasks'], key=lambda x: x.get('d', ''), reverse=True)
                        except: task_items = history['tasks']
                        
                        for idx, t_item in enumerate(task_items[:50]):
                            c_t1, c_t2 = st.columns([3, 1])
                            with c_t1:
                                st.markdown(f"**{t_item.get('d','?')}** - {t_item.get('s','Unknown')}")
                            with c_t2:
                                if st.button("📝 Tarea", key=f"hist_btn_tk_{idx}"):
                                    st.session_state[f"show_hist_tk_{idx}"] = True
                                    
                            if st.session_state.get(f"show_hist_tk_{idx}", False):
                                with st.form(f"hist_form_tk_{idx}"):
                                    st.write("Crear Tarea")
                                    tk_title = st.text_input("Título", value=t_item.get('s', 'Tarea'))
                                    tk_due = st.date_input("Vencimiento", value=datetime.date.today())
                                    
                                    if st.form_submit_button("Guardar Tarea"):
                                        svc_tk = get_tasks_service()
                                        if svc_tk:
                                            due_dt = datetime.datetime.combine(tk_due, datetime.time(12,0))
                                            res = add_task_to_google(svc_tk, "@default", tk_title, "Recuperado de historial", due_date=due_dt)
                                            if res:
                                                st.toast("✅ Tarea creada.")
                                                st.session_state[f"show_hist_tk_{idx}"] = False
                                                time.sleep(1)
                                                st.rerun()
                                            else:
                                                st.error("Error creando tarea.")
        # ------------------------------------------------------------

        # Execute if triggered
        if st.session_state.trigger_mail_analysis:
            from googleapiclient.discovery import build
            creds = get_gmail_credentials() # This might stop/rerun

            if creds:
                # REFRESH USER DATA (Hot Reload for Quota/History)
                if 'license_key' in st.session_state:
                    fresh_data = auth.refresh_user_data(st.session_state.license_key)
                    if fresh_data:
                        st.session_state.user_data_full = fresh_data
                        # st.toast("🔄 Datos de usuario actualizados.") 

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
                        st.warning("No se encontraron correos nuevos relevantes en el período.")
                    else:
                        # --- FILTER (Always Skip Already Processed) ---
                        force_re = False  # Re-analysis removed, always respect history
                        
                        initial_count = len(emails)
                        emails = [e for e in emails if e['id'] not in all_ids]
                        skipped_count = initial_count - len(emails)
                        if skipped_count > 0:
                            st.info(f"⏩ Se omitieron **{skipped_count} correos** ya presentes en tu Historial Global.")
                        # --------------

                        if not emails:
                            st.warning("Todos los correos recientes ya fueron procesados. ¡Estás al día!")
                        else:
                            st.session_state.fetched_emails = emails
                            
                            # === EMERGENCY LOGGING ===
                            st.info(f"📊 DEBUG: Procesando {len(emails)} correos...")
                            
                            analyzed_items = []
                            try:
                                with st.spinner(f"🧠 La IA está analizando y categorizando {len(emails)} correos..."):
                                    analyzed_items = analyze_emails_ai(emails)
                                
                                # FORCE debug output check
                                if 'debug_ai_raw' not in st.session_state or not st.session_state.debug_ai_raw:
                                    st.error("⚠️ CRITICAL: analyze_emails_ai NO capturó debug output. Posible fallo silencioso.")
                                else:
                                    st.success(f"✅ Debug capturado: {len(st.session_state.debug_ai_raw)} batches")
                                    
                            except Exception as ai_err:
                                st.error(f"❌ ERROR EN ANÁLISIS DE IA: {ai_err}")
                                st.error(f"Tipo: {type(ai_err).__name__}")
                                import traceback
                                st.code(traceback.format_exc())
                                analyzed_items = []
                            
                            st.session_state.ai_gmail_events = analyzed_items 
                            
                            # --- GTD AUTO-TAG (New Feature) ---
                            with st.spinner("🏷️ Aplicando etiquetas GTD..."):
                                from modules.google_services import auto_tag_gtd
                                tagged_count = auto_tag_gtd(service_gmail, analyzed_items, user_id='me')
                                if tagged_count > 0:
                                    st.toast(f"✅ {tagged_count} etiquetas GTD aplicadas.")
                            # ---------------------------------- 

                            # --- ATOMIC SAVE: HISTORY + QUOTA ---
                            # CRITICAL FIX: Only save if NOT in re-analysis mode
                            if not force_re and 'license_key' in st.session_state:
                                rich_items = []
                                if emails:
                                    for e in emails:
                                        if e.get('id'):
                                            s_text = e.get('subject', e.get('snippet', 'Sin Asunto'))[:50]
                                            rich_items.append({
                                                'id': e['id'], 
                                                's': s_text,
                                                'd': e.get('date', datetime.date.today().strftime('%Y-%m-%d'))
                                            })

                                # Call ATOMIC function
                                auth.update_history_and_quota(
                                    st.session_state.license_key, 
                                    {'mail': rich_items}, 
                                    quota_amount=len(emails)
                                )
                            elif force_re:
                                st.warning("⚠️ Modo Re-análisis: NO se guardará historial ni se consumirá cuota.")
                            # -------------------------------------

                            # Auto-labeling REMOVED. Now handled manually in UI.

                            if not analyzed_items:
                                st.warning('La IA leyó los correos pero no encontró nada accionable.')
                except Exception as e:
                    st.error(f"Error procesando correos: {e}")
                    import traceback
                    st.code(traceback.format_exc())
                finally:
                    # Reset trigger so it doesn't loop forever
                    st.session_state.trigger_mail_analysis = False
            else:
                pass
                
        # --- DEBUG AI OUTPUT (ADMIN ONLY) ---
        user_role = st.session_state.get('user_data_full', {}).get('rol', '').strip().upper()
        if user_role == 'ADMIN':
            with st.expander("🕵️ Output Crudo de IA (Debug - ADMIN ONLY)", expanded=False):
                if 'debug_ai_raw' in st.session_state and st.session_state.debug_ai_raw:
                    st.info(f"Total batches capturados: {len(st.session_state.debug_ai_raw)}")
                    for idx, d in enumerate(st.session_state.debug_ai_raw):
                        st.text(f"--- Batch {idx+1} ---")
                        st.code(d, language='json')
                else:
                    st.warning("⚠️ No hay output de IA todavía. Ejecuta un análisis primero.")
                    st.info("Si acabas de ejecutar y ves esto, significa que analyze_emails_ai falló silenciosamente.")
        # -----------------------

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
                                        # --- SAVE HISTORY: LABELS (RICH METADATA) ---
                                        rich_labels = []
                                        for x in items:
                                            if x.get('id'):
                                                rich_labels.append({
                                                    'id': x['id'],
                                                    's': x.get('summary', 'Etiquetado'),
                                                    'd': datetime.date.today().strftime('%Y-%m-%d')
                                                })

                                        if rich_labels and 'license_key' in st.session_state:
                                            auth.update_user_history(st.session_state.license_key, {'labels': rich_labels})
                                        # ----------------------------

                                        st.success(f"¡Listo! {count_ok} correos etiquetados.")
                                        time.sleep(2)
                                        st.rerun()
                                    else:
                                        st.warning("No se pudo etiquetar nada.")
                    else:
                        st.write("No hay correos para etiquetar.")

                with tab_ev:
                    # New Strict Logic: 'type' == 'event'
                    events = [x for x in items if x.get('type') == 'event' or (x.get('is_event') is True)] 
                    if not events: st.info("No hay eventos de calendario estrictos.")

                    # Prepare V2 Items
                    v2_events = []
                    from modules.google_services import check_event_exists, get_calendar_service, add_event_to_calendar
                    
                    # Use Selected Calendar from Session State
                    cal_id = st.session_state.get('inbox_target_calendar_id', 'primary')
                    
                    service_cal = get_calendar_service()

                    for ev in events:
                        is_scheduled = False
                        if service_cal:
                             is_scheduled = check_event_exists(service_cal, cal_id, ev)
                        
                        # Generate Content HTML with Badge
                        badge = render_date_badge(ev.get('start_time', ''))
                        
                        desc_html = f"""
                         <div style="display: flex; gap: 15px; align-items: start;">
                             {badge}
                             <div>
                                 <div style="font-weight: bold; color: white;">{ev.get('category','-')}</div>
                                 <div style="color: #ccc; font-size: 0.9rem;">{ev.get('description', '-')}</div>
                             </div>
                         </div>
                        """
                        if ev.get('id'):
                            t_id = ev.get('threadId', ev['id'])
                            u_email = st.session_state.get('connected_email', '0')
                            link = f"https://mail.google.com/mail/u/?authuser={u_email}#inbox/{t_id}"
                            desc_html += f'<div style="margin-top:8px;"><a href="{link}" target="_blank" style="color:#0dd7f2;text-decoration:none;">🔗 Ver Correo Original</a></div>'

                        actions = []
                        if is_scheduled:
                            actions.append({"id": "regenerate", "label": "Regenerar", "icon": "🔄", "type": "secondary", "autoHide": False}) # Don't hide for regen
                            actions.append({"id": "view", "label": "Agendado", "icon": "✅", "type": "secondary", "autoHide": False})
                        else:
                            actions.append({"id": "schedule", "label": "Agendar", "icon": "📅", "type": "primary", "autoHide": True})

                        v2_events.append({
                            "id": ev['id'], # Use email ID or generated ID
                            "title": f"{ev.get('summary', 'Evento')}",
                            "subtitle": ev.get('urgency','Media'),
                            "content": desc_html,
                            "actions": actions
                        })


                    # Render Component
                    # Render Native UI (Fallback for Reliability)
                    for idx_ev, ev in enumerate(v2_events):
                        # Card Container
                        with st.container():
                            st.markdown(f"""
                            <div style="background: rgba(24, 40, 42, 0.4); border: 1px solid rgba(255, 255, 255, 0.08); 
                                        border-radius: 12px; padding: 16px; margin-bottom: 12px;">
                                {ev['content']}
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Actions Row
                            cols = st.columns(len(ev['actions']) + 2) # Flex spacing
                            for idx, act in enumerate(ev['actions']):
                                with cols[idx]:
                                    # Create specific unique key
                                    btn_key = f"btn_{act['id']}_{ev['id']}_{idx_ev}"
                                    if st.button(f"{act['icon']} {act['label']}", key=btn_key):
                                        st.session_state['triggered_action'] = {'itemId': ev['id'], 'actionId': act['id']}

                    # Handle Triggered Action (from above buttons)
                    if 'triggered_action' in st.session_state:
                         trigger = st.session_state.triggered_action
                         ev_id = trigger['itemId']
                         act_id = trigger['actionId']
                         del st.session_state['triggered_action'] # Consume click immediately
                         
                         target_ev = next((e for e in events if e['id'] == ev_id), None)
                         
                         if target_ev and service_cal:
                             if act_id == "schedule" or act_id == "regenerate":
                                 # Append Link to Description
                                 final_desc = target_ev.get('description', '-')
                                 st.toast(f"📅 Agendando '{target_ev.get('summary')}'...", icon="⏳")
                                 
                                 if target_ev.get('id'):
                                     t_id = target_ev.get('threadId', target_ev['id'])
                                     user_email = st.session_state.get('connected_email', '0')
                                     link = f"https://mail.google.com/mail/u/?authuser={user_email}#inbox/{t_id}"
                                     if link not in final_desc:
                                         final_desc += f"\n\n🔗 Correo: {link}"

                                 ev_to_add = target_ev.copy()
                                 ev_to_add['description'] = final_desc

                                 # Force Work Hour Limits (Mon-Thu 17h, Fri 16h)
                                 # (Already handled by AI/helper, but good to ensure default logic applies if AI missed it)
                                 
                                 with st.spinner("Agendando..."):
                                     res, msg = add_event_to_calendar(service_cal, ev_to_add, cal_id)
                                     if res:
                                         # Save History
                                         if 'license_key' in st.session_state:
                                              rich_ev = [{'id': target_ev['id'], 's': target_ev.get('summary', 'Evento'), 'd': datetime.date.today().strftime('%Y-%m-%d')}]
                                              auth.update_user_history(st.session_state.license_key, {'mail': rich_ev})
                                         
                                         st.toast("✅ Evento agendado correctamente")
                                         time.sleep(1) 
                                         st.rerun()
                                     else:
                                         st.error(f"Error: {msg}")

                with tab_info:
                    # New Strict Logic: 'type' == 'task'
                    tasks = [x for x in items if x.get('type') == 'task' or (x.get('is_event') is False)]
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

                            # --- SMART REPLY UI ---
                            st.divider()
                            st.caption("🤖 Asistente de Respuesta")
                            c_sr1, c_sr2 = st.columns([2, 1])
                            with c_sr1:
                                intent_opts = ["Confirmar recepción", "Solicitar reunión", "Agradecer", "Pedir más detalles", "Rechazar amablemente", "Delegar"]
                                intent = st.selectbox("Intención", intent_opts, key=f"sr_int_{i}", label_visibility="collapsed")
                            with c_sr2:
                                if st.button("✍️ Redactar", key=f"sr_gen_{i}", use_container_width=True):
                                    with st.spinner("Redactando..."):
                                        from modules.ai_core import generate_reply_email
                                        draft_text = generate_reply_email(t.get('body', ''), intent)
                                        st.session_state[f"draft_body_{i}"] = draft_text

                            if st.session_state.get(f"draft_body_{i}"):
                                d_body = st.text_area("Borrador", st.session_state[f"draft_body_{i}"], key=f"dr_txt_{i}", height=150)
                                if st.button("📤 Guardar en Borradores Gmail", key=f"dr_save_{i}"):
                                    from modules.google_services import create_draft, get_gmail_credentials
                                    creds = get_gmail_credentials()
                                    if creds:
                                        from googleapiclient.discovery import build
                                        svc = build('gmail', 'v1', credentials=creds)
                                        # Get original subject if available
                                        original_subject = t.get('subject_original', t.get('summary', 'Re: (Sin asunto)'))
                                        if not original_subject.startswith('Re:'):
                                            original_subject = f"Re: {original_subject}"
                                        
                                        if create_draft(svc, 'me', d_body, subject=original_subject):
                                            st.success("✅ Borrador guardado en Gmail.")
                                            time.sleep(1)
                                            # Optional: Clear state
                                            del st.session_state[f"draft_body_{i}"]
                                            st.rerun()
                                        else: 
                                            st.error("Error guardando.")
                            # ----------------------

                            # Action: Save as Task OR Time Block
                            c_task1, c_task2 = st.columns([1, 1.2]) # Adjusted ratio
                            
                            # Option 1: Calendar Block (Focus)
                            with c_task1:
                                if st.button(f"⏱️ Bloquear (Focus)", key=f"btn_blk_tk_{i}", use_container_width=True):
                                     cal_id = st.session_state.get('connected_email')
                                     svc_cal = get_calendar_service()
                                     if svc_cal and cal_id:
                                         # Create Block Event
                                         blk_ev = {
                                             'summary': f"Focus: {t.get('summary')}",
                                             'description': t.get('description', '') + (f"\n\n🔗 {email_link}" if email_link else ""),
                                             'start_time': datetime.datetime.now().replace(hour=10, minute=0).isoformat(), # Default 10am
                                             'colorId': "7" # Peacock
                                         }
                                         res, msg = add_event_to_calendar(svc_cal, blk_ev, cal_id)
                                         if res: st.success("¡Tiempo Bloqueado!")
                                         else: st.error(msg)
                            
                            # Option 2: Google Task with List Selection
                            with c_task2:
                                # Fetch lists for selector (Cached ideally, but doing it here for safety)
                                # Optimization: We could fetch once outside loop, but Streamlit caches get_task_lists logic if we wrap it properly or relies on session.
                                # For now, let's assume get_tasks_service is fast enough or we just use default if this is slow.
                                # To avoid slow API calls inside loop, we'll just use a text input or a simplified selector if we had top-level cache.
                                # BETTER: Just separate the button.
                                
                                if st.button("💾 Guardar Tarea (@Default)", key=f"btn_tk_{i}", use_container_width=True):
                                    svc_tasks = get_tasks_service()
                                    if svc_tasks:
                                        # Append Link to Notes
                                        final_notes = t.get('description', '')
                                        if email_link:
                                            final_notes += f"\n\n🔗 Correo: {email_link}"

                                        # Default Due Date: Today + 1
                                        due_dt = datetime.datetime.now() + datetime.timedelta(days=1)
                                        due_dt = due_dt.replace(hour=12, minute=0)

                                        res = add_task_to_google(svc_tasks, "@default", t.get('summary'), final_notes, due_date=due_dt)

                                        if res:
                                            # --- SAVE HISTORY: TASK (RICH) ---
                                            if t.get('id') and 'license_key' in st.session_state:
                                                rich_tk = [{
                                                    'id': t['id'],
                                                    's': t.get('summary', 'Tarea Guardada'),
                                                    'd': datetime.date.today().strftime('%Y-%m-%d'),
                                                    't': 'task'
                                                }]
                                                auth.update_user_history(st.session_state.license_key, {'tasks': rich_tk})
                                            # --------------------------
                                            st.success(f"✅ Guardada en Inbox")
                                            time.sleep(1)
                                            st.rerun()
                                        else:
                                            st.error("❌ Error al guardar tarea.")

        elif 'fetched_emails' in st.session_state:
            st.info(f"📨 Se leyeron {len(st.session_state.fetched_emails)} correos. Esperando análisis...")

def view_optimize():
    from modules.google_services import get_calendar_service, get_tasks_service, add_task_to_google, delete_events_bulk, delete_tasks_bulk, deduplicate_calendar_events, deduplicate_tasks
    
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

    # --- UX GUIDE: OPTIMIZE ---
    with st.expander("📚 Guía Rápida: Auditoría y Optimización", expanded=False):
         import modules.ui_components as ui
         st.markdown(ui.render_guide_card_html(
             "El Optimizador actúa como un consultor de productividad externo. Analiza tu agenda futura para detectar conflictos, días sobrecargados y oportunidades de mejora.",
             "Úsalo al principio de la semana para asegurar tiempos de enfoque y evitar el agotamiento."
         ), unsafe_allow_html=True)

    calendar_id = st.session_state.get('connected_email', '')
    if not calendar_id:
        st.warning("⚠️  Configura tu ID de Calendario en la barra lateral.")
        return

    # --- HISTORIAL INTERACTIVO DE OPTIMIZACIONES ---
    if 'user_data_full' in st.session_state:
        history = auth.get_user_history(st.session_state.user_data_full)
        opt_ids = {x.get('id') for x in history.get('opt_events', [])}
        
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

    st.divider()
    st.markdown("### 🧹 Limpieza de Duplicados")
    c_dup1, c_dup2 = st.columns([3, 1])
    c_dup1.info("Esta herramienta escaneará los eventos en el rango seleccionado y todas tus tareas para eliminar copias exactas.")

    if c_dup2.button("♻️ Escanear y Eliminar", type="secondary"):
        with st.spinner("Buscando y eliminando duplicados..."):
            from modules.google_services import deduplicate_calendar_events, deduplicate_tasks

            cal_svc = get_calendar_service()
            task_svc = get_tasks_service()

            deleted_ev = 0
            if cal_svc:
                deleted_ev = deduplicate_calendar_events(cal_svc, calendar_id, start_date, end_date)

            deleted_tk = 0
            if task_svc:
                deleted_tk = deduplicate_tasks(task_svc)

            if deleted_ev > 0 or deleted_tk > 0:
                st.success(f"✅ Limpieza Completada: Se eliminaron **{deleted_ev} eventos** y **{deleted_tk} tareas** duplicadas.")
                time.sleep(2)
                st.rerun()
            else:
                st.success("✨ No se encontraron duplicados. Tu agenda está limpia.")

    # --- BULK MANAGEMENT (DELETE) ---
    with st.expander("🗑️ Gestión Masiva (Eliminación)", expanded=False):
        st.warning("⚠️ ZONA DE PELIGRO: Las acciones aquí no se pueden deshacer.")
        
        tab_del_ev, tab_del_tk = st.tabs(["📅 Eliminar Eventos", "📝 Eliminar Tareas"])
        
        # TAB 1: EVENTS
        with tab_del_ev:
            c_de1, c_de2 = st.columns(2)
            with c_de1:
                de_start = st.date_input("Desde", datetime.date.today().replace(day=1), key="de_start")
            with c_de2:
                de_end = st.date_input("Hasta", datetime.date.today().replace(day=28) + datetime.timedelta(days=4), key="de_end")
            
            st.info(f"Se eliminarán TODOS los eventos entre {de_start} y {de_end} del calendario seleccionado ({calendar_id}).")
            
            confirm_ev = st.checkbox("Entiendo que esto es irreversible", key="chk_del_ev")
            if st.button("🗑️ Eliminar Eventos en Rango", disabled=not confirm_ev, type="primary"):
                with st.spinner("Eliminando eventos..."):
                    from modules.google_services import delete_events_bulk, get_calendar_service
                    svc = get_calendar_service()
                    if svc:
                        count = delete_events_bulk(svc, calendar_id, de_start, de_end)
                        if isinstance(count, int):
                            st.success(f"✅ Se eliminaron {count} eventos.")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"Error: {count}")

        # TAB 2: TASKS
        with tab_del_tk:
            st.write("Selecciona Lista:")
            task_svc = get_tasks_service()
            if task_svc:
                lists = get_task_lists(task_svc)
                list_opts = {l['title']: l['id'] for l in lists}
                sel_list_name = st.selectbox("Lista de Tareas", list(list_opts.keys()))
                sel_list_id = list_opts.get(sel_list_name)
                
                del_mode = st.radio("Modo de Eliminación", ["Por Fecha de Vencimiento", "TODO (Vaciar Lista)"], key="radio_del_tk")
                
                dt_start, dt_end = None, None
                if "Fecha" in del_mode:
                    c_dt1, c_dt2 = st.columns(2)
                    with c_dt1: dt_start = st.date_input("Vencimiento Desde", datetime.date.today(), key="tk_start")
                    with c_dt2: dt_end = st.date_input("Vencimiento Hasta", datetime.date.today(), key="tk_end")
                
                confirm_tk = st.checkbox("Confirmar eliminación permanente de tareas", key="chk_del_tk")
                
                if st.button("🗑️ Eliminar Tareas", disabled=not confirm_tk, type="primary"):
                    with st.spinner("Eliminando tareas..."):
                        from modules.google_services import delete_tasks_bulk
                        delete_all = "TODO" in del_mode
                        count = delete_tasks_bulk(task_svc, sel_list_id, dt_start, dt_end, delete_all=delete_all)
                         
                        if isinstance(count, int):
                            st.success(f"✅ Se eliminaron {count} tareas.")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"Error: {count}")
    # --------------------------------


    if 'opt_events' in st.session_state and st.session_state.opt_events:
        events = st.session_state.opt_events

        # Fetch Tasks for Context
        task_svc = get_tasks_service()
        tasks = []
        if task_svc:
            tasks = get_existing_tasks_simple(task_svc)

        # --- PERSISTENCE FILTER ---
        if 'user_data_full' in st.session_state:
            # Re-fetch history to be safe
            history_now = auth.get_user_history(st.session_state.user_data_full)
            already_optimized_ids = {x.get('id') for x in history_now.get('opt_events', []) if x.get('id')}
            
            # Filter
            events_to_optimize = [e for e in events if e['id'] not in already_optimized_ids]
            skipped_count = len(events) - len(events_to_optimize)
            
            st.write(f"📅 Total Eventos: {len(events)} | ⚡ Pendientes de Optimizar: {len(events_to_optimize)}")
            if skipped_count > 0:
                st.caption(f"ℹ️ Se han omitido **{skipped_count} eventos** que ya fueron optimizados previamente.")
        else:
            events_to_optimize = events
            st.write(f"📅 Se leyeron {len(events)} eventos y {len(tasks)} tareas activas.")



        if st.button("🧠 AI: Analizar Agenda Completa (Eventos + Tareas)"):
             # === FORCE REFRESH: Clear cache and reimport data ===
             with st.spinner("🔄 Actualizando datos desde Google Calendar/Tasks..."):
                 # Clear cached events
                 if 'opt_events' in st.session_state:
                     del st.session_state['opt_events']
                 
                 # Reimport fresh data
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
                         events_to_optimize = st.session_state.opt_events
                         st.toast(f"✅ Datos actualizados: {len(events_to_optimize)} eventos", icon="✅")
                     except Exception as e:
                         st.error(f"Error actualizando datos: {e}")
                         events_to_optimize = []
                 else:
                     events_to_optimize = []
                 
                 # Refetch tasks as well
                 task_svc = get_tasks_service()
                 tasks = []
                 if task_svc:
                     tasks = get_existing_tasks_simple(task_svc)
                     st.toast(f"✅ Tareas actualizadas: {len(tasks)}", icon="✅")
             
             # Now filter by optimization history
             if 'user_data_full' in st.session_state:
                 history_now = auth.get_user_history(st.session_state.user_data_full)
                 already_optimized_ids = {x.get('id') for x in history_now.get('opt_events', []) if x.get('id')}
                 events_to_optimize = [e for e in events_to_optimize if e['id'] not in already_optimized_ids]
             
             if not events_to_optimize and not tasks:
                  st.warning("No hay elementos nuevos para optimizar.")
             else:
                 with st.spinner("Analizando patrones y optimizando agenda..."):
                    # Only send new stuff + tasks
                    # (Tasks usually change state often so strict persistence might be overkill, 
                    # but we can improve later. For now, we optim tasks every time.)
                    result = analyze_agenda_ai(events_to_optimize, tasks)
                    if isinstance(result, dict):
                        st.session_state.opt_plan = result.get('optimization_plan', {})
                        st.session_state.advisor_note = result.get('advisor_note', "Sin comentarios.")
                    else:
                        st.warning("⚠️ Respuesta inesperada de la IA.")

        if 'opt_plan' in st.session_state:
            st.markdown("### 💡 Informe Estratégico:")
            st.info(st.session_state.advisor_note)

            st.subheader("Mejoras Propuestas:")

            with st.form("exec_optimization"):
                c1, c2, c3 = st.columns([2, 2, 1])
                c1.markdown("**Original**")
                c2.markdown("**Propuesta IA**")
                c3.markdown("**Acción**")

                # Render Events from Plan
                plan = st.session_state.opt_plan

                # We iterate through keys to find both events and tasks
                count_props = 0

                for item_id, proposal in plan.items():
                    item_type = proposal.get('type', 'event') # Default to event for backward compat

                    # Find original item data for display
                    orig_summary = "Desconocido"
                    if item_type == 'event':
                        found = next((e for e in events if e['id'] == item_id), None)
                        if found: orig_summary = found.get('summary', '')
                        new_text = proposal.get('new_summary', '')
                    else: # Task
                        found = next((t for t in tasks if t['id'] == item_id), None)
                        if found: orig_summary = f"📝 {found.get('title', '')}"
                        else: orig_summary = "📝 Tarea"
                        new_text = f"📝 {proposal.get('new_title', '')}"
                        if proposal.get('new_due'):
                            new_text += f"\n📅 {proposal['new_due']}"

                    if found:
                        c1, c2, c3 = st.columns([2, 2, 1])
                        c1.text(orig_summary)
                        c2.markdown(f"**{new_text}**")
                        c3.caption("Optimizar")
                        st.divider()
                        count_props += 1

                if count_props == 0:
                    st.write("No hay sugerencias de mejora para los ítems actuales.")

                if st.form_submit_button("✨ Ejecutar Transformación"):
                    service_cal = get_calendar_service()
                    service_task = get_tasks_service()
                    
                    # Store IDs of successfully optimized items
                    successful_ids = []

                    if service_cal:
                        bar = st.progress(0)
                        done = 0
                        total = len(plan)
                        idx = 0

                        for item_id, proposal in plan.items():
                            item_type = proposal.get('type', 'event')

                            try:
                                if item_type == 'event':
                                    ok = optimize_event(service_cal, calendar_id, item_id, proposal.get('new_summary'), proposal.get('colorId'))
                                    if ok: successful_ids.append(item_id)
                                    
                                elif item_type == 'task' and service_task:
                                    # Parse due date if present
                                    due_dt = None
                                    if proposal.get('new_due'):
                                        try:
                                            due_dt = datetime.datetime.strptime(proposal['new_due'], "%Y-%m-%d").date()
                                            # Add noon UTC for tasks
                                            due_dt = datetime.datetime.combine(due_dt, datetime.time(12,0))
                                        except: pass

                                    update_task_google(
                                        service_task, 
                                        proposal.get('list_id', '@default'), 
                                        item_id, 
                                        title=proposal.get('new_title'),
                                        due=due_dt
                                    )
                                    # Tasks don't have global unique IDs in the same way across all lists easily unless we track list_id too.
                                    # For now, we skip task persistence tracking or add it if needed later.
                                    
                                done += 1
                            except Exception as ex:
                                print(f"Error optimizing {item_id}: {ex}")

                            idx += 1
                            bar.progress(idx / total if total > 0 else 1.0)
                        
                        # --- SAVE OPTIMIZED IDS TO SHEET ---
                        if successful_ids and 'license_key' in st.session_state:
                            rich_opts = []
                            today_str = datetime.date.today().strftime('%Y-%m-%d')
                            for mid in successful_ids:
                                rich_opts.append({'id': mid, 's': 'Optimizado AI', 'd': today_str})
                            
                            auth.update_user_history(st.session_state.license_key, {'opt_events': rich_opts})
                        # -----------------------------------

                        st.success(f"¡Agenda Transformada! {done} elementos optimizados.")

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

# --- PRODUCTIVITY ANALYTICS ---


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
                    st.markdown("""
                    <div style="background: rgba(255,255,255,0.05); border-radius: 10px; padding: 15px; border: 1px solid rgba(255,255,255,0.1);">
                        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                            <span style="font-size: 1.5rem;">🏦</span>
                            <div>
                                <div style="color: #9cb6ba; font-size: 0.75rem; text-transform: uppercase;">Banco</div>
                                <div style="color: white; font-weight: bold;">Tenpo (Vista)</div>
                            </div>
                        </div>
                        <div style="margin-bottom: 8px;">
                            <div style="color: #9cb6ba; font-size: 0.75rem; text-transform: uppercase;">Nro Cuenta</div>
                            <div style="color: #0dd7f2; font-family: monospace; font-size: 1.1rem; letter-spacing: 1px;">111118581575</div>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <div>
                                <div style="color: #9cb6ba; font-size: 0.75rem; text-transform: uppercase;">RUT</div>
                                <div style="color: white;">18.581.575-7</div>
                            </div>
                            <div style="text-align: right;">
                                <div style="color: #9cb6ba; font-size: 0.75rem; text-transform: uppercase;">Mail</div>
                                <div style="color: white; font-size: 0.9rem;">alain.antinao.s@gmail.com</div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        # QUICK NOTE WIDGET (Removed)
        # notes_view.render_brain_dump_widget()
        # st.divider()

        # Navigation Buttons with icons and emojis for visual appeal
        nav_options = {
            "Dashboard": "📊 Panel Principal",
            "Chat": "💬 Asistente", # NEW CHAT OPTION
            "Create": "➕ Crear Evento",
            "Planner": "📅 Planificador",
            "Inbox": "📧 Bandeja IA",
            "Notes": "🧠 Notas/Ideas",
            "Optimize": "⚡ Optimizar",
            "Insights": "📉 Insights",
            "Account": "⚙️ Mi Cuenta"
        }

        selection = st.radio("Navegación", list(nav_options.keys()), format_func=lambda x: nav_options[x], label_visibility="collapsed")

        st.divider()
        st.caption("Configuración de Calendario")
        
        
        # Input de Calendar ID
        current_calendar = st.session_state.get('connected_email', '')
        new_calendar = st.text_input("ID Calendario", value=current_calendar, key='connected_email_input', 
                                     help="Ingresa tu email de Google Calendar")

        # Detectar cambio y guardar
        # CRITICAL: Only save if user is authenticated (has license_key)
        # This prevents saving during app logout when session states are being cleared
        if new_calendar != current_calendar and 'license_key' in st.session_state:
            st.session_state.connected_email = new_calendar
            # SIEMPRE guardar, incluso si está vacío
            auth.save_calendar_session(st.session_state.license_key, new_calendar)
            
            # Limpiar caché al cambiar calendario
            if 'c_events_cache' in st.session_state:
                del st.session_state['c_events_cache']
            if 'c_events_cache_time' in st.session_state:
                del st.session_state['c_events_cache_time']
            if new_calendar:
                st.toast("🔄 Caché de eventos limpiado")
            else:
                st.toast("📅 Sesión de calendario cerrada")

        # Botones de control
        col_cal_1, col_cal_2 = st.columns(2)
        with col_cal_1:
            if st.button("🔄 Refrescar", key="btn_refresh", use_container_width=True, 
                        help="Limpiar caché y actualizar eventos"):
                if 'c_events_cache' in st.session_state:
                    del st.session_state['c_events_cache']
                if 'c_events_cache_time' in st.session_state:
                    del st.session_state['c_events_cache_time']
                st.success("✅ Caché limpiado")
                st.rerun()

        with col_cal_2:
            if st.button("🚪 Cerrar Cal", key="btn_logout_cal", use_container_width=True,
                        help="Cerrar sesión de calendario"):
                # Clear session state
                st.session_state.connected_email = ''
                
                # Delete widget key to force reset (can't modify after widget creation)
                if 'connected_email_input' in st.session_state:
                    del st.session_state['connected_email_input']
                
                # Save empty to Sheets
                if 'license_key' in st.session_state:
                    auth.save_calendar_session(st.session_state.license_key, '')
                
                # Clear cache
                if 'c_events_cache' in st.session_state:
                    del st.session_state['c_events_cache']
                if 'c_events_cache_time' in st.session_state:
                    del st.session_state['c_events_cache_time']
                
                st.info("📅 Sesión de calendario cerrada")
                st.rerun()

        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("🔐 Cerrar Sesión App", key="btn_logout_sidebar", width="stretch"):
            # IMPORTANTE: NO borrar COD_VAL (token Google OAuth)
            # El token debe persistir en Google Sheets para evitar re-autenticación
            # Solo se borra si el usuario hace clic en "Cambiar Cuenta / Salir"

            # Clear Local Session State ONLY (UI Reset)
            keys_to_clear = ['connected_email', 'connected_email_input', 'google_token',
                             'calendar_service', 'tasks_service', 'sheets_service',
                             'authenticated', 'user_data_full', 'license_key',
                             'c_events_cache', 'c_events_cache_time',
                             'last_flashcards', 'temp_cornell_result', 'processing_note_id',
                             'ai_result_cache']
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
    elif selection == "Chat": chat_view.render_chat_view() # NEW ROUTE
    elif selection == "Create": view_create()
    elif selection == "Planner": view_planner()
    elif selection == "Inbox": view_inbox()
    elif selection == "Notes": notes_view.view_notes_page()
    elif selection == "Optimize": view_optimize()
    elif selection == "Insights": view_time_insights()
    elif selection == "Account": view_account()

    # --- FOOTER ---
    st.markdown("---")
    with st.container():
        col_f1, col_f2, col_f3, col_f4 = st.columns([3, 1, 5, 1])

        with col_f2:
            # LOGO EMPRESA
            try:
                logo_p = "logo_agent.png"
                if os.path.exists(logo_p):
                    try:
                        st.image(logo_p, width=150)
                    except Exception:
                        st.markdown("🤖 **Asistente IA**")
                else:
                    st.caption("Agent AI")
            except: pass

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
    
    # Restore license_key from username if missing but authenticated (e.g. after reload)
    if st.session_state.get('authenticated') and not st.session_state.get('license_key') and st.session_state.get('username'):
        st.session_state.license_key = st.session_state.username

    if not st.session_state.authenticated:
        render_login_page()
    else:
        main_app()
