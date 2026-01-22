
import os
import datetime
import json
import logging
from typing import List, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from groq import Groq
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("event_log.log"),
        logging.StreamHandler()
    ]
)

# Load environment variables
load_dotenv()

# Configuration
SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'service_account.json')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    """Authenticates and returns the Google Calendar service."""
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        service = build('calendar', 'v3', credentials=creds)
        logging.info("Successfully authenticated with Google Calendar API.")
        return service
    except Exception as e:
        logging.error(f"Error authenticating: {e}")
        raise

def parse_events_with_groq(text_input: str) -> List[dict]:
    """Uses Groq to parse natural language text into structured event data."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not found in environment variables.")

    client = Groq(api_key=GROQ_API_KEY)

    system_prompt = """
    You are a helpful assistant that extracts calendar events from text.
    Your output must be a valid JSON array of objects.
    Each object should have the following keys:
    - "summary": The title or subject of the event.
    - "description": A detailed description of the event.
    - "start_time": The start time in ISO 8601 format (YYYY-MM-DDTHH:MM:SS). If the year is not specified, assume the current year (2026). If time is not specified, assume it's an all-day event (YYYY-MM-DD).
    - "end_time": The end time in ISO 8601 format. If duration is not specified, assume 1 hour.
    
    Current Date: """ + datetime.datetime.now().strftime("%Y-%m-%d") + """
    
    Example Input: "Meeting with John tomorrow at 2pm for project discussion."
    Example Output:
    [
        {
            "summary": "Meeting with John",
            "description": "Project discussion",
            "start_time": "2026-01-22T14:00:00",
            "end_time": "2026-01-22T15:00:00"
        }
    ]
    
    Only return the JSON array. Do not include markdown formatting like ```json ... ```.
    """

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": text_input,
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=1024,
        )
        
        content = chat_completion.choices[0].message.content.strip()
        # Clean up if the model includes markdown code blocks despite instructions
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
            
        events = json.loads(content)
        logging.info(f"Successfully parsed {len(events)} events from text.")
        return events
    except Exception as e:
        logging.error(f"Error parsing text with Groq: {e}")
        logging.error(f"Raw output: {content if 'content' in locals() else 'N/A'}")
        return []

def create_event(service, event_data: dict, calendar_id: str = 'primary'):
    """Creates an event in the specified calendar."""
    
    # Handle ISO format vs Date only format
    start = {}
    end = {}
    
    if 'T' in event_data['start_time']:
        start = {'dateTime': event_data['start_time'], 'timeZone': 'America/Santiago'} # Configuring for Chile time as per usual context or default
    else:
        start = {'date': event_data['start_time']}

    if 'T' in event_data['end_time']:
        end = {'dateTime': event_data['end_time'], 'timeZone': 'America/Santiago'}
    else:
        end = {'date': event_data['end_time']}

    event = {
        'summary': event_data.get('summary', 'No Title'),
        'description': event_data.get('description', ''),
        'start': start,
        'end': end,
    }

    try:
        created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
        logging.info(f"Event created: {created_event.get('htmlLink')}")
        print(f"Success: Created event '{event['summary']}'")
    except Exception as e:
        logging.error(f"Error creating event '{event.get('summary')}': {e}")
        print(f"Error: Failed to create event '{event.get('summary')}'")

def main():
    print("--- Google Calendar Event Registrar ---")
    
    # 1. Get Calendar ID
    print("\nNote: For Service Accounts, 'primary' refers to the service account's own calendar.")
    print("If you want to add to your personal calendar, you must share it with:")
    print("mensajeria-rev@sistemas-473713.iam.gserviceaccount.com")
    print("and allow 'Make changes to events'.")
    
    calendar_id = input("\nEnter Calendar ID (press Enter for 'primary' or paste your email): ").strip() or 'primary'
    
    # 2. Get Input Mode
    print("\nHow would you like to provide the events?")
    print("1. Type/Paste here")
    print("2. Read from 'input_events.txt' file")
    choice = input("Select (1/2): ").strip()
    
    text_input = ""
    
    if choice == '1':
        print("\nEnter your events found below (Press Ctrl+Z then Enter on Windows to finish, or Ctrl+D on Linux/Mac):")
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass
        text_input = "\n".join(lines)
    
    elif choice == '2':
        if os.path.exists('input_events.txt'):
            with open('input_events.txt', 'r', encoding='utf-8') as f:
                text_input = f.read()
            print(f"Read {len(text_input)} characters from input_events.txt")
        else:
            print("Error: input_events.txt not found.")
            return
            
    if not text_input.strip():
        print("No text provided. Exiting.")
        return
        
    # 3. Process
    print("\nProcessing with AI...")
    events = parse_events_with_groq(text_input)
    
    if not events:
        print("No events could be parsed.")
        return
        
    print(f"\nFound {len(events)} events. Connecting to Calendar...")
    service = get_calendar_service()
    
    for event in events:
        create_event(service, event, calendar_id)
        
    print("\nDone. Check the log file for details.")

if __name__ == '__main__':
    main()
