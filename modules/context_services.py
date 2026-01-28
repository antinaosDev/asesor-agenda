import requests
import datetime
import streamlit as st

# --- CONSTANTS ---
HOLIDAYS_2026 = {
  "year": 2026,
  "feriados": {
    "enero": [{"mes": 1, "dia": 1, "dia_semana": "jueves", "descripcion": "Año Nuevo", "tipo": "civil", "irrenunciable": True}],
    "abril": [{"mes": 4, "dia": 3, "dia_semana": "viernes", "descripcion": "Viernes Santo", "tipo": "religioso", "irrenunciable": False}, {"mes": 4, "dia": 4, "dia_semana": "sábado", "descripcion": "Sábado Santo", "tipo": "religioso", "irrenunciable": False}],
    "mayo": [{"mes": 5, "dia": 1, "dia_semana": "viernes", "descripcion": "Día del Trabajo", "tipo": "civil", "irrenunciable": True}, {"mes": 5, "dia": 21, "dia_semana": "jueves", "descripcion": "Día de las Glorias Navales", "tipo": "civil", "irrenunciable": False}],
    "junio": [{"mes": 6, "dia": 21, "dia_semana": "domingo", "descripcion": "Día Nacional de los Pueblos Indígenas", "tipo": "civil", "irrenunciable": False}, {"mes": 6, "dia": 29, "dia_semana": "lunes", "descripcion": "San Pedro y San Pablo", "tipo": "religioso", "irrenunciable": False}],
    "julio": [{"mes": 7, "dia": 16, "dia_semana": "jueves", "descripcion": "Día de la Virgen del Carmen", "tipo": "religioso", "irrenunciable": False}],
    "agosto": [{"mes": 8, "dia": 15, "dia_semana": "sábado", "descripcion": "Asunción de la Virgen", "tipo": "religioso", "irrenunciable": False}],
    "septiembre": [{"mes": 9, "dia": 17, "dia_semana": "jueves", "descripcion": "Feriado Adicional Fiestas Patrias", "tipo": "civil", "irrenunciable": False}, {"mes": 9, "dia": 18, "dia_semana": "viernes", "descripcion": "Independencia Nacional", "tipo": "civil", "irrenunciable": True}, {"mes": 9, "dia": 19, "dia_semana": "sábado", "descripcion": "Día de las Glorias del Ejército", "tipo": "civil", "irrenunciable": True}],
    "octubre": [{"mes": 10, "dia": 11, "dia_semana": "domingo", "descripcion": "Encuentro de Dos Mundos", "tipo": "civil", "irrenunciable": False}, {"mes": 10, "dia": 31, "dia_semana": "sábado", "descripcion": "Día de las Iglesias Evangélicas y Protestantes", "tipo": "religioso", "irrenunciable": False}],
    "noviembre": [{"mes": 11, "dia": 1, "dia_semana": "domingo", "descripcion": "Día de Todos los Santos", "tipo": "religioso", "irrenunciable": False}],
    "diciembre": [{"mes": 12, "dia": 8, "dia_semana": "martes", "descripcion": "Inmaculada Concepción", "tipo": "religioso", "irrenunciable": False}, {"mes": 12, "dia": 25, "dia_semana": "viernes", "descripcion": "Navidad", "tipo": "religioso", "irrenunciable": True}]
  }
}

AIRPORT_CODES = {
    "Santiago": "SCEL",
    "Arica": "SCAR",
    "Iquique": "SCDA",
    "Antofagasta": "SCFA",
    "Copiapó": "SCAT",
    "La Serena": "SCSE",
    "Viña del Mar": "SCVM",
    "Concepción": "SCIE",
    "Los Ángeles": "SCGE",
    "Temuco": "SCQP",
    "Valdivia": "SCVD",
    "Osorno": "SCJO",
    "Puerto Montt": "SCTE",
    "Chiloé": "SCAP",
    "Balmaceda": "SCBA",
    "Punta Arenas": "SCCI",
    "Cholchol": "SCQP" # Mapping to nearest (Temuco)
}

# --- SERVICES ---

def get_ip_info():
    """
    Intenta obtener info geográfica básica por IP.
    Nota: En Streamlit Cloud esto devolverá la IP del servidor (USA),
    por lo que se usa principalmente para defaults locales si se corre localmente.
    """
    try:
        # Service suggested by user style response
        resp = requests.get("http://ip-api.com/json/", timeout=3)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return {}

