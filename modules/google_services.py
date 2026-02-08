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
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/documents'
]

# Google Calendar Color IDs
COLOR_MAP = {
    "1": "Lavanda (General/Otros)",
    "2": "Salvia (Planificación/Estrategia)",
    "3": "Uva (Proyectos Esp)",
    "4": "Flamenco (Reuniones Int)",
    "5": "Banana (Brainstorming/Ideas)",
    "6": "Mandarina (Reuniones Ext/Clientes)",
    "7": "Pavo Real (Trabajo Operativo)",
    "8": "Grafito (Admin/Logística)",
    "9": "Arándano (Deporte/Personal)",
    "10": "Albahaca (Balance/Salud)",
    "11": "Tomate (URGENTE/Crítico)"
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
    print(f"DEBUG: get_calendar_service called (force_sa={force_service_account})")
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

def get_calendar_list(service):
    """Returns a list of calendars (id, summary, primary)."""
    try:
        page_token = None
        calendar_list = []
        while True:
            calendar_list_entry = service.calendarList().list(pageToken=page_token).execute()
            for calendar_list_entry_item in calendar_list_entry['items']:
                calendar_list.append({
                    'id': calendar_list_entry_item['id'],
                    'summary': calendar_list_entry_item['summary'],
                    'primary': calendar_list_entry_item.get('primary', False)
                })
            page_token = calendar_list_entry.get('nextPageToken')
            if not page_token:
                break
        return calendar_list
    except Exception as e:
        print(f"Error checking calendar access: {e}")
        return False

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

def get_docs_service():
    """Authenticates and returns the Google Docs service."""
    if 'docs_service' not in st.session_state:
        try:
            # Reuse existing credentials logic
            creds = _load_service_account_creds()
            if not creds:
                creds = get_gmail_credentials()
                
            if creds:
                service = build('docs', 'v1', credentials=creds, cache_discovery=False)
                st.session_state.docs_service = service
                return service
        except Exception as e:
            st.error(f"Failed to authenticate Docs: {e}")
            return None
    return st.session_state.docs_service

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

    print("DEBUG: Starting get_gmail_credentials")
    creds = None
    # 1. Try to load token from Session State
    if 'google_token' in st.session_state:
        print("DEBUG: Found google_token in session_state")
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
        print("DEBUG: No valid creds, starting new login flow check")
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

def create_draft(service, user_id, message_body, to_email=None, subject="(Sin asunto)"):
    """
    Creates a draft email with proper RFC 2822 formatting.
    Args:
        service: Gmail API service instance
        user_id: User ID ('me' for authenticated user)
        message_body: Plain text body of the email
        to_email: Recipient email (optional, can be empty for draft)
        subject: Email subject line
    """
    try:
        from email.mime.text import MIMEText
        import base64
        
        # Create a MIMEText object
        message = MIMEText(message_body, 'plain', 'utf-8')
        message['subject'] = subject
        
        if to_email:
            # Clean and validate recipient
            to_clean = to_email.strip()
            if '@' in to_clean and '.' in to_clean:
                message['to'] = to_clean
            else:
                print(f"Warning: Invalid email format '{to_email}'. Creating draft without recipient.")
        
        # Encode the message in base64
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Create draft
        draft_body = {'message': {'raw': raw_message}}
        draft = service.users().drafts().create(userId=user_id, body=draft_body).execute()
        return draft
    except Exception as e:
        print(f"Error creating draft: {e}")
        import traceback
        traceback.print_exc()
        return None

def modify_message_labels(service, user_id, msg_id, add_ids=[], remove_ids=[]):
    """Modifies labels of a message (e.g., Archive = remove INBOX)."""
    try:
        body = {'addLabelIds': add_ids, 'removeLabelIds': remove_ids}
        message = service.users().messages().modify(userId=user_id, id=msg_id, body=body).execute()
        return message
    except Exception as e:
        print(f"Error modifying labels: {e}")
        return None

def archive_message(service, user_id, msg_id):
    """Archives a message by removing the INBOX label."""
    return modify_message_labels(service, user_id, msg_id, remove_ids=['INBOX'])

def get_or_create_label(service, user_id, label_name):
    """Gets label ID by name or creates it if missing."""
    try:
        # List labels
        results = service.users().labels().list(userId=user_id).execute()
        labels = results.get('labels', [])
        
        for label in labels:
            if label['name'].lower() == label_name.lower():
                return label['id']
        
        # Create if not found
        label_object = {
            'name': label_name,
            'labelListVisibility': 'labelShow',
            'messageListVisibility': 'show'
        }
        created_label = service.users().labels().create(userId=user_id, body=label_object).execute()
        return created_label['id']
    except Exception as e:
        print(f"Error managing label {label_name}: {e}")
        return None

def archive_old_emails(service, hours_old=720):
    """Archives 'Promotions' older than X hours (default 30 days)."""
    try:
        # Calculate date
        cutoff = datetime.datetime.now() - datetime.timedelta(hours=hours_old)
        date_str = cutoff.strftime('%Y/%m/%d')
        
        # Query: category:promotions AND before:YYYY/MM/DD AND in:inbox
        query = f"category:promotions before:{date_str} in:inbox"
        
        # List messages (up to 500 at a time)
        results = service.users().messages().list(userId='me', q=query, maxResults=500).execute()
        messages = results.get('messages', [])
        
        if not messages:
            return 0
            
        # Batch Modify
        msg_ids = [m['id'] for m in messages]
        body = {'removeLabelIds': ['INBOX']}
        service.users().messages().batchModify(userId='me', body={'ids': msg_ids, 'removeLabelIds': ['INBOX']}).execute()
        
        return len(msg_ids)
    except Exception as e:
        print(f"Error bulk archiving: {e}")
        return -1

def setup_gtd_labels(service, user_id='me'):
    """Ensures GTD label hierarchy exists."""
    labels = ["@GTD/1-Acción", "@GTD/2-Espera", "@GTD/3-Leer", "@GTD/4-Fiscal"]
    ids = {}
    for lbl in labels:
        lid = get_or_create_label(service, user_id, lbl)
        if lid: ids[lbl] = lid
    return ids

def auto_tag_gtd(service, email_results, user_id='me'):
    """Applies GTD labels based on AI analysis."""
    try:
        label_map = setup_gtd_labels(service, user_id)
        
        # Mapping AI Category -> GTD Label
        # AI Categories (from prompt): Solicitud, Información, Pagos, Reunión, Otro
        cat_map = {
            "Solicitud": "@GTD/1-Acción",
            "Reunión": "@GTD/1-Acción", # Meetings require action (scheduling)
            "Pagos": "@GTD/4-Fiscal",
            "Información": "@GTD/3-Leer",
            "Otro": "@GTD/3-Leer"
        }
        
        # Also check Urgency
        
        count = 0
        for ev in email_results:
            cat = ev.get('category', 'Otro')
            urg = ev.get('urgency', 'Baja')
            
            target_label_name = cat_map.get(cat, "@GTD/3-Leer")
            
            # Override for High Urgency
            if urg == 'Alta':
                target_label_name = "@GTD/1-Acción"
                
            label_id = label_map.get(target_label_name)
            
            if label_id and ev.get('id'):
                # Apply Label
                modify_message_labels(service, user_id, ev['id'], add_ids=[label_id])
                count += 1
        
        return count
    except Exception as e:
        print(f"Error Auto-Tagging: {e}")
        return 0


def delete_events_bulk(service, calendar_id, start_date, end_date):
    """Deletes events within a range."""
    try:
        # ISO format with timezone (Z for UTC or just straight ISO)
        t_min = datetime.datetime.combine(start_date, datetime.time.min).isoformat() + 'Z'
        t_max = datetime.datetime.combine(end_date, datetime.time.max).isoformat() + 'Z'
        
        # List events
        events_result = service.events().list(
            calendarId=calendar_id, 
            timeMin=t_min, 
            timeMax=t_max, 
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        
        count = 0
        for event in events:
            try:
                service.events().delete(calendarId=calendar_id, eventId=event['id']).execute()
                count += 1
                # Rate limit safety
                if count % 10 == 0: time.sleep(0.5)
            except: pass
            
        return count
    except Exception as e:
        return f"Error: {e}"

def delete_tasks_bulk(service, tasklist_id, start_date=None, end_date=None, delete_all=False):
    """Deletes tasks. Optionally filtered by due date."""
    try:
        # List all tasks
        results = service.tasks().list(tasklist=tasklist_id, showHidden=True).execute()
        tasks = results.get('items', [])
        
        count = 0
        deleted = 0
        
        for t in tasks:
            should_delete = False
            if delete_all:
                should_delete = True
            elif start_date and end_date:
                # Check Due Date
                due_str = t.get('due')
                if due_str:
                    # Parse ISO
                    try:
                        # Handle '2023-10-25T12:00:00.000Z'
                        due_dt = datetime.datetime.fromisoformat(due_str.replace('Z', '+00:00')).date()
                        if start_date <= due_dt <= end_date:
                            should_delete = True
                    except: pass
            
            if should_delete:
                try:
                    service.tasks().delete(tasklist=tasklist_id, task=t['id']).execute()
                    deleted += 1
                    if deleted % 10 == 0: time.sleep(0.5)
                except: pass
                
        return deleted
    except Exception as e:
        return f"Error: {e}"

def get_task_lists(service):
    """Returns a list of task lists."""
    retries = 3
    for attempt in range(retries):
        try:
            results = service.tasklists().list(maxResults=10).execute()
            items = results.get('items', [])
            return items
        except Exception as e:
            err_str = str(e).lower()
            if "broken pipe" in err_str or "ssl" in err_str or "connection" in err_str or "500" in err_str or "503" in err_str:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
            
            if attempt == retries - 1:
                st.error(f"Error fetching task lists: {e}")
                return []
    return []

def create_task_list(service, title):
    """Creates a new task list."""
    retries = 3
    for attempt in range(retries):
        try:
            tasklist = {'title': title}
            result = service.tasklists().insert(body=tasklist).execute()
            return result['id']
        except Exception as e:
            err_str = str(e).lower()
            if "broken pipe" in err_str or "ssl" in err_str or "connection" in err_str or "500" in err_str or "503" in err_str:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
            
            if attempt == retries - 1:
                st.error(f"Error creating task list: {e}")
                return None
    return None

def add_task_to_google(service, tasklist_id, title, notes=None, due_date=None, start_date=None, parent=None):
    """Adds a task to the specified list with optional start and due dates."""
    print(f"DEBUG: add_task_to_google called for title='{title}'")
    try:
        task = {
            'title': title,
            'notes': notes
        }
        
        # Add START date if provided (Google Tasks API supports 'start' field)
        if start_date:
            # Use same RFC 3339 format as due_date
            if hasattr(start_date, 'date'):
                s_str = start_date.date().isoformat()
            else:
                s_str = str(start_date)[:10] # Ensure YYYY-MM-DD
            
            task['start'] = f"{s_str}T12:00:00.000Z"
        
        # Add DUE date if provided
        if due_date:
            # Google Tasks 'due' field is strict RFC 3339 timestamp.
            # To avoid timezone shifts (e.g. 00:00 UTC -> previous day in Chile),
            # we set it to 12:00:00 UTC (Noon) which safely lands on the correct day globally.
            if hasattr(due_date, 'date'):
                d_str = due_date.date().isoformat()
            else:
                d_str = str(due_date)[:10] # Ensure YYYY-MM-DD
            
            task['due'] = f"{d_str}T12:00:00.000Z"
        
        if parent:
            task['parent'] = parent
            
        # Retry Logic
        retries = 3
        for attempt in range(retries):
            try:
                result = service.tasks().insert(tasklist=tasklist_id, body=task).execute()
                return result
            except Exception as e:
                # Check for transient errors
                err_str = str(e).lower()
                if "broken pipe" in err_str or "ssl" in err_str or "connection" in err_str or "500" in err_str or "503" in err_str:
                    if attempt < retries - 1:
                        time.sleep(2 ** attempt) # 1s, 2s, 4s
                        continue
                
                # If not retryable or out of retries
                if attempt == retries - 1:
                     st.error(f"Error adding task after {retries} attempts: {e}")
                     return None
        return None
    except Exception as e:
        st.error(f"Error adding task: {e}")
        return None

def delete_task_google(service, tasklist_id, task_id):
    """Deletes a task from the specified list."""
    print(f"DEBUG: delete_task_google called for id='{task_id}'")
    retries = 3
    for attempt in range(retries):
        try:
            service.tasks().delete(tasklist=tasklist_id, task=task_id).execute()
            return True
        except Exception as e:
            err_str = str(e).lower()
            if "broken pipe" in err_str or "ssl" in err_str or "connection" in err_str or "500" in err_str or "503" in err_str:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue

            # If it's a 404, consider it success (already deleted)
            if "404" in str(e) or "notFound" in str(e):
                return True
                
            if attempt == retries - 1:
                st.error(f"Error deleting task: {e}")
                return False
    return False

def update_task_google(service, tasklist_id, task_id, title=None, notes=None, status=None, due=None):
    """Updates an existing task."""
    retries = 3
    for attempt in range(retries):
        try:
            # First get the existing task to preserve other fields
            # We also wrap the 'get' in the retry logic implicitly by restarting the loop if it fails? 
            # Ideally we want granular retries but simplistic block retry is safer for consistency.
            
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
            err_str = str(e).lower()
            if "broken pipe" in err_str or "ssl" in err_str or "connection" in err_str or "500" in err_str or "503" in err_str:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
            
            if attempt == retries - 1:
                st.error(f"Error updating task: {e}")
                return None
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

        # Check for nested start/end (Google API extraction format)
        if not start_time and 'start' in event_data:
             start_time = event_data['start'].get('dateTime', event_data['start'].get('date'))
        if not end_time and 'end' in event_data:
             end_time = event_data['end'].get('dateTime', event_data['end'].get('date'))

        if not start_time:
             # AUTO-FIX: Default to Tomorrow 9:00 AM if missing
             import datetime as dt
             tomorrow = dt.date.today() + dt.timedelta(days=1)
             start_time = f"{tomorrow.isoformat()}T09:00:00"
             description = f"[FECHA AUTOMÁTICA] La IA no detectó fecha exacta.\n\n{description}"
             st.toast(f"⚠️ Fecha faltante corregida a {start_time}")

        # Ensure strings
        if not isinstance(start_time, str): start_time = start_time.isoformat()
        
        # Auto-calculate end_time if missing (Default: 1 hour)
        if not end_time:
             try:
                 import datetime as dt
                 # Parse start_time to add delta
                 if 'T' in start_time:
                     s_dt = dt.datetime.fromisoformat(start_time)
                     e_dt = s_dt + dt.timedelta(hours=1)
                     end_time = e_dt.isoformat()
                 else:
                     # Fallback for date-only strings (though less common for specific times)
                     end_time = start_time 
             except:
                 return False, "Error calculando fecha fin automática."
        
        if not isinstance(end_time, str): end_time = end_time.isoformat()

        event_body = {
            'summary': summary,
            'start': {'dateTime': start_time, 'timeZone': 'America/Santiago'}, 
            'end': {'dateTime': end_time, 'timeZone': 'America/Santiago'},
            'description': description,
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 30},
                    {'method': 'popup', 'minutes': 1440} # 24 hours
                ]
            }
        }
        

        
        # Simple heuristic: If string doesn't have Z or offset, assume it needs a specific TZ
        # For now we stick to UTC to match previous behavior or simple pass-through
        
        if color_id:
            event_body['colorId'] = color_id
            
        # Transparency (Availability Control)
        # 'opaque' = Busy (Default), 'transparent' = Free/Available
        transparency = event_data.get('transparency')
        if transparency:
            event_body['transparency'] = transparency
            
        # Recurrence Support
        recurrence = event_data.get('recurrence')
        if recurrence and isinstance(recurrence, list):
            event_body['recurrence'] = recurrence
            
        created_event = service.events().insert(calendarId=calendar_id, body=event_body).execute()
        event_id = created_event.get('id', '')
        return True, f"Evento creado. ID: {event_id}"

    except Exception as e:
        # Fallback: Try with Service Account (Robot) if User fails (403/404)
        error_str = str(e)
        if "403" in error_str or "404" in error_str:
            print(f"User auth failed for {calendar_id}. Retrying with Service Account...")
            try:
                # Force load SA
                creds_sa = _load_service_account_creds()
                if creds_sa:
                    service_sa = build('calendar', 'v3', credentials=creds_sa, cache_discovery=False)
                    created_event = service_sa.events().insert(calendarId=calendar_id, body=event_body).execute()
                    event_id = created_event.get('id', '')
                    return True, f"Evento creado (Robot). ID: {event_id}"
            except Exception as e_sa:
                return False, f"Fallo User y Robot: {e_sa}"
        
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
        # Ensure we produce an offset-aware ISO string
        time_min_dt = new_start_dt - dt.timedelta(days=1)
        time_max_dt = new_start_dt + dt.timedelta(days=1)
        
        # If naive, make it aware (local) or UTC
        if not time_min_dt.tzinfo:
            time_min_dt = time_min_dt.astimezone()
        if not time_max_dt.tzinfo:
            time_max_dt = time_max_dt.astimezone()
            
        time_min = time_min_dt.isoformat()
        time_max = time_max_dt.isoformat()
        
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
                # Ensure existing is aware
                if 'T' in existing_start_raw:
                     # If replace('Z',...) works it's usually UTC, but if naive needs .astimezone()
                     existing_start_dt = dt.datetime.fromisoformat(existing_start_raw.replace('Z', '+00:00'))
                     if not existing_start_dt.tzinfo:
                         existing_start_dt = existing_start_dt.astimezone()
                else: 
                     existing_start_dt = dt.datetime.fromisoformat(existing_start_raw).astimezone()
            except:
                continue
            
            # Ensure new event is aware/consistent BEFORE math
            match_new_start = new_start_dt
            if not match_new_start.tzinfo:
                match_new_start = match_new_start.astimezone()

            # Similarity check
            title_similarity = SequenceMatcher(None, new_summary, existing_summary).ratio()
            
            # Use abs difference
            time_diff = abs((match_new_start - existing_start_dt).total_seconds() / 60)
            
            if title_similarity > 0.8 and time_diff <= 30:
                return True  # Duplicate found
        
        return False  # No duplicate
        
    except Exception as e:
        # If check fails (e.g. 404 Not Found due to invalid email), allow creation (fail-open)
        if "404" in str(e) or "notFound" in str(e):
             print(f"DEBUG: 404 in check_event_exists for {calendar_id}. Treating as no duplicate.")
             return False

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
        
        # Color ID Validation (1-11 are valid standard colors)
        img_valid_colors = [str(i) for i in range(1, 12)]
        if color_id:
             if str(color_id) in img_valid_colors:
                 event['colorId'] = str(color_id)
             else:
                 print(f"Warning: Invalid colorId '{color_id}' ignored.")
        
        
        if start_time and end_time:
            # Handle both datetime objects and ISO strings
            s_iso = start_time.isoformat() if hasattr(start_time, 'isoformat') else start_time
            e_iso = end_time.isoformat() if hasattr(end_time, 'isoformat') else end_time
            
            event['start'] = {'dateTime': s_iso, 'timeZone': 'America/Santiago'}
            event['end'] = {'dateTime': e_iso, 'timeZone': 'America/Santiago'}
            
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

