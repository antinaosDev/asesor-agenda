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
You are an Elite Executive Assistant ("Agente A2").
Analyze these emails. Your goal is to:
1. Detect Calendar Events (meetings, deadlines).
2. Detect INFO/TASKS that don't have a date but are IMPORTANT (e.g. "Review this report").
3. Classify EVERY email by Urgency and Category.

Current Date: {current_date}

Output: JSON List of objects.
Structure:
{{
    "id": "email_id_from_input",
    "is_event": boolean, 
    "summary": "Title in Spanish",
    "description": "Details in Spanish",
    "start_time": "YYYY-MM-DDTHH:MM:SS" (or null if no date),
    "end_time": "YYYY-MM-DDTHH:MM:SS" (or null),
    "urgency": "Alta" | "Media" | "Baja",
    "category": "Solicitud" | "Información" | "Pagos" | "Otro"
}}

Rules:
- If an email implies a task ("Do X") but has no date, set is_event=False, start_time=null.
- Urgency "Alta": Deadlines today/tomorrow, money, angry clients.
- Urgency "Media": Normal requests.
- Urgency "Baja": newsletters, fyi.
- LANGUAGE: SPANISH.
- LANGUAGE: SPANISH.
- STRICTLY JSON. NO MARKDOWN. NO CODE BLOCKS. JUST THE RAW JSON LIST.
"""

PROMPT_EVENT_PARSING = """
You are an intelligent assistant that extracts calendar events from text and categorizes them with colors.

Context:
- Current Date: {current_date}
- Default Year: {current_year}

COLOR RULES (Google Calendar IDs):
- "5" (Yellow): MAIS (Programa, Gestión MAIS).
- "2" (Light Green): Intercultural (Temas interculturales, facilitación).
- "11" (Red): Urgent, Deadlines.
- "7" (Peacock): General Work, standard tasks.
- "6" (Orange): External Meetings.
- "3" (Purple): Special Projects.
- "8" (Grey): Admin, Logistics.
- "9" (Blueberry): Personal, Sports.
- "10" (Green): Health.
- "1": Misc/Other.

CRITICAL RULES:
1. **Lists of Dates**: If text lists dates + a general time, apply that time to all.
2. **Contextual Time**: Use intro time for subsequent events if unspecified.
3. **Smart Year**: Dates before today ({current_date}) should be next year ({current_year} + 1).
4. **NO Timezones/UTC**: Return local time `YYYY-MM-DDTHH:MM:SS`.
5. **LANGUAGE**: ALL OUTPUT MUST BE IN SPANISH.

JSON Structure:
- "summary": Professional, Executive Title IN SPANISH.
- "description": Comprehensive, FORMAL/EXECUTIVE description IN SPANISH. Use professional phrasing. MUST include ALL technical details.
- "start_time": ISO 8601 (No Z).
- "end_time": ISO 8601 (No Z).
- "colorId": String ID.

