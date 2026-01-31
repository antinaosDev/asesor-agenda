# 🚀 Nuevas Funciones para Implementar - Priorizadas

## 📊 Matriz de Priorización

| Feature | Impacto Ventas | Facilidad | Prioridad | Tiempo Est. |
|---------|---------------|-----------|-----------|-------------|
| 1. Recordatorios Inteligentes | ⭐⭐⭐⭐⭐ | 🟢 Fácil | **ALTA** | 4 horas |
| 2. Plantillas de Eventos | ⭐⭐⭐⭐⭐ | 🟢 Fácil | **ALTA** | 3 horas |
| 3. Análisis de Productividad | ⭐⭐⭐⭐⭐ | 🟡 Media | **ALTA** | 8 horas |
| 4. Integración WhatsApp | ⭐⭐⭐⭐ | 🔴 Difícil | MEDIA | 20 horas |
| 5. Modo Equipo/Compartir | ⭐⭐⭐⭐⭐ | 🟡 Media | **ALTA** | 12 horas |
| 6. Exportar Reports PDF | ⭐⭐⭐⭐ | 🟢 Fácil | MEDIA | 6 horas |
| 7. Smart Scheduling | ⭐⭐⭐⭐⭐ | 🔴 Difícil | ALTA | 16 horas |
| 8. Modo Focus/DND | ⭐⭐⭐ | 🟢 Fácil | BAJA | 4 horas |
| 9. Análisis de Sentiment | ⭐⭐⭐⭐ | 🟡 Media | MEDIA | 6 horas |

---

## 🔥 TOP 3 - Implementar YA (Máximo Impacto)

### 1️⃣ Recordatorios Inteligentes con IA

**Problema que resuelve:**
- Usuario crea evento pero olvida preparación
- No hay contexto de QUÉ hacer antes de la reunión

**Solución:**
IA analiza evento y sugiere recordatorios automáticos:
- "Reunión con cliente X" → Recordatorio: "Revisar propuesta 30 min antes"
- "Llamada de sales" → Recordatorio: "Preparar demo 1 hora antes"
- "Presentación Q1" → Recordatorio: "Revisar slides día anterior"

**Implementación (Código):**

```python
# En modules/ai_core.py
def generate_smart_reminders(event_title, event_description, start_time):
    """
    Genera recordatorios inteligentes basados en tipo de evento
    """
    prompt = f'''Analiza este evento y sugiere 1-3 recordatorios específicos:

Evento: {event_title}
Descripción: {event_description}
Inicio: {start_time}

Genera recordatorios en formato JSON:
{{
    "reminders": [
        {{"time_before_minutes": 30, "action": "Revisar agenda del cliente"}},
        {{"time_before_minutes": 1440, "action": "Preparar presentación"}}
    ]
}}

Solo acciones CONCRETAS y ÚTILES. No genéricos.'''

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    
    try:
        result = json.loads(response.choices[0].message.content)
        return result['reminders']
    except:
        return []

# En modules/google_services.py (modificar add_event_to_calendar)
def add_event_to_calendar_with_reminders(calendar_id, event_data):
    # ... código existente ...
    
    # Generar recordatorios IA
    smart_reminders = generate_smart_reminders(
        event_data['summary'],
        event_data.get('description', ''),
        event_data['start']['dateTime']
    )
    
    # Agregar a evento
    if smart_reminders:
        event_data['reminders'] = {
            'useDefault': False,
            'overrides': [
                {'method': 'popup', 'minutes': r['time_before_minutes']}
                for r in smart_reminders
            ]
        }
    
    return service.events().insert(calendarId=calendar_id, body=event_data).execute()
```

**UI en app.py:**
```python
# En view_create() después de crear evento
if event_created:
    st.success("✅ Evento creado")
    
    # Mostrar recordatorios sugeridos
    with st.expander("🔔 Recordatorios Inteligentes Agregados"):
        for reminder in smart_reminders:
            st.info(f"⏰ {reminder['time_before_minutes']} min antes: {reminder['action']}")
```

**Impacto Comercial:**
- ✅ Feature único (competencia NO tiene esto)
- ✅ Diferenciador clave en demos
- ✅ Aumenta retención (usuarios se vuelven dependientes)

**Tiempo: 4 horas** | **ROI: ALTO**

---

### 2️⃣ Plantillas de Eventos Reutilizables

**Problema que resuelve:**
- Usuario crea mismo tipo de evento repetidamente
- "Reunión 1-on-1 equipo" siempre con misma estructura

**Solución:**
Guardar eventos como plantillas y reutilizar con 1 click

**Implementación:**

