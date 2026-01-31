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
    try:
        # Streamlit UploadedFile -> BytesIO
        # Groq client espera un archivo con nombre para detectar formato
        completion = client.audio.transcriptions.create(
            file=(audio_file.name, audio_file.getvalue()),
            model="whisper-large-v3", # Multilingual, excellent for Spanish
            response_format="json",
            language="es", # Force Spanish for better accuracy
            temperature=0.0
        )
        return completion.text
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
IMPORTANTE: Si generas el JSON, tu respuesta verbal DEBE confirmar que lo harás. NO digas "no puedo" y luego pongas el JSON.
Sé flexible con los emails; si parece un email, úsalo.

Formato JSON ESTRICTO (No inventes otro formato):
```json
{{
  "action": "create_event", // Valores válidos: "create_event", "create_task", "draft_email"
  "params": {{
    // EVENTO: "summary", "start_time" (ISO), "end_time" (ISO), "description"
    // TAREA: "title", "due_date" (ISO)
    // EMAIL: "subject", "body", "recipient" (opcional)
  }}
}}
```

EJEMPLOS:
1. Evento: `{{"action": "create_event", "params": {{"summary": "Cita", "start_time": "2024-01-31T10:00:00", "end_time": "2024-01-31T11:00:00"}}}}`
2. Tarea: `{{"action": "create_task", "params": {{"title": "Comprar pan", "due_date": "2024-02-01"}}}}`
3. Email: `{{"action": "draft_email", "params": {{"subject": "Hola", "body": "Texto..."}}}}`

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
        max_tokens=512,
        stream=True
    )

    for chunk in completion:
        if chunk.choices[0].delta.content is not None:
            yield chunk.choices[0].delta.content


# --- SYSTEM PROMPTS (CONSTANTS) ---

PROMPT_EMAIL_ANALYSIS = """
Eres un asistente ejecutivo de élite que extrae eventos y tareas de correos electrónicos.

🎯 CLASIFICACIÓN:
1. Si menciona "Reunión", "Jornada", "Curso", "Consejo", "Comité", "Sesión" o tiene hora específica (10:00, 3pm) → type="event"
2. Todo lo demás → type="task"
3. NUNCA devuelvas lista vacía. Cada correo genera al menos un objeto.
4. Si no hay fecha explícita, usa {current_date} con hora 09:00

📝 REGLAS CRÍTICAS PARA DESCRIPCIONES:

⭐ Para EVENTOS (reuniones, consejos, comités):
La descripción DEBE ser COMPLETA y PROFESIONAL:
1. Incluir TODOS los temas/puntos de agenda mencionados en el correo
2. Capturar TEXTUALMENTE:
   - Nombres completos de personas (funcionarios, participantes)
   - Cargos y categorías (ej: "Tecnólogo Médico, categoría B")
   - Artículos de ley, decretos, reglamentos (ej: "artículo 56 del D.S. N°1889/2005")
   - Fechas y plazos específicos
   - Lugares/salas mencionadas
3. Organizar con viñetas o numeración para claridad
4. Estilo: Formal, ejecutivo, profesional - como un acta de reunión
5. NO resumir - incluir TODOS los detalles relevantes del correo

EJEMPLO DE ESTRUCTURA IDEAL:
- AGENDA: Lista numerada de todos los temas
- PARTICIPANTES: Nombres mencionados
- UBICACION: Sala/lugar si se menciona
- REFERENCIAS: Artículos, decretos, reglamentos citados
- NOTAS: Información adicional del remitente

⭐ Para TAREAS:
- Descripción clara del objetivo
- Incluir responsables si se mencionan
- Especificar fechas límite o plazos


🎨 CÓDIGO DE COLOR (Google Calendar IDs):
- "11" (Rojo): URGENTE / Alta Prioridad
- "10" (Verde): Salud / Médico
- "7" (Azul): Proyectos / Operaciones
- "6" (Naranja): Reuniones Externas / Clientes
- "4" (Rosado): Reuniones Internas / Consejos / Comités
- "2" (Verde Salvia): Planificación / Revisión
- "1" (Lavanda): General / Otros

📋 ESTRUCTURA JSON DE SALIDA:
[
  {{
    "id": "email_id",
    "type": "event",
    "summary": "Título Profesional del Evento",
    "description": "Descripción COMPLETA y DETALLADA con TODOS los temas, nombres, referencias, ubicación y notas del correo",
    "start_time": "YYYY-MM-DDTHH:MM:SS",
    "end_time": "YYYY-MM-DDTHH:MM:SS",
    "category": "Reunión",
    "colorId": "4"
  }}
]

⚠️ CRÍTICO:
- Devuelve SOLO el JSON. Sin texto adicional ni markdown.
- Las descripciones de eventos DEBEN capturar TODA la información del correo
- NO omitir detalles importantes: nombres, artículos legales, fechas, lugares
- Formato JSON válido estricto
"""


