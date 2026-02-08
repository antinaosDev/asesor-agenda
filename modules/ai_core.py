import datetime
import json
import streamlit as st
from groq import Groq
import re

# Load API Key properly
def _get_groq_client():
    import os
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    if not GROQ_API_KEY and "GROQ_API_KEY" in st.secrets:
        GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    return Groq(api_key=GROQ_API_KEY)

# --- CHAT & AUDIO FUNCTIONS (NEW) ---

def transcribe_audio_groq(audio_file):
    """
    Transcribe audio usando Groq Whisper (Whisper-large-v3).
    Soporta input directo de st.audio_input (UploadedFile).
    """
    client = _get_groq_client()
    import tempfile
    import os
    try:
        # Streamlit UploadedFile -> BytesIO
        # Groq client espera un archivo con nombre para detectar formato
        # Create a temporary file to write the audio content
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_file.write(audio_file.getvalue())
            tmp_path = tmp_file.name

        # Now open the temporary file to pass it to the Groq client
        with open(tmp_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(tmp_path, file.read()), # Send tuple (filename, bytes) or just file object
                model="whisper-large-v3-turbo", # Optimized for speed and cost ($0.04/hr)
                response_format="json",
                language="es", # Force Spanish for better results in this context
                temperature=0.0
            )
        
        # Clean up the temporary file
        os.remove(tmp_path)

        return transcription.text
    except Exception as e:
        return f"Error en transcripción: {str(e)}"

def chat_stream(user_input, history, context_data):
    """
    Genera respuesta de chat en streaming.
    Eficiente en tokens: System Prompt Conciso + Historial Limitado.
    """
    client = _get_groq_client()
    
    SYSTEM_PROMPT = f"""Eres un Asistente Ejecutivo IA eficiente y profesional.
CONTEXTO ACTUAL:
{context_data}

OBJETIVO: Ayudar al usuario a gestionar su agenda, tareas y correos.
REGLAS:
1. Respuestas BREVES y DIRECTAS (ahorro de tokens).
2. Si te piden una acción (crear evento, enviar correo), confirma los detalles necesarios.
3. Habla en español profesional.
4. No uses saludos largos. Ve al grano.
5. INFORMACIÓN "REAL": Usa EXCLUSIVAMENTE los datos bajo "CONTEXTO ACTUAL" para responder sobre agenda/tareas.
6. Si el contexto dice "Sin eventos" o "Error", dilo honestamente. NO INVENTES EVENTOS.
7. Hoy es {datetime.datetime.now().strftime('%A %d de %B de %Y')}.

8. ⚡ ACCIONES REALES (FUNCTION CALLING):
Si el usuario pide crear algo (evento, tarea, email), TU RESPUESTA DEBE TERMINAR CON UN BLOQUE JSON OBLIGATORIO.
IMPORTANTE: 
- Si generas el JSON, tu respuesta verbal DEBE confirmar que lo harás primero. 
- Completa tu narración ANTES del bloque JSON.
- NO digas "no puedo" y luego pongas el JSON.
- Para BORRAR o EDITAR eventos: Usa los IDs de eventos mostrados en el contexto (eventos recientes).
- Si el usuario dice "el último evento" o "el evento que acabas de crear", busca en "ACCIONES RECIENTES".

🎯 EDICIÓN DE EVENTOS:
Cuando el usuario pide editar un evento PERO no especifica qué cambiar:
1. Confirma que encontraste el evento
2. Pregunta qué desea modificar: ¿título, fecha/hora, o descripción?
3. Espera su respuesta antes de generar el JSON

Si el usuario especifica claramente qué editar, procede con el JSON directamente.

Sé flexible con los emails; si parece un email, úsalo.

Formato JSON ESTRICTO (No inventes otro formato):
Puedes devolver UN OBJETO `{{ "action": ... }}` o UNA LISTA `[ {{ "action": ... }}, {{ "action": ... }} ]` para múltiples acciones (ej. 5 cumpleaños).

```json
{{
  "action": "create_event", // O "create_task", "draft_email", "delete_event", "delete_task", "edit_event"
  "params": {{
    // EVENTO: "summary", "start_time" (ISO REQUERIDO), "end_time" (ISO - si no se especifica, se auto-genera +1 hora), "description"
    // TAREA: "title", "due_date" (ISO)
    // EMAIL: "subject", "body", "recipient" (opcional)
    // BORRAR EVENTO: "event_id" (Sacar del contexto)
    // BORRAR TAREA: "task_id" (Sacar del contexto)
    // EDITAR EVENTO: "event_id", y los campos a modificar ("summary", "start_time", "end_time", "description", "colorId")
  }}
}}
```

EJEMPLOS:
1. Batch Eventos: `[{{ "action": "create_event", "params": {{...}} }}, {{ "action": "create_event", "params": {{...}} }}]`
2. Borrar: `{{"action": "delete_event", "params": {{"event_id": "ab123..."}}}}`
3. Tarea: `{{"action": "create_task", "params": {{"title": "Comprar pan", "due_date": "2024-02-01"}}}}`
4. Email: `{{"action": "draft_email", "params": {{"subject": "Hola", "body": "Texto..."}}}}`
5. Editar Evento: `{{"action": "edit_event", "params": {{"event_id": "xyz789", "start_time": "2026-02-03T15:00:00"}}}}`

IMPORTANTE: NO devuelvas `{{ "draft_email": ... }}`. SIEMPRE usa `{{ "action": "...", "params": ... }}`.
"""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Add history (should be already limited by caller)
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
        
    # Add current user input if not already in history (caller handles append Usually, but safe check)
    if history and history[-1]["content"] != user_input:
        messages.append({"role": "user", "content": user_input})

    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant", # Most efficient model
        messages=messages,
        temperature=0.5,
        max_tokens=2000, # Increased for batch actions
        stream=True
    )

    for chunk in completion:
        if chunk.choices[0].delta.content is not None:
            yield chunk.choices[0].delta.content


# --- SYSTEM PROMPTS (CONSTANTS) ---