# --- DEDUPLICATION HELPERS ---

def deduplicate_calendar_events(service, calendar_id, start_date=None, end_date=None):
    """
    Removes duplicate events based on (summary, start_time).
    Respects the provided date range (default: last 30 days).
    """
    try:
        import datetime as dt
        
        # Default window: Last 30 days to Next 365 days if no range provided
        if not start_date:
            start_date = dt.date.today() - dt.timedelta(days=30)
        if not end_date:
            end_date = dt.date.today() + dt.timedelta(days=365)
            
        t_min = dt.datetime.combine(start_date, dt.time.min).isoformat() + 'Z'
        t_max = dt.datetime.combine(end_date, dt.time.max).isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId=calendar_id, 
            timeMin=t_min, 
            timeMax=t_max, 
            singleEvents=True, 
            orderBy='startTime',
            maxResults=2500 # Reasonable limit
        ).execute()
        
        events = events_result.get('items', [])
        deleted_count = 0
        
        # Group by hash key: (summary_lower, start_time)
        seen = {}
        for ev in events:
            summary = ev.get('summary', '').strip().lower()
            start = ev.get('start', {}).get('dateTime') or ev.get('start', {}).get('date')
            
            if not summary or not start: continue
            
            key = (summary, start)
            
            if key in seen:
                # Duplicate found! Delete this one.
                try:
                    service.events().delete(calendarId=calendar_id, eventId=ev['id']).execute()
                    deleted_count += 1
                except: pass
            else:
                seen[key] = True
                
        return deleted_count
    except Exception as e:
        st.error(f"Error deduplicating events: {e}")
        return 0