```python
# Nueva tabla en Google Sheets: event_templates
# Columnas: user, template_name, summary, duration_min, description, attendees, color

# En modules/auth.py
def save_event_template(username, template_data):
    """Guarda plantilla de evento en Google Sheets"""
    conn = st.connection("gsheets", type=GSheetsConnection)
    sheet_url = st.secrets["private_sheet_url"]
    
    # Leer sheet de templates
    df_templates = conn.read(spreadsheet=sheet_url, worksheet="event_templates")
    
    # Agregar nueva fila
    new_row = {
        'user': username,
        'template_name': template_data['name'],
        'summary': template_data['summary'],
        'duration_min': template_data['duration'],
        'description': template_data['description'],
        'attendees': ','.join(template_data.get('attendees', [])),
        'color': template_data.get('color', '1')
    }
    
    df_templates = pd.concat([df_templates, pd.DataFrame([new_row])], ignore_index=True)
    conn.update(spreadsheet=sheet_url, worksheet="event_templates", data=df_templates)
    
    st.toast("✅ Plantilla guardada")

def load_event_templates(username):
    """Carga plantillas del usuario"""
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=st.secrets["private_sheet_url"], worksheet="event_templates")
    
    user_templates = df[df['user'] == username]
    return user_templates.to_dict('records')

# En app.py (nueva sección en view_create)
def view_create():
    st.title("📅 Crear Evento Rápido")
    
    # Tab para plantillas
    tab1, tab2 = st.tabs(["➕ Crear Nuevo", "📋 Desde Plantilla"])
    
    with tab2:
        templates = auth.load_event_templates(st.session_state.license_key)
        
        if templates:
            selected_template = st.selectbox(
                "Selecciona plantilla",
                options=templates,
                format_func=lambda x: f"📌 {x['template_name']}"
            )
            
            col1, col2 = st.columns([3, 1])
            with col1:
                event_date = st.date_input("Fecha")
                event_time = st.time_input("Hora")
            
            with col2:
                if st.button("🚀 Crear desde plantilla", use_container_width=True):
                    # Crear evento usando template
                    event_data = {
                        'summary': selected_template['summary'],
                        'description': selected_template['description'],
                        'start': {
                            'dateTime': f"{event_date}T{event_time}",
                            'timeZone': 'America/Santiago'
                        },
                        'end': {
                            'dateTime': f"{event_date}T{event_time + timedelta(minutes=selected_template['duration_min'])}",
                            'timeZone': 'America/Santiago'
                        },
                        'colorId': selected_template['color']
                    }
                    
                    add_event_to_calendar(st.session_state.connected_email, event_data)
                    st.success("✅ Evento creado desde plantilla")
        else:
            st.info("No tienes plantillas guardadas. Crea un evento y márcalo como plantilla.")
    
    with tab1:
        # ... código existente de crear evento ...
        
        # Checkbox para guardar como plantilla
        save_as_template = st.checkbox("💾 Guardar como plantilla para reutilizar")
        
        if save_as_template and st.button("Crear Evento"):
            # Crear evento normal
            # ...
            
            # Guardar template
            template_name = st.text_input("Nombre de la plantilla", value=event_summary)
            auth.save_event_template(st.session_state.license_key, {
                'name': template_name,
                'summary': event_summary,
                'duration': duration_minutes,
                'description': description,
                'attendees': attendees_list,
                'color': color_id
            })
```

**Ejemplos de Plantillas:**
- 🤝 "Reunión 1-on-1 Equipo" (30 min, sin descripción)
- 📞 "Llamada de Sales" (45 min, checklist automático)
- 🎤 "Demo para Cliente" (60 min, agenda predefinida)
- ☕ "Coffee Chat" (15 min, casual)

**Impacto Comercial:**
- ✅ Reduce tiempo de creación 80%
- ✅ Usuarios power adoptan RÁPIDO
- ✅ Feature "sticky" (no querrán migrar a otra app)

**Tiempo: 3 horas** | **ROI: MUY ALTO**

---

### 3️⃣ Análisis de Productividad Semanal/Mensual

**Problema que resuelve:**
- Usuario no sabe si está siendo productivo
- No hay visibilidad de "tiempo deep work vs meetings"

**Solución:**
Dashboard con métricas avanzadas:
- Horas en reuniones vs tiempo libre
- Días con más/menos carga
- Tipos de actividades (calls, emails, tareas)
- Tendencias mes a mes

**Implementación:**

