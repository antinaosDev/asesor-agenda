

# ─────────────────────────────────────────────────────────────
# GOOGLE KEEP INTEGRATION
# ─────────────────────────────────────────────────────────────

def get_keep_service(credentials=None):
    """
    Build and return Google Keep API service.
    Args:
        credentials: OAuth credentials (if None, will get from get_gmail_credentials)
    Returns:
        Google Keep service instance
    """
    from googleapiclient.discovery import build
    
    if not credentials:
        credentials = get_gmail_credentials()
    
    if not credentials:
        return None
    
    try:
        service = build('keep', 'v1', credentials=credentials)
        return service
    except Exception as e:
        print(f"Error building Keep service: {e}")
        import streamlit as st
        st.error(f"❌ Error conectando a Google Keep: {e}")
        return None


def create_keep_note(service, title, content, color=None, labels=None):
    """
    Create a note in Google Keep.
    
    Args:
        service: Keep API service instance
        title: Note title (string)
        content: Note content/body (string)
        color: Note color (optional). Valid values:
               'DEFAULT', 'RED', 'ORANGE', 'YELLOW', 'GREEN', 
               'TEAL', 'BLUE', 'DARK_BLUE', 'PURPLE', 'PINK', 
               'BROWN', 'GRAY'
        labels: List of label names (optional)
    
    Returns:
        Created note object or None on error
    """
    try:
        note_body = {
            'title': title,
            'body': {
                'text': {
                    'text': content
                }
            }
        }
        
        # Add color if specified
        if color:
            valid_colors = ['DEFAULT', 'RED', 'ORANGE', 'YELLOW', 'GREEN', 
                           'TEAL', 'BLUE', 'DARK_BLUE', 'PURPLE', 'PINK', 
                           'BROWN', 'GRAY']
            if color.upper() in valid_colors:
                note_body['color'] = color.upper()
        
        # Add labels if specified
        if labels:
            # Keep API uses label IDs, need to create/fetch labels first
            # For simplicity, we'll skip labels in MVP
            pass
        
        note = service.notes().create(body=note_body).execute()
        return note
    
    except Exception as e:
        print(f"Error creating Keep note: {e}")
        import traceback
        traceback.print_exc()
        return None


def list_keep_notes(service, query=None, max_results=100):
    """
    List notes from Google Keep.
    
    Args:
        service: Keep API service instance
        query: Search query (optional)
        max_results: Maximum number of notes to return
    
    Returns:
        List of note objects
    """
    try:
        params = {'pageSize': min(max_results, 100)}
        
        if query:
            params['filter'] = query
        
        results = service.notes().list(**params).execute()
        notes = results.get('notes', [])
        
        return notes
    
    except Exception as e:
        print(f"Error listing Keep notes: {e}")
        return []


def delete_keep_note(service, note_id):
    """
    Delete a note from Google Keep.
    
    Args:
        service: Keep API service instance
        note_id: ID of the note to delete
    
    Returns:
        True on success, False on error
    """
    try:
        service.notes().delete(name=f'notes/{note_id}').execute()
        return True
    except Exception as e:
        print(f"Error deleting Keep note: {e}")
        return False