PROMPT_EMAIL_ANALYSIS = """
Eres un asistente ejecutivo de élite que extrae eventos y tareas de correos electrónicos.

🎯 FILOSOFÍA: "ANTE LA DUDA, ES UN EVENTO".
Tu prioridad ABSOLUTA es NO PERDER ningún compromiso, reunión o fecha importante.

📋 CLASIFICACIÓN AGRESIVA:
1. EVENTO (type="event"):
   - CUALQUIER mención de una fecha o hora futura.
   - Listas de fechas (ej: "Enero 20, Marzo 5...").
   - Palabras clave: Calendario, Programación, Reunión, Cita, Visita, Entrega.
2. TAREA (type="task"):
   - Acciones sin fecha específica ("Revisar informe").
   - Solicitudes generales ("Favor enviar cotización").
3. IMPORTANTE: NUNCA devuelvas lista vacía si hay fechas en el texto.

🔍 REGLAS PARA LISTAS Y FECHAS:
1. 🔢 LISTAS: Si hay una lista de fechas (separada por enters, comas, guiones o pipes "|"), GENERA UN EVENTO POR CADA UNA.
2. 🗓️ FECHA IMPLÍCITA: Si dice "Martes 20" y estamos en Enero, asume Enero 20 del año actual.
3. 🙈 IGNORA encabezados (De/Para). Lee solo el cuerpo.

📝 FORMATO DE SALIDA (JSON):
[
  {{
    "id": "email_id",
    "type": "event",
    "summary": "Título del Evento (Infiérelo si es necesario)",
    "description": "ESTE CAMPO ES CRÍTICO. DEBE INCLUIR TODOS LOS DETALLES DEL TEXTO ORIGINAL. Copia las reglas, instrucciones, agenda y cualquier contexto importante del correo. NO RESUMAS EXCESIVAMENTE.",
    "start_time": "YYYY-MM-DDTHH:MM:SS",
    "end_time": "YYYY-MM-DDTHH:MM:SS", 
    "colorId": "11"
  }}
]

⚠️ CRÍTICO:
- Devuelve SOLO el JSON.
- Si hay múltiples fechas, crea múltiples objetos EVENTO.
- **IMPORTANTE**: La descripción debe capturar el espíritu completo del correo, incluyendo reglas de asistencia (ej: si asiste titular o subrogante), ubicación y agenda.
"""


PROMPT_EVENT_PARSING = """
Eres un asistente ejecutivo de élite especializado en extraer eventos y tareas de texto en lenguaje natural.

🎯 OBJETIVO PRINCIPAL: Analizar el input y generar una lista JSON con TODOS los eventos/tareas encontrados.

CONTEXTO TEMPORAL:
- Fecha Actual: {current_date}
- Año por Defecto: {current_year} (Si no se especifica año, usa este. Si el mes es anterior al actual, asume el próximo año).

📋 REGLAS DE CLASIFICACIÓN:

1️⃣ EVENTO (type="event"):
- Reuniones, juntas, capacitaciones, consejos con fecha y hora.
- Listas de fechas en correos de "Calendario Anual" o "Programación".
- Palabras clave: "Reunión", "Comité", "Jornada", "Sesión", "Cita".

2️⃣ TAREA (type="task"):  
- Pendientes sin hora específica o con plazos (deadlines).
- Acciones a realizar: "Enviar informe", "Comprar insumos".

🔍 REGLAS PARA EMAIL Y LISTAS:
1. 🙈 IGNORA encabezados de correo (De:, Para:, Asunto:, Enviado:). Céntrate en el CUERPO.
2. 🔢 LISTAS NUMERADAS O SEPARADAS: Si hay una lista "1. Febrero 5..." o separada por signos (|, /, -) "ENERO 20 | FEBRERO 15", GENERA UN EVENTO POR CADA ÍTEM.
3. 🗓️ FECHAS RELATIVAS: 
   - "jueves 22 de enero" -> Calcula la fecha exacta usando el año {current_year}.
   - "ENERO, MARTES 20" -> Mismo caso, infiere el año actual.
4. ⏰ RANGOS DE HORAS: "14:00 a 17:00" -> start_time 14:00:00, end_time 17:00:00.

📝 FORMATO DE SALIDA (JSON ÚNICAMENTE):
[
  {{
    "type": "event",
    "summary": "Título Descriptivo (ej: Reunión Comité Capacitación)",
    "description": "ESTE CAMPO ES CRÍTICO. DEBE INCLUIR TODOS LOS DETALLES DEL TEXTO ORIGINAL. NO RESUMAS EXCESIVAMENTE. Incluye: Agenda, Reglas de asistencia (ej: titular/subrogante), Ubicación, Links, Notas importantes. Si es un correo, copia las instrucciones relevantes verbatim.",
    "start_time": "YYYY-MM-DDTHH:MM:SS",
    "end_time": "YYYY-MM-DDTHH:MM:SS",
    "colorId": "4"
  }}
]

⚠️ CRÍTICO:
- Devuelve SOLO el JSON válido.
- SIEMPRE devuelve una lista `[...]`, aunque sea de un solo elemento.
- NO omitas ningún ítem de una lista de fechas.
- Si el título no es explícito en el ítem, usa el contexto del correo (ej: "Reunión Comité" para todas las fechas).
- **IMPORTANTE**: La descripción debe ser RICA y DETALLADA. El usuario necesita saber reglas de asistencia, contexto y cualquier otra instrucción mencionada en el texto original.
"""

PROMPT_PLANNING = """
You are an Expert Project Manager.
Goal: Create a strict MONDAY to FRIDAY work plan based on the user's task list.

Context:
- Current Date: {current_date}
- EXISTING CALENDAR EVENTS (Fixed Commitments):
{calendar_context}

RULES:
1. **Integrate**: Include the "Fixed Commitments" in the daily plan.
2. **NO Overload**: If a day has many Fixed Commitments, assign fewer new tasks.
3. **NO Fragmentation**: Do not split a single task across multiple days unless explicitly stated.
4. **Prioritize**: Put most critical/hard tasks earlier in the week.
5. **Output**: JSON Object where keys are "Monday", "Tuesday", "Wednesday", "Thursday", "Friday".
   Value is a LIST of strings (the tasks AND events).
6. **STRICTLY JSON**: Do NOT output introductory text.
7. **LANGUAGE**: ALL TASKS AND KEYS MUST BE IN SPANISH.
   Use keys: "Lunes", "Martes", "Miércoles", "Jueves", "Viernes".

Output JSON Format:
{{
    "Lunes": ["[Evento] Reunión Equipo", "Tarea 1"],
    "Martes": ["Tarea 2"],
    ...
}}
"""

# --- HELPERS ---
def _clean_json_output(content):
    """
    Revised Robust Strategy: Stream Decoder.
    Uses json.JSONDecoder to extract valid objects/lists sequentially.
    Handles truncated output by saving whatever was successfully parsed before the error.
    """
    decoder = json.JSONDecoder()
    content = content.strip()
    results = []
    pos = 0
    
    while pos < len(content):
        # Find next potential start of JSON (Object or Array)
        match = re.search(r'[\{\[]', content[pos:])
        if not match:
            break
            
        start_idx = pos + match.start()
        
        try:
            # raw_decode returns (object, end_index)
            obj, end_idx = decoder.raw_decode(content, idx=start_idx)
            
            if isinstance(obj, list):
                results.extend(obj)
            elif isinstance(obj, dict):
                results.append(obj)
            
            # Move position to end of parsed object
            pos = end_idx
            
        except json.JSONDecodeError:
            # If parsing fails (e.g. truncated or invalid), skip this char and try next
            # But usually if it fails at top level, it might be the cut-off at the end.
            # We just increment to continue searching or eventually exit
            pos = start_idx + 1
            
    return json.dumps(results)

