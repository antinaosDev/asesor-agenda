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

# --- SYSTEM PROMPTS (CONSTANTS) ---

PROMPT_EMAIL_ANALYSIS = """
Eres un asistente que extrae eventos y tareas de correos.

REGLAS:
1. Si el asunto contiene "Reunión", "Jornada", "Curso", "Consejo", "Comité" o tiene hora (10:00, 3pm) -> type="event"
2. Todo lo demás -> type="task"
3. NUNCA devuelvas lista vacía. Cada correo genera un objeto.
4. Si no hay fecha, usa {current_date} con hora 09:00

OUTPUT (JSON válido):
[
  {{
    "id": "email_id",
    "type": "event",
    "summary": "Título del correo",
    "description": "Resumen del asunto y cuerpo",
    "start_time": "YYYY-MM-DDTHH:MM:SS",
    "end_time": "YYYY-MM-DDTHH:MM:SS",
    "category": "Reunión"
  }}
]

IMPORTANTE: Devuelve SOLO el JSON. Sin texto adicional ni markdown.
"""


PROMPT_EVENT_PARSING = """
You are an intelligent assistant. Your PRIMARY GOAL is to classify the input ONLY as "event" or "task".

1️⃣ NON-NEGOTIABLE DEFINITIONS:

🗓 EVENT
- Occurs at a SPECIFIC time.
- Blocks time on the calendar.
- If you don't go, you "miss it".
- Examples: Meeting, Call, Appointment, Class, Presentation, Flight.
👉 An event ALWAYS has at least one concrete date. Ideally has a time. Lasts hours, not days.

✅ TASK
- Can be done at any time within a range.
- Does NOT block fixed time.
- Has progress.
- Can be completed before the deadline.
- Examples: Submit report, Prepare presentation, Complete evaluation, Formalize budget.
👉 A task might have a deadline, but it is NOT an event.

2️⃣ HARD RULES (NO EXCEPTIONS):

🧱 Rule 1 – Date Range = TASK
If text contains: "from X to Y", "Jan - Mar", "during the month", "throughout".
➡️ TASK, ALWAYS. (Never event).

🧱 Rule 2 – Action Verbs = TASK
If it starts with: "perform", "complete", "prepare", "submit", "deliver", "review", "formalize".
➡️ TASK. (Even if it has a date).

🧱 Rule 3 – Exact Time = EVENT
If it says: "10:00", "15:30", "at 9", "from 14:00 to 15:00".
➡️ EVENT. (Even if text sounds like a task).

🧱 Rule 4 – "Deadline" ≠ Event
If date indicates: "deadline", "until", "before", "max by".
➡️ TASK with deadline.

🧱 Rule 5 – Full Days/Weeks = TASK
If it lasts: "several days", "weeks", "months".
➡️ TASK.

🧱 Rule 6 – Multiple Items = SPLIT
If input contains multiple distinct sections, dates, or milestones (e.g. a schedule list):
➡️ SPLIT into a JSON LIST of multiple objects. Do NOT combine them.
Example Input: "Jan 5: Meeting. Feb 10: Report due."
Output: [{{"summary": "Meeting"...}}, {{"summary": "Report due"...}}]

Context:
- Current Date: {current_date}
- Default Year: {current_year}

COLOR_RULES (Google Calendar IDs) - Smart Executive Mapping:
- "11" (Red): HIGH PRIORITY / Critical / Deadlines.
- "10" (Green): Bio / Health / Medical / Balance.
- "9" (Blueberry): Personal / Sports / Family.
- "8" (Graphite): Admin / Logistics / Commute.
- "7" (Peacock): Deep Work / Focus / Operations.
- "6" (Orange): External Meeting / Client / Sales.
- "5" (Yellow): Brainstorming / Ideas / Strategy.
- "4" (Flamingo): Internal Meeting / Team / HR.
- "3" (Purple): Special Projects / Innovation.
- "2" (Sage): Planning / Review / QBR.
- "1": General / Misc / Other.

JSON Structure:
- "type": "event" or "task" (LOWERCASE).
- "summary": Professional Title in Spanish.
- "description": Complete description in Spanish.
- "start_time": ISO 8601 (YYYY-MM-DDTHH:MM:SS).
- "end_time": ISO 8601 (YYYY-MM-DDTHH:MM:SS).
- "recurrence": [OPTIONAL] List of RRULE strings for Google Calendar. 
    - Examples: ["RRULE:FREQ=WEEKLY;BYDAY=MO"], ["RRULE:FREQ=DAILY;COUNT=5"], ["RRULE:FREQ=MONTHLY;BYMONTHDAY=15"].
    - Use ONLY if text says "every Monday", "each week", "monthly", etc.
- "colorId": String ID.

IMPORTANT: 
- DO NOT interpret user intention. If in doubt -> CLASSIFY AS TASK.
- OUTPUT MUST BE VALID JSON.
- LANGUAGE: SPANISH.
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

@st.cache_data(ttl=3600, show_spinner=False)
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

@st.cache_data(ttl=7200, show_spinner=False)
def analyze_emails_ai(emails, custom_model=None):
    if not emails: return []
    client = _get_groq_client()
    
    # Configuration
    BATCH_SIZE = 5 # Process 5 emails at a time to prevent token truncation
    # EMERGENCY: Reverting to 8b-instant with ultra-simple prompt for reliability
    default_primary = "llama-3.1-8b-instant" 
    fallback_model = "llama-3.1-8b-instant"
    
    # Model Selection
    model_id = custom_model if custom_model else default_primary
    
    # ... (Rest of analyze_emails_ai code)

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
    if not model_id:
         if 'user_data_full' in st.session_state and 'modelo_ia' in st.session_state.user_data_full:
             pref = str(st.session_state.user_data_full['modelo_ia']).strip()
             if pref and pref.lower() != 'nan' and pref != '':
                 model_id = pref
    if not model_id: model_id = default_primary

    all_results = []
    
    # Chunking Loop
    for i in range(0, len(emails), BATCH_SIZE):
        batch = emails[i : i + BATCH_SIZE]
        
        # Prepare Prompt for this Batch
        batch_text = "ANALIZA ESTOS CORREOS:\n"
        for e in batch:
            raw_body = e.get('body', '') or ''
            # Optimize Tokens: Collapse whitespace
            import re
            body_clean = re.sub(r'\s+', ' ', raw_body).strip()
            # Max Recall: Limit increased to 4000
            body_final = body_clean[:4000]
            
            batch_text += f"ID: {e['id']} | DE: {e['sender']} | ASUNTO: {e['subject']} | CUERPO: {body_final}\n---\n"
            
        prompt = PROMPT_EMAIL_ANALYSIS.format(current_date=datetime.datetime.now().strftime("%Y-%m-%d"))
        
        try:
            # Call AI
            completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": batch_text}
                ],
                model=model_id,
                temperature=0.1,
                max_tokens=4096 # Increased from 2048
            )
            raw_content = completion.choices[0].message.content.strip()
            # FORCE Debug Output (ALWAYS create)
            if 'debug_ai_raw' not in st.session_state: 
                st.session_state.debug_ai_raw = []
            st.session_state.debug_ai_raw.append(f"=== BATCH {i} (Model: {model_id}) ===\n{raw_content}\n")
            
            # Also log to console
            print(f"\n{'='*60}")
            print(f"BATCH {i} | MODEL: {model_id}")
            print(f"INPUT: {len(batch_text)} chars, {len(batch)} emails")
            print(f"OUTPUT:\n{raw_content}")
            print(f"{'='*60}\n")
            
            print(f"--- DEBUG AI BATCH {i} ---")
            print(f"INPUT LEN: {len(batch_text)}")
            print(f"OUTPUT: {raw_content[:500]}...") # Print first 500 chars
            
            content = _clean_json_output(raw_content)
            results = json.loads(content)
            if isinstance(results, dict): results = [results]
            
            # Verify results exist
            if not results:
                 print(f"WARNING: Batch {i} returned empty JSON results.")
                 st.toast(f"⚠️ Batch {i}: IA no encontró datos (Posible formato inválido o vacío).", icon="⚠️")
                 
            all_results.extend(results)
            
        except Exception as e:
            err_msg = str(e)
            print(f"ERROR BATCH {i}: {err_msg}")
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
                    if isinstance(fb_results, dict): fb_results = [fb_results]
                    all_results.extend(fb_results)
                except Exception as e2:
                    st.error(f"❌ Fallback Error (Batch {i}): {e2}")
            else:
                st.error(f"❌ Error Analysis (Batch {i}): {e}")

    # Final Post-Processing (Thread ID Attachment)
    email_map = {e['id']: e for e in emails}
    final_clean = []
    for res in all_results:
        # Validate ID match
        if 'id' in res and res['id'] in email_map:
            original = email_map[res['id']]
            res['threadId'] = original.get('threadId')
            # Enrichment for Smart Reply
            res['body'] = original.get('body', '') 
            res['sender'] = original.get('sender', '')
            res['subject_original'] = original.get('subject', '')
            final_clean.append(res)
            
    return final_clean


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
    
    prompt = f"""Actúa como un asistente personal de élite (locutor de radio carismático). Genera un guion breve para ser leído en voz alta.
    
    TUS OBJETIVOS DE HOY ({datetime.datetime.now().strftime('%A %d de %B')}):
    
    1. 📅 AGENDA:
    {events_text if events_text else "• Agenda libre 🎉"}
    
    2. 📝 PRIORIDADES:
    {tasks_text if tasks_text else "• Todo al día"}
    
    3. 📬 BANDEJA: {unread_count} correos sin leer.

    INSTRUCCIONES DE ESTILO (CRÍTICO PARA TTS):
    - **TONO**: Conversacional, cálido, profesional pero cercano. Como un Asesor Ejecutivo Senior que se preocupa por el bienestar del usuario.
    - **ESTRUCTURA**:
        1. Saludo breve y enérgico.
        2. Resumen fluido de la agenda y pendientes (Conversado, no lista).
        3. **ASESORÍA DE VALOR (NUEVO)**: Analiza la carga del día y da un consejo personalizado:
            - ¿Día muy lleno? sugiere pausas tácticas, hidratación o respiración entre reuniones.
            - ¿Día ligero? sugiere enfoque estratégico (Deep Work) o adelantar proyectos clave.
            - ¿Tarde libre? sugiere desconexión temprana o formación.
            - Incluye SIEMPRE un tip breve de bienestar físico/mental (postura, vista, luz).
        4. Cierre motivador y profesional.
    - **EDICIÓN**:
        - Convierte horas "14:00" a "las dos de la tarde".
        - No leas IDs ni códigos raros.
        - Usa conectores naturales.
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
    ... (Use standard Google Colors) ...
    - "11": Tomate (Urgente/Rojo)

    GOALS:
    1. EVENTS: Rewrite summaries to be professional/executive. Assign correct Color ID.
    2. TASKS: Rewrite titles to be ACTIONABLE (Start with verb). Suggest 'new_due' ONLY if urgent/overdue context is obvious (otherwise keep same).
    
    OUTPUT FORMAT (JSON):
    {
        "optimization_plan": {
            "event_id_1": {"type": "event", "new_summary": "...", "colorId": "ID_STRING"},
            "task_id_1":  {"type": "task",  "new_title": "...", "list_id": "...", "new_due": "YYYY-MM-DD (Optional)"}
        },
        "advisor_note": "Resumen estratégico de mejoras..."
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
