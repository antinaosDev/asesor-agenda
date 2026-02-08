
import streamlit as st
import datetime
import json
import modules.notes_manager as notes_manager
import modules.ai_core as ai_core
import modules.google_services as google_services

def render_brain_dump_widget():
    """Renders the simplified Brain Dump widget for the sidebar or dashboard."""
    with st.container(border=True):
        st.markdown("### 🧠 Brain Dump")
        # Ensure Sheets Service is Ready
        google_services.get_sheets_service()

        note_content = st.text_area("Captura rapida:", height=100, key="quick_note_input", placeholder="Ej: Llamar a proveedor mañana a las 3pm...")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("💾 Guardar", use_container_width=True):
                if note_content.strip():
                    user_id = st.session_state.get('license_key', '')
                    new_id = notes_manager.create_note(note_content, source="quick_widget", user_id=user_id)
                    if new_id:
                        st.success("Nota guardada")
                        # Clear input hack if needed, or just let user see confirmation
                    else:
                        st.error("Error al guardar")
                else:
                    st.warning("Escribe algo primero")
                    
        with col2:
            if st.button("✨ Procesar", use_container_width=True):
                 if note_content.strip():
                    with st.spinner("Analizando con IA..."):
                        result = ai_core.process_brain_dump(note_content)
                        _handle_ai_result(result, note_content)
                 else:
                    st.warning("Escribe algo primero")

