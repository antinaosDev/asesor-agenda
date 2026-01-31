import streamlit as st
import modules.ai_core as ai
import modules.google_services as gs
import datetime
import time

def render_chat_view():
    st.markdown("""
    <h1 style='color: #0dd7f2; font-size: 2rem;'>💬 Asistente Ejecutivo IA</h1>
    <p style='color: #9cb6ba;'>Tu copiloto inteligente. Habla o escribe para gestionar tu agenda.</p>
    """, unsafe_allow_html=True)

    # 1. Initialize Chat History
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "assistant", "content": "Hola. Soy tu asistente ejecutivo. ¿En qué puedo ayudarte hoy? Puedes pedirme que revise tu agenda, redacte correos o cree tareas."}
        ]

    # 2. Display Chat History
    for msg in st.session_state.chat_history:
        avatar = "🤖" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    # 3. Input Handling (Audio & Text)
    
    # Audio Input (Experimental)
    audio_value = st.audio_input("🎤 Hablar con el asistente")
    
    # Text Input
    prompt_text = st.chat_input("Escribe tu instrucción aquí...")

    user_input = None
    is_audio = False

    # PRIORITY 1: Text Input (Ephemeral, always new if present)
    if prompt_text:
        user_input = prompt_text

    # PRIORITY 2: Audio Input (Persistent, need hash check)
    # Only process audio if no text was entered to avoid conflict
    elif audio_value:
        audio_bytes = audio_value.getvalue()
        audio_hash = hash(audio_bytes)
        
        # Check against session state to see if this is a NEW recording
        if "last_audio_hash" not in st.session_state or st.session_state.last_audio_hash != audio_hash:
            st.session_state.last_audio_hash = audio_hash
            with st.spinner("🎧 Escuchando y transcribiendo..."):
                user_input = ai.transcribe_audio_groq(audio_value)
                is_audio = True

    # 4. Process Logic
    if user_input:
        # Add User Message
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)

        # Generate Assistant Response
        with st.chat_message("assistant", avatar="🤖"):
            response_placeholder = st.empty()
            full_response = ""
            
            # Prepare Context (Lite Version for Token Efficiency)
            context = _get_lite_context()
            
            # Reduce History for Token Efficiency (Last 6 messages)
            recent_history = st.session_state.chat_history[-6:]
            
            # Stream Response
            try:
                stream = ai.chat_stream(user_input, recent_history, context)
                for chunk in stream:
                    if chunk:
                        full_response += chunk
                        response_placeholder.markdown(full_response + "▌")
                response_placeholder.markdown(full_response)
            except Exception as e:
                st.error(f"Error del asistente: {e}")
                full_response = "Lo siento, tuve un problema procesando eso. ¿Podrías intentarlo de nuevo?"
                response_placeholder.markdown(full_response)

        # Add Assistant Message to History
        st.session_state.chat_history.append({"role": "assistant", "content": full_response})

        # Logic to trigger actions based on response (Function Calling)
        # 1. Check for JSON Blocks (Robust Multi-Action Strategy)
        # Strategy: Find all potential JSON blocks (code blocked or raw)
        # and iterate to execute them.
        
        regex_strategies = [
            r'```json\s*([\[\{].*?[\]\}])\s*```', # Code block with { or [
            r'([\[\{][\s\n]*"action".*?[\]\}])\s*$' # Raw JSON at end
        ]
        
        found_matches = []
        for reg in regex_strategies:
             found_matches = list(re.finditer(reg, full_response, re.DOTALL))
             if found_matches: break
        
        clean_text = full_response
        action_executed = False
        
        if found_matches:
            for match in found_matches:
                try:
                    json_str = match.group(1)
                    # Cleaning
                    json_str = re.sub(r'//.*', '', json_str)
                    
                    # Parse (Handle List or Single Object)
                    data = json.loads(json_str)
                    actions_list = data if isinstance(data, list) else [data]
                    
                    for action_data in actions_list:
                        action_type = action_data.get('action')
                        params = action_data.get('params', {})
                        result_msg = ""
                        
                        if action_type == 'create_event':
                            # ... existing create_event logic ...
                            with st.spinner(f"🗓️ Creando: {params.get('summary', 'Evento')}"):
                                s_time = params.get('start_time', '')
                                e_time = params.get('end_time', '')
                                if not s_time or not e_time:
                                    st.error("⚠️ Faltan fecha/hora.")
                                else:
                                    svc = gs.get_calendar_service()
                                    if svc:
                                        ok, msg = gs.add_event_to_calendar(svc, params)
                                        if ok: 
                                            result_msg = f"✅ Evento creado: {params.get('summary')}"
                                            action_executed = True
                                        else: st.error(f"Error: {msg}")

                        elif action_type == 'delete_event':
                            with st.spinner("🗑️ Eliminando evento..."):
                                 evt_id = params.get('event_id')
                                 if evt_id:
                                     svc = gs.get_calendar_service()
                                     if svc:
                                         if gs.delete_event(svc, evt_id):
                                             result_msg = "🗑️ Evento eliminado correctamente."
                                             action_executed = True
                                         else: st.error("No se pudo eliminar el evento.")
                                 else: st.error("ID de evento no proporcionado.")

                        elif action_type == 'create_task':
                             # ... existing create_task logic ...
                             with st.spinner(f"✅ Creando tarea: {params.get('title', 'Tarea')}"):
                                svc = gs.get_tasks_service()
                                if svc:
                                    t_lists = gs.get_task_lists(svc)
                                    if t_lists:
                                        t_list_id = t_lists[0]['id']
                                        res = gs.add_task_to_google(svc, t_list_id, params.get('title'), due_date=params.get('due_date'))
                                        if res:
                                            result_msg = f"✅ Tarea creada: {params.get('title')}"
                                            action_executed = True
                                        else: st.error("Error al crear tarea.")

                        elif action_type == 'delete_task':
                            with st.spinner("🗑️ Eliminando tarea..."):
                                 tsk_id = params.get('task_id')
                                 # We ideally need the list_id too, but we can try finding it or default
                                 # For simplicity, let's look in the first list or search
                                 svc = gs.get_tasks_service()
                                 if svc and tsk_id:
                                     t_lists = gs.get_task_lists(svc)
                                     deleted = False
                                     for tl in t_lists: # Brute force search delete
                                         if gs.delete_task_google(svc, tl['id'], tsk_id):
                                             deleted = True
                                             break
                                     if deleted:
                                          result_msg = "🗑️ Tarea eliminada."
                                          action_executed = True
                                     else: st.error("No se pudo eliminar (o no encontrada).")

                        elif action_type == 'draft_email':
                             with st.spinner("📧 Dejando borrador..."):
                                svc = gs.get_gmail_credentials()
                                if svc:
                                    from googleapiclient.discovery import build
                                    svc_gmail = build('gmail', 'v1', credentials=svc, cache_discovery=False)
                                    draft = gs.create_draft(svc_gmail, 'me', params.get('body'), params.get('recipient'), params.get('subject'))
                                    if draft:
                                        result_msg = f"✅ Borrador: {params.get('subject')}"
                                        action_executed = True

                        if action_executed and result_msg:
                            st.toast(result_msg, icon="🚀")

                    # Remove matched JSON from display text
                    clean_text = clean_text.replace(match.group(0), "").strip()

                except Exception as e:
                    st.error(f"Error procesando lote de acciones: {e}")

        # 2. TTS Generation (Jarvis Mode)
        # Use clean_text (without JSON)
        if clean_text:
            try:
                import modules.tts_service as tts
                # Voice: AlvaroNeural (Spanish Male Executive)
                audio_bytes = tts.text_to_speech(clean_text, voice='es-ES-AlvaroNeural')
                if audio_bytes:
                    st.audio(audio_bytes, format='audio/mp3', autoplay=True)
            except Exception as e:
                # Silent fail for TTS
                print(f"TTS Error: {e}")

        # Force Rerun if action changed state significantly (optional)
        if action_executed:
            time.sleep(1)
            st.rerun()

        # Rerun to update if it was an audio interaction to clear the widget state visually if needed
        # (Streamlit handles audio widget state tricky, usually requires user to clear it)

