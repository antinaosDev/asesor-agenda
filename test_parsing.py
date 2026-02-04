import modules.ai_core as ai_core
import streamlit as st
import os

# Mock secrets if needed
if "GROQ_API_KEY" not in os.environ:
    print("WARNING: GROQ_API_KEY not set in env. This might fail if not using st.secrets")

input_text = """
CALENDARIO ANUAL DE REUNIONES DEL COMITÉ DE CAPACITACIÓN 2026
Recibidos

Resume este correo electrónico

Marcela Teuque <tsmarcela684@gmail.com>
mar, 2 dic 2025, 4:00 p.m.
para Freddy, Grechen, Recursos, nicole, mí, Carlos, Felipe, SOME, Cesfam, Rocio

Estimado Comité :
junto con saludar, esperando que se encuentren bien, envío calendario de reunión de comité de capacitación ANUAL  año 2026

además informar  que en el caso de las reuniones de no estar  el titular,  asiste el  subrogante. no es necesario que asistan los dos. 
 
detallo los meses de reunión que serán los jueves, mes por medio, excepto penúltimo mes, en horario de las 14:00 a 17:00hrs. para que puedan agregar a sus agendas y copio correo a SOME  para conocimiento y respectivos bloqueos. 

cualquier modificación y cambio de fecha se les avisara, o algún requerimiento del servicio, ante convenio y/o curso entre otras acciones de contingencia 

detalló calendario : 

 1- jueves 22 de enero,  horario 14:00 a 17 hrs
 2- jueves 19 de marzo,  horario 14:00 a 17 hrs
3- jueves 23 de abril,  horario 14:00 a 17 hrs
4- jueves 18 de junio, horario  14:00 a 17 hrs
5- jueves 20 de agosto, horario  14:00 a 17 hrs
6- jueves 15 octubre, horario 14:00 a 17 hrs
7- jueves 26 de noviembre, horario  14:00 a 17 hrs

atentamente, saludos cordiales 
"""

print("--- TESTING AI PARSING ---")
try:
    events = ai_core.parse_events_ai(input_text)
    print(f"Found {len(events)} events.")
    for e in events:
        print(f"- {e.get('summary')} ({e.get('start_time')})")
except Exception as e:
    print(f"Error: {e}")