def deduplicate_tasks(service):
    """
    Removes duplicate tasks based on (title, due, list_id).
    """
    try:
        deleted_count = 0
        tasklists = get_task_lists(service)
        
        for tl in tasklists:
            # Get all tasks for this list
            results = service.tasks().list(tasklist=tl['id'], showCompleted=False, maxResults=100).execute()
            tasks = results.get('items', [])
            
            seen = {}
            for t in tasks:
                title = t.get('title', '').strip().lower()
                due = t.get('due', 'no-due')
                
                if not title: continue
                
                key = (title, due)
                
                if key in seen:
                    # Duplicate!
                    try:
                        service.tasks().delete(tasklist=tl['id'], task=t['id']).execute()
                        deleted_count += 1
                    except: pass
                else:
                    seen[key] = True
                    
        return deleted_count
    except Exception as e:
        st.error(f"Error deduplicating tasks: {e}")
        return 0

# --- DOCS GENERATION (ACTAS) ---

def create_meeting_minutes_doc(title, data):
    """
    Creates a Google Doc with the specific Health Service Meeting Minutes format.
    Args:
        title (str): Document title
        data (dict): JSON data from AI generation
    Returns:
        str: URL of the created document or None
    """
    service = get_docs_service()
    if not service: return None
    
    try:
        # 1. Create Blank Doc
        doc = service.documents().create(body={'title': title}).execute()
        doc_id = doc.get('documentId')
        
        requests = []
        
        # HEADER
        header_text = f"IDENTIFICACIÓN DEL PRESTADOR\\nCENTRO DE SALUD: [Institución]\\nACTA DE REUNIÓN: {data.get('asunto', 'Sin Asunto')}\\nFECHA: {data.get('fecha', '')} | HORA: {data.get('hora_inicio')} - {data.get('hora_termino')}\\n________________________________________________________________________________\\n\\n"
        
        # 1. ANTECEDENTES
        sec1_title = "1. ANTECEDENTES GENERALES\\n"
        sec1_body = f"• ASUNTO: {data.get('asunto')}\\n• LUGAR: {data.get('lugar')}\\n\\n"
        
        # 2. ASISTENTES
        sec2_title = "2. ASISTENTES\\n"
        att_body = ""
        for p in data.get('asistentes', []):
            att_body += f"• {p}\\n"
        att_body += "\\n"
        
        # 3. ORDEN DEL DÍA
        sec3_title = "3. ORDEN DEL DÍA\\n"
        points_body = ""
        for i, p in enumerate(data.get('tabla_puntos', [])):
            points_body += f"{i+1}. {p}\\n"
        points_body += "\\n"
        
        # 4. DESARROLLO
        sec4_title = "4. DESARROLLO DE LA SESIÓN\\n"
        dev_body = f"{data.get('desarrollo', '')}\\n\\n"
        
        # 5. ACUERDOS
        sec5_title = "5. ACUERDOS Y COMPROMISOS\\n"
        ac_body = "ACUERDO | RESPONSABLE | PLAZO\\n"
        ac_body += "--------------------------------------------------------\\n"
        for ac in data.get('acuerdos', []):
            ac_body += f"{ac.get('descripcion')} | {ac.get('responsable')} | {ac.get('plazo')}\\n"
        ac_body += "--------------------------------------------------------\\n\\n"
        
        # 6. SIGNATURES
        sig_body = "\\n\\n__________________________          __________________________\\nEncargado de Reunión                     Secretario de Actas\\n"
        
        # Concatenate All
        full_text = header_text + sec1_title + sec1_body + sec2_title + att_body + sec3_title + points_body + sec4_title + dev_body + sec5_title + ac_body + sig_body
        
        # Insert All Text at Index 1
        requests.append({'insertText': {'location': {'index': 1}, 'text': full_text}})
        
        # CALCULATE RANGES FOR STYLING (Sequential)
        current_index = 1
        
        # Style Header (Bold)
        len_header = len(header_text)
        requests.append({
            'updateTextStyle': {
                'range': {'startIndex': current_index, 'endIndex': current_index + len_header},
                'textStyle': {'bold': True, 'fontSize': {'magnitude': 10, 'unit': 'PT'}},
                'fields': 'bold,fontSize'
            }
        })
        current_index += len_header
        
        # Style Sec 1 Title (Bold + Color)
        len_sec1_title = len(sec1_title)
        requests.append({
            'updateTextStyle': {
                'range': {'startIndex': current_index, 'endIndex': current_index + len_sec1_title},
                'textStyle': {'bold': True, 'foregroundColor': {'color': {'rgbColor': {'red': 0.1, 'green': 0.1, 'blue': 0.6}}}},
                'fields': 'bold,foregroundColor'
            }
        })
        current_index += len_sec1_title + len(sec1_body)
        
        # Style Sec 2 Title
        len_sec2_title = len(sec2_title)
        requests.append({
            'updateTextStyle': {
                'range': {'startIndex': current_index, 'endIndex': current_index + len_sec2_title},
                'textStyle': {'bold': True},
                'fields': 'bold'
            }
        })
        current_index += len_sec2_title + len(att_body)

        # Style Sec 3 Title
        len_sec3_title = len(sec3_title)
        requests.append({
            'updateTextStyle': {
                'range': {'startIndex': current_index, 'endIndex': current_index + len_sec3_title},
                'textStyle': {'bold': True},
                'fields': 'bold'
            }
        })
        current_index += len_sec3_title + len(points_body)
        
        # Style Sec 4 Title
        len_sec4_title = len(sec4_title)
        requests.append({
            'updateTextStyle': {
                'range': {'startIndex': current_index, 'endIndex': current_index + len_sec4_title},
                'textStyle': {'bold': True},
                'fields': 'bold'
            }
        })
        current_index += len_sec4_title + len(dev_body)
        
        # Style Sec 5 Title
        len_sec5_title = len(sec5_title)
        requests.append({
            'updateTextStyle': {
                'range': {'startIndex': current_index, 'endIndex': current_index + len_sec5_title},
                'textStyle': {'bold': True},
                'fields': 'bold'
            }
        })
        
        # EXECUTE BATCH
        service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
        
        return f"https://docs.google.com/document/d/{doc_id}/edit", None
        
    except Exception as e:
        print(f"Error generating Doc: {e}")
        return None, str(e)


