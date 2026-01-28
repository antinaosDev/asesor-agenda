
import streamlit as st

def get_design_css():
    """Returns the CSS string for the application based on the HTML templates."""
    return """
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
    <style>
        /* --- GLOBAL & FONTS --- */
        .stApp {
            background-color: #102022 !important;
            font-family: 'Space Grotesk', sans-serif !important;
        }
        h1, h2, h3, h4, h5, h6, p, div, span, button, input {
            font-family: 'Space Grotesk', sans-serif !important;
        }
        
        /* --- COLORS & VARS --- */
        :root {
            --primary: #0dd7f2;
            --background-dark: #102022;
            --surface-dark: #1b2627;
            --surface-highlight: #233032;
            --border-color: #283739;
            --text-secondary: #9cb6ba;
            --tomato: #ff6347;
        }

        /* --- TABS --- */
        .stTabs [data-baseweb="tab-list"] {
            gap: 2rem;
            background-color: transparent;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 0px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 3.5rem;
            color: var(--text-secondary);
            font-weight: 700;
            padding: 0 1rem;
            border: none;
            background-color: transparent;
        }
        .stTabs [aria-selected="true"] {
            color: #ffffff !important;
            border-bottom: 3px solid var(--primary) !important;
            background-color: transparent !important;
        }
        
        /* --- CARDS & PANELS --- */
        .kpi-card {
            background-color: var(--surface-dark);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            position: relative;
            overflow: hidden;
            transition: all 0.2s ease;
        }
        .kpi-card:hover {
            transform: translateY(-2px);
            border-color: #3b5154;
        }
        
        .agenda-card {
            background-color: var(--surface-dark);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 1rem;
            position: relative;
        }
        
        /* --- EMAIL ROW --- */
        .email-row {
            background-color: var(--surface-dark);
            border-bottom: 1px solid var(--border-color);
            padding: 1rem;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        .email-row:hover {
            background-color: var(--surface-highlight);
        }
        
        /* --- BUTTONS --- */
        .primary-btn {
            background-color: var(--primary);
            color: #111718;
            font-weight: 700;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            border: none;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
        }
        .secondary-btn {
            background-color: transparent;
            color: var(--text-secondary);
            border: 1px solid #3b5154;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            cursor: pointer;
        }
        
        /* --- UTILS --- */
        .text-primary { color: var(--primary) !important; }
        .text-secondary { color: var(--text-secondary) !important; }
        .text-tomato { color: var(--tomato) !important; }
        .bg-highlight { background-color: var(--surface-highlight); }
        
        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        ::-webkit-scrollbar-track {
            background: #102022; 
        }
        ::-webkit-scrollbar-thumb {
            background: #283739; 
            border-radius: 4px;
        }
    </style>
    """

def render_kpi_card_html(title, value, trend, icon_name="timer"):
    """Generates HTML for a KPI card."""
    return f"""
    <div class="kpi-card">
        <div style="position: absolute; top: 0; right: 0; padding: 1rem; opacity: 0.1;">
            <span class="material-symbols-outlined" style="font-size: 64px; color: white;">{icon_name}</span>
        </div>
        <p style="color: #9cb6ba; font-size: 0.875rem; font-weight: 500; text-transform: uppercase;">{title}</p>
        <div style="display: flex; align-items: baseline; gap: 0.5rem;">
            <p style="color: white; font-size: 1.875rem; font-weight: 700; margin: 0;">{value}</p>
            <span style="color: #0bda54; font-size: 0.875rem; font-weight: 700; background-color: rgba(11, 218, 84, 0.1); padding: 2px 6px; rounded: 4px;">
                {trend}
            </span>
        </div>
    </div>
    """

def render_agenda_card_html(time_range, title, location, duration="1h", is_urgent=False, notes=None):
    """Generates HTML for an agenda card."""
    border_color = "var(--tomato)" if is_urgent else "var(--border-color)"
    time_color = "var(--tomato)" if is_urgent else "var(--primary)"
    
    html = f"""
    <div class="agenda-card" style="border-color: {border_color};">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.75rem;">
            <div style="display: flex; flex-direction: column;">
                <span style="color: {time_color}; font-size: 0.875rem; font-family: monospace; font-weight: 700;">{time_range}</span>
                <h4 style="color: white; font-size: 1.125rem; font-weight: 700; margin-top: 0.25rem; margin-bottom:0;">{title}</h4>
            </div>
            <span style="padding: 2px 8px; border-radius: 4px; background-color: #283739; color: #9cb6ba; font-size: 0.75rem; font-weight: 500;">{duration}</span>
        </div>
        <div style="display: flex; align-items: center; color: #9cb6ba; font-size: 0.875rem; gap: 0.5rem;">
            <span class="material-symbols-outlined" style="font-size: 16px;">location_on</span>
            {location}
        </div>
    """
    if notes:
        html += f"""
        <div style="margin-top: 0.75rem; padding: 0.5rem; background-color: var(--surface-highlight); border-radius: 4px; border: 1px solid var(--border-color);">
            <p style="color: #9cb6ba; font-size: 0.75rem; margin: 0;">{notes}</p>
        </div>
        """
    html += "</div>"
    return html

