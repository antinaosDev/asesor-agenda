import os
import streamlit as st
import json
import datetime
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials as UserCredentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from bs4 import BeautifulSoup
import time

# --- CONSTANTS ---
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.modify',  # Changed from .readonly to allow label creation
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/spreadsheets'
]

# Google Calendar Color IDs
COLOR_MAP = {
    "1": "Lavanda (General/Otros)",
    "2": "Salvia (Intercultural)",
    "3": "Uva (Proyectos Esp)",
    "4": "Flamenco (Entrevistas)",
    "5": "Banana (MAIS)",
    "6": "Mandarina (Reuniones Ext)",
    "7": "Pavo Real (Trabajo Operativo)",
    "8": "Grafito (Admin/Logística)",
    "9": "Arándano (Deporte/Personal)",
    "10": "Albahaca (Salud)",
    "11": "Tomate (URGENTE)"
}

# --- SERVICE ACCOUNT HELPER ---
def _load_service_account_creds():
    """Loads Service Account credentials from available sources with priority."""
    # Priority 0: Session State (Hotfix/Already Loaded)
    if 'current_user_sa_creds' in st.session_state:
        try:
            return service_account.Credentials.from_service_account_info(
                st.session_state.current_user_sa_creds, scopes=SCOPES
            )
        except Exception:
            pass

    # Priority 1: From "user_data_full" in session (if not parsed yet)
    if 'user_data_full' in st.session_state:
        try:
            ud = st.session_state.user_data_full
            if 'clave_cuenta_servicio_admin' in ud:
                sa_raw = ud['clave_cuenta_servicio_admin']
                if isinstance(sa_raw, str) and sa_raw.strip():
                    if '""' in sa_raw: sa_raw = sa_raw.replace('""', '"')
                    sa_raw = sa_raw.strip()
                    if sa_raw.startswith('"') and sa_raw.endswith('"'): sa_raw = sa_raw[1:-1]
                    sa_info = json.loads(sa_raw)
                    st.session_state.current_user_sa_creds = sa_info # Cache it
                    return service_account.Credentials.from_service_account_info(
                        sa_info, scopes=SCOPES
                    )
        except Exception:
            pass

    # Priority 2: Local File
    if os.path.exists('service_account.json'):
        try:
            return service_account.Credentials.from_service_account_file(
                'service_account.json', scopes=SCOPES
            )
        except Exception:
            pass
            
    # Priority 3: Streamlit Secrets
    if "service_account" in st.secrets:
        try:
            sa_info = dict(st.secrets["service_account"])
            return service_account.Credentials.from_service_account_info(
                sa_info, scopes=SCOPES
            )
        except Exception:
            pass
            
    return None

# --- PUBLIC FUNCTIONS ---

def get_calendar_service(force_service_account=False):
    """Authenticates and returns the Google Calendar service."""
    if force_service_account:
        # Bypass cache and user creds, force Robot (SA)
        creds = _load_service_account_creds()
        if creds:
             return build('calendar', 'v3', credentials=creds, cache_discovery=False)
        return None

    if 'calendar_service' not in st.session_state:
        try:
            # 1. OAuth User (Prioritized)
            creds = get_gmail_credentials()

            # 2. Service Account (Fallback)
            if not creds:
                creds = _load_service_account_creds()
                
            if creds:
                service = build('calendar', 'v3', credentials=creds, cache_discovery=False)
                st.session_state.calendar_service = service
                return service
        except Exception as e:
            st.error(f"Failed to authenticate Calendar: {e}")
            return None
    return st.session_state.calendar_service

def get_tasks_service():
    """Authenticates and returns the Google Tasks service."""
    if 'tasks_service' not in st.session_state:
        try:
            # 1. OAuth User (Prioritized)
            creds = get_gmail_credentials()

            # 2. Service Account (Fallback)
            if not creds:
                creds = _load_service_account_creds()
                
            if creds:
                service = build('tasks', 'v1', credentials=creds, cache_discovery=False)
                st.session_state.tasks_service = service
                return service
        except Exception as e:
            st.error(f"Failed to authenticate Tasks: {e}")
            return None
    return st.session_state.tasks_service