# --- VOICE ANALYST EXECUTION ---

def execute_voice_action(action_data):
    """
    Executes a single action defined by the Voice Analyst AI.
    Args:
        action_data (dict): {'action': '...', 'params': {...}}
    Returns:
        tuple: (bool success, str message)
    """
    action = action_data.get('action')
    params = action_data.get('params', {})
    
    try:
        if action == "create_event":
            # Map params to function args
            # add_event_to_calendar expects: service, summary, start_time, end_time, description=None
            # We need to get service here or passed? 
            # Better to use the wrapper that handles auth internally if possible, 
            # but add_event_to_calendar takes 'service' as arg.
            
            calendar_service = get_calendar_service()
            if not calendar_service: return False, "Error de autenticación Calendario"
            
            # Extract
            summary = params.get('summary')
            start = params.get('start_time')
            end = params.get('end_time')
            desc = params.get('description', '')
            
            # Default to 1 hour if end missing
            if start and not end:
                # Logic handled inside? No, let's parse.
                # Actually, add_event_to_calendar handles ISO strings.
                pass 
                
            # Call
            created_event = add_event_to_calendar(calendar_service, summary, start, end, desc)
            if created_event:
                return True, f"Evento creado: {summary}"
            else:
                return False, "Falló la creación del evento"

        elif action == "create_task":
            # create_task(title, notes=None, due=None)
            title = params.get('title')
            due = params.get('due_date')
            
            res = create_task(title, due=due) # notes? 
            if res: return True, f"Tarea creada: {title}"
            else: return False, "Falló la creación de tarea"
            
        elif action == "draft_email":
            # create_draft(service, user_id, message_body) -> needs MIME construction
            # We have 'create_draft' in this file?
            # Let's check...
            # We NEED a 'create_draft_simple' helper if not exists or use existing.
            
            gmail_service = get_gmail_service()
            if not gmail_service: return False, "Error autenticación Gmail"
            
            to = params.get('recipient', '')
            subject = params.get('subject', '(Sin Asunto)')
            body = params.get('body', '')
            
            # Construct message
            from email.mime.text import MIMEText
            import base64
            
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            try:
                draft = gmail_service.users().drafts().create(userId='me', body={'message': {'raw': raw}}).execute()
                return True, f"Borrador guardado: {subject}"
            except Exception as e:
                return False, str(e)

        return False, f"Acción desconocida: {action}"
        
    except Exception as e:
        return False, f"Error ejecución: {str(e)}"


