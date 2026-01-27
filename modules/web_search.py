"""
Módulo de búsqueda web GRATUITA para contexto externo
Usa DuckDuckGo + web scraping + Groq AI (sin costos adicionales)
"""

import requests
from bs4 import BeautifulSoup
import json

def search_web_free(query, max_results=3):
    """
    Búsqueda web GRATUITA usando DuckDuckGo Instant Answer API
    
    Args:
        query: Término de búsqueda
        max_results: Cantidad de resultados (max 3 para ahorro)
    
    Returns:
        list: Resultados con título, snippet, url
    """
    results = []
    
    # Opción 1: DuckDuckGo Instant Answer API (100% GRATIS)
    try:
        url = "https://api.duckduckgo.com/"
        params = {
            'q': query,
            'format': 'json',
            'no_html': 1,
            'skip_disambig': 1
        }
        
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        # Extraer Abstract (resumen principal)
        if data.get('Abstract'):
            results.append({
                'title': data.get('Heading', query),
                'snippet': data.get('Abstract', ''),
                'url': data.get('AbstractURL', '')
            })
        
        # Extraer Related Topics
        for topic in data.get('RelatedTopics', [])[:max_results]:
            if isinstance(topic, dict) and 'Text' in topic:
                results.append({
                    'title': topic.get('Text', '').split(' - ')[0] if ' - ' in topic.get('Text', '') else query,
                    'snippet': topic.get('Text', ''),
                    'url': topic.get('FirstURL', '')
                })
        
        if results:
            return results[:max_results]
    
    except Exception as e:
        print(f"DuckDuckGo error: {e}")
    
    # Opción 2: FALLBACK - Simple Google scraping (usar con moderación)
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        search_url = f"https://www.google.com/search?q={requests.utils.quote(query)}&num=3"
        response = requests.get(search_url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extraer resultados de búsqueda
            for g in soup.find_all('div', class_='g')[:max_results]:
                title_elem = g.find('h3')
                snippet_elem = g.find('div', class_=['VwiC3b', 'yXK7lf'])
                link_elem = g.find('a')
                
                if title_elem and snippet_elem and link_elem:
                    results.append({
                        'title': title_elem.get_text(),
                        'snippet': snippet_elem.get_text(),
                        'url': link_elem.get('href', '')
                    })
            
            return results[:max_results]
    
    except Exception as e:
        print(f"Google scraping error: {e}")
    
    return results


def summarize_context_with_ai(search_results, entity_name):
    """
    Resume resultados de búsqueda usando Groq AI (GRATIS - ya lo tienes)
    
    Args:
        search_results: Lista de resultados de búsqueda
        entity_name: Nombre de la entidad (empresa/persona)
    
    Returns:
        str: Resumen conciso en español
    """
    from modules.ai_core import _get_groq_client
    
    if not search_results:
        return f"No se encontró información reciente sobre {entity_name}."
    
    # Construir contexto compacto
    context = f"Información web sobre '{entity_name}':\n\n"
    for i, result in enumerate(search_results, 1):
        context += f"{i}. {result['title']}\n"
        context += f"   {result['snippet'][:200]}...\n\n"
    
    # Prompt ultra-compacto para Groq
    prompt = f"""Resume en 2-3 líneas lo más relevante sobre {entity_name}:

{context[:1000]}

Enfócate en: qué es/hacen, noticias recientes (últimos 30 días), datos clave."""
    
    try:
        client = _get_groq_client()
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=150  # Muy compacto
        )
        
        return completion.choices[0].message.content.strip()
    
    except Exception as e:
        # Fallback: devolver primer snippet
        return search_results[0]['snippet'][:300] if search_results else "Sin información disponible."


def enrich_event_with_free_context(event_title):
    """
    Enriquece un evento con contexto externo GRATIS
    
    Args:
        event_title: Título del evento
    
    Returns:
        str: Contexto enriquecido o None
    """
    # Extraer entidades importantes (empresas, organizaciones)
    # Palabras clave que sugieren entidades relevantes
    keywords = ['reunión', 'junta', 'presentación', 'con', 'visita']
    
    # Detectar si hay nombre propio/empresa (simplificado)
    words = event_title.split()
    potential_entities = []
    
    for i, word in enumerate(words):
        # Si la palabra empieza con mayúscula y no es palabra común
        if word[0].isupper() and word.lower() not in keywords and len(word) > 3:
            # Tomar palabra + siguiente si también es mayúscula
            if i + 1 < len(words) and words[i+1][0].isupper():
                potential_entities.append(f"{word} {words[i+1]}")
            else:
                potential_entities.append(word)
    
    if not potential_entities:
        return None
    
    # Buscar la entidad más prometedora
    entity = potential_entities[0]
    
    # Realizar búsqueda
    results = search_web_free(f"{entity} noticias chile", max_results=3)
    
    if not results:
        return None
    
    # Resumir con IA
    summary = summarize_context_with_ai(results, entity)
    
    return summary