PROMPT_EVENT_PARSING = """
Eres un asistente ejecutivo de élite especializado en extraer eventos y tareas de texto en lenguaje natural.

🎯 OBJETIVO PRINCIPAL: Analizar el input y generar una lista JSON con TODOS los eventos/tareas encontrados.

📋 REGLAS DE CLASIFICACIÓN:

1️⃣ EVENTO (type="event"):
- Reuniones, juntas, llamadas, consejos, comités con hora específica
- Tiene hora exacta (10:00, 14:30, "a las 3pm") o período específico
- Palabras clave: "Reunión", "Jornada", "Curso", "Consejo", "Comité", "Sesión"
- Ejemplos: "Reunión coordinación", "Consejo técnico", "Jornada de capacitación"

2️⃣ TAREA (type="task"):  
- Actividades con período extendido o fecha límite
- Rangos de fechas ("2 enero - 15 marzo", "enero-febrero")
- Palabras como: "realizar", "completar", "entregar", "formalizar", "validar"
- Hitos, procesos, evaluaciones
- Ejemplos: "Autoevaluación MAIS", "Presupuesto 2026", "Plan de Acción"

📝 REGLAS CRÍTICAS PARA DESCRIPCIONES DE EVENTOS:

⭐ DESCRIPCIÓN PROFESIONAL Y COMPLETA:
Para EVENTOS (reuniones, consejos, comités):
1. La descripción DEBE incluir TODOS los temas/puntos de agenda mencionados
2. Capturar TEXTUALMENTE nombres completos, cargos, artículos de ley, números de decreto
(Para tareas usa "title", "due_date" en params. Para emails usa "subject", "body", y opcionalmente "recipient").
NO ejecutes la acción si faltan datos críticos (hora/fecha para eventos). 
Para borradores de email, el destinatario NO es obligatorio.
5. NO resumir - incluir TODOS los detalles relevantes
6. Mantener el orden de los temas tal como aparecen

EJEMPLO DE ESTRUCTURA IDEAL PARA DESCRIPCIONES:
- AGENDA: Lista numerada completa con todos los temas y detalles
- PARTICIPANTES: Nombres y cargos si se mencionan
- UBICACION: Sala o lugar si se menciona
- REFERENCIAS: Artículos, decretos, reglamentos mencionados textualmente

Para TAREAS:
- Descripción clara del objetivo y entregable esperado
- Incluir responsables si se mencionan
- Especificar requisitos o referencias normativas


🔍 REGLAS ESPECIALES:

📌 Rule 1 - MÚLTIPLES ITEMS
Si el input contiene VARIOS eventos/tareas separados (por títulos, emojis, secciones):
➡️ Genera un objeto JSON por cada uno
➡️ Detecta separadores como: emojis de fecha 📅, saltos de línea, títulos diferentes

📌 Rule 2 - PERÍODOS = TAREA CON DEADLINE
"2 enero - 15 marzo" → start_time="2026-01-02T09:00:00", end_time="2026-03-15T18:00:00"
"Enero - febrero" → start_time="2026-01-01T09:00:00", end_time="2026-02-28T18:00:00"

📌 Rule 3 - PRESERVAR INFORMACIÓN CRÍTICA
✅ SIEMPRE incluir:
- Nombres completos de personas (funcionarios, personal, etc.)
- Cargos y categorías (ej: "Tecnólogo Médico, categoría B")
- Números de artículos, decretos, leyes (ej: "artículo 56 del D.S. N°1889/2005")
- Fechas y plazos específicos
- Lugares o salas (ej: "sala de reunión")

❌ NUNCA simplificar ni omitir:
- Referencias legales o normativas
- Nombres de funcionarios o participantes
- Detalles técnicos o administrativos

📌 Rule 4 - ESPAÑOL PROFESIONAL
Todos los textos deben estar en español formal y profesional

📅 CONTEXTO:
- Fecha Actual: {current_date}
- Año por Defecto: {current_year}

🎨 COLORES (Google Calendar IDs):
- "11" (Rojo): URGENTE / Alta Prioridad / Deadlines Críticos
- "10" (Verde): Salud / Bienestar / Médico
- "7" (Azul Peacock): Trabajo Profundo / Proyectos / Operaciones  
- "6" (Naranja): Reuniones Externas / Clientes
- "4" (Rosado): Reuniones Internas / Equipo / Consejos / Comités
- "2" (Verde Salvia): Planificación / Revisión / QBR
- "1" (Lavanda): General / Otros

📝 ESTRUCTURA JSON DE SALIDA:
[
  {{
    "type": "event",
    "summary": "Título Profesional y Claro del Evento",
    "description": "Descripción COMPLETA y DETALLADA con TODOS los temas de agenda, nombres, referencias, etc.",
    "start_time": "YYYY-MM-DDTHH:MM:SS",
    "end_time": "YYYY-MM-DDTHH:MM:SS",
    "colorId": "4"
  }},
  {{
    "type": "task",
    "summary": "Título de la Tarea",
    "description": "Descripción completa incluyendo responsables, hitos y detalles",
    "start_time": "YYYY-MM-DDTHH:MM:SS",
    "end_time": "YYYY-MM-DDTHH:MM:SS",
    "colorId": "11"
  }}
]

⚠️ CRÍTICO:
- SIEMPRE devuelve al menos un objeto si hay información
- Si detectas MÚLTIPLES items, devuelve un array con varios objetos
- NO devuelvas array vacío [] a menos que el input esté completamente vacío
- Formato JSON válido, sin texto adicional
- Extrae TODA la información útil (responsables, hitos, períodos, referencias)
- Las descripciones de eventos DEBEN ser completas y profesionales
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
    You are an Elite Executive Assistant. Your job is to OPTIMIZE the user's agenda (Calendar + Tasks).
    
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
    1. EVENTS: Rewrite summaries to be professional/executive. Assign correct Color ID.
    2. TASKS: Rewrite titles to be ACTIONABLE (Start with verb). Suggest 'new_due' ONLY if urgent/overdue context is obvious (otherwise keep same).
    
    CRITICAL RULE - USE REAL IDs:
    - You will receive a JSON payload with events and/or tasks
    - Each event/task has an "id" field
    - In your output, you MUST use the EXACT SAME "id" values from the input
    - DO NOT generate fictional IDs like "event_id_1" or "task_id_1"
    - ONLY include items in the output if they actually need optimization
    - If an item is already well-written, SKIP it from the output
    
    OUTPUT FORMAT (JSON):
    {
        "optimization_plan": {
            "<REAL_EVENT_ID_FROM_INPUT>": {"type": "event", "new_summary": "...", "colorId": "ID_STRING"},
            "<REAL_TASK_ID_FROM_INPUT>":  {"type": "task",  "new_title": "...", "list_id": "...", "new_due": "YYYY-MM-DD (Optional)"}
        },
        "advisor_note": "Resumen estratégico de mejoras..."
    }
    
    EXAMPLE INPUT:
    {"events": [{"id": "abc123xyz", "summary": "reunion equipo", "start": "..."}], "tasks": []}
    
    EXAMPLE OUTPUT (using REAL ID from input):
    {
        "optimization_plan": {
            "abc123xyz": {"type": "event", "new_summary": "Reunión Estratégica del Equipo", "colorId": "4"}
        },
        "advisor_note": "Mejorado el profesionalismo del título del evento."
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
        content = _clean_json_output(completion.choices[0].message.content.strip())
        return json.loads(content)
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