# --- SMART REMINDERS ---


# Backup: Keep _try_parse_block just in case imports rely on it, 
# but it's not used by the new function.
def _try_parse_block(block, results_list):
    try:
        parsed = json.loads(block)
        if isinstance(parsed, list):
            results_list.extend(parsed)
        elif isinstance(parsed, dict):
            results_list.append(parsed)
    except:
        pass

# --- HELPERS ---
def _calculate_default_end_time(start_str):
    """
    Calculates end time with 2-hour default + Work Hour Constraints.
    Mon-Thu: Limit 17:00
    Fri: Limit 16:00
    """
    import datetime
    try:
        start_dt = datetime.datetime.fromisoformat(start_str)
        default_end = start_dt + datetime.timedelta(hours=2)
        
        # Work Hour Limits
        weekday = start_dt.weekday() # 0=Mon, 4=Fri
        limit_hour = 17 
        if weekday == 4: # Friday
            limit_hour = 16
            
        limit_dt = start_dt.replace(hour=limit_hour, minute=0, second=0, microsecond=0)
        
        # If default end exceeds limit (and start is before limit), cap it.
        # But if start is already after limit (e.g. evening meeting), keep 2h duration.
        if start_dt < limit_dt and default_end > limit_dt:
             return limit_dt.strftime("%Y-%m-%dT%H:%M:%S")
        
        return default_end.strftime("%Y-%m-%dT%H:%M:%S")
    except:
        return None

# --- CORE FUNCTIONS ---

# @st.cache_data(ttl=3600, show_spinner=False) # TEMPORARILY DISABLED FOR TESTING
def parse_events_ai(text_input):
    client = _get_groq_client()
    now = datetime.datetime.now()
    
    prompt = PROMPT_EVENT_PARSING.format(
        current_date=now.strftime("%Y-%m-%d"),
        current_year=now.year
    )
    
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text_input}
            ],
            model="llama-3.1-8b-instant", # Optimized for speed/cost
            temperature=0.1,
            max_tokens=3072
        )
        content = _clean_json_output(completion.choices[0].message.content.strip())
        
        # Safe Parse
        events = json.loads(content, strict=False)
        if isinstance(events, dict): events = [events]
        
        # Post-Processing
        for event in events:
            if event.get('start_time') and event['start_time'].endswith('Z'): event['start_time'] = event['start_time'][:-1]
            if event.get('end_time') and event['end_time'].endswith('Z'): event['end_time'] = event['end_time'][:-1]
            
        return events
    except Exception as e:
        err_msg = str(e).lower()
        if "rate limit" in err_msg or "429" in err_msg:
             st.warning("⚠️ Límite de tokens en parse_events. Fallback a modelo rápido...")
             try:
                completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": "Generate JSON Simple."}
                    ],
                    model="llama-3.1-8b-instant",
                    temperature=0.1,
                    max_tokens=3072
                )
                content = _clean_json_output(completion.choices[0].message.content.strip())
                events = json.loads(content, strict=False)
                if isinstance(events, dict): events = [events]
                return events
             except: pass

        # Fallback manual cleaning if strict=False fails
        try:
            if "content" in locals():
               cleaned = content.replace('\n', '\\n').replace('\r', '')
               events = json.loads(cleaned, strict=False)
               if isinstance(events, dict): events = [events]
               return events
        except: pass
        
        st.error(f"AI Parsing Error: {e}")
        return []

@st.cache_data(ttl=3600, show_spinner=False)
def analyze_document_vision(text_content, images_base64=[]):
    """
    Analiza texto + imágenes usando Llama 3.2 Vision (11b).
    """
    client = _get_groq_client()
    now = datetime.datetime.now()
    
    # Construct Content Payload
    user_content = []
    
    # 1. Text Context
    if text_content:
        user_content.append({"type": "text", "text": f"DOCUMENT TEXT:\n{text_content}\n\n"})
        
    # 2. Images
    for img_b64 in images_base64:
        user_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{img_b64}"
            }
        })
        
    # 3. Final Instruction
    prompt_instruction = PROMPT_EVENT_PARSING.format(
        current_date=now.strftime("%Y-%m-%d"),
        current_year=now.year
    ) + "\n\nINSTRUCTION: Extract events from the provided text and images. Images might contain schedules, tables, or flyers."

    user_content.append({"type": "text", "text": prompt_instruction})

    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "user", "content": user_content}
            ],
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            temperature=0.1,
            max_tokens=4096
        )
        content = _clean_json_output(completion.choices[0].message.content.strip())
        
        # Safe Parse
        events = json.loads(content, strict=False)
        if isinstance(events, dict): events = [events]
        
        # Post-Processing
        for event in events:
            if event.get('start_time') and event['start_time'].endswith('Z'): event['start_time'] = event['start_time'][:-1]
            if event.get('end_time') and event['end_time'].endswith('Z'): event['end_time'] = event['end_time'][:-1]
            
            # Auto-calculate End Time (+2h) if missing
            if event.get('start_time') and not event.get('end_time'):
                calc_end = _calculate_default_end_time(event['start_time'])
                if calc_end: event['end_time'] = calc_end
            
        return events
    except Exception as e:
        st.error(f"Vision Analysis Error: {e}")
        return []

