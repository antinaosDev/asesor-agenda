import streamlit as st
import os
import datetime
import json
import logging
from dotenv import load_dotenv
import pandas as pd
import time
import plotly.express as px

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
    page_title="AI Event Manager",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for "Modern/Tech" Look ---
st.markdown("""
<style>
    /* Dark Theme Base is assumed from Streamlit config, adding specific overrides */
     .stApp {
        background-color: #0e1117;
        color: #ffffff;
    }
    
    /* Custom Headers */
    h1, h2, h3 {
        color: #00e5ff !important;
        font-family: 'Inter', sans-serif;
    }
    
    /* Cards/Containers */
    .stTextArea, .stTextInput {
        border-radius: 10px;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(45deg, #2196F3, #00BCD4);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 15px rgba(33, 150, 243, 0.4);
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #1a1e24;
        border-radius: 8px;
    }
    
    /* Success/Error messages */
    .stSuccess, .stInfo {
        background-color: rgba(0, 229, 255, 0.1);
        border: 1px solid #00e5ff;
        color: #00e5ff;
    }
</style>
""", unsafe_allow_html=True)
def authenticated_main():

    st.sidebar.title("⚙️ Configuraciones")
    
    with st.sidebar.expander("🔌 Conexión", expanded=False):
        st.code("mensajeria-rev@sistemas-473713.iam.gserviceaccount.com", language="text")
        st.write("Permiso requerido: 'Hacer cambios en eventos'")

    # Auto-fill with connected email if available
    default_cal = st.session_state.get('connected_email', '')
    calendar_id = st.sidebar.text_input("ID Calendario (Tu Email)", value=default_cal, placeholder="tu.correo@gmail.com")
    
    # --- PROACTIVE SUMMARY (UX ENHANCEMENT) ---
    if 'first_load_summary' not in st.session_state:
        st.session_state.first_load_summary = False

    if calendar_id and not st.session_state.first_load_summary:
         with st.spinner("🤖 Analizando tu día..."):
             # Simple "Morning Briefing" context
             try:
                 # Check if we have service
                 svc = get_calendar_service()
                 if svc:
                      # Get today's events for quick context (cached if possible)
                      now = datetime.datetime.now()
                      t_min = now.replace(hour=0, minute=0, second=0).isoformat() + 'Z'
                      t_max = now.replace(hour=23, minute=59, second=59).isoformat() + 'Z'
                      
                      day_events = svc.events().list(
                          calendarId=calendar_id, timeMin=t_min, timeMax=t_max, singleEvents=True, orderBy='startTime'
                      ).execute().get('items', [])
                      
                      count = len(day_events)
                      msg = f"Hola! Hoy tienes **{count} eventos**."
                      if count == 0: msg += " Día libre para avanzar en pendientes."
                      elif count > 4: msg += " Será un día movido, ¡toma agua!"
                      
                      st.toast(msg, icon="👋")
                 st.session_state.first_load_summary = True
             except:
                 pass
    
    if 'current_user_sa_creds' in st.session_state:
        sa_email = st.session_state.current_user_sa_creds.get('client_email', 'Desconocido')
        st.sidebar.caption(f"✅ Bot Activo: `{sa_email}`")
        st.sidebar.info(f"👉 Asegúrate de compartir tu calendario con: **{sa_email}** (Permiso: Cambios en eventos)")

    if st.sidebar.button("🛠️ Check Permisos"):
        # [Check logic remains same]
        if not calendar_id:
            st.sidebar.warning("❌ Ingresa ID.")
        else:
            service = get_calendar_service()
            if service:
                try:
                    s = service.events().list(calendarId=calendar_id.strip(), maxResults=1).execute(num_retries=3)
                    st.sidebar.success("Conexión OK")
                except Exception as e:
                    if "404" in str(e):
                        err_msg = "❌ Calendario no encontrado (404)."
                        if 'current_user_sa_creds' in st.session_state:
                             bot_mail = st.session_state.current_user_sa_creds.get('client_email', 'Bot Desconocido')
                             err_msg += f"\n\n👉 SOLUCIÓN: Comparte tu calendario con: **{bot_mail}**"
                        else:
                             err_msg += "\n\nVerifica que hayas compartido tu calendario con el email del Service Account (service_account.json)."
                        st.sidebar.error(err_msg)
                    else:
                        st.sidebar.error(f"Error: {e}")

    # --- TASK LISTS ---
    st.sidebar.divider()
    st.sidebar.subheader("📂 Listas de Tareas")
    
    tasks_service = get_tasks_service()
    if tasks_service:
        # Load lists
        if 'available_tasklists' not in st.session_state:
            st.session_state.available_tasklists = get_task_lists(tasks_service)
        
        lists = st.session_state.available_tasklists
        if lists:
            list_names = [l['title'] for l in lists]
            # Default to index 0 (My Tasks)
            selected_idx = 0
            
            # Restore selection if exists
            if 'active_tasklist' in st.session_state:
                try:
                    current_id = st.session_state.active_tasklist['id']
                    for i, l in enumerate(lists):
                        if l['id'] == current_id:
                            selected_idx = i
                            break
                except: pass
            
            selected_name = st.sidebar.selectbox("Seleccionar Lista:", list_names, index=selected_idx, key="list_selector")
            
            # Store full list object in session
            st.session_state.active_tasklist = next((l for l in lists if l['title'] == selected_name), lists[0])
            st.sidebar.caption(f"ID: {st.session_state.active_tasklist['id']}")
            
            # Create New List
            with st.sidebar.expander("➕ Nueva Lista"):
                new_list_name = st.text_input("Nombre de Lista")
                if st.button("Crear Lista"):
                    if new_list_name:
                        nl = create_task_list(tasks_service, new_list_name)
                        if nl:
                            st.sidebar.success("Creada!")
                            st.session_state.available_tasklists = get_task_lists(tasks_service) # Refresh
                            st.rerun()
    else:
        st.sidebar.warning("Autentícate para ver tus listas.")

    st.title("🤖 AI Executive Assistant")
    st.markdown("Tu asistente personal inteligente para gestión de tiempo.")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["✨ Crear Eventos", "👔 Optimizar Agenda", "📊 Métricas y Herramientas", "📧 Análisis de Correos", "✅ Planificador de Tareas"])
    
    # TAB 1: CREAR
    with tab1:
        st.markdown("Escribe lo que necesites agendar. Yo me encargo de categorizarlo, ponerle íconos y color.")
        with st.form("input_form"):
            text_input = st.text_area("✍️ Escribe aquí...", height=150, placeholder="Reunión de equipos a las X hrs...")
            submitted = st.form_submit_button("Analizar")
        
        if submitted and text_input:
            with st.spinner("Procesando..."):
                events = parse_events_ai(text_input)
                st.session_state.pending_events = events
        
        if 'pending_events' in st.session_state and st.session_state.pending_events:
            st.subheader("Propuesta de Agenda:")
            cols = st.columns(3)
            for i, event in enumerate(st.session_state.pending_events):
                with cols[i % 3]:
                    color_id = event.get('colorId', '1')
                    color_name = COLOR_MAP.get(color_id, "Estándar")
                    with st.container(border=True):
                        st.markdown(f"**{event.get('summary')}**")
                        # Handle potential space instead of T in display too
                        st_display = event.get('start_time').replace('T', ' ')
                        st.caption(f"📅 {st_display}")
                        st.text(event.get('description'))
                        st.caption(f"🎨 {color_name}")
            
            if st.button("✅ Aprobar y Guardar"):
                if not calendar_id: st.error("Falta Email.")
                else:
                    service = get_calendar_service()
                    if service:
                        count = 0
                        errors = []
                        for ev in st.session_state.pending_events:
                            ok, msg = add_event_to_calendar(service, ev, calendar_id)
                            if ok: 
                                count += 1
                            else:
                                errors.append(f"Fallo en '{ev.get('summary')}': {msg}")
                        
                        if count > 0:
                            st.success(f"¡{count} eventos agendados!")
                        
                        if errors:
                            for e_msg in errors:
                                if "writer access" in str(e_msg) or "403" in str(e_msg):
                                    sa_email = "Desconocido"
                                    if 'current_user_sa_creds' in st.session_state:
                                        sa_email = st.session_state.current_user_sa_creds.get('client_email', 'Desconocido')
                                    
                                    st.error("⛔ **Error de Permisos (403):** El Bot no tiene permiso para escribir en tu calendario.")
                                    st.info(f"""
                                    **Cómo solucionarlo:**
                                    1. 📅 Ve a tu Google Calendar ({calendar_id}).
                                    2. ⚙️ Configuración -> Compartir con personas específicas.
                                    3. ➕ Añade este email:
                                    """)
                                    st.code(sa_email, language="text")
                                    st.info("**Importante:** Selecciona el permiso **'Hacer cambios en eventos'**.")
                                else:
                                    st.error(e_msg)
                                
                        if count == len(st.session_state.pending_events):
                             del st.session_state.pending_events

            if st.button("🗑️ Descartar"):
                del st.session_state.pending_events
                st.rerun()

    # TAB 2: OPTIMIZAR
    with tab2:
        st.info("Herramienta de Auditoría y Mejora Continua. Analiza periodos pasados o futuros.")
        
        col_opt_1, col_opt_2 = st.columns(2)
        with col_opt_1:
            today = datetime.date.today()
            start_date = st.date_input("Fecha Inicio", today)
        with col_opt_2:
            end_date = st.date_input("Fecha Fin", today + datetime.timedelta(days=30))
            
        if st.button("📥 Importar Período Seleccionado"):
            if not calendar_id: st.error("Ingresa tu email a la izquierda.")
            else:
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
                    except Exception as e:
                        st.error(f"Error cargando calendario: {e}")
        
        if 'opt_events' in st.session_state:
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
                        if not calendar_id: st.error("Falta Email.")
                        else:
                            service = get_calendar_service()
                            bar = st.progress(0)
                            done = 0
                            plan = st.session_state.opt_plan
                            for i, ev in enumerate(events):
                                if ev['id'] in plan:
                                    p = plan[ev['id']]
                                    optimize_event(service, calendar_id, ev['id'], p['new_summary'], p['colorId'])
                                    done += 1
                                bar.progress((i+1)/len(events))
                            st.balloons()
                            st.success(f"¡Agenda Transformada! {done} eventos optimizados.")

    # TAB 3: MÉTRICAS Y HERRAMIENTAS
    with tab3:
        st.subheader("📊 Panel de Control y Limpieza")
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            m_start = st.date_input("Desde", datetime.date.today(), key="metrics_start")
        with col_m2:
            m_end = st.date_input("Hasta", datetime.date.today() + datetime.timedelta(days=30), key="metrics_end")
            
        if st.button("🔍 Cargar Datos del Período"):
            if not calendar_id: st.error("Falta Email.")
            else:
                service = get_calendar_service()
                if service:
                    try:
                        t_min = datetime.datetime.combine(m_start, datetime.time.min).isoformat() + 'Z'
                        t_max = datetime.datetime.combine(m_end, datetime.time.max).isoformat() + 'Z'
                        res = service.events().list(
                            calendarId=calendar_id, timeMin=t_min, timeMax=t_max, 
                            singleEvents=True, orderBy='startTime', maxResults=2000,
                            fields="items(id,summary,start,end,colorId)",
                            showDeleted=False
                        ).execute(num_retries=3)
                        st.session_state.metrics_events = res.get('items', [])
                        st.success(f"Cargados {len(st.session_state.metrics_events)} eventos.")
                    except Exception as e:
                        st.error(f"Error: {e}")

        if 'metrics_events' in st.session_state and st.session_state.metrics_events:
            events_df = st.session_state.metrics_events
            
            # --- CALCULATE METRICS ---
            st.divider()
            
            # Prepare data
            data = []
            for e in events_df:
                start = e['start'].get('dateTime') or e['start'].get('date')
                end = e['end'].get('dateTime') or e['end'].get('date')
                # Simple parsing assuming ISO
                try:
                    # Robust ISO Parsing & Timezone Stripping for Plotly compatibility
                    s_str = start if 'T' in start else f"{start}T00:00:00"
                    e_str = end if 'T' in end else f"{end}T00:00:00"

                    s_dt = datetime.datetime.fromisoformat(s_str.replace('Z', '+00:00'))
                    e_dt = datetime.datetime.fromisoformat(e_str.replace('Z', '+00:00'))
                    
                    # Store duration before stripping TZ
                    duration = (e_dt - s_dt).total_seconds() / 3600 

                    # Make Naive for Plotly (removes timezone info to avoid mixing errors)
                    if s_dt.tzinfo: s_dt = s_dt.replace(tzinfo=None)
                    if e_dt.tzinfo: e_dt = e_dt.replace(tzinfo=None)
                except:
                    s_dt = datetime.datetime.now()
                    e_dt = s_dt + datetime.timedelta(hours=1)
                    duration = 1 # Default
                
                color = e.get('colorId', '1')
                cat = COLOR_MAP.get(color, f"Color {color}")
                data.append({
                    "Categoría": cat, 
                    "Horas": round(duration, 2), 
                    "Evento": e.get('summary', 'Sin Título'),
                    "Inicio": s_dt,
                    "Fin": e_dt,
                    "Fecha": start[:10],
                    "ID": e['id'],
                    "Color": color
                })
            
            df = pd.DataFrame(data)
            
            if not df.empty:
                st.subheader("📈 Visualización Interactiva")
                
                c1, c2 = st.columns(2)
                with c1:
                    # Pie Chart of Counts
                    fig_pie = px.pie(df, names='Categoría', title='Distribución por Cantidad de Eventos', hole=0.4)
                    st.plotly_chart(fig_pie, use_container_width=True)
                
                with c2:
                    # Bar Chart of Hours
                    fig_bar = px.bar(df, x='Categoría', y='Horas', color='Categoría', title='Carga de Trabajo (Horas Totales)')
                    st.plotly_chart(fig_bar, use_container_width=True)

                # Gantt Chart (Timeline)
                st.markdown("### 🗓️ Vista de Cronograma (Gantt)")
                fig_timeline = px.timeline(
                    df, 
                    x_start="Inicio", 
                    x_end="Fin", 
                    y="Categoría", 
                    color="Categoría", 
                    hover_name="Evento",
                    hover_data=["Horas"],
                    title="Línea de Tiempo de Eventos"
                )
                fig_timeline.update_yaxes(categoryorder="total ascending") # Order by busiest category
                fig_timeline.update_layout(xaxis_title="Tiempo", yaxis_title="Categoría")
                st.plotly_chart(fig_timeline, use_container_width=True)
                
                total_hours = df["Horas"].sum()
                st.metric(label=" Total de Horas Agendadas", value=f"{total_hours:.1f} hrs")
            
            # --- DELETE TOOLS ---
            st.divider()
            st.subheader("🧹 Gestión y Limpieza Inteligente")
            
            col_del_intro, _ = st.columns([2,1])
            col_del_intro.info("Selecciona los eventos que deseas eliminar permanentemente de tu calendario.")

            # Create selection dataframe
            if "selection_df" not in st.session_state or len(st.session_state.selection_df) != len(df):
                # Initialize with False
                df["Seleccionar"] = False
                st.session_state.selection_df = df[["Seleccionar", "Fecha", "Evento", "Categoría", "ID"]].copy()

            # Data Editor with Key to maintain state
            edited_df = st.data_editor(
                st.session_state.selection_df,
                hide_index=True,
                column_config={"ID": None}, # Hide ID column
                key="editor_delete",
                use_container_width=True
            )
            
            # Filter selected rows
            to_delete = edited_df[edited_df["Seleccionar"] == True]
            
            if not to_delete.empty:
                st.warning(f"⚠️ Has seleccionado {len(to_delete)} eventos para borrar.")
                
                if st.button("🗑️ CONFIRMAR BORRADO", type="primary"):
                    if not calendar_id: st.error("Falta ID Calendario.")
                    else:
                        service = get_calendar_service()
                        progress_bar = st.progress(0)
                        success_count = 0
                        
                        for i, row in enumerate(to_delete.itertuples()):
                            if delete_event(service, calendar_id, row.ID):
                                success_count += 1
                            progress_bar.progress((i + 1) / len(to_delete))
                        
                        st.success(f"✅ Se eliminaron correctamente {success_count} eventos.")
                        # Clear cache to force reload
                        del st.session_state.metrics_events
                        del st.session_state.selection_df
                        st.rerun()
            else:
                st.button("🗑️ Borrar (Selecciona items primero)", disabled=True)

    # TAB 4: GMAIL ANALYZER
    with tab4:
        st.subheader("📧 Análisis de Buzón Inteligente")
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
                                 # (Remainder of logic usually follows here, assuming analyze_emails_ai returns events to be handled)
                                 # Since the original code ended here, we just ensure state is cleared.
                     except Exception as e:
                         st.error(f"Error procesando correos: {e}")
                     finally:
                         # Reset trigger so it doesn't loop forever
                         st.session_state.trigger_mail_analysis = False
                         # Optional: rerun to clear the "Running" state visuals if needed, but usually not required
                 else:
                     # If get_gmail_credentials returned None (e.g. user cancelled), we should probably stop trying
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
                                 service_cal = get_calendar_service()
                                 if service_cal:
                                      res, msg = add_event_to_calendar(service_cal, calendar_id, ev)
                                      if res: st.success(f"¡Agendado!")
                                      else: st.error(f"Error: {msg}")
             elif 'fetched_emails' in st.session_state:
                  st.info(f"📨 Se leyeron {len(st.session_state.fetched_emails)} correos. Esperando análisis...")

    # TAB 5: TASK PLANNER
    with tab5:
        st.subheader("✅ Planificador Semanal Inteligente")
        st.markdown("Dime qué tienes que hacer y yo organizo tu semana de Lunes a Viernes.")
        
        mode = st.radio("Modo de Planificación", ["Semana Estándar (Manual + Calendario)", "Desglosar Proyecto (Eventos Largos)"], horizontal=True)
        
        calendar_context_str = ""
        long_events = []
        
        # Common Calendar Fetch (Optimized)
        if 'c_events_cache' not in st.session_state:
             st.session_state.c_events_cache = []
             
        # Always fetch if cache empty or requested
        if not st.session_state.c_events_cache:
            if not calendar_id:
                 st.warning("⚠️ Configura tu ID de Calendario.")
            else:
                service = get_calendar_service()
                if service:
                    try:
                        today = datetime.date.today()
                        t_min = datetime.datetime(today.year, 1, 1).isoformat() + 'Z'
                        t_max = datetime.datetime(today.year, 12, 31, 23, 59, 59).isoformat() + 'Z'
                        
                        st.session_state.c_events_cache = service.events().list(
                            calendarId=calendar_id, timeMin=t_min, timeMax=t_max, 
                            singleEvents=True, orderBy='startTime', maxResults=2000,
                            fields="items(summary,start,end,description)" 
                        ).execute(num_retries=3).get('items', [])
                    except Exception as e:
                        st.error(f"Error calendario: {e}")

        # Process Events for Context or Selection
        if st.session_state.c_events_cache:
            pass
        
        if mode == "Semana Estándar (Manual + Calendario)":
            c1, c2 = st.columns([2, 1])
            with c1:
                use_calendar = st.checkbox("📥 Considerar eventos (Contexto)", value=True)
            with c2:
                # Select week
                target_date = st.date_input("Planificar semana del:", value=datetime.date.today())
                # Find Monday - Sunday of that week
                start_of_target_week = target_date - datetime.timedelta(days=target_date.weekday())
                end_of_target_week = start_of_target_week + datetime.timedelta(days=6)
            
            if use_calendar and st.session_state.c_events_cache:
                 # Filter for relevant context (Target Week)
                 ctx_lines = []
                 for e in st.session_state.c_events_cache:
                     try:
                         start_str = e['start'].get('dateTime', e['start'].get('date'))
                         start_dt = datetime.datetime.fromisoformat(start_str.replace('Z', '+00:00')).date()
                         # Include events for that week
                         if start_of_target_week <= start_dt <= end_of_target_week:
                             summ = e.get('summary', 'Evento')
                             ctx_lines.append(f"- {start_str}: {summ}")
                     except: pass
                 calendar_context_str = "\n".join(ctx_lines)

            with st.form("task_input_form"):
                task_input = st.text_area("Lista de Tareas / Metas:", height=150, placeholder="- Terminar reporte Q1...")
                btn_plan = st.form_submit_button("📅 Generar Plan Semanal")
                
            if btn_plan:
                with st.spinner(f"Diseñando semana del {start_of_target_week}..."):
                    final_input = task_input if task_input else "Solo eventos calendario."
                    plan = generate_work_plan_ai(final_input, calendar_context_str, start_date_str=str(start_of_target_week))
                    st.session_state.work_plan = plan
                    st.session_state.plan_type = 'weekly'
                    st.session_state.current_week_start = start_of_target_week # Store for display logic

        else: # PROJECT MODE
            st.info("ℹ️ Busca eventos largos (>3 días) para desglosarlos en tareas diarias.")
            
            # Filter Long Events
            long_events_opts = []
            for e in st.session_state.c_events_cache:
                try:
                    start_str = e['start'].get('dateTime', e['start'].get('date'))
                    end_str = e['end'].get('dateTime', e['end'].get('date'))
                    
                    s_dt = datetime.datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                    e_dt = datetime.datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                    
                    duration = (e_dt - s_dt).days
                    if duration >= 3:
                        summ = e.get('summary', 'Sin Título')
                        long_events_opts.append(f"{summ} | {start_str[:10]} -> {end_str[:10]} ({duration}d)")
                except: pass
            
            if not long_events_opts:
                st.warning("No encontré eventos largos (>3 días) en tu calendario de este año.")
            else:
                selected_proj = st.selectbox("Selecciona Proyecto/Evento:", long_events_opts)
                
                if st.button("🔨 Desglosar Proyecto"):
                    sel_summ = selected_proj.split(" | ")[0]
                    sel_start = selected_proj.split(" | ")[1].split(" -> ")[0]
                    
                    target_event = next((e for e in st.session_state.c_events_cache if e.get('summary') == sel_summ and (e['start'].get('dateTime', e['start'].get('date'))).startswith(sel_start)), None)
                    
                    if target_event:
                        with st.spinner("Generando Roadmap..."):
                            s_date = target_event['start'].get('dateTime', target_event['start'].get('date'))[:10]
                            e_date = target_event['end'].get('dateTime', target_event['end'].get('date'))[:10]
                            desc = target_event.get('description', '')
                            
                            project_tasks = generate_project_breakdown_ai(sel_summ, desc, s_date, e_date)
                            st.session_state.project_plan = project_tasks 
                            st.session_state.plan_type = 'project'
                        
        # DISPLAY RESULTS     
        if 'plan_type' in st.session_state:
            st.divider()
            
            if st.session_state.plan_type == 'weekly' and 'work_plan' in st.session_state:
                # Helper to calculate dates for the TARGET week
                # If we stored it, use it. Else default to today's week.
                start_of_week = st.session_state.get('current_week_start', datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday()))
                # Correction: if user didn't pick date (old session), use today.
                # Actually we should have set it. But default fallback safe.
                if 'current_week_start' not in st.session_state:
                     t = datetime.date.today()
                     start_of_week = t - datetime.timedelta(days=t.weekday())
                     if t.weekday() > 4: start_of_week += datetime.timedelta(days=7)
                    
                days_map = {
                    "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4,
                    "Lunes": 0, "Martes": 1, "Miércoles": 2, "Jueves": 3, "Viernes": 4
                }
                
                cols = st.columns(5)
                
                # To store tasks for syncing
                tasks_to_sync = []
                
                for day_name, tasks in st.session_state.work_plan.items():
                    if day_name not in days_map: continue
                    
                    day_idx = days_map[day_name]
                    day_date = start_of_week + datetime.timedelta(days=day_idx)
                    
                    with cols[day_idx]:
                        st.markdown(f"**{day_name}**")
                        st.caption(f"{day_date.strftime('%d/%m')}")
                        
                        for t in tasks:
                            st.info(t)
                            tasks_to_sync.append({
                                "title": t,
                                "notes": f"Planificado para {day_name}",
                                "due": day_date.isoformat()
                            })
                
                st.divider()
                if st.button("🚀 Sincronizar con Google Tasks"):
                    tasks_service = get_tasks_service()
                    if tasks_service:
                        # Get destination list
                        dest_list_id = '@default'
                        if 'active_tasklist' in st.session_state:
                            dest_list_id = st.session_state.active_tasklist['id']
                        
                        # Deduplication
                        existing_sigs = get_existing_tasks_simple(tasks_service, tasklist=dest_list_id)
                        
                        count = 0
                        skipped = 0
                        
                        progress_bar = st.progress(0)
                        total_items = sum(len(tasks) for tasks in st.session_state.work_plan.values())
                        current_idx = 0
                        
                        for day, items in st.session_state.work_plan.items():
                            target_date_str = None
                            try:
                                days_map = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, 
                                            "lunes": 0, "martes": 1, "miércoles": 2, "jueves": 3, "viernes": 4}
                                d_idx = days_map.get(day.lower().strip(), -1)
                                
                                if d_idx != -1:
                                    today = datetime.date.today()
                                    days_ahead = (d_idx - today.weekday() + 7) % 7
                                    if days_ahead == 0: days_ahead = 7 
                                    target_date = today + datetime.timedelta(days=(d_idx - today.weekday())) 
                                    target_date_str = target_date.isoformat()
                            except: pass

                            for item in items:
                                current_idx += 1
                                progress_bar.progress(min(current_idx / max(1, total_items), 1.0))
                                
                                if "[Event]" in item or "[Meeting]" in item:
                                    continue 
                                
                                clean_title = item.strip()
                                is_dup = False
                                for e_title, e_date in existing_sigs:
                                    if e_title.lower() == clean_title.lower():
                                        if target_date_str and e_date == target_date_str:
                                            is_dup = True; break
                                        if not target_date_str:
                                            is_dup = True; break
                                
                                if is_dup:
                                    skipped += 1; continue

                                if add_task_to_google(tasks_service, clean_title, f"Planificado para {day}", due_date_str=target_date_str, tasklist=dest_list_id):
                                    count += 1
                                    
                        st.success(f"¡Sincronizado! {count} tareas creadas en '{st.session_state.get('active_tasklist', {}).get('title', 'Default')}'. ({skipped} duplicadas).")
                    else:
                        st.error("No se pudo conectar con Google Tasks.")
            
            elif st.session_state.plan_type == 'project' and 'project_plan' in st.session_state:
                st.subheader("Roadmap del Proyecto")
                p_tasks = st.session_state.project_plan
                
                if not p_tasks:
                    st.error("No se pudieron generar tareas.")
                else:
                    df = pd.DataFrame(p_tasks)
                    st.dataframe(df, use_container_width=True)
                    
                    if st.button("🚀 Sincronizar Roadmap a Google Tasks"):
                        tasks_service = get_tasks_service()
                        if tasks_service:
                             # Get destination list
                             dest_list_id = '@default'
                             if 'active_tasklist' in st.session_state:
                                 dest_list_id = st.session_state.active_tasklist['id']

                             existing_sigs = get_existing_tasks_simple(tasks_service, tasklist=dest_list_id)
                             count = 0
                             skipped = 0
                             prog = st.progress(0)
                             
                             # 1. Prepare Parent Task Content
                             p_parts = selected_proj.split(" | ")
                             p_title = p_parts[0]
                             p_date_str = p_parts[1].split(" (")[0] # "YYYY-MM-DD -> YYYY-MM-DD"
                             p_end = p_date_str.split(" -> ")[1].strip()
                             
                             project_title = f"[PROYECTO] {p_title}"
                             
                             checklist_text = "Desglose generado por IA:\n\n"
                             for task in p_tasks:
                                 d_txt = task.get('date', 'Sin fecha')
                                 checklist_text += f"[ ] {task.get('title')} ({d_txt})\n"
                             
                             parent_id = add_task_to_google(tasks_service, project_title, checklist_text, due_date_str=p_end, tasklist=dest_list_id)
                             
                             if not parent_id:
                                 st.error("Error creando la Tarea Principal. Se cancela la sincronización.")
                             else:
                                 st.toast(f"Proyecto creado. Insertando subtareas...")
                                 
                                 success_subs = 0
                                 fail_subs = 0
                                 
                                 for i, t in enumerate(p_tasks):
                                     prog.progress((i+1)/len(p_tasks))
                                     title = t.get('title', 'Tarea sin nombre')
                                     date = t.get('date')
                                     notes = t.get('notes', '')
                                     
                                     sid = add_task_to_google(tasks_service, title, notes, due_date_str=date, parent=parent_id, tasklist=dest_list_id)
                                     if sid: success_subs += 1
                                     else: fail_subs += 1
                                         
                                 if fail_subs > 0:
                                     st.warning(f"Se crearon {success_subs} subtareas, fallaron {fail_subs}.")
                                 else:
                                     st.success(f"¡Éxito! Proyecto '{project_title}' creado en lista '{st.session_state.get('active_tasklist', {}).get('title', 'Default')}'.")
                                     st.caption("Nota: Busca la tarea en Google Tasks y toca la flecha '↪' o 'Subtareas' para ver el detalle.")

            # --- TASK MANAGER SECTION ---
            st.divider()
            st.subheader("📋 Gestionar Tareas Existentes")
            
            if 'tasks_service' not in st.session_state:
                 get_tasks_service()
            
            if 'tasks_service' in st.session_state and st.session_state.tasks_service:
                try:
                    dest_list_id = '@default'
                    list_title = "Mis Tareas"
                    if 'active_tasklist' in st.session_state:
                         dest_list_id = st.session_state.active_tasklist['id']
                         list_title = st.session_state.active_tasklist['title']

                    st.markdown(f"**Viendo lista:** `{list_title}`")
                    
                    tasks_result = st.session_state.tasks_service.tasks().list(
                        tasklist=dest_list_id, showCompleted=False, maxResults=50
                    ).execute(num_retries=3)
                    
                    my_tasks = tasks_result.get('items', [])
                    
                    if not my_tasks:
                        st.info(f"No hay tareas pendientes en '{list_title}'.")
                    else:
                        for t in my_tasks:
                            c1, c2, c3 = st.columns([5, 1, 1])
                            with c1:
                                new_val = st.text_input(f"Editar '{t['title']}'", value=t['title'], key=f"txt_{t['id']}", label_visibility="collapsed")
                            with c2:
                                if new_val != t['title']:
                                    if st.button("💾", key=f"save_{t['id']}", help="Guardar cambios"):
                                        if update_task_google(st.session_state.tasks_service, t['id'], new_val, tasklist=dest_list_id):
                                            st.toast(f"Tarea actualizada!")
                                            st.rerun()
                            with c3:
                                if st.button("🗑️", key=f"del_{t['id']}", help="Eliminar tarea"):
                                    if delete_task_google(st.session_state.tasks_service, t['id'], tasklist=dest_list_id):
                                        st.toast("Tarea eliminada")
                                        st.rerun()
                                        
                except Exception as e:
                    st.error(f"Error cargando tareas: {e}")