# --- CALENDAR API: QUICK ADD & FREE/BUSY ---

def quick_add_event(service, text, calendar_id='primary'):
    """
    Creates an event from a simple text string using Calendar API quickAdd.
    Examples: "Reunión mañana 3pm", "Almuerzo viernes 1pm"
    
    Args:
        service: Google Calendar service instance
        text: Natural language text describing the event
        calendar_id: Calendar ID (default: 'primary')
    
    Returns:
        dict: Created event object or None if error
    """
    try:
        event = service.events().quickAdd(
            calendarId=calendar_id,
            text=text
        ).execute()
        
        return event
    except Exception as e:
        st.error(f"Error en quickAdd: {e}")
        return None


def get_free_busy(service, calendars, time_min, time_max):
    """
    Queries free/busy information for specified calendars.
    
    Args:
        service: Google Calendar service instance
        calendars: List of calendar IDs to query (e.g., ['primary', 'other@gmail.com'])
        time_min: Start time (ISO format string or datetime object)
        time_max: End time (ISO format string or datetime object)
    
    Returns:
        dict: Free/busy data with 'calendars' key containing busy blocks
    """
    try:
        # Convert datetime objects to ISO strings if needed
        if hasattr(time_min, 'isoformat'):
            time_min = time_min.isoformat() + 'Z'
        if hasattr(time_max, 'isoformat'):
            time_max = time_max.isoformat() + 'Z'
        
        body = {
            "timeMin": time_min,
            "timeMax": time_max,
            "items": [{"id": cal_id} for cal_id in calendars]
        }
        
        result = service.freebusy().query(body=body).execute()
        return result
    except Exception as e:
        st.error(f"Error consultando disponibilidad: {e}")
        return None