# TEMPORARILY DISABLED FOR DEBUGGING - Re-enable after AI is working
# @st.cache_data(ttl=7200, show_spinner=False)
def analyze_emails_ai(emails, custom_model=None):
    """
    Analiza correos usando IA para categorizar/etiquetar.
    Retorna lista de objetos {id, type, summary, description, start_time, end_time, category, urgency, ...}
    """
    import streamlit as st
    import datetime
    import json
    import traceback
    
    if not emails:
        return []
    
    # Get client
    client = _get_groq_client()
    if not client:
        st.error("❌ No se pudo crear cliente Groq")
        return []
    
    # Configuration
    BATCH_SIZE = 5
    default_primary = "llama-3.1-8b-instant" 
    fallback_model = "llama-3.1-8b-instant"
    
    # Model Selection
    model_id = custom_model if custom_model else default_primary
    
    all_results = []
    total_batches = (len(emails) + BATCH_SIZE - 1) // BATCH_SIZE
    
    st.toast(f"📊 Procesando {total_batches} batches con modelo {model_id}", icon="📊")
    
    for i in range(0, len(emails), BATCH_SIZE):
        batch = emails[i:i+BATCH_SIZE]
        
        # Prepare Prompt for this Batch
        batch_text = "ANALIZA ESTOS CORREOS:\n"
        for e in batch:
            raw_body = e.get('body', '') or ''
            import re
            body_clean = re.sub(r'\s+', ' ', raw_body).strip()
            body_final = body_clean[:4000]
            
            batch_text += f"ID: {e['id']} | DE: {e['sender']} | ASUNTO: {e['subject']} | CUERPO: {body_final}\n---\n"
            
        prompt = PROMPT_EMAIL_ANALYSIS.format(current_date=datetime.datetime.now().strftime("%Y-%m-%d"))
        
        try:
            st.toast(f"🤖 Llamando a {model_id} (Batch {i//BATCH_SIZE + 1}/{total_batches})", icon="🤖")
            
            # Call AI
            completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": batch_text}
                ],
                model=model_id,
                temperature=0.1,
                max_tokens=4096
            )
            raw_content = completion.choices[0].message.content.strip()
            
            st.toast(f"✅ Recibida respuesta de IA ({len(raw_content)} chars)", icon="✅")
            
            # FORCE Debug Output
            if 'debug_ai_raw' not in st.session_state: 
                st.session_state.debug_ai_raw = []
            st.session_state.debug_ai_raw.append(f"=== BATCH {i} (Model: {model_id}) ===\n{raw_content}\n")
            
            print(f"\n{'='*60}")
            print(f"BATCH {i} | MODEL: {model_id}")
            print(f"OUTPUT:\n{raw_content}")
            print(f"{'='*60}\n")
            
            content = _clean_json_output(raw_content)
            results = json.loads(content)
            if isinstance(results, dict): 
                results = [results]
            
            if not results:
                 st.toast(f"⚠️ Batch {i}: IA no encontró datos", icon="⚠️")
                 
            all_results.extend(results)
            
        except Exception as e:
            err_msg = str(e)
            st.error(f"❌ Error en Batch {i//BATCH_SIZE + 1}: {err_msg}")
            
            traceback_str = traceback.format_exc()
            st.code(traceback_str)
            
            # Automatic Fallback for 429 Rate Limits
            if ("429" in err_msg or "rate limit" in err_msg.lower()) and not custom_model:
                st.warning(f"⚠️ Limit (Batch {i//BATCH_SIZE + 1}): Swapping to {fallback_model}...")
                try:
                    completion = client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": batch_text}
                        ],
                        model=fallback_model,
                        temperature=0.1,
                        max_tokens=3072
                    )
                    content = _clean_json_output(completion.choices[0].message.content.strip())
                    fb_results = json.loads(content)
                    if isinstance(fb_results, dict): 
                        fb_results = [fb_results]
                    all_results.extend(fb_results)
                except Exception as e2:
                    st.error(f"❌ Fallback Error (Batch {i}): {e2}")
            else:
                st.error(f"❌ Error Analysis (Batch {i}): {e}")

    # Final Post-Processing
    email_map = {e['id']: e for e in emails}
    final_clean = []
    for res in all_results:
        if 'id' in res and res['id'] in email_map:
            original = email_map[res['id']]
            res['threadId'] = original.get('threadId')
            res['body'] = original.get('body', '') 
            res['sender'] = original.get('sender', '')
            res['subject_original'] = original.get('subject', '')
            final_clean.append(res)
            
    return final_clean


# --- NEW: SMART REPLY ---
PROMPT_EMAIL_REPLY = """
Eres un Asistente Ejecutivo. Tu tarea es redactar una RESPUESTA DE BORRADOR para el siguiente correo.
Correo Recibido:
"{email_body}"

Intención de Respuesta: {intent} (Ej: Confirmar, Reagendar, Negociar)

Instrucciones:
- Idioma: Español Profesional (Neutro).
- Tono: Cortés, directo y eficiente.
- Formato: Solo el cuerpo del correo. No incluyas "Asunto:" ni saludos placeholders como "[Tu Nombre]" (usa 'Atte.' simple).

Borrador:
"""

@st.cache_data(show_spinner=False)
def generate_reply_email(email_body, intent="Confirmar recepción"):
    client = _get_groq_client()
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": PROMPT_EMAIL_REPLY.format(email_body=email_body[:2000], intent=intent)}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.3,
            max_tokens=256
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generando borrador: {e}"


@st.cache_data(ttl=3600, show_spinner=False)
def generate_daily_briefing(events, tasks, unread_count):
    """Genera briefing textual para TTS (max 300 palabras)"""
    import datetime
    client = _get_groq_client()
    
    events_text = ""
    for i, ev in enumerate(events[:5], 1):
        time = ev.get('start', {}).get('dateTime', '')[:16] if 'start' in ev else ''
        events_text += f"{i}. {ev.get('summary', 'Sin título')} a las {time[-5:]}\n"
    
    tasks_text = ""
    for i, task in enumerate(tasks[:3], 1):
        tasks_text += f"{i}. {task.get('title', 'Sin título')}\n"
    
    prompt = f"""
ROL:
Eres un asistente personal de élite con voz de locutor profesional.
Hablas como un Asesor Ejecutivo Senior, similar a Jarvis en Iron Man:
analítico, cercano, preciso y orientado a optimizar el rendimiento del usuario.
Tu texto será leído en voz alta mediante TTS.

MISIÓN:
Generar un guion breve, fluido y natural para iniciar el día del usuario,
resumiendo agenda, prioridades y correos, y aportando asesoría de alto valor
como si conocieras bien al usuario desde hace tiempo.

CONTEXTO DEL DÍA ({datetime.datetime.now().strftime('%A %d de %B')}):
AGENDA:
{events_text if events_text else "Agenda libre"}

PRIORIDADES:
{tasks_text if tasks_text else "Todo al día"}

BANDEJA:
{unread_count} correos sin leer.

FORMATO OBLIGATORIO DEL GUION:
1. Apertura breve y natural.
   - Varía el estilo cada día (saludo directo, comentario contextual u observación del día).
2. Resumen conversado de la agenda y pendientes.
   - No enumeres.
   - No leas títulos textualmente.
   - Usa transiciones naturales.
3. ASESORÍA DE VALOR (núcleo del mensaje):
   Analiza la carga del día usando estas heurísticas:
   - Día cargado: más de 4 eventos o bloques consecutivos → sugiere pausas tácticas.
   - Día medio: 2–4 eventos → sugiere enfoque, priorización y gestión de energía.
   - Día ligero o agenda libre → sugiere Deep Work, adelantar proyectos o formación.
   Incluye SIEMPRE una micro-recomendación de bienestar basada en desempeño,
   como lo haría un asesor experto en productividad humana.
   Puede ser UNA de estas categorías:
   - Postura y ergonomía (cuello, espalda, hombros).
   - Fatiga visual y descanso ocular.
   - Respiración breve para reset cognitivo (≤30 segundos).
   - Hidratación o nutrición ligera.
   - Gestión de energía mental entre bloques de trabajo.
4. Cierre profesional, sereno y motivador (1–2 frases).

DISTRIBUCIÓN APROXIMADA DEL GUION:
- Resumen de agenda y pendientes: ~40%
- Asesoría y recomendaciones: ~35%
- Cierre: ~10%
(El resto se reparte entre apertura y transiciones.)

ESTILO DE VOZ:
- Conversacional, cálido y profesional.
- Cercano sin ser informal.
- Inspirador sin sonar a coach motivacional.
- Frases claras, ritmo natural y pausas implícitas.

REGLAS CRÍTICAS PARA TTS:
- Convierte horas numéricas a lenguaje natural
  (ej. "14:00" → "las dos de la tarde").
- No leas símbolos, emojis, IDs ni códigos.
- Evita paréntesis, viñetas o listas.
- No hagas preguntas al usuario.

RESTRICCIONES:
- No excedas 300–350 palabras.
- No inventes eventos, tareas ni correos.
- No repitas estructuras de saludo entre días consecutivos.
- No uses lenguaje grandilocuente ni excesivamente emocional.
"""

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=400
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        err_msg = str(e).lower()
        if "rate limit" in err_msg or "429" in err_msg:
             try:
                completion = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=400
                )
                return completion.choices[0].message.content.strip()
             except: pass
        return f"Error generando briefing: {e}"