def _get_lite_context():
    """Recopila contexto esencial y ligero para el prompt del sistema."""
    import modules.google_services as gs
    
    # Date
    now = datetime.datetime.now()
    ctx = f"Fecha: {now.strftime('%Y-%m-%d %H:%M')}\n"
    
    # --- CONTEXTO REAL TIME ---
    # 1. EVENTS (Today + Tomorrow)
    ctx += "=== AGENDA REAL ===\n"
    try:
        # Try Cache First
        events = st.session_state.get('c_events_cache', [])
        
        # If cache empty, force fetch (Critical for Chat accuracy)
        if not events:
            svc_cal = gs.get_calendar_service()
            if svc_cal:
                t_min = now.isoformat() + 'Z'
                t_max = (now + datetime.timedelta(days=2)).isoformat() + 'Z' # 48 hours window
                events_result = svc_cal.events().list(
                    calendarId='primary', timeMin=t_min, timeMax=t_max, 
                    singleEvents=True, orderBy='startTime'
                ).execute()
                events = events_result.get('items', [])
        
        if events:
            count = 0
            for e in events:
                start = e.get('start', {}).get('dateTime', e.get('start', {}).get('date'))
                summary = e.get('summary', 'Sin Título')
                
                # Format friendly
                try: 
                    dt_s = datetime.datetime.fromisoformat(start)
                    start_str = dt_s.strftime("%d/%m %H:%M")
                except: start_str = start
                
                ctx += f"- [{start_str}] {summary} (ID: {e['id']})\n"
                count += 1
                if count >= 8: break # Cap at 8 events
        else:
            ctx += "(Sin eventos próximos)\n"
    except Exception as e:
        ctx += f"(Error leyendo agenda: {e})\n"

    # 2. TASKS (Pending)
    ctx += "\n=== TAREAS PENDIENTES ===\n"
    try:
        svc_tasks = gs.get_tasks_service()
        if svc_tasks:
            tasks = gs.get_existing_tasks_simple(svc_tasks)
            # Filter only needing action? API already returns 'needsAction' primarily if showCompleted=False
            if tasks:
                for t in tasks[:5]: # Top 5
                   ctx += f"- {t.get('title', 'Tarea')} (ID: {t.get('id')})\n"
            else:
                ctx += "(Sin tareas pendientes)\n"
    except:
        ctx += "(No se pudo leer Tasks)\n"

    # 3. EMAILS (Unread Context)
    ctx += "\n=== CORREOS NO LEÍDOS (Recientes) ===\n"
    try:
        svc_gmail = gs.get_gmail_credentials() # Returns creds, need service
        if svc_gmail:
            from googleapiclient.discovery import build
            curr_svc = build('gmail', 'v1', credentials=svc_gmail, cache_discovery=False)
            
            # Re-use fetch logic but keep it simple/fast
            # Query: unread
            results = curr_svc.users().messages().list(userId='me', q="is:unread -category:promotions -category:social", maxResults=5).execute()
            msgs = results.get('messages', [])
            
            if msgs:
                for m in msgs:
                    # Quick fetch snippet
                    full = curr_svc.users().messages().get(userId='me', id=m['id'], format='minimal').execute()
                    headers = full.get('payload', {}).get('headers', [])
                    subj = next((h['value'] for h in headers if h['name'] == 'Subject'), '(Sin Asunto)')
                    sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Desconocido')
                    ctx += f"- De: {sender} | Asunto: {subj}\n"
            else:
               ctx += "(Bandeja al día)\n"
    except:
        ctx += "(Error leyendo correos)\n"

    return ctx