def get_calendar_colors(service):
    """
    Retrieves the color definitions for calendars and events.
    
    Returns:
        dict: Color definitions with 'event' and 'calendar' keys
    """
    try:
        colors = service.colors().get().execute()
        return colors
    except Exception as e:
        st.error(f"Error obteniendo colores: {e}")
        return None


# --- GMAIL API: LABELS & DRAFTS ---

def create_gmail_label(service, label_name, user_id='me'):
    """
    Creates a new Gmail label.
    
    Args:
        service: Gmail API service instance
        label_name: Name of the label to create
        user_id: User ID (default: 'me')
    
    Returns:
        dict: Created label object with 'id' and 'name'
    """
    try:
        label = {
            'name': label_name,
            'labelListVisibility': 'labelShow',
            'messageListVisibility': 'show'
        }
        
        result = service.users().labels().create(
            userId=user_id,
            body=label
        ).execute()
        
        return result
    except Exception as e:
        # Check if label already exists
        if '409' in str(e) or 'already exists' in str(e).lower():
            # Try to get existing label
            try:
                labels_result = service.users().labels().list(userId=user_id).execute()
                labels = labels_result.get('labels', [])
                for lbl in labels:
                    if lbl['name'] == label_name:
                        return lbl
            except:
                pass
        
        st.error(f"Error creando etiqueta: {e}")
        return None