def categorize_event_local(event):
    """Categoriza evento SIN IA (ahorro tokens)"""
    title = event.get('summary', '').lower()
    description = event.get('description', '').lower()
    keywords = {
        'reuniones_internas': ['reunión', 'sync', 'standup', 'planning', 'retro', '1:1'],
        'reuniones_externas': ['cliente', 'proveedor', 'demo', 'venta', 'externo'],
        'trabajo_focalizado': ['desarrollo', 'diseño', 'análisis', 'investigación'],
        'admin': ['admin', 'correo', 'review', 'reporte'],
    }
    for category, words in keywords.items():
        if any(word in title or word in description for word in words):
            return category
    return 'otros'

def calc_event_duration_hours(event):
    """Calcula duración en horas"""
    import datetime
    start_str = event.get('start', {}).get('dateTime') or event.get('start', {}).get('date')
    end_str = event.get('end', {}).get('dateTime') or event.get('end', {}).get('date')
    if not start_str or not end_str:
        return 0
    try:
        start = datetime.datetime.fromisoformat(start_str.replace('Z', '+00:00'))
        end = datetime.datetime.fromisoformat(end_str.replace('Z', '+00:00'))
        return min((end - start).total_seconds() / 3600, 12)
    except:
        return 0

@st.cache_data(ttl=21600, show_spinner=False)
def analyze_time_leaks_weekly(events_last_7days):
    """Analiza distribución semanal con optimización extrema de tokens"""
    client = _get_groq_client()
    
    categories = {
        'reuniones_internas': [],
        'reuniones_externas': [],
        'trabajo_focalizado': [],
        'admin': [],
        'otros': []
    }
    
    total_hours = 0
    for event in events_last_7days:
        duration = calc_event_duration_hours(event)
        category = categorize_event_local(event)
        categories[category].append({'title': event.get('summary', ''), 'duration': duration})
        total_hours += duration
    
    stats = {}
    for cat, items in categories.items():
        cat_hours = sum(e['duration'] for e in items)
        stats[cat] = {
            'hours': round(cat_hours, 1),
            'percentage': round((cat_hours / total_hours * 100) if total_hours > 0 else 0, 1),
            'count': len(items)
        }
    
    prompt = f"""Analiza distribución semanal y da 3 sugerencias ACCIONABLES:

TOTAL: {total_hours:.1f}h (7 días)
- Reuniones Internas: {stats['reuniones_internas']['percentage']}% ({stats['reuniones_internas']['hours']}h, {stats['reuniones_internas']['count']} reuniones)
- Reuniones Externas: {stats['reuniones_externas']['percentage']}% ({stats['reuniones_externas']['hours']}h)
- Trabajo Focalizado: {stats['trabajo_focalizado']['percentage']}% ({stats['trabajo_focalizado']['hours']}h)
- Admin/Otros: {stats['admin']['percentage']}% + {stats['otros']['percentage']}%

FORMATO: Diagnóstico > Top 3 sugerencias con tiempo ahorrado > Acción prioritaria > Score 1-10"""

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=500
        )
        insights = completion.choices[0].message.content.strip()
    except Exception as e:
        err_msg = str(e).lower()
        if "rate limit" in err_msg or "429" in err_msg:
             try:
                completion = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.4,
                    max_tokens=500
                )
                insights = completion.choices[0].message.content.strip()
             except: insights = f"Error (Fallback Failed): {e}"
        else:
             insights = f"Error: {e}"
    
    return {
        'stats': stats,
        'total_hours': round(total_hours, 1),
        'insights': insights,
        'categories': categories
    }

# @st.cache_data(ttl=86400, show_spinner=False) # REMOVED: To prevent caching fallback errors
# @st.cache_data(ttl=86400, show_spinner=False)
def analyze_agenda_ai(events_list, tasks_list=[]):
    client = _get_groq_client()
    
    # Simplify Inputs First
    s_events = [{"id": e['id'], "summary": e.get('summary', 'Sin Título'), "start": e['start']} for e in events_list]
    s_tasks = [{"id": t['id'], "title": t.get('title', 'Sin Título'), "due": t.get('due', 'Sin Fecha'), "list_id": t.get('list_id')} for t in tasks_list]
    
    final_plan = {}
    notes = []
    
    # --- PROCESS EVENTS IN BATCHES ---
    BATCH_EVENTS = 10
    for i in range(0, len(s_events), BATCH_EVENTS):
        chunk = s_events[i : i + BATCH_EVENTS]
        payload = {"events": chunk, "tasks": []}
        
        # Call Helper
        res = _call_agenda_ai_chunk(client, payload)
        if res and 'optimization_plan' in res:
             final_plan.update(res['optimization_plan'])
        if res and 'advisor_note' in res:
             notes.append(res['advisor_note'])

    # --- PROCESS TASKS IN BATCHES ---
    BATCH_TASKS = 5
    for i in range(0, len(s_tasks), BATCH_TASKS):
        chunk = s_tasks[i : i + BATCH_TASKS]
        payload = {"events": [], "tasks": chunk}
        
        # Call Helper
        res = _call_agenda_ai_chunk(client, payload)
        if res and 'optimization_plan' in res:
             final_plan.update(res['optimization_plan'])
             
    # Combine Note
    full_note = " ".join(notes[:2]) # Keep it brief, maybe first 2 notes
    if not full_note: full_note = "Agenda procesada por lotes para máxima precisión."
    
    return {
        "optimization_plan": final_plan,
        "advisor_note": full_note
    }

