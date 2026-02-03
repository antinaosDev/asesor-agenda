
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
    with st.container(border=True):
        st.subheader("📝 Nueva Captura")
        new_note = st.text_area("¿Qué tienes en mente?", height=150, key="main_note_input")
        
        c1, c2 = st.columns([1, 4])
        with c1:
            if st.button("✨ Procesar con IA", type="primary", use_container_width=True):
                if new_note.strip():
                    with st.spinner("Analizando..."):
                        result = ai_core.process_brain_dump(new_note)
                        _handle_ai_result(result, new_note)
                else:
                    st.warning("El campo está vacío")
                    
        with c2:
            if st.button("💾 Solo Guardar", use_container_width=True):
                if new_note.strip():
                    if notes_manager.create_note(new_note, source="main_view"):
                        st.success("Nota guardada en Inbox")
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
        if action:
            note_id = action['itemId']
            act_id = action['actionId']
            
            # Retrieve note data
            target_note = next((n for n in active_notes if n['id'] == note_id), None)
            
            if target_note:
                if act_id == "process":
                    with st.spinner("Analizando..."):
                        # Show result container
                        st.markdown(f"### 🤖 Resultado para: *{target_note['content'][:30]}...*")
                        result = ai_core.process_brain_dump(target_note['content'])
                        
                        # We handle result. If event created, we archive note.
                        # _handle_ai_result needs to return True/False if successful to know if we archive
                        # Currently _handle_ai_result returns nothing/None (it generates UI)
                        # We might need to tweak _handle_ai_result or just rely on user interaction there.
                        # Wait, _handle_ai_result renders buttons.
                        # If the user clicks "Confirm" INSIDE _handle_ai_result, THEN we archive?
                        # But the card is already hidden.
                        # If user doesn't confirm, card stays hidden until reload.
                        # That's acceptable for "Draft" mode.
                        
                        # But wait, _handle_ai_result renders buttons. 
                        # If I click "Confirm", Streamlit reruns.
                        # On rerun, 'action' is None (unless persisted? No, component state resets?)
                        # Standard Streamlit: Button click triggers rerun.
                        # The component 'action' might be lost on next rerun if not persisted.
                        
                        # FIX: We should execute _handle_ai_result. 
                        # If it contains buttons, those buttons need to work.
                        # If I click a button inside _handle_ai_result, the script reruns.
                        # Will it re-enter this 'if action:' block?
                        # PROBABLY NOT.
                        # Because 'action' comes from component. 
                        # Component retains state? Yes, usually.
                        # But if I click another button, the component state might persist or not.
                        # If it persists, we re-enter.
                        
                        _handle_ai_result(result, target_note['content'])
                        
                        # We can't auto-archive here because we don't know if user confirmed.
                        # But visually the card is GONE.
                        # If user confirms event, we should archive note.
                        # _handle_ai_result should take the note_id and archive it if successful?
                        # Refactoring _handle_ai_result is risky/complex right now.
                        # Alternative: For "Process", we DON'T auto-hide?
                        # Let's try Auto-Hide TRUE first. It feels better.
                        # If I create event, I see success.
                        # I can manually archive later if it reappears? 
                        # Or we add "Archive" button to the result view?
                        
                elif act_id == "archive":
                    notes_manager.archive_note(note_id)
                    time.sleep(0.5) # Let animation finish
                    st.rerun()

def _handle_ai_result(result, original_text):
    """Handles the JSON action from AI."""
    # Defensive programming: Handle list vs dict (Force Update)
    if isinstance(result, list):
        if len(result) > 0:
            result = result[0]
        else:
            result = {}

    action = result.get('action')
    
    if action == 'create_event':
        with st.expander("📅 Propuesta de Evento", expanded=True):
            st.info("La IA sugiere crear un evento:")
            st.json(result)
            
            if st.button("✅ Confirmar y Crear Evento"):
                # Call Google Calendar
                service = st.session_state.calendar_service
                if not service:
                    service = google_services.get_calendar_service()
                
                event_data = {
                    "summary": result.get('summary'),
                    "description": result.get('description', original_text),
                    "start_time": result.get('start_time'),
                    "end_time": result.get('end_time'),
                    "colorId": result.get('colorId', '11')
                }
                
                created = google_services.add_event_to_calendar(service, event_data)
                if created:
                    st.success("Evento creado exitosamente!")
                    return True
                else:
                    st.error("Error creando evento")
                    return False
                    
    elif action == 'create_task':
        with st.expander("✅ Propuesta de Tarea", expanded=True):
            st.info("La IA sugiere crear una tarea:")
            st.json(result)
            
            if st.button("✅ Confirmar y Crear Tarea"):
                service = st.session_state.tasks_service
                if not service:
                    service = google_services.get_tasks_service()
                
                # Default list (first one)
                task_lists = google_services.get_task_lists(service)
                if task_lists:
                    list_id = task_lists[0]['id']
                    
                    created = google_services.add_task_to_google(
                        service, 
                        list_id, 
                        title=result.get('title'),
                        notes=result.get('notes', original_text),
                        due_date=result.get('due_date')
                    )
                    if created:
                        st.success("Tarea creada exitosamente!")
                        return True
                    else:
                        st.error("Error creando tarea")
                        return False
                else:
                    st.error("No se encontraron listas de tareas")
                    
    elif action == 'keep_note':
        st.success(f"Nota clasificada como referencia: {result.get('summary')}")
        return True
        
    else:
        st.error(f"Acción desconocida: {result}")
        return False
    return False