def get_weather_boostr(city_name="Santiago"):
    """
    Obtiene el clima usando la API de Boostr.cl (Meteorología aeronáutica).
    Mapea nombres de ciudades a códigos de aeropuerto.
    """
    code = AIRPORT_CODES.get(city_name, "SCEL") # Default Santiago
    url = f"https://api.boostr.cl/weather/{code}.json"
    
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('status') == 'success':
                return data['data']
    except Exception as e:
        print(f"Weather Error: {e}")
        pass
    return None

def get_next_holiday():
    """Calcula el próximo feriado desde la fecha actual (2026 simulation or real logic)"""
    # Assuming we stick to 2026 data provided, or adapt to current year if possible?
    # User provided 2026 data specific. We will use that structure.
    
    now = datetime.datetime.now()
    # If currently 2025, we might want to look ahead to 2026? 
    # Or assuming app is running in 2026 context as per user provided json?
    # Let's map strict logic: Find first holiday >= Today.
    
    # Flat list
    all_holidays = []
    for mes_name, dias in HOLIDAYS_2026["feriados"].items():
        for d in dias:
            dt = datetime.datetime(HOLIDAYS_2026["year"], d["mes"], d["dia"])
            all_holidays.append({
                "date": dt,
                "desc": d["descripcion"],
                "irrenunciable": d["irrenunciable"]
            })
            
    all_holidays.sort(key=lambda x: x['date'])
    
    # Find next
    for h in all_holidays:
        if h['date'].date() >= now.date():
            days_left = (h['date'].date() - now.date()).days
            return h, days_left
            
    return None, -1

def render_context_widget():
    """Renders the UI component in Streamlit"""
    
    # 1. Location / Weather
    # Sidebar selection for stability
    default_idx = list(AIRPORT_CODES.keys()).index("Santiago")
    
    # Try to auto-detect from session or IP if not set
    if 'user_location' not in st.session_state:
        ip_data = get_ip_info()
        region = ip_data.get('regionName', '')
        city = ip_data.get('city', '')
        
        # Simple heuristic mapping
        detected = "Santiago"
        if "Biobío" in region or "Biobio" in region: detected = "Concepción"
        if "Araucanía" in region or "Araucania" in region: detected = "Temuco"
        if "Los Lagos" in region: detected = "Puerto Montt"
        if city in AIRPORT_CODES: detected = city
        
        st.session_state.user_location = detected

    with st.container():
        c1, c2 = st.columns([3, 1])
        with c1:
            weather = get_weather_boostr(st.session_state.user_location)
            
            # Icon Logic
            icon = "🌦️" # Default
            if weather:
                cond = weather.get('condition', '').lower()
                if "despejado" in cond or "soleado" in cond: icon = "☀️"
                elif "parcial" in cond or "escasa" in cond or "dispersa" in cond: icon = "⛅"
                elif "nublado" in cond or "cubierto" in cond: icon = "☁️"
                elif "lluvia" in cond or "chubasco" in cond or "llovizna" in cond: icon = "🌧️"
                elif "tormenta" in cond: icon = "⛈️"
                elif "nieve" in cond: icon = "❄️"
                elif "niebla" in cond or "neblina" in cond: icon = "🌫️"

                st.markdown(f"### {icon} {st.session_state.user_location}")
                st.write(f"**{weather.get('temperature')}°C** | {weather.get('condition')} | 💧 {weather.get('humidity')}%")
            else:
                st.markdown(f"### 🌦️ {st.session_state.user_location}")
                st.caption("No hay datos del clima disponibles.")
                
        with c2:
            # Edit Location
            loc = st.selectbox("Cambiar", list(AIRPORT_CODES.keys()), key="user_location_select", label_visibility="collapsed", index=list(AIRPORT_CODES.keys()).index(st.session_state.user_location) if st.session_state.user_location in AIRPORT_CODES else 0)
            if loc != st.session_state.user_location:
               st.session_state.user_location = loc
               st.rerun()

    # 2. Next Holiday
    h, days = get_next_holiday()
    if h:
        color = "red" if h['irrenunciable'] else "blue"
        if days == 0:
            msg = f"🎉 ¡HOY es **{h['desc']}**!"
        elif days == 1:
            msg = f"🚀 ¡Mañana es **{h['desc']}**!"
        else:
            msg = f"⏳ Faltan {days} días para **{h['desc']}**"
        
        st.caption(f"{msg}")
        if h['irrenunciable']:
            st.caption("🔴 *Irrenunciable*")

    st.divider()