def get_sheets_service():
    """Authenticates and returns the Google Sheets service."""
    if 'sheets_service' not in st.session_state:
        try:
            # 1. Service Account
            creds = _load_service_account_creds()
            
            # 2. OAuth User Fallback
            if not creds:
                creds = get_gmail_credentials()
                
            if creds:
                service = build('sheets', 'v4', credentials=creds, cache_discovery=False)
                st.session_state.sheets_service = service
                return service
        except Exception as e:
            st.error(f"Failed to authenticate Sheets: {e}")
            return None
    return st.session_state.sheets_service

def get_gmail_credentials():
    """Handles OAuth 2.0 Flow for User Data Access."""
    # 0. Check Logout Request
    if st.session_state.get('logout_google', False):
        if os.path.exists('token.pickle'):
            os.remove('token.pickle')
        if 'google_token' in st.session_state:
            del st.session_state.google_token
        if 'connected_email' in st.session_state:
            del st.session_state.connected_email
        st.session_state.logout_google = False
        return None

    creds = None
    # 1. Try to load token from Session State
    if 'google_token' in st.session_state:
        creds = st.session_state.google_token
        
    # 2. Try to load token from Google Sheets (Persistent Storage)
    elif 'user_data_full' in st.session_state and 'cod_val' in st.session_state.user_data_full:
         try:
             token_raw = st.session_state.user_data_full.get('cod_val')
             if token_raw and isinstance(token_raw, str) and token_raw.strip():
                 token_raw = token_raw.strip()
                 found_info = None
                 
                 # Attempt 1: Direct JSON parsing
                 try:
                     found_info = json.loads(token_raw)
                 except json.JSONDecodeError:
                     if token_raw.startswith('"') and token_raw.endswith('"'):
                         try: found_info = json.loads(token_raw[1:-1])
                         except: pass
                 
                 # Attempt 2: Handle CSV escaping
                 if not found_info and '""' in token_raw:
                     try:
                         cleaned = token_raw.replace('""', '"')
                         if cleaned.startswith('"') and cleaned.endswith('"'): cleaned = cleaned[1:-1]
                         found_info = json.loads(cleaned)
                     except: pass
                 
                 if found_info:
                     creds = UserCredentials.from_authorized_user_info(found_info, SCOPES)
                     st.session_state.google_token = creds # Save to session
                     st.toast("🔄 Sesión recuperada desde la nube")
         except Exception as e:
             st.error(f"Error crítico recuperando sesión: {e}")

    # 3. Refresh if expired
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            st.session_state.google_token = creds 
        except:
            creds = None

    # 4. New Login (If no valid creds found)
    if not creds or not creds.valid:
        # Load Client Config
        client_config = None
        
        # Priority 1: Custom Config
        if "custom_google_config" in st.session_state:
            try: client_config = json.loads(st.session_state.custom_google_config)
            except: pass

        # Priority 1.5: From Sheet (user_data_full) - FIX for Multi-Tenant OAuth
        # Priority 1.5: From Sheet (user_data_full) - FIX for Multi-Tenant OAuth
        if not client_config and 'user_data_full' in st.session_state:
             ud = st.session_state.user_data_full
             # Key from Sheet column: CREDENCIALES_AUTH_USER (lowercased)
             if 'credenciales_auth_user' in ud:
                 try:
                     raw = ud['credenciales_auth_user']
                     if raw and isinstance(raw, str) and raw.strip():
                         # Clean potential CSV formatting artifacts
                         cleaned = raw.strip()
                         if '""' in cleaned: cleaned = cleaned.replace('""', '"')
                         if cleaned.startswith('"') and cleaned.endswith('"'): cleaned = cleaned[1:-1]
                         
                         client_config = json.loads(cleaned)
                         st.toast("🔑 Config OAuth cargada OK desde Hoja.")
                 except Exception as e:
                     st.error(f"❌ Error crítico leyendo Credenciales de Hoja: {e}")
                     # Do NOT pass, fail loud so we don't fallback to broken files
                     pass
            
        # Priority 2: Secrets
        if not client_config and "google" in st.secrets:
            client_config = json.loads(st.secrets["google"]["client_config_json"]) if "client_config_json" in st.secrets["google"] else st.secrets["google"]
            
        # Priority 3: Local File (DISABLED/STRICT)
        # We suspect 'credentials.json' is the deleted client. Attempt to delete it or ignore it.
        elif not client_config and os.path.exists('credentials.json'):
            st.warning("⚠️ Se detectó 'credentials.json' local pero se ignorará para evitar conflictos con claves antiguas.")
            try:
                # Optional: aggressive cleanup
                # os.remove('credentials.json')
                pass
            except: pass
            
            # Uncomment to allow fallback if you are SURE it's correct
            # client_config = json.load(open('credentials.json'))
        
        if not client_config:
            # Only warn if we really need user creds (and don't have SA)
            st.error("❌ NO SE ENCONTRARON CREDENCIALES OAUTH VÁLIDAS.")
            st.info("Revisa la columna 'CREDENCIALES_AUTH_USER' en tu Google Sheet.")
            return None

        # Build Flow
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob' 

        st.warning("⚠️ **Autenticación requerida** (Para leer tu correo)")
        auth_url, _ = flow.authorization_url(prompt='consent')
        
        st.markdown(f"""
        1. [Haz clic aquí para autorizar en Google]({auth_url})
        2. Copia el código que aparece.
        3. Pégalo abajo 👇
        """)
        
        code = st.text_input("Ingresa el Código de Google:", key=f"auth_code_{hash(st.session_state.get('license_key', 'default'))}")
        
        if code:
            try:
                flow.fetch_token(code=code)
                creds = flow.credentials
                st.session_state.google_token = creds
                
                # --- AUTO SAVE TO SHEET ---
                if 'license_key' in st.session_state:
                     user = st.session_state.license_key
                     creds_json = creds.to_json()
                     with st.spinner("Guardando tu sesión para el futuro..."):
                         import modules.auth as auth_mod
                         if auth_mod.update_user_token(user, creds_json):
                             if 'user_data_full' in st.session_state:
                                  st.session_state.user_data_full['cod_val'] = creds_json
                             st.toast("✅ Sesión guardada.")
                
                # --- UPDATE UI EMAIL IMMEDIATELY ---
                try:
                    service = build('gmail', 'v1', credentials=creds)
                    profile = service.users().getProfile(userId='me').execute()
                    new_email = profile.get('emailAddress', 'Desconocido')
                    
                    # Force update ALL related keys so Sidebar widget syncs correctly
                    st.session_state.connected_email = new_email
                    st.session_state.connected_email_input = new_email
                except: pass
                # -----------------------------------

                st.success(f"✅ ¡Conectado como {new_email}! Recargando...")
                time.sleep(2)
                st.rerun()
            except Exception as e:
                st.error(f"Error de autenticación: {e}")
                return None
        else:
            st.stop()
    
    # 5. Extract Email for UI (ALWAYS, for any valid session)
    try:
        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()
        detected_email = profile.get('emailAddress', 'Desconocido')
        
        # Sync BOTH keys to ensure UI sidebar stays in sync
        st.session_state.connected_email = detected_email
        st.session_state.connected_email_input = detected_email
    except:
        pass

    return creds