def apply_gmail_label(service, message_id, label_id, user_id='me'):
    """
    Applies a label to a Gmail message.
    
    Args:
        service: Gmail API service instance
        message_id: ID of the message
        label_id: ID of the label to apply
        user_id: User ID (default: 'me')
    
    Returns:
        dict: Modified message object
    """
    try:
        result = service.users().messages().modify(
            userId=user_id,
            id=message_id,
            body={'addLabelIds': [label_id]}
        ).execute()
        
        return result
    except Exception as e:
        st.error(f"Error aplicando etiqueta: {e}")
        return None


def setup_ai_labels(service, user_id='me'):
    """
    Creates AI-related labels if they don't exist.
    Returns dict mapping label names to IDs.
    
    Labels:
        - 🤖 IA/Procesado: Emails processed by AI
        - ⏰ IA/Agenda: Emails converted to calendar events
        - ✅ IA/Tarea: Emails converted to tasks
    """
    ai_labels = {
        '🤖 IA/Procesado': None,
        '⏰ IA/Agenda': None,
        '✅ IA/Tarea': None
    }
    
    try:
        # Get existing labels
        labels_result = service.users().labels().list(userId=user_id).execute()
        labels = labels_result.get('labels', [])
        
        for label_name in ai_labels.keys():
            # Check if label exists
            found = False
            for lbl in labels:
                if lbl['name'] == label_name:
                    ai_labels[label_name] = lbl['id']
                    found = True
                    break
            
            # Create if missing
            if not found:
                new_label = create_gmail_label(service, label_name, user_id)
                if new_label:
                    ai_labels[label_name] = new_label['id']
        
        return ai_labels
    except Exception as e:
        st.error(f"Error configurando etiquetas IA: {e}")
        return ai_labels


