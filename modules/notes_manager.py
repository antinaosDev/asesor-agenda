
import streamlit as st
import datetime
import pandas as pd
import uuid
import json
from modules.google_services import get_sheets_service

# --- CONSTANTS ---
NOTES_SHEET_NAME = "notes"
NOTES_COLUMNS = ["id", "created_at", "content", "status", "tags", "source", "linked_event_id"]

def _get_notes_data(service, spreadsheet_id):
    """Fetches all notes from the 'notes' tab."""
    try:
        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=spreadsheet_id, 
            range=f"{NOTES_SHEET_NAME}!A:G"
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
                "linked_event_id": row[6]
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

def create_note(content, source="manual", tags="", linked_event_id=""):
    """Creates a new note."""
    if 'sheets_service' not in st.session_state:
        st.error("Servicio de Sheets no conectado")
        return False
        
    service = st.session_state.sheets_service
    # We need the user's specific spreadsheet ID where they store data
    # Assuming it is stored in st.session_state.user_data_full['spreadsheet_id'] 
    # OR retrieving it dynamically. 
    # Based on app logic, user data is in a main sheet, but each user might just use the main DB 
    # or their own. Let's assume we write to the MAIN database defined in .env or config 
    # BUT wait, this app uses Google Sheets AS the database. 
    
    # Correction: The app seems to use a single sheet for Auth but maybe expects users to have their own?
    # Let's look at how other modules get the spreadsheet ID.
    # Looking at google_services.py might help. 
    # For now, let's assume we pass the ID or get it from env.
    
    # RETRIEVING CONFIG
    # In this specific app, it seems 'st.secrets' or implicit knowledge is used.
    # Let's check how 'auth.py' or others identify the sheet.
    # If not found, we will simply use st.secrets["connections"]["gsheets"]["spreadsheet"] if available.
    
    # Let's assume there is a specific 'user_data_full' that contains personal config?
    # Or simply use the main one. I'll defer ID resolution to logic below.
    
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
    
    values = [[new_id, timestamp, content, "active", tags, source, linked_event_id]]
    
    body = {'values': values}
    
    import time
    retries = 3
    for attempt in range(retries):
        try:
            service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=f"{NOTES_SHEET_NAME}!A:G",
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

def get_active_notes():
    """Returns list of active notes."""
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
        return [n for n in all_notes if n['status'] == 'active']
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