def render_email_list_header():
    return """
    <div style="display: grid; grid-template-columns: 2fr 4fr 1fr; gap: 1rem; padding: 1rem; border-bottom: 1px solid var(--border-color); background-color: #1a2024; color: #9cb6ba; font-size: 0.75rem; font-weight: 700; text-transform: uppercase;">
        <div>SENDER</div>
        <div>SUMMARY & INSIGHT</div>
        <div style="text-align: right;">TIME</div>
    </div>
    """

def render_email_row_html(sender, subject, summary, time_str, initials="JD", is_urgent=False):
    """Generates HTML for an email row."""
    # Simplified structure for Streamlit markdown
    bg_avatar = "linear-gradient(135deg, #ff6347, #7f1d1d)" if is_urgent else "linear-gradient(135deg, #3b82f6, #1e3a8a)"
    
    return f"""
    <div class="email-row">
        <div style="display: grid; grid-template-columns: 2fr 4fr 1fr; gap: 1rem; align-items: center;">
            <!-- Sender -->
            <div style="display: flex; align-items: center; gap: 0.75rem;">
                <div style="width: 2.5rem; height: 2.5rem; border-radius: 9999px; background: {bg_avatar}; display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; font-size: 0.875rem;">
                    {initials}
                </div>
                <div style="overflow: hidden;">
                    <div style="color: white; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{sender}</div>
                    <div style="color: #9cb6ba; font-size: 0.75rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{subject}</div>
                </div>
            </div>
            
            <!-- Content -->
            <div style="display: flex; flex-direction: column; gap: 0.25rem;">
                <p style="color: #d1d5db; font-size: 0.875rem; margin: 0; line-height: 1.25;">{summary}</p>
            </div>
            
            <!-- Time -->
            <div style="text-align: right;">
                <div style="color: white; font-family: monospace; font-size: 0.875rem;">{time_str}</div>
            </div>
        </div>
    </div>
    """

def render_smart_header(title, subtitle, weather_context=None):
    """
    Renders a premium 'Smart Header' with weather and date integration.
    weather_context expect dict: {'location': {...}, 'weather': {'temp': 20, 'condition': 'Soleado', 'icon': 'sunny'}}
    """
    import datetime
    
    # Date Handling
    now = datetime.datetime.now()
    d_name = now.strftime("%A") # Day Name (requires locale set in app.py for Spanish)
    d_num = now.day
    m_name = now.strftime("%B")
    
    date_str = f"{d_name} {d_num}, {m_name}".capitalize()
    
    # Weather Handling
    w_html = ""
    if weather_context:
        w_temp = weather_context['weather']['temp']
        w_cond = weather_context['weather']['condition']
        w_icon = weather_context['weather']['icon']
        w_city = weather_context['location']['city']
        
        w_html = f'<div style="display: flex; align-items: center; gap: 1rem; background: rgba(0,0,0,0.2); padding: 0.5rem 1rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1);"><div style="text-align: right;"><div style="color: white; font-weight: 700; font-size: 1.2rem; line-height: 1;">{w_temp}°</div><div style="color: #9cb6ba; font-size: 0.75rem;">{w_city}</div></div><span class="material-symbols-outlined" style="color: #0dd7f2; font-size: 2rem;">{w_icon}</span></div>'
    
    # Greeting logic based on hour
    hour = now.hour
    greeting = "Buenos días"
    if 12 <= hour < 20: greeting = "Buenas tardes"
    elif hour >= 20: greeting = "Buenas noches"
    
    return f'<div class="glass-panel" style="background: linear-gradient(135deg, rgba(24, 40, 42, 0.9) 0%, rgba(16, 32, 34, 0.95) 100%); border-left: 4px solid var(--primary); display: flex; justify-content: space-between; align-items: center; padding: 2rem; margin-bottom: 2rem; position: relative; overflow: hidden;"><div style="position: absolute; right: -20px; top: -50px; font-size: 10rem; opacity: 0.05; color: var(--primary); font-family: \'Material Symbols Outlined\'; pointer-events: none;">water_drop</div><div style="z-index: 2;"><p style="color: var(--primary); font-weight: 600; text-transform: uppercase; letter-spacing: 1px; font-size: 0.8rem; margin: 0 0 0.5rem 0;">{date_str}</p><h1 style="margin: 0; font-size: 2.5rem; color: white; font-weight: 700;">{greeting}, {title.split(" ")[0]}</h1><p style="color: #9cb6ba; font-size: 1rem; margin: 0.5rem 0 0 0;">{subtitle}</p></div><div style="z-index: 2; display: flex; align-items: center; gap: 1.5rem;">{w_html}</div></div>'

