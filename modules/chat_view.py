import streamlit as st
import modules.ai_core as ai
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

    if audio_value:
        # Process Audio
        # Use simple hash of bytes to detect change, as .id attribute is unreliable
        audio_bytes = audio_value.getvalue()
        audio_hash = hash(audio_bytes)
        
        if "last_audio_hash" not in st.session_state or st.session_state.last_audio_hash != audio_hash:
            st.session_state.last_audio_hash = audio_hash
            with st.spinner("🎧 Escuchando y transcribiendo..."):
                user_input = ai.transcribe_audio_groq(audio_value)
                is_audio = True
    elif prompt_text:
        user_input = prompt_text

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

        # Logic to trigger actions based on response (Optional - Advanced)
        # If response contains specific flags, we could trigger UI updates here.
        
        # Rerun to update if it was an audio interaction to clear the widget state visually if needed
        # (Streamlit handles audio widget state tricky, usually requires user to clear it)

def _get_lite_context():
    """Recopila contexto esencial y ligero para el prompt del sistema."""
    import modules.google_services as gs
    
    # Date
    now = datetime.datetime.now()
    ctx = f"Fecha: {now.strftime('%Y-%m-%d %H:%M')}\n"
    
    # Events (Lite)
    try:
        if 'c_events_cache' in st.session_state:
            # Use Cache if available to save API calls
            events = st.session_state.c_events_cache
            ctx += "Agenda Hoy:\n"
            count = 0
            for e in events:
                start = e.get('start', {}).get('dateTime', '')[11:16]
                summary = e.get('summary', 'Evento')
                ctx += f"- {start} {summary}\n"
                count += 1
                if count >= 5: break # Limit to 5 for tokens
            if count == 0: ctx += "(Agenda libre)\n"
    except:
        ctx += "Agenda: No disponible\n"

    return ctx
