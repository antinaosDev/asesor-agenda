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
    'https://www.googleapis.com/auth/gmail.readonly',
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

def get_calendar_service():
    """Authenticates and returns the Google Calendar service."""
    if 'calendar_service' not in st.session_state:
        try:
            # 1. Service Account
            creds = _load_service_account_creds()
            
            # 2. OAuth User Fallback
            if not creds:
                creds = get_gmail_credentials()
                
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
            # 1. Service Account
            creds = _load_service_account_creds()
            
            # 2. OAuth User Fallback
            if not creds:
                creds = get_gmail_credentials()
                
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
            
        # Priority 2: Secrets
        if not client_config and "google" in st.secrets:
            client_config = json.loads(st.secrets["google"]["client_config_json"]) if "client_config_json" in st.secrets["google"] else st.secrets["google"]
            
        # Priority 3: Local File
        elif not client_config and os.path.exists('credentials.json'):
            client_config = json.load(open('credentials.json'))
        
        if not client_config:
            # Only warn if we really need user creds (and don't have SA)
            # But here this function is explicitly for User Creds
            st.error("⚠️ Falta configuración de Google (Secrets, Sheet o credentials.json).")
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
        
        code = st.text_input("Ingresa el Código de Google:", key="auth_code")
        
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
                             st.success("✅ ¡Conectado! Recargando...")
                             time.sleep(2)
                             st.rerun()
            except Exception as e:
                st.error(f"Error de autenticación: {e}")
                return None
        else:
            st.stop()
    
    # 5. Extract Email for UI
    try:
        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()
        st.session_state.connected_email = profile.get('emailAddress', 'Desconocido')
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
                
                body = "Sin contenido"
                if 'parts' in payload:
                    for part in payload['parts']:
                        if part['mimeType'] == 'text/plain':
                            import base64
                            data = part['body'].get('data')
                            if data:
                                body = base64.urlsafe_b64decode(data).decode()
                                break
                elif 'body' in payload and payload['body'].get('data'):
                     import base64
                     body = base64.urlsafe_b64decode(payload['body']['data']).decode()

                email_data.append({
                    "id": msg['id'],
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

def add_task_to_google(service, tasklist_id, title, notes=None, due_date=None):
    """Adds a task to the specified list."""
    try:
        task = {
            'title': title,
            'notes': notes
        }
        if due_date:
            # Google Tasks expects RFC 3339 timestamp
            task['due'] = due_date.isoformat() + 'Z'
            
        result = service.tasks().insert(tasklist=tasklist_id, body=task).execute()
        return result
    except Exception as e:
        st.error(f"Error adding task: {e}")
        return None 
 d e f   d e l e t e _ t a s k _ g o o g l e ( s e r v i c e ,   t a s k l i s t _ i d ,   t a s k _ i d ) :  
         " " " D e l e t e s   a   t a s k   f r o m   t h e   s p e c i f i e d   l i s t . " " "  
         t r y :  
                 s e r v i c e . t a s k s ( ) . d e l e t e ( t a s k l i s t = t a s k l i s t _ i d ,   t a s k = t a s k _ i d ) . e x e c u t e ( )  
                 r e t u r n   T r u e  
         e x c e p t   E x c e p t i o n   a s   e :  
                 s t . e r r o r ( f " E r r o r   d e l e t i n g   t a s k :   { e } " )  
                 r e t u r n   F a l s e  
  
 d e f   u p d a t e _ t a s k _ g o o g l e ( s e r v i c e ,   t a s k l i s t _ i d ,   t a s k _ i d ,   t i t l e = N o n e ,   n o t e s = N o n e ,   s t a t u s = N o n e ,   d u e = N o n e ) :  
         " " " U p d a t e s   a n   e x i s t i n g   t a s k . " " "  
         t r y :  
                 #   F i r s t   g e t   t h e   e x i s t i n g   t a s k   t o   p r e s e r v e   o t h e r   f i e l d s  
                 t a s k   =   s e r v i c e . t a s k s ( ) . g e t ( t a s k l i s t = t a s k l i s t _ i d ,   t a s k = t a s k _ i d ) . e x e c u t e ( )  
                  
                 i f   t i t l e :   t a s k [ ' t i t l e ' ]   =   t i t l e  
                 i f   n o t e s :   t a s k [ ' n o t e s ' ]   =   n o t e s  
                 i f   s t a t u s :   t a s k [ ' s t a t u s ' ]   =   s t a t u s  
                  
                 i f   d u e :  
                           t a s k [ ' d u e ' ]   =   d u e . i s o f o r m a t ( )   +   ' Z '  
                 e l i f   d u e   = =   " " :   #   C l e a r   d u e   d a t e   l o g i c   i f   n e e d e d ,   b u t   f o r   n o w   b a s i c   u p d a t e  
                           i f   ' d u e '   i n   t a s k :   d e l   t a s k [ ' d u e ' ]  
  
                 r e s u l t   =   s e r v i c e . t a s k s ( ) . u p d a t e ( t a s k l i s t = t a s k l i s t _ i d ,   t a s k = t a s k _ i d ,   b o d y = t a s k ) . e x e c u t e ( )  
                 r e t u r n   r e s u l t  
         e x c e p t   E x c e p t i o n   a s   e :  
                 s t . e r r o r ( f " E r r o r   u p d a t i n g   t a s k :   { e } " )  
                 r e t u r n   N o n e  
  
 d e f   g e t _ e x i s t i n g _ t a s k s _ s i m p l e ( s e r v i c e ) :  
         " " " F e t c h e s   a l l   t a s k s   f r o m   a l l   l i s t s   ( s i m p l i f i e d   f o r   A I   c o n t e x t ) . " " "  
         t r y :  
                 a l l _ t a s k s   =   [ ]  
                 t a s k l i s t s   =   g e t _ t a s k _ l i s t s ( s e r v i c e )  
                 f o r   t l   i n   t a s k l i s t s :  
                         r e s u l t s   =   s e r v i c e . t a s k s ( ) . l i s t ( t a s k l i s t = t l [ ' i d ' ] ,   s h o w C o m p l e t e d = F a l s e ) . e x e c u t e ( )  
                         t a s k s   =   r e s u l t s . g e t ( ' i t e m s ' ,   [ ] )  
                         f o r   t   i n   t a s k s :  
                                 a l l _ t a s k s . a p p e n d ( {  
                                         ' i d ' :   t [ ' i d ' ] ,  
                                         ' t i t l e ' :   t [ ' t i t l e ' ] ,  
                                         ' l i s t _ i d ' :   t l [ ' i d ' ] ,  
                                         ' l i s t _ t i t l e ' :   t l [ ' t i t l e ' ] ,  
                                         ' d u e ' :   t . g e t ( ' d u e ' ,   ' N o   D u e   D a t e ' )  
                                 } )  
                 r e t u r n   a l l _ t a s k s  
         e x c e p t   E x c e p t i o n   a s   e :  
                 #   s t . w a r n i n g ( f " C o u l d   n o t   f e t c h   t a s k s :   { e } " )   #   S u p p r e s s   t o   a v o i d   U I   c l u t t e r  
                 r e t u r n   [ ]  
  
 d e f   a d d _ e v e n t _ t o _ c a l e n d a r ( s e r v i c e ,   s u m m a r y ,   s t a r t _ t i m e ,   e n d _ t i m e ,   d e s c r i p t i o n = N o n e ,   c o l o r _ i d = N o n e ) :  
         " " " A d d s   a n   e v e n t   t o   G o o g l e   C a l e n d a r . " " "  
         t r y :  
                 e v e n t   =   {  
                         ' s u m m a r y ' :   s u m m a r y ,  
                         ' s t a r t ' :   { ' d a t e T i m e ' :   s t a r t _ t i m e . i s o f o r m a t ( ) ,   ' t i m e Z o n e ' :   ' U T C ' } ,   #   A d j u s t   T Z   a s   n e e d e d  
                         ' e n d ' :   { ' d a t e T i m e ' :   e n d _ t i m e . i s o f o r m a t ( ) ,   ' t i m e Z o n e ' :   ' U T C ' } ,  
                         ' d e s c r i p t i o n ' :   d e s c r i p t i o n  
                 }  
                 i f   c o l o r _ i d :  
                         e v e n t [ ' c o l o r I d ' ]   =   c o l o r _ i d  
                          
                 e v e n t   =   s e r v i c e . e v e n t s ( ) . i n s e r t ( c a l e n d a r I d = ' p r i m a r y ' ,   b o d y = e v e n t ) . e x e c u t e ( )  
                 r e t u r n   e v e n t  
         e x c e p t   E x c e p t i o n   a s   e :  
                 s t . e r r o r ( f " E r r o r   a d d i n g   e v e n t :   { e } " )  
                 r e t u r n   N o n e  
  
 d e f   d e l e t e _ e v e n t ( s e r v i c e ,   e v e n t _ i d ) :  
         " " " D e l e t e s   a n   e v e n t   f r o m   t h e   p r i m a r y   c a l e n d a r . " " "  
         t r y :  
                 s e r v i c e . e v e n t s ( ) . d e l e t e ( c a l e n d a r I d = ' p r i m a r y ' ,   e v e n t I d = e v e n t _ i d ) . e x e c u t e ( )  
                 r e t u r n   T r u e  
         e x c e p t   E x c e p t i o n   a s   e :  
                 s t . e r r o r ( f " E r r o r   d e l e t i n g   e v e n t :   { e } " )  
                 r e t u r n   F a l s e  
  
 d e f   o p t i m i z e _ e v e n t ( s e r v i c e ,   e v e n t _ i d ,   n e w _ s t a r t ,   n e w _ e n d ) :  
         " " " U p d a t e s   e v e n t   t i m i n g . " " "  
         t r y :  
                 e v e n t   =   s e r v i c e . e v e n t s ( ) . g e t ( c a l e n d a r I d = ' p r i m a r y ' ,   e v e n t I d = e v e n t _ i d ) . e x e c u t e ( )  
                 e v e n t [ ' s t a r t ' ] [ ' d a t e T i m e ' ]   =   n e w _ s t a r t . i s o f o r m a t ( )  
                 e v e n t [ ' e n d ' ] [ ' d a t e T i m e ' ]   =   n e w _ e n d . i s o f o r m a t ( )  
                 u p d a t e d _ e v e n t   =   s e r v i c e . e v e n t s ( ) . u p d a t e ( c a l e n d a r I d = ' p r i m a r y ' ,   e v e n t I d = e v e n t _ i d ,   b o d y = e v e n t ) . e x e c u t e ( )  
                 r e t u r n   u p d a t e d _ e v e n t  
         e x c e p t   E x c e p t i o n   a s   e :  
                 s t . e r r o r ( f " E r r o r   o p t i m i z i n g   e v e n t :   { e } " )  
                 r e t u r n   N o n e  
 