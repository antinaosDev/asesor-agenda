"""
TTS Service Module - Text-to-Speech for Voice Briefings
Usa Edge TTS (gratis) para generar audio profesional en español
"""

import edge_tts
import asyncio
import streamlit as st
from datetime import datetime
import os

# Voces disponibles en español (Microsoft Edge TTS)
VOICES = {
    'es-MX-DaliaNeural': 'Mujer Mexicana (Profesional)',
    'es-MX-JorgeNeural': 'Hombre Mexicano (Cálido)',
    'es-ES-ElviraNeural': 'Mujer Española (Formal)',
    'es-ES-AlvaroNeural': 'Hombre Español (Ejecutivo)',
    'es-AR-ElenaNeural': 'Mujer Argentina (Amigable)',
    'es-CL-CatalinaNeural': 'Mujer Chilena (Natural)'
}

DEFAULT_VOICE = 'es-MX-DaliaNeural'  # Voz por defecto

async def generate_audio_async(text, voice=DEFAULT_VOICE, rate='+20%', volume='+0%'):
    """
    Genera audio MP3 usando Edge TTS (async)
    
    Args:
        text: Texto a convertir
        voice: ID de voz de Microsoft
        rate: Velocidad (-50% a +100%)
        volume: Volumen (-50% a +50%)
    
    Returns:
        bytes: Audio en formato MP3
    """
    communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
    
    # Generar en memoria
    audio_bytes = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes += chunk["data"]
    
    return audio_bytes

def text_to_speech(text, voice=DEFAULT_VOICE):
    """
    Wrapper síncrono para Streamlit
    
    Args:
        text: Texto para convertir a audio
        voice: Voz a usar (ver VOICES dict)
    
    Returns:
        bytes: Audio MP3 listo para st.audio()
    """
    try:
        # Ejecutar función async de forma síncrona
        audio_data = asyncio.run(generate_audio_async(text, voice))
        return audio_data
    except Exception as e:
        st.error(f"Error generando audio: {e}")
        return None

def save_audio_file(audio_bytes, filename=None):
    """
    Guarda audio en archivo temporal
    
    Args:
        audio_bytes: Datos de audio
        filename: Nombre del archivo (opcional)
    
    Returns:
        str: Path del archivo guardado
    """
    if filename is None:
        filename = f"briefing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
    
    # Crear directorio temporal si no existe
    temp_dir = "temp_audio"
    os.makedirs(temp_dir, exist_ok=True)
    
    filepath = os.path.join(temp_dir, filename)
    
    with open(filepath, 'wb') as f:
        f.write(audio_bytes)
    
    return filepath

def get_available_voices():
    """Retorna diccionario de voces disponibles"""
    return VOICES
