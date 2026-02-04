import modules.ai_core as ai_core
import datetime

# Mock context
input_text = """
Estimados:
Junto con saludar, se cita a reunión de Comité de Salud Intercultural para esta tarde a contar de las 14:30 horas en sala de reuniones, las agendas se encuentra debidamente bloqueadas; informo las siguientes fechas para conocimiento:

ENERO,MARTES 20 |MARZO,MARTES 03|MAYO,MARTES 05|JULIO,MARTES 07|SEPTIEMBRE,MARTES 01|NOVIEMBRE,MARTES 03
"""

print("--- TESTING AI PARSING (PIPE SEPARATORS) ---")
try:
    events = ai_core.parse_events_ai(input_text)
    print(f"Found {len(events)} items.")
    for e in events:
        print(f"[{e.get('type')}] {e.get('summary')} ({e.get('start_time')})")
        
    # Validation
    event_count = sum(1 for e in events if e.get('type') == 'event')
    # We expect 7 events: 1 for "esta tarde" + 6 from the pipe list
    if event_count >= 6:
        print("✅ SUCCESS: Detected multiple events from list.")
    else:
        print("❌ FAILURE: Did not detect enough events.")
        
except Exception as e:
    print(f"Error: {e}")