```python
# En app.py (nueva función)
def view_productivity_analytics():
    st.title("📊 Análisis de Productividad")
    
    # Selector de rango
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Desde", value=datetime.date.today() - datetime.timedelta(days=30))
    with col2:
        end_date = st.date_input("Hasta", value=datetime.date.today())
    
    # Obtener eventos del rango
    calendar_id = st.session_state.get('connected_email')
    svc = get_calendar_service()
    
    events = svc.events().list(
        calendarId=calendar_id,
        timeMin=start_date.isoformat() + 'T00:00:00Z',
        timeMax=end_date.isoformat() + 'T23:59:59Z',
        singleEvents=True,
        orderBy='startTime'
    ).execute().get('items', [])
    
    # Análisis de datos
    total_events = len(events)
    total_meeting_hours = sum([
        (datetime.datetime.fromisoformat(e['end']['dateTime'].replace('Z', '+00:00')) - 
         datetime.datetime.fromisoformat(e['start']['dateTime'].replace('Z', '+00:00'))).seconds / 3600
        for e in events if 'dateTime' in e['start']
    ])
    
    # Métricas principales
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Reuniones", total_events)
    
    with col2:
        st.metric("Horas en Meetings", f"{total_meeting_hours:.1f} hrs")
    
    with col3:
        avg_per_day = total_meeting_hours / ((end_date - start_date).days + 1)
        st.metric("Promedio Diario", f"{avg_per_day:.1f} hrs/día")
    
    with col4:
        # Calcular % de tiempo en meetings (asumiendo 8 hrs/día laborables)
        work_days = ((end_date - start_date).days + 1) * 5 / 7  # Aproximación
        total_work_hours = work_days * 8
        meeting_percentage = (total_meeting_hours / total_work_hours) * 100 if total_work_hours > 0 else 0
        
        st.metric(
            "% Tiempo en Meetings",
            f"{meeting_percentage:.0f}%",
            delta=f"{'⚠️ Alto' if meeting_percentage > 60 else '✅ OK'}",
            delta_color="inverse" if meeting_percentage > 60 else "normal"
        )
    
    # Gráfico de tendencia diaria
    st.subheader("📈 Carga de Trabajo Diaria")
    
    # Agrupar por día
    daily_hours = {}
    for event in events:
        if 'dateTime' in event['start']:
            event_date = datetime.datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00')).date()
            duration_hours = (
                datetime.datetime.fromisoformat(event['end']['dateTime'].replace('Z', '+00:00')) - 
                datetime.datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
            ).seconds / 3600
            
            daily_hours[event_date] = daily_hours.get(event_date, 0) + duration_hours
    
    # Crear DataFrame para Plotly
    df_daily = pd.DataFrame([
        {'Fecha': date, 'Horas': hours}
        for date, hours in sorted(daily_hours.items())
    ])
    
    # Gráfico de barras
    fig = px.bar(
        df_daily,
        x='Fecha',
        y='Horas',
        title="Horas de Reuniones por Día",
        color='Horas',
        color_continuous_scale=['green', 'yellow', 'red'],
        range_color=[0, 8]
    )
    
    # Línea de referencia (6 hrs = límite saludable)
    fig.add_hline(y=6, line_dash="dash", line_color="red", annotation_text="Límite Saludable (6 hrs)")
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Análisis de tipos de eventos (por palabra clave)
    st.subheader("🏷️ Distribución por Tipo")
    
    event_types = {
        'Reuniones Internas': 0,
        'Llamadas Clientes': 0,
        'Presentaciones': 0,
        'Reuniones 1-on-1': 0,
        'Otros': 0
    }
    
    for event in events:
        summary = event.get('summary', '').lower()
        if any(word in summary for word in ['cliente', 'sales', 'demo']):
            event_types['Llamadas Clientes'] += 1
        elif any(word in summary for word in ['presentación', 'keynote']):
            event_types['Presentaciones'] += 1
        elif any(word in summary for word in ['1-on-1', '1:1', 'feedback']):
            event_types['Reuniones 1-on-1'] += 1
        elif any(word in summary for word in ['equipo', 'standup', 'sync']):
            event_types['Reuniones Internas'] += 1
        else:
            event_types['Otros'] += 1
    
    # Gráfico de pie
    fig_pie = px.pie(
        values=list(event_types.values()),
        names=list(event_types.keys()),
        title="Tipos de Actividades"
    )
    st.plotly_chart(fig_pie, use_container_width=True)
    
    # Insights con IA
    st.subheader("💡 Insights Inteligentes")
    
    with st.spinner("Analizando patrones..."):
        insights_prompt = f'''Analiza estos datos de productividad y da 3 insights accionables:

Total reuniones: {total_events}
Horas totales: {total_meeting_hours:.1f}
% tiempo en meetings: {meeting_percentage:.0f}%
Distribución: {event_types}

Da recomendaciones CONCRETAS en formato bullet points.'''
        
        insights = analyze_agenda_ai(insights_prompt)  # Reutilizar función existente
        st.markdown(insights)
    
    # Exportar reporte
    if st.button("📥 Exportar Reporte PDF"):
        # TODO: Implementar export PDF
        st.info("Feature próximamente: Export a PDF")

# Agregar a navegación principal
nav_options = {
    # ... existentes ...
    "📊 Productividad": "Análisis de Productividad"
}
```