IMPORTANT: OUTPUT MUST BE VALID JSON. Escape all newlines in strings as \\n.
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
    Ultra-Robust Strategy: Stack-based bracket counting.
    Extracts all top-level [...] AND {...} blocks.
    SAFE: Ignores text outside blocks. Returns [] if nothing found.
    """
    content = content.strip()
    results = []
    
    # Scan for top-level brackets/braces
    i = 0
    depth_array = 0
    depth_object = 0
    start_idx = -1
    
    # We treat it as one continuous stream, capturing ANY valid top-level block
    while i < len(content):
        char = content[i]
        
        # Start of a block (if at depth 0)
        if char == '[':
            if depth_array == 0 and depth_object == 0:
                start_idx = i
            depth_array += 1
        elif char == '{':
            if depth_array == 0 and depth_object == 0:
                start_idx = i
            depth_object += 1
            
        # End of a block
        elif char == ']':
            if depth_array > 0:
                depth_array -= 1
                # If we closed the last array and are not in an object
                if depth_array == 0 and depth_object == 0:
                    _try_parse_block(content[start_idx : i+1], results)

        elif char == '}':
            if depth_object > 0:
                depth_object -= 1
                if depth_array == 0 and depth_object == 0:
                     _try_parse_block(content[start_idx : i+1], results)
            
        i += 1

    return json.dumps(results)

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
            model="llama-3.3-70b-versatile",
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

def analyze_emails_ai(emails, custom_model=None):
    if not emails: return []
    client = _get_groq_client()
    
    # Use lighter model by default to avoid Rate Limits (429)
    # llama-3.1-8b-instant is faster and has higher limits than 70b
    model_id = custom_model if custom_model else "llama-3.1-8b-instant"
    
    batch_text = "ANALYZE THESE EMAILS:\n"
    for i, e in enumerate(emails):
        # Pass ID to map back. Truncate body strictly (800 chars) to save tokens.
        body_clean = (e.get('body', '') or '')[:800]
        batch_text += f"ID: {e['id']} | FROM: {e['sender']} | SUBJ: {e['subject']} | BODY: {body_clean}\n---\n"

    prompt = PROMPT_EMAIL_ANALYSIS.format(current_date=datetime.datetime.now().strftime("%Y-%m-%d"))

    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": batch_text}
            ],
            model=model_id,
            temperature=0.1,
            max_tokens=2048
        )
        content = _clean_json_output(completion.choices[0].message.content.strip())
        
        results = json.loads(content) # clean_json always returns valid JSON string now
        if isinstance(results, dict): results = [results]
        
        # --- DEBUG FOR "NO EVENTS" ISSUE ---
        if not results:
             st.warning("⚠️ DEBUG: La IA devolvió 0 elementos.")
             with st.expander("Ver Respuesta Cruda de la IA (Debug)"):
                 st.text(completion.choices[0].message.content)
        # -----------------------------------
        
        return results
    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg or "rate limit" in err_msg.lower():
            st.error("📉 Límite de uso de IA alcanzado (Rate Limit).")
            st.warning("Hemos cambiado a un modelo más ligero (8b) para evitar esto, pero si persiste, espera unos minutos.")
            st.info("Tip: Reduce la cantidad de correos a analizar en la barra lateral.")
        else:
            st.error(f"AI Email Error: {e}")
        return []

def analyze_existing_events_ai(events_list):
    client = _get_groq_client()
    simplified_events = [{"id": e['id'], "summary": e.get('summary', 'Sin Título'), "start": e['start']} for e in events_list]
    
    system_prompt = """
    You are an Elite Executive Assistant. Your job is to OPTIMIZE the user's calendar.
    OUTPUT FORMAT (JSON):
    {
        "optimization_plan": {
            "event_id_1": {"new_summary": "...", "colorId": "..."},
            ...
        },
        "advisor_note": "..."
    }
    LANGUAGE: SPANISH.
    """
    
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(simplified_events)}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=4000
        )
        content = _clean_json_output(completion.choices[0].message.content.strip())
        return json.loads(content)
    except Exception as e:
        st.error(f"AI Assistant Error: {e}")
        return {}

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
        return json.loads(content)
    except Exception as e:
        st.error(f"AI Planning Error: {e}")
        return {}

def generate_project_breakdown_ai(project_title, project_desc, start_date, end_date, extra_context=""):
    client = _get_groq_client()
    
    context_block = f"Extra Context/Docs: {extra_context}" if extra_context else ""

    system_prompt = f"""
    You are an Expert Project Manager using Qwen Intelligence.
    Goal: Break down the project "{project_title}" into actionable Daily/Weekly tasks.
    Context: {start_date} to {end_date}
    Desc: {project_desc}
    {context_block}
    
    Output: JSON List of objects ({{"title": "", "date": "YYYY-MM-DD", "notes": ""}}).
    Language: Spanish.
    """
    
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Generate Breakdown taking into account the context if provided."}
            ],
            model="qwen/qwen3-32b", 
            temperature=0.6, 
            max_tokens=4096
        )
        content = _clean_json_output(completion.choices[0].message.content.strip())
        return json.loads(content)
    except Exception as e:
        st.error(f"AI Breakdown Error (Qwen): {e}")
        return []
