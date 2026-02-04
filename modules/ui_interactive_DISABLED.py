
import streamlit as st
import json

def action_card_list(items, key="action_list"):
    """
    Renders a list of interactive cards using st.components.v2.
    
    Args:
        items (list): List of dicts, each containing:
                      - id (str): Unique ID of the item
                      - title (str): Main text
                      - subtitle (str): Secondary text (optional)
                      - content (str): Body text (optional)
                      - actions (list): List of dicts for buttons:
                                        - id (str): Action ID
                                        - label (str): Button text
                                        - icon (str): Emoji or icon char
                                        - type (str): 'primary', 'danger', 'secondary'
        key (str): Unique key for the component.

    Returns:
        dict: {'itemId': str, 'actionId': str} or None if no action.
    """
    
    # --- HTML TEMPLATE ---
    # We build the HTML string dynamically based on items to pass initial state
    # This avoids complex JSON parsing in JS for V1, keeping it simple.
    
    cards_html = ""
    for item in items:
        actions_html = ""
        for act in item.get('actions', []):
            btn_class = f"btn-{act.get('type', 'secondary')}"
            auto_hide = "true" if act.get('autoHide', True) else "false"
            actions_html += f"""
                <button class="action-btn {btn_class}" 
                        data-item-id="{item['id']}" 
                        data-action-id="{act['id']}"
                        data-auto-hide="{auto_hide}">
                    {act.get('icon', '')} {act.get('label', '')}
                </button>
            """
            
        cards_html += f"""
            <div class="card" id="card-{item['id']}">
                <div class="card-content">
                    <div class="card-header">
                        <span class="card-title">{item.get('title', '')}</span>
                        <span class="card-date">{item.get('subtitle', '')}</span>
                    </div>
                    <div class="card-body">
                        {item.get('content', '')}
                    </div>
                </div>
                <div class="card-actions">
                    {actions_html}
                </div>
            </div>
        """

    full_html = f"""
    <div class="card-container">
        {cards_html}
    </div>
    """

    # --- CSS ---
    css = """
    .card-container {
        display: flex;
        flex-direction: column;
        gap: 12px;
        font-family: 'Space Grotesk', sans-serif;
    }
    
    .card {
        background: rgba(24, 40, 42, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        transition: all 0.3s ease;
        backdrop-filter: blur(12px);
    }
    
    .card.hidden {
        opacity: 0;
        transform: translateX(20px);
        height: 0;
        padding: 0;
        margin: 0;
        border: none;
        overflow: hidden;
    }
    
    .card-content {
        flex: 1;
        margin-right: 16px;
    }
    
    .card-title {
        color: #ffffff;
        font-weight: 600;
        font-size: 1rem;
        display: block;
        margin-bottom: 4px;
    }
    
    .card-date {
        color: #9cb6ba;
        font-size: 0.8rem;
    }
    
    .card-body {
        color: #d1d5db;
        font-size: 0.9rem;
        margin-top: 4px;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    
    .card-actions {
        display: flex;
        gap: 8px;
    }
    
    .action-btn {
        background: transparent;
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: #9cb6ba;
        padding: 8px 12px;
        border-radius: 8px;
        cursor: pointer;
        font-family: inherit;
        font-size: 0.85rem;
        display: flex;
        align-items: center;
        gap: 6px;
        transition: all 0.2s;
    }
    
    .action-btn:hover {
        background: rgba(255, 255, 255, 0.05);
        border-color: rgba(255, 255, 255, 0.3);
        color: white;
    }
    
    .btn-primary:hover {
        background: rgba(13, 215, 242, 0.15);
        border-color: #0dd7f2;
        color: #0dd7f2;
    }
    
    .btn-danger:hover {
        background: rgba(255, 75, 75, 0.15);
        border-color: #ff4b4b;
        color: #ff4b4b;
    }
    """

    # --- JS ---
    js = """
    export default function(component) {
        const { setTriggerValue, parentElement } = component;
        
        // Add click listeners to all buttons
        const buttons = parentElement.querySelectorAll('.action-btn');
        
        buttons.forEach((btn) => {
            btn.onclick = (e) => {
                e.preventDefault(); // Prevent accidental form submits if any
                
                const itemId = btn.getAttribute('data-item-id');
                const actionId = btn.getAttribute('data-action-id');
                
                // 1. Optimistic UI: Find parent card and hide it
                const card = parentElement.querySelector(`#card-${itemId}`);
                if (card) {
                    card.classList.add('hidden');
                }
                
                // 2. Send signal to Python
                setTriggerValue({
                    itemId: itemId,
                    actionId: actionId,
                    timestamp: Date.now() // Force update even if same action clicked twice (though component remounts usually)
                });
            };
        });
    }
    """

    # Register/Mount Component
    # We use a unique name based on key to avoid collisions if multiple lists exist, 
    # BUT st.components.v2.component registers a type. 
    # Re-registering with same name is a warning.
    # We should register ONCE globaly, but the function injects specific HTML.
    # The 'html' param is static for the component definition. 
    # For dynamic HTML, we should pass it via 'data' param in the mount call 
    # OR (as per docs example 2) update innerHTML.
    # Let's use the Example 2 approach: Generic component that populates from data.
    
    # Define generic component ONCE? 
    # Streamlit scripts rerun top to bottom. 
    # If we define it inside this function, it registers every rerun. 
    # Optimization: Use a singleton pattern or just rely on Streamlit handling it (warning is logged).
    # For safety/simplicity in this context, we'll register it with a fixed name "action_card_list_v1".
    
    generic_js = """
    export default function(component) {
        const { data, setTriggerValue, parentElement } = component;
        
        // Inject HTML
        parentElement.innerHTML = data;
        
        // Add Listeners
        const buttons = parentElement.querySelectorAll('.action-btn');
        
        buttons.forEach((btn) => {
            btn.onclick = (e) => {
                // e.preventDefault(); 
                
                const itemId = btn.getAttribute('data-item-id');
                const actionId = btn.getAttribute('data-action-id');
                const autoHide = btn.getAttribute('data-auto-hide') === 'true';
                
                // Optimistic UI
                if (autoHide) {
                    const card = parentElement.querySelector(`#card-${itemId}`);
                    if (card) {
                        card.classList.add('hidden');
                    }
                }
                
                setTriggerValue({
                    itemId: itemId,
                    actionId: actionId,
                    timestamp: Date.now()
                });
            };
        });
    }
    """
    
    # We need to wrap this so it works. 
    # Note: Streamlit V2 components might be experimental/preview.
    # If standard st.components.v2 is not available in the installed version, we might crash.
    # Checking requirements.txt: streamlit is there. 
    # V2 was introduced recently. Let's assume 1.40+ or similar.
    
    # If st.components.v2 is missing, we fallback? 
    # The user explicitly asked for v2.
    
    try:
        # Register component type
        Component = st.components.v2.component(
            "action_card_list",
            css=css,
            js=generic_js
        )
        
        # Mount instance
        return Component(key=key, data=full_html, on_change=None)
        
    except AttributeError:
        st.error("Tu versión de Streamlit no soporta st.components.v2. Actualiza tu requirements.txt.")
        return None
