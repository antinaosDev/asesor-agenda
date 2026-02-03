
import streamlit as st
import datetime
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
                    new_id = notes_manager.create_note(note_content, source="quick_widget")
                    if new_id:
                        st.success("Nota guardada")
                        # Clear input hack if needed, or just let user see confirmation
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
    st.title("🧠 Captura y Procesamiento (Brain Dump)")
    # Ensure Sheets Service is Ready
    google_services.get_sheets_service()
    
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
    
    # 1. Main Input Area
    # 1. Main Input Area & Mode Selector
    with st.container(border=True):
        st.subheader("📝 Nueva Captura")
        
        # Mode Selector
        mode = st.radio("Modo de Procesamiento:", 
            ["⚡ Estándar (Eventos/Tareas)", "📚 Cornell (Estudio)", "🧠 Flashcards (Memorizar)"],
            horizontal=True,
            label_visibility="collapsed"
        )
        
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
                            st.markdown("### 📚 Notas Cornell Generadas")
                            st.markdown(result, unsafe_allow_html=True)
                            # Save option?
                            if st.button("💾 Guardar en Notas"):
                                # Save as HTML note? Or Markdown? 
                                # For now, just a toast as 'saving rich text' is complex in simple text notes
                                notes_manager.create_note(f"CORNELL: {new_note[:50]}...", source="cornell", tags="study")
                                st.success("Guardado en referencias")
                        elif "Flashcards" in mode:
                            result = ai_core.process_study_notes(new_note, mode="flashcards")
                            st.session_state.last_flashcards = result # Save for rendering
                            st.rerun() # Rerun to show flashcards below or in a clean state
                            
                else:
                    st.warning("El campo está vacío")
                    
        with c2:
            if st.button("💾 Solo Guardar", use_container_width=True):
                if new_note.strip():
                    if notes_manager.create_note(new_note, source="main_view"):
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
    
    active_notes = notes_manager.get_active_notes()
    
    import modules.ui_interactive as ui
    import time
    
    if not active_notes:
        st.info("No hay notas pendientes. ¡Estás al día!")
    else:
        # Prepare props for V2 Component
        items = []
        for note in active_notes:
            items.append({
                "id": note['id'],
                "title": f"📌 {note['created_at'][:10]}",
                "content": note['content'],
                "actions": [
                    {"id": "process", "label": "Procesar", "icon": "✨", "type": "primary", "autoHide": True},
                    {"id": "archive", "label": "Archivar", "icon": "🗑️", "type": "danger", "autoHide": True}
                ]
            })
            
        # Render Component
        action = ui.action_card_list(items, key="inbox_list")
        
        # Handle Events
    # Init Session State for processing
    if 'processing_note_id' not in st.session_state:
        st.session_state.processing_note_id = None
    if 'ai_result_cache' not in st.session_state:
        st.session_state.ai_result_cache = None

    # Handle Component Events
    if action:
        note_id = action['itemId']
        act_id = action['actionId']
        
        target_note = next((n for n in active_notes if n['id'] == note_id), None)
        
        if target_note:
            if act_id == "process":
                st.session_state.processing_note_id = note_id
                # Clear previous cache if different note
                if st.session_state.get('last_processed_note') != note_id:
                     st.session_state.ai_result_cache = None
                     st.session_state.last_processed_note = note_id
                     
            elif act_id == "archive":
                notes_manager.archive_note(note_id)
                time.sleep(0.5)
                st.rerun()

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

def _handle_ai_result(result, original_text):
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