def save_draft_from_ai(service, email_data, intent="Confirmar recepción", user_id='me'):
    """
    Generates a draft reply using AI and saves it to Gmail.
    
    Args:
        service: Gmail API service instance
        email_data: Dict with 'body', 'subject', 'sender', etc.
        intent: Reply intent (e.g., "Confirmar", "Reagendar", "Negociar")
        user_id: User ID (default: 'me')
    
    Returns:
        dict: Created draft object with 'id' field
    """
    from modules.ai_core import generate_reply_email
    
    try:
        # Generate draft content with AI
        email_body = email_data.get('body', '')
        draft_body = generate_reply_email(email_body, intent)
        
        # Extract subject (add Re: if not present)
        original_subject = email_data.get('subject', '(Sin asunto)')
        if not original_subject.lower().startswith('re:'):
            subject = f"Re: {original_subject}"
        else:
            subject = original_subject
        
        # Get recipient (reply to sender)
        to_email = email_data.get('sender', '')
        
        # Create draft
        draft = create_draft(service, user_id, draft_body, to_email, subject)
        
        return draft
    except Exception as e:
        st.error(f"Error generando borrador con IA: {e}")
        return None

def quick_add_event(service, text, calendarId='primary'):
    """
    Agrega un evento rápido usando procesamiento de lenguaje natural de Google.
    
    Args:
        service: Servicio de Google Calendar
        text: Texto del evento (ej: 'Reunión mañana a las 3pm')
        calendarId: ID del calendario destino (default: 'primary')
        
    Returns:
        dict: Objeto del evento creado o None si falla
    """
    try:
        created_event = service.events().quickAdd(
            calendarId=calendarId,
            text=text
        ).execute()
        return created_event
    except Exception as e:
        # Fallback Service Account
        error_str = str(e)
        if "403" in error_str or "404" in error_str:
            print(f"QuickAdd failed for {calendarId}. Retrying with Service Account...")
            try:
                # Force load SA
                creds_sa = _load_service_account_creds()
                if creds_sa:
                    from googleapiclient.discovery import build
                    service_sa = build('calendar', 'v3', credentials=creds_sa, cache_discovery=False)
                    created_event = service_sa.events().quickAdd(
                        calendarId=calendarId,
                        text=text
                    ).execute()
                    return created_event
            except: pass
            
        print(f"Error quick_add: {e}")
        return None