def _call_agenda_ai_chunk(client, payload):
    """Helper to process one chunk with fallback logic"""
    system_prompt = """
    You are an Elite Executive Assistant. Your job is to OPTIMIZE the user's agenda (Calendar + Tasks) by CATEGORIZING items.
    
    VALID COLOR IDs (String 1-11) for EVENTS:
    - "1": Lavanda (Misc)
    - "2": Salvia (Intercultural/VerdeClaro)
    - "3": Uva (Morado)
    - "4": Rosado (Reuniones Internas/Equipo)
    - "5": Amarillo (Planificación)
    - "6": Naranja (Reuniones Externas/Clientes)
    - "7": Azul Peacock (Trabajo Profundo/Proyectos)
    - "8": Gris (Neutro)
    - "9": Azul Oscuro
    - "10": Verde (Salud/Bienestar)
    - "11": Tomate (Urgente/Rojo)

    GOALS:
    1. EVENTS: CATEGORIZE ONLY. Assign the correct "colorId".
       - CRITICAL: DO NOT CHANGE THE SUMMARY (Title) OR DESCRIPTION. PRESERVE ORIGINAL TEXT EXACTLY.
       - ONLY if the title is "Sin Título" or clearly broken, you may suggest a fix. Otherwise, keeping it identical is preferred.
    2. TASKS: Rewrite titles to be ACTIONABLE (Start with verb). Suggest 'new_due' ONLY if urgent/overdue context is obvious.
    
    CRITICAL RULE - USE REAL IDs:
    - You will receive a JSON payload with events and/or tasks
    - Each event/task has an "id" field
    - In your output, you MUST use the EXACT SAME "id" values from the input
    - DO NOT generate fictional IDs like "event_id_1" or "task_id_1"
    - ONLY include items in the output if they actually need optimization (e.g. missing color or tasks that need actionable verbs)
    - If an event already has a correct color and title, SKIP it.
    
    JSON OUTPUT FORMAT (Object):
    {
        "optimization_plan": {
            "<REAL_EVENT_ID>": {"type": "event", "colorId": "7"}, // ONLY return fields that need update. OMIT "new_summary" to preserve original.
            "<REAL_TASK_ID>":  {"type": "task",  "new_title": "Comprar pan", "list_id": "...", "new_due": "YYYY-MM-DD"}
        },
        "advisor_note": "Resumen estratégico de mejoras..."
    }
    
    EXAMPLE INPUT:
    {"events": [{"id": "abc123xyz", "summary": "reunion equipo", "start": "..."}], "tasks": []}
    
    EXAMPLE OUTPUT (using REAL ID from input):
    {
        "optimization_plan": {
            "abc123xyz": {"type": "event", "colorId": "4"}
        },
        "advisor_note": "Asignado color Rosado a reunión de equipo interna."
    }
    
    LANGUAGE: SPANISH.
    """
    
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload)}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=4096
        )
        content = _clean_json_output(completion.choices[0].message.content.strip())
        result = json.loads(content)
        # Check if result is wrapped in list (sometimes happens)
        if isinstance(result, list) and len(result) > 0: return result[0]
        return result
    except Exception as e:
        # Fallback Logic
        err_msg = str(e).lower()
        if "rate limit" in err_msg or "429" in err_msg:
             try:
                simple_prompt = system_prompt + "\n\nCRÍTICO: Devuelve SOLO el JSON válido. Sin texto explicativo."
                completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": simple_prompt},
                        {"role": "user", "content": json.dumps(payload)}
                    ],
                    model="llama-3.1-8b-instant",
                    temperature=0.2, 
                    max_tokens=3000
                )
                content = _clean_json_output(completion.choices[0].message.content.strip())
                result = json.loads(content)
                if isinstance(result, list) and len(result) > 0: return result[0]
                return result
             except: return {}
        return {}

@st.cache_data(ttl=3600, show_spinner=False)
def generate_work_plan_ai(tasks_text, calendar_context=""):
    client = _get_groq_client()
    prompt = PROMPT_PLANNING.format(
        current_date=datetime.datetime.now().strftime("%Y-%m-%d"),
        calendar_context=calendar_context
    )
    
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": tasks_text}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=2048
        )
        content = _clean_json_output(completion.choices[0].message.content.strip())
        content = _clean_json_output(completion.choices[0].message.content.strip())
        result = json.loads(content)
        if isinstance(result, list) and len(result) > 0:
            return result[0]
        return result
    except Exception as e:
        err_msg = str(e).lower()
        if "rate limit" in err_msg or "429" in err_msg:
             st.warning("⚠️ Límite de tokens en Planificación. Usando modelo rápido...")
             try:
                completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": tasks_text}
                    ],
                    model="llama-3.1-8b-instant",
                    temperature=0.1,
                    max_tokens=2048
                )
                content = _clean_json_output(completion.choices[0].message.content.strip())
                result = json.loads(content)
                if isinstance(result, list) and len(result) > 0:
                    return result[0]
                return result
             except: pass
        
        st.error(f"AI Planning Error: {e}")
        return {}

