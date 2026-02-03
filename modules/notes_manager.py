
import streamlit as st
import datetime
import pandas as pd
import uuid
import json
from modules.google_services import get_sheets_service

# --- CONSTANTS ---
NOTES_SHEET_NAME = "notes"
NOTES_COLUMNS = ["id", "created_at", "content", "status", "tags", "source", "linked_event_id", "user_id"]

def _get_notes_data(service, spreadsheet_id):
    """Fetches all notes from the 'notes' tab."""
    try:
        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=spreadsheet_id, 
            range=f"{NOTES_SHEET_NAME}!A:H"
        ).execute()
        rows = result.get('values', [])
        
        if not rows:
            return []
            
        # Assuming header row is present
        headers = rows[0]
        data = []
        for row in rows[1:]:
            # Pad row if missing columns
            while len(row) < len(NOTES_COLUMNS):
                row.append("")
            
            note = {
                "id": row[0],
                "created_at": row[1],
                "content": row[2],
                "status": row[3],
                "tags": row[4],
                "source": row[5],
                "linked_event_id": row[6],
                "user_id": row[7]
            }
            data.append(note)
            
        return data
    except Exception as e:
        print(f"Error getting notes: {e}")
        return []

def ensure_notes_tab_exists(service, spreadsheet_id):
    """Checks if 'notes' tab exists, creates if not."""
    import time
    retries = 3
    for attempt in range(retries):
        try:
            if not spreadsheet_id: return False
            spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheets = spreadsheet.get('sheets', '')
            sheet_titles = [s['properties']['title'] for s in sheets]
            
            if NOTES_SHEET_NAME not in sheet_titles:
                # Create sheet
                body = {
                    'requests': [{
                        'addSheet': {
                            'properties': {
                                'title': NOTES_SHEET_NAME
                            }
                        }
                    }]
                }
                service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=body
                ).execute()
                
                # Add headers
                header_body = {
                    'values': [NOTES_COLUMNS]
                }
                service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=f"{NOTES_SHEET_NAME}!A1",
                    valueInputOption="RAW",
                    body=header_body
                ).execute()
                return True
            return True # Exists
            
        except Exception as e:
            err_str = str(e).lower()
            if "ssl" in err_str or "decryption" in err_str or "connection" in err_str or "broken pipe" in err_str:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
            
            if attempt == retries - 1:
                st.error(f"Error checking/creating Notes tab: {e}")
                return False
    return True

def create_note(content, source="manual", tags="", linked_event_id="", user_id=""):
    """Creates a new note."""
    if 'sheets_service' not in st.session_state:
        st.error("Servicio de Sheets no conectado")
        return False
        
    service = st.session_state.sheets_service
    
    # --- ROBUST ID EXTRACTION ---
    spreadsheet_id = None
    if "private_sheet_url" in st.secrets:
        import re
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", st.secrets["private_sheet_url"])
        if match: spreadsheet_id = match.group(1)
            
    if not spreadsheet_id and "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
         spreadsheet_id = st.secrets["connections"]["gsheets"].get("spreadsheet")     
    
    if not spreadsheet_id:
        spreadsheet_id = "1DB2whTniVqxaom6x-lPMempJozLnky1c0GTzX2R2-jQ"
    
    if not spreadsheet_id:
        st.error("Spreadsheet ID no configurado.")
        return False 
    
    ensure_notes_tab_exists(service, spreadsheet_id)
    
    new_id = str(uuid.uuid4())
    timestamp = datetime.datetime.now().isoformat()
    
    values = [[new_id, timestamp, content, "active", tags, source, linked_event_id, user_id]]
    
    body = {'values': values}
    
    import time
    retries = 3
    for attempt in range(retries):
        try:
            service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=f"{NOTES_SHEET_NAME}!A:H",
                valueInputOption="USER_ENTERED",
                body=body
            ).execute()
            return new_id
        except Exception as e:
            err_str = str(e).lower()
            if "ssl" in err_str or "decryption" in err_str or "connection" in err_str or "broken pipe" in err_str:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
            
            if attempt == retries - 1:
                st.error(f"Error saving note: {e}")
                return None
    return None

def get_active_notes(user_id=""):
    """Returns list of active notes for a specific user."""
    if 'sheets_service' not in st.session_state:
        return []
    
    service = st.session_state.sheets_service
    
    # --- ROBUST ID EXTRACTION ---
    spreadsheet_id = None
    
    # 1. Try 'private_sheet_url' (from auth.py)
    if "private_sheet_url" in st.secrets:
        url = st.secrets["private_sheet_url"]
        # Extract /d/ID/
        import re
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
        if match:
            spreadsheet_id = match.group(1)
            
    # 2. Try 'connections.gsheets' (standard)
    if not spreadsheet_id and "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
         spreadsheet_id = st.secrets["connections"]["gsheets"].get("spreadsheet")     
    
    # 3. Fallback Hardcoded (Matches auth.py logic for this user)
    if not spreadsheet_id:
        spreadsheet_id = "1DB2whTniVqxaom6x-lPMempJozLnky1c0GTzX2R2-jQ"
    
    if not spreadsheet_id:
        st.error("Spreadsheet ID no configurado en secrets.")
        return []
    
    try:
        all_notes = _get_notes_data(service, spreadsheet_id)
        # Filter for 'active' AND user_id strict match
        # We handle empty user_id in DB (legacy) by showing them ONLY if user_id arg is also empty (admin?) or maybe just show?
        # User requested Strict Isolation. If Note has no ID, who owns it? 
        # For now, simplistic check: if note['user_id'] matches user_id
        return [n for n in all_notes if n['status'] == 'active' and str(n.get('user_id', '')).strip() == str(user_id).strip()]
    except Exception as e:
        if "404" in str(e):
            st.error(f"No se encontró la hoja. ID: {spreadsheet_id}")
        else:
            st.error(f"Error leyendo notas: {e}")
        return []