def view_notes_page():
    """Main Notes/Inbox Management Page."""
    import json
    st.title("🧠 Captura y Procesamiento (Brain Dump)")
    # Ensure Sheets Service is Ready
    google_services.get_sheets_service()
    
    # --- DEBUG SCOPES (Temporary) ---
    with st.expander("🔍 Debug: Ver Scopes Actuales", expanded=False):
        if 'google_token' in st.session_state:
            creds = st.session_state.google_token
            st.write(f"Válido: {creds.valid}")
            st.write("Scopes Cargados:")
            st.json(creds.scopes)
            if st.button("Forzar Borrado Token Session"):
                del st.session_state.google_token
                st.rerun()
        else:
            st.warning("No hay token en memoria.")
    
    with st.expander("ℹ️ ¿Qué es el Brain Dump?", expanded=False):
        st.markdown("""
        **Brain Dump** (Vaciado Mental) es una técnica de productividad para **sacar todo lo que tienes en la cabeza** y guardarlo en un sistema confiable.
        
        **¿Cómo usar esta herramienta?**
        1.  **Captura Rápida:** Escribe CUALQUIER cosa que se te ocurra en el cuadro de abajo.
            *   *"Reunión de coordinación mañana a las 5pm"* (Evento)
            *   *"Comprar insumos de oficina"* (Tarea)
            *   *"Idea para el proyecto X: usar IA"* (Nota)
        2.  **Procesar con IA:** La Inteligencia Artificial analizará tu texto y te sugerirá la mejor acción:
            *   📅 **Crear Evento:** Si detecta fecha y hora.
            *   ☑️ **Crear Tarea:** Si es algo que debes hacer.
            *   📌 **Guardar Nota:** Si es información o una idea.
        
        ¡Úsalo para liberar tu mente y asegurarte de que nada se te olvide!
        """)
    
    # 1. Main Input Area & Mode Selector
    with st.container(border=True):
        st.subheader("📝 Nueva Captura")
        
        # Mode Selector
        mode = st.radio("Modo de Procesamiento:", 
            ["⚡ Estándar (Eventos/Tareas)", "📚 Cornell (Estudio)", "🧠 Flashcards (Memorizar)", "📋 Actas de Reunión", "🏗️ Proyectos", "🎙️ Comandos"],
            horizontal=True,
            label_visibility="collapsed"
        )
        
        # --- GENERADOR DE ACTAS MODE (RENAMED) ---
        if "Actas" in mode:
            st.info("Generador de Actas: Transforma notas o grabaciones en vivo en documentos formales.")
            acta_title = st.text_input("Título de la Reunión (Opcional)", placeholder="Ej: Comité de Calidad - Agosto")
            
            tab_text, tab_audio = st.tabs(["📝 Texto / Pegar Acta", "🎙️ Grabación en Vivo (Beta)"])
            
            with tab_text:
                acta_content = st.text_area("Contenido / Transcripción:", height=300, key="acta_text_input", placeholder="Pega aquí los apuntes brutos o la transcripción...")
                if st.button("📄 Generar Acta en Docs", use_container_width=True, key="btn_gen_acta_txt"):
                    if acta_content.strip():
                        with st.spinner("🤖 Redactando Acta y Generando Doc..."):
                            # 1. AI Analysis
                            struct_data = ai_core.generate_meeting_minutes_ai(acta_content)
                            if "error" in struct_data:
                                st.error(f"Error AI: {struct_data['error']}")
                            else:
                                # 2. Doc Generation
                                final_title = acta_title if acta_title else f"Acta_{datetime.datetime.now().strftime('%Y%m%d')}"
                                doc_url, error_msg = google_services.create_meeting_minutes_doc(final_title, struct_data)
                                
                                if doc_url:
                                    st.success("✅ Acta creada exitosamente!")
                                    st.markdown(f"### [📂 Abrir Documento en Google Docs]({doc_url})")
                                    st.balloons()
                                else:
                                    st.error(f"Error creando el documento: {error_msg}")
                                    if "403" in str(error_msg) or "permission" in str(error_msg).lower():
                                        st.warning("⚠️ Parece que faltan permisos para Google Docs.")
                                        if st.button("🔄 Actualizar Permisos (Re-conectar)", key="fix_perms_txt"):
                                            st.session_state.logout_google = True
                                            if 'user_data_full' in st.session_state and 'cod_val' in st.session_state.user_data_full:
                                                del st.session_state.user_data_full['cod_val']
                                            st.rerun()
                    else:
                        st.warning("El contenido está vacío.")

            with tab_audio:
                st.warning("⚠️ Nota: La grabación se guarda en la memoria del navegador. Si cierras la pestaña, se pierde. Para reuniones de >3 horas, asegúrate de tener suficiente RAM.")
                
                # NEW: LIVE RECORDING INPUT
                audio_value = st.audio_input("Grabar reunión ahora")
                
                if audio_value is not None:
                    # Show player for review
                    st.audio(audio_value)
                    
                    if st.button("🎙️ Transcribir y Generar Acta", use_container_width=True, key="btn_gen_acta_audio"):
                         with st.spinner("🎧 Transcribiendo audio (esto puede demorar)..."):
                             # 1. Transcribe (works with file-like object from audio_input)
                             transcription = ai_core.transcribe_audio_groq(audio_value)
                             
                             if transcription and "Error" not in transcription:
                                 st.success("✅ Transcripción completada.")
                                 with st.expander("Ver Transcripción"):
                                     st.write(transcription[:1000] + "...")
                                     
                                 with st.spinner("🤖 Redactando Acta y Generando Doc..."):
                                     # 2. AI Structuring
                                     struct_data = ai_core.generate_meeting_minutes_ai(transcription)
                                     
                                     # 3. Doc Generation
                                     final_title = acta_title if acta_title else f"Acta_Audio_{datetime.datetime.now().strftime('%Y%m%d')}"
                                     doc_url, error_msg = google_services.create_meeting_minutes_doc(final_title, struct_data)
                                     
                                     if doc_url:
                                         st.success("✅ Acta creada exitosamente!")
                                         st.markdown(f"### [📂 Abrir Documento en Google Docs]({doc_url})")
                                         st.balloons()
                                     else:
                                         st.error(f"Error creando documento: {error_msg}")
                                         if "403" in str(error_msg) or "permission" in str(error_msg).lower():
                                            st.warning("⚠️ Parece que faltan permisos para Google Docs.")
                                            if st.button("🔄 Actualizar Permisos (Re-conectar)", key="fix_perms_audio"):
                                                st.session_state.logout_google = True
                                                if 'user_data_full' in st.session_state and 'cod_val' in st.session_state.user_data_full:
                                                    del st.session_state.user_data_full['cod_val']
                                                st.rerun()
                             else:
                                 st.error(f"Falló la transcripción: {transcription}")

        # --- PROJECT BREAKDOWN MODE ---
        elif "Proyectos" in mode:
            st.info("Desglose de Proyectos: Convierte una idea compleja en una lista de tareas ejecutables.")
            project_input = st.text_area("Descripción del Proyecto:", height=100, placeholder="Ej: Organizar la fiesta de fin de año para 50 personas...")
            
            if st.button("🚀 Generar Plan de Trabajo", use_container_width=True):
                if project_input.strip():
                    with st.spinner("🧠 Analizando y desglosando proyecto..."):
                        plan = ai_core.generate_project_breakdown(project_input)
                        if "error" in plan:
                            st.error(f"Error AI: {plan['error']}")
                        else:
                            st.session_state.temp_project_plan = plan
                            st.rerun()
            
            # Display Generated Plan
            if 'temp_project_plan' in st.session_state:
                plan = st.session_state.temp_project_plan
                st.subheader(f"Plan: {plan.get('project_name')}")
                
                # Editable Dataframe or List? Let's use clean expanders for V1
                tasks_to_create = plan.get('tasks', [])
                for t in tasks_to_create:
                    st.markdown(f"- **{t['due']}**: {t['title']}")
                
                if st.button("✅ Crear todas las tareas en Google Tasks", type="primary"):
                    progress_bar = st.progress(0)
                    created_count = 0
                    
                    for i, task in enumerate(tasks_to_create):
                        # Create Task
                        google_services.create_task(task['title'], due=task['due'])
                        created_count += 1
                        progress_bar.progress((i + 1) / len(tasks_to_create))
                        
                    st.success(f"¡{created_count} tareas creadas exitosamente!")
                    del st.session_state.temp_project_plan
                    time.sleep(1)
                    st.rerun()



        # --- VOICE ANALYST MODE ---
        elif "Comandos" in mode:
            st.info("Analista de Voz: Habla instrucciones complejas y la IA las ejecutará (Eventos, Tareas, Emails).")
            
            voice_command_audio = st.audio_input("Grabar Instrucción", key="voice_analyst_input")
            
            if voice_command_audio:
                st.audio(voice_command_audio)
                
                if st.button("🧠 Analizar y Ejecutar", use_container_width=True, type="primary"):
                    with st.spinner("🎧 Escuchando y Pensando..."):
                        # 1. Transcribe
                        text_cmd = ai_core.transcribe_audio_groq(voice_command_audio)
                        if not text_cmd or "Error" in text_cmd:
                            st.error(f"Error transcripción: {text_cmd}")
                        else:
                            st.info(f"🗣️ Dijiste: '{text_cmd}'")
                            
                            # 2. Analyze
                            analysis = ai_core.analyze_voice_command(text_cmd)
                            if "error" in analysis:
                                st.error(f"Error Análisis: {analysis['error']}")
                            else:
                                actions = analysis.get('actions', [])
                                if not actions:
                                    st.warning("No se detectaron acciones ejecutables.")
                                else:
                                    st.subheader(f"✅ {len(actions)} Acciones Detectadas:")
                                    
                                    # Preview
                                    for act in actions:
                                        icon = "📅" if "event" in act['action'] else "✅" if "task" in act['action'] else "📧"
                                        st.markdown(f"{icon} **{act['action']}**: {act['params']}")
                                    
                                    # Execute Loop (Automatic or require second confirmation? Let's do automatic for "Analizar y Ejecutar")
                                    # User asked for "Execute All" button in plan, but here we can streamline.
                                    # Let's add a secondary confirmation just to be safe/impressive.
                                    st.session_state.temp_voice_actions = actions
                                    st.rerun()
            
            # Execution State
            if 'temp_voice_actions' in st.session_state:
                st.divider()
                st.write("¿Confirmas la ejecución de estas acciones?")
                c_yes, c_no = st.columns(2)
                with c_yes:
                    if st.button("⚡ Ejecutar Todo", type="primary", use_container_width=True):
                        results_log = []
                        progress = st.progress(0)
                        
                        for i, action in enumerate(st.session_state.temp_voice_actions):
                            ok, msg = google_services.execute_voice_action(action)
                            icon = "✅" if ok else "❌"
                            results_log.append(f"{icon} {msg}")
                            progress.progress((i + 1) / len(st.session_state.temp_voice_actions))
                        
                        for log in results_log:
                            st.write(log)
                            
                        st.success("Proceso finalizado.")
                        del st.session_state.temp_voice_actions
                        
                with c_no:
                    if st.button("Cancelar", use_container_width=True):
                        del st.session_state.temp_voice_actions
                        st.rerun()

        # --- OTHER MODES (Standard, Cornell, Flashcards) ---
        else: 
            new_note = st.text_area("¿Qué tienes en mente?", height=150, key="main_note_input", placeholder="Escribe o pega tu texto aquí...")
            
            c1, c2 = st.columns([1, 4])
            with c1:
                if st.button("✨ Procesar", type="primary", use_container_width=True):
                    if new_note.strip():
                        with st.spinner("Analizando..."):
                            if "Estándar" in mode:
                                result = ai_core.process_brain_dump(new_note)
                                _handle_ai_result(result, new_note)
                            elif "Cornell" in mode:
                                result = ai_core.process_study_notes(new_note, mode="cornell")
                                st.session_state.temp_cornell_result = result
                                st.rerun()
                            elif "Flashcards" in mode:
                                result = ai_core.process_study_notes(new_note, mode="flashcards")
                                st.session_state.last_flashcards = result 
                                st.rerun() 
                                
                    else:
                        st.warning("El campo está vacío")
            
            # Save Button (Standard Mode Only)
            with c2:
                if st.button("💾 Solo Guardar", use_container_width=True):
                    if new_note.strip():
                        user_id = st.session_state.get('license_key', '')
                        if notes_manager.create_note(new_note, source="main_view", user_id=user_id):
                            st.success("Nota guardada en Inbox")
                            st.rerun()

    # Flashcard Renderer (if in session)
    if 'last_flashcards' in st.session_state and st.session_state.last_flashcards:
        st.divider()
        st.subheader("🧠 Tarjetas de Memoria Generadas")
        cards = json.loads(st.session_state.last_flashcards) if isinstance(st.session_state.last_flashcards, str) else st.session_state.last_flashcards
        
        if cards:
            cols = st.columns(3)
            for i, card in enumerate(cards):
                with cols[i % 3]:
                    with st.container(border=True):
                        st.markdown(f"**P:** {card.get('q')}")
                        with st.expander("Ver Respuesta"):
                            st.info(card.get('a'))
            
            if st.button("🗑️ Limpiar Tarjetas"):
                del st.session_state.last_flashcards
                st.rerun()

    st.divider()
    
    # 2. Processor Inbox (Unprocessed Notes)
    st.subheader("📥 Inbox de Notas")
    
    user_id = st.session_state.get('license_key', '')
    active_notes = notes_manager.get_active_notes(user_id=user_id)
    
    import time
    
    if not active_notes:
        st.info("No hay notas pendientes. ¡Estás al día!")
    else:
        # Standard Streamlit UI Loop
        for note in active_notes:
            with st.container(border=True):
                # Header: Title/Date
                c_title, c_date = st.columns([0.7, 0.3])
                with c_title:
                    st.markdown(f"**📌 Nota**")
                with c_date:
                    st.caption(f"{note['created_at'][:16]}")
                
                # Content
                st.markdown(note['content'], unsafe_allow_html=True)
                
                # Actions
                c_proc, c_arch, c_del = st.columns([1, 1, 1])
                
                with c_proc:
                    if st.button("✨ Procesar", key=f"proc_{note['id']}", type="primary", use_container_width=True):
                         st.session_state.processing_note_id = note['id']
                         # Clear previous cache if different note
                         if st.session_state.get('last_processed_note') != note['id']:
                              st.session_state.ai_result_cache = None
                              st.session_state.last_processed_note = note['id']
                         st.rerun()
                         
                with c_arch:
                    if st.button("📂 Archivar", key=f"arch_{note['id']}", use_container_width=True):
                        notes_manager.archive_note(note['id'])
                        st.toast("Nota archivada")
                        time.sleep(0.5)
                        st.rerun()

                with c_del:
                    if st.button("🗑️ Eliminar", key=f"del_{note['id']}", type="primary", help="Borrar permanentemente", use_container_width=True):
                        notes_manager.delete_note(note['id'])
                        st.toast("Nota eliminada")
                        time.sleep(0.5)
                        st.rerun()

                # --- NOTE ACTIONS EXTRAS (TAGS) ---
                with st.expander("🏷️ Etiquetas y Vínculos", expanded=False):
                    c_tag, c_btn = st.columns([0.7, 0.3])
                    current_tags = note.get('tags', '')
                    
                    with c_tag:
                        new_tags = st.text_input("Etiquetas (sep. por comas)", value=current_tags, key=f"tags_{note['id']}")
                    with c_btn:
                        st.write("") # Spacer
                        st.write("") 
                        if st.button("Guardar Tags", key=f"save_tags_{note['id']}"):
                            if new_tags != current_tags:
                                notes_manager.update_note(note['id'], {'tags': new_tags})
                                st.toast("Etiquetas actualizadas")
                                time.sleep(0.5)
                                st.rerun()

    # 3. Archived Notes Section
    st.divider()
    with st.expander("🗄️ Historial / Archivadas", expanded=False):
        user_id = st.session_state.get('license_key', '')
        archived_notes = notes_manager.get_archived_notes(user_id=user_id)
        if not archived_notes:
            st.info("No hay notas archivadas.")
        else:
             for anote in archived_notes:
                with st.container(border=True):
                     st.caption(f"📅 {anote['created_at'][:10]} | 🏷️ {anote.get('tags', 'Sin etiquetas')}")
                     st.markdown(anote['content'], unsafe_allow_html=True)
                     
                     c_rest, c_del_perm = st.columns([1, 1])
                     with c_rest:
                         if st.button("♻️ Recuperar", key=f"rest_{anote['id']}"):
                             notes_manager.update_note(anote['id'], {'status': 'active'})
                             st.toast("Nota recuperada a Inbox")
                             time.sleep(0.5)
                             st.rerun()
                     with c_del_perm:
                          if st.button("❌ Borrar", key=f"perm_del_{anote['id']}", type="primary"):
                             notes_manager.delete_note(anote['id'])
                             st.toast("Eliminada permanentemente")
                             time.sleep(0.5)
                             st.rerun()

    # Init Session State for processing
    if 'processing_note_id' not in st.session_state:
        st.session_state.processing_note_id = None
    if 'ai_result_cache' not in st.session_state:
        st.session_state.ai_result_cache = None

    # Handle Component Events (Legacy/Fallback removed)

    # --- Render Processing UI (Persistent) ---
    if st.session_state.processing_note_id:
        # Find note content again (it might be archived now? Assuming active)
        p_note_id = st.session_state.processing_note_id
        p_note = next((n for n in active_notes if n['id'] == p_note_id), None)
        
        if p_note:
            with st.container(border=True):
                c_head, c_close = st.columns([0.9, 0.1])
                with c_head:
                    st.markdown(f"### 🤖 Procesando: *{p_note['content'][:40]}...*")
                with c_close:
                    if st.button("✖️", key="close_proc"):
                        st.session_state.processing_note_id = None
                        st.session_state.ai_result_cache = None
                        st.rerun()

                # Calculate or Retrieve AI Result
                result = st.session_state.ai_result_cache
                if not result:
                    with st.spinner("Analizando con IA..."):
                        result = ai_core.process_brain_dump(p_note['content'])
                        st.session_state.ai_result_cache = result
                
                # Handle Result
                success = _handle_ai_result(result, p_note['content'])
                
                # If Action Successful, Archive and Reset
                if success:
                    notes_manager.archive_note(p_note_id)
                    st.success("Nota procesada y archivada.")
                    time.sleep(1)
                    st.session_state.processing_note_id = None
                    st.session_state.ai_result_cache = None
                    st.rerun()
        else:
            # Note likely archived or gone
            st.session_state.processing_note_id = None
            st.rerun()

def _handle_ai_result(result, original_text, user_id=None):
    """Handles the JSON action from AI. Returns True if action completed successfully."""
    # Defensive programming
    if isinstance(result, list):
        result = result[0] if result else {}

    action = result.get('action')
    
    if action == 'create_event':
        st.info("📅 La IA sugiere crear un evento:")
        with st.expander("Ver detalles JSON", expanded=False):
            st.json(result)
        
        col_card = st.columns([1])[0]
        with col_card:
            st.markdown(f"""
            **Evento:** {result.get('summary')}  
            **Inicio:** {result.get('start_time')}  
            **Fin:** {result.get('end_time')}
            """)
            
        if st.button("✅ Confirmar y Crear Evento", type="primary", use_container_width=True):
            service = st.session_state.get('calendar_service') or google_services.get_calendar_service()
            
            event_data = {
                "summary": result.get('summary'),
                "description": result.get('description', original_text),
                "start_time": result.get('start_time'),
                "end_time": result.get('end_time'),
                "colorId": result.get('colorId', '11')
            }
            return google_services.add_event_to_calendar(service, event_data)

    elif action == 'create_task':
        st.info("☑️ La IA sugiere crear una tarea:")
        st.write(f"**{result.get('title')}**")
        st.caption(f"Vencimiento: {result.get('due_date', 'Sin fecha')}")
        
        if st.button("✅ Confirmar y Crear Tarea", type="primary", use_container_width=True):
            service = st.session_state.get('tasks_service') or google_services.get_tasks_service()
            task_lists = google_services.get_task_lists(service)
            if task_lists:
                list_id = task_lists[0]['id']
                return google_services.add_task_to_google(
                    service, list_id, 
                    title=result.get('title'),
                    notes=result.get('notes', original_text),
                    due_date=result.get('due_date')
                )
            else:
                st.error("No se encontraron listas de tareas.")
                return False

    elif action == 'keep_note':
        st.info("📌 Se guardará como nota de referencia.")
        if st.button("✅ Archivar Nota", type="primary"):
            return True
        
    else:
        st.warning(f"Acción no reconocida o ambigua: {action}")
        if st.button("🗑️ Archivar de todas formas"):
            return True

    return False