def main():
    """Logic to handle Login vs Main App."""
    
    # 1. Initialize session state
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    # 2. Show Login or App
    if not st.session_state.authenticated:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.title("🔒 AI Event Manager Premium")
            st.markdown("### Organiza tu vida profesional con Inteligencia Artificial.")
            st.info("Para acceder a todas las funcionalidades ejecutivas, por favor ingresa tu Licencia.")
            
            with st.form("login_form"):
                col_u, col_p = st.columns(2)
                username_input = col_u.text_input("👤 Usuario", placeholder="adm_user")
                password_input = col_p.text_input("🔑 Contraseña", type="password")
                
                submitted = st.form_submit_button("Iniciar Sesión")
                
                if submitted:
                    is_valid, user_data = auth.login_user(username_input, password_input)

                    if is_valid:
                        st.session_state.license_key = username_input # Usamos username como llave de sesión
                        st.session_state.user_data_full = user_data # Store full data for role checks
                        st.session_state.authenticated = True
                        
                        # --- CARGAR CREDENCIALES DEL USUARIO (OAuth Clients) ---
                        if 'credenciales_auth_user' in user_data:
                            try:
                                raw_json = user_data['credenciales_auth_user']
                                if isinstance(raw_json, str):
                                    if '""' in raw_json: raw_json = raw_json.replace('""', '"')
                                    raw_json = raw_json.strip()
                                    if raw_json.startswith('"') and raw_json.endswith('"'): raw_json = raw_json[1:-1]
                                import json
                                json.loads(raw_json)
                                st.session_state.custom_google_config = raw_json
                            except Exception as e:
                                st.warning(f"⚠️ Credenciales de usuario inválidas en BD ({e}).")
                        
                        # --- CARGAR SERVICE ACCOUNT (Backend Bot) ---
                        # PRIORIDAD 0 para acceso a calendarios
                        if 'clave_cuenta_servicio_admin' in user_data:
                             try:
                                 sa_raw = user_data['clave_cuenta_servicio_admin']
                                 if isinstance(sa_raw, str) and sa_raw.strip():
                                     # Limpieza standard CSV/Excel
                                     if '""' in sa_raw: sa_raw = sa_raw.replace('""', '"')
                                     sa_raw = sa_raw.strip()
                                     if sa_raw.startswith('"') and sa_raw.endswith('"'): sa_raw = sa_raw[1:-1]
                                     
                                     sa_json = json.loads(sa_raw)
                                     st.session_state.current_user_sa_creds = sa_json
                             except Exception as e:
                                 st.warning(f"⚠️ Error cargando Service Account de hoja: {e}")
                        # ----------------------------------------

                        # --- CARGAR CREDENCIALES NOTIFICACIONES ---
                        if 'notification_api_client' in user_data and 'notification_api_secret' in user_data:
                             st.session_state.notif_creds = {
                                 "client_id": user_data['notification_api_client'],
                                 "client_secret": user_data['notification_api_secret'],
                                 "to_email": user_data.get('email_send', '') 
                             }
                        # -------------------------------------------

                        # st.checkbox("Recordar Sesión", value=True) -> REMOVED PER USER REQUEST
                        # auth.save_license(username_input, password_input) 
                            
                        st.success("✅ Licencia Validada. Cargando...")
                        st.rerun()
                    else:
                        st.error("❌ Licencia Inválida o Inactiva.")
            

            st.divider()
            with st.expander("💳 ¿Cómo obtener una licencia?"):
                st.markdown(auth.get_billing_info())

            
    else:
        # Sidebar Logout
        with st.sidebar:
            st.divider()
            
            # --- ADMIN PANEL ---
            # Check if user is admin (Rol = ADMIN or user=admin)
            current_user = st.session_state.get('license_key', '')
            user_data = st.session_state.get('user_data_full', {}) # Need to ensure we store this on login
            
            # Backdoor or DB Role
            u_role = str(user_data.get('rol', '')).upper().strip()
            is_admin = (current_user == 'admin') or (u_role in ['ADMIN', 'ADMINISTRADOR'])
            
            if is_admin:
                st.subheader("🛡️ Panel Admin")
                
                # 1. Configurar Límites
                new_limit = st.number_input("Límite Global Correos IA", min_value=5, max_value=500, value=st.session_state.get('admin_max_emails', 50))
                if new_limit != st.session_state.get('admin_max_emails', 50):
                    st.session_state.admin_max_emails = new_limit
                    st.toast(f"Límite actualizado a {new_limit}")
                
                st.divider()
                
                # 2. Simulador de Roles
                st.caption("🎭 Simulador de Roles")
                all_users = auth.get_all_users()
                if all_users:
                    user_opts = [f"{u.get('user')} ({u.get('rol', 'N/A')})" for u in all_users]
                    selected_sim = st.selectbox("Impersonar a:", ["-- Seleccionar --"] + user_opts)
                    
                    if st.button("Simular Sesión"):
                        if selected_sim != "-- Seleccionar --":
                            target_user = selected_sim.split(" (")[0]
                            # Find user data
                            target_data = next((u for u in all_users if u.get('user') == target_user), {})
                            if target_data:
                                # Switch Session
                                st.session_state.license_key = target_user
                                st.session_state.user_data_full = target_data # Update context
                                # Reload credentials logic (simplified)
                                if 'notification_api_client' in target_data:
                                     st.session_state.notif_creds = {
                                         "client_id": target_data['notification_api_client'],
                                         "client_secret": target_data['notification_api_secret'],
                                         "to_email": target_data.get('email_send', '') 
                                     }
                                st.success(f"Ahora eres: {target_user}")
                                st.rerun()
                else:
                    st.warning("No se pudieron cargar usuarios.")
            
            st.divider()
        if 'notif_creds' in st.session_state:
            st.divider()
            if st.button("📧 Probar Notificación"):
                creds = st.session_state.notif_creds
                to_email = creds['to_email'] if creds['to_email'] else "test@example.com"
                
                if notif.send_verification_email(creds['client_id'], creds['client_secret'], to_email):
                    st.success(f"Notificación enviada a {to_email}")
                else:
                    st.error("Error enviando. Revisa consola.")
        
        # Run the Real App
        authenticated_main()

if __name__ == "__main__":
    main()