def clean_email_body(html_content, max_chars=800):
    """Parses HTML and returns clean text, truncated for token savings."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        return text[:max_chars]
    except:
        return str(html_content)[:max_chars]

def fetch_emails_batch(service, start_date=None, end_date=None, max_results=15):
    """Fetches emails from inbox within a date range."""
    try:
        query_parts = ['-category:promotions', '-category:social']
        
        if start_date:
            query_parts.append(f"after:{start_date.strftime('%Y/%m/%d')}")
        if end_date:
            next_day = end_date + datetime.timedelta(days=1)
            query_parts.append(f"before:{next_day.strftime('%Y/%m/%d')}")
            
        query = " ".join(query_parts)
        
        results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
        messages = results.get('messages', [])
        
        email_data = []
        for msg in messages:
            try:
                msg_full = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
                payload = msg_full.get('payload', {})
                headers = payload.get('headers', [])
                
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "Sin Asunto")
                sender = next((h['value'] for h in headers if h['name'] == 'From'), "Desconocido")
                
                # Recursive Body Extraction
                def get_best_body(payload):
                    # 1. Plain Text at current level
                    if 'body' in payload and payload['body'].get('data'):
                        if payload.get('mimeType') == 'text/plain':
                            import base64
                            return base64.urlsafe_b64decode(payload['body']['data']).decode()
                    
                    # 2. Search in Parts
                    if 'parts' in payload:
                        # Prioritize text/plain
                        for part in payload['parts']:
                            if part['mimeType'] == 'text/plain' and part.get('body', {}).get('data'):
                                import base64
                                return base64.urlsafe_b64decode(part['body']['data']).decode()
                        
                        # Fallback to text/html
                        for part in payload['parts']:
                            if part['mimeType'] == 'text/html' and part.get('body', {}).get('data'):
                                import base64
                                html = base64.urlsafe_b64decode(part['body']['data']).decode()
                                return clean_email_body(html) # Helper we already have
                                
                        # Recursive deep dive if multipart
                        for part in payload['parts']:
                            if 'multipart' in part['mimeType']:
                                found = get_best_body(part)
                                if found: return found
                                
                    return None

                # Call extraction
                extracted_body = get_best_body(payload)
                body = extracted_body if extracted_body else "Sin contenido (Posible adjunto o imagen)"

                email_data.append({
                    "id": msg['id'],
                    "threadId": msg.get('threadId', msg['id']), # Add threadId, fallback to id
                    "subject": subject,
                    "sender": sender,
                    "body": clean_email_body(body)
                })
            except:
                pass 
        return email_data
    except Exception as e:
        st.error(f"Error Gmail: {e}")
        return []

def get_task_lists(service):
    """Returns a list of task lists."""
    try:
        results = service.tasklists().list(maxResults=10).execute()
        items = results.get('items', [])
        return items
    except Exception as e:
        st.error(f"Error fetching task lists: {e}")
        return []

def create_task_list(service, title):
    """Creates a new task list."""
    try:
        tasklist = {'title': title}
        result = service.tasklists().insert(body=tasklist).execute()
        return result['id']
    except Exception as e:
        st.error(f"Error creating task list: {e}")
        return None

def add_task_to_google(service, tasklist_id, title, notes=None, due_date=None, parent=None):
    """Adds a task to the specified list."""
    try:
        task = {
            'title': title,
            'notes': notes
        }
        if due_date:
            # Google Tasks expects RFC 3339 timestamp with proper format
            # The 'due' field specifically needs the date at midnight UTC
            if hasattr(due_date, 'date'):
                # If it's a datetime, extract just the date
                due_date = due_date.date()
            # Format as RFC 3339 date string (YYYY-MM-DD format, no time)
            task['due'] = due_date.isoformat() + 'T00:00:00.000Z'
        
        if parent:
            task['parent'] = parent
            
        result = service.tasks().insert(tasklist=tasklist_id, body=task).execute()
        return result
    except Exception as e:
        st.error(f"Error adding task: {e}")
        return None

def delete_task_google(service, tasklist_id, task_id):
    """Deletes a task from the specified list."""
    try:
        service.tasks().delete(tasklist=tasklist_id, task=task_id).execute()
        return True
    except Exception as e:
        st.error(f"Error deleting task: {e}")
        return False

def update_task_google(service, tasklist_id, task_id, title=None, notes=None, status=None, due=None):
    """Updates an existing task."""
    try:
        # First get the existing task to preserve other fields
        task = service.tasks().get(tasklist=tasklist_id, task=task_id).execute()
        
        if title: task['title'] = title
        if notes: task['notes'] = notes
        if status: task['status'] = status
        
        if due:
             task['due'] = due.isoformat() + 'Z'
        elif due == "": # Clear due date logic if needed, but for now basic update
             if 'due' in task: del task['due']

        result = service.tasks().update(tasklist=tasklist_id, task=task_id, body=task).execute()
        return result
    except Exception as e:
        st.error(f"Error updating task: {e}")
        return None

def get_existing_tasks_simple(service):
    """Fetches all tasks from all lists (simplified for AI context)."""
    retries = 3
    for attempt in range(retries):
        try:
            all_tasks = []
            tasklists = get_task_lists(service)
            for tl in tasklists:
                results = service.tasks().list(tasklist=tl['id'], showCompleted=False, maxResults=100).execute()
                tasks = results.get('items', [])
                for t in tasks:
                    all_tasks.append({
                        'id': t['id'],
                        'title': t['title'],
                        'list_id': tl['id'],
                        'list_title': tl['title'],
                        'due': t.get('due', 'No Due Date')
                    })
            return all_tasks
        except Exception as e:
            # Check for SSL or transient errors
            err_str = str(e).lower()
            if "ssl" in err_str or "connection" in err_str:
                if attempt < retries - 1:
                    time.sleep(1 * (attempt + 1))
                    continue
            st.error(f"Error fetching tasks after {retries} attempts: {e}")
            return []
    return []

def add_event_to_calendar(service, event_data, calendar_id='primary'):
    """Adds an event to Google Calendar. Expects event_data dict."""
    try:
        summary = event_data.get('summary', 'Sin Título')
        start_time = event_data.get('start_time')
        end_time = event_data.get('end_time')
        description = event_data.get('description', '')
        color_id = event_data.get('colorId')

        if not start_time or not end_time:
            return False, "Faltan fechas de inicio o fin."

        # Ensure strings
        if not isinstance(start_time, str): start_time = start_time.isoformat()
        if not isinstance(end_time, str): end_time = end_time.isoformat()

        event_body = {
            'summary': summary,
            'start': {'dateTime': start_time, 'timeZone': 'UTC'}, 
            'end': {'dateTime': end_time, 'timeZone': 'UTC'},
            'description': description
        }
        
        # Simple heuristic: If string doesn't have Z or offset, assume it needs a specific TZ
        # For now we stick to UTC to match previous behavior or simple pass-through
        
        if color_id:
            event_body['colorId'] = color_id
            
        created_event = service.events().insert(calendarId=calendar_id, body=event_body).execute()
        return True, "Evento creado exitosamente"
    except Exception as e:
        return False, str(e)


def check_event_exists(service, calendar_id, event_data):
    """
    Checks if a similar event already exists in the calendar.
    
    Args:
        service: Google Calendar service instance
        calendar_id: Calendar ID to search in
        event_data: Dict with 'summary', 'start_time', 'end_time'
    
    Returns:
        bool: True if duplicate found, False otherwise
    """
    try:
        import datetime as dt
        from difflib import SequenceMatcher
        
        # Extract new event data
        new_summary = event_data.get('summary', '').lower().strip()
        new_start = event_data.get('start_time')
        
        if not new_summary or not new_start:
            return False
        
        # Parse start time
        if isinstance(new_start, str):
            try:
                # Ensure it's a datetime object
                if 'T' in new_start:
                    new_start_dt = dt.datetime.fromisoformat(new_start.replace('Z', '+00:00'))
                else: 
                     # Handle simple date case or malformed
                     new_start_dt = dt.datetime.fromisoformat(new_start)
            except:
                # Fallback
                return False
        else:
            new_start_dt = new_start
        
        # Search window: ±1 day from event start
        # Use simple string manipulation to ensure "Z" is present if we treat them as UTC
        time_min_dt = new_start_dt - dt.timedelta(days=1)
        time_max_dt = new_start_dt + dt.timedelta(days=1)
        
        time_min = time_min_dt.isoformat().split('+')[0] + 'Z'
        time_max = time_max_dt.isoformat().split('+')[0] + 'Z'
        
        # Fetch existing events in time window
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime',
            maxResults=50
        ).execute()
        
        existing_events = events_result.get('items', [])
        
        # Check each existing event for similarity
        for event in existing_events:
            existing_summary = event.get('summary', '').lower().strip()
            existing_start_raw = event.get('start', {}).get('dateTime') or event.get('start', {}).get('date')
            
            if not existing_start_raw:
                continue
            
            try:
                existing_start_dt = dt.datetime.fromisoformat(existing_start_raw.replace('Z', '+00:00'))
            except:
                continue
            
            # Similarity check: Title match (>80%) + Time match (±30 min)
            title_similarity = SequenceMatcher(None, new_summary, existing_summary).ratio()
            time_diff = abs((new_start_dt - existing_start_dt).total_seconds() / 60)  # minutes
            
            if title_similarity > 0.8 and time_diff <= 30:
                return True  # Duplicate found
        
        return False  # No duplicate
        
    except Exception as e:
        # If check fails, allow creation (fail-open)
        st.warning(f"Error verificando duplicados: {e}")
        return False

def delete_event(service, event_id):
    """Deletes an event from the primary calendar."""
    try:
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return True
    except Exception as e:
        # If it's a 404 Not Found, strictly speaking it's already deleted, so we return True.
        if "404" in str(e) or "notFound" in str(e):
             return True
        st.error(f"Error deleting event: {e}")
        return False

def update_event_calendar(service, calendar_id, event_id, summary=None, description=None, start_time=None, end_time=None, color_id=None):
    """Updates an existing Google Calendar event."""
    try:
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        
        if summary: event['summary'] = summary
        if description: event['description'] = description
        if color_id: event['colorId'] = color_id
        
        if start_time and end_time:
            # Handle both datetime objects and ISO strings
            s_iso = start_time.isoformat() if hasattr(start_time, 'isoformat') else start_time
            e_iso = end_time.isoformat() if hasattr(end_time, 'isoformat') else end_time
            
            event['start'] = {'dateTime': s_iso, 'timeZone': 'UTC'} # UTC simplification
            event['end'] = {'dateTime': e_iso, 'timeZone': 'UTC'}
            
        updated_event = service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()
        return True, "Evento actualizado"
    except Exception as e:
        return False, str(e)

def optimize_event(service, calendar_id, event_id, new_summary=None, color_id=None):
    """Updates event details for Optimization Module."""
    # Wrapper around the robust update function
    ok, msg = update_event_calendar(service, calendar_id, event_id, summary=new_summary, color_id=color_id)
    if not ok:
        st.error(f"Error optimizing event: {msg}")
    return ok

# --- GMAIL LABELING HELPERS ---

def ensure_label(service, label_name):
    """
    Checks if a label exists, if not creates it.
    Returns the Label ID.
    Handles hierarchy (e.g. 'Parent/Child').
    """
    try:
        # List existing labels
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        
        # Check match
        for l in labels:
            if l['name'].lower() == label_name.lower():
                return l['id']
        
        # Create if missing
        label_object = {
            'name': label_name,
            'labelListVisibility': 'labelShow',
            'messageListVisibility': 'show'
        }
        created = service.users().labels().create(userId='me', body=label_object).execute()
        return created['id']
    except Exception as e:
        # Often fails if parent doesn't exist? Gmail API usually handles slashes automatically for hierarchy
        # But if error "Label name exists" or similar, just ignore
        print(f"Label Error ({label_name}): {e}")
        return None

def add_label_to_email(service, msg_id, label_id):
    """Adds a specific label to a message."""
    try:
        body = {
            'addLabelIds': [label_id],
            'removeLabelIds': []
        }
        service.users().messages().modify(userId='me', id=msg_id, body=body).execute()
        return True
    except Exception as e:
        print(f"Error labeling email {msg_id}: {e}")
        return False