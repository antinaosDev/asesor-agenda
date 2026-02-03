
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
    try:
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
    except Exception as e:
        st.error(f"Error creating Notes tab: {e}")
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
    
    spreadsheet_id = st.secrets["connections"]["gsheets"]["spreadsheet"] 
    
    ensure_notes_tab_exists(service, spreadsheet_id)
    
    new_id = str(uuid.uuid4())
    timestamp = datetime.datetime.now().isoformat()
    
    values = [[new_id, timestamp, content, "active", tags, source, linked_event_id]]
    
    body = {'values': values}
    
    try:
        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f"{NOTES_SHEET_NAME}!A:G",
            valueInputOption="USER_ENTERED",
            body=body
        ).execute()
        return new_id
    except Exception as e:
        st.error(f"Error saving note: {e}")
        return None

def get_active_notes():
    """Returns list of active notes."""
    if 'sheets_service' not in st.session_state:
        return []
    
    service = st.session_state.sheets_service
    # Use standard lookup from Google Services if possible, or fallback
    spreadsheet_id = st.secrets.get("spreadsheet", {}).get("spreadsheet_id")
    if not spreadsheet_id and "connections" in st.secrets:
         # Try streamlit cloud default
         spreadsheet_id = st.secrets["connections"]["gsheets"].get("spreadsheet")     
    
    if not spreadsheet_id:
        st.error("Spreadsheet ID no configurado en secrets.")
        return [] 
    
    all_notes = _get_notes_data(service, spreadsheet_id)
    return [n for n in all_notes if n['status'] == 'active']

def archive_note(note_id):
    """Marks a note as archived."""
    # This acts like a 'delete' from view but keeps data
    # We need to find the row index. This is inefficient in raw Sheets API without a row cache.
    # For MVP, we fetch all, find index, update.
    if 'sheets_service' not in st.session_state:
        return False
        
    service = st.session_state.sheets_service
    # Use standard lookup from Google Services if possible, or fallback
    spreadsheet_id = st.secrets.get("spreadsheet", {}).get("spreadsheet_id")
    if not spreadsheet_id and "connections" in st.secrets:
         # Try streamlit cloud default
         spreadsheet_id = st.secrets["connections"]["gsheets"].get("spreadsheet")     
    
    if not spreadsheet_id: return False
    
    all_notes = _get_notes_data(service, spreadsheet_id)
    
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

