import requests
import streamlit as st
import datetime

def get_user_location():
    """
    Approximates user location using IP address via ip-api.com.
    Returns dict with lat, lon, city, country.
    """
    try:
        # Use a timeout to avoid hanging if the service is down
        response = requests.get('http://ip-api.com/json/', timeout=3)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                return {
                    'lat': data['lat'],
                    'lon': data['lon'],
                    'city': data['city'],
                    'country': data['countryCode']
                }
    except Exception as e:
        print(f"Location Error: {e}")
    
    # Fallback to Santiago, Chile if detection fails
    return {
        'lat': -33.4489,
        'lon': -70.6693,
        'city': 'Santiago',
        'country': 'CL'
    }

def get_weather_data(lat, lon):
    """
    Fetches current weather from Open-Meteo.
    """
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code&timezone=auto"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            current = data.get('current', {})
            
            temp = current.get('temperature_2m', 0)
            code = current.get('weather_code', 0)
            
            # Map WMO codes to icons/descriptions
            # 0: Clear, 1-3: Cloud, 45-48: Fog, 51-67: Rain, 71-77: Snow, 95-99: Thunder
            condition = "Despejado"
            icon = "sunny"
            
            if code == 0: 
                condition = "Soleado"
                icon = "sunny"
            elif code in [1, 2, 3]: 
                condition = "Parcialmente Nublado"
                icon = "partly_cloudy_day"
            elif code in [45, 48]: 
                condition = "Neblina"
                icon = "mist"
            elif code in [51, 53, 55, 61, 63, 65, 80, 81, 82]: 
                condition = "Lluvia"
                icon = "rainy"
            elif code >= 95: 
                condition = "Tormenta"
                icon = "thunderstorm"
                
            return {
                'temp': temp,
                'condition': condition,
                'icon': icon
            }
    except Exception as e:
        print(f"Weather Error: {e}")
        
    return {
        'temp': '--',
        'condition': 'No disponible',
        'icon': 'cloud_off'
    }

def get_dashboard_weather_context():
    """
    Orchestrates location and weather fetching with caching to be nice to APIs.
    """
    # Cache key based on hour to refresh hourly
    now_str = datetime.datetime.now().strftime('%Y-%m-%d-%H')
    cache_key = f"weather_context_{now_str}"
    
    if cache_key in st.session_state:
        return st.session_state[cache_key]
        
    # Fetch
    loc = get_user_location()
    weather = get_weather_data(loc['lat'], loc['lon'])
    
    result = {
        'location': loc,
        'weather': weather
    }
    
    # Save to session
    st.session_state[cache_key] = result
    return result