# @st.cache_data(ttl=86400, show_spinner=False) # REMOVED: To avoid caching error states
def generate_project_breakdown_ai(project_title, project_desc, start_date, end_date, extra_context=""):
    client = _get_groq_client()
    
    # 1. Determine Model (User Pref > Default)
    # Default to 70b but respect limits
    model_id = "llama-3.3-70b-versatile"
    
    if 'user_data_full' in st.session_state and 'modelo_ia' in st.session_state.user_data_full:
             pref = str(st.session_state.user_data_full['modelo_ia']).strip()
             if pref and pref.lower() != 'nan' and pref != '':
                 model_id = pref

    context_block = f"Contexto Extra/Docs: {extra_context}" if extra_context else ""

    system_prompt = f"""
    Eres un Experto Gerente de Proyectos (Project Manager).
    Objetivo: Desglosar el proyecto "{project_title}" en tareas accionables diarias/semanales.
    Contexto Temporal: {start_date} hasta {end_date}
    Descripción: {project_desc}
    {context_block}
    
    CRÍTICO:
    1. EL OUTPUT DEBE SER 100% EN ESPAÑOL.
    2. Formato: Lista JSON de objetos ({{"title": "Título en Español", "date": "YYYY-MM-DD", "notes": "Detalles en Español"}}).
    """
    
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Genera el desglose del proyecto en JSON (Español)."}
            ],
            model=model_id, 
            temperature=0.6, 
            max_tokens=4096
        )
        analysis = _clean_json_output(completion.choices[0].message.content)
        return json.loads(analysis)
    except Exception as e:
        err_msg = str(e).lower()
        # Robust check for Rate Limits
        if "429" in err_msg or "rate limit" in err_msg or "quota" in err_msg:
             st.warning(f"⚠️ Límite de tokens en {model_id}. Reintentando con modelo ligero (llama-3.1-8b)...")
             try:
                # Simplified prompt for 8B model to ensure JSON stability
                simple_prompt = system_prompt + "\n\nIMPORTANTE: Responde SOLO con el JSON. Sin introducción."
                
                completion = client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": simple_prompt},
                        {"role": "user", "content": "Genera el desglose JSON ahora."}
                    ],
                    model="llama-3.1-8b-instant",  # Fallback
                    temperature=0.4, # Lower temp for 8B
                    max_tokens=2048
                )
                raw_content = completion.choices[0].message.content.strip()
                content = _clean_json_output(raw_content)
                return json.loads(content)
             except Exception as e2:
                 st.error(f"❌ Error en Fallback (8B): {e2}")
                 # Debug info for user/admin
                 if 'raw_content' in locals():
                     with st.expander("Ver Respuesta Fallida (Debug)"):
                         st.code(raw_content)
                 return []
        
        st.error(f"AI Breakdown Error ({model_id}): {e}")
        return []

# --- BRAIN DUMP PROCESSING (NOTES) ---
PROMPT_BRAIN_DUMP = """
Eres un asistente ejecutivo experto en GTD (Getting Things Done).
Tu tarea es analizar una "Nota Rápida" (Brain Dump) y clasificarla.

INPUT: "{note_text}"
FECHA ACTUAL: {current_date}

🎯 REGLA DE ORO:
Si el texto menciona una FECHA, HORA, o COMPROMISO TEMPORAL (ej: "mañana", "el martes", "en 2 horas"), DEBE ser "create_event".
No lo conviertas en tarea si puedes ponerle fecha y hora en el calendario.

OPCIONES:
1. "create_event": Si tiene fecha/hora (explícita o implícita). Prioriza esto.
2. "create_task": Solo si es una acción SIN fecha específica.
3. "keep_note": Solo información pasiva (ideas, referencias).

OUTPUT (JSON):
Si es EVENTO:
{{
    "action": "create_event",
    "summary": "Título del evento",
    "description": "Descripción detallada",
    "start_time": "YYYY-MM-DDTHH:MM:SS",
    "end_time": "YYYY-MM-DDTHH:MM:SS" (Calcula 2h por defecto),
    "colorId": "11"
}}

Si es TAREA:
{{
    "action": "create_task",
    "title": "Título de la tarea",
    "notes": "Notas adicionales",
    "due_date": "YYYY-MM-DD" (Solo si es fecha límite, no evento)
}}

Si es NOTA:
{{
    "action": "keep_note",
    "tags": ["tag1", "tag2"],
    "summary": "Título Breve"
}}

REGLAS:
- Responde SOLO el JSON.
- Sé agresivo detectando eventos. Mejor que sobre a que falte en el calendario.
"""

def process_brain_dump(note_text):
    """
    Analiza una nota rápida y determina si es Evento, Tarea o Nota.
    Retorna dict con 'action' y datos.
    """
    import datetime
    import json
    
    client = _get_groq_client()
    now = datetime.datetime.now()
    
    prompt = PROMPT_BRAIN_DUMP.format(
        note_text=note_text,
        current_date=now.strftime("%Y-%m-%d %H:%M")
    )
    
    try:
        completion = client.chat.completions.create(
            messages=[{"role": "system", "content": prompt}],
            model="llama-3.1-8b-instant",
            temperature=0.1,
            max_tokens=1024
        )
        content = _clean_json_output(completion.choices[0].message.content.strip())
        result = json.loads(content)
        if isinstance(result, list):
            result = result[0] if result else {"action": "error", "error": "No data returned"}
            
        # Enforce 2h default for Brain Dump events
        if result.get('action') == 'create_event' and result.get('start_time') and not result.get('end_time'):
             calc_end = _calculate_default_end_time(result['start_time'])
             if calc_end: result['end_time'] = calc_end
             
        return result
    except Exception as e:
        return {"action": "error", "error": str(e)}

# --- STUDY MODES ---
PROMPT_CORNELL = """
RESUME ESTO:
{text}

FORMATO HTML ESTRICTO (bootstrap classes, sin markdown blocks):
<div class='cornell-notes' style='background: rgba(255,255,255,0.05); padding: 20px; border-radius: 10px;'>
  <div class='row'>
    <div class='col-md-4 key-points' style='border-right: 1px solid rgba(255,255,255,0.1); padding-right: 15px;'>
      <h5 style='color: #0dd7f2;'>📌 Puntos Clave</h5>
      <ul>
        <li>Concepto 1</li>
        <li>Pregunta Clave?</li>
      </ul>
    </div>
    <div class='col-md-8 detailed-notes' style='padding-left: 15px;'>
      <h5 style='color: #0dd7f2;'>📝 Notas Detalladas</h5>
      <p>Explicación detallada del tema...</p>
    </div>
  </div>
  <hr style='border-color: rgba(255,255,255,0.1); margin: 20px 0;'>
  <div class='summary-section'>
    <h5 style='color: #f59e0b;'>💡 Resumen (Síntesis)</h5>
    <p>Resumen breve de todo el contenido...</p>
  </div>
</div>
"""

PROMPT_FLASHCARDS = """
EXTRAE JSON FLASHCARDS DE ESTE TEXTO:
{text}

FORMATO EXCLUSIVO JSON (Lista de objetos):
[
  {{"q": "Pregunta corta?", "a": "Respuesta precisa"}},
  ...
]
REGLAS:
- Mínimo 3, Máximo 10 tarjetas.
- Preguntas desafiantes pero claras.
- Respuestas breves para memorizar.
"""

