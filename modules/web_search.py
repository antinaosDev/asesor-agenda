"""
Módulo de búsqueda web GRATUITA para contexto externo
Usa DuckDuckGo HTML Scraping + Groq AI para queries inteligentes
"""

import requests
from bs4 import BeautifulSoup
import json
import urllib.parse
from modules.ai_core import _get_groq_client

def generate_smart_query(title, description):
    """
    Usa IA para extraer el MEJOR término de búsqueda
    basado en título y descripción.
    """
    try:
        client = _get_groq_client()
        # Truncate description to save tokens
        desc_short = (description or "")[:300]
        
        prompt = f"""Tu misión es crear UNA sola consulta de búsqueda web (Query) para encontrar información sobre este evento.
        
        Evento: {title}
        Detalles: {desc_short}
        
        Instrucciones:
        1. Identifica el tema central, programa gubernamental, sigla o entidad.
        2. Si es una sigla (ej: MAIS, RCE, REM), agrégale contexto (ej: "Salud Chile", "Minsal").
        3. NO inventes info.
        4. SOLO devuelve la query (ej: "Programa MAIS Minsal Chile").
        5. Máximo 4-5 palabras.
        """
        
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=20
        )
        return completion.choices[0].message.content.strip().replace('"', '')
    except Exception as e:
        print(f"Error generando query: {e}")
        return title  # Fallback

def search_web_free(query, max_results=3):
    """
    Búsqueda robusta scrapeando DuckDuckGo HTML (No API, No key required)
    """
    results = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # Scrape DuckDuckGo HTML version (lighter, less blocking)
        encoded_query = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find result links
            for result in soup.find_all('div', class_='result')[:max_results]:
                title_tag = result.find('a', class_='result__a')
                snippet_tag = result.find('a', class_='result__snippet')
                
                if title_tag and snippet_tag:
                    link = title_tag.get('href', '')
                    # Unescape DDG redirect url if needed, but often href is enough or relative
                    # DDG HTML often gives simple links
                    
                    results.append({
                        'title': title_tag.get_text(strip=True),
                        'snippet': snippet_tag.get_text(strip=True),
                        'url': link
                    })
        
        # Fallback to Google if DDG fails or yields 0
        if not results:
            google_url = f"https://www.google.com/search?q={encoded_query}&num={max_results}"
            resp_g = requests.get(google_url, headers=headers, timeout=5)
            if resp_g.status_code == 200:
                soup_g = BeautifulSoup(resp_g.text, 'html.parser')
                for g in soup_g.find_all('div', class_='g')[:max_results]:
                    t_elem = g.find('h3')
                    s_elem = g.find('div', class_='VwiC3b') or g.find('span', class_='aCOpRe')
                    
                    if t_elem:
                        results.append({
                            'title': t_elem.get_text(strip=True),
                            'snippet': s_elem.get_text(strip=True) if s_elem else "",
                            'url': ""
                        })

        return results[:max_results]

    except Exception as e:
        print(f"Search Error: {e}")
        return []

def summarize_context_with_ai(search_results, topic):
    """Resume resultados con enfoque ejecutivo"""
    if not search_results:
        return None
    
    client = _get_groq_client()
    context = "\n".join([f"- {r['title']}: {r['snippet']}" for r in search_results])
    
    prompt = f"""Analiza estos resultados de búsqueda sobre '{topic}' y resume lo más útil para un gerente de salud/administrativo.
    
    Contexto Web:
    {context}
    
    Salida: Un párrafo breve (max 3 líneas) explicando qué es, implicancias o plazos si los hay. Si no hay nada relevante, di "No se encontró información específica"."""
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=150
        )
        return completion.choices[0].message.content.strip()
    except:
        return search_results[0]['snippet']

def enrich_event_with_free_context(event_title, event_description=""):
    """
    Flujo principal:
    1. Generar Query Inteligente (Título + Desc)
    2. Buscar en Web (DDG/Google)
    3. Resumir Hallazgos
    """
    # 1. Generate Query
    search_query = generate_smart_query(event_title, event_description)
    
    # 2. Search
    results = search_web_free(search_query)
    
    if not results:
        return f"⚠️ No se encontró info web para: '{search_query}'"
    
    # 3. Summarize
    summary = summarize_context_with_ai(results, search_query)
    
    return f"🌍 **Contexto Web ({search_query})**:\n{summary}"