def archive_note(note_id):
    """Marks a note as archived."""
    # This acts like a 'delete' from view but keeps data
    # We need to find the row index. This is inefficient in raw Sheets API without a row cache.
    # For MVP, we fetch all, find index, update.
    if 'sheets_service' not in st.session_state:
        return False
        
    service = st.session_state.sheets_service
        
    # --- ROBUST ID EXTRACTION (Duplicate logic for safety) ---
    spreadsheet_id = None
    if "private_sheet_url" in st.secrets:
        import re
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", st.secrets["private_sheet_url"])
        if match: spreadsheet_id = match.group(1)
            
    if not spreadsheet_id and "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
         spreadsheet_id = st.secrets["connections"]["gsheets"].get("spreadsheet")     
    
    if not spreadsheet_id:
        spreadsheet_id = "1DB2whTniVqxaom6x-lPMempJozLnky1c0GTzX2R2-jQ"
    
    if not spreadsheet_id: return False
    
    try:
        all_notes = _get_notes_data(service, spreadsheet_id)
    except: return False
    
    row_index = -1
    for i, note in enumerate(all_notes):
        if note['id'] == note_id:
            row_index = i + 2 # +1 for header, +1 for 0-index conversion
            break
            
    if row_index != -1:
        body = {'values': [['archived']]}
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{NOTES_SHEET_NAME}!D{row_index}", # Status is column D (4th)
            valueInputOption="RAW",
            body=body
        ).execute()
        return True
    return False

def delete_note(note_id):
    """Marks a note as deleted."""
    if 'sheets_service' not in st.session_state:
        return False
        
    service = st.session_state.sheets_service
    
    # --- ROBUST ID EXTRACTION ---
    spreadsheet_id = None
    if "private_sheet_url" in st.secrets:
        import re
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", st.secrets["private_sheet_url"])
        if match: spreadsheet_id = match.group(1)
            
    if not spreadsheet_id and "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
         spreadsheet_id = st.secrets["connections"]["gsheets"].get("spreadsheet")     
    
    if not spreadsheet_id:
        spreadsheet_id = "1DB2whTniVqxaom6x-lPMempJozLnky1c0GTzX2R2-jQ"
    
    if not spreadsheet_id: return False
    
    try:
        all_notes = _get_notes_data(service, spreadsheet_id)
    except: return False
    
    row_index = -1
    for i, note in enumerate(all_notes):
        if note['id'] == note_id:
            row_index = i + 2 
            break
            
    if row_index != -1:
        body = {'values': [['deleted']]}
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{NOTES_SHEET_NAME}!D{row_index}", # Status is column D (4th)
            valueInputOption="RAW",
            body=body
        ).execute()
        return True
    return False

def get_archived_notes(user_id=""):
    """Returns list of archived notes for a specific user."""
    if 'sheets_service' not in st.session_state:
        return []
    
    service = st.session_state.sheets_service
    
    # --- IDS ---
    spreadsheet_id = None
    if "private_sheet_url" in st.secrets:
        import re
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", st.secrets["private_sheet_url"])
        if match: spreadsheet_id = match.group(1)
            
    if not spreadsheet_id and "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
         spreadsheet_id = st.secrets["connections"]["gsheets"].get("spreadsheet")     
    
    if not spreadsheet_id:
        spreadsheet_id = "1DB2whTniVqxaom6x-lPMempJozLnky1c0GTzX2R2-jQ"
        
    try:
        all_notes = _get_notes_data(service, spreadsheet_id)
        # Filter for 'archived' AND user_id strict match
        return [n for n in all_notes if n['status'] == 'archived' and str(n.get('user_id', '')).strip() == str(user_id).strip()]
    except Exception as e:
        print(f"Error reading archived notes: {e}")
        return []

def update_note(note_id, updates):
    """
    Updates specific fields of a note.
    updates: dict with keys 'status', 'tags', 'linked_event_id'
    """
    if 'sheets_service' not in st.session_state:
        return False
        
    service = st.session_state.sheets_service
    
    # --- IDS ---
    spreadsheet_id = None
    if "private_sheet_url" in st.secrets:
        import re
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", st.secrets["private_sheet_url"])
        if match: spreadsheet_id = match.group(1)
            
    if not spreadsheet_id and "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
         spreadsheet_id = st.secrets["connections"]["gsheets"].get("spreadsheet")     
    
    if not spreadsheet_id:
        spreadsheet_id = "1DB2whTniVqxaom6x-lPMempJozLnky1c0GTzX2R2-jQ"
        
    try:
        all_notes = _get_notes_data(service, spreadsheet_id)
    except: return False
    
    row_index = -1
    for i, note in enumerate(all_notes):
        if note['id'] == note_id:
            row_index = i + 2 # Header + 1-indexed
            break
            
    if row_index != -1:
        # Columns mapping: 
        # A: id, B: created_at, C: content, D: status, E: tags, F: source, G: linked_event_id
        
        # We process each update safely
        if 'status' in updates:
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id, range=f"{NOTES_SHEET_NAME}!D{row_index}",
                valueInputOption="RAW", body={'values': [[updates['status']]]}
            ).execute()
            
        if 'tags' in updates:
             service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id, range=f"{NOTES_SHEET_NAME}!E{row_index}",
                valueInputOption="USER_ENTERED", body={'values': [[updates['tags']]]}
            ).execute()
            
        if 'linked_event_id' in updates:
             service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id, range=f"{NOTES_SHEET_NAME}!G{row_index}",
                valueInputOption="RAW", body={'values': [[updates['linked_event_id']]]}
            ).execute()
            
        return True
    return False