@st.cache_data(ttl=3600, show_spinner=False)
def process_study_notes(text, mode="cornell"):
    client = _get_groq_client()
    
    if mode == "cornell":
        prompt = PROMPT_CORNELL.replace("{text}", text[:8000])
    elif mode == "flashcards":
        prompt = PROMPT_FLASHCARDS.replace("{text}", text[:8000])
    else:
        return {"error": "Modo desconocido"}

    try:
        completion = client.chat.completions.create(
            messages=[{"role": "system", "content": prompt}],
            model="llama-3.1-8b-instant",
            temperature=0.3, # Low temp for factual accuracy
            max_tokens=2048
        )
        content = completion.choices[0].message.content.strip()
        
        if mode == "flashcards":
             return _clean_json_output(content)
        
        # Cleanup potential markdown wrapper for Cornell
        clean_html = content.replace("```html", "").replace("```", "").strip()
        return clean_html
        
    except Exception as e:
        return f"Error procesando estudio: {str(e)}"

# --- MEETING MINUTES GENERATOR (ACTAS) ---

def generate_meeting_minutes_ai(content_text):
    """
    Genera la estructura JSON de un Acta de Reunión a partir de texto/transcripción.
    """
    import datetime
    import json
    client = _get_groq_client()
    
    # NOTE: Llama 3.3 70B has 128k context window. 
    # We remove the 30k char limit to support long meetings (5+ hours).
    # If content is truly massive (>400k chars), it might still hit limits, 
    # but 5 hours of speech is usually ~40k-60k words, well within limits.

    curr_date = datetime.datetime.now().strftime("%d/%m/%Y")
        
    PROMPT_MEETING_MINUTES = f"""
    Eres un Secretario Técnico experto en Gestión de Salud y Documentación Clínica (Norma Técnica Chilena).
    Tu tarea es REDACTAR UN ACTA DE REUNIÓN FORMAL basada en el audio/texto proporcionado.

    INPUT TRANSCRITO:
    "{content_text}"

    FECHA REAL: {curr_date}

    OBJETIVO:
    Generar un objeto JSON estructurado que llene los campos del "FORMATO OFICIAL DE ACTA INSTITUCIONAL DE REUNIÓN / COMITÉ".

    REGLAS DE REDACCIÓN:
    1. TIEMPO VERBAL: Pasado ("se acordó", "se analizó", "se determinó").
    2. TONO: Técnico, objetivo, impersonal y formal. Sin juicios de valor.
    3. ESTRUCTURA:
       - Identificar ASUNTO principal.
       - Extraer ASISTENTES (Si no están claros, poner "No especificados - Completar manualmente").
       - Resumir el DESARROLLO en puntos clave.
       - Extraer ACUERDOS CON RESPONSABLES y PLAZOS (Si no hay plazo, poner "Por definir").

    FORMATO JSON ESPERADO (No inventes claves):
    {{
      "asunto": "Resumen breve del tema",
      "fecha": "DD/MM/AAAA",
      "hora_inicio": "HH:MM",
      "hora_termino": "HH:MM",
      "lugar": "Sala/Virtual",
      "asistentes": ["Nombre 1 - Cargo", "Nombre 2 - Cargo"],
      "tabla_puntos": ["Punto 1", "Punto 2"],
      "desarrollo": "Texto narrativo formal describiendo la discusión...",
      "acuerdos": [
        {{"descripcion": "Acuerdo 1", "responsable": "Cargo/Nombre", "plazo": "Fecha"}},
        {{"descripcion": "Acuerdo 2", "responsable": "Cargo/Nombre", "plazo": "Fecha"}}
      ],
      "proxima_reunion": "DD/MM/AAAA HH:MM"
    }}
    """
    
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": PROMPT_MEETING_MINUTES}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=4000,
            response_format={"type": "json_object"}
        )
        msg_content = completion.choices[0].message.content
        return json.loads(msg_content)
    except Exception as e:
        return {"error": str(e)}

# --- PROJECT BREAKDOWN (DESGLOSE) ---

def generate_project_breakdown(project_text):
    """
    Breaks down a project into actionable subtasks using AI.
    """
    import datetime
    import json
    client = _get_groq_client()
    
    curr_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    PROMPT_PROJECT_BREAKDOWN = f"""
    Eres un Project Manager experto.
    TU OBJETIVO: Desglosar el siguiente PROYECTO o TAREA COMPLEJA en una lista de subtareas accionables.
    
    PROYECTO: "{project_text}"
    HOY ES: {curr_date}
    
    REGLAS:
    1. Genera entre 5 y 15 subtareas lógicas y secuenciales.
    2. Asigna una fecha de vencimiento ("due") estimada para cada una, comenzando desde HOY.
    3. Distribuye las tareas en el tiempo de forma realista.
    
    FORMATO JSON OBLIGATORIO:
    {{
      "project_name": "Nombre refinado del proyecto",
      "tasks": [
        {{"title": "Verbo + Acción específica 1", "due": "YYYY-MM-DD"}},
        {{"title": "Verbo + Acción específica 2", "due": "YYYY-MM-DD"}}
      ]
    }}
    """
    
    try:
        completion = client.chat.completions.create(
            messages=[{"role": "system", "content": PROMPT_PROJECT_BREAKDOWN}],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        return {"error": str(e)}

# --- VOICE ANALYST (COMANDOS) ---

def analyze_voice_command(text_command):
    """
    Analyzes a voice command and returns a list of executable actions.
    """
    import datetime
    import json
    client = _get_groq_client()
    
    curr_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    PROMPT_VOICE_ANALYST = f"""
    Eres un Asistente Ejecutivo de alto nivel.
    TU OBJETIVO: Analizar el comando de voz del usuario y extraer una LISTA DE ACCIONES EJECUTABLES.
    
    COMANDO: "{text_command}"
    FECHA ACTUAL: {curr_date}
    
    REGLAS:
    1. Detecta múltiples intenciones (ej: "Agenda reunión Y envía correo").
    2. Extrae fechas relativas ("mañana a las 3", "el viernes") a ISO 8601.
    3. Si falta información (ej: duración), asume valores por defecto lógicos (1 hora).
    
    ACCIONES SOPORTADAS:
    - "create_event": {{ "summary": "...", "start_time": "ISO", "end_time": "ISO", "description": "..." }}
    - "create_task": {{ "title": "...", "due_date": "YYYY-MM-DD" }}
    - "draft_email": {{ "recipient": "email@...", "subject": "...", "body": "..." }}
    
    FORMATO JSON OBLIGATORIO:
    {{
      "actions": [
        {{ "action": "create_event", "params": {{ ... }} }},
        {{ "action": "draft_email", "params": {{ ... }} }}
      ]
    }}
    """
    
    try:
        completion = client.chat.completions.create(
            messages=[{"role": "system", "content": PROMPT_VOICE_ANALYST}],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        return {"error": str(e)}