**Métricas que muestra:**
- ✅ Total reuniones en período
- ✅ Horas en meetings vs tiempo disponible
- ✅ Promedio horas/día
- ✅ % tiempo en meetings (alerta si >60%)
- ✅ Tendencia diaria (gráfico de barras)
- ✅ Distribución por tipo (pie chart)
- ✅ Insights IA personalizados
- ✅ Días más/menos cargados

**Impacto Comercial:**
- ✅ Feature "wow" en demos
- ✅ Justifica precio premium ($29.99)
- ✅ Usuarios enterprise AMAN esto
- ✅ Upsell a Plan Empresarial (métricas de equipo)

**Tiempo: 8 horas** | **ROI: ALTÍSIMO**

---

## 🔥 Bonus: Features Rápidas (1-2 horas cada una)

### 4️⃣ Modo Focus/No Molestar

**UI Simple:**
```python
# En sidebar
with st.expander("🎯 Modo Focus"):
    focus_enabled = st.toggle("Activar Modo Focus")
    
    if focus_enabled:
        focus_until = st.time_input("Hasta las", value=datetime.time(17, 0))
        
        # Silenciar notificaciones
        st.session_state.notifications_muted = True
        st.success(f"🔇 Sin notificaciones hasta {focus_until}")
```

---

### 5️⃣ Búsqueda Global Unificada

**Busca en emails, calendar, tasks simultáneamente:**
```python
def global_search(query):
    results = {
        'emails': search_emails(query),
        'events': search_calendar(query),
        'tasks': search_tasks(query)
    }
    return results

# UI
search_term = st.text_input("🔍 Buscar en todo", placeholder="cliente X, proyecto Y...")

if search_term:
    results = global_search(search_term)
    
    st.write(f"📧 {len(results['emails'])} emails")
    st.write(f"📅 {len(results['events'])} eventos")
    st.write(f"✅ {len(results['tasks'])} tareas")
```

---

### 6️⃣ Widget de "Próximas 3 Horas"

**Mini-dashboard con urgencia:**
```python
def upcoming_3_hours_widget():
    now = datetime.datetime.now(CHILE_TZ)
    three_hours_later = now + datetime.timedelta(hours=3)
    
    events = get_events_in_range(now, three_hours_later)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("⏰ Próximas 3 Horas")
    
    if events:
        for event in events[:3]:
            time_until = event['start'] - now
            minutes = time_until.seconds // 60
            
            if minutes < 15:
                st.sidebar.error(f"🔴 {event['summary']} (en {minutes} min)")
            elif minutes < 60:
                st.sidebar.warning(f"🟡 {event['summary']} (en {minutes} min)")
            else:
                st.sidebar.info(f"🟢 {event['summary']} (en {minutes} min)")
    else:
        st.sidebar.success("✨ Sin eventos próximos")
```

---

## 🎯 Recomendación de Implementación

### Semana 1: (Impacto Inmediato)
1. ✅ **Plantillas de Eventos** (3 hrs)
2. ✅ **Recordatorios Inteligentes** (4 hrs)
3. ✅ **Widget Próximas 3 Horas** (1 hr)

**Total: 8 horas → 3 features vendedoras**

---

### Semana 2: (Analytics)
4. ✅ **Análisis de Productividad** (8 hrs)
5. ✅ **Exportar PDF** (6 hrs)

**Total: 14 horas → Dashboard profesional**

---

### Mes 2: (Colaboración)
6. ✅ **Modo Equipo** (12 hrs)
7. ✅ **Compartir Calendarios** (8 hrs)

**Total: 20 horas → Feature enterprise**

---

## 💰 Impacto Comercial Proyectado

**Con estas 3 features principales:**

### Antes:
- Demo: "Es un asistente con IA para emails"
- Conversión: 30%
- Precio: $29.99/mes

### Después:
- Demo: "Asistente + Analytics + Plantillas + Recordatorios IA"
- Conversión estimada: 50%
- Precio justificado: $39.99/mes (↑33%)

**ROI de desarrollo:**
- Inversión: 25 horas dev
- Aumento precio: +$10/mes × 100 usuarios = **+$1,000/mes**
- **Recuperación: 1 mes**
- **Ganancia anual: +$12,000**

---

## 🚀 Mi Recomendación TOP

**Implementa en este orden:**

1. **Plantillas de Eventos** → Feature más fácil, impacto enorme
2. **Recordatorios Inteligentes** → Diferenciador único vs competencia
3. **Análisis de Productividad** → Justifica precio premium

**Estas 3 features te ponen 2 años adelante de la competencia.**

¿Quieres que prepare el código completo para alguna de estas? 🚀